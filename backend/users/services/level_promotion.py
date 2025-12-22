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
    def bulk_process_level_promotions(batch_size=1000):
        """Process level promotions for all eligible users"""
        promoted_count = 0
        error_count = 0

        # Process users in batches to manage memory
        user_queryset = User.objects.filter(level__lt=4).order_by('id')
        total_users = user_queryset.count()

        logger.info(f"Starting bulk level promotion check for {total_users} users")

        for i in range(0, total_users, batch_size):
            batch_users = user_queryset[i:i + batch_size]

            for user in batch_users:
                try:
                    if LevelPromotionService.check_and_promote_user(user):
                        promoted_count += 1
                except Exception as e:
                    error_count += 1
                    logger.error(f"Failed to process user {user.id}: {str(e)}")

        logger.info(f"Bulk promotion completed: {promoted_count} promoted, {error_count} errors")
        return {
            'promoted_count': promoted_count,
            'error_count': error_count,
            'total_processed': total_users
        }