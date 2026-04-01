"""
男娘幻城 — 数据库模型
文字版溜走塔科夫 + 狼人杀
"""
import uuid
from django.db import models
from django.conf import settings
from django.utils import timezone


# ─────────────────────────────────────────────
# 区域与在场
# ─────────────────────────────────────────────

class GameZone(models.Model):
    ZONE_CHOICES = [
        ('ruins', '备皮间'),
        ('ruins_deep', '深处备皮间'),
        ('ruins_outer', '外围备皮间'),
        ('salon', '闺房'),
        ('black_market', '黑市'),
        ('armory', '储物柜'),
        ('checkpoint', '安检口'),
        ('abandoned_camp', '更衣室'),
        ('sewer', '下水道'),
        ('interrogation_room', '审问室'),
        ('control_room', '禁闭室'),
    ]
    name = models.CharField(max_length=20, choices=ZONE_CHOICES, unique=True)
    display_name = models.CharField(max_length=50)
    description = models.TextField()
    crystal_respawn_rate = models.IntegerField(default=5, help_text='每小时刷新刀具数')
    max_players = models.IntegerField(default=50)
    config = models.JSONField(default=dict)

    class Meta:
        verbose_name = '游戏区域'
        verbose_name_plural = '游戏区域'

    def __str__(self):
        return self.display_name


class PlayerZonePresence(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='zone_presence'
    )
    zone = models.ForeignKey(GameZone, on_delete=models.CASCADE, related_name='presences')
    entered_at = models.DateTimeField(auto_now_add=True)
    exited_at = models.DateTimeField(null=True, blank=True)
    entry_stats = models.JSONField(default=dict)

    class Meta:
        verbose_name = '玩家区域在场'
        verbose_name_plural = '玩家区域在场'
        indexes = [
            models.Index(fields=['user', 'exited_at']),
            models.Index(fields=['zone', 'exited_at']),
        ]

    def __str__(self):
        return f'{self.user.username} @ {self.zone.display_name}'


# ─────────────────────────────────────────────
# 阵营档案
# ─────────────────────────────────────────────

FACTION_CHOICES = [('mimic', '小男娘'), ('patrol', '小s')]


class MimicProfile(models.Model):
    """小男娘（男娘）档案"""
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='mimic_profile'
    )
    depilation_charge = models.IntegerField(default=100, help_text='脱毛仪电量 0-100')
    suppression_value = models.IntegerField(default=0, help_text='发毛值 0-100')
    purity_score = models.IntegerField(default=50, help_text='光滑度 0-100')
    femboy_score = models.IntegerField(default=0, help_text='柔化度 0-100')
    smoothness_score = models.IntegerField(default=0, help_text='光滑度 0-100')
    control_resistance = models.IntegerField(default=0, help_text='抵抗力')
    permanent_tells = models.JSONField(default=list)
    base_detectability = models.IntegerField(default=0)
    current_faction = models.CharField(max_length=10, choices=FACTION_CHOICES, default='mimic')
    active_run_lock_task = models.ForeignKey(
        'tasks.LockTask', null=True, blank=True,
        on_delete=models.SET_NULL, related_name='mimic_run'
    )
    is_disguised = models.BooleanField(default=False)
    disguise_start_time = models.DateTimeField(null=True, blank=True)
    last_suppression_tick = models.DateTimeField(null=True, blank=True)
    last_depilation_tick = models.DateTimeField(null=True, blank=True)
    total_successful_runs = models.IntegerField(default=0)
    total_failed_runs = models.IntegerField(default=0)
    total_crystals_collected = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = '小男娘档案'
        verbose_name_plural = '小男娘档案'

    def __str__(self):
        return f'小男娘:{self.user.username}'


class PatrolProfile(models.Model):
    """小s档案"""
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='patrol_profile'
    )
    authority_value = models.IntegerField(default=80, help_text='管控力 0-100')
    reputation_score = models.IntegerField(default=60, help_text='声誉值 0-100')
    inspection_tokens = models.IntegerField(default=10, help_text='配额（每日重置）')
    inspection_tokens_last_reset = models.DateField(auto_now_add=True)
    suspicion_evidence = models.JSONField(default=dict)
    detection_tools = models.JSONField(
        default=dict,
        help_text='{"visual": true, "pat_down": true, "body_scan": false}'
    )
    current_faction = models.CharField(max_length=10, choices=FACTION_CHOICES, default='patrol')
    total_arrests = models.IntegerField(default=0)
    false_accusations = models.IntegerField(default=0)
    total_correct_identifications = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = '小s档案'
        verbose_name_plural = '小s档案'

    def __str__(self):
        return f'小s:{self.user.username}'


