#!/usr/bin/env python3
"""
Django管理命令：手动处理等级晋升

使用方法：
    python manage.py process_level_promotions                    # 处理所有符合条件的用户
    python manage.py process_level_promotions --user-id 123     # 只处理指定用户
    python manage.py process_level_promotions --dry-run         # 预览模式，不实际执行
    python manage.py process_level_promotions --batch-size 500  # 自定义批处理大小
    python manage.py process_level_promotions --level 2         # 只处理特定等级的用户
    python manage.py process_level_promotions --force           # 强制处理，忽略一些限制
"""

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone
from users.models import User, UserLevelUpgrade
from users.services.level_promotion import LevelPromotionService
import sys


class Command(BaseCommand):
    help = '手动处理用户等级晋升'

    def add_arguments(self, parser):
        parser.add_argument(
            '--user-id',
            type=int,
            help='只处理指定用户ID的等级晋升'
        )

        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='预览模式，显示哪些用户符合晋升条件但不实际执行'
        )

        parser.add_argument(
            '--batch-size',
            type=int,
            default=1000,
            help='批处理大小，默认1000'
        )

        parser.add_argument(
            '--level',
            type=int,
            choices=[1, 2, 3],
            help='只处理指定当前等级的用户（1, 2, 或 3）'
        )

        parser.add_argument(
            '--force',
            action='store_true',
            help='强制处理模式，忽略一些限制'
        )

        parser.add_argument(
            '--verbose',
            action='store_true',
            help='显示详细信息'
        )

    def handle(self, *args, **options):
        self.stdout.write(
            self.style.SUCCESS('🎯 开始处理用户等级晋升...\n')
        )

        start_time = timezone.now()

        try:
            if options['user_id']:
                # 处理单个用户
                result = self._process_single_user(options)
            else:
                # 批量处理用户
                result = self._process_batch_users(options)

            self._print_summary(result, start_time, options)

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ 处理过程中发生错误: {str(e)}')
            )
            if options['verbose']:
                import traceback
                self.stdout.write(traceback.format_exc())
            sys.exit(1)

    def _process_single_user(self, options):
        """处理单个用户的等级晋升"""
        user_id = options['user_id']
        dry_run = options['dry_run']
        verbose = options['verbose']

        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            raise CommandError(f'用户ID {user_id} 不存在')

        self.stdout.write(f'🔍 检查用户: {user.username} (ID: {user.id}, 当前等级: {user.level})')

        # 检查是否符合晋升条件
        target_level = user.check_level_promotion_eligibility()

        if target_level is None:
            self.stdout.write(
                self.style.WARNING(f'   ⚠️  用户 {user.username} 暂不符合晋升条件')
            )

            if verbose:
                # 显示详细的晋升要求
                if user.level < 4:
                    next_level = user.level + 1
                    requirements = user.get_level_promotion_requirements(next_level)
                    self.stdout.write(f'   📋 升级到{next_level}级的要求:')

                    # 检查各项要求
                    req_checks = [
                        ('活跃度积分', user.activity_score, requirements.get('activity_score', 0)),
                        ('发布动态总数', user.total_posts, requirements.get('total_posts', 0)),
                        ('收到点赞总数', user.total_likes_received, requirements.get('total_likes_received', 0)),
                        ('带锁时长', user.get_total_lock_duration() / 60, requirements.get('lock_duration_hours', 0)),  # 转换为小时
                    ]

                    # 如果是4级，还需要检查任务完成率
                    if next_level == 4:
                        req_checks.append(('任务完成率', user.get_task_completion_rate(), requirements.get('task_completion_rate', 0)))

                    for req_name, current, required in req_checks:
                        status = '✅' if current >= required else '❌'
                        if req_name == '带锁时长':
                            self.stdout.write(f'      {status} {req_name}: {current:.1f}小时/{required}小时')
                        elif req_name == '任务完成率':
                            self.stdout.write(f'      {status} {req_name}: {current:.1f}%/{required}%')
                        else:
                            self.stdout.write(f'      {status} {req_name}: {current}/{required}')
                else:
                    self.stdout.write(f'   🏆 用户已是最高等级')

            return {
                'processed': 1,
                'promoted': 0,
                'errors': 0,
                'skipped': 1,
                'details': []
            }

        if dry_run:
            self.stdout.write(
                self.style.SUCCESS(f'   ✨ [预览] 用户 {user.username} 可以从 {user.level} 级晋升到 {target_level} 级')
            )
            return {
                'processed': 1,
                'promoted': 0,
                'errors': 0,
                'skipped': 0,
                'details': [{'user': user.username, 'from_level': user.level, 'to_level': target_level, 'action': 'preview'}]
            }

        # 执行晋升
        try:
            with transaction.atomic():
                user.promote_to_level(target_level, reason='manual_command')

            self.stdout.write(
                self.style.SUCCESS(f'   ✅ 用户 {user.username} 成功从 {user.level - 1} 级晋升到 {user.level} 级')
            )

            return {
                'processed': 1,
                'promoted': 1,
                'errors': 0,
                'skipped': 0,
                'details': [{'user': user.username, 'from_level': user.level - 1, 'to_level': user.level, 'action': 'promoted'}]
            }

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'   ❌ 晋升用户 {user.username} 时发生错误: {str(e)}')
            )
            return {
                'processed': 1,
                'promoted': 0,
                'errors': 1,
                'skipped': 0,
                'details': []
            }

    def _process_batch_users(self, options):
        """批量处理用户等级晋升"""
        batch_size = options['batch_size']
        dry_run = options['dry_run']
        level_filter = options['level']
        verbose = options['verbose']

        # 构建查询条件
        queryset = User.objects.filter(level__lt=4).order_by('id')

        if level_filter:
            queryset = queryset.filter(level=level_filter)

        total_users = queryset.count()

        if total_users == 0:
            self.stdout.write(
                self.style.WARNING('📭 没有找到符合条件的用户')
            )
            return {
                'processed': 0,
                'promoted': 0,
                'errors': 0,
                'skipped': 0,
                'details': []
            }

        self.stdout.write(f'📊 找到 {total_users} 个待检查用户')
        if level_filter:
            self.stdout.write(f'🎯 仅处理当前等级为 {level_filter} 的用户')
        if dry_run:
            self.stdout.write(self.style.WARNING('🔍 预览模式 - 不会实际执行晋升'))

        self.stdout.write('')

        promoted_count = 0
        error_count = 0
        skipped_count = 0
        processed_count = 0
        details = []

        # 分批处理
        for offset in range(0, total_users, batch_size):
            batch_users = list(queryset[offset:offset + batch_size])
            batch_num = offset // batch_size + 1
            total_batches = (total_users + batch_size - 1) // batch_size

            self.stdout.write(f'📦 处理批次 {batch_num}/{total_batches} ({len(batch_users)} 个用户)')

            for user in batch_users:
                processed_count += 1

                # 检查晋升条件
                target_level = user.check_level_promotion_eligibility()

                if target_level is None:
                    skipped_count += 1
                    if verbose:
                        self.stdout.write(f'   ⚠️  {user.username} (等级{user.level}) - 暂不符合晋升条件')
                    continue

                if dry_run:
                    self.stdout.write(f'   ✨ [预览] {user.username} 可以从 {user.level} 级晋升到 {target_level} 级')
                    details.append({
                        'user': user.username,
                        'from_level': user.level,
                        'to_level': target_level,
                        'action': 'preview'
                    })
                    continue

                # 执行晋升
                try:
                    with transaction.atomic():
                        old_level = user.level
                        user.promote_to_level(target_level, reason='manual_command')

                    promoted_count += 1
                    self.stdout.write(f'   ✅ {user.username} 成功从 {old_level} 级晋升到 {user.level} 级')
                    details.append({
                        'user': user.username,
                        'from_level': old_level,
                        'to_level': user.level,
                        'action': 'promoted'
                    })

                except Exception as e:
                    error_count += 1
                    self.stdout.write(f'   ❌ {user.username} 晋升失败: {str(e)}')
                    if verbose:
                        import traceback
                        self.stdout.write(traceback.format_exc())

        return {
            'processed': processed_count,
            'promoted': promoted_count,
            'errors': error_count,
            'skipped': skipped_count,
            'details': details
        }

    def _print_summary(self, result, start_time, options):
        """打印执行结果摘要"""
        end_time = timezone.now()
        duration = (end_time - start_time).total_seconds()

        self.stdout.write('\n' + '='*60)
        self.stdout.write(self.style.SUCCESS('📊 执行结果摘要'))
        self.stdout.write('='*60)

        if options['dry_run']:
            self.stdout.write(self.style.WARNING('🔍 预览模式 - 未实际执行晋升'))

        self.stdout.write(f'⏱️  执行时间: {duration:.2f} 秒')
        self.stdout.write(f'👥 处理用户数: {result["processed"]}')
        self.stdout.write(f'🎉 成功晋升: {result["promoted"]}')
        self.stdout.write(f'⚠️  跳过用户: {result["skipped"]}')
        self.stdout.write(f'❌ 错误数量: {result["errors"]}')

        if result['details'] and options['verbose']:
            self.stdout.write('\n📋 详细信息:')
            for detail in result['details'][:20]:  # 最多显示20条详细信息
                action_icon = {'promoted': '✅', 'preview': '👀', 'error': '❌'}.get(detail['action'], '📝')
                self.stdout.write(f'   {action_icon} {detail["user"]}: {detail["from_level"]} → {detail["to_level"]}')

            if len(result['details']) > 20:
                self.stdout.write(f'   ... 还有 {len(result["details"]) - 20} 条记录')

        if result['promoted'] > 0 and not options['dry_run']:
            self.stdout.write('\n🎊 等级晋升处理完成！用户将收到晋升通知。')
        elif options['dry_run'] and result['details']:
            self.stdout.write(f'\n👀 预览完成！发现 {len(result["details"])} 个用户符合晋升条件。')
            self.stdout.write('   使用不带 --dry-run 参数的命令来实际执行晋升。')
        else:
            self.stdout.write('\n✨ 处理完成！')