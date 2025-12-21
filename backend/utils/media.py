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

    if settings.DEBUG:
        # Development: use localhost backend
        return f"http://localhost:8000{relative_url}"
    else:
        # Production: use backend domain
        return f"https://lock-down.zheermao.top{relative_url}"