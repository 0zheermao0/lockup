from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, Friendship, UserLevelUpgrade


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """用户管理"""

    list_display = ['username', 'email', 'level', 'activity_score', 'coins', 'is_active', 'created_at']
    list_filter = ['level', 'is_active', 'created_at']
    search_fields = ['username', 'email']
    ordering = ['-created_at']

    fieldsets = BaseUserAdmin.fieldsets + (
        ('扩展信息', {
            'fields': (
                'level', 'activity_score', 'last_active', 'location_precision',
                'coins', 'avatar', 'bio', 'total_posts', 'total_likes_received',
                'total_tasks_completed'
            )
        }),
    )

    readonly_fields = ['last_login', 'date_joined', 'activity_score', 'total_posts',
                       'total_likes_received', 'total_tasks_completed']


@admin.register(Friendship)
class FriendshipAdmin(admin.ModelAdmin):
    """好友关系管理"""

    list_display = ['from_user', 'to_user', 'status', 'created_at']
    list_filter = ['status', 'created_at']
    search_fields = ['from_user__username', 'to_user__username']
    ordering = ['-created_at']


@admin.register(UserLevelUpgrade)
class UserLevelUpgradeAdmin(admin.ModelAdmin):
    """用户等级晋升记录管理"""

    list_display = ['user', 'from_level', 'to_level', 'reason', 'promoted_by', 'created_at']
    list_filter = ['from_level', 'to_level', 'reason', 'created_at']
    search_fields = ['user__username', 'promoted_by__username']
    ordering = ['-created_at']
