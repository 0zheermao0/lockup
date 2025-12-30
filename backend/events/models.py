from django.db import models
from django.conf import settings
from django.utils import timezone
from datetime import timedelta
import uuid


class EventDefinition(models.Model):
    """事件定义 - 管理员配置的事件模板"""

    EVENT_CATEGORY_CHOICES = [
        ('weather', '天气事件'),
        ('magic', '魔法事件'),
        ('system', '系统事件'),
        ('special', '特殊事件'),
    ]

    SCHEDULE_TYPE_CHOICES = [
        ('manual', '手动触发'),
        ('interval_hours', '小时间隔'),
        ('interval_days', '天数间隔'),
        ('cron', '定时触发'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100, unique=True, help_text="事件名称")
    category = models.CharField(max_length=20, choices=EVENT_CATEGORY_CHOICES)
    title = models.CharField(max_length=200, help_text="事件标题")
    description = models.TextField(help_text="事件描述内容")

    # 调度配置
    schedule_type = models.CharField(max_length=20, choices=SCHEDULE_TYPE_CHOICES)
    interval_value = models.IntegerField(null=True, blank=True, help_text="间隔数值")
    cron_expression = models.CharField(max_length=100, null=True, blank=True)

    # 状态控制
    is_active = models.BooleanField(default=True, help_text="是否启用")
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='created_events')

    # 时间戳
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'event_definitions'
        verbose_name = '事件定义'
        verbose_name_plural = '事件定义'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} ({self.get_category_display()})"

    def get_next_scheduled_time(self):
        """获取下次调度时间"""
        if self.schedule_type == 'manual':
            return None

        now = timezone.now()
        if self.schedule_type == 'interval_hours':
            return now + timedelta(hours=self.interval_value or 1)
        elif self.schedule_type == 'interval_days':
            return now + timedelta(days=self.interval_value or 1)

        return None


