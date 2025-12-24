from django.contrib import admin
from django.db import models
from django.utils.html import format_html
from django.db.models import Count
from .models import (
    LockTask, TaskKey, TaskVote, OvertimeAction,
    TaskTimelineEvent, HourlyReward, TaskSubmissionFile, TaskParticipant, PinnedUser
)


@admin.register(LockTask)
class LockTaskAdmin(admin.ModelAdmin):
    """任务管理"""

    list_display = [
        'title',
        'task_type_badge',
        'user',
        'status_badge',
        'difficulty_badge',
        'created_at',
        'is_active'
    ]
    list_filter = [
        'task_type',
        'status',
        'difficulty',
        'unlock_type',
        'duration_type',
        'created_at',
        'user'
    ]
    search_fields = [
        'title',
        'description',
        'user__username'
    ]
    ordering = ['-created_at']
    readonly_fields = ['created_at', 'updated_at']

    fieldsets = (
        ('基本信息', {
            'fields': (
                'user', 'task_type', 'title', 'description',
                'status', 'difficulty'
            )
        }),
        ('带锁任务设置', {
            'fields': (
                'duration_type', 'duration_value', 'duration_max',
                'unlock_type', 'vote_threshold', 'vote_agreement_ratio',
                'overtime_multiplier', 'overtime_duration'
            ),
            'classes': ('collapse',)
        }),
        ('投票期设置', {
            'fields': (
                'voting_duration', 'vote_failed_penalty_minutes',
                'voting_start_time', 'voting_end_time'
            ),
            'classes': ('collapse',)
        }),
        ('任务板设置', {
            'fields': (
                'reward', 'deadline', 'max_duration',
                'taker', 'taken_at', 'completion_proof', 'completed_at'
            ),
            'classes': ('collapse',)
        }),
        ('时间信息', {
            'fields': (
                'start_time', 'end_time', 'last_hourly_reward_at',
                'total_hourly_rewards', 'created_at', 'updated_at'
            )
        }),
    )

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user', 'taker').annotate(
            total_votes_count=Count('votes'),
            agree_votes_count=Count('votes', filter=models.Q(votes__agree=True)),
            disagree_votes_count=Count('votes', filter=models.Q(votes__agree=False))
        )

    def task_type_badge(self, obj):
        """显示任务类型徽章"""
        colors = {
            'lock': '#007bff',
            'board': '#28a745'
        }
        color = colors.get(obj.task_type, '#6c757d')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 2px 8px; '
            'border-radius: 12px; font-size: 11px; font-weight: bold;">{}</span>',
            color,
            obj.get_task_type_display()
        )
    task_type_badge.short_description = '类型'
    task_type_badge.admin_order_field = 'task_type'

    def status_badge(self, obj):
        """显示状态徽章"""
        colors = {
            'pending': '#6c757d',
            'active': '#007bff',
            'voting': '#ffc107',
            'completed': '#28a745',
            'failed': '#dc3545',
            'open': '#28a745',
            'taken': '#ffc107',
            'submitted': '#17a2b8'
        }
        color = colors.get(obj.status, '#6c757d')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 2px 8px; '
            'border-radius: 12px; font-size: 11px; font-weight: bold;">{}</span>',
            color,
            obj.get_status_display()
        )
    status_badge.short_description = '状态'
    status_badge.admin_order_field = 'status'

    def difficulty_badge(self, obj):
        """显示难度徽章"""
        if not obj.difficulty:
            return '-'
        colors = {
            'easy': '#28a745',
            'normal': '#ffc107',
            'hard': '#fd7e14',
            'hell': '#dc3545'
        }
        color = colors.get(obj.difficulty, '#6c757d')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 2px 8px; '
            'border-radius: 12px; font-size: 11px; font-weight: bold;">{}</span>',
            color,
            obj.get_difficulty_display()
        )
    difficulty_badge.short_description = '难度'
    difficulty_badge.admin_order_field = 'difficulty'

    def is_active(self, obj):
        """显示是否活跃"""
        if obj.status in ['active', 'voting', 'taken', 'submitted', 'open']:
            return format_html(
                '<span style="color: #28a745; font-weight: bold;">✓</span>'
            )
        return format_html(
            '<span style="color: #dc3545; font-weight: bold;">✗</span>'
        )
    is_active.short_description = '活跃'
    # Removed: is_active.boolean = True  # This was causing the error

    list_per_page = 20


