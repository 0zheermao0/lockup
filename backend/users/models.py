from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from datetime import timedelta


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
