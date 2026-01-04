from django.core.management.base import BaseCommand
from django.utils import timezone
from tasks.models import LockTask, HourlyReward, TaskTimelineEvent
from users.models import Notification


class Command(BaseCommand):
    help = '强制增加1点'

    def handle(self, *args, **options):
        # self.stdout.write(
        #     self.style.WARNING(
        #         '⚠️  此命令已废弃。请使用 Celery Beat 自动处理每小时奖励。\n'
        #         '如需手动执行，请确认 Celery Beat 未在运行以避免重复处理。'
        #     )
        # )

        # confirm = input('确认继续执行吗？ (y/N): ')
        # if confirm.lower() != 'y':
        #     self.stdout.write('操作已取消')
        #     return

        now = timezone.now()

        # 1. 处理小时奖励
        self.stdout.write("Processing hourly rewards...")
        hourly_results = self.process_hourly_rewards(now)

        # 2. 处理投票结果
        # self.stdout.write("Processing voting results...")
        # from tasks.views import _process_voting_results_internal
        # try:
        #     _process_voting_results_internal()
        # except Exception as e:
        #     self.stdout.write(self.style.WARNING(f"Failed to process voting results: {e}"))

        # 输出结果
        self.stdout.write(
            self.style.SUCCESS(f'Successfully processed {hourly_results} hourly rewards')
        )

    def process_hourly_rewards(self, now):
        """处理带锁任务的每小时积分奖励"""
        # 找到所有活跃状态的带锁任务
        active_lock_tasks = LockTask.objects.filter(
            task_type='lock',
            status__in=['active', 'voting']  # 活跃状态和投票期都算活跃
        )

        processed_rewards = []

        for task in active_lock_tasks:
            if not task.start_time:
                continue

            # 计算任务已运行的总时间（小时）
            elapsed_time = now - task.start_time
            elapsed_hours = int(elapsed_time.total_seconds() // 3600)

            if elapsed_hours < 1:
                # 任务运行不满一小时，跳过
                # continue
                pass

            # 检查上次奖励时间
            if task.last_hourly_reward_at:
                # 如果已经有奖励记录，检查是否需要新的奖励
                time_since_last_reward = now - task.last_hourly_reward_at
                hours_since_last_reward = int(time_since_last_reward.total_seconds() // 3600)

                if hours_since_last_reward < 1:
                    # 距离上次奖励不足一小时，跳过
                    # continue
                    pass

                # 计算需要补发的奖励小时数
                next_reward_hour = task.total_hourly_rewards + 1
            else:
                # 第一次发放奖励，从第1小时开始
                next_reward_hour = 1

            # 发放所有应该获得但还没有获得的小时奖励
            # rewards_to_give = elapsed_hours - task.total_hourly_rewards
            rewards_to_give = 1

            for hour_num in range(next_reward_hour, next_reward_hour + rewards_to_give):
                # 给用户增加1积分（coins）
                task.user.coins += 1
                task.user.save()

                # 创建奖励记录
                hourly_reward = HourlyReward.objects.create(
                    task=task,
                    user=task.user,
                    reward_amount=1,
                    hour_count=hour_num
                )

                # 记录到时间线
                TaskTimelineEvent.objects.create(
                    task=task,
                    event_type='hourly_reward',
                    user=None,  # 系统事件
                    description=f'第{hour_num}小时奖励：{task.user.username}获得1积分',
                    metadata={
                        'reward_amount': 1,
                        'hour_count': hour_num,
                        'total_coins': task.user.coins,
                        'auto_processed': True
                    }
                )

                # 减少通知频率：只在特定小时数时发送批量通知，减轻视觉负担
                should_notify = (
                    hour_num == 1 or  # 第一小时
                    hour_num % 3 == 0  # 每3小时
                )

                if should_notify:
                    # 计算当前批次的奖励总数
                    batch_rewards = min(3, hour_num) if hour_num % 3 == 0 else 1

                    try:
                        Notification.create_notification(
                            recipient=task.user,
                            notification_type='coins_earned_hourly_batch',
                            actor=None,  # 系统通知
                            related_object_type='task',
                            related_object_id=task.id,
                            extra_data={
                                'task_title': task.title,
                                'current_hour': hour_num,
                                'batch_rewards': batch_rewards,
                                'total_hourly_rewards': task.total_hourly_rewards + 1,
                                'notification_type': 'batched'  # 标记为批量通知
                            },
                            priority='low'  # 低优先级，减少视觉干扰
                        )
                    except Exception as e:
                        self.stdout.write(
                            self.style.WARNING(f"Failed to send notification: {e}")
                        )

                processed_rewards.append({
                    'task_id': str(task.id),
                    'task_title': task.title,
                    'user': task.user.username,
                    'hour_count': hour_num,
                    'reward_amount': 1
                })

            # 更新任务的奖励记录
            if rewards_to_give > 0:
                task.total_hourly_rewards += rewards_to_give
                task.last_hourly_reward_at = now
                task.save()

                self.stdout.write(
                    f"  - {task.user.username}: {task.title} (+{rewards_to_give} hourly rewards)"
                )

        return len(processed_rewards)