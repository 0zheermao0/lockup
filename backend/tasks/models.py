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
    description = models.TextField()
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

    class Meta:
        ordering = ['-created_at']

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
        ('task_voted', '任务投票'),
        ('task_completed', '任务完成'),
        ('task_stopped', '任务停止'),
        ('task_failed', '任务失败'),
        ('deadline_extended', '截止时间延长'),
        ('manual_adjustment', '手动调整'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    task = models.ForeignKey(LockTask, on_delete=models.CASCADE, related_name='timeline_events')
    event_type = models.CharField(max_length=20, choices=EVENT_TYPE_CHOICES)

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