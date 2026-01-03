from django.apps import AppConfig


class UtilsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'utils'

    def ready(self):
        """在应用启动时进行配置验证"""
        try:
            from .email import validate_email_configuration
            validate_email_configuration()
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Email configuration validation failed: {e}")