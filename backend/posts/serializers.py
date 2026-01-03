import logging
from rest_framework import serializers
from .models import Post, PostImage, PostLike, Comment, CommentImage, CommentLike, CheckinVotingSession, CheckinVote
from users.serializers import UserPublicSerializer

logger = logging.getLogger(__name__)


class PostImageSerializer(serializers.ModelSerializer):
    """动态图片序列化器"""
    image = serializers.SerializerMethodField()

    class Meta:
        model = PostImage
        fields = ['id', 'image', 'order', 'created_at']
        read_only_fields = ['id', 'created_at']

    def get_image(self, obj):
        """获取图片的完整URL"""
        if obj.image:
            from utils.media import get_full_media_url
            return get_full_media_url(obj.image.url)
        return None


class CommentImageSerializer(serializers.ModelSerializer):
    """评论图片序列化器"""
    image = serializers.SerializerMethodField()

    class Meta:
        model = CommentImage
        fields = ['id', 'image', 'order', 'created_at']
        read_only_fields = ['id', 'created_at']

    def get_image(self, obj):
        """获取图片的完整URL"""
        if obj.image:
            from utils.media import get_full_media_url
            return get_full_media_url(obj.image.url)
        return None


class CommentSerializer(serializers.ModelSerializer):
    """评论序列化器 - 支持两层结构"""

    user = UserPublicSerializer(read_only=True)
    images = CommentImageSerializer(many=True, read_only=True)
    reply_to_user = UserPublicSerializer(read_only=True)
    is_liked = serializers.SerializerMethodField()

    class Meta:
        model = Comment
        fields = [
            'id', 'user', 'content', 'parent', 'root_reply_id', 'path',
            'depth', 'reply_to_user', 'likes_count', 'replies_count',
            'images', 'is_liked', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'user', 'root_reply_id', 'path', 'depth', 'reply_to_user',
            'likes_count', 'replies_count', 'created_at', 'updated_at'
        ]

    def get_is_liked(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return CommentLike.objects.filter(
                user=request.user, comment=obj
            ).exists()
        return False


class CheckinVotingSessionSerializer(serializers.ModelSerializer):
    """打卡投票会话序列化器"""

    class Meta:
        model = CheckinVotingSession
        fields = ['voting_deadline', 'total_coins_collected', 'is_processed', 'result']
        read_only_fields = ['voting_deadline', 'total_coins_collected', 'is_processed', 'result']


class PostSerializer(serializers.ModelSerializer):
    """动态序列化器"""

    user = UserPublicSerializer(read_only=True)
    images = PostImageSerializer(many=True, read_only=True)
    user_has_liked = serializers.SerializerMethodField()
    comments = serializers.SerializerMethodField()
    voting_session = CheckinVotingSessionSerializer(read_only=True)
    user_vote = serializers.SerializerMethodField()

    class Meta:
        model = Post
        fields = [
            'id', 'user', 'post_type', 'content', 'latitude', 'longitude',
            'location_name', 'verification_string', 'is_verified',
            'likes_count', 'comments_count', 'images', 'user_has_liked',
            'comments', 'voting_session', 'user_vote', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'user', 'is_verified', 'likes_count', 'comments_count',
            'created_at', 'updated_at'
        ]

    def get_user_has_liked(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return PostLike.objects.filter(
                user=request.user, post=obj
            ).exists()
        return False

    def get_comments(self, obj):
        # 只返回第一层评论（前5条）
        top_comments = obj.comments.filter(depth=0).order_by('created_at')[:5]
        return CommentSerializer(
            top_comments, many=True, context=self.context
        ).data

    def get_user_vote(self, obj):
        """获取当前用户对该打卡动态的投票"""
        request = self.context.get('request')
        if request and request.user.is_authenticated and obj.post_type == 'checkin':
            try:
                vote = CheckinVote.objects.get(post=obj, voter=request.user)
                return vote.vote_type
            except CheckinVote.DoesNotExist:
                pass
        return None


class PostCreateSerializer(serializers.ModelSerializer):
    """动态创建序列化器"""

    images = serializers.ListField(
        child=serializers.ImageField(),
        required=False,
        allow_empty=True,
        max_length=9  # 最多9张图片
    )

    class Meta:
        model = Post
        fields = [
            'post_type', 'content', 'images'
        ]

    def validate_content(self, value):
        if len(value.strip()) < 1:
            raise serializers.ValidationError("动态内容不能为空")
        if len(value) > 2000:
            raise serializers.ValidationError("动态内容不能超过2000字符")
        return value

    def validate(self, attrs):
        post_type = attrs.get('post_type')

        # 如果是打卡任务，生成验证字符串
        if post_type == 'checkin':
            import random
            import string
            verification_string = ''.join(
                random.choices(string.ascii_uppercase + string.digits, k=8)
            )
            attrs['verification_string'] = verification_string

        return attrs

    def create(self, validated_data):
        import logging
        logger = logging.getLogger(__name__)

        images_data = validated_data.pop('images', [])
        user = self.context['request'].user

        try:
            # 创建动态
            post = Post.objects.create(user=user, **validated_data)
            logger.info(f"Post created: {post.id} for user {user.username}")
        except Exception as e:
            logger.error(f"Failed to create post for user {user.username}: {e}")
            raise serializers.ValidationError(f"创建动态失败: {str(e)}")

        # 创建图片 - 添加错误处理
        created_images = []
        try:
            for i, image in enumerate(images_data):
                try:
                    # 验证图片文件
                    from utils.file_upload import validate_uploaded_file
                    validate_uploaded_file(image, 'image')

                    # 创建图片记录
                    post_image = PostImage.objects.create(
                        post=post,
                        image=image,
                        order=i
                    )
                    created_images.append(post_image)
                    logger.info(f"Image {i+1}/{len(images_data)} created for post {post.id}")

                except Exception as e:
                    logger.error(f"Failed to create image {i+1} for post {post.id}: {e}")
                    # 清理已创建的图片
                    for img in created_images:
                        try:
                            img.delete()
                        except:
                            pass
                    # 删除动态
                    post.delete()
                    raise serializers.ValidationError(f"图片 {i+1} 处理失败: {str(e)}")

        except serializers.ValidationError:
            # 重新抛出验证错误
            raise
        except Exception as e:
            logger.error(f"Unexpected error during image processing for post {post.id}: {e}")
            # 清理已创建的图片和动态
            for img in created_images:
                try:
                    img.delete()
                except:
                    pass
            post.delete()
            raise serializers.ValidationError(f"图片处理过程中发生错误: {str(e)}")

        # 为严格模式打卡动态创建投票会话
        if post.post_type == 'checkin':
            # 只为有活跃严格模式带锁任务的用户创建投票会话
            from tasks.models import LockTask
            from django.utils import timezone

            # 检查用户是否有活跃的严格模式任务（移除24小时限制）
            active_strict_tasks = LockTask.objects.filter(
                user=user,
                task_type='lock',
                status__in=['pending', 'active', 'voting'],
                strict_mode=True
                # 移除 start_time__gte=yesterday 限制，只要任务活跃就创建投票会话
            )

            if active_strict_tasks.exists():
                # 记录关联的严格模式任务信息
                task = active_strict_tasks.first()
                self._create_voting_session(post, task)

        # 更新用户统计
        user.total_posts += 1
        user.update_activity(points=2)  # 发布动态 +2 活跃度
        user.save(update_fields=['total_posts', 'activity_score', 'last_active'])

        # 刷新post实例以确保关联关系正确加载
        post.refresh_from_db()
        return post

    def _create_voting_session(self, post, task):
        """为严格模式打卡动态创建投票会话"""
        from datetime import datetime, time
        from django.utils import timezone
        from datetime import timedelta

        # 计算投票截止时间（次日凌晨4点）
        now = timezone.now()
        tomorrow = now.date() + timedelta(days=1)
        deadline = timezone.datetime.combine(tomorrow, time(4, 0))
        deadline = timezone.make_aware(deadline, timezone=timezone.get_current_timezone())

        # 创建投票会话，关联严格模式任务
        session = CheckinVotingSession.objects.create(
            post=post,
            voting_deadline=deadline
        )

        # 在投票会话的元数据中记录关联的严格模式任务
        if hasattr(session, 'metadata'):
            session.metadata = {
                'strict_task_id': str(task.id),
                'strict_task_title': task.title,
                'task_start_time': task.start_time.isoformat() if task.start_time else None
            }
            session.save()


class CommentCreateSerializer(serializers.ModelSerializer):
    """评论创建序列化器"""

    images = serializers.ListField(
        child=serializers.ImageField(),
        required=False,
        allow_empty=True,
        max_length=3  # 最多3张图片
    )
    reply_to_user_id = serializers.IntegerField(
        required=False,
        allow_null=True,
        help_text="被回复的用户ID"
    )

    class Meta:
        model = Comment
        fields = ['content', 'parent', 'images', 'reply_to_user_id']

    def validate_content(self, value):
        if len(value.strip()) < 1:
            raise serializers.ValidationError("评论内容不能为空")
        if len(value) > 500:
            raise serializers.ValidationError("评论内容不能超过500字符")
        return value

    def validate_parent(self, value):
        if value:
            # 检查父评论是否属于同一个动态
            post_id = self.context.get('post_id')
            # 确保类型匹配 - 将post_id转换为字符串进行比较
            if str(value.post.id) != str(post_id):
                raise serializers.ValidationError("父评论不属于当前动态")

            # 在两层结构中，只允许回复第一层评论
            # 如果回复的是第二层评论，会自动转换为回复第一层评论
            if value.depth > 0:
                # 这是第二层评论，需要找到它的根评论
                root_comment = Comment.objects.filter(
                    id=value.root_reply_id,
                    post_id=post_id
                ).first()
                if not root_comment:
                    raise serializers.ValidationError("无法找到根评论")
                # 在create方法中会处理这种情况

        return value

    def create(self, validated_data):
        images_data = validated_data.pop('images', [])
        reply_to_user_id = validated_data.pop('reply_to_user_id', None)
        user = self.context['request'].user
        post_id = self.context['post_id']
        post = Post.objects.get(id=post_id)

        # 如果指定了reply_to_user_id，设置reply_to_user
        reply_to_user = None
        if reply_to_user_id:
            try:
                from django.contrib.auth import get_user_model
                User = get_user_model()
                reply_to_user = User.objects.get(id=reply_to_user_id)
            except User.DoesNotExist:
                pass


        # 创建评论
        comment = Comment.objects.create(
            user=user,
            post=post,
            reply_to_user=reply_to_user,
            **validated_data
        )

        # 创建评论图片 - 添加安全验证和错误处理
        created_images = []
        try:
            for i, image in enumerate(images_data):
                try:
                    # 验证图片文件
                    from utils.file_upload import validate_uploaded_file
                    validate_uploaded_file(image, 'image')

                    # 创建图片记录
                    comment_image = CommentImage.objects.create(
                        comment=comment,
                        image=image,
                        order=i
                    )
                    created_images.append(comment_image)
                    logger.info(f"Comment image {i+1}/{len(images_data)} created for comment {comment.id}")

                except Exception as e:
                    logger.error(f"Failed to create comment image {i+1} for comment {comment.id}: {e}")
                    # 清理已创建的图片
                    for img in created_images:
                        try:
                            img.delete()
                        except:
                            pass
                    # 删除评论
                    comment.delete()
                    raise serializers.ValidationError(f"图片 {i+1} 处理失败: {str(e)}")

        except serializers.ValidationError:
            # 重新抛出验证错误
            raise
        except Exception as e:
            logger.error(f"Unexpected error during comment image processing for comment {comment.id}: {e}")
            # 清理已创建的图片和评论
            for img in created_images:
                try:
                    img.delete()
                except:
                    pass
            comment.delete()
            raise serializers.ValidationError(f"图片处理过程中发生错误: {str(e)}")

        # 更新动态评论数
        post.comments_count += 1
        post.save(update_fields=['comments_count'])

        # 更新用户活跃度
        user.update_activity()

        return comment


class PostLikeSerializer(serializers.ModelSerializer):
    """动态点赞序列化器"""

    class Meta:
        model = PostLike
        fields = ['id', 'created_at']
        read_only_fields = ['id', 'created_at']


class CommentLikeSerializer(serializers.ModelSerializer):
    """评论点赞序列化器"""

    class Meta:
        model = CommentLike
        fields = ['id', 'created_at']
        read_only_fields = ['id', 'created_at']


class PostStatsSerializer(serializers.Serializer):
    """动态统计序列化器"""

    total_posts = serializers.IntegerField()
    posts_today = serializers.IntegerField()
    total_likes = serializers.IntegerField()
    total_comments = serializers.IntegerField()
    checkin_posts = serializers.IntegerField()
    verified_checkins = serializers.IntegerField()


class CheckinVerificationSerializer(serializers.Serializer):
    """打卡验证序列化器"""

    verification_image = serializers.ImageField()

    def validate_verification_image(self, value):
        # 这里可以添加图片验证逻辑
        # 例如：使用OCR检测图片中是否包含验证字符串
        # 暂时返回验证成功
        return value