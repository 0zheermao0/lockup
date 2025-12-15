from rest_framework import generics, permissions, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from django.db.models import Q
from django.utils import timezone
from datetime import timedelta
from django.shortcuts import get_object_or_404
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
import logging
from .models import Post, PostLike, Comment, CommentLike
from .serializers import (
    PostSerializer, PostCreateSerializer, CommentSerializer,
    CommentCreateSerializer, PostLikeSerializer, CommentLikeSerializer,
    PostStatsSerializer, CheckinVerificationSerializer
)
from users.models import Notification
from tasks.pagination import DynamicPageNumberPagination

logger = logging.getLogger(__name__)


class PostListCreateView(generics.ListCreateAPIView):
    """动态列表和创建视图"""

    permission_classes = [permissions.IsAuthenticated]
    pagination_class = DynamicPageNumberPagination

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return PostCreateSerializer
        return PostSerializer

    def create(self, request, *args, **kwargs):
        """重写create方法以确保响应序列化正确"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        post = serializer.save()

        # 重新获取post实例，确保正确的预取关联关系
        post = Post.objects.select_related('user').prefetch_related(
            'images', 'likes', 'comments__images'
        ).get(id=post.id)

        # 使用PostSerializer序列化响应
        response_serializer = PostSerializer(post, context=self.get_serializer_context())
        headers = self.get_success_headers(response_serializer.data)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    def get_queryset(self):
        queryset = Post.objects.select_related('user').prefetch_related(
            'images', 'likes', 'comments__images'
        )

        # 筛选参数
        post_type = self.request.query_params.get('type', None)
        search = self.request.query_params.get('search', None)
        user_id = self.request.query_params.get('user', None)

        if post_type:
            queryset = queryset.filter(post_type=post_type)

        if search:
            queryset = queryset.filter(
                Q(content__icontains=search) |
                Q(user__username__icontains=search)
            )

        if user_id:
            try:
                user_id_int = int(user_id)
                queryset = queryset.filter(user_id=user_id_int)
            except ValueError:
                pass

        return queryset.order_by('-created_at')

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['request'] = self.request
        return context


@api_view(['POST', 'DELETE'])
@permission_classes([permissions.IsAuthenticated])
def toggle_post_like(request, post_id):
    """切换动态点赞状态"""
    try:
        post = Post.objects.get(id=post_id)
    except Post.DoesNotExist:
        return Response(
            {'error': '动态不存在'},
            status=status.HTTP_404_NOT_FOUND
        )

    like, created = PostLike.objects.get_or_create(
        user=request.user,
        post=post
    )

    if request.method == 'POST':
        if not created:
            return Response({'message': '已经点过赞了'})

        # 增加点赞数
        post.likes_count += 1
        post.save(update_fields=['likes_count'])

        # 给动态作者加金币
        if post.user != request.user:
            post.user.coins += 1
            post.user.total_likes_received += 1
            post.user.save(update_fields=['coins', 'total_likes_received'])

            # 创建点赞通知
            Notification.create_notification(
                recipient=post.user,
                notification_type='post_liked',
                actor=request.user,
                related_object_type='post',
                related_object_id=post.id
            )

        # 更新用户活跃度
        request.user.update_activity()

        return Response({
            'message': '点赞成功',
            'likes_count': post.likes_count
        })

    elif request.method == 'DELETE':
        if not created:
            like.delete()

            # 减少点赞数
            post.likes_count = max(0, post.likes_count - 1)
            post.save(update_fields=['likes_count'])

            # 减少动态作者金币
            if post.user != request.user:
                post.user.coins = max(0, post.user.coins - 1)
                post.user.total_likes_received = max(0, post.user.total_likes_received - 1)
                post.user.save(update_fields=['coins', 'total_likes_received'])

            return Response({
                'message': '取消点赞成功',
                'likes_count': post.likes_count
            })

        return Response({'message': '还没有点赞'})


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def get_post_comments(request, post_id):
    """获取动态的评论列表（分页）"""
    try:
        # 获取动态
        post = Post.objects.get(id=post_id)

        # 分页参数
        page = int(request.GET.get('page', 1))
        page_size = min(int(request.GET.get('page_size', 5)), 20)  # 限制最大每页20个

        # 获取评论查询集
        comments_queryset = Comment.objects.filter(post=post).select_related(
            'user'
        ).prefetch_related(
            'images', 'likes'
        ).order_by('-created_at')

        # 分页
        paginator = Paginator(comments_queryset, page_size)

        try:
            comments_page = paginator.page(page)
        except PageNotAnInteger:
            comments_page = paginator.page(1)
        except EmptyPage:
            comments_page = paginator.page(paginator.num_pages)

        # 序列化评论
        comments_data = []
        for comment in comments_page:
            # 检查是否已点赞
            is_liked = CommentLike.objects.filter(user=request.user, comment=comment).exists()

            comment_data = {
                'id': str(comment.id),
                'user': {
                    'id': comment.user.id,
                    'username': comment.user.username,
                    'avatar': comment.user.avatar.url if comment.user.avatar else None,
                    'level': comment.user.level,
                },
                'content': comment.content,
                'parent': str(comment.parent.id) if comment.parent else None,
                'likes_count': comment.likes_count,
                'is_liked': is_liked,
                'images': [
                    {
                        'id': img.id,
                        'image': img.image.url,
                        'order': img.order,
                        'created_at': img.created_at.isoformat()
                    }
                    for img in comment.images.all()
                ],
                'created_at': comment.created_at.isoformat(),
                'updated_at': comment.updated_at.isoformat(),
            }

            # 获取回复（只获取直接回复，不递归）
            replies = Comment.objects.filter(parent=comment).select_related('user').prefetch_related('images', 'likes')[:3]
            comment_data['replies'] = []
            for reply in replies:
                is_reply_liked = CommentLike.objects.filter(user=request.user, comment=reply).exists()
                comment_data['replies'].append({
                    'id': str(reply.id),
                    'user': {
                        'id': reply.user.id,
                        'username': reply.user.username,
                        'avatar': reply.user.avatar.url if reply.user.avatar else None,
                        'level': reply.user.level,
                    },
                    'content': reply.content,
                    'likes_count': reply.likes_count,
                    'is_liked': is_reply_liked,
                    'created_at': reply.created_at.isoformat(),
                })

            comments_data.append(comment_data)

        return Response({
            'comments': comments_data,
            'pagination': {
                'page': comments_page.number,
                'page_size': page_size,
                'total_pages': paginator.num_pages,
                'total_count': paginator.count,
                'has_next': comments_page.has_next(),
                'has_previous': comments_page.has_previous(),
            }
        })

    except Post.DoesNotExist:
        return Response({'error': '动态不存在'}, status=404)
    except Exception as e:
        logger.error(f"Error getting post comments: {e}")
        return Response({'error': '获取评论失败'}, status=500)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def post_stats(request):
    """动态统计信息"""
    today = timezone.now().date()

    # 总动态数
    total_posts = Post.objects.count()

    # 今日动态数
    posts_today = Post.objects.filter(
        created_at__date=today
    ).count()

    # 总点赞数
    total_likes = PostLike.objects.count()

    # 总评论数
    total_comments = Comment.objects.count()

    # 打卡动态数
    checkin_posts = Post.objects.filter(post_type='checkin').count()

    # 已验证打卡数
    verified_checkins = Post.objects.filter(
        post_type='checkin',
        is_verified=True
    ).count()

    stats_data = {
        'total_posts': total_posts,
        'posts_today': posts_today,
        'total_likes': total_likes,
        'total_comments': total_comments,
        'checkin_posts': checkin_posts,
        'verified_checkins': verified_checkins,
    }

    serializer = PostStatsSerializer(stats_data)
    return Response(serializer.data)


@api_view(['DELETE'])
@permission_classes([permissions.IsAuthenticated])
def delete_post(request, post_id):
    """删除动态"""
    try:
        post = get_object_or_404(Post, id=post_id)
    except:
        return Response(
            {'error': '动态不存在'},
            status=status.HTTP_404_NOT_FOUND
        )

    # 检查权限：只有发帖人或超级管理员可以删除
    if request.user != post.user and not request.user.is_superuser:
        return Response(
            {'error': '没有权限删除该动态'},
            status=status.HTTP_403_FORBIDDEN
        )

    # 删除动态（级联删除相关数据）
    post.delete()

    # 更新用户统计
    if post.user.total_posts > 0:
        post.user.total_posts -= 1
        post.user.save(update_fields=['total_posts'])

    return Response({'message': '删除成功'}, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def get_post_detail(request, post_id):
    """获取单个动态详情"""
    try:
        post = Post.objects.select_related('user').prefetch_related(
            'images', 'likes'
        ).get(id=post_id)
    except Post.DoesNotExist:
        return Response(
            {'error': '动态不存在'},
            status=status.HTTP_404_NOT_FOUND
        )

    serializer = PostSerializer(post, context={'request': request})
    return Response(serializer.data)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def create_comment(request, post_id):
    """创建评论"""
    try:
        post = Post.objects.get(id=post_id)
    except Post.DoesNotExist:
        return Response(
            {'error': '动态不存在'},
            status=status.HTTP_404_NOT_FOUND
        )

    serializer = CommentCreateSerializer(
        data=request.data,
        context={'request': request, 'post_id': post_id}
    )

    if serializer.is_valid():
        comment = serializer.save()

        # 创建评论通知 - 通知动态作者
        if comment.user != post.user:
            Notification.create_notification(
                recipient=post.user,
                notification_type='post_commented',
                actor=comment.user,
                related_object_type='post',
                related_object_id=post.id,
                extra_data={'comment_id': str(comment.id)}
            )

        # 如果是回复评论，通知被回复的用户
        if comment.parent and comment.user != comment.parent.user:
            Notification.create_notification(
                recipient=comment.parent.user,
                notification_type='comment_replied',
                actor=comment.user,
                related_object_type='comment',
                related_object_id=comment.parent.id,
                extra_data={'post_id': str(post.id), 'reply_id': str(comment.id)}
            )

        # 返回完整的评论数据
        response_serializer = CommentSerializer(comment, context={'request': request})
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST', 'DELETE'])
@permission_classes([permissions.IsAuthenticated])
def toggle_comment_like(request, comment_id):
    """切换评论点赞状态"""
    try:
        comment = Comment.objects.get(id=comment_id)
    except Comment.DoesNotExist:
        return Response(
            {'error': '评论不存在'},
            status=status.HTTP_404_NOT_FOUND
        )

    like, created = CommentLike.objects.get_or_create(
        user=request.user,
        comment=comment
    )

    if request.method == 'POST':
        if not created:
            return Response({'message': '已经点过赞了'})

        # 增加点赞数
        comment.likes_count += 1
        comment.save(update_fields=['likes_count'])

        # 给评论作者加金币
        if comment.user != request.user:
            comment.user.coins += 1
            comment.user.save(update_fields=['coins'])

            # 创建评论点赞通知
            Notification.create_notification(
                recipient=comment.user,
                notification_type='comment_liked',
                actor=request.user,
                related_object_type='comment',
                related_object_id=comment.id,
                extra_data={'post_id': str(comment.post.id)}
            )

        # 更新用户活跃度
        request.user.update_activity()

        return Response({
            'message': '点赞成功',
            'likes_count': comment.likes_count
        })

    elif request.method == 'DELETE':
        if not created:
            like.delete()

            # 减少点赞数
            comment.likes_count = max(0, comment.likes_count - 1)
            comment.save(update_fields=['likes_count'])

            # 减少评论作者金币
            if comment.user != request.user:
                comment.user.coins = max(0, comment.user.coins - 1)
                comment.user.save(update_fields=['coins'])

            return Response({
                'message': '取消点赞成功',
                'likes_count': comment.likes_count
            })

        return Response({'message': '还没有点赞'})


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def get_post_comments(request, post_id):
    """获取动态的评论列表（分页）"""
    try:
        # 获取动态
        post = Post.objects.get(id=post_id)

        # 分页参数
        page = int(request.GET.get('page', 1))
        page_size = min(int(request.GET.get('page_size', 5)), 20)  # 限制最大每页20个

        # 获取评论查询集
        comments_queryset = Comment.objects.filter(post=post).select_related(
            'user'
        ).prefetch_related(
            'images', 'likes'
        ).order_by('-created_at')

        # 分页
        paginator = Paginator(comments_queryset, page_size)

        try:
            comments_page = paginator.page(page)
        except PageNotAnInteger:
            comments_page = paginator.page(1)
        except EmptyPage:
            comments_page = paginator.page(paginator.num_pages)

        # 序列化评论
        comments_data = []
        for comment in comments_page:
            # 检查是否已点赞
            is_liked = CommentLike.objects.filter(user=request.user, comment=comment).exists()

            comment_data = {
                'id': str(comment.id),
                'user': {
                    'id': comment.user.id,
                    'username': comment.user.username,
                    'avatar': comment.user.avatar.url if comment.user.avatar else None,
                    'level': comment.user.level,
                },
                'content': comment.content,
                'parent': str(comment.parent.id) if comment.parent else None,
                'likes_count': comment.likes_count,
                'is_liked': is_liked,
                'images': [
                    {
                        'id': img.id,
                        'image': img.image.url,
                        'order': img.order,
                        'created_at': img.created_at.isoformat()
                    }
                    for img in comment.images.all()
                ],
                'created_at': comment.created_at.isoformat(),
                'updated_at': comment.updated_at.isoformat(),
            }

            # 获取回复（只获取直接回复，不递归）
            replies = Comment.objects.filter(parent=comment).select_related('user').prefetch_related('images', 'likes')[:3]
            comment_data['replies'] = []
            for reply in replies:
                is_reply_liked = CommentLike.objects.filter(user=request.user, comment=reply).exists()
                comment_data['replies'].append({
                    'id': str(reply.id),
                    'user': {
                        'id': reply.user.id,
                        'username': reply.user.username,
                        'avatar': reply.user.avatar.url if reply.user.avatar else None,
                        'level': reply.user.level,
                    },
                    'content': reply.content,
                    'likes_count': reply.likes_count,
                    'is_liked': is_reply_liked,
                    'created_at': reply.created_at.isoformat(),
                })

            comments_data.append(comment_data)

        return Response({
            'comments': comments_data,
            'pagination': {
                'page': comments_page.number,
                'page_size': page_size,
                'total_pages': paginator.num_pages,
                'total_count': paginator.count,
                'has_next': comments_page.has_next(),
                'has_previous': comments_page.has_previous(),
            }
        })

    except Post.DoesNotExist:
        return Response({'error': '动态不存在'}, status=404)
    except Exception as e:
        logger.error(f"Error getting post comments: {e}")
        return Response({'error': '获取评论失败'}, status=500)
