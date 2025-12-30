from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from datetime import timedelta
import uuid
from utils.file_upload import secure_avatar_upload_to


class User(AbstractUser):
    """自定义用户模型，扩展Django默认用户"""

    # 用户等级相关
    level = models.IntegerField(
        default=1,
        validators=[MinValueValidator(1), MaxValueValidator(4)],
        help_text="用户等级 1-4"
    )
    activity_score = models.IntegerField(
        default=0,
        help_text="活跃度积分"
    )
    last_active = models.DateTimeField(
        default=timezone.now,
        help_text="最后活跃时间"
    )

    # 地理位置设置
    location_precision = models.IntegerField(
        default=100,
        help_text="地理位置精确度（米）"
    )

    # 虚拟货币
    coins = models.IntegerField(
        default=0,
        help_text="金币数量"
    )

    # 个人资料
    avatar = models.ImageField(
        upload_to=secure_avatar_upload_to,
        blank=True,
        null=True,
        help_text="用户头像"
    )
    bio = models.TextField(
        max_length=500,
        blank=True,
        help_text="个人简介"
    )

    # Telegram Bot 绑定
    telegram_user_id = models.BigIntegerField(
        null=True,
        blank=True,
        unique=True,
        help_text="Telegram 用户ID"
    )
    telegram_username = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        help_text="Telegram 用户名"
    )
    telegram_chat_id = models.BigIntegerField(
        null=True,
        blank=True,
        help_text="Telegram 聊天ID"
    )
    telegram_bound_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Telegram 绑定时间"
    )
    telegram_notifications_enabled = models.BooleanField(
        default=True,
        help_text="是否启用 Telegram 通知"
    )
    show_telegram_account = models.BooleanField(
        default=False,
        help_text="是否在个人资料中展示 Telegram 账号"
    )
    telegram_binding_token = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        help_text="临时绑定令牌，用于自动绑定流程"
    )

    # 统计信息
    total_posts = models.IntegerField(default=0, help_text="发布动态总数")
    total_likes_received = models.IntegerField(default=0, help_text="收到点赞总数")
    total_tasks_completed = models.IntegerField(default=0, help_text="完成任务总数")

    # 活跃度衰减处理
    last_decay_processed = models.DateTimeField(
        null=True,
        blank=True,
        help_text="最后一次处理衰减的时间"
    )

    # 时间戳
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'users'
        verbose_name = '用户'
        verbose_name_plural = '用户'

    def __str__(self):
        return f"{self.username} (Level {self.level})"

    def can_upgrade_to_level_2(self):
        """Check if user can upgrade from level 1 to 2"""
        if self.level != 1:
            return False

        # New criteria: Activity ≥100 + Posts ≥5 + Likes ≥10 + Lock Duration ≥24h
        lock_duration_hours = self.get_total_lock_duration() / 60  # Convert minutes to hours

        return (
            self.activity_score >= 100 and
            self.total_posts >= 5 and
            self.total_likes_received >= 10 and
            lock_duration_hours >= 24
        )

    def can_upgrade_to_level_3(self):
        """Check if user can upgrade from level 2 to 3"""
        if self.level != 2:
            return False

        # New criteria: Activity ≥200 + Posts ≥20 + Likes ≥50 + Lock Duration ≥7 days
        lock_duration_hours = self.get_total_lock_duration() / 60
        lock_duration_days = lock_duration_hours / 24

        return (
            self.activity_score >= 200 and
            self.total_posts >= 20 and
            self.total_likes_received >= 50 and
            lock_duration_days >= 7
        )

    def can_upgrade_to_level_4(self):
        """Check if user can upgrade from level 3 to 4"""
        if self.level != 3:
            return False

        # New criteria: Activity ≥500 + Posts ≥50 + Likes ≥1000 + Lock Duration ≥30 days + Task Completion Rate ≥90%
        lock_duration_hours = self.get_total_lock_duration() / 60
        lock_duration_days = lock_duration_hours / 24
        task_completion_rate = self.get_task_completion_rate()

        return (
            self.activity_score >= 500 and
            self.total_posts >= 50 and
            self.total_likes_received >= 1000 and
            lock_duration_days >= 30 and
            task_completion_rate >= 90.0
        )

    def check_level_promotion_eligibility(self):
        """Check which level user is eligible for promotion to"""
        if self.level == 1 and self.can_upgrade_to_level_2():
            return 2
        elif self.level == 2 and self.can_upgrade_to_level_3():
            return 3
        elif self.level == 3 and self.can_upgrade_to_level_4():
            return 4
        return None

    def get_level_promotion_requirements(self, target_level):
        """Get requirements for specific level promotion"""
        requirements = {
            2: {
                'activity_score': 100,
                'total_posts': 5,
                'total_likes_received': 10,
                'lock_duration_hours': 24
            },
            3: {
                'activity_score': 200,
                'total_posts': 20,
                'total_likes_received': 50,
                'lock_duration_hours': 7 * 24  # 7 days
            },
            4: {
                'activity_score': 500,
                'total_posts': 50,
                'total_likes_received': 1000,
                'lock_duration_hours': 30 * 24,  # 30 days
                'task_completion_rate': 90.0
            }
        }
        return requirements.get(target_level, {})

    def promote_to_level(self, new_level, reason='automatic'):
        """Promote user to new level with proper tracking"""

        old_level = self.level
        self.level = new_level
        self.save(update_fields=['level'])

        # Record level upgrade
        UserLevelUpgrade.objects.create(
            user=self,
            from_level=old_level,
            to_level=new_level,
            reason=reason if reason in ['activity', 'manual', 'downgrade'] else 'activity',  # Map 'automatic' to 'activity'
            promoted_by=None  # System promotion
        )

        # Create notification
        Notification.create_notification(
            recipient=self,
            notification_type='level_upgraded',
            title=f'恭喜升级到等级 {new_level}！',
            message=f'您已成功从等级 {old_level} 升级到等级 {new_level}！',
            actor=None,  # System notification
            extra_data={'old_level': old_level, 'new_level': new_level},
            priority='normal'
        )

        return True

    def update_activity(self, points=1):
        """更新用户活跃度 - 支持可变积分"""
        self.last_active = timezone.now()
        self.activity_score += points
        self.save(update_fields=['activity_score', 'last_active'])

        # 创建活动日志
        try:
            ActivityLog.objects.create(
                user=self,
                action_type='activity_gain',
                points_change=points,
                new_total=self.activity_score
            )
        except Exception:
            # 如果ActivityLog模型还不存在，忽略错误（迁移期间）
            pass

    def calculate_fibonacci_decay(self):
        """计算斐波那契衰减值"""
        if not self.last_active:
            return 0

        days_inactive = (timezone.now().date() - self.last_active.date()).days
        if days_inactive <= 0:
            return 0

        # 斐波那契数列计算
        fib_sequence = [1, 1]
        total_decay = 0

        for day in range(1, min(days_inactive + 1, 30)):  # 限制最大30天
            if day <= 2:
                total_decay += fib_sequence[day - 1]
            else:
                next_fib = fib_sequence[-1] + fib_sequence[-2]
                fib_sequence.append(next_fib)
                total_decay += next_fib

        return total_decay

    def apply_time_decay(self):
        """应用时间衰减"""
        decay_amount = self.calculate_fibonacci_decay()
        if decay_amount > 0:
            old_score = self.activity_score
            self.activity_score = max(0, self.activity_score - decay_amount)
            self.last_decay_processed = timezone.now()
            self.save(update_fields=['activity_score', 'last_decay_processed'])

            # 记录衰减日志
            if old_score != self.activity_score:
                try:
                    ActivityLog.objects.create(
                        user=self,
                        action_type='time_decay',
                        points_change=-(old_score - self.activity_score),
                        new_total=self.activity_score,
                        metadata={'days_inactive': (timezone.now().date() - self.last_active.date()).days}
                    )
                except Exception:
                    # 如果ActivityLog模型还不存在，忽略错误（迁移期间）
                    pass

    def get_daily_login_reward(self):
        """根据用户等级获取每日登录奖励积分"""
        return self.level  # 1/2/3/4级用户分别获得1/2/3/4积分

    def get_total_lock_duration(self):
        """获取用户总带锁时长（分钟），使用实际经历的时长（解锁时间-开始时间）"""
        from tasks.models import LockTask

        total_duration = 0

        # 获取用户的所有带锁任务
        user_lock_tasks = LockTask.objects.filter(
            user=self,
            task_type='lock'
        )

        for task in user_lock_tasks:
            # 只计算已完成任务的实际时长
            if task.status == 'completed' and task.start_time:
                # 使用实际完成时间作为结束时间，而不是配置的end_time
                actual_end_time = task.completed_at or task.end_time
                if actual_end_time:
                    actual_duration = int((actual_end_time - task.start_time).total_seconds() / 60)
                    total_duration += max(0, actual_duration)
            elif task.status == 'active' and task.start_time:
                # 进行中的任务，计算从开始到现在的实际时长
                actual_duration = int((timezone.now() - task.start_time).total_seconds() / 60)
                total_duration += max(0, actual_duration)

        return total_duration

    def get_task_completion_rate(self):
        """计算任务完成率：(已完成带锁任务+参与他人任务板的通过数) / (已完成+失败带锁任务+参与他人任务板的完成数)"""
        from tasks.models import LockTask, TaskParticipant

        # 1. 计算用户创建的已完成带锁任务数
        completed_lock_tasks = LockTask.objects.filter(
            user=self,
            task_type='lock',
            status='completed'
        ).count()

        # 2. 计算用户参与他人任务板任务中已通过审核的数量
        approved_participations = TaskParticipant.objects.filter(
            participant=self,
            status='approved'
        ).count()

        # 3. 计算分母：参与带锁任务和他人任务板的已完成+失败数
        # 用户创建的已完成+失败的带锁任务数
        finished_lock_tasks = LockTask.objects.filter(
            user=self,
            task_type='lock',
            status__in=['completed', 'failed']
        ).count()

        # 用户参与他人任务板任务中已完成的数量（通过审核和被拒绝的）
        finished_participations = TaskParticipant.objects.filter(
            participant=self,
            status__in=['approved', 'rejected']
        ).count()

        total_finished_tasks = finished_lock_tasks + finished_participations

        # 4. 计算完成率
        if total_finished_tasks == 0:
            return 0.0  # 没有已完成或失败的任务，完成率为0%

        completed_tasks = completed_lock_tasks + approved_participations
        completion_rate = (completed_tasks / total_finished_tasks) * 100

        return round(completion_rate, 1)  # 保留一位小数

    def bind_telegram(self, telegram_user_id, telegram_username=None, telegram_chat_id=None):
        """绑定 Telegram 账户"""
        self.telegram_user_id = telegram_user_id
        self.telegram_username = telegram_username
        self.telegram_chat_id = telegram_chat_id
        self.telegram_bound_at = timezone.now()
        self.save()

    def unbind_telegram(self):
        """解绑 Telegram 账户"""
        self.telegram_user_id = None
        self.telegram_username = None
        self.telegram_chat_id = None
        self.telegram_bound_at = None
        self.telegram_notifications_enabled = True  # 重置为默认值
        self.save()

    def is_telegram_bound(self):
        """检查是否已绑定 Telegram"""
        return (self.telegram_user_id is not None and
                self.telegram_chat_id is not None)

    def can_receive_telegram_notifications(self):
        """检查是否可以接收 Telegram 通知"""
        return (self.is_telegram_bound() and
                self.telegram_notifications_enabled and
                self.telegram_chat_id is not None)

    def save(self, *args, **kwargs):
        """保存时验证头像文件"""
        # 如果是路径修复，跳过验证
        skip_validation = kwargs.pop('skip_file_validation', False)

        if self.avatar and not skip_validation:
            from utils.file_upload import validate_file_security
            try:
                validate_file_security(self.avatar)
            except Exception as e:
                from django.core.exceptions import ValidationError
                raise ValidationError(f"头像文件验证失败: {e}")
        super().save(*args, **kwargs)


