from rest_framework import serializers
from .models import (
    ItemType, UserInventory, Item, StoreItem, Purchase,
    Game, GameParticipant, DriftBottle, BuriedTreasure, GameSession
)
from users.serializers import UserSerializer


class ItemTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = ItemType
        fields = '__all__'


class ItemSerializer(serializers.ModelSerializer):
    item_type = ItemTypeSerializer(read_only=True)
    owner = UserSerializer(read_only=True)
    original_creator = serializers.SerializerMethodField()

    class Meta:
        model = Item
        fields = '__all__'

    def get_original_creator(self, obj):
        """获取物品的原始创建者（通过购买记录追溯）"""
        try:
            # 通过Purchase记录找到原始购买者
            purchase = obj.purchase.first()
            if purchase and purchase.user:
                return UserSerializer(purchase.user).data
            return None
        except:
            return None


class UserInventorySerializer(serializers.ModelSerializer):
    items = ItemSerializer(many=True, read_only=True)
    max_slots = serializers.ReadOnlyField()
    used_slots = serializers.ReadOnlyField()
    available_slots = serializers.ReadOnlyField()

    class Meta:
        model = UserInventory
        fields = ['user', 'items', 'max_slots', 'used_slots', 'available_slots', 'created_at', 'updated_at']


class StoreItemSerializer(serializers.ModelSerializer):
    item_type = ItemTypeSerializer(read_only=True)

    class Meta:
        model = StoreItem
        fields = '__all__'


class PurchaseSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    store_item = StoreItemSerializer(read_only=True)
    item = ItemSerializer(read_only=True)

    class Meta:
        model = Purchase
        fields = '__all__'


class GameParticipantSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)

    class Meta:
        model = GameParticipant
        fields = '__all__'


class GameSerializer(serializers.ModelSerializer):
    creator = UserSerializer(read_only=True)
    participants = GameParticipantSerializer(many=True, read_only=True, source='gameparticipant_set')

    class Meta:
        model = Game
        fields = '__all__'


class DriftBottleSerializer(serializers.ModelSerializer):
    sender = UserSerializer(read_only=True)
    finder = UserSerializer(read_only=True)
    items = ItemSerializer(many=True, read_only=True)

    class Meta:
        model = DriftBottle
        fields = '__all__'


class BuriedTreasureSerializer(serializers.ModelSerializer):
    burier = UserSerializer(read_only=True)
    finder = UserSerializer(read_only=True)
    item = ItemSerializer(read_only=True)

    class Meta:
        model = BuriedTreasure
        fields = '__all__'


class GameSessionSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)

    class Meta:
        model = GameSession
        fields = '__all__'


# Create serializers for specific actions
class PurchaseItemSerializer(serializers.Serializer):
    store_item_id = serializers.UUIDField()


class TimeWheelPlaySerializer(serializers.Serializer):
    bet_amount = serializers.IntegerField(min_value=1, max_value=10)
    task_id = serializers.UUIDField()


class JoinGameSerializer(serializers.Serializer):
    action = serializers.JSONField(required=False, default=dict)


class CreateDriftBottleSerializer(serializers.Serializer):
    message = serializers.CharField(max_length=1000)
    item_ids = serializers.ListField(
        child=serializers.UUIDField(),
        required=False,
        allow_empty=True
    )


class UploadPhotoSerializer(serializers.Serializer):
    """上传照片到相纸"""
    paper_item_id = serializers.UUIDField()
    photo = serializers.ImageField()


class BuryItemSerializer(serializers.Serializer):
    """掩埋物品序列化器"""
    item_id = serializers.UUIDField()
    location_zone = serializers.CharField(max_length=50)
    location_hint = serializers.CharField(max_length=200)


class ExploreZoneSerializer(serializers.Serializer):
    """探索区域序列化器"""
    zone_name = serializers.CharField(max_length=50)
    card_position = serializers.IntegerField(min_value=0, required=False)


class FindTreasureSerializer(serializers.Serializer):
    """发现宝物序列化器"""
    treasure_id = serializers.UUIDField()