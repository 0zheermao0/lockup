from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from store.models import ItemType, Item, StoreItem, UserInventory
from store.serializers import UserInventorySerializer
import json


class Command(BaseCommand):
    help = '诊断小金库按钮不显示的问题'

    def add_arguments(self, parser):
        parser.add_argument(
            '--user-id',
            type=int,
            help='指定要检查的用户ID'
        )

    def handle(self, *args, **options):
        self.stdout.write('🔍 开始诊断小金库问题...')

        # 1. 检查ItemType
        self.stdout.write('\n=== 1. 检查ItemType ===')
        treasury_types = ItemType.objects.filter(display_name='小金库')

        if not treasury_types.exists():
            self.stdout.write(self.style.ERROR('❌ 未找到小金库ItemType'))
            return

        for t in treasury_types:
            self.stdout.write(f'✅ ItemType找到:')
            self.stdout.write(f'   - ID: {t.id}')
            self.stdout.write(f'   - name: "{t.name}"')
            self.stdout.write(f'   - display_name: "{t.display_name}"')
            self.stdout.write(f'   - is_consumable: {t.is_consumable}')

        # 2. 检查StoreItem
        self.stdout.write('\n=== 2. 检查StoreItem ===')
        store_items = StoreItem.objects.filter(name='小金库')

        if not store_items.exists():
            self.stdout.write(self.style.WARNING('⚠️ 未找到小金库StoreItem'))
        else:
            for s in store_items:
                self.stdout.write(f'✅ StoreItem找到:')
                self.stdout.write(f'   - ID: {s.id}')
                self.stdout.write(f'   - name: "{s.name}"')
                self.stdout.write(f'   - item_type.name: "{s.item_type.name}"')
                self.stdout.write(f'   - price: {s.price}')
                self.stdout.write(f'   - is_available: {s.is_available}')

        # 3. 检查用户物品
        self.stdout.write('\n=== 3. 检查用户物品 ===')

        if options['user_id']:
            users = User.objects.filter(id=options['user_id'])
        else:
            # 查找拥有小金库的用户
            users = User.objects.filter(item__item_type__name='little_treasury').distinct()[:3]

        if not users.exists():
            self.stdout.write(self.style.WARNING('⚠️ 未找到拥有小金库的用户'))
            return

        for user in users:
            self.stdout.write(f'\n--- 用户: {user.username} (ID: {user.id}) ---')

            # 检查用户的小金库物品
            treasury_items = Item.objects.filter(
                owner=user,
                item_type__name='little_treasury'
            )

            self.stdout.write(f'小金库物品数量: {treasury_items.count()}')

            for item in treasury_items:
                self.stdout.write(f'  物品 {item.id}:')
                self.stdout.write(f'    - item_type.name: "{item.item_type.name}"')
                self.stdout.write(f'    - item_type.display_name: "{item.item_type.display_name}"')
                self.stdout.write(f'    - status: {item.status}')
                self.stdout.write(f'    - properties: {item.properties}')

            # 4. 检查API序列化数据
            self.stdout.write('\n=== 4. 检查API序列化数据 ===')

            try:
                inventory, created = UserInventory.objects.get_or_create(user=user)
                serializer = UserInventorySerializer(inventory)
                data = serializer.data

                self.stdout.write(f'背包总物品数: {len(data["items"])}')

                treasury_items_in_api = []
                for item in data['items']:
                    if item['item_type']['display_name'] == '小金库':
                        treasury_items_in_api.append(item)

                self.stdout.write(f'API中的小金库物品数: {len(treasury_items_in_api)}')

                for item in treasury_items_in_api:
                    self.stdout.write(f'  API物品:')
                    self.stdout.write(f'    - ID: {item["id"]}')
                    self.stdout.write(f'    - item_type.name: "{item["item_type"]["name"]}"')
                    self.stdout.write(f'    - item_type.display_name: "{item["item_type"]["display_name"]}"')
                    self.stdout.write(f'    - status: {item["status"]}')

                    # 检查前端逻辑条件
                    can_share = (item["status"] == "available" and
                               item["item_type"]["name"] in ["photo", "note", "key", "little_treasury"])
                    can_use_treasury = (item["status"] == "available" and
                                      item["item_type"]["name"] == "little_treasury")

                    self.stdout.write(f'    - 前端canShareItem(): {can_share}')
                    self.stdout.write(f'    - 前端canUseTreasury(): {can_use_treasury}')

            except Exception as e:
                self.stdout.write(self.style.ERROR(f'❌ API序列化出错: {str(e)}'))

        # 5. 总结诊断结果
        self.stdout.write('\n=== 5. 诊断总结 ===')

        treasury_type = treasury_types.first()
        if treasury_type.name != 'little_treasury':
            self.stdout.write(self.style.ERROR(f'❌ ItemType.name错误: "{treasury_type.name}" 应该是 "little_treasury"'))
        else:
            self.stdout.write(self.style.SUCCESS('✅ ItemType.name正确'))

        active_items = Item.objects.filter(
            item_type__name='little_treasury',
            status='available'
        ).count()

        self.stdout.write(f'✅ 系统中可用的小金库物品总数: {active_items}')

        if active_items == 0:
            self.stdout.write(self.style.WARNING('⚠️ 没有可用状态的小金库物品'))

        self.stdout.write('\n🔍 诊断完成')