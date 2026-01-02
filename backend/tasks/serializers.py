from rest_framework import serializers
from .models import LockTask, TaskKey, TaskVote, TaskTimelineEvent, TaskSubmissionFile, TaskParticipant
from users.serializers import UserSerializer, UserMinimalSerializer, UserPublicSerializer
from .utils import calculate_weighted_vote_counts


class TaskSubmissionFileSerializer(serializers.ModelSerializer):
    """任务提交文件序列化器"""
    uploader = UserMinimalSerializer(read_only=True)
    file_url = serializers.ReadOnlyField()
    is_image = serializers.ReadOnlyField()
    is_video = serializers.ReadOnlyField()

    class Meta:
        model = TaskSubmissionFile
        fields = [
            'id', 'task', 'uploader', 'file', 'file_url', 'file_type',
            'file_name', 'file_size', 'description', 'is_primary',
            'is_image', 'is_video', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'uploader', 'created_at', 'updated_at']


class TaskParticipantSerializer(serializers.ModelSerializer):
    """任务参与者序列化器"""
    participant = UserMinimalSerializer(read_only=True)
    submission_files = serializers.SerializerMethodField()

    class Meta:
        model = TaskParticipant
        fields = [
            'id', 'participant', 'status', 'submission_text', 'submitted_at',
            'reviewed_at', 'review_comment', 'reward_amount', 'joined_at',
            'updated_at', 'submission_files'
        ]
        read_only_fields = ['id', 'participant', 'joined_at', 'updated_at']

    def get_submission_files(self, obj):
        """获取参与者的提交文件"""
        # 权限检查：任务发布者和任务参与者可以查看提交文件
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return []

        user = request.user
        task = obj.task

        # 检查是否是任务发布者
        is_publisher = user == task.user

        # 检查是否是任务参与者
        is_participant = task.participants.filter(participant=user).exists()

        # 任务发布者或任务参与者都可以查看提交文件
        if is_publisher or is_participant:
            files = TaskSubmissionFile.objects.filter(participant=obj)
            return TaskSubmissionFileSerializer(files, many=True).data

        return []

    def to_representation(self, instance):
        """自定义序列化输出，根据权限控制敏感字段"""
        data = super().to_representation(instance)

        # 权限检查：任务发布者和任务参与者可以查看敏感信息
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            # 未登录用户，隐藏敏感信息
            data['submission_text'] = None
            data['review_comment'] = None
            data['submission_files'] = []
            return data

        user = request.user
        task = instance.task

        # 检查是否是任务发布者
        is_publisher = user == task.user

        # 检查是否是任务参与者
        is_participant = task.participants.filter(participant=user).exists()

        # 如果不是任务发布者也不是任务参与者，隐藏敏感信息
        if not is_publisher and not is_participant:
            data['submission_text'] = None
            data['review_comment'] = None
            data['submission_files'] = []

        return data


