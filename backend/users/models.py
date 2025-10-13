from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from datetime import timedelta
import uuid


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
        upload_to='avatars/',
        blank=True,
        null=True,
        help_text="头像"
    )
    bio = models.TextField(
        max_length=500,
        blank=True,
        help_text="个人简介"
    )

    # 统计信息
    total_posts = models.IntegerField(default=0, help_text="发布动态总数")
    total_likes_received = models.IntegerField(default=0, help_text="收到点赞总数")
    total_tasks_completed = models.IntegerField(default=0, help_text="完成任务总数")

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
        """检查是否可以升级到2级"""
        return (self.level == 1 and
                self.total_posts >= 5 and
                self.total_likes_received >= 10)

    def can_upgrade_to_level_3(self):
        """检查是否可以升级到3级"""
        if self.level != 2:
            return False

        # 检查是否连续7天活跃
        seven_days_ago = timezone.now() - timedelta(days=7)
        return self.last_active >= seven_days_ago

    def should_downgrade_from_level_3(self):
        """检查3级用户是否应该降级"""
        if self.level != 3:
            return False

        # 7天以上不活跃则降级
        seven_days_ago = timezone.now() - timedelta(days=7)
        return self.last_active < seven_days_ago

    def update_activity(self):
        """更新用户活跃度"""
        self.last_active = timezone.now()
        self.activity_score += 1
        self.save()

    def get_daily_login_reward(self):
        """根据用户等级获取每日登录奖励积分"""
        return self.level  # 1/2/3/4级用户分别获得1/2/3/4积分

    def get_total_lock_duration(self):
        """获取用户总带锁时长（分钟），包括所有时间变化"""
        from tasks.models import LockTask, TaskTimelineEvent

        total_duration = 0

        # 获取用户的所有带锁任务
        user_lock_tasks = LockTask.objects.filter(
            user=self,
            task_type='lock'
        )

        for task in user_lock_tasks:
            # 计算每个任务的原始时长
            original_duration = task.duration_value if task.duration_type == 'fixed' else task.duration_max

            # 计算任务的实际运行时长（如果已完成）或当前时长（如果进行中）
            if task.end_time and task.start_time:
                actual_duration = int((task.end_time - task.start_time).total_seconds() / 60)
            elif task.start_time:
                # 任务还在进行中，计算从开始到现在的时长
                actual_duration = int((timezone.now() - task.start_time).total_seconds() / 60)
            else:
                actual_duration = 0

            # 取较大值作为基础时长
            base_duration = max(original_duration or 0, actual_duration)

            # 加上时间线中的所有时间变化
            timeline_changes = TaskTimelineEvent.objects.filter(
                task=task,
                time_change_minutes__isnull=False
            ).aggregate(
                total_change=models.Sum('time_change_minutes')
            )

            time_adjustment = timeline_changes['total_change'] or 0

            # 计算最终时长（基础时长 + 时间调整）
            final_duration = base_duration + time_adjustment

            # 只计算正数时长（避免负数）
            total_duration += max(0, final_duration)

        return total_duration


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

        # 积分系统类
        ('coins_earned_hourly', '小时奖励积分'),
        ('coins_earned_daily_login', '每日登录奖励积分'),
        ('coins_earned_task_reward', '任务奖励积分'),
        ('coins_spent_task_creation', '创建任务消耗积分'),

        # 物品/探索类
        ('treasure_found', '掩埋物品被发现'),
        ('photo_viewed', '照片被查看'),
        ('drift_bottle_found', '漂流瓶被发现'),
        ('item_received', '收到物品'),

        # 好友系统类
        ('friend_request', '好友请求'),
        ('friend_accepted', '好友请求被接受'),

        # 系统类
        ('level_upgraded', '等级提升'),
        ('system_announcement', '系统公告'),
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

        return notification

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
            'coins_earned_hourly': "获得小时奖励积分",
            'coins_earned_daily_login': "获得每日登录奖励",
            'coins_earned_task_reward': "获得任务奖励积分",
            'treasure_found': f"{actor_name}发现了你的宝物",
            'photo_viewed': f"{actor_name}查看了你的照片",
            'drift_bottle_found': f"{actor_name}发现了你的漂流瓶",
            'friend_request': f"{actor_name}向你发送了好友请求",
            'friend_accepted': f"{actor_name}接受了你的好友请求",
            'level_upgraded': "恭喜你等级提升！",
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
            'coins_earned_hourly': "你的任务已运行满一小时，获得1积分奖励",
            'coins_earned_daily_login': "欢迎回来！获得每日登录奖励积分",
            'coins_earned_task_reward': "任务完成，获得奖励积分",
            'treasure_found': f"{actor_name}在探索中发现了你埋藏的宝物",
            'photo_viewed': f"{actor_name}查看了你分享的照片",
            'drift_bottle_found': f"你的漂流瓶被{actor_name}发现了",
            'friend_request': f"{actor_name}想要和你成为好友",
            'friend_accepted': f"你们现在是好友了，可以开始聊天",
            'level_upgraded': "你的等级已经提升，解锁了新功能",
        }

        return message_mapping.get(notification_type, "你有新的通知")