class EventEffect(models.Model):
    """事件效果配置"""

    EFFECT_TYPE_CHOICES = [
        ('coins_add', '增加积分'),
        ('coins_subtract', '减少积分'),
        ('item_distribute', '分发道具'),
        ('item_remove', '移除道具'),
        ('store_discount', '商店折扣'),
        ('store_price_increase', '商店涨价'),
        ('task_freeze_all', '冻结所有任务'),
        ('task_unfreeze_all', '解冻所有任务'),
        ('task_time_add', '任务加时'),
        ('task_time_subtract', '任务减时'),
        ('overtime_effect_double', '加时效果翻倍'),
        ('game_multiplier', '游戏效果倍增'),
        ('game_reverse_outcome', '游戏结果反转'),
        ('key_holder_operation', '钥匙持有者操作'),
        ('temporary_coins_multiplier', '临时积分倍数'),
        ('temporary_game_enhancement', '临时游戏增强'),
    ]

    TARGET_TYPE_CHOICES = [
        ('all_users', '全体用户'),
        ('random_percentage', '随机百分比'),
        ('level_based', '等级筛选'),
        ('active_task_users', '有活跃任务的用户'),
        ('recent_active_users', '最近活跃用户'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    event_definition = models.ForeignKey(EventDefinition, on_delete=models.CASCADE, related_name='effects')

    effect_type = models.CharField(max_length=30, choices=EFFECT_TYPE_CHOICES)
    target_type = models.CharField(max_length=20, choices=TARGET_TYPE_CHOICES)

    # 效果参数 (JSON存储灵活配置)
    effect_parameters = models.JSONField(default=dict, help_text="效果参数配置")

    # 目标筛选参数
    target_parameters = models.JSONField(default=dict, help_text="目标用户筛选参数")

    # 持续时间 (分钟)
    duration_minutes = models.IntegerField(null=True, blank=True, help_text="效果持续时间")

    # 优先级
    priority = models.IntegerField(default=0, help_text="执行优先级")

    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = 'event_effects'
        verbose_name = '事件效果'
        verbose_name_plural = '事件效果'
        ordering = ['priority', 'id']

    def __str__(self):
        return f"{self.event_definition.name} - {self.get_effect_type_display()}"


class EventOccurrence(models.Model):
    """事件发生记录"""

    STATUS_CHOICES = [
        ('pending', '待执行'),
        ('executing', '执行中'),
        ('completed', '已完成'),
        ('failed', '执行失败'),
        ('cancelled', '已取消'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    event_definition = models.ForeignKey(EventDefinition, on_delete=models.CASCADE, related_name='occurrences')

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')

    # 执行时间
    scheduled_at = models.DateTimeField(help_text="计划执行时间")
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    # 执行结果
    affected_users_count = models.IntegerField(default=0)
    execution_log = models.JSONField(default=list, help_text="执行日志")
    error_message = models.TextField(null=True, blank=True)

    # 触发方式
    triggered_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    trigger_type = models.CharField(max_length=20, default='scheduled')  # scheduled, manual

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'event_occurrences'
        verbose_name = '事件发生记录'
        verbose_name_plural = '事件发生记录'
        ordering = ['-scheduled_at']

    def __str__(self):
        return f"{self.event_definition.name} - {self.scheduled_at.strftime('%Y-%m-%d %H:%M')} ({self.get_status_display()})"

    @property
    def duration_seconds(self):
        """获取执行持续时间（秒）"""
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None


class EventEffectExecution(models.Model):
    """事件效果执行记录"""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    occurrence = models.ForeignKey(EventOccurrence, on_delete=models.CASCADE, related_name='effect_executions')
    effect = models.ForeignKey(EventEffect, on_delete=models.CASCADE)

    target_user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='received_event_effects')

    # 执行详情
    executed_at = models.DateTimeField(auto_now_add=True)
    effect_data = models.JSONField(default=dict, help_text="具体执行的效果数据")

    # 回滚支持
    rollback_data = models.JSONField(default=dict, help_text="回滚所需数据")
    is_rolled_back = models.BooleanField(default=False)
    rolled_back_at = models.DateTimeField(null=True, blank=True)

    # 持续效果支持
    expires_at = models.DateTimeField(null=True, blank=True)
    is_expired = models.BooleanField(default=False)

    class Meta:
        db_table = 'event_effect_executions'
        verbose_name = '事件效果执行记录'
        verbose_name_plural = '事件效果执行记录'
        ordering = ['-executed_at']
        indexes = [
            models.Index(fields=['target_user', '-executed_at']),
            models.Index(fields=['expires_at']),
            models.Index(fields=['occurrence', 'effect']),
        ]

    def __str__(self):
        return f"{self.effect.get_effect_type_display()} -> {self.target_user.username}"

    @property
    def is_active(self):
        """检查效果是否仍然有效"""
        if self.is_expired or self.is_rolled_back:
            return False
        if self.expires_at and timezone.now() > self.expires_at:
            return False
        return True


class UserGameEffect(models.Model):
    """用户游戏效果增强记录 - 支持持续效果"""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='game_effects')

    # 效果类型
    effect_type = models.CharField(max_length=30, default='multiplier', help_text="效果类型")
    multiplier = models.FloatField(default=1.0, help_text="倍数效果")

    # 时间控制
    expires_at = models.DateTimeField(help_text="过期时间")
    is_active = models.BooleanField(default=True)

    # 关联事件执行记录
    event_execution = models.ForeignKey(EventEffectExecution, on_delete=models.CASCADE, null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'user_game_effects'
        verbose_name = '用户游戏效果'
        verbose_name_plural = '用户游戏效果'
        indexes = [
            models.Index(fields=['user', 'is_active', 'expires_at']),
            models.Index(fields=['expires_at']),
        ]

    def __str__(self):
        return f"{self.user.username} - {self.effect_type} x{self.multiplier}"

    @property
    def is_valid(self):
        """检查效果是否有效"""
        return self.is_active and timezone.now() < self.expires_at


class UserCoinsMultiplier(models.Model):
    """用户积分倍数记录 - 支持持续效果"""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='coins_multipliers')

    multiplier = models.FloatField(default=1.0, help_text="积分倍数")

    # 时间控制
    expires_at = models.DateTimeField(help_text="过期时间")
    is_active = models.BooleanField(default=True)

    # 关联事件执行记录
    event_execution = models.ForeignKey(EventEffectExecution, on_delete=models.CASCADE, null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'user_coins_multipliers'
        verbose_name = '用户积分倍数'
        verbose_name_plural = '用户积分倍数'
        indexes = [
            models.Index(fields=['user', 'is_active', 'expires_at']),
            models.Index(fields=['expires_at']),
        ]

    def __str__(self):
        return f"{self.user.username} - 积分 x{self.multiplier}"

    @property
    def is_valid(self):
        """检查倍数是否有效"""
        return self.is_active and timezone.now() < self.expires_at