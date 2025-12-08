from rest_framework import serializers
from .models import LockTask, TaskKey, TaskVote, TaskTimelineEvent
from users.serializers import UserSerializer


class LockTaskSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    taker = UserSerializer(read_only=True)
    key_holder = serializers.SerializerMethodField()
    vote_count = serializers.SerializerMethodField()
    vote_agreement_count = serializers.SerializerMethodField()

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
            'reward', 'deadline', 'max_duration', 'taker', 'taken_at',
            'completion_proof', 'completed_at',
            # 时间字段
            'start_time', 'end_time', 'created_at', 'updated_at',
            # 计算字段
            'key_holder', 'vote_count', 'vote_agreement_count'
        ]
        read_only_fields = ['id', 'user', 'created_at', 'updated_at']

    def get_key_holder(self, obj):
        """获取钥匙持有者"""
        if hasattr(obj, 'key') and obj.key:
            return UserSerializer(obj.key.holder).data
        return None

    def get_vote_count(self, obj):
        """获取总投票数"""
        return obj.votes.count()

    def get_vote_agreement_count(self, obj):
        """获取同意票数"""
        return obj.votes.filter(agree=True).count()


class LockTaskCreateSerializer(serializers.ModelSerializer):
    """创建任务的序列化器"""

    class Meta:
        model = LockTask
        fields = [
            'id', 'task_type', 'title', 'description', 'status',
            # 带锁任务字段
            'duration_type', 'duration_value', 'duration_max', 'difficulty',
            'unlock_type', 'vote_threshold', 'vote_agreement_ratio',
            'overtime_multiplier', 'overtime_duration', 'voting_duration',
            # 任务板字段
            'reward', 'deadline', 'max_duration'
        ]
        read_only_fields = ['id', 'status']

    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user
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

            # 随机时间类型需要最大值
            if data.get('duration_type') == 'random' and not data.get('duration_max'):
                raise serializers.ValidationError("随机时间类型必须设置最大持续时间")

            # 投票解锁需要投票相关参数
            if data.get('unlock_type') == 'vote':
                if not data.get('vote_agreement_ratio'):
                    raise serializers.ValidationError("投票解锁必须设置同意比例")
                if not data.get('voting_duration'):
                    raise serializers.ValidationError("投票解锁必须设置投票持续时间")

        elif task_type == 'board':
            # 任务板必须字段
            required_fields = ['reward', 'max_duration']
            for field in required_fields:
                if not data.get(field):
                    raise serializers.ValidationError(f"任务板必须填写 {field}")

        return data


class TaskKeySerializer(serializers.ModelSerializer):
    task = LockTaskSerializer(read_only=True)
    holder = UserSerializer(read_only=True)

    class Meta:
        model = TaskKey
        fields = ['id', 'task', 'holder', 'status', 'created_at', 'used_at']
        read_only_fields = ['id', 'created_at']


class TaskVoteSerializer(serializers.ModelSerializer):
    voter = UserSerializer(read_only=True)
    task = LockTaskSerializer(read_only=True)

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
    user = UserSerializer(read_only=True)
    event_type_display = serializers.CharField(source='get_event_type_display', read_only=True)

    class Meta:
        model = TaskTimelineEvent
        fields = [
            'id', 'event_type', 'event_type_display', 'user',
            'time_change_minutes', 'previous_end_time', 'new_end_time',
            'description', 'metadata', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']