class LockTaskListSerializer(serializers.ModelSerializer):
    """任务列表序列化器（精简版，用于列表显示，不包含敏感用户信息）"""
    user = UserMinimalSerializer(read_only=True)
    taker = UserMinimalSerializer(read_only=True)
    vote_count = serializers.SerializerMethodField()
    vote_agreement_count = serializers.SerializerMethodField()
    participant_count = serializers.SerializerMethodField()
    submitted_count = serializers.SerializerMethodField()
    approved_count = serializers.SerializerMethodField()
    can_take = serializers.SerializerMethodField()

    class Meta:
        model = LockTask
        fields = [
            'id', 'user', 'task_type', 'title', 'description', 'status',
            # 带锁任务字段
            'duration_type', 'duration_value', 'duration_max', 'difficulty',
            'unlock_type', 'vote_threshold', 'vote_agreement_ratio',
            # 投票期相关字段
            'voting_start_time', 'voting_end_time', 'voting_duration',
            # 严格模式字段
            'strict_mode', 'strict_code',
            # 任务板字段
            'reward', 'deadline', 'max_duration', 'completion_rate_threshold', 'taker', 'taken_at',
            'completed_at',
            # 多人任务字段
            'max_participants',
            # 时间字段
            'start_time', 'end_time', 'created_at',
            # 钥匙玩法字段
            'time_display_hidden',
            # 冻结/解冻字段
            'is_frozen', 'frozen_at', 'frozen_end_time',
            # 计算字段
            'vote_count', 'vote_agreement_count',
            'participant_count', 'submitted_count', 'approved_count', 'can_take'
        ]
        read_only_fields = ['id', 'user', 'created_at']

    def get_vote_count(self, obj):
        """获取总投票数（包含影响力王冠权重）"""
        vote_counts = calculate_weighted_vote_counts(obj)
        return vote_counts['total_votes']

    def get_vote_agreement_count(self, obj):
        """获取同意票数（包含影响力王冠权重）"""
        vote_counts = calculate_weighted_vote_counts(obj)
        return vote_counts['agree_votes']

    def get_participant_count(self, obj):
        """获取参与者数量"""
        return obj.participants.count()

    def get_submitted_count(self, obj):
        """获取已提交参与者数量"""
        return obj.participants.filter(status='submitted').count()

    def get_approved_count(self, obj):
        """获取已通过审核的参与者数量"""
        return obj.participants.filter(status='approved').count()

    def get_can_take(self, obj):
        """判断当前用户是否可以接取任务"""
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return False

        user = request.user

        # 不能接取自己的任务
        if obj.user == user:
            return False

        # 检查是否已经参与过
        if obj.participants.filter(participant=user).exists():
            return False

        # 检查完成率门槛（仅适用于任务板）
        if obj.task_type == 'board' and obj.completion_rate_threshold is not None and obj.completion_rate_threshold > 0:
            user_completion_rate = user.get_task_completion_rate()
            if user_completion_rate < obj.completion_rate_threshold:
                return False

        # 判断是单人还是多人任务
        is_multi_person = obj.max_participants and obj.max_participants > 1

        if is_multi_person:
            # 多人任务：检查状态和人数限制
            if obj.status not in ['open', 'taken', 'submitted']:
                return False

            # 检查是否已满员
            current_participants = obj.participants.count()
            return current_participants < obj.max_participants
        else:
            # 单人任务：只能是开放状态
            return obj.status == 'open'


