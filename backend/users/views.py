from rest_framework import generics, permissions, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.authtoken.models import Token
from django.contrib.auth import login, logout
from django.db.models import Q, Count
from django.utils import timezone
from datetime import timedelta
from tasks.pagination import DynamicPageNumberPagination
from .models import User, Friendship, UserLevelUpgrade, DailyLoginReward, Notification
from .serializers import (
    UserSerializer, UserPublicSerializer, UserRegistrationSerializer,
    UserLoginSerializer, UserProfileUpdateSerializer, FriendshipSerializer,
    FriendRequestSerializer, UserLevelUpgradeSerializer, UserStatsSerializer,
    PasswordChangeSerializer, SimplePasswordChangeSerializer, NotificationSerializer, NotificationCreateSerializer
)


class UserRegistrationView(generics.CreateAPIView):
    """用户注册视图"""

    queryset = User.objects.all()
    serializer_class = UserRegistrationSerializer
    permission_classes = [permissions.AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        # 创建认证token
        token, created = Token.objects.get_or_create(user=user)

        return Response({
            'user': UserSerializer(user).data,
            'token': token.key,
            'message': '注册成功'
        }, status=status.HTTP_201_CREATED)


class UserLoginView(generics.GenericAPIView):
    """用户登录视图"""

    serializer_class = UserLoginSerializer
    permission_classes = [permissions.AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = serializer.validated_data['user']
        login(request, user)

        # 获取或创建token
        token, created = Token.objects.get_or_create(user=user)

        # 更新用户活跃度
        user.update_activity()

        # 处理每日登录奖励
        today = timezone.now().date()

        # 使用get_or_create避免竞争条件
        reward_amount = user.get_daily_login_reward()
        daily_reward, created = DailyLoginReward.objects.get_or_create(
            user=user,
            date=today,
            defaults={
                'user_level': user.level,
                'reward_amount': reward_amount
            }
        )

        daily_reward_message = ""
        if created:
            # 只有在新创建奖励记录时才给用户增加积分
            user.coins += reward_amount
            user.save()

            # 创建每日登录奖励通知
            Notification.create_notification(
                recipient=user,
                notification_type='coins_earned_daily_login',
                actor=None,  # 系统通知
                extra_data={
                    'user_level': user.level,
                    'reward_amount': reward_amount,
                    'daily_reward_date': today.isoformat()
                },
                priority='normal'
            )

            daily_reward_message = f"，获得每日登录奖励{reward_amount}积分"
            print(f"Daily login reward created for user {user.username} on {today}: {reward_amount} coins")
        else:
            print(f"Daily login reward already exists for user {user.username} on {today}")

        return Response({
            'user': UserSerializer(user).data,
            'token': token.key,
            'message': f'登录成功{daily_reward_message}'
        })


class UserLogoutView(generics.GenericAPIView):
    """用户登出视图"""

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, *args, **kwargs):
        # 删除token
        try:
            token = Token.objects.get(user=request.user)
            token.delete()
        except Token.DoesNotExist:
            pass

        logout(request)
        return Response({'message': '登出成功'})


class UserProfileView(generics.RetrieveUpdateAPIView):
    """用户资料视图"""

    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user

    def get_serializer_class(self):
        if self.request.method == 'PATCH':
            return UserProfileUpdateSerializer
        return UserSerializer


class UserDetailView(generics.RetrieveAPIView):
    """其他用户详情视图"""

    queryset = User.objects.all()
    serializer_class = UserPublicSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['request_user'] = self.request.user
        return context


class UserListView(generics.ListAPIView):
    """用户列表视图"""

    queryset = User.objects.all()
    serializer_class = UserPublicSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        queryset = super().get_queryset()
        search = self.request.query_params.get('search', None)
        level = self.request.query_params.get('level', None)

        if search:
            queryset = queryset.filter(
                Q(username__icontains=search) | Q(bio__icontains=search)
            )

        if level:
            try:
                level_int = int(level)
                queryset = queryset.filter(level=level_int)
            except ValueError:
                pass

        return queryset.order_by('-activity_score', '-last_active')


class FriendListView(generics.ListAPIView):
    """好友列表视图"""

    serializer_class = FriendshipSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        return Friendship.objects.filter(
            Q(from_user=user) | Q(to_user=user),
            status='accepted'
        )


class FriendRequestView(generics.CreateAPIView):
    """发送好友请求视图"""

    serializer_class = FriendRequestSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['request'] = self.request
        return context


class FriendRequestListView(generics.ListAPIView):
    """好友请求列表视图"""

    serializer_class = FriendshipSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        return Friendship.objects.filter(
            to_user=user,
            status='pending'
        ).order_by('-created_at')


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def accept_friend_request(request, friendship_id):
    """接受好友请求"""
    try:
        friendship = Friendship.objects.get(
            id=friendship_id,
            to_user=request.user,
            status='pending'
        )
        friendship.status = 'accepted'
        friendship.save()

        # 创建反向好友关系
        Friendship.objects.get_or_create(
            from_user=friendship.to_user,
            to_user=friendship.from_user,
            defaults={'status': 'accepted'}
        )

        return Response({
            'message': '好友请求已接受',
            'friendship': FriendshipSerializer(friendship).data
        })
    except Friendship.DoesNotExist:
        return Response(
            {'error': '好友请求不存在'},
            status=status.HTTP_404_NOT_FOUND
        )


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def reject_friend_request(request, friendship_id):
    """拒绝好友请求"""
    try:
        friendship = Friendship.objects.get(
            id=friendship_id,
            to_user=request.user,
            status='pending'
        )
        friendship.delete()

        return Response({'message': '好友请求已拒绝'})
    except Friendship.DoesNotExist:
        return Response(
            {'error': '好友请求不存在'},
            status=status.HTTP_404_NOT_FOUND
        )


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def promote_user(request, user_id):
    """晋升用户等级（仅4级用户可操作）"""
    if request.user.level != 4:
        return Response(
            {'error': '只有4级用户可以晋升其他用户'},
            status=status.HTTP_403_FORBIDDEN
        )

    try:
        user = User.objects.get(id=user_id)
        if user.level >= 4:
            return Response(
                {'error': '用户已是最高等级'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 检查今日是否已经晋升过其他用户
        today = timezone.now().date()
        today_promotions = UserLevelUpgrade.objects.filter(
            promoted_by=request.user,
            created_at__date=today,
            reason='manual'
        ).count()

        if today_promotions >= 1:
            return Response(
                {'error': '每天只能晋升一个用户'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 执行晋升
        old_level = user.level
        user.level = min(4, user.level + 1)
        user.save()

        # 记录晋升日志
        UserLevelUpgrade.objects.create(
            user=user,
            promoted_by=request.user,
            from_level=old_level,
            to_level=user.level,
            reason='manual'
        )

        return Response({
            'message': f'用户已晋升至{user.level}级',
            'user': UserPublicSerializer(user).data
        })

    except User.DoesNotExist:
        return Response(
            {'error': '用户不存在'},
            status=status.HTTP_404_NOT_FOUND
        )


class PasswordChangeView(generics.GenericAPIView):
    """密码修改视图"""

    serializer_class = PasswordChangeSerializer
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response({'message': '密码修改成功'})


class SimplePasswordChangeView(APIView):
    """简化密码修改视图（无需原密码验证）"""

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        """处理密码修改请求"""
        serializer = SimplePasswordChangeSerializer(
            data=request.data,
            context={'request': request}
        )

        if serializer.is_valid():
            serializer.save()
            return Response({
                'message': '密码修改成功'
            }, status=status.HTTP_200_OK)

        return Response(
            serializer.errors,
            status=status.HTTP_400_BAD_REQUEST
        )


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def upload_avatar(request):
    """上传用户头像"""
    if 'avatar' not in request.FILES:
        return Response(
            {'error': '请选择头像文件'},
            status=status.HTTP_400_BAD_REQUEST
        )

    avatar_file = request.FILES['avatar']

    # 验证文件类型
    if not avatar_file.content_type.startswith('image/'):
        return Response(
            {'error': '请上传图片文件'},
            status=status.HTTP_400_BAD_REQUEST
        )

    # 验证文件大小 (5MB)
    if avatar_file.size > 5 * 1024 * 1024:
        return Response(
            {'error': '图片大小不能超过5MB'},
            status=status.HTTP_400_BAD_REQUEST
        )

    # 保存头像
    user = request.user
    user.avatar = avatar_file
    user.save()

    # 更新用户活跃度
    user.update_activity()

    return Response({
        'message': '头像上传成功',
        'avatar_url': user.avatar.url if user.avatar else None
    })


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def user_stats(request):
    """用户统计信息"""
    today = timezone.now().date()
    week_ago = today - timedelta(days=7)

    # 总用户数
    total_users = User.objects.count()

    # 等级分布
    level_distribution = {}
    for i in range(1, 5):
        level_distribution[f'level_{i}'] = User.objects.filter(level=i).count()

    # 今日活跃用户
    active_users_today = User.objects.filter(
        last_active__date=today
    ).count()

    # 本周新用户
    new_users_this_week = User.objects.filter(
        created_at__date__gte=week_ago
    ).count()

    # 最活跃用户（前10名）
    top_active_users = User.objects.order_by(
        '-activity_score'
    )[:10]

    stats_data = {
        'total_users': total_users,
        'level_distribution': level_distribution,
        'active_users_today': active_users_today,
        'new_users_this_week': new_users_this_week,
        'top_active_users': top_active_users
    }

    serializer = UserStatsSerializer(stats_data)
    return Response(serializer.data)


class NotificationListView(generics.ListAPIView):
    """通知列表视图"""
    serializer_class = NotificationSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = DynamicPageNumberPagination

    def get_queryset(self):
        user = self.request.user

        # 获取查询参数
        is_read = self.request.query_params.get('is_read', None)
        notification_type = self.request.query_params.get('type', None)

        queryset = Notification.objects.filter(recipient=user)

        # 按已读状态过滤
        if is_read is not None:
            queryset = queryset.filter(is_read=is_read.lower() == 'true')

        # 按通知类型过滤
        if notification_type:
            queryset = queryset.filter(notification_type=notification_type)

        # 排序（移除手动limit处理，让DRF pagination处理）
        return queryset.order_by('-created_at')


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def mark_notification_read(request, notification_id):
    """标记通知为已读"""
    try:
        notification = Notification.objects.get(
            id=notification_id,
            recipient=request.user
        )
        notification.mark_as_read()

        return Response({
            'message': '通知已标记为已读',
            'notification': NotificationSerializer(notification).data
        })
    except Notification.DoesNotExist:
        return Response(
            {'error': '通知不存在'},
            status=status.HTTP_404_NOT_FOUND
        )


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def mark_all_notifications_read(request):
    """标记所有通知为已读"""
    count = Notification.objects.filter(
        recipient=request.user,
        is_read=False
    ).update(
        is_read=True,
        read_at=timezone.now()
    )

    return Response({
        'message': f'已标记{count}条通知为已读',
        'marked_count': count
    })


@api_view(['DELETE'])
@permission_classes([permissions.IsAuthenticated])
def delete_notification(request, notification_id):
    """删除通知"""
    try:
        notification = Notification.objects.get(
            id=notification_id,
            recipient=request.user
        )
        notification.delete()

        return Response({'message': '通知已删除'})
    except Notification.DoesNotExist:
        return Response(
            {'error': '通知不存在'},
            status=status.HTTP_404_NOT_FOUND
        )


@api_view(['DELETE'])
@permission_classes([permissions.IsAuthenticated])
def clear_read_notifications(request):
    """清理所有已读通知"""
    count, _ = Notification.objects.filter(
        recipient=request.user,
        is_read=True
    ).delete()

    return Response({
        'message': f'已清理{count}条已读通知',
        'cleared_count': count
    })


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def notification_stats(request):
    """获取通知统计信息"""
    user = request.user

    total_notifications = Notification.objects.filter(recipient=user).count()
    unread_notifications = Notification.objects.filter(
        recipient=user,
        is_read=False
    ).count()

    # 按类型统计未读通知
    unread_by_type = {}
    for type_choice in Notification.TYPE_CHOICES:
        type_name = type_choice[0]
        type_display = type_choice[1]

        count = Notification.objects.filter(
            recipient=user,
            notification_type=type_name,
            is_read=False
        ).count()

        if count > 0:
            unread_by_type[type_name] = {
                'display_name': type_display,
                'count': count
            }

    # 按优先级统计未读通知
    unread_by_priority = {}
    for priority_choice in Notification.PRIORITY_CHOICES:
        priority_name = priority_choice[0]
        priority_display = priority_choice[1]

        count = Notification.objects.filter(
            recipient=user,
            priority=priority_name,
            is_read=False
        ).count()

        if count > 0:
            unread_by_priority[priority_name] = {
                'display_name': priority_display,
                'count': count
            }

    return Response({
        'total_notifications': total_notifications,
        'unread_notifications': unread_notifications,
        'unread_by_type': unread_by_type,
        'unread_by_priority': unread_by_priority
    })


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def create_notification(request):
    """创建通知（管理员功能）"""
    # 检查是否是管理员
    if not request.user.is_superuser:
        return Response(
            {'error': '没有权限'},
            status=status.HTTP_403_FORBIDDEN
        )

    serializer = NotificationCreateSerializer(data=request.data)
    if serializer.is_valid():
        try:
            recipient = User.objects.get(id=serializer.validated_data['recipient_id'])

            notification = Notification.create_notification(
                recipient=recipient,
                notification_type=serializer.validated_data['notification_type'],
                title=serializer.validated_data.get('title'),
                message=serializer.validated_data.get('message'),
                actor=None,  # 管理员创建，无特定actor
                related_object_type=serializer.validated_data.get('related_object_type'),
                related_object_id=serializer.validated_data.get('related_object_id'),
                extra_data=serializer.validated_data.get('extra_data', {}),
                priority=serializer.validated_data.get('priority', 'normal')
            )

            return Response({
                'message': '通知创建成功',
                'notification': NotificationSerializer(notification).data
            }, status=status.HTTP_201_CREATED)

        except User.DoesNotExist:
            return Response(
                {'error': '接收者不存在'},
                status=status.HTTP_404_NOT_FOUND
            )

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
