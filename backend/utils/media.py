"""
Media file URL utilities
"""
from django.conf import settings


def get_full_media_url(relative_url):
    """
    Generate full media URL based on environment
    """
    if not relative_url:
        return None

    if relative_url.startswith('http'):
        return relative_url

    # Get media base URL from environment variable or auto-detect
    import os

    # First check if explicitly set in environment
    media_base_url = os.getenv('MEDIA_BASE_URL')
    if media_base_url:
        return f"{media_base_url.rstrip('/')}{relative_url}"

    # Auto-detect based on environment
    # Priority order: ENVIRONMENT var > DEBUG setting > host detection
    environment = os.getenv('ENVIRONMENT', '').lower()
    debug_mode = getattr(settings, 'DEBUG', True)

    if environment == 'development':
        is_production = False
    elif environment == 'production':
        is_production = True
    elif debug_mode is False:
        # DEBUG=False usually means production
        is_production = True
    else:
        # DEBUG=True usually means development, even if production hosts are in ALLOWED_HOSTS
        is_production = False

    if is_production:
        # Production: use backend domain with HTTPS
        return f"https://lock-down.zheermao.top{relative_url}"
    else:
        # Development: use localhost backend
        return f"http://localhost:8000{relative_url}"