#!/usr/bin/env python3
"""
Celery Application Configuration for Lockup Backend

This module configures Celery for handling asynchronous tasks in the Lockup application.
Currently focused on hourly rewards processing for lock tasks.

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
        'tasks.celery_tasks.process_hourly_rewards': {'queue': 'rewards'},
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

# Beat schedule for periodic tasks
from celery.schedules import crontab

app.conf.beat_schedule = {
    'process-hourly-rewards': {
        'task': 'tasks.celery_tasks.process_hourly_rewards',
        'schedule': 60.0 * 60.0,  # Execute every hour (3600 seconds)
        'options': {
            'queue': 'rewards',
            'routing_key': 'rewards',
        },
    },
    'process-pinning-queue': {
        'task': 'tasks.celery_tasks.process_pinning_queue',
        'schedule': 60.0,  # Execute every minute (60 seconds)
        'options': {
            'queue': 'default',
            'routing_key': 'default',
        },
    },
    'pinning-health-check': {
        'task': 'tasks.celery_tasks.pinning_health_check',
        'schedule': 60.0 * 5,  # Execute every 5 minutes (300 seconds)
        'options': {
            'queue': 'default',
            'routing_key': 'default',
        },
    },
    'process-checkin-voting-results': {
        'task': 'tasks.celery_tasks.process_checkin_voting_results',
        'schedule': crontab(hour=4, minute=0),  # Execute daily at 4:00 AM
        'options': {
            'queue': 'default',
            'routing_key': 'default',
        },
    },
    'process-level-promotions': {
        'task': 'tasks.celery_tasks.process_level_promotions',
        'schedule': crontab(hour=4, minute=30, day_of_week=3),  # Wednesday 4:30 AM
        'options': {
            'queue': 'default',
            'expires': 3600,  # Task expires after 1 hour
        }
    },
    'auto-freeze-strict-mode-tasks': {
        'task': 'tasks.celery_tasks.auto_freeze_strict_mode_tasks',
        'schedule': crontab(hour=4, minute=15),  # Daily at 4:15 AM (after check-in voting at 4:00)
        'options': {
            'queue': 'default',
            'expires': 3600,  # Task expires after 1 hour
        }
    },
}

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
except Exception as e:
    print(f"Warning: Could not import tasks: {e}")

if __name__ == '__main__':
    app.start()