from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from .models import UserInventory

User = get_user_model()


@receiver(post_save, sender=User)
def create_user_inventory(sender, instance, created, **kwargs):
    """当用户创建时自动创建背包"""
    if created:
        UserInventory.objects.create(user=instance)


@receiver(post_save, sender=User)
def save_user_inventory(sender, instance, **kwargs):
    """确保用户有背包"""
    if not hasattr(instance, 'inventory'):
        UserInventory.objects.create(user=instance)