class LockTaskSerializer(serializers.ModelSerializer):
    """任务详情序列化器（完整版，用于详情显示）"""
    user = UserPublicSerializer(read_only=True)
    taker = UserPublicSerializer(read_only=True)
    shield_activated_by = UserPublicSerializer(read_only=True)
    key_holder = serializers.SerializerMethodField()
    vote_count = serializers.SerializerMethodField()
    vote_agreement_count = serializers.SerializerMethodField()
    submission_files = TaskSubmissionFileSerializer(many=True, read_only=True)
    participants = TaskParticipantSerializer(many=True, read_only=True)
    participant_count = serializers.SerializerMethodField()
    submitted_count = serializers.SerializerMethodField()
    approved_count = serializers.SerializerMethodField()
    can_take = serializers.SerializerMethodField()

    class Meta:
        model = LockTask
        fields = [
            'id', 'user', 'task_type', 'title', 'description', 'status',
            # 带锁任务字段
            'duration_type', 'duration_value', 'duration_max', 'difficulty',
            'unlock_type', 'vote_threshold', 'vote_agreement_ratio',
            'overtime_multiplier', 'overtime_duration',
            # 投票期相关字段
            'voting_start_time', 'voting_end_time', 'voting_duration', 'vote_failed_penalty_minutes',
            # 任务板字段
            'reward', 'deadline', 'max_duration', 'completion_rate_threshold', 'taker', 'taken_at',
            'completion_proof', 'completed_at',
            # 多人任务字段
            'max_participants',
            # 严格模式字段
            'strict_mode', 'strict_code',
            # 时间字段
            'start_time', 'end_time', 'created_at', 'updated_at',
            # 钥匙玩法字段
            'time_display_hidden',
            # 冻结/解冻字段
            'is_frozen', 'frozen_at', 'frozen_end_time', 'total_frozen_duration',
            # 防护罩字段
            'shield_active', 'shield_activated_at', 'shield_activated_by',
            # 计算字段
            'key_holder', 'vote_count', 'vote_agreement_count', 'submission_files',
            'participants', 'participant_count', 'submitted_count', 'approved_count', 'can_take'
        ]
        read_only_fields = ['id', 'user', 'created_at', 'updated_at']

    def get_key_holder(self, obj):
        """获取钥匙持有者"""
        if hasattr(obj, 'key') and obj.key:
            return UserPublicSerializer(obj.key.holder).data
        return None

    def get_vote_count(self, obj):
        """获取总投票数（包含影响力王冠权重）"""
        vote_counts = calculate_weighted_vote_counts(obj)
        return vote_counts['total_votes']

    def get_vote_agreement_count(self, obj):
        """获取同意票数（包含影响力王冠权重）"""
        vote_counts = calculate_weighted_vote_counts(obj)
        return vote_counts['agree_votes']

    def get_participant_count(self, obj):
        """获取参与者数量"""
        return obj.participants.count()

    def get_submitted_count(self, obj):
        """获取已提交参与者数量"""
        return obj.participants.filter(status='submitted').count()

    def get_approved_count(self, obj):
        """获取已通过审核的参与者数量"""
        return obj.participants.filter(status='approved').count()

    def get_can_take(self, obj):
        """判断当前用户是否可以接取任务"""
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return False

        user = request.user

        # 不能接取自己的任务
        if obj.user == user:
            return False

        # 检查是否已经参与过
        if obj.participants.filter(participant=user).exists():
            return False

        # 检查完成率门槛（仅适用于任务板）
        if obj.task_type == 'board' and obj.completion_rate_threshold is not None and obj.completion_rate_threshold > 0:
            user_completion_rate = user.get_task_completion_rate()
            if user_completion_rate < obj.completion_rate_threshold:
                return False

        # 判断是单人还是多人任务
        is_multi_person = obj.max_participants and obj.max_participants > 1

        if is_multi_person:
            # 多人任务：检查状态和人数限制
            if obj.status not in ['open', 'taken', 'submitted']:
                return False

            # 检查是否已满员
            current_participants = obj.participants.count()
            return current_participants < obj.max_participants
        else:
            # 单人任务：只能是开放状态
            return obj.status == 'open'

    def to_representation(self, instance):
        """自定义序列化输出，根据权限控制敏感字段"""
        data = super().to_representation(instance)

        # 只对任务板类型进行权限控制
        if instance.task_type != 'board':
            return data

        # 权限检查：只有任务发布者和参与者可以查看敏感信息
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            # 未登录用户，隐藏敏感信息
            data['completion_proof'] = None
            data['submission_files'] = []
            return data

        user = request.user

        # 检查是否是任务发布者或参与者
        is_publisher = user == instance.user
        is_participant = instance.participants.filter(participant=user).exists()

        if not is_publisher and not is_participant:
            # 既不是发布者也不是参与者，隐藏敏感信息
            data['completion_proof'] = None
            data['submission_files'] = []

        return data