# ─────────────────────────────────────────────
# 破绽系统
# ─────────────────────────────────────────────

class TellEvent(models.Model):
    TELL_TYPE_CHOICES = [
        ('body_hair', '体毛破绽'),
        ('suppression_tremor', '压抑震颤'),
        ('abnormal_pause', '异常停顿'),
        ('weight_anomaly', '重量异常'),
        ('scent_residue', '气味残留'),
        ('disguise_fatigue', '伪装疲态'),
        ('lock_resonance', '锁链暗示'),
        ('pitch_slippage', '声调滑落'),
    ]
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    player = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='tell_events'
    )
    tell_type = models.CharField(max_length=30, choices=TELL_TYPE_CHOICES)
    tell_text = models.TextField(help_text='渲染的斜体文字')
    zone = models.ForeignKey(GameZone, on_delete=models.CASCADE, related_name='tell_events')
    checkpoint_session = models.ForeignKey(
        'CheckpointSession', null=True, blank=True,
        on_delete=models.SET_NULL, related_name='tell_events'
    )
    action_type = models.CharField(max_length=50, default='presence')
    stats_snapshot = models.JSONField(default=dict)
    discovered_by = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        blank=True, related_name='discovered_tells'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = '破绽事件'
        verbose_name_plural = '破绽事件'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['player', 'checkpoint_session']),
            models.Index(fields=['checkpoint_session', 'created_at']),
        ]

    def __str__(self):
        return f'{self.player.username} - {self.get_tell_type_display()}'


# ─────────────────────────────────────────────
# 安检口会话
# ─────────────────────────────────────────────

class CheckpointSession(models.Model):
    STATUS_CHOICES = [
        ('active', '进行中'),
        ('closed', '已结束'),
    ]
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    zone = models.ForeignKey(GameZone, on_delete=models.CASCADE, related_name='checkpoint_sessions')
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='active')
    participants = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        through='CheckpointParticipant',
        related_name='checkpoint_sessions'
    )
    npc_count = models.IntegerField(default=0)
    npc_data = models.JSONField(default=list)
    opened_at = models.DateTimeField(auto_now_add=True)
    closed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = '安检口会话'
        verbose_name_plural = '安检口会话'

    def __str__(self):
        return f'安检口会话 {self.id} ({self.status})'


class CheckpointParticipant(models.Model):
    ROLE_CHOICES = [('smuggler', '小男娘'), ('patrol', '巡逻')]
    OUTCOME_CHOICES = [
        ('pending', '未决'),
        ('passed', '通过'),
        ('arrested', '被捕'),
        ('fled', '逃脱'),
        ('bribed_through', '打点通过'),
    ]
    session = models.ForeignKey(CheckpointSession, on_delete=models.CASCADE, related_name='checkpoint_participants')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='checkpoint_participations')
    role = models.CharField(max_length=10, choices=ROLE_CHOICES)
    outcome = models.CharField(max_length=15, choices=OUTCOME_CHOICES, default='pending')
    entered_at = models.DateTimeField(auto_now_add=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    contraband_snapshot = models.JSONField(default=list)
    queue_position = models.IntegerField(null=True, blank=True)

    class Meta:
        verbose_name = '安检口参与者'
        verbose_name_plural = '安检口参与者'
        unique_together = ['session', 'user']

    def __str__(self):
        return f'{self.user.username} ({self.role})'


class InterrogationRequest(models.Model):
    """盘问请求（异步，有截止时间）"""
    STATUS_CHOICES = [
        ('pending', '等待作答'),
        ('answered', '已作答'),
        ('expired', '已超时'),
    ]
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    session = models.ForeignKey(CheckpointSession, on_delete=models.CASCADE, related_name='interrogations')
    interrogator = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='interrogations_sent'
    )
    target = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='interrogations_received'
    )
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    question = models.TextField()
    response_text = models.TextField(blank=True)
    response_time_seconds = models.IntegerField(null=True, blank=True)
    triggered_pause_tell = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    deadline = models.DateTimeField()
    answered_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = '盘问请求'
        verbose_name_plural = '盘问请求'

    def __str__(self):
        return f'{self.interrogator.username} 盘问 {self.target.username}'


