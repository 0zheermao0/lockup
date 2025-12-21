from django.core.management.base import BaseCommand
from store.models import ItemType
from django.db import connection


class Command(BaseCommand):
    help = '精确检查小金库数据的真实情况'

    def handle(self, *args, **options):
        self.stdout.write('🔍 精确检查小金库数据...')

        # 1. 使用 Django ORM 查询
        self.stdout.write('\n=== Django ORM 查询 ===')
        treasury_items = ItemType.objects.filter(display_name='小金库')

        for item in treasury_items:
            self.stdout.write(f'ID: {item.id}')
            self.stdout.write(f'name: "{item.name}" (长度: {len(item.name)})')
            self.stdout.write(f'display_name: "{item.display_name}"')
            self.stdout.write(f'name 的字符码: {[ord(c) for c in item.name]}')

            # 检查 name 字段是否真的是 'little_treasury'
            if item.name == 'little_treasury':
                self.stdout.write('✅ name 字段确实是 "little_treasury"')
            elif item.name == '-':
                self.stdout.write('❌ name 字段是 "-"')
            elif item.name == '':
                self.stdout.write('❌ name 字段是空字符串')
            elif item.name is None:
                self.stdout.write('❌ name 字段是 None')
            else:
                self.stdout.write(f'❓ name 字段是其他值: "{repr(item.name)}"')

        # 2. 使用原生 SQL 查询
        self.stdout.write('\n=== 原生 SQL 查询 ===')
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT id, name, display_name
                FROM store_itemtype
                WHERE display_name = '小金库'
            """)

            for row in cursor.fetchall():
                item_id, name, display_name = row
                self.stdout.write(f'SQL 结果:')
                self.stdout.write(f'  ID: {item_id}')
                self.stdout.write(f'  name: "{name}" (长度: {len(name) if name else 0})')
                self.stdout.write(f'  display_name: "{display_name}"')

                if name:
                    self.stdout.write(f'  name 的字符码: {[ord(c) for c in name]}')

                # 检查 name 字段的真实值
                if name == 'little_treasury':
                    self.stdout.write('  ✅ SQL: name 字段确实是 "little_treasury"')
                elif name == '-':
                    self.stdout.write('  ❌ SQL: name 字段是 "-"')
                elif name == '' or name is None:
                    self.stdout.write('  ❌ SQL: name 字段是空/None')
                else:
                    self.stdout.write(f'  ❓ SQL: name 字段是其他值: "{repr(name)}"')

        # 3. 检查前端逻辑
        self.stdout.write('\n=== 前端逻辑检查 ===')
        for item in treasury_items:
            # 模拟前端的检查逻辑
            can_share = item.name in ['photo', 'note', 'key', 'little_treasury']
            can_use_treasury = item.name == 'little_treasury'

            self.stdout.write(f'对于 name="{item.name}":')
            self.stdout.write(f'  canShareItem 会返回: {can_share}')
            self.stdout.write(f'  canUseTreasury 会返回: {can_use_treasury}')

            if not can_share or not can_use_treasury:
                self.stdout.write('  ❌ 这就是为什么按钮不显示的原因！')
            else:
                self.stdout.write('  ✅ 按钮应该显示')

        self.stdout.write('\n🔍 检查完成')