from django.db import models
from django.conf import settings
import uuid

# Create your models here.

class LockTask(models.Model):
    """带锁任务和任务板的统一模型"""

    TASK_TYPE_CHOICES = [
        ('lock', '带锁任务'),
        ('board', '任务板'),
    ]

    DURATION_TYPE_CHOICES = [
        ('fixed', '固定时间'),
        ('random', '随机时间'),
    ]

    DIFFICULTY_CHOICES = [
        ('easy', '简单'),
        ('normal', '普通'),
        ('hard', '困难'),
        ('hell', '地狱'),
    ]

    UNLOCK_TYPE_CHOICES = [
        ('time', '定时解锁'),
        ('vote', '投票解锁'),
    ]

    STATUS_CHOICES = [
        # 带锁任务状态
        ('pending', '待开始'),
        ('active', '进行中'),
        ('voting', '投票期'),  # 新增：投票解锁任务的投票期状态
        ('completed', '已完成'),
        ('failed', '已失败'),
        # 任务板特有状态
        ('open', '开放中'),
        ('taken', '已接取'),
        ('submitted', '已提交'),  # 等待发布者审核
    ]

    # 基础字段
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='created_tasks')
    task_type = models.CharField(max_length=10, choices=TASK_TYPE_CHOICES)
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True, default='')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')

    # 带锁任务字段
    duration_type = models.CharField(max_length=10, choices=DURATION_TYPE_CHOICES, blank=True, null=True)
    duration_value = models.IntegerField(blank=True, null=True, help_text='持续时间（分钟）')
    duration_max = models.IntegerField(blank=True, null=True, help_text='最大持续时间（分钟）- 仅随机类型')
    difficulty = models.CharField(max_length=10, choices=DIFFICULTY_CHOICES, blank=True, null=True)
    unlock_type = models.CharField(max_length=10, choices=UNLOCK_TYPE_CHOICES, blank=True, null=True)
    vote_threshold = models.IntegerField(blank=True, null=True, help_text='投票门槛')
    vote_agreement_ratio = models.FloatField(blank=True, null=True, help_text='同意比例 (0.0-1.0)')
    overtime_multiplier = models.IntegerField(blank=True, null=True, help_text='加时惩罚倍数')
    overtime_duration = models.IntegerField(blank=True, null=True, help_text='置顶时间（分钟）')

    # 投票期相关字段
    voting_start_time = models.DateTimeField(blank=True, null=True, help_text='投票开始时间')
    voting_end_time = models.DateTimeField(blank=True, null=True, help_text='投票结束时间')
    voting_duration = models.IntegerField(default=10, help_text='投票持续时间（分钟）')
    vote_failed_penalty_minutes = models.IntegerField(blank=True, null=True, help_text='投票失败加时分钟数')

    # 任务板字段
    reward = models.IntegerField(blank=True, null=True, help_text='奖励金额')
    deadline = models.DateTimeField(blank=True, null=True, help_text='截止时间')
    max_duration = models.IntegerField(blank=True, null=True, help_text='最大完成时间（小时）')
    taker = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
                             blank=True, null=True, related_name='taken_tasks')
    taken_at = models.DateTimeField(blank=True, null=True)
    completion_proof = models.TextField(blank=True, null=True, help_text='完成证明')
    completed_at = models.DateTimeField(blank=True, null=True)

    # 时间字段
    start_time = models.DateTimeField(blank=True, null=True)
    end_time = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # 小时奖励字段
    last_hourly_reward_at = models.DateTimeField(blank=True, null=True, help_text='上次获得小时奖励的时间')
    total_hourly_rewards = models.IntegerField(default=0, help_text='总共获得的小时奖励数')

    # 钥匙玩法字段
    time_display_hidden = models.BooleanField(default=False, help_text='是否隐藏时间显示')

    # 多人任务字段
    max_participants = models.IntegerField(blank=True, null=True, help_text='最大参与人数（仅任务板）')

    class Meta:
        ordering = ['-created_at']

    def get_vote_penalty_minutes(self):
        """根据难度等级获取投票失败的加时分钟数"""
        penalty_map = {
            'easy': 10,
            'normal': 20,
            'hard': 30,
            'hell': 60,
        }
        return penalty_map.get(self.difficulty, 20)  # 默认20分钟

    def __str__(self):
        return f"{self.get_task_type_display()}: {self.title}"


class TaskKey(models.Model):
    """任务钥匙"""

    STATUS_CHOICES = [
        ('active', '有效'),
        ('used', '已使用'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    task = models.OneToOneField(LockTask, on_delete=models.CASCADE, related_name='key')
    holder = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='held_keys')
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='active')
    created_at = models.DateTimeField(auto_now_add=True)
    used_at = models.DateTimeField(blank=True, null=True)

    def __str__(self):
        return f"Key for {self.task.title} held by {self.holder.username}"