@admin.register(TaskKey)
class TaskKeyAdmin(admin.ModelAdmin):
    """任务钥匙管理"""

    list_display = ['task', 'holder', 'status_badge', 'created_at', 'used_at']
    list_filter = ['status', 'created_at', 'used_at']
    search_fields = ['task__title', 'holder__username']
    ordering = ['-created_at']
    readonly_fields = ['created_at', 'used_at']

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('task', 'holder')

    def status_badge(self, obj):
        """显示状态徽章"""
        colors = {
            'active': '#28a745',
            'used': '#dc3545'
        }
        color = colors.get(obj.status, '#6c757d')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 2px 8px; '
            'border-radius: 12px; font-size: 11px; font-weight: bold;">{}</span>',
            color,
            obj.get_status_display()
        )
    status_badge.short_description = '状态'
    status_badge.admin_order_field = 'status'


@admin.register(TaskVote)
class TaskVoteAdmin(admin.ModelAdmin):
    """任务投票管理"""

    list_display = ['task', 'voter', 'vote_badge', 'created_at']
    list_filter = ['agree', 'created_at']
    search_fields = ['task__title', 'voter__username']
    ordering = ['-created_at']

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('task', 'voter')

    def vote_badge(self, obj):
        """显示投票徽章"""
        if obj.agree:
            return format_html(
                '<span style="background-color: #28a745; color: white; padding: 2px 8px; '
                'border-radius: 12px; font-size: 11px; font-weight: bold;">同意</span>'
            )
        return format_html(
            '<span style="background-color: #dc3545; color: white; padding: 2px 8px; '
            'border-radius: 12px; font-size: 11px; font-weight: bold;">反对</span>'
        )
    vote_badge.short_description = '投票'
    vote_badge.admin_order_field = 'agree'


@admin.register(OvertimeAction)
class OvertimeActionAdmin(admin.ModelAdmin):
    """加时操作管理"""

    list_display = ['task', 'user', 'task_publisher', 'overtime_minutes', 'created_at']
    list_filter = ['created_at', 'overtime_minutes']
    search_fields = ['task__title', 'user__username', 'task_publisher__username']
    ordering = ['-created_at']

    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'task', 'user', 'task_publisher'
        )


@admin.register(TaskTimelineEvent)
class TaskTimelineEventAdmin(admin.ModelAdmin):
    """任务时间线事件管理"""

    list_display = [
        'event_type_badge',
        'task',
        'user_info',
        'time_change_info',
        'created_at'
    ]
    list_filter = ['event_type', 'created_at']
    search_fields = ['task__title', 'user__username', 'description']
    ordering = ['-created_at']
    readonly_fields = ['created_at']

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('task', 'user')

    def event_type_badge(self, obj):
        """显示事件类型徽章"""
        colors = {
            'task_created': '#007bff',
            'task_started': '#28a745',
            'time_wheel_increase': '#ffc107',
            'time_wheel_decrease': '#fd7e14',
            'overtime_added': '#dc3545',
            'voting_started': '#17a2b8',
            'voting_ended': '#6f42c1',
            'vote_passed': '#28a745',
            'vote_failed': '#dc3545',
            'task_completed': '#28a745',
            'task_stopped': '#ffc107',
            'task_failed': '#dc3545',
            'hourly_reward': '#28a745',
        }
        color = colors.get(obj.event_type, '#6c757d')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 2px 8px; '
            'border-radius: 12px; font-size: 10px; font-weight: bold;">{}</span>',
            color,
            obj.get_event_type_display()
        )
    event_type_badge.short_description = '事件类型'
    event_type_badge.admin_order_field = 'event_type'

    def user_info(self, obj):
        """显示用户信息"""
        if obj.user:
            return format_html(
                '<span style="color: #28a745;">{}</span>',
                obj.user.username
            )
        return format_html(
            '<span style="color: #6c757d; font-style: italic;">系统</span>'
        )
    user_info.short_description = '用户'

    def time_change_info(self, obj):
        """显示时间变化信息"""
        if obj.time_change_minutes is not None:
            if obj.time_change_minutes > 0:
                return format_html(
                    '<span style="color: #dc3545;">+{} 分钟</span>',
                    obj.time_change_minutes
                )
            else:
                return format_html(
                    '<span style="color: #28a745;">{} 分钟</span>',
                    obj.time_change_minutes
                )
        return '-'
    time_change_info.short_description = '时间变化'


