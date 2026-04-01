from django.contrib import admin
from .models import (
    GameZone, PlayerZonePresence, MimicProfile, PatrolProfile,
    TellEvent, CheckpointSession, CheckpointParticipant, InterrogationRequest,
    GrayMarketTransaction, GameControlTransfer, DetentionRecord,
    FactionConversionEvent, EncryptedChannel, EncryptedMessage,
    ZoneChatMessage, CrystalDeposit, PlayerCrystals, GameMarketRate,
    GameItem, PlayerGameInventory, ActiveDisguise, SmuggleRun,
)


@admin.register(GameZone)
class GameZoneAdmin(admin.ModelAdmin):
    list_display = ['name', 'display_name', 'crystal_respawn_rate', 'max_players']
    list_editable = ['crystal_respawn_rate']


@admin.register(PlayerZonePresence)
class PlayerZonePresenceAdmin(admin.ModelAdmin):
    list_display = ['user', 'zone', 'entered_at', 'exited_at']
    list_filter = ['zone']
    search_fields = ['user__username']


@admin.register(MimicProfile)
class MimicProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'current_faction', 'depilation_charge', 'suppression_value',
                    'purity_score', 'femboy_score', 'total_successful_runs']
    list_filter = ['current_faction']
    search_fields = ['user__username']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(PatrolProfile)
class PatrolProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'current_faction', 'authority_value', 'reputation_score',
                    'inspection_tokens', 'total_arrests', 'false_accusations']
    list_filter = ['current_faction']
    search_fields = ['user__username']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(TellEvent)
class TellEventAdmin(admin.ModelAdmin):
    list_display = ['player', 'tell_type', 'zone', 'action_type', 'created_at']
    list_filter = ['tell_type', 'zone']
    search_fields = ['player__username']
    readonly_fields = ['created_at']


@admin.register(CheckpointSession)
class CheckpointSessionAdmin(admin.ModelAdmin):
    list_display = ['id', 'zone', 'status', 'npc_count', 'opened_at', 'closed_at']
    list_filter = ['status', 'zone']
    readonly_fields = ['opened_at']


@admin.register(CheckpointParticipant)
class CheckpointParticipantAdmin(admin.ModelAdmin):
    list_display = ['user', 'session', 'role', 'outcome', 'entered_at']
    list_filter = ['role', 'outcome']
    search_fields = ['user__username']


@admin.register(InterrogationRequest)
class InterrogationRequestAdmin(admin.ModelAdmin):
    list_display = ['interrogator', 'target', 'status', 'response_time_seconds',
                    'triggered_pause_tell', 'created_at']
    list_filter = ['status', 'triggered_pause_tell']
    search_fields = ['interrogator__username', 'target__username']


@admin.register(GrayMarketTransaction)
class GrayMarketTransactionAdmin(admin.ModelAdmin):
    list_display = ['transaction_type', 'initiator', 'recipient', 'status',
                    'escrowed_crystals', 'created_at']
    list_filter = ['transaction_type', 'status']
    search_fields = ['initiator__username', 'recipient__username']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(GameControlTransfer)
class GameControlTransferAdmin(admin.ModelAdmin):
    list_display = ['grantee', 'grantor', 'source', 'duration_hours',
                    'is_active', 'expires_at']
    list_filter = ['source', 'is_active']
    search_fields = ['grantee__username', 'grantor__username']
    readonly_fields = ['created_at']


@admin.register(DetentionRecord)
class DetentionRecordAdmin(admin.ModelAdmin):
    list_display = ['prisoner', 'captor', 'status', 'duration_hours',
                    'seized_crystals', 'arrested_at', 'release_at']
    list_filter = ['status']
    search_fields = ['prisoner__username', 'captor__username']
    readonly_fields = ['arrested_at']


@admin.register(FactionConversionEvent)
class FactionConversionEventAdmin(admin.ModelAdmin):
    list_display = ['converted_user', 'from_faction', 'to_faction',
                    'charm_attempts_count', 'created_at']
    list_filter = ['from_faction', 'to_faction']
    readonly_fields = ['created_at']


@admin.register(CrystalDeposit)
class CrystalDepositAdmin(admin.ModelAdmin):
    list_display = ['zone', 'quantity', 'max_quantity', 'respawn_rate_per_hour',
                    'last_harvested_at']
    list_filter = ['zone']
    list_editable = ['max_quantity', 'respawn_rate_per_hour']


@admin.register(PlayerCrystals)
class PlayerCrystalsAdmin(admin.ModelAdmin):
    list_display = ['user', 'raw_crystals', 'purified_crystals', 'updated_at']
    search_fields = ['user__username']


@admin.register(GameMarketRate)
class GameMarketRateAdmin(admin.ModelAdmin):
    list_display = ['item_slug', 'item_display_name', 'current_price_crystals',
                    'base_price_crystals', 'demand_pressure']
    list_editable = ['base_price_crystals']


@admin.register(GameItem)
class GameItemAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'tier', 'slot', 'price_crystals',
                    'is_lock_device', 'is_removal_device', 'is_active']
    list_filter = ['tier', 'slot', 'is_active', 'is_lock_device', 'is_removal_device']
    search_fields = ['name', 'slug']
    list_editable = ['price_crystals', 'is_active']


@admin.register(PlayerGameInventory)
class PlayerGameInventoryAdmin(admin.ModelAdmin):
    list_display = ['user', 'item', 'quantity', 'obtained_at']
    search_fields = ['user__username', 'item__name']


@admin.register(ActiveDisguise)
class ActiveDisguiseAdmin(admin.ModelAdmin):
    list_display = ['user', 'behavioral_mode', 'computed_detectability',
                    'computed_disguise_quality', 'last_computed_at']
    search_fields = ['user__username']


@admin.register(SmuggleRun)
class SmuggleRunAdmin(admin.ModelAdmin):
    list_display = ['player', 'status', 'crystals_collected', 'crystals_delivered',
                    'crystals_seized', 'coins_earned', 'started_at']
    list_filter = ['status']
    search_fields = ['player__username']
    readonly_fields = ['started_at']