class Friendship(models.Model):
    """好友关系模型"""

    STATUS_CHOICES = [
        ('pending', '待确认'),
        ('accepted', '已接受'),
        ('blocked', '已屏蔽'),
    ]

    from_user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='sent_friend_requests',
        help_text="发起好友请求的用户"
    )
    to_user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='received_friend_requests',
        help_text="接收好友请求的用户"
    )
    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default='pending',
        help_text="好友关系状态"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'friendships'
        unique_together = ['from_user', 'to_user']
        verbose_name = '好友关系'
        verbose_name_plural = '好友关系'

    def __str__(self):
        return f"{self.from_user.username} -> {self.to_user.username} ({self.status})"


class UserLevelUpgrade(models.Model):
    """用户等级晋升记录"""

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='level_upgrades',
        help_text="被晋升的用户"
    )
    promoted_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='promotions_given',
        help_text="执行晋升的4级用户",
        null=True,
        blank=True
    )
    from_level = models.IntegerField(help_text="原等级")
    to_level = models.IntegerField(help_text="新等级")
    reason = models.CharField(
        max_length=20,
        choices=[
            ('activity', '活跃度达标'),
            ('manual', '手动晋升'),
            ('downgrade', '降级'),
        ],
        help_text="晋升原因"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'user_level_upgrades'
        verbose_name = '等级晋升记录'
        verbose_name_plural = '等级晋升记录'

    def __str__(self):
        return f"{self.user.username}: Level {self.from_level} -> {self.to_level}"


class DailyLoginReward(models.Model):
    """每日登录奖励记录"""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='daily_login_rewards',
        help_text="获得奖励的用户"
    )
    date = models.DateField(help_text="奖励日期")
    user_level = models.IntegerField(help_text="用户等级")
    reward_amount = models.IntegerField(help_text="奖励积分数量")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'daily_login_rewards'
        unique_together = ['user', 'date']  # 确保每个用户每天只能获得一次奖励
        verbose_name = '每日登录奖励'
        verbose_name_plural = '每日登录奖励'

    def __str__(self):
        return f"{self.user.username} - {self.date} - Level {self.user_level} - {self.reward_amount}积分"