class TaskVote(models.Model):
    """任务投票"""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    task = models.ForeignKey(LockTask, on_delete=models.CASCADE, related_name='votes')
    voter = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='task_votes')
    agree = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['task', 'voter']

    def __str__(self):
        return f"{self.voter.username} voted {'Yes' if self.agree else 'No'} for {self.task.title}"


class OvertimeAction(models.Model):
    """加时操作记录"""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    task = models.ForeignKey(LockTask, on_delete=models.CASCADE, related_name='overtime_actions')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='overtime_actions')
    task_publisher = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='received_overtime_actions')
    overtime_minutes = models.IntegerField(help_text='加时分钟数')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username} added {self.overtime_minutes} minutes to {self.task.title}"


class TaskTimelineEvent(models.Model):
    """任务时间线事件 - 记录所有时间变化"""

    EVENT_TYPE_CHOICES = [
        ('task_created', '任务创建'),
        ('task_started', '任务开始'),
        ('time_wheel_increase', '时间转盘增加时间'),
        ('time_wheel_decrease', '时间转盘减少时间'),
        ('overtime_added', '他人加时'),
        ('voting_started', '投票期开始'),
        ('voting_ended', '投票期结束'),
        ('vote_passed', '投票通过'),
        ('vote_failed', '投票失败'),
        ('task_voted', '任务投票'),
        ('task_completed', '任务完成'),
        ('task_stopped', '任务停止'),
        ('task_failed', '任务失败'),
        ('deadline_extended', '截止时间延长'),
        ('manual_adjustment', '手动调整'),
        ('hourly_reward', '小时奖励'),
        ('task_keys_destroyed', '任务钥匙销毁'),
        ('user_pinned', '用户被置顶'),
        ('user_unpinned', '用户置顶结束'),
        ('pinning_queue_updated', '置顶队列更新'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    task = models.ForeignKey(LockTask, on_delete=models.CASCADE, related_name='timeline_events')
    event_type = models.CharField(max_length=30, choices=EVENT_TYPE_CHOICES)

    # 事件相关用户（可能为空，如系统事件）
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                           blank=True, null=True, related_name='timeline_events')

    # 时间变化详情
    time_change_minutes = models.IntegerField(blank=True, null=True, help_text='时间变化（分钟）, 正数为增加，负数为减少')
    previous_end_time = models.DateTimeField(blank=True, null=True, help_text='变化前的结束时间')
    new_end_time = models.DateTimeField(blank=True, null=True, help_text='变化后的结束时间')

    # 事件描述和额外数据
    description = models.TextField(blank=True, help_text='事件描述')
    metadata = models.JSONField(default=dict, blank=True, help_text='额外的事件数据')

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['task', '-created_at']),
            models.Index(fields=['event_type', '-created_at']),
        ]

    def __str__(self):
        user_info = f" by {self.user.username}" if self.user else ""
        return f"{self.get_event_type_display()}{user_info} for {self.task.title}"


class HourlyReward(models.Model):
    """带锁任务小时奖励记录"""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    task = models.ForeignKey(LockTask, on_delete=models.CASCADE, related_name='hourly_rewards')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='hourly_rewards')
    reward_amount = models.IntegerField(default=1, help_text='奖励积分数量')
    hour_count = models.IntegerField(help_text='任务运行的小时数')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['task', '-created_at']),
            models.Index(fields=['user', '-created_at']),
        ]

    def __str__(self):
        return f"{self.user.username} received {self.reward_amount} points for hour {self.hour_count} of {self.task.title}"


