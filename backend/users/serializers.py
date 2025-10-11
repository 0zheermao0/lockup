from rest_framework import serializers
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from .models import User, Friendship, UserLevelUpgrade


class UserSerializer(serializers.ModelSerializer):
    """用户基础序列化器"""

    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'level', 'activity_score',
            'last_active', 'location_precision', 'coins', 'avatar',
            'bio', 'total_posts', 'total_likes_received',
            'total_tasks_completed', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'level', 'activity_score', 'last_active', 'coins',
            'total_posts', 'total_likes_received', 'total_tasks_completed',
            'created_at', 'updated_at'
        ]


class UserPublicSerializer(serializers.ModelSerializer):
    """用户公开信息序列化器（用于显示给其他用户）"""

    class Meta:
        model = User
        fields = [
            'id', 'username', 'level', 'avatar', 'bio',
            'total_posts', 'total_likes_received', 'total_tasks_completed',
            'created_at'
        ]


class UserRegistrationSerializer(serializers.ModelSerializer):
    """用户注册序列化器"""

    password = serializers.CharField(write_only=True, validators=[validate_password])
    password_confirm = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ['username', 'email', 'password', 'password_confirm']

    def validate(self, attrs):
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError("密码不匹配")
        return attrs

    def create(self, validated_data):
        validated_data.pop('password_confirm')
        user = User.objects.create_user(**validated_data)
        return user


class UserLoginSerializer(serializers.Serializer):
    """用户登录序列化器"""

    username = serializers.CharField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        username = attrs.get('username')
        password = attrs.get('password')

        if username and password:
            user = authenticate(username=username, password=password)
            if not user:
                raise serializers.ValidationError('用户名或密码错误')
            if not user.is_active:
                raise serializers.ValidationError('账户已被禁用')
            attrs['user'] = user
        else:
            raise serializers.ValidationError('必须提供用户名和密码')

        return attrs


class UserProfileUpdateSerializer(serializers.ModelSerializer):
    """用户资料更新序列化器"""

    class Meta:
        model = User
        fields = ['bio', 'avatar', 'location_precision']

    def update(self, instance, validated_data):
        # 更新用户活跃度
        instance.update_activity()
        return super().update(instance, validated_data)


class FriendshipSerializer(serializers.ModelSerializer):
    """好友关系序列化器"""

    from_user = UserPublicSerializer(read_only=True)
    to_user = UserPublicSerializer(read_only=True)

    class Meta:
        model = Friendship
        fields = ['id', 'from_user', 'to_user', 'status', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']


class FriendRequestSerializer(serializers.Serializer):
    """好友请求序列化器"""

    to_user_id = serializers.IntegerField()

    def validate_to_user_id(self, value):
        try:
            user = User.objects.get(id=value)
        except User.DoesNotExist:
            raise serializers.ValidationError("用户不存在")
        return value

    def create(self, validated_data):
        from_user = self.context['request'].user
        to_user_id = validated_data['to_user_id']
        to_user = User.objects.get(id=to_user_id)

        # 检查是否已经存在好友关系
        existing = Friendship.objects.filter(
            from_user=from_user, to_user=to_user
        ).first()

        if existing:
            if existing.status == 'pending':
                raise serializers.ValidationError("好友请求已发送")
            elif existing.status == 'accepted':
                raise serializers.ValidationError("已经是好友关系")
            elif existing.status == 'blocked':
                raise serializers.ValidationError("无法发送好友请求")

        # 创建好友请求
        friendship = Friendship.objects.create(
            from_user=from_user,
            to_user=to_user,
            status='pending'
        )
        return friendship


class UserLevelUpgradeSerializer(serializers.ModelSerializer):
    """用户等级晋升记录序列化器"""

    user = UserPublicSerializer(read_only=True)
    promoted_by = UserPublicSerializer(read_only=True)

    class Meta:
        model = UserLevelUpgrade
        fields = [
            'id', 'user', 'promoted_by', 'from_level', 'to_level',
            'reason', 'created_at'
        ]


class UserStatsSerializer(serializers.Serializer):
    """用户统计信息序列化器"""

    total_users = serializers.IntegerField()
    level_distribution = serializers.DictField()
    active_users_today = serializers.IntegerField()
    new_users_this_week = serializers.IntegerField()
    top_active_users = UserPublicSerializer(many=True)


class PasswordChangeSerializer(serializers.Serializer):
    """密码修改序列化器"""

    old_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(
        write_only=True,
        validators=[validate_password]
    )
    new_password_confirm = serializers.CharField(write_only=True)

    def validate_old_password(self, value):
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError("原密码错误")
        return value

    def validate(self, attrs):
        if attrs['new_password'] != attrs['new_password_confirm']:
            raise serializers.ValidationError("新密码不匹配")
        return attrs

    def save(self):
        user = self.context['request'].user
        user.set_password(self.validated_data['new_password'])
        user.save()
        return user