@admin.register(HourlyReward)
class HourlyRewardAdmin(admin.ModelAdmin):
    """小时奖励管理"""

    list_display = ['task', 'user', 'reward_amount', 'hour_count', 'created_at']
    list_filter = ['reward_amount', 'created_at']
    search_fields = ['task__title', 'user__username']
    ordering = ['-created_at']

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('task', 'user')


@admin.register(TaskSubmissionFile)
class TaskSubmissionFileAdmin(admin.ModelAdmin):
    """任务提交文件管理"""

    list_display = ['task', 'file_name', 'file_size_display', 'created_at']
    list_filter = ['created_at', 'file_type']
    search_fields = ['task__title', 'file_name']
    ordering = ['-created_at']
    readonly_fields = ['created_at', 'file_size', 'file_type']

    fieldsets = (
        ('基本信息', {
            'fields': ('task', 'file_name', 'file_type')
        }),
        ('文件属性', {
            'fields': ('file_size', 'created_at')
        }),
    )

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('task')

    def file_size_display(self, obj):
        """显示文件大小"""
        if obj.file_size:
            if obj.file_size < 1024:
                return f"{obj.file_size} B"
            elif obj.file_size < 1024 * 1024:
                return f"{obj.file_size / 1024:.1f} KB"
            else:
                return f"{obj.file_size / (1024 * 1024):.1f} MB"
        return "-"
    file_size_display.short_description = '文件大小'


@admin.register(TaskParticipant)
class TaskParticipantAdmin(admin.ModelAdmin):
    """任务参与者管理"""

    list_display = [
        'task',
        'participant',
        'status_badge',
        'submitted_at',
        'reviewed_at',
        'reward_amount'
    ]
    list_filter = ['status', 'submitted_at', 'reviewed_at']
    search_fields = ['task__title', 'participant__username']
    ordering = ['-submitted_at']
    readonly_fields = ['submitted_at', 'reviewed_at', 'joined_at']

    fieldsets = (
        ('基本信息', {
            'fields': ('task', 'participant', 'status', 'reward_amount')
        }),
        ('提交信息', {
            'fields': ('submission_text', 'submitted_at')
        }),
        ('审核信息', {
            'fields': ('reviewed_at', 'review_comment'),
            'classes': ('collapse',)
        }),
    )

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('task', 'participant')

    def status_badge(self, obj):
        """显示状态徽章"""
        colors = {
            'pending': '#6c757d',
            'submitted': '#ffc107',
            'approved': '#28a745',
            'rejected': '#dc3545'
        }
        color = colors.get(obj.status, '#6c757d')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 2px 8px; '
            'border-radius: 12px; font-size: 11px; font-weight: bold;">{}</span>',
            color,
            obj.get_status_display()
        )
    status_badge.short_description = '状态'
    status_badge.admin_order_field = 'status'


@admin.register(PinnedUser)
class PinnedUserAdmin(admin.ModelAdmin):
    """置顶用户管理"""

    list_display = ['pinned_user', 'key_holder', 'created_at', 'is_active']
    list_filter = ['created_at', 'key_holder']
    search_fields = ['pinned_user__username', 'key_holder__username']
    ordering = ['-created_at']
    readonly_fields = ['created_at']

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('pinned_user', 'key_holder')

    def is_active(self, obj):
        """显示是否活跃（简单显示为是）"""
        return format_html(
            '<span style="color: #28a745; font-weight: bold;">✓</span>'
        )
    is_active.short_description = '活跃'
