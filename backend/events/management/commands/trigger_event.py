#!/usr/bin/env python3
"""
Django Management Command to Manually Trigger Events

This command allows administrators to manually trigger specific events:
- Trigger events by name or ID
- Support for dry-run mode to preview effects
- Detailed output showing affected users and results

Author: Claude Code
Created: 2024-12-30
"""

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from django.db import transaction
from events.models import EventDefinition, EventOccurrence
from events.celery_tasks import trigger_manual_event
from users.models import User
import json


class Command(BaseCommand):
    help = 'Manually trigger a specific event by name or ID'

    def add_arguments(self, parser):
        parser.add_argument(
            '--event-name',
            type=str,
            help='Event name to trigger'
        )
        parser.add_argument(
            '--event-id',
            type=str,
            help='Event ID to trigger'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be done without actually executing'
        )
        parser.add_argument(
            '--user-id',
            type=int,
            help='User ID who triggered the event (defaults to system)'
        )
        parser.add_argument(
            '--async',
            action='store_true',
            help='Execute asynchronously using Celery (default: synchronous)'
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Skip confirmation prompt and execute immediately'
        )

    def handle(self, *args, **options):
        event_name = options.get('event_name')
        event_id = options.get('event_id')
        dry_run = options['dry_run']
        user_id = options.get('user_id')
        async_execution = options.get('async', False)
        force = options.get('force', False)

        if not event_name and not event_id:
            raise CommandError('Either --event-name or --event-id must be provided')

        if event_name and event_id:
            raise CommandError('Cannot specify both --event-name and --event-id')

        # Find the event definition
        try:
            if event_name:
                event_def = EventDefinition.objects.get(name=event_name)
                self.stdout.write(f'Found event by name: {event_name}')
            else:
                event_def = EventDefinition.objects.get(id=event_id)
                self.stdout.write(f'Found event by ID: {event_id}')
        except EventDefinition.DoesNotExist:
            identifier = event_name or event_id
            raise CommandError(f'Event not found: {identifier}')

        # Get triggered by user
        triggered_by = None
        if user_id:
            try:
                triggered_by = User.objects.get(id=user_id)
                self.stdout.write(f'Triggered by user: {triggered_by.username}')
            except User.DoesNotExist:
                raise CommandError(f'User not found: {user_id}')

        # Display event information
        self.stdout.write('\n' + '=' * 60)
        self.stdout.write(self.style.SUCCESS(f'Event: {event_def.title}'))
        self.stdout.write(f'Description: {event_def.description}')
        self.stdout.write(f'Category: {event_def.get_category_display()}')
        self.stdout.write(f'Active: {event_def.is_active}')
        self.stdout.write(f'Effects count: {event_def.effects.count()}')

        if not event_def.is_active:
            self.stdout.write(
                self.style.WARNING('Warning: Event is not active')
            )

        # Display effects
        effects = event_def.effects.filter(is_active=True).order_by('priority')
        if effects.exists():
            self.stdout.write('\n--- Effects ---')
            for i, effect in enumerate(effects, 1):
                self.stdout.write(f'{i}. {effect.get_effect_type_display()}')
                self.stdout.write(f'   Target: {effect.get_target_type_display()}')
                self.stdout.write(f'   Parameters: {effect.effect_parameters}')
                if effect.duration_minutes:
                    self.stdout.write(f'   Duration: {effect.duration_minutes} minutes')
        else:
            self.stdout.write(
                self.style.WARNING('No active effects found for this event')
            )

        if dry_run:
            self.stdout.write('\n' + '=' * 60)
            self.stdout.write(
                self.style.SUCCESS('[DRY RUN] Event would be triggered but no changes made')
            )
            self._show_target_preview(effects)
            return

        # Confirm execution
        self.stdout.write('\n' + '=' * 60)
        if not async_execution and not force:
            confirm = input('Do you want to trigger this event? [y/N]: ')
            if confirm.lower() != 'y':
                self.stdout.write('Event trigger cancelled')
                return

        # Execute the event
        if async_execution:
            # Use Celery task
            task = trigger_manual_event.delay(
                str(event_def.id),
                user_id
            )
            self.stdout.write(
                self.style.SUCCESS(f'Event triggered asynchronously. Task ID: {task.id}')
            )
        else:
            # Execute synchronously
            result = self._execute_event_sync(event_def, triggered_by)
            self._display_results(result)

    def _show_target_preview(self, effects):
        """Show preview of target users for each effect"""
        from events.effects import get_effect_executor

        self.stdout.write('\n--- Target Preview ---')
        for i, effect in enumerate(effects, 1):
            try:
                executor = get_effect_executor(effect)
                target_users = executor.get_target_users()

                self.stdout.write(f'Effect {i}: {effect.get_effect_type_display()}')
                self.stdout.write(f'  Target users: {len(target_users)}')

                if target_users and len(target_users) <= 10:
                    usernames = [user.username for user in target_users[:10]]
                    self.stdout.write(f'  Users: {", ".join(usernames)}')
                elif len(target_users) > 10:
                    usernames = [user.username for user in target_users[:5]]
                    self.stdout.write(f'  Sample users: {", ".join(usernames)}... (+{len(target_users)-5} more)')

            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'  Error getting targets: {e}')
                )

    def _execute_event_sync(self, event_def, triggered_by):
        """Execute event synchronously"""
        from events.celery_tasks import _execute_single_effect

        self.stdout.write(
            self.style.SUCCESS('Executing event synchronously...')
        )

        try:
            with transaction.atomic():
                now = timezone.now()

                # Create event occurrence
                occurrence = EventOccurrence.objects.create(
                    event_definition=event_def,
                    scheduled_at=now,
                    trigger_type='manual',
                    triggered_by=triggered_by,
                    status='executing',
                    started_at=now
                )

                # Execute all effects
                total_affected = 0
                execution_log = []

                effects = event_def.effects.filter(is_active=True).order_by('priority')

                for effect in effects:
                    self.stdout.write(f'Executing effect: {effect.get_effect_type_display()}')

                    effect_result = _execute_single_effect(occurrence, effect)
                    total_affected += effect_result['affected_count']
                    execution_log.append(effect_result)

                    self.stdout.write(
                        f'  Affected {effect_result["affected_count"]}/{effect_result.get("total_targets", 0)} users'
                    )

                # Update occurrence
                occurrence.status = 'completed'
                occurrence.completed_at = timezone.now()
                occurrence.affected_users_count = total_affected
                occurrence.execution_log = execution_log
                occurrence.save()

                # Send notifications to affected users
                from events.celery_tasks import _send_event_notifications
                _send_event_notifications(occurrence)

                return {
                    'status': 'success',
                    'occurrence_id': str(occurrence.id),
                    'total_affected': total_affected,
                    'execution_log': execution_log
                }

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Event execution failed: {e}')
            )

            # Update occurrence status
            if 'occurrence' in locals():
                occurrence.status = 'failed'
                occurrence.error_message = str(e)
                occurrence.completed_at = timezone.now()
                occurrence.save()

            return {
                'status': 'error',
                'error': str(e)
            }

    def _display_results(self, result):
        """Display execution results"""
        self.stdout.write('\n' + '=' * 60)

        if result['status'] == 'success':
            self.stdout.write(
                self.style.SUCCESS(f'Event executed successfully!')
            )
            self.stdout.write(f'Occurrence ID: {result["occurrence_id"]}')
            self.stdout.write(f'Total affected users: {result["total_affected"]}')

            # Show effect results
            for i, log_entry in enumerate(result['execution_log'], 1):
                self.stdout.write(f'\nEffect {i}: {log_entry["effect_type"]}')
                self.stdout.write(f'  Target type: {log_entry["target_type"]}')
                self.stdout.write(f'  Affected: {log_entry["affected_count"]}/{log_entry.get("total_targets", 0)}')

                if 'error' in log_entry:
                    self.stdout.write(
                        self.style.ERROR(f'  Error: {log_entry["error"]}')
                    )
        else:
            self.stdout.write(
                self.style.ERROR(f'Event execution failed: {result["error"]}')
            )