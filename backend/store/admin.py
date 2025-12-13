from django.contrib import admin
from .models import (
    ItemType, UserInventory, Item, StoreItem, Purchase,
    Game, GameParticipant, DriftBottle, BuriedTreasure, GameSession, SharedItem
)


@admin.register(ItemType)
class ItemTypeAdmin(admin.ModelAdmin):
    list_display = ['name', 'display_name', 'icon', 'is_consumable', 'created_at']
    list_filter = ['is_consumable', 'created_at']
    search_fields = ['name', 'display_name']


class ItemInline(admin.TabularInline):
    model = Item
    extra = 0
    readonly_fields = ['created_at']


@admin.register(UserInventory)
class UserInventoryAdmin(admin.ModelAdmin):
    list_display = ['user', 'used_slots', 'max_slots', 'available_slots', 'created_at']
    list_filter = ['created_at']
    search_fields = ['user__username', 'user__email']
    inlines = [ItemInline]


@admin.register(Item)
class ItemAdmin(admin.ModelAdmin):
    list_display = ['item_type', 'owner', 'original_owner', 'status', 'inventory', 'created_at']
    list_filter = ['item_type', 'status', 'created_at']
    search_fields = ['owner__username', 'original_owner__username', 'item_type__name']
    readonly_fields = ['created_at', 'used_at']

    fieldsets = (
        ('基本信息', {
            'fields': ('item_type', 'owner', 'original_owner', 'status', 'inventory')
        }),
        ('物品属性', {
            'fields': ('properties',),
            'classes': ('collapse',)
        }),
        ('时间信息', {
            'fields': ('created_at', 'used_at')
        }),
    )

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('item_type', 'owner', 'original_owner', 'inventory')


@admin.register(StoreItem)
class StoreItemAdmin(admin.ModelAdmin):
    list_display = ['name', 'item_type', 'price', 'is_available', 'stock', 'level_requirement']
    list_filter = ['item_type', 'is_available', 'level_requirement', 'created_at']
    search_fields = ['name', 'item_type__name']


@admin.register(Purchase)
class PurchaseAdmin(admin.ModelAdmin):
    list_display = ['user', 'store_item', 'price_paid', 'created_at']
    list_filter = ['created_at', 'store_item__item_type']
    search_fields = ['user__username', 'store_item__name']
    readonly_fields = ['created_at']


class GameParticipantInline(admin.TabularInline):
    model = GameParticipant
    extra = 0


@admin.register(Game)
class GameAdmin(admin.ModelAdmin):
    list_display = ['game_type', 'creator', 'status', 'bet_amount', 'created_at']
    list_filter = ['game_type', 'status', 'created_at']
    search_fields = ['creator__username']
    inlines = [GameParticipantInline]


@admin.register(DriftBottle)
class DriftBottleAdmin(admin.ModelAdmin):
    list_display = ['sender', 'finder', 'status', 'created_at', 'expires_at']
    list_filter = ['status', 'created_at']
    search_fields = ['sender__username', 'finder__username']


@admin.register(BuriedTreasure)
class BuriedTreasureAdmin(admin.ModelAdmin):
    list_display = ['burier', 'finder', 'item', 'location_zone', 'difficulty', 'status']
    list_filter = ['difficulty', 'status', 'created_at']
    search_fields = ['burier__username', 'finder__username', 'location_zone']


@admin.register(GameSession)
class GameSessionAdmin(admin.ModelAdmin):
    list_display = ['user', 'game_type', 'bet_amount', 'created_at']
    list_filter = ['game_type', 'created_at']
    search_fields = ['user__username']
    readonly_fields = ['created_at']


@admin.register(SharedItem)
class SharedItemAdmin(admin.ModelAdmin):
    """分享物品管理"""
    list_display = ['sharer', 'item', 'status', 'share_token_short', 'claimer', 'created_at', 'expires_at']
    list_filter = ['status', 'created_at', 'expires_at']
    search_fields = ['sharer__username', 'claimer__username', 'item__item_type__name', 'share_token']
    readonly_fields = ['share_token', 'created_at', 'claimed_at']
    ordering = ['-created_at']

    fieldsets = (
        ('基本信息', {
            'fields': ('sharer', 'item', 'status', 'share_token')
        }),
        ('分享设置', {
            'fields': ('expires_at',)
        }),
        ('领取信息', {
            'fields': ('claimer', 'claimed_at'),
            'classes': ('collapse',)
        }),
        ('时间信息', {
            'fields': ('created_at',)
        }),
    )

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('sharer', 'claimer', 'item', 'item__item_type')

    def share_token_short(self, obj):
        """显示分享令牌的前8位"""
        if obj.share_token:
            return f"{obj.share_token[:8]}..."
        return "-"
    share_token_short.short_description = '分享令牌'
