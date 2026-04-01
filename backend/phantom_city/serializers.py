"""
男娘幻城 — DRF 序列化器
"""
from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import (
    GameZone, PlayerZonePresence, MimicProfile, PatrolProfile,
    TellEvent, CheckpointSession, CheckpointParticipant, InterrogationRequest,
    GrayMarketTransaction, GameControlTransfer, DetentionRecord,
    FactionConversionEvent, EncryptedChannel, EncryptedMessage,
    ZoneChatMessage, CrystalDeposit, PlayerCrystals, GameMarketRate,
    GameItem, PlayerGameInventory, ActiveDisguise, SmuggleRun,
)

User = get_user_model()


class UserBriefSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'avatar']


# ─────────────────────────────────────────────
# 区域
# ─────────────────────────────────────────────

class GameZoneSerializer(serializers.ModelSerializer):
    player_count = serializers.SerializerMethodField()

    class Meta:
        model = GameZone
        fields = ['id', 'name', 'display_name', 'description', 'player_count']

    def get_player_count(self, obj):
        return obj.presences.filter(exited_at__isnull=True).count()


class PlayerZonePresenceSerializer(serializers.ModelSerializer):
    user = UserBriefSerializer(read_only=True)
    zone_name = serializers.CharField(source='zone.display_name', read_only=True)

    class Meta:
        model = PlayerZonePresence
        fields = ['id', 'user', 'zone_name', 'entered_at']


# ─────────────────────────────────────────────
# 阵营档案
# ─────────────────────────────────────────────

class MimicProfileSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username', read_only=True)
    avatar = serializers.ImageField(source='user.avatar', read_only=True)

    class Meta:
        model = MimicProfile
        fields = [
            'username', 'avatar',
            'depilation_charge', 'suppression_value', 'purity_score',
            'femboy_score', 'smoothness_score', 'control_resistance',
            'base_detectability', 'current_faction',
            'is_disguised', 'total_successful_runs', 'total_failed_runs',
            'total_crystals_collected', 'permanent_tells',
        ]


class PatrolProfileSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username', read_only=True)
    avatar = serializers.ImageField(source='user.avatar', read_only=True)

    class Meta:
        model = PatrolProfile
        fields = [
            'username', 'avatar',
            'authority_value', 'reputation_score', 'inspection_tokens',
            'current_faction', 'total_arrests', 'false_accusations',
            'total_correct_identifications', 'detection_tools',
        ]


class MimicProfilePublicSerializer(serializers.ModelSerializer):
    """公开档案（小sinspect时使用，不含敏感数字）"""
    username = serializers.CharField(source='user.username', read_only=True)
    avatar = serializers.ImageField(source='user.avatar', read_only=True)

    class Meta:
        model = MimicProfile
        fields = ['username', 'avatar', 'current_faction', 'is_disguised']


# ─────────────────────────────────────────────
# 破绽
# ─────────────────────────────────────────────

class TellEventSerializer(serializers.ModelSerializer):
    player_username = serializers.CharField(source='player.username', read_only=True)

    class Meta:
        model = TellEvent
        fields = [
            'id', 'player_username', 'tell_type', 'tell_text',
            'action_type', 'created_at',
        ]


# ─────────────────────────────────────────────
# 安检口
# ─────────────────────────────────────────────

class CheckpointParticipantSerializer(serializers.ModelSerializer):
    user = UserBriefSerializer(read_only=True)

    class Meta:
        model = CheckpointParticipant
        fields = ['id', 'user', 'role', 'outcome', 'entered_at', 'queue_position']


class CheckpointSessionSerializer(serializers.ModelSerializer):
    participants = CheckpointParticipantSerializer(
        source='checkpoint_participants', many=True, read_only=True
    )
    npc_queue = serializers.SerializerMethodField()

    class Meta:
        model = CheckpointSession
        fields = ['id', 'status', 'npc_count', 'opened_at', 'participants', 'npc_queue']

    def get_npc_queue(self, obj):
        # 只返回NPC的公开信息（不含is_red_herring标志）
        return [
            {
                'id': npc['id'],
                'name': npc['name'],
                'description': npc['description'],
                'tells': npc.get('tells', []),
            }
            for npc in obj.npc_data
        ]


