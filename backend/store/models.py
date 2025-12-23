from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError
import uuid
import json


class ItemType(models.Model):
    """道具类型"""

    TYPE_CHOICES = [
        ('photo_paper', '相纸'),
        ('photo', '照片'),
        ('drift_bottle', '漂流瓶'),
        ('key', '钥匙'),
        ('note', '纸条'),
        ('little_treasury', '小金库'),
        ('detection_radar', '探测雷达'),
        ('blizzard_bottle', '暴雪瓶'),
        ('sun_bottle', '太阳瓶'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=50, choices=TYPE_CHOICES, unique=True)
    display_name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    icon = models.CharField(max_length=50, default='📦')  # 用emoji作为图标
    is_consumable = models.BooleanField(default=True)  # 是否消耗品
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.display_name


class UserInventory(models.Model):
    """用户背包"""

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='inventory')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def max_slots(self):
        """根据用户等级计算背包容量"""
        user_level = getattr(self.user, 'level', 1)
        slots_map = {1: 6, 2: 12, 3: 18, 4: 24}
        return slots_map.get(min(user_level, 4), 6)

    @property
    def used_slots(self):
        """已使用的背包格数"""
        return self.items.count()

    @property
    def available_slots(self):
        """可用的背包格数"""
        return self.max_slots - self.used_slots

    def can_add_item(self):
        """检查是否可以添加新道具"""
        return self.available_slots > 0

    def __str__(self):
        return f"{self.user.username}的背包 ({self.used_slots}/{self.max_slots})"


class Item(models.Model):
    """道具实例"""

    STATUS_CHOICES = [
        ('available', '可用'),
        ('used', '已使用'),
        ('expired', '已过期'),
        ('in_drift_bottle', '在漂流瓶中'),
        ('buried', '已掩埋'),
        ('shared', '已分享'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    item_type = models.ForeignKey(ItemType, on_delete=models.CASCADE)
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='items')
    original_owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='originally_owned_items', null=True, blank=True, help_text='原始拥有者（如任务创建者）')
    inventory = models.ForeignKey(UserInventory, on_delete=models.CASCADE, related_name='items', null=True, blank=True)

    # 道具属性（JSON存储）
    properties = models.JSONField(default=dict, blank=True)

    # 状态管理
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='available')

    # 时间信息
    created_at = models.DateTimeField(auto_now_add=True)
    used_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.item_type.display_name} ({self.owner.username})"


class StoreItem(models.Model):
    """商店商品"""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    item_type = models.ForeignKey(ItemType, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    description = models.TextField()
    price = models.IntegerField(help_text='价格（积分）')
    icon = models.CharField(max_length=50, default='🛍️')
    is_available = models.BooleanField(default=True)
    stock = models.IntegerField(null=True, blank=True, help_text='库存，null表示无限')

    # 购买限制
    daily_limit = models.IntegerField(null=True, blank=True, help_text='每日购买限制')
    level_requirement = models.IntegerField(default=1, help_text='所需用户等级')

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['price']

    def __str__(self):
        return f"{self.name} - {self.price}积分"


class Purchase(models.Model):
    """购买记录"""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='purchases')
    store_item = models.ForeignKey(StoreItem, on_delete=models.CASCADE)
    item = models.ForeignKey(Item, on_delete=models.CASCADE, related_name='purchase')
    price_paid = models.IntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} 购买 {self.store_item.name}"


class Game(models.Model):
    """游戏实例"""

    GAME_TYPE_CHOICES = [
        ('time_wheel', '时间转盘'),
        ('rock_paper_scissors', '石头剪刀布'),
        ('exploration', '探索'),
        ('dice', '掷骰子'),
    ]

    STATUS_CHOICES = [
        ('waiting', '等待玩家'),
        ('active', '进行中'),
        ('completed', '已完成'),
        ('cancelled', '已取消'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    game_type = models.CharField(max_length=30, choices=GAME_TYPE_CHOICES)
    creator = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='created_games')
    participants = models.ManyToManyField(settings.AUTH_USER_MODEL, through='GameParticipant', related_name='participated_games')

    # 游戏参数
    bet_amount = models.IntegerField(default=1, help_text='下注积分')
    max_players = models.IntegerField(default=2)

    # 游戏状态
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='waiting')
    game_data = models.JSONField(default=dict, blank=True)  # 存储游戏特定数据
    result = models.JSONField(default=dict, blank=True)     # 存储游戏结果

    # 时间信息
    created_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.get_game_type_display()} - {self.creator.username}"


class GameParticipant(models.Model):
    """游戏参与者"""

    game = models.ForeignKey(Game, on_delete=models.CASCADE)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    joined_at = models.DateTimeField(auto_now_add=True)

    # 游戏中的行动
    action = models.JSONField(default=dict, blank=True)

    class Meta:
        unique_together = ['game', 'user']

    def __str__(self):
        return f"{self.user.username} in {self.game}"


class DriftBottle(models.Model):
    """漂流瓶"""

    STATUS_CHOICES = [
        ('floating', '漂流中'),
        ('found', '已被发现'),
        ('expired', '已过期'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='sent_bottles')
    finder = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='found_bottles')

    # 漂流瓶内容
    message = models.TextField(blank=True)
    items = models.ManyToManyField(Item, blank=True)

    # 漂流参数
    drift_duration = models.IntegerField(default=24, help_text='漂流持续时间（小时）')
    location_hint = models.CharField(max_length=200, blank=True)

    # 状态管理
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='floating')

    # 时间信息
    created_at = models.DateTimeField(auto_now_add=True)
    found_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField()

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"漂流瓶 from {self.sender.username}"


class BuriedTreasure(models.Model):
    """埋藏的宝物"""

    STATUS_CHOICES = [
        ('buried', '已埋藏'),
        ('found', '已发现'),
        ('expired', '已过期'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    burier = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='buried_treasures')
    finder = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='found_treasures')

    # 宝物内容
    item = models.ForeignKey(Item, on_delete=models.CASCADE)

    # 位置信息（简化为区域）
    location_zone = models.CharField(max_length=50)
    location_hint = models.CharField(max_length=200)

    # 发现难度
    difficulty = models.CharField(max_length=20, choices=[
        ('easy', '简单'),
        ('normal', '普通'),
        ('hard', '困难'),
    ], default='normal')

    # 状态管理
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='buried')

    # 时间信息
    created_at = models.DateTimeField(auto_now_add=True)
    found_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField()

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"宝物 {self.item.item_type.display_name} by {self.burier.username}"


class SharedItem(models.Model):
    """分享的道具"""

    STATUS_CHOICES = [
        ('active', '可领取'),
        ('claimed', '已领取'),
        ('expired', '已过期'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    sharer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='shared_items')
    claimer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='claimed_shared_items')

    # 分享的道具
    item = models.ForeignKey(Item, on_delete=models.CASCADE)

    # 分享链接和状态
    share_token = models.CharField(max_length=64, unique=True, help_text='分享链接的唯一标识符')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')

    # 时间信息
    created_at = models.DateTimeField(auto_now_add=True)
    claimed_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(help_text='分享链接过期时间')

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"分享: {self.item.item_type.display_name} by {self.sharer.username}"


class GameSession(models.Model):
    """游戏会话（用于记录时间转盘等结果）"""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='game_sessions')
    game_type = models.CharField(max_length=30)

    # 游戏参数
    bet_amount = models.IntegerField()
    result_data = models.JSONField(default=dict)

    # 关联的任务（如果适用）
    related_task = models.ForeignKey('tasks.LockTask', on_delete=models.SET_NULL, null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.game_type} - {self.bet_amount}积分"