# ─────────────────────────────────────────────
# 灰色市场交易
# ─────────────────────────────────────────────

class GrayMarketTransaction(models.Model):
    TRANSACTION_TYPE_CHOICES = [
        ('bribe', '打点'),
        ('extortion', '威胁'),
        ('trade', '交易'),
        ('armory_toll', '储物柜通行费'),
    ]
    STATUS_CHOICES = [
        ('proposed', '提议中'),
        ('negotiating', '谈判中'),
        ('accepted', '已接受'),
        ('rejected', '已拒绝'),
        ('betrayed', '被背叛'),
        ('completed', '已完成'),
        ('expired', '已过期'),
    ]
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    transaction_type = models.CharField(max_length=15, choices=TRANSACTION_TYPE_CHOICES)
    initiator = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='initiated_transactions'
    )
    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='received_transactions'
    )
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='proposed')
    offer_from_initiator = models.JSONField(default=dict)
    offer_from_recipient = models.JSONField(default=dict)
    escrowed_crystals = models.IntegerField(default=0)
    checkpoint_session = models.ForeignKey(
        CheckpointSession, null=True, blank=True,
        on_delete=models.SET_NULL, related_name='transactions'
    )
    encrypted_channel_id = models.UUIDField(null=True, blank=True)
    zone_name = models.CharField(max_length=20, blank=True, default='')
    negotiation_log = models.JSONField(default=list)
    created_at = models.DateTimeField(auto_now_add=True)
    accepted_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField()
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = '灰色市场交易'
        verbose_name_plural = '灰色市场交易'
        indexes = [
            models.Index(fields=['initiator', 'status']),
            models.Index(fields=['recipient', 'status']),
            models.Index(fields=['expires_at', 'status']),
        ]

    def __str__(self):
        return f'{self.get_transaction_type_display()} {self.initiator.username}→{self.recipient.username}'


# ─────────────────────────────────────────────
# 锁控制权转移
# ─────────────────────────────────────────────

class GameControlTransfer(models.Model):
    SOURCE_CHOICES = [
        ('arrest', '收押'),
        ('bribe_deal', '打点协议'),
        ('extortion_deal', '威胁协议'),
    ]
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    lock_task = models.ForeignKey(
        'tasks.LockTask', on_delete=models.CASCADE,
        related_name='game_control_transfers'
    )
    grantor = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='granted_controls'
    )
    grantee = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='received_controls'
    )
    source = models.CharField(max_length=15, choices=SOURCE_CHOICES)
    can_add_time = models.BooleanField(default=True)
    can_freeze = models.BooleanField(default=True)
    can_assign_tasks = models.BooleanField(default=False)
    duration_hours = models.IntegerField()
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    is_active = models.BooleanField(default=True)
    revoked_at = models.DateTimeField(null=True, blank=True)
    revoked_reason = models.CharField(max_length=100, blank=True)

    class Meta:
        verbose_name = '锁控制权转移'
        verbose_name_plural = '锁控制权转移'
        indexes = [
            models.Index(fields=['grantee', 'is_active']),
            models.Index(fields=['expires_at', 'is_active']),
        ]

    def __str__(self):
        return f'{self.grantee.username} 控制 {self.grantor.username} 的锁'


# ─────────────────────────────────────────────
# 收押记录
# ─────────────────────────────────────────────

class DetentionRecord(models.Model):
    STATUS_CHOICES = [
        ('active', '收押中'),
        ('released_timeout', '时限释放'),
        ('released_ransom', '赎金释放'),
        ('released_conversion', '转化释放'),
        ('escaped', '逃脱'),
    ]
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    prisoner = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='detention_records'
    )
    captor = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='captured_records'
    )
    status = models.CharField(max_length=25, choices=STATUS_CHOICES, default='active')
    seized_crystals = models.IntegerField(default=0)
    control_transfer = models.OneToOneField(
        GameControlTransfer, null=True, blank=True,
        on_delete=models.SET_NULL, related_name='detention'
    )
    duration_hours = models.IntegerField(default=12)
    arrested_at = models.DateTimeField(auto_now_add=True)
    release_at = models.DateTimeField()
    released_at = models.DateTimeField(null=True, blank=True)
    punishment_tasks_completed = models.IntegerField(default=0)
    punishment_tasks_failed = models.IntegerField(default=0)
    charm_attempts_used = models.IntegerField(default=0)
    last_charm_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = '收押记录'
        verbose_name_plural = '收押记录'
        indexes = [
            models.Index(fields=['prisoner', 'status']),
            models.Index(fields=['release_at', 'status']),
        ]

    def __str__(self):
        return f'{self.prisoner.username} 被 {self.captor.username} 收押'