class LockTaskCreateSerializer(serializers.ModelSerializer):
    """创建任务的序列化器"""

    description = serializers.CharField(required=False, allow_blank=True, default='')
    auto_publish = serializers.BooleanField(default=False, write_only=True)

    class Meta:
        model = LockTask
        fields = [
            'id', 'task_type', 'title', 'description', 'status',
            # 带锁任务字段
            'duration_type', 'duration_value', 'duration_max', 'difficulty',
            'unlock_type', 'vote_threshold', 'vote_agreement_ratio',
            'overtime_multiplier', 'overtime_duration', 'voting_duration',
            # 严格模式字段
            'strict_mode', 'strict_code',
            # 任务板字段
            'reward', 'deadline', 'max_duration', 'completion_rate_threshold',
            # 多人任务字段
            'max_participants',
            # 自动发布动态字段
            'auto_publish'
        ]
        read_only_fields = ['id', 'status', 'strict_code']

    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user

        # 提取auto_publish字段，不保存到数据库
        auto_publish = validated_data.pop('auto_publish', False)

        # 处理 max_participants 字段：如果为空或None，设置为1（单人任务）
        if validated_data.get('task_type') == 'board':
            max_participants = validated_data.get('max_participants')
            if max_participants is None or max_participants == 0:
                validated_data['max_participants'] = 1

        # 将auto_publish存储在上下文中，供视图使用
        self.context['auto_publish'] = auto_publish

        return super().create(validated_data)

    def validate(self, data):
        """验证数据的一致性"""
        task_type = data.get('task_type')

        if task_type == 'lock':
            # 检查用户是否已有活跃的带锁任务
            user = self.context['request'].user
            existing_active_lock_tasks = LockTask.objects.filter(
                user=user,
                task_type='lock',
                status='active'
            )

            if existing_active_lock_tasks.exists():
                raise serializers.ValidationError("您已经有一个正在进行的带锁任务，一次只能进行一个带锁任务")

            # 带锁任务必须字段
            required_fields = ['duration_type', 'duration_value', 'difficulty', 'unlock_type']
            for field in required_fields:
                if not data.get(field):
                    raise serializers.ValidationError(f"带锁任务必须填写 {field}")

            # 验证持续时间基本要求（移除上限，允许无限制）
            duration_value = data.get('duration_value')
            duration_max = data.get('duration_max')

            if duration_value and duration_value < 1:
                raise serializers.ValidationError("持续时间至少为1分钟")

            # 随机时间类型需要最大值
            if data.get('duration_type') == 'random':
                if not duration_max:
                    raise serializers.ValidationError("随机时间类型必须设置最大持续时间")

                if duration_value and duration_max <= duration_value:
                    raise serializers.ValidationError("最大持续时间必须大于最短持续时间")

            # 投票解锁需要投票相关参数
            if data.get('unlock_type') == 'vote':
                if not data.get('vote_agreement_ratio'):
                    raise serializers.ValidationError("投票解锁必须设置同意比例")
                # voting_duration 有默认值10分钟，不需要强制设置

        elif task_type == 'board':
            # 任务板必须字段
            required_fields = ['reward', 'max_duration']
            for field in required_fields:
                if not data.get(field):
                    raise serializers.ValidationError(f"任务板必须填写 {field}")

            # 验证任务板基本要求（移除时间上限，允许无限制）
            max_duration = data.get('max_duration')
            reward = data.get('reward')

            if max_duration and max_duration < 1:
                raise serializers.ValidationError("最大完成时间至少为1小时")

            # 奖励金额限制保持合理范围
            if reward and reward > 10000:
                raise serializers.ValidationError("奖励金额不能超过10000积分")

            if reward and reward < 1:
                raise serializers.ValidationError("奖励金额至少为1积分")

            # 验证完成率门槛
            completion_rate_threshold = data.get('completion_rate_threshold')
            if completion_rate_threshold is not None:
                if not (0 <= completion_rate_threshold <= 100):
                    raise serializers.ValidationError("完成率门槛必须在0%到100%之间")

        elif data.get('completion_rate_threshold') is not None:
            # 不允许带锁任务设置完成率门槛
            raise serializers.ValidationError("完成率门槛仅适用于任务板")

        return data


class TaskKeySerializer(serializers.ModelSerializer):
    task = LockTaskListSerializer(read_only=True)
    holder = UserMinimalSerializer(read_only=True)

    class Meta:
        model = TaskKey
        fields = ['id', 'task', 'holder', 'status', 'created_at', 'used_at']
        read_only_fields = ['id', 'created_at']


class TaskVoteSerializer(serializers.ModelSerializer):
    voter = UserMinimalSerializer(read_only=True)
    task = LockTaskListSerializer(read_only=True)

    class Meta:
        model = TaskVote
        fields = ['id', 'task', 'voter', 'agree', 'created_at']
        read_only_fields = ['id', 'voter', 'task', 'created_at']


class TaskVoteCreateSerializer(serializers.ModelSerializer):
    """投票创建序列化器"""

    class Meta:
        model = TaskVote
        fields = ['agree']

    def create(self, validated_data):
        validated_data['voter'] = self.context['request'].user
        validated_data['task'] = self.context['task']
        return super().create(validated_data)


class TaskTimelineEventSerializer(serializers.ModelSerializer):
    """任务时间线事件序列化器"""
    user = UserMinimalSerializer(read_only=True)
    event_type_display = serializers.CharField(source='get_event_type_display', read_only=True)

    class Meta:
        model = TaskTimelineEvent
        fields = [
            'id', 'event_type', 'event_type_display', 'user',
            'time_change_minutes', 'previous_end_time', 'new_end_time',
            'description', 'metadata', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']