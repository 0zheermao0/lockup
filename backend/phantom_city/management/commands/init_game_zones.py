"""
初始化男娘幻城游戏区域数据。
使用 get_or_create 保证幂等，可重复运行。
"""
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = '初始化男娘幻城游戏区域（GameZone）和备皮间矿点（CrystalDeposit）'

    def handle(self, *args, **options):
        from phantom_city.models import GameZone, CrystalDeposit

        zones_data = [
            {
                'name': 'salon',
                'display_name': '闺房',
                'description': '小男娘的安全区。黑市交易、补觉降压抑、补充物资的据点。',
                'crystal_respawn_rate': 0,
            },
            {
                'name': 'checkpoint',
                'display_name': '安检口',
                'description': '必经之路。小s把守，每次穿越都是一场博弈。',
                'crystal_respawn_rate': 0,
            },
            {
                'name': 'ruins',
                'display_name': '备皮间',
                'description': '原初刀具产地。环境危险，发毛值持续攀升，但收益丰厚。',
                'crystal_respawn_rate': 3,
            },
            {
                'name': 'control_room',
                'display_name': '禁闭室',
                'description': '被捕者的收押区。完成任务可减少收押时间，或尝试哄骗看守。',
                'crystal_respawn_rate': 0,
            },
            {
                'name': 'black_market',
                'display_name': '黑市',
                'description': '闺房外围的地下交易网络。没有小s的眼线，但交易风险自担。',
                'crystal_respawn_rate': 0,
            },
            {
                'name': 'abandoned_camp',
                'display_name': '更衣室',
                'description': '安检口与备皮间之间的废弃驻扎点。可以短暂补觉，但不如闺房安全。',
                'crystal_respawn_rate': 0,
            },
            {
                'name': 'ruins_deep',
                'display_name': '深处备皮间',
                'description': '污染最严重的核心地带。原初刀具密度极高，但发毛值积累速度翻倍。',
                'crystal_respawn_rate': 6,
            },
            {
                'name': 'interrogation_room',
                'display_name': '审问室',
                'description': '安检口内的封闭盘问间。被强制盘问时由系统移入。',
                'crystal_respawn_rate': 0,
            },
            {
                'name': 'armory',
                'display_name': '储物柜',
                'description': '闺房的军备仓库。绕过安检口的暗道入口就在这里，但物资全部高价。',
                'crystal_respawn_rate': 0,
            },
            {
                'name': 'sewer',
                'display_name': '下水道',
                'description': '贯通城市地下的腐蚀性排水网络。最快的路——但污染环境会立即推高发毛值（+10）。',
                'crystal_respawn_rate': 0,
            },
            {
                'name': 'ruins_outer',
                'display_name': '外围备皮间',
                'description': '备皮间的外缘地带。可从下水道入场，少量刀具矿点，与更衣室横向互通。',
                'crystal_respawn_rate': 2,
            },
        ]

        for data in zones_data:
            zone, created = GameZone.objects.get_or_create(
                name=data['name'],
                defaults={
                    'display_name': data['display_name'],
                    'description': data['description'],
                    'crystal_respawn_rate': data['crystal_respawn_rate'],
                }
            )
            status = '已创建' if created else '已存在'
            self.stdout.write(f'  {status}：{zone.display_name}（{zone.name}）')

        # 初始化备皮间矿点（目标3个）
        ruins = GameZone.objects.get(name='ruins')
        existing = CrystalDeposit.objects.filter(zone=ruins).count()
        deposits_created = 0
        while CrystalDeposit.objects.filter(zone=ruins).count() < 3:
            CrystalDeposit.objects.create(
                zone=ruins,
                quantity=20,
                max_quantity=20,
                respawn_rate_per_hour=3,
            )
            deposits_created += 1

        total_deposits = CrystalDeposit.objects.filter(zone=ruins).count()
        self.stdout.write(f'  备皮间矿点：共 {total_deposits} 个（本次新建 {deposits_created} 个）')

        # 初始化深处备皮间矿点（目标3个，高密度 respawn_rate=6）
        ruins_deep = GameZone.objects.get(name='ruins_deep')
        deep_created = 0
        while CrystalDeposit.objects.filter(zone=ruins_deep).count() < 3:
            CrystalDeposit.objects.create(
                zone=ruins_deep,
                quantity=15,
                max_quantity=15,
                respawn_rate_per_hour=6,
            )
            deep_created += 1

        total_deep = CrystalDeposit.objects.filter(zone=ruins_deep).count()
        self.stdout.write(f'  深处备皮间矿点：共 {total_deep} 个（本次新建 {deep_created} 个）')

        # 初始化外围备皮间矿点（目标2个，respawn_rate=2）
        try:
            ruins_outer = GameZone.objects.get(name='ruins_outer')
            outer_created = 0
            while CrystalDeposit.objects.filter(zone=ruins_outer).count() < 2:
                CrystalDeposit.objects.create(
                    zone=ruins_outer,
                    quantity=10,
                    max_quantity=10,
                    respawn_rate_per_hour=2,
                )
                outer_created += 1
            total_outer = CrystalDeposit.objects.filter(zone=ruins_outer).count()
            self.stdout.write(f'  外围备皮间矿点：共 {total_outer} 个（本次新建 {outer_created} 个）')
        except GameZone.DoesNotExist:
            self.stdout.write('  外围备皮间区域未找到，跳过矿点初始化')

        self.stdout.write(self.style.SUCCESS('男娘幻城区域初始化完成！'))