# ─────────────────────────────────────────────
# 阵营转化事件
# ─────────────────────────────────────────────

class FactionConversionEvent(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    converted_user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='conversion_events'
    )
    from_faction = models.CharField(max_length=10, choices=FACTION_CHOICES)
    to_faction = models.CharField(max_length=10, choices=FACTION_CHOICES)
    detention_record = models.ForeignKey(
        DetentionRecord, null=True, blank=True,
        on_delete=models.SET_NULL, related_name='conversion_events'
    )
    charm_attempts_count = models.IntegerField(default=0)
    authority_at_conversion = models.IntegerField(default=0)
    purity_at_conversion = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = '阵营转化事件'
        verbose_name_plural = '阵营转化事件'

    def __str__(self):
        return f'{self.converted_user.username}: {self.from_faction}→{self.to_faction}'


# ─────────────────────────────────────────────
# 加密频道
# ─────────────────────────────────────────────

class EncryptedChannel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    participant_a = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='encrypted_channels_a'
    )
    participant_b = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='encrypted_channels_b'
    )
    linked_transaction = models.ForeignKey(
        GrayMarketTransaction, null=True, blank=True,
        on_delete=models.SET_NULL, related_name='encrypted_channel'
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    closed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = '加密频道'
        verbose_name_plural = '加密频道'

    def __str__(self):
        return f'加密: {self.participant_a.username} ↔ {self.participant_b.username}'


class EncryptedMessage(models.Model):
    channel = models.ForeignKey(
        EncryptedChannel, on_delete=models.CASCADE,
        related_name='messages'
    )
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        null=True, blank=True, related_name='encrypted_messages'
    )
    content = models.TextField()
    is_system = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = '加密消息'
        verbose_name_plural = '加密消息'
        ordering = ['created_at']

    def __str__(self):
        sender = self.sender.username if self.sender else '系统'
        return f'{sender}: {self.content[:30]}'


# ─────────────────────────────────────────────
# 区域聊天
# ─────────────────────────────────────────────

class ZoneChatMessage(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    zone = models.ForeignKey(GameZone, on_delete=models.CASCADE, related_name='chat_messages')
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        null=True, blank=True, related_name='zone_chat_messages'
    )
    content = models.TextField()
    is_system = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = '区域聊天'
        verbose_name_plural = '区域聊天'
        ordering = ['created_at']
        indexes = [
            models.Index(fields=['zone', 'created_at']),
        ]

    def __str__(self):
        sender = self.sender.username if self.sender else '系统'
        return f'[{self.zone.display_name}] {sender}: {self.content[:30]}'


# ─────────────────────────────────────────────
# 资源与市场
# ─────────────────────────────────────────────

class CrystalDeposit(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    zone = models.ForeignKey(GameZone, on_delete=models.CASCADE, related_name='crystal_deposits')
    quantity = models.IntegerField(default=0)
    max_quantity = models.IntegerField(default=20)
    last_harvested_at = models.DateTimeField(null=True, blank=True)
    last_harvested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL, related_name='harvested_deposits'
    )
    last_respawn_at = models.DateTimeField(auto_now_add=True)
    respawn_rate_per_hour = models.IntegerField(default=3)

    class Meta:
        verbose_name = '刀具矿点'
        verbose_name_plural = '刀具矿点'

    def __str__(self):
        return f'矿点({self.quantity}/{self.max_quantity})'


class PlayerCrystals(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='crystals'
    )
    raw_crystals = models.IntegerField(default=0, help_text='原初刀具（未提纯）')
    purified_crystals = models.IntegerField(default=0, help_text='提纯刀具')
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = '玩家刀具'
        verbose_name_plural = '玩家刀具'

    def __str__(self):
        return f'{self.user.username}: 原初{self.raw_crystals} 提纯{self.purified_crystals}'


