from rest_framework import serializers
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password, ValidationError as DjangoValidationError
from django.utils import timezone
from .models import User, Friendship, UserLevelUpgrade, Notification


def validate_password_with_detailed_messages(password, user=None):
    """
    自定义密码验证函数，提供详细的错误信息
    """
    errors = []

    try:
        validate_password(password, user=user)
    except DjangoValidationError as e:
        # 分析每个验证器的错误信息并提供更详细的中文说明
        for error in e.messages:
            if 'too short' in error.lower() or '至少' in error or 'minimum' in error.lower():
                errors.append("密码太短：密码至少需要8个字符")
            elif 'too common' in error.lower() or '常见' in error or 'common' in error.lower():
                errors.append("密码太常见：请避免使用常见密码（如123456、password等）")
            elif 'numeric' in error.lower() or '数字' in error or 'entirely numeric' in error.lower():
                errors.append("密码过于简单：密码不能只包含数字，请添加字母或特殊字符")
            elif 'similar' in error.lower() or '相似' in error or 'similarity' in error.lower():
                errors.append("密码与用户信息相似：密码不能与用户名、邮箱等个人信息过于相似")
            else:
                # 保留原始错误信息作为备用
                errors.append(f"密码不符合要求：{error}")

    if errors:
        raise serializers.ValidationError(errors)

    return password


class UserSerializer(serializers.ModelSerializer):
    """用户基础序列化器"""

    active_lock_task = serializers.SerializerMethodField()
    total_lock_duration = serializers.SerializerMethodField()
    task_completion_rate = serializers.SerializerMethodField()
    avatar = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'level', 'activity_score',
            'last_active', 'location_precision', 'coins', 'avatar',
            'bio', 'total_posts', 'total_likes_received',
            'total_tasks_completed', 'total_lock_duration', 'task_completion_rate',
            'created_at', 'updated_at', 'active_lock_task',
            'telegram_username', 'telegram_notifications_enabled', 'show_telegram_account',
            'is_staff', 'is_superuser'
        ]
        read_only_fields = [
            'id', 'level', 'activity_score', 'last_active', 'coins',
            'total_posts', 'total_likes_received', 'total_tasks_completed',
            'total_lock_duration', 'task_completion_rate', 'created_at', 'updated_at', 'active_lock_task',
            'telegram_username', 'telegram_notifications_enabled', 'is_staff', 'is_superuser'
        ]

    def get_active_lock_task(self, obj):
        """获取用户当前活跃的带锁任务"""
        from tasks.models import LockTask

        # 查询所有进行中的带锁任务（包括active和voting状态）
        active_task = LockTask.objects.filter(
            user=obj,
            task_type='lock',
            status__in=['active', 'voting']
        ).first()

        if not active_task:
            return None

        now = timezone.now()
        time_remaining = None
        is_expired = False

        if active_task.end_time:
            # For frozen tasks, calculate time remaining using frozen_end_time and frozen_at
            if active_task.is_frozen and active_task.frozen_end_time and active_task.frozen_at:
                time_remaining_ms = (active_task.frozen_end_time - active_task.frozen_at).total_seconds() * 1000
            else:
                time_remaining_ms = (active_task.end_time - now).total_seconds() * 1000
            time_remaining = max(0, int(time_remaining_ms))
            is_expired = time_remaining <= 0 and not active_task.is_frozen

        return {
            'id': str(active_task.id),
            'title': active_task.title,
            'difficulty': active_task.difficulty,
            'start_time': active_task.start_time.isoformat() if active_task.start_time else None,
            'end_time': active_task.end_time.isoformat() if active_task.end_time else None,
            'time_remaining_ms': time_remaining,
            'is_expired': is_expired,
            'can_complete': is_expired,  # Can only complete after time expires
            'duration_value': active_task.duration_value,
            'duration_type': active_task.duration_type,
            'duration_max': active_task.duration_max,
            'time_display_hidden': active_task.time_display_hidden,  # 时间显示控制状态
            'is_frozen': active_task.is_frozen,  # 冻结状态
            'frozen_at': active_task.frozen_at.isoformat() if active_task.frozen_at else None,  # 冻结时间
            'frozen_end_time': active_task.frozen_end_time.isoformat() if active_task.frozen_end_time else None  # 冻结时保存的结束时间
        }

    def get_total_lock_duration(self, obj):
        """获取用户总带锁时长（分钟）"""
        return obj.get_total_lock_duration()

    def get_task_completion_rate(self, obj):
        """获取用户任务完成率（%）"""
        return obj.get_task_completion_rate()

    def get_avatar(self, obj):
        """获取头像的完整URL"""
        if obj.avatar:
            from utils.media import get_full_media_url
            return get_full_media_url(obj.avatar.url)
        return None