class InterrogationRequestSerializer(serializers.ModelSerializer):
    interrogator = UserBriefSerializer(read_only=True)
    target = UserBriefSerializer(read_only=True)

    class Meta:
        model = InterrogationRequest
        fields = [
            'id', 'interrogator', 'target', 'status',
            'question', 'response_text', 'response_time_seconds',
            'triggered_pause_tell', 'created_at', 'deadline',
        ]


# ─────────────────────────────────────────────
# 交易
# ─────────────────────────────────────────────

class GrayMarketTransactionSerializer(serializers.ModelSerializer):
    initiator = UserBriefSerializer(read_only=True)
    recipient = UserBriefSerializer(read_only=True)

    class Meta:
        model = GrayMarketTransaction
        fields = [
            'id', 'transaction_type', 'initiator', 'recipient',
            'status', 'offer_from_initiator', 'offer_from_recipient',
            'escrowed_crystals', 'encrypted_channel_id',
            'negotiation_log', 'created_at', 'expires_at',
        ]


# ─────────────────────────────────────────────
# 锁控制权
# ─────────────────────────────────────────────

class GameControlTransferSerializer(serializers.ModelSerializer):
    grantor = UserBriefSerializer(read_only=True)
    grantee = UserBriefSerializer(read_only=True)
    lock_task_title = serializers.CharField(source='lock_task.title', read_only=True)

    class Meta:
        model = GameControlTransfer
        fields = [
            'id', 'grantor', 'grantee', 'lock_task_title',
            'source', 'can_add_time', 'can_freeze', 'can_assign_tasks',
            'duration_hours', 'expires_at', 'is_active',
        ]


# ─────────────────────────────────────────────
# 收押
# ─────────────────────────────────────────────

class DetentionRecordSerializer(serializers.ModelSerializer):
    prisoner = UserBriefSerializer(read_only=True)
    captor = UserBriefSerializer(read_only=True)
    control_transfer = GameControlTransferSerializer(read_only=True)
    time_remaining_seconds = serializers.SerializerMethodField()

    class Meta:
        model = DetentionRecord
        fields = [
            'id', 'prisoner', 'captor', 'status',
            'seized_crystals', 'duration_hours', 'arrested_at', 'release_at',
            'charm_attempts_used', 'last_charm_at',
            'control_transfer', 'time_remaining_seconds',
        ]

    def get_time_remaining_seconds(self, obj):
        from django.utils import timezone
        if obj.status != 'active':
            return 0
        remaining = (obj.release_at - timezone.now()).total_seconds()
        return max(0, int(remaining))


class FactionConversionEventSerializer(serializers.ModelSerializer):
    converted_user = UserBriefSerializer(read_only=True)

    class Meta:
        model = FactionConversionEvent
        fields = [
            'id', 'converted_user', 'from_faction', 'to_faction',
            'charm_attempts_count', 'authority_at_conversion', 'created_at',
        ]


# ─────────────────────────────────────────────
# 加密频道
# ─────────────────────────────────────────────

class EncryptedMessageSerializer(serializers.ModelSerializer):
    sender = UserBriefSerializer(read_only=True)

    class Meta:
        model = EncryptedMessage
        fields = ['id', 'sender', 'content', 'is_system', 'created_at']


class EncryptedChannelSerializer(serializers.ModelSerializer):
    participant_a = UserBriefSerializer(read_only=True)
    participant_b = UserBriefSerializer(read_only=True)
    messages = EncryptedMessageSerializer(many=True, read_only=True)

    class Meta:
        model = EncryptedChannel
        fields = [
            'id', 'participant_a', 'participant_b',
            'is_active', 'created_at', 'messages',
        ]


# ─────────────────────────────────────────────
# 区域聊天
# ─────────────────────────────────────────────

class ZoneChatMessageSerializer(serializers.ModelSerializer):
    sender = UserBriefSerializer(read_only=True)
    tells = serializers.SerializerMethodField()

    class Meta:
        model = ZoneChatMessage
        fields = ['id', 'sender', 'content', 'is_system', 'created_at', 'tells']

    def get_tells(self, obj):
        """附加该消息时间点附近的破绽事件"""
        if obj.sender and not obj.is_system:
            from django.utils import timezone
            from datetime import timedelta
            # 获取消息发送前后5秒内的破绽
            tells = TellEvent.objects.filter(
                player=obj.sender,
                created_at__gte=obj.created_at - timedelta(seconds=5),
                created_at__lte=obj.created_at + timedelta(seconds=5),
            )
            return TellEventSerializer(tells, many=True).data
        return []


