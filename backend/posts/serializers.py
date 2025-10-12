from rest_framework import serializers
from .models import Post, PostImage, PostLike, Comment, CommentLike
from users.serializers import UserPublicSerializer


class PostImageSerializer(serializers.ModelSerializer):
    """动态图片序列化器"""

    class Meta:
        model = PostImage
        fields = ['id', 'image', 'order', 'created_at']
        read_only_fields = ['id', 'created_at']


class CommentSerializer(serializers.ModelSerializer):
    """评论序列化器"""

    user = UserPublicSerializer(read_only=True)
    replies = serializers.SerializerMethodField()
    is_liked = serializers.SerializerMethodField()

    class Meta:
        model = Comment
        fields = [
            'id', 'user', 'content', 'parent', 'likes_count',
            'replies', 'is_liked', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'user', 'likes_count', 'created_at', 'updated_at']

    def get_replies(self, obj):
        if obj.parent is None:  # 只对顶级评论返回回复
            replies = obj.replies.all()[:5]  # 限制回复数量
            return CommentSerializer(replies, many=True, context=self.context).data
        return []

    def get_is_liked(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return CommentLike.objects.filter(
                user=request.user, comment=obj
            ).exists()
        return False


class PostSerializer(serializers.ModelSerializer):
    """动态序列化器"""

    user = UserPublicSerializer(read_only=True)
    images = PostImageSerializer(many=True, read_only=True)
    user_has_liked = serializers.SerializerMethodField()
    comments = serializers.SerializerMethodField()

    class Meta:
        model = Post
        fields = [
            'id', 'user', 'post_type', 'content', 'latitude', 'longitude',
            'location_name', 'verification_string', 'is_verified',
            'likes_count', 'comments_count', 'images', 'user_has_liked',
            'comments', 'created_at', 'updated_at'
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
        # 只返回顶级评论（前5条）
        top_comments = obj.comments.filter(parent=None)[:5]
        return CommentSerializer(
            top_comments, many=True, context=self.context
        ).data


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
            'post_type', 'content', 'latitude', 'longitude',
            'location_name', 'images'
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
        images_data = validated_data.pop('images', [])
        user = self.context['request'].user

        # 创建动态
        post = Post.objects.create(user=user, **validated_data)

        # 创建图片
        for i, image in enumerate(images_data):
            PostImage.objects.create(
                post=post,
                image=image,
                order=i
            )

        # 更新用户统计
        user.total_posts += 1
        user.update_activity()
        user.save(update_fields=['total_posts', 'activity_score', 'last_active'])

        # 刷新post实例以确保关联关系正确加载
        post.refresh_from_db()
        return post


class CommentCreateSerializer(serializers.ModelSerializer):
    """评论创建序列化器"""

    class Meta:
        model = Comment
        fields = ['content', 'parent']

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
            if value.post.id != post_id:
                raise serializers.ValidationError("父评论不属于当前动态")

            # 不允许多层嵌套回复
            if value.parent is not None:
                raise serializers.ValidationError("不允许多层嵌套回复")

        return value

    def create(self, validated_data):
        user = self.context['request'].user
        post_id = self.context['post_id']
        post = Post.objects.get(id=post_id)

        # 创建评论
        comment = Comment.objects.create(
            user=user,
            post=post,
            **validated_data
        )

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