class UserMinimalSerializer(serializers.ModelSerializer):
    """用户最小信息序列化器（用于任务列表等场景，不包含敏感信息）"""

    avatar = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            'id', 'username', 'level', 'avatar'
        ]

    def get_avatar(self, obj):
        """获取头像的完整URL"""
        if obj.avatar:
            from utils.media import get_full_media_url
            return get_full_media_url(obj.avatar.url)
        return None


class UserPublicSerializer(serializers.ModelSerializer):
    """用户公开信息序列化器（用于显示给其他用户）"""

    active_lock_task = serializers.SerializerMethodField()
    total_lock_duration = serializers.SerializerMethodField()
    task_completion_rate = serializers.SerializerMethodField()
    telegram_username = serializers.SerializerMethodField()
    avatar = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            'id', 'username', 'level', 'avatar', 'bio',
            'total_posts', 'total_likes_received', 'total_tasks_completed',
            'created_at', 'coins', 'activity_score', 'last_active', 'updated_at',
            'active_lock_task', 'total_lock_duration', 'task_completion_rate', 'telegram_username'
        ]

    def get_active_lock_task(self, obj):
        """获取用户当前活跃的带锁任务"""
        from tasks.models import LockTask

        # 查询所有进行中的带锁任务（包括active和voting状态）
        active_task = LockTask.objects.filter(
            user=obj,
            task_type='lock',
            status__in=['active', 'voting']
        ).first()

        if not active_task:
            return None

        now = timezone.now()
        time_remaining = None
        is_expired = False

        if active_task.end_time:
            # For frozen tasks, calculate time remaining using frozen_end_time and frozen_at
            if active_task.is_frozen and active_task.frozen_end_time and active_task.frozen_at:
                time_remaining_ms = (active_task.frozen_end_time - active_task.frozen_at).total_seconds() * 1000
            else:
                time_remaining_ms = (active_task.end_time - now).total_seconds() * 1000
            time_remaining = max(0, int(time_remaining_ms))
            is_expired = time_remaining <= 0 and not active_task.is_frozen

        return {
            'id': str(active_task.id),
            'title': active_task.title,
            'difficulty': active_task.difficulty,
            'start_time': active_task.start_time.isoformat() if active_task.start_time else None,
            'end_time': active_task.end_time.isoformat() if active_task.end_time else None,
            'time_remaining_ms': time_remaining,
            'is_expired': is_expired,
            'can_complete': is_expired,  # Can only complete after time expires
            'duration_value': active_task.duration_value,
            'duration_type': active_task.duration_type,
            'duration_max': active_task.duration_max,
            'time_display_hidden': active_task.time_display_hidden,  # 时间显示控制状态
            'is_frozen': active_task.is_frozen,  # 冻结状态
            'frozen_at': active_task.frozen_at.isoformat() if active_task.frozen_at else None,  # 冻结时间
            'frozen_end_time': active_task.frozen_end_time.isoformat() if active_task.frozen_end_time else None  # 冻结时保存的结束时间
        }

    def get_total_lock_duration(self, obj):
        """获取用户总带锁时长（分钟）"""
        return obj.get_total_lock_duration()

    def get_task_completion_rate(self, obj):
        """获取用户任务完成率（%）"""
        return obj.get_task_completion_rate()

    def get_telegram_username(self, obj):
        """只有在用户启用展示账号选项时才返回 Telegram 用户名"""
        if obj.show_telegram_account and obj.telegram_username:
            return obj.telegram_username
        return None

    def get_avatar(self, obj):
        """获取头像的完整URL"""
        if obj.avatar:
            from utils.media import get_full_media_url
            return get_full_media_url(obj.avatar.url)
        return None


