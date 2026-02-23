# Generated migration to add telegram_priority_settings and remove telegram_min_priority

from django.db import migrations, models


def migrate_telegram_priority_settings(apps, schema_editor):
    """Migrate existing telegram_min_priority values to telegram_priority_settings"""
    User = apps.get_model('users', 'User')

    # Migration mapping from old threshold to new individual settings
    # The old threshold meant "this priority and above"
    migration_map = {
        'low': {'low': True, 'normal': True, 'high': True, 'urgent': True},
        'normal': {'low': False, 'normal': True, 'high': True, 'urgent': True},
        'high': {'low': False, 'normal': False, 'high': True, 'urgent': True},
        'urgent': {'low': False, 'normal': False, 'high': False, 'urgent': True},
    }

    for user in User.objects.all():
        old_priority = getattr(user, 'telegram_min_priority', 'urgent')
        new_settings = migration_map.get(old_priority, migration_map['urgent'])
        user.telegram_priority_settings = new_settings
        user.save(update_fields=['telegram_priority_settings'])


def reverse_migrate_telegram_priority_settings(apps, schema_editor):
    """Reverse migration - convert settings back to threshold (best effort)"""
    User = apps.get_model('users', 'User')

    for user in User.objects.all():
        settings = user.telegram_priority_settings or {}

        # Determine the threshold based on settings
        if settings.get('low', False):
            user.telegram_min_priority = 'low'
        elif settings.get('normal', False):
            user.telegram_min_priority = 'normal'
        elif settings.get('high', False):
            user.telegram_min_priority = 'high'
        else:
            user.telegram_min_priority = 'urgent'

        user.save(update_fields=['telegram_min_priority'])


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0022_alter_dailyloginreward_options_usercheckin'),
    ]

    operations = [
        # Add the new field
        migrations.AddField(
            model_name='user',
            name='telegram_priority_settings',
            field=models.JSONField(
                default=dict,
                help_text="哪些优先级的通知会触发Telegram推送，格式: {'low': false, 'normal': false, 'high': true, 'urgent': true}"
            ),
        ),
        # Run data migration
        migrations.RunPython(
            migrate_telegram_priority_settings,
            reverse_migrate_telegram_priority_settings
        ),
        # Remove the old field
        migrations.RemoveField(
            model_name='user',
            name='telegram_min_priority',
        ),
    ]