class Notification(models.Model):
    """通知系统"""

    TYPE_CHOICES = [
        # 社交互动类
        ('post_liked', '动态被点赞'),
        ('post_commented', '动态被评论'),
        ('comment_liked', '评论被点赞'),
        ('comment_replied', '评论被回复'),

        # 任务相关类
        ('task_overtime_added', '任务被他人加时'),
        ('task_board_taken', '任务板任务被接取'),
        ('task_board_submitted', '任务板任务被提交'),
        ('task_board_approved', '任务板任务被审核通过'),
        ('task_board_rejected', '任务板任务被拒绝'),
        ('task_deadline_reminder_8h', '任务截止前8小时提醒'),

        # 打卡投票系统类
        ('checkin_vote_cast', '打卡投票'),
        ('checkin_vote_passed', '打卡投票通过'),
        ('checkin_vote_rejected', '打卡投票拒绝'),
        ('checkin_vote_reward', '打卡投票奖励'),
        ('checkin_vote_passed_voter', '投票成功通知（投票者）'),
        ('task_frozen_by_vote', '投票冻结任务'),
        ('task_frozen_auto_strict', '严格模式自动冻结任务'),
        ('task_failed_by_vote', '投票失败任务'),

        # 积分系统类
        ('coins_earned_hourly', '小时奖励积分'),
        ('coins_earned_hourly_batch', '批量小时奖励积分'),
        ('coins_earned_daily_login', '每日登录奖励积分'),
        ('coins_earned_daily_checkin', '每日首次打卡奖励积分'),
        ('coins_earned_daily_board_post', '每日首次发布任务板奖励积分'),
        ('coins_earned_task_reward', '任务奖励积分'),
        ('coins_spent_task_creation', '创建任务消耗积分'),

        # 物品/探索类
        ('treasure_found', '掩埋物品被发现'),
        ('photo_viewed', '照片被查看'),
        ('note_viewed', '纸条被查看'),
        ('drift_bottle_found', '漂流瓶被发现'),
        ('item_received', '收到物品'),

        # 好友系统类
        ('friend_request', '好友请求'),
        ('friend_accepted', '好友请求被接受'),

        # 系统类
        ('level_upgraded', '等级提升'),
        ('system_announcement', '系统公告'),
        ('system_event_occurred', '系统事件发生'),
    ]

    PRIORITY_CHOICES = [
        ('low', '低'),
        ('normal', '普通'),
        ('high', '高'),
        ('urgent', '紧急'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # 接收通知的用户
    recipient = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='notifications',
        help_text="接收通知的用户"
    )

    # 触发通知的用户（可以为空，比如系统通知）
    actor = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='triggered_notifications',
        null=True,
        blank=True,
        help_text="触发通知的用户"
    )

    # 通知类型和内容
    notification_type = models.CharField(
        max_length=30,
        choices=TYPE_CHOICES,
        help_text="通知类型"
    )
    title = models.CharField(
        max_length=200,
        help_text="通知标题"
    )
    message = models.TextField(
        max_length=500,
        help_text="通知内容"
    )

    # 优先级
    priority = models.CharField(
        max_length=10,
        choices=PRIORITY_CHOICES,
        default='normal',
        help_text="通知优先级"
    )

    # 关联对象信息（使用JSON存储）
    related_object_type = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        help_text="关联对象类型 (如: post, task, comment 等)"
    )
    related_object_id = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        help_text="关联对象ID"
    )

    # 额外数据
    extra_data = models.JSONField(
        default=dict,
        blank=True,
        help_text="额外的通知数据"
    )

    # 状态管理
    is_read = models.BooleanField(
        default=False,
        help_text="是否已读"
    )
    read_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="读取时间"
    )

    # 时间戳
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'notifications'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['recipient', '-created_at']),
            models.Index(fields=['recipient', 'is_read']),
            models.Index(fields=['notification_type', '-created_at']),
        ]
        verbose_name = '通知'
        verbose_name_plural = '通知'

    def __str__(self):
        return f"{self.get_notification_type_display()} -> {self.recipient.username}"

    def mark_as_read(self):
        """标记为已读"""
        if not self.is_read:
            self.is_read = True
            self.read_at = timezone.now()
            self.save(update_fields=['is_read', 'read_at'])

    @property
    def target_url(self):
        """获取通知目标链接"""
        url_mapping = {
            'post_liked': f'/posts/{self.related_object_id}',
            'post_commented': f'/posts/{self.related_object_id}',
            'comment_liked': f'/posts/{self.extra_data.get("post_id")}',
            'comment_replied': f'/posts/{self.extra_data.get("post_id")}',
            'task_overtime_added': f'/tasks/{self.related_object_id}',
            'task_board_taken': f'/tasks/{self.related_object_id}',
            'task_board_submitted': f'/tasks/{self.related_object_id}',
            'task_board_approved': f'/tasks/{self.related_object_id}',
            'task_board_rejected': f'/tasks/{self.related_object_id}',
            'treasure_found': f'/store/treasures/{self.related_object_id}',
            'photo_viewed': f'/store/photos/{self.related_object_id}',
            'note_viewed': f'/store/notes/{self.related_object_id}',
            'drift_bottle_found': f'/store/bottles/{self.related_object_id}',
            'friend_request': '/friends',
            'friend_accepted': f'/profile/{self.actor.username}' if self.actor else '/friends',
        }

        return url_mapping.get(self.notification_type, '/')

    @classmethod
    def create_notification(cls, recipient, notification_type, title=None, message=None,
                          actor=None, related_object_type=None, related_object_id=None,
                          extra_data=None, priority='normal'):
        """创建通知的便捷方法"""
        # 避免给自己发送通知（除了系统通知）
        if actor and actor == recipient and notification_type != 'system_announcement':
            return None

        notification = cls.objects.create(
            recipient=recipient,
            actor=actor,
            notification_type=notification_type,
            title=title or cls._get_default_title(notification_type, actor),
            message=message or cls._get_default_message(notification_type, actor),
            priority=priority,
            related_object_type=related_object_type,
            related_object_id=str(related_object_id) if related_object_id else None,
            extra_data=extra_data or {}
        )

        # 异步发送 Telegram 通知
        cls._send_telegram_notification_async(notification)

        return notification

    @classmethod
    def _send_telegram_notification_async(cls, notification):
        """异步发送 Telegram 通知"""
        try:
            # 导入放在方法内部避免循环导入
            from telegram_bot.services import telegram_service

            # 检查用户是否可以接收 Telegram 通知，并且只转发 urgent 优先级的通知
            if (notification.recipient.can_receive_telegram_notifications() and
                notification.priority == 'urgent'):
                # 异步发送通知（这里简化处理，实际生产环境可能需要使用 Celery 等任务队列）
                import asyncio
                import threading

                def send_notification():
                    try:
                        # 使用 asyncio.run() 来安全地运行异步代码
                        asyncio.run(
                            telegram_service.send_notification(
                                user_id=notification.recipient.id,
                                title=notification.title,
                                message=notification.message,
                                extra_data=notification.extra_data
                            )
                        )
                    except Exception as e:
                        # 记录错误但不影响主流程
                        import logging
                        logger = logging.getLogger(__name__)
                        logger.error(f"Failed to send Telegram notification: {e}")
                        import traceback
                        logger.error(f"Traceback: {traceback.format_exc()}")

                # 在后台线程中发送通知
                thread = threading.Thread(target=send_notification)
                thread.daemon = True
                thread.start()

        except Exception as e:
            # 记录错误但不影响主流程
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error in Telegram notification async send: {e}")

    @classmethod
    def _get_default_title(cls, notification_type, actor):
        """获取默认标题"""
        actor_name = actor.username if actor else "系统"

        title_mapping = {
            'post_liked': f"{actor_name}点赞了你的动态",
            'post_commented': f"{actor_name}评论了你的动态",
            'comment_liked': f"{actor_name}点赞了你的评论",
            'comment_replied': f"{actor_name}回复了你的评论",
            'task_overtime_added': f"{actor_name}给你的任务加时了",
            'task_board_taken': f"{actor_name}接取了你的任务",
            'task_board_submitted': f"{actor_name}提交了任务完成证明",
            'task_board_approved': "任务审核通过",
            'task_board_rejected': "任务被拒绝",
            'task_deadline_reminder_8h': "任务即将截止提醒",
            'task_board_ended': f"{actor_name}结束了任务",
            'task_board_reward': "获得任务奖励",
            'checkin_vote_cast': f"{actor_name}对你的打卡投票了",
            'checkin_vote_passed': "打卡投票通过",
            'checkin_vote_rejected': "打卡投票被拒绝",
            'checkin_vote_reward': "打卡投票奖励",
            'checkin_vote_passed_voter': "投票成功",
            'task_frozen_by_vote': "任务因投票被冻结",
            'task_frozen_auto_strict': "严格模式任务自动冻结",
            'task_failed_by_vote': "任务因投票失败",
            'coins_earned_hourly': "获得小时奖励积分",
            'coins_earned_hourly_batch': "获得批量小时奖励积分",
            'coins_earned_daily_login': "获得每日登录奖励",
            'coins_earned_daily_checkin': "获得每日首次打卡奖励",
            'coins_earned_daily_board_post': "获得每日首次发布任务板奖励",
            'coins_earned_task_reward': "获得任务奖励积分",
            'coins_earned_task_completion': "获得任务完成积分",
            'coins_refunded_task_failed': "任务失败积分退还",
            'treasure_found': f"{actor_name}发现了你的宝物",
            'photo_viewed': f"{actor_name}查看了你的照片",
            'note_viewed': f"{actor_name}查看了你的纸条",
            'drift_bottle_found': f"{actor_name}发现了你的漂流瓶",
            'friend_request': f"{actor_name}向你发送了好友请求",
            'friend_accepted': f"{actor_name}接受了你的好友请求",
            'level_upgraded': "恭喜你等级提升！",
            'item_shared': f"{actor_name}分享了物品给你",
            'game_result': "游戏结果通知",
            'system_event_occurred': "系统事件发生",
        }

        return title_mapping.get(notification_type, "新通知")

    @classmethod
    def _get_default_message(cls, notification_type, actor):
        """获取默认消息"""
        actor_name = actor.username if actor else "系统"

        message_mapping = {
            'post_liked': f"{actor_name}觉得你的动态很棒！",
            'post_commented': f"{actor_name}对你的动态发表了评论",
            'comment_liked': f"{actor_name}赞同了你的观点",
            'comment_replied': f"{actor_name}回复了你的评论，快去看看吧",
            'task_overtime_added': f"{actor_name}给你的任务增加了时间",
            'task_board_taken': f"你发布的任务已被{actor_name}接取",
            'task_board_submitted': f"{actor_name}已提交任务完成证明，请及时审核",
            'task_board_approved': "你的任务已通过审核，奖励已到账",
            'task_board_rejected': "很遗憾，你的任务未通过审核",
            'task_deadline_reminder_8h': "您参与的任务即将在8小时内截止，请及时提交完成证明",
            'checkin_vote_cast': f"{actor_name}对你的打卡动态投了票",
            'checkin_vote_passed': "你的打卡动态投票通过，任务继续进行",
            'checkin_vote_rejected': "你的打卡动态投票被拒绝，任务已被冻结或失败",
            'checkin_vote_reward': "你的打卡动态投票通过，获得社区奖励积分",
            'checkin_vote_passed_voter': "你支持的打卡动态投票通过了",
            'task_frozen_by_vote': "你的活跃任务因打卡投票被拒绝而冻结",
            'task_frozen_auto_strict': "你的严格模式任务因未在24小时内打卡而被系统自动冻结",
            'task_failed_by_vote': "你的任务因打卡投票被拒绝而失败",
            'coins_earned_hourly': "你的任务已运行满一小时，获得1积分奖励",
            'coins_earned_hourly_batch': "你的任务持续进行中，累计获得积分奖励",
            'coins_earned_daily_login': "欢迎回来！获得每日登录奖励积分",
            'coins_earned_daily_checkin': "带锁任务状态下每日首次打卡，获得1积分奖励",
            'coins_earned_daily_board_post': "恭喜！每日首次发布任务板，获得5积分奖励",
            'coins_earned_task_reward': "任务完成，获得奖励积分",
            'coins_earned_task_completion': "任务完成，获得完成奖励积分",
            'coins_refunded_task_failed': "任务失败，已退还扣除的积分",
            'task_board_ended': f"{actor_name}结束了任务，请查看结果",
            'task_board_reward': "任务完成，获得奖励积分",
            'item_shared': f"{actor_name}与你分享了一个物品",
            'game_result': "游戏结果已出炉，快来查看",
            'treasure_found': f"{actor_name}在探索中发现了你埋藏的宝物",
            'photo_viewed': f"{actor_name}查看了你分享的照片",
            'note_viewed': f"{actor_name}查看了你的纸条内容",
            'drift_bottle_found': f"你的漂流瓶被{actor_name}发现了",
            'friend_request': f"{actor_name}想要和你成为好友",
            'friend_accepted': f"你们现在是好友了，可以开始聊天",
            'level_upgraded': "你的等级已经提升，解锁了新功能",
            'system_event_occurred': "系统事件已触发，可能对你的游戏体验产生影响",
        }

        return message_mapping.get(notification_type, "你有新的通知")


class ActivityLog(models.Model):
    """用户活跃度变化日志"""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='activity_logs',
        help_text="相关用户"
    )
    action_type = models.CharField(
        max_length=50,
        choices=[
            ('activity_gain', '活跃度获得'),
            ('time_decay', '时间衰减'),
        ],
        help_text="活动类型"
    )
    points_change = models.IntegerField(
        help_text="积分变化（正数为增加，负数为减少）"
    )
    new_total = models.IntegerField(
        help_text="变化后的总积分"
    )
    metadata = models.JSONField(
        default=dict,
        blank=True,
        help_text="额外的元数据"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'activity_logs'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['action_type', '-created_at']),
        ]
        verbose_name = '活跃度日志'
        verbose_name_plural = '活跃度日志'

    def __str__(self):
        return f"{self.user.username} - {self.get_action_type_display()}: {self.points_change:+d} (总计: {self.new_total})"
