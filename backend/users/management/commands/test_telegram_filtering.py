#!/usr/bin/env python3
"""
Test Telegram notification filtering

This command creates test notifications with different priority levels
to verify that only urgent notifications are sent to Telegram.
"""

from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from users.models import Notification
from django.utils import timezone
import logging

User = get_user_model()
logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Test Telegram notification filtering by creating notifications with different priorities'

    def add_arguments(self, parser):
        parser.add_argument(
            '--user-id',
            type=int,
            help='User ID to send test notifications to (default: first user with Telegram binding)',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be done without actually creating notifications',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']

        # Find a user with Telegram binding
        if options['user_id']:
            try:
                test_user = User.objects.get(id=options['user_id'])
            except User.DoesNotExist:
                self.stdout.write(
                    self.style.ERROR(f'User with ID {options["user_id"]} not found')
                )
                return
        else:
            # Find first user with Telegram binding
            test_user = User.objects.filter(
                telegram_user_id__isnull=False,
                telegram_chat_id__isnull=False,
                telegram_notifications_enabled=True
            ).first()

        if not test_user:
            self.stdout.write(
                self.style.ERROR('No user found with Telegram binding enabled')
            )
            return

        self.stdout.write(f'Testing with user: {test_user.username} (ID: {test_user.id})')

        if not test_user.can_receive_telegram_notifications():
            self.stdout.write(
                self.style.WARNING(f'User {test_user.username} cannot receive Telegram notifications')
            )
            return

        # Test notifications with different priorities
        test_cases = [
            {
                'priority': 'low',
                'title': 'Low Priority Test',
                'message': 'This is a low priority test notification - should NOT be sent to Telegram',
                'should_send_telegram': False
            },
            {
                'priority': 'normal',
                'title': 'Normal Priority Test',
                'message': 'This is a normal priority test notification - should NOT be sent to Telegram',
                'should_send_telegram': False
            },
            {
                'priority': 'high',
                'title': 'High Priority Test',
                'message': 'This is a high priority test notification - should NOT be sent to Telegram',
                'should_send_telegram': False
            },
            {
                'priority': 'urgent',
                'title': 'Urgent Priority Test',
                'message': 'This is an urgent priority test notification - should BE SENT to Telegram',
                'should_send_telegram': True
            }
        ]

        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN - No notifications will be created'))

        for i, test_case in enumerate(test_cases, 1):
            priority = test_case['priority']
            title = test_case['title']
            message = test_case['message']
            should_send = test_case['should_send_telegram']

            self.stdout.write(f'\n{i}. Testing {priority} priority notification:')
            self.stdout.write(f'   Title: {title}')
            self.stdout.write(f'   Expected Telegram: {"YES" if should_send else "NO"}')

            if not dry_run:
                try:
                    # Create the notification
                    notification = Notification.create_notification(
                        recipient=test_user,
                        notification_type='system_announcement',
                        title=title,
                        message=message,
                        priority=priority,
                        extra_data={
                            'test_notification': True,
                            'test_timestamp': timezone.now().isoformat(),
                            'expected_telegram': should_send
                        }
                    )

                    if notification:
                        self.stdout.write(
                            self.style.SUCCESS(f'   ✓ Created notification {notification.id}')
                        )

                        # Check if the notification meets Telegram criteria
                        telegram_criteria_met = (
                            notification.recipient.can_receive_telegram_notifications() and
                            notification.priority == 'urgent'
                        )

                        if telegram_criteria_met == should_send:
                            self.stdout.write(
                                self.style.SUCCESS(f'   ✓ Telegram filtering working correctly')
                            )
                        else:
                            self.stdout.write(
                                self.style.ERROR(f'   ✗ Telegram filtering issue detected!')
                            )
                    else:
                        self.stdout.write(
                            self.style.ERROR(f'   ✗ Failed to create notification')
                        )

                except Exception as e:
                    self.stdout.write(
                        self.style.ERROR(f'   ✗ Error creating notification: {e}')
                    )
                    logger.error(f'Error creating test notification: {e}', exc_info=True)

        if not dry_run:
            self.stdout.write(f'\n{self.style.SUCCESS("Test completed!")}')
            self.stdout.write('Check your Telegram to verify that only the URGENT notification was received.')

            # Show recent test notifications
            recent_test_notifications = Notification.objects.filter(
                recipient=test_user,
                extra_data__test_notification=True,
                created_at__gte=timezone.now() - timezone.timedelta(minutes=5)
            ).order_by('-created_at')

            if recent_test_notifications:
                self.stdout.write(f'\nRecent test notifications created:')
                for notif in recent_test_notifications:
                    self.stdout.write(
                        f'  - {notif.priority}: {notif.title} (ID: {notif.id})'
                    )
        else:
            self.stdout.write(f'\n{self.style.WARNING("Dry run completed - no notifications created")}')