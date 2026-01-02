from django.db import transaction
from django.utils import timezone
from users.models import User, UserLevelUpgrade
import logging

logger = logging.getLogger(__name__)

class LevelPromotionService:
    """Service for handling user level promotions"""

    @staticmethod
    def check_and_promote_user(user):
        """Check and promote a single user if eligible"""
        try:
            with transaction.atomic():
                # Lock user record to prevent concurrent modifications
                user = User.objects.select_for_update().get(id=user.id)

                eligible_level = user.check_level_promotion_eligibility()
                if eligible_level:
                    user.promote_to_level(eligible_level, reason='automatic')
                    logger.info(f"User {user.username} promoted from level {user.level-1} to {user.level}")
                    return True

                return False
        except Exception as e:
            logger.error(f"Error promoting user {user.id}: {str(e)}")
            return False

    @staticmethod
    def bulk_process_level_promotions(batch_size=50):
        """
        Process level promotions for all eligible users

        优化版本：使用小批次处理，避免SQLite数据库锁定问题
        """
        import time
        promoted_count = 0
        error_count = 0

        # 获取需要处理的用户ID列表（只查询ID，避免锁定）
        eligible_user_ids = list(User.objects.filter(
            level__lt=4
        ).values_list('id', flat=True))

        total_users = len(eligible_user_ids)
        logger.info(f"Starting bulk level promotion check for {total_users} users")

        if total_users == 0:
            return {
                'promoted_count': 0,
                'error_count': 0,
                'total_processed': 0,
                'message': 'No users to process'
            }

        # 分批处理，避免长时间锁定数据库
        for i in range(0, total_users, batch_size):
            batch_ids = eligible_user_ids[i:i + batch_size]
            batch_number = i // batch_size + 1
            total_batches = (total_users + batch_size - 1) // batch_size

            try:
                # 使用独立的事务处理每个批次
                with transaction.atomic():
                    batch_users = User.objects.select_for_update().filter(id__in=batch_ids)

                    for user in batch_users:
                        try:
                            eligible_level = user.check_level_promotion_eligibility()
                            if eligible_level:
                                user.promote_to_level(eligible_level, reason='automatic')
                                promoted_count += 1
                                logger.debug(f"User {user.username} promoted from level {user.level-1} to {user.level}")
                        except Exception as e:
                            error_count += 1
                            logger.error(f"Failed to process user {user.id}: {str(e)}")
                            continue

                logger.info(f"Completed batch {batch_number}/{total_batches}: processed {len(batch_ids)} users")

                # 批次间短暂休息，释放数据库锁，让其他操作有机会执行
                if i + batch_size < total_users:  # 不是最后一批
                    time.sleep(0.1)  # 100ms休息

            except Exception as batch_error:
                logger.error(f"Error processing batch {batch_number}: {batch_error}")
                error_count += len(batch_ids)
                # 继续处理下一批次，不中断整个流程
                continue

        logger.info(f"Bulk promotion completed: {promoted_count} promoted, {error_count} errors, {total_batches} batches processed")
        return {
            'promoted_count': promoted_count,
            'error_count': error_count,
            'total_processed': total_users,
            'batches_processed': total_batches
        }