from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.html import format_html
from .models import User, Friendship, UserLevelUpgrade, DailyLoginReward, Notification, ActivityLog


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """用户管理"""

    list_display = ['username', 'email', 'level', 'activity_score', 'coins', 'last_decay_processed', 'is_active', 'created_at']
    list_filter = ['level', 'is_active', 'created_at']
    search_fields = ['username', 'email']
    ordering = ['-created_at']

    fieldsets = BaseUserAdmin.fieldsets + (
        ('扩展信息', {
            'fields': (
                'level', 'activity_score', 'last_active', 'last_decay_processed', 'location_precision',
                'coins', 'avatar', 'bio', 'total_posts', 'total_likes_received',
                'total_tasks_completed'
            )
        }),
    )

    readonly_fields = ['last_login', 'date_joined', 'activity_score', 'last_decay_processed', 'total_posts',
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


@admin.register(DailyLoginReward)
class DailyLoginRewardAdmin(admin.ModelAdmin):
    """每日登录奖励管理"""

    list_display = ['user', 'date', 'user_level', 'reward_amount', 'created_at']
    list_filter = ['date', 'user_level', 'created_at']
    search_fields = ['user__username']
    ordering = ['-date', '-created_at']
    readonly_fields = ['created_at']

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user')


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    """通知管理"""

    list_display = [
        'get_notification_type_display',
        'recipient',
        'actor_info',
        'title',
        'priority_badge',
        'is_read_badge',
        'created_at'
    ]
    list_filter = [
        'notification_type',
        'priority',
        'is_read',
        'created_at',
        'recipient'
    ]
    search_fields = [
        'recipient__username',
        'actor__username',
        'title',
        'message'
    ]
    ordering = ['-created_at']
    readonly_fields = ['created_at', 'updated_at']

    fieldsets = (
        ('基本信息', {
            'fields': (
                'recipient', 'actor', 'notification_type',
                'title', 'message', 'priority'
            )
        }),
        ('关联信息', {
            'fields': (
                'related_object_type',
                'related_object_id',
                'extra_data'
            ),
            'classes': ('collapse',)
        }),
        ('状态管理', {
            'fields': (
                'is_read', 'read_at', 'created_at', 'updated_at'
            )
        }),
    )

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('recipient', 'actor')

    def actor_info(self, obj):
        """显示触发者信息，如果没有则显示系统"""
        if obj.actor:
            return format_html(
                '<span style="color: #28a745;">{}</span>',
                obj.actor.username
            )
        return format_html(
            '<span style="color: #6c757d; font-style: italic;">系统</span>'
        )
    actor_info.short_description = '触发者'
    actor_info.admin_order_field = 'actor__username'

    def priority_badge(self, obj):
        """显示优先级徽章"""
        colors = {
            'low': '#28a745',
            'normal': '#17a2b8',
            'high': '#ffc107',
            'urgent': '#dc3545'
        }
        color = colors.get(obj.priority, '#6c757d')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 2px 8px; '
            'border-radius: 12px; font-size: 11px; font-weight: bold;">{}</span>',
            color,
            obj.get_priority_display()
        )
    priority_badge.short_description = '优先级'
    priority_badge.admin_order_field = 'priority'

    def is_read_badge(self, obj):
        """显示已读状态徽章"""
        if obj.is_read:
            return format_html(
                '<span style="background-color: #28a745; color: white; padding: 2px 8px; '
                'border-radius: 12px; font-size: 11px; font-weight: bold;">已读</span>'
            )
        return format_html(
            '<span style="background-color: #dc3545; color: white; padding: 2px 8px; '
            'border-radius: 12px; font-size: 11px; font-weight: bold;">未读</span>'
        )
    is_read_badge.short_description = '状态'
    is_read_badge.admin_order_field = 'is_read'

    # 添加批量操作
    actions = ['mark_as_read', 'mark_as_unread', 'delete_selected_notifications']

    def mark_as_read(self, request, queryset):
        """批量标记为已读"""
        updated = queryset.filter(is_read=False).update(is_read=True)
        self.message_user(request, f'成功将 {updated} 条通知标记为已读。')
    mark_as_read.short_description = '标记选中通知为已读'

    def mark_as_unread(self, request, queryset):
        """批量标记为未读"""
        updated = queryset.filter(is_read=True).update(is_read=False, read_at=None)
        self.message_user(request, f'成功将 {updated} 条通知标记为未读。')
    mark_as_unread.short_description = '标记选中通知为未读'

    def delete_selected_notifications(self, request, queryset):
        """批量删除通知"""
        count = queryset.count()
        queryset.delete()
        self.message_user(request, f'成功删除 {count} 条通知。')
    delete_selected_notifications.short_description = '删除选中通知'

    # 在列表页面显示更多信息
    list_per_page = 25
    show_full_result_count = True


@admin.register(ActivityLog)
class ActivityLogAdmin(admin.ModelAdmin):
    """活跃度日志管理"""

    list_display = [
        'user',
        'action_type_badge',
        'points_change_display',
        'new_total',
        'created_at'
    ]
    list_filter = [
        'action_type',
        'created_at',
        'user'
    ]
    search_fields = [
        'user__username',
    ]
    ordering = ['-created_at']
    readonly_fields = ['created_at', 'user', 'action_type', 'points_change', 'new_total', 'metadata']

    fieldsets = (
        ('基本信息', {
            'fields': (
                'user', 'action_type', 'points_change', 'new_total'
            )
        }),
        ('元数据', {
            'fields': (
                'metadata', 'created_at'
            ),
            'classes': ('collapse',)
        }),
    )

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user')

    def action_type_badge(self, obj):
        """显示活动类型徽章"""
        colors = {
            'activity_gain': '#28a745',
            'time_decay': '#dc3545'
        }
        color = colors.get(obj.action_type, '#6c757d')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 2px 8px; '
            'border-radius: 12px; font-size: 11px; font-weight: bold;">{}</span>',
            color,
            obj.get_action_type_display()
        )
    action_type_badge.short_description = '活动类型'
    action_type_badge.admin_order_field = 'action_type'

    def points_change_display(self, obj):
        """显示积分变化"""
        if obj.points_change > 0:
            return format_html(
                '<span style="color: #28a745; font-weight: bold;">+{}</span>',
                obj.points_change
            )
        elif obj.points_change < 0:
            return format_html(
                '<span style="color: #dc3545; font-weight: bold;">{}</span>',
                obj.points_change
            )
        else:
            return format_html(
                '<span style="color: #6c757d;">0</span>'
            )
    points_change_display.short_description = '积分变化'
    points_change_display.admin_order_field = 'points_change'

    # 在列表页面显示更多信息
    list_per_page = 50
    show_full_result_count = True
