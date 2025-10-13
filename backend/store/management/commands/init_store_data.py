"""
Django管理命令：初始化商店和道具系统的基础数据

用法：
    python manage.py init_store_data

这个命令会创建系统运行所需的基础数据：
- 所有道具类型 (ItemType)
- 基础商店商品 (StoreItem)

该命令是幂等的，可以安全地重复运行。
"""

from django.core.management.base import BaseCommand
from django.db import transaction
from store.models import ItemType, StoreItem


class Command(BaseCommand):
    help = '初始化商店和道具系统的基础数据'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='强制重新创建所有数据（会删除现有数据）',
        )

    def handle(self, *args, **options):
        force = options['force']

        with transaction.atomic():
            # 初始化道具类型
            self.init_item_types(force)

            # 初始化商店商品
            self.init_store_items(force)

        self.stdout.write(
            self.style.SUCCESS('✅ 所有基础数据初始化完成！')
        )

    def init_item_types(self, force=False):
        """初始化道具类型"""
        self.stdout.write('🔧 初始化道具类型...')

        # 定义所有道具类型的详细信息
        item_types_data = [
            {
                'name': 'photo_paper',
                'display_name': '相纸',
                'description': '用于拍摄照片的相纸，可以记录美好瞬间',
                'icon': '📸',
                'is_consumable': True
            },
            {
                'name': 'photo',
                'display_name': '照片',
                'description': '记录了特殊时刻的照片，具有纪念价值',
                'icon': '🖼️',
                'is_consumable': False
            },
            {
                'name': 'drift_bottle',
                'display_name': '漂流瓶',
                'description': '可以装载消息和物品的神秘漂流瓶，能够穿越时空传递心意',
                'icon': '🍾',
                'is_consumable': True
            },
            {
                'name': 'key',
                'display_name': '钥匙',
                'description': '用于解锁带锁任务的特殊钥匙，每个任务都有唯一的钥匙',
                'icon': '🗝️',
                'is_consumable': True
            },
            {
                'name': 'note',
                'display_name': '纸条',
                'description': '记录文字信息的纸条，可以传递秘密消息',
                'icon': '📝',
                'is_consumable': False
            }
        ]

        created_count = 0
        updated_count = 0

        for item_data in item_types_data:
            item_type, created = ItemType.objects.get_or_create(
                name=item_data['name'],
                defaults={
                    'display_name': item_data['display_name'],
                    'description': item_data['description'],
                    'icon': item_data['icon'],
                    'is_consumable': item_data['is_consumable']
                }
            )

            if created:
                created_count += 1
                self.stdout.write(f'  ✅ 创建道具类型: {item_type.display_name} ({item_type.name})')
            else:
                # 如果是force模式或者数据不完整，更新现有记录
                updated = False
                if force or not item_type.description:
                    for field, value in item_data.items():
                        if field != 'name':  # name是唯一键，不更新
                            if getattr(item_type, field) != value:
                                setattr(item_type, field, value)
                                updated = True

                    if updated:
                        item_type.save()
                        updated_count += 1
                        self.stdout.write(f'  🔄 更新道具类型: {item_type.display_name} ({item_type.name})')
                    else:
                        self.stdout.write(f'  ✓ 道具类型已存在: {item_type.display_name} ({item_type.name})')
                else:
                    self.stdout.write(f'  ✓ 道具类型已存在: {item_type.display_name} ({item_type.name})')

        self.stdout.write(f'📊 道具类型初始化完成: 新创建 {created_count} 个，更新 {updated_count} 个')

    def init_store_items(self, force=False):
        """初始化商店商品"""
        self.stdout.write('🛒 初始化商店商品...')

        # 确保所有ItemType都存在
        try:
            photo_paper_type = ItemType.objects.get(name='photo_paper')
            key_type = ItemType.objects.get(name='key')
            drift_bottle_type = ItemType.objects.get(name='drift_bottle')
            note_type = ItemType.objects.get(name='note')
        except ItemType.DoesNotExist as e:
            self.stdout.write(
                self.style.ERROR(f'❌ 道具类型不存在: {e}')
            )
            return

        # 定义商店商品
        store_items_data = [
            {
                'item_type': photo_paper_type,
                'name': '相纸',
                'description': '高质量的拍照相纸，让你的照片更加清晰美丽',
                'price': 5,
                'icon': '📸',
                'is_available': True,
                'stock': None,  # 无限库存
                'daily_limit': 10,
                'level_requirement': 1
            },
            {
                'item_type': key_type,
                'name': '通用钥匙',
                'description': '神秘的万能钥匙，在紧急情况下可以解锁任何带锁任务（价格较高，谨慎使用）',
                'price': 50,
                'icon': '🗝️',
                'is_available': True,
                'stock': None,
                'daily_limit': 3,
                'level_requirement': 2
            },
            {
                'item_type': drift_bottle_type,
                'name': '漂流瓶',
                'description': '装载着希望与梦想的漂流瓶，可以将你的消息送给未知的朋友',
                'price': 15,
                'icon': '🍾',
                'is_available': True,
                'stock': None,
                'daily_limit': 5,
                'level_requirement': 1
            },
            {
                'item_type': note_type,
                'name': '留言纸条',
                'description': '精美的留言纸条，适合写下重要的话语或秘密',
                'price': 3,
                'icon': '📝',
                'is_available': True,
                'stock': None,
                'daily_limit': 20,
                'level_requirement': 1
            }
        ]

        created_count = 0
        updated_count = 0

        for item_data in store_items_data:
            # 使用name和item_type作为唯一标识
            store_item, created = StoreItem.objects.get_or_create(
                name=item_data['name'],
                item_type=item_data['item_type'],
                defaults={
                    'description': item_data['description'],
                    'price': item_data['price'],
                    'icon': item_data['icon'],
                    'is_available': item_data['is_available'],
                    'stock': item_data['stock'],
                    'daily_limit': item_data['daily_limit'],
                    'level_requirement': item_data['level_requirement']
                }
            )

            if created:
                created_count += 1
                self.stdout.write(f'  ✅ 创建商店商品: {store_item.name} - {store_item.price}积分')
            else:
                # 如果是force模式，更新现有记录
                if force:
                    updated = False
                    for field, value in item_data.items():
                        if field not in ['name', 'item_type']:  # 这些是唯一键，不更新
                            if getattr(store_item, field) != value:
                                setattr(store_item, field, value)
                                updated = True

                    if updated:
                        store_item.save()
                        updated_count += 1
                        self.stdout.write(f'  🔄 更新商店商品: {store_item.name} - {store_item.price}积分')
                    else:
                        self.stdout.write(f'  ✓ 商店商品已存在: {store_item.name} - {store_item.price}积分')
                else:
                    self.stdout.write(f'  ✓ 商店商品已存在: {store_item.name} - {store_item.price}积分')

        self.stdout.write(f'📊 商店商品初始化完成: 新创建 {created_count} 个，更新 {updated_count} 个')

    def print_summary(self):
        """打印当前数据库状态摘要"""
        self.stdout.write('📋 当前数据库状态摘要:')

        # ItemType统计
        item_type_count = ItemType.objects.count()
        self.stdout.write(f'  道具类型: {item_type_count} 个')
        for item_type in ItemType.objects.all():
            self.stdout.write(f'    - {item_type.display_name} ({item_type.name}) {item_type.icon}')

        # StoreItem统计
        store_item_count = StoreItem.objects.count()
        self.stdout.write(f'  商店商品: {store_item_count} 个')
        for store_item in StoreItem.objects.all():
            self.stdout.write(f'    - {store_item.name}: {store_item.price}积分 ({store_item.item_type.name})')