class GameMarketRate(models.Model):
    item_slug = models.CharField(max_length=50, unique=True)
    item_display_name = models.CharField(max_length=100)
    current_price_crystals = models.IntegerField()
    base_price_crystals = models.IntegerField()
    demand_pressure = models.FloatField(default=1.0)
    units_traded_last_period = models.IntegerField(default=0)
    last_recalculated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = '市场定价'
        verbose_name_plural = '市场定价'

    def __str__(self):
        return f'{self.item_display_name}: {self.current_price_crystals}刀具'


# ─────────────────────────────────────────────
# 游戏道具（男娘主题化）
# ─────────────────────────────────────────────

class GameItem(models.Model):
    TIER_CHOICES = [(1, '普通'), (2, '稀有'), (3, '珍稀'), (4, '传说')]
    SLOT_CHOICES = [
        ('outer', '外层服装'),
        ('inner', '内层装备'),
        ('device', '装置'),
        ('consumable', '消耗品'),
        ('material', '材料'),
    ]
    slug = models.CharField(max_length=60, unique=True)
    name = models.CharField(max_length=100)
    tier = models.IntegerField(choices=TIER_CHOICES, default=1)
    slot = models.CharField(max_length=20, choices=SLOT_CHOICES, default='consumable')
    description = models.TextField()
    icon = models.CharField(max_length=10, default='📦')
    stat_modifiers = models.JSONField(default=dict)
    is_lock_device = models.BooleanField(default=False)
    is_removal_device = models.BooleanField(default=False)
    is_disguise_item = models.BooleanField(default=False)
    permanent_tell = models.CharField(max_length=50, blank=True)
    permanent_detectability_bonus = models.IntegerField(default=0)
    craft_recipe = models.JSONField(default=dict)
    price_crystals = models.IntegerField(default=0)
    available_in_zones = models.JSONField(default=list)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = '游戏道具'
        verbose_name_plural = '游戏道具'

    def __str__(self):
        return f'{self.name} (Tier {self.tier})'


class PlayerGameInventory(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='game_inventory'
    )
    item = models.ForeignKey(GameItem, on_delete=models.CASCADE, related_name='inventory_entries')
    quantity = models.IntegerField(default=1)
    obtained_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = '游戏背包'
        verbose_name_plural = '游戏背包'
        unique_together = ['user', 'item']

    def __str__(self):
        return f'{self.user.username}: {self.item.name} x{self.quantity}'


class ActiveDisguise(models.Model):
    BEHAVIORAL_MODE_CHOICES = [
        ('passive', '被动'),
        ('confident', '自信'),
        ('evasive', '回避'),
    ]
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='active_disguise'
    )
    outer_layer_item = models.ForeignKey(
        GameItem, null=True, blank=True,
        on_delete=models.SET_NULL, related_name='outer_disguise_users'
    )
    inner_items = models.ManyToManyField(GameItem, blank=True, related_name='inner_disguise_users')
    behavioral_mode = models.CharField(
        max_length=20, choices=BEHAVIORAL_MODE_CHOICES, default='passive'
    )
    computed_detectability = models.IntegerField(default=0)
    computed_disguise_quality = models.IntegerField(default=0)
    computed_active_tells = models.JSONField(default=list)
    last_computed_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = '当前伪装配置'
        verbose_name_plural = '当前伪装配置'

    def __str__(self):
        return f'{self.user.username} 的伪装'


# ─────────────────────────────────────────────
# 跑商记录
# ─────────────────────────────────────────────

class SmuggleRun(models.Model):
    STATUS_CHOICES = [
        ('in_progress', '进行中'),
        ('success', '成功返回'),
        ('failed_arrested', '失败-被捕'),
        ('failed_fled', '失败-溜走'),
        ('abandoned', '放弃'),
    ]
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    player = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='smuggle_runs'
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='in_progress')
    crystals_collected = models.IntegerField(default=0)
    crystals_delivered = models.IntegerField(default=0)
    crystals_seized = models.IntegerField(default=0)
    checkpoint_session = models.ForeignKey(
        CheckpointSession, null=True, blank=True,
        on_delete=models.SET_NULL, related_name='smuggle_runs'
    )
    detention_record = models.ForeignKey(
        DetentionRecord, null=True, blank=True,
        on_delete=models.SET_NULL, related_name='smuggle_run'
    )
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    coins_earned = models.IntegerField(default=0)

    class Meta:
        verbose_name = '跑商记录'
        verbose_name_plural = '跑商记录'
        ordering = ['-started_at']

    def __str__(self):
        return f'{self.player.username} 跑商 ({self.status})'
