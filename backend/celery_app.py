#!/usr/bin/env python3
"""
Celery Application Configuration for Lockup Backend

This module configures Celery for handling asynchronous tasks in the Lockup application.
Includes hourly rewards processing for lock tasks and daily activity decay processing.

Author: Claude Code
Created: 2024-12-19
"""

import os
from celery import Celery
from django.conf import settings
from django.apps import apps

# Set default Django settings module for 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'lockup_backend.settings')

# Create Celery application instance
app = Celery('lockup_backend')

# Load configuration from Django settings with CELERY_ prefix
app.config_from_object('django.conf:settings', namespace='CELERY')

# Auto-discover tasks from all registered Django apps
app.autodiscover_tasks(lambda: [n.name for n in apps.get_app_configs()])

# Celery configuration
app.conf.update(
    # Task serialization
    task_serializer='json',
    result_serializer='json',
    accept_content=['json'],

    # Timezone settings
    timezone=settings.TIME_ZONE,
    enable_utc=True,

    # Task routing - separate queues for different task types
    task_routes={
        # Core reward and activity tasks
        'tasks.celery_tasks.process_hourly_rewards': {'queue': 'rewards'},
        'tasks.celery_tasks.process_activity_decay': {'queue': 'activity'},

        # Event-driven tasks (high frequency, real-time)
        'tasks.celery_tasks.process_pinning_queue': {'queue': 'events'},

        # Settlement tasks (financial operations, require reliability)
        'tasks.celery_tasks.auto_settle_expired_board_task': {'queue': 'settlements'},
        'tasks.celery_tasks.process_expired_board_tasks': {'queue': 'settlements'},

        # Voting and verification tasks (community operations)
        'tasks.celery_tasks.process_checkin_voting_results': {'queue': 'voting'},
    },

    # Worker configuration
    task_acks_late=True,                    # Acknowledge tasks only after completion
    task_reject_on_worker_lost=True,        # Reject tasks if worker connection is lost
    worker_prefetch_multiplier=1,           # Only fetch one task at a time
    worker_max_tasks_per_child=1000,        # Restart worker after 1000 tasks (memory cleanup)

    # Task execution settings
    task_soft_time_limit=300,               # Soft timeout: 5 minutes
    task_time_limit=600,                    # Hard timeout: 10 minutes

    # Result backend settings
    result_expires=3600,                    # Results expire after 1 hour
    result_backend_transport_options={
        'visibility_timeout': 3600,
    },

    # Monitoring and events
    worker_send_task_events=True,
    task_send_sent_event=True,
)

# Beat schedule configuration removed - using DatabaseScheduler
# All periodic tasks are now managed through Django admin interface
# via django_celery_beat.models.PeriodicTask
#
# This eliminates redundancy between static code definitions and dynamic database records.
# Tasks can be managed, enabled/disabled, and scheduled through Django admin without code changes.

# Set default queue for beat scheduler
app.conf.beat_scheduler = 'django_celery_beat.schedulers:DatabaseScheduler'

@app.task(bind=True)
def debug_task(self):
    """Debug task for testing Celery setup"""
    print(f'Request: {self.request!r}')
    return {'status': 'success', 'message': 'Celery is working!'}


# Explicitly import tasks to ensure they are registered
# This must be done after Django is configured
try:
    import django
    django.setup()
    # Import all task modules to register them with Celery
    from tasks.celery_tasks import *
    from utils.email import send_email_task
except Exception as e:
    print(f"Warning: Could not import tasks: {e}")

if __name__ == '__main__':
    app.start()