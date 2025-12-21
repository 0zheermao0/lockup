from django.core.management.base import BaseCommand
from store.models import ItemType, StoreItem


class Command(BaseCommand):
    help = '修复小金库道具类型的name字段错误'

    def handle(self, *args, **options):
        self.stdout.write('🔧 开始修复小金库道具类型...')

        try:
            # 查找name为'-'且display_name为'小金库'的ItemType
            treasury_item_type = ItemType.objects.filter(
                name='-',
                display_name='小金库'
            ).first()

            if treasury_item_type:
                self.stdout.write(f'找到错误的小金库道具类型: name="{treasury_item_type.name}", display_name="{treasury_item_type.display_name}"')

                # 修复name字段
                treasury_item_type.name = 'little_treasury'
                treasury_item_type.save()

                self.stdout.write(
                    self.style.SUCCESS(f'✅ 成功修复小金库道具类型: name="{treasury_item_type.name}"')
                )

                # 同时检查并修复相关的StoreItem
                store_items = StoreItem.objects.filter(item_type=treasury_item_type)
                for store_item in store_items:
                    self.stdout.write(f'找到相关商店物品: {store_item.name}')

                self.stdout.write(
                    self.style.SUCCESS(f'✅ 修复完成！涉及 {store_items.count()} 个商店物品')
                )

            else:
                # 检查是否已经存在正确的小金库类型
                correct_treasury = ItemType.objects.filter(name='little_treasury').first()
                if correct_treasury:
                    self.stdout.write(
                        self.style.SUCCESS('✅ 小金库道具类型已经是正确的')
                    )
                else:
                    self.stdout.write(
                        self.style.WARNING('⚠️ 未找到小金库道具类型，请运行 init_store_data 命令')
                    )

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ 修复过程中出错: {str(e)}')
            )

        self.stdout.write('🔧 修复过程完成')