class UserRegistrationSerializer(serializers.ModelSerializer):
    """用户注册序列化器"""

    password = serializers.CharField(write_only=True)
    password_confirm = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ['username', 'email', 'password', 'password_confirm']

    def validate_password(self, value):
        """验证密码强度，提供详细的错误信息"""
        # 创建一个临时用户对象用于验证
        temp_user = User(
            username=self.initial_data.get('username', ''),
            email=self.initial_data.get('email', '')
        )
        return validate_password_with_detailed_messages(value, user=temp_user)

    def validate(self, attrs):
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError({"password_confirm": "密码不匹配"})
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
        fields = ['username', 'bio', 'avatar', 'location_precision', 'show_telegram_account']

    def validate_username(self, value):
        """验证用户名是否唯一"""
        if User.objects.filter(username=value).exclude(id=self.instance.id).exists():
            raise serializers.ValidationError("用户名已存在")
        return value

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
    new_password = serializers.CharField(write_only=True)
    new_password_confirm = serializers.CharField(write_only=True)

    def validate_old_password(self, value):
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError("原密码错误")
        return value

    def validate_new_password(self, value):
        """验证新密码强度，提供详细的错误信息"""
        user = self.context['request'].user
        return validate_password_with_detailed_messages(value, user=user)

    def validate(self, attrs):
        if attrs['new_password'] != attrs['new_password_confirm']:
            raise serializers.ValidationError({"new_password_confirm": "新密码不匹配"})
        return attrs

    def save(self):
        user = self.context['request'].user
        user.set_password(self.validated_data['new_password'])
        user.save()
        return user


class NotificationSerializer(serializers.ModelSerializer):
    """通知序列化器"""

    actor = UserPublicSerializer(read_only=True)
    target_url = serializers.ReadOnlyField()
    time_ago = serializers.SerializerMethodField()

    class Meta:
        model = Notification
        fields = [
            'id', 'notification_type', 'title', 'message', 'priority',
            'is_read', 'read_at', 'created_at', 'updated_at',
            'actor', 'target_url', 'related_object_type', 'related_object_id',
            'extra_data', 'time_ago'
        ]
        read_only_fields = [
            'id', 'created_at', 'updated_at', 'target_url', 'time_ago'
        ]

    def get_time_ago(self, obj):
        """获取相对时间显示"""
        from datetime import timedelta
        now = timezone.now()
        diff = now - obj.created_at

        if diff < timedelta(minutes=1):
            return "刚刚"
        elif diff < timedelta(hours=1):
            minutes = int(diff.total_seconds() // 60)
            return f"{minutes}分钟前"
        elif diff < timedelta(days=1):
            hours = int(diff.total_seconds() // 3600)
            return f"{hours}小时前"
        elif diff < timedelta(days=7):
            days = diff.days
            return f"{days}天前"
        else:
            return obj.created_at.strftime("%Y-%m-%d")


class NotificationCreateSerializer(serializers.Serializer):
    """通知创建序列化器（管理员用）"""

    recipient_id = serializers.IntegerField()
    notification_type = serializers.ChoiceField(choices=Notification.TYPE_CHOICES)
    title = serializers.CharField(max_length=200, required=False)
    message = serializers.CharField(max_length=500, required=False)
    priority = serializers.ChoiceField(
        choices=Notification.PRIORITY_CHOICES,
        default='normal'
    )
    related_object_type = serializers.CharField(max_length=50, required=False)
    related_object_id = serializers.CharField(max_length=50, required=False)
    extra_data = serializers.JSONField(default=dict)