class TaskSubmissionFile(models.Model):
    """任务提交文件（图片、视频等证明材料）"""

    FILE_TYPE_CHOICES = [
        ('image', '图片'),
        ('video', '视频'),
        ('document', '文档'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    task = models.ForeignKey(LockTask, on_delete=models.CASCADE, related_name='submission_files')
    uploader = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='uploaded_submission_files')
    participant = models.ForeignKey('TaskParticipant', on_delete=models.CASCADE,
                                   blank=True, null=True, related_name='submission_files',
                                   help_text='关联的参与者（多人任务）')

    # 文件信息
    file = models.FileField(upload_to='task_submissions/%Y/%m/%d/', max_length=500)
    file_type = models.CharField(max_length=10, choices=FILE_TYPE_CHOICES, default='image')
    file_name = models.CharField(max_length=255, help_text='原始文件名')
    file_size = models.PositiveIntegerField(help_text='文件大小（字节）')

    # 元数据
    description = models.CharField(max_length=500, blank=True, help_text='文件描述')
    is_primary = models.BooleanField(default=False, help_text='是否为主要证明文件')

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['task', '-created_at']),
            models.Index(fields=['uploader', '-created_at']),
            models.Index(fields=['file_type', '-created_at']),
        ]

    def __str__(self):
        return f"{self.file_name} for {self.task.title} by {self.uploader.username}"

    @property
    def file_url(self):
        """获取文件的完整URL"""
        if self.file:
            return self.file.url
        return None

    @property
    def is_image(self):
        """判断是否为图片文件"""
        return self.file_type == 'image'

    @property
    def is_video(self):
        """判断是否为视频文件"""
        return self.file_type == 'video'

    def get_file_type_from_extension(self, filename):
        """根据文件扩展名判断文件类型"""
        ext = filename.lower().split('.')[-1] if '.' in filename else ''

        if ext in ['jpg', 'jpeg', 'png', 'gif', 'webp', 'bmp']:
            return 'image'
        elif ext in ['mp4', 'avi', 'mov', 'wmv', 'flv', 'webm']:
            return 'video'
        elif ext in ['pdf', 'doc', 'docx', 'txt', 'rtf']:
            return 'document'
        else:
            return 'image'  # 默认为图片

    def save(self, *args, **kwargs):
        # 如果没有设置file_type，根据文件扩展名自动判断
        if not self.file_type and self.file:
            self.file_type = self.get_file_type_from_extension(self.file_name)

        # 如果没有设置file_name，使用原始文件名
        if not self.file_name and self.file:
            self.file_name = self.file.name.split('/')[-1]

        super().save(*args, **kwargs)


class TaskParticipant(models.Model):
    """任务参与者（多人任务支持）"""

    PARTICIPANT_STATUS_CHOICES = [
        ('joined', '已加入'),
        ('submitted', '已提交'),
        ('approved', '已通过'),
        ('rejected', '已拒绝'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    task = models.ForeignKey(LockTask, on_delete=models.CASCADE, related_name='participants')
    participant = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='task_participations')

    # 参与状态
    status = models.CharField(max_length=20, choices=PARTICIPANT_STATUS_CHOICES, default='joined')

    # 提交相关
    submission_text = models.TextField(blank=True, help_text='文字提交内容')
    submitted_at = models.DateTimeField(blank=True, null=True)

    # 审核相关
    reviewed_at = models.DateTimeField(blank=True, null=True)
    review_comment = models.TextField(blank=True, help_text='审核意见')
    reward_amount = models.IntegerField(blank=True, null=True, help_text='分配的奖励金额')

    # 时间字段
    joined_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['task', 'participant']
        ordering = ['joined_at']
        indexes = [
            models.Index(fields=['task', 'status']),
            models.Index(fields=['participant', 'status']),
        ]

    def __str__(self):
        return f"{self.participant.username} - {self.task.title} ({self.get_status_display()})"


class PinnedUser(models.Model):
    """置顶用户记录 - 钥匙持有者置顶惩罚系统"""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    task = models.ForeignKey(LockTask, on_delete=models.CASCADE, related_name='pinned_records',
                            help_text='被置顶的任务（钥匙对应的任务）')
    pinned_user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                                   related_name='pinned_records', help_text='被置顶的用户（任务创建者）')
    key_holder = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                                  related_name='pinning_actions', help_text='执行置顶的钥匙持有者')

    # 置顶详情
    coins_spent = models.IntegerField(default=60, help_text='消费的金币数')
    duration_minutes = models.IntegerField(default=30, help_text='置顶持续时间（分钟）')

    # 状态和位置
    is_active = models.BooleanField(default=True, help_text='是否处于置顶状态')
    position = models.IntegerField(null=True, blank=True,
                                  help_text='置顶位置（1-3，null表示排队中）')

    # 时间追踪
    created_at = models.DateTimeField(auto_now_add=True, help_text='创建时间（排队时间）')
    expires_at = models.DateTimeField(help_text='置顶过期时间')
    activated_at = models.DateTimeField(null=True, blank=True, help_text='开始置顶的时间')

    class Meta:
        ordering = ['created_at']  # 按操作时间排队
        indexes = [
            models.Index(fields=['is_active', 'position']),
            models.Index(fields=['expires_at']),
            models.Index(fields=['created_at']),
            models.Index(fields=['pinned_user', 'is_active']),
        ]

    def __str__(self):
        status = f"位置{self.position}" if self.position else "排队中"
        return f"{self.key_holder.username} 置顶 {self.pinned_user.username} ({status})"

    def save(self, *args, **kwargs):
        # 确保 pinned_user 是 task 的创建者
        if self.pinned_user != self.task.user:
            raise ValueError("被置顶用户必须是任务的创建者")
        super().save(*args, **kwargs)