from django.contrib import admin
from .models import (
    ItemType, UserInventory, Item, StoreItem, Purchase,
    Game, GameParticipant, DriftBottle, BuriedTreasure, GameSession
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
    list_display = ['item_type', 'owner', 'status', 'created_at']
    list_filter = ['item_type', 'status', 'created_at']
    search_fields = ['owner__username', 'item_type__name']
    readonly_fields = ['created_at', 'used_at']


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