# ─────────────────────────────────────────────
# 资源与市场
# ─────────────────────────────────────────────

class CrystalDepositSerializer(serializers.ModelSerializer):
    zone_name = serializers.CharField(source='zone.display_name', read_only=True)

    class Meta:
        model = CrystalDeposit
        fields = ['id', 'zone_name', 'quantity', 'max_quantity', 'respawn_rate_per_hour']


class PlayerCrystalsSerializer(serializers.ModelSerializer):
    class Meta:
        model = PlayerCrystals
        fields = ['raw_crystals', 'purified_crystals', 'updated_at']


class GameMarketRateSerializer(serializers.ModelSerializer):
    class Meta:
        model = GameMarketRate
        fields = [
            'item_slug', 'item_display_name',
            'current_price_crystals', 'base_price_crystals',
            'demand_pressure', 'last_recalculated_at',
        ]


# ─────────────────────────────────────────────
# 道具
# ─────────────────────────────────────────────

class GameItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = GameItem
        fields = [
            'id', 'slug', 'name', 'tier', 'slot', 'description', 'icon',
            'stat_modifiers', 'is_lock_device', 'is_removal_device',
            'is_disguise_item', 'permanent_tell', 'permanent_detectability_bonus',
            'craft_recipe', 'price_crystals', 'available_in_zones',
        ]


class PlayerGameInventorySerializer(serializers.ModelSerializer):
    item = GameItemSerializer(read_only=True)

    class Meta:
        model = PlayerGameInventory
        fields = ['id', 'item', 'quantity', 'obtained_at']


class ActiveDisguiseSerializer(serializers.ModelSerializer):
    outer_layer_item = GameItemSerializer(read_only=True)
    inner_items = GameItemSerializer(many=True, read_only=True)

    class Meta:
        model = ActiveDisguise
        fields = [
            'outer_layer_item', 'inner_items', 'behavioral_mode',
            'computed_detectability', 'computed_disguise_quality',
            'computed_active_tells', 'last_computed_at',
        ]


# ─────────────────────────────────────────────
# 跑商记录
# ─────────────────────────────────────────────

class SmuggleRunSerializer(serializers.ModelSerializer):
    player = UserBriefSerializer(read_only=True)

    class Meta:
        model = SmuggleRun
        fields = [
            'id', 'player', 'status',
            'crystals_collected', 'crystals_delivered', 'crystals_seized',
            'coins_earned', 'started_at', 'completed_at',
        ]


# ─────────────────────────────────────────────
# 综合档案（游戏大厅用）
# ─────────────────────────────────────────────

class GameProfileSerializer(serializers.Serializer):
    """玩家完整游戏档案（聚合视图）"""
    mimic_profile = MimicProfileSerializer(read_only=True)
    patrol_profile = PatrolProfileSerializer(read_only=True)
    crystals = PlayerCrystalsSerializer(read_only=True)
    active_disguise = ActiveDisguiseSerializer(read_only=True)
    current_zone = serializers.SerializerMethodField()
    active_detention = serializers.SerializerMethodField()
    active_control_transfers = serializers.SerializerMethodField()
    has_active_lock = serializers.SerializerMethodField()

    def get_current_zone(self, user):
        presence = user.zone_presence.filter(exited_at__isnull=True).select_related('zone').first()
        if presence:
            return GameZoneSerializer(presence.zone).data
        return None

    def get_active_detention(self, user):
        detention = DetentionRecord.objects.filter(
            prisoner=user, status='active'
        ).first()
        if detention:
            return DetentionRecordSerializer(detention).data
        return None

    def get_active_control_transfers(self, user):
        transfers = GameControlTransfer.objects.filter(
            grantee=user, is_active=True
        ).select_related('lock_task', 'grantor')
        return GameControlTransferSerializer(transfers, many=True).data

    def get_has_active_lock(self, user):
        from tasks.models import LockTask
        return LockTask.objects.filter(
            user=user,
            task_type='lock',
            status__in=['active', 'voting', 'voting_passed']
        ).exists()
