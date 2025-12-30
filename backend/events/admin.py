from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from django.contrib import messages
from .models import (
    EventDefinition,
    EventEffect,
    EventOccurrence,
    EventEffectExecution,
    UserGameEffect,
    UserCoinsMultiplier
)


class EventEffectInline(admin.TabularInline):
    model = EventEffect
    extra = 1
    fields = ['effect_type', 'target_type', 'effect_parameters', 'target_parameters', 'duration_minutes', 'priority', 'is_active']
    readonly_fields = []

    def get_formset(self, request, obj=None, **kwargs):
        formset = super().get_formset(request, obj, **kwargs)

        # 为JSON字段提供帮助文本
        if hasattr(formset.form.base_fields.get('effect_parameters'), 'help_text'):
            formset.form.base_fields['effect_parameters'].help_text = (
                '效果参数JSON格式，例如: {"amount": 10, "item_type": "photo_paper"}'
            )

        if hasattr(formset.form.base_fields.get('target_parameters'), 'help_text'):
            formset.form.base_fields['target_parameters'].help_text = (
                '目标参数JSON格式，例如: {"percentage": 50, "levels": [1, 2]}'
            )

        return formset


@admin.register(EventDefinition)
class EventDefinitionAdmin(admin.ModelAdmin):
    list_display = [
        'name',
        'category_badge',
        'schedule_type_badge',
        'is_active_badge',
        'effects_count',
        'recent_occurrences_count',
        'created_by',
        'created_at'
    ]
    list_filter = ['category', 'schedule_type', 'is_active', 'created_at']
    search_fields = ['name', 'title', 'description']
    readonly_fields = ['created_by', 'created_at', 'updated_at']
    inlines = [EventEffectInline]

    fieldsets = [
        ('基本信息', {
            'fields': ['name', 'category', 'title', 'description', 'is_active']
        }),
        ('调度配置', {
            'fields': ['schedule_type', 'interval_value', 'cron_expression'],
            'description': '设置事件的触发方式和频率'
        }),
        ('元数据', {
            'fields': ['created_by', 'created_at', 'updated_at'],
            'classes': ['collapse']
        })
    ]

    def category_badge(self, obj):
        colors = {
            'weather': '#2196F3',  # 蓝色
            'magic': '#9C27B0',    # 紫色
            'system': '#FF9800',   # 橙色
            'special': '#4CAF50'   # 绿色
        }
        color = colors.get(obj.category, '#757575')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 2px 8px; border-radius: 3px; font-size: 11px;">{}</span>',
            color, obj.get_category_display()
        )
    category_badge.short_description = '类别'

    def schedule_type_badge(self, obj):
        colors = {
            'manual': '#757575',
            'interval_hours': '#2196F3',
            'interval_days': '#4CAF50',
            'cron': '#9C27B0'
        }
        color = colors.get(obj.schedule_type, '#757575')

        schedule_text = obj.get_schedule_type_display()
        if obj.interval_value and obj.schedule_type in ['interval_hours', 'interval_days']:
            unit = '小时' if obj.schedule_type == 'interval_hours' else '天'
            schedule_text = f"每{obj.interval_value}{unit}"

        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color, schedule_text
        )
    schedule_type_badge.short_description = '调度类型'

    def is_active_badge(self, obj):
        if obj.is_active:
            return format_html('<span style="color: #4CAF50;">● 启用</span>')
        return format_html('<span style="color: #F44336;">● 禁用</span>')
    is_active_badge.short_description = '状态'

    def effects_count(self, obj):
        count = obj.effects.count()
        active_count = obj.effects.filter(is_active=True).count()
        return format_html('{} 个效果 ({} 活跃)', count, active_count)
    effects_count.short_description = '效果数量'

    def recent_occurrences_count(self, obj):
        from django.utils import timezone
        from datetime import timedelta

        recent_count = obj.occurrences.filter(
            created_at__gte=timezone.now() - timedelta(days=7)
        ).count()

        return f"近7天: {recent_count}次"
    recent_occurrences_count.short_description = '最近执行'

    actions = ['enable_events', 'disable_events', 'trigger_manual_events', 'duplicate_events']

    def enable_events(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f'已启用 {updated} 个事件定义', messages.SUCCESS)
    enable_events.short_description = '启用选中的事件'

    def disable_events(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f'已禁用 {updated} 个事件定义', messages.SUCCESS)
    disable_events.short_description = '禁用选中的事件'

    def trigger_manual_events(self, request, queryset):
        from .celery_tasks import trigger_manual_event
        triggered = 0
        for event in queryset:
            trigger_manual_event.delay(str(event.id), request.user.id)
            triggered += 1
        self.message_user(request, f'已触发 {triggered} 个事件（异步执行中...）', messages.INFO)
    trigger_manual_events.short_description = '手动触发选中的事件'

    def duplicate_events(self, request, queryset):
        duplicated = 0
        for event in queryset:
            # 复制事件定义
            new_event = EventDefinition.objects.create(
                name=f"{event.name}_副本",
                category=event.category,
                title=f"{event.title} (副本)",
                description=event.description,
                schedule_type='manual',  # 副本默认为手动触发
                is_active=False,  # 副本默认禁用
                created_by=request.user
            )

            # 复制效果
            for effect in event.effects.all():
                EventEffect.objects.create(
                    event_definition=new_event,
                    effect_type=effect.effect_type,
                    target_type=effect.target_type,
                    effect_parameters=effect.effect_parameters.copy(),
                    target_parameters=effect.target_parameters.copy(),
                    duration_minutes=effect.duration_minutes,
                    priority=effect.priority,
                    is_active=effect.is_active
                )

            duplicated += 1

        self.message_user(request, f'已复制 {duplicated} 个事件定义', messages.SUCCESS)
    duplicate_events.short_description = '复制选中的事件'

    def save_model(self, request, obj, form, change):
        if not change:  # 新建时设置创建者
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(EventOccurrence)
class EventOccurrenceAdmin(admin.ModelAdmin):
    list_display = [
        'event_definition',
        'status_badge',
        'scheduled_at',
        'duration_display',
        'affected_users_count',
        'trigger_type_badge',
        'triggered_by'
    ]
    list_filter = ['status', 'trigger_type', 'scheduled_at', 'event_definition__category']
    search_fields = ['event_definition__name', 'event_definition__title']
    readonly_fields = ['execution_log_display', 'error_message', 'duration_display']
    date_hierarchy = 'scheduled_at'

    fieldsets = [
        ('基本信息', {
            'fields': ['event_definition', 'status', 'trigger_type', 'triggered_by']
        }),
        ('时间信息', {
            'fields': ['scheduled_at', 'started_at', 'completed_at', 'duration_display']
        }),
        ('执行结果', {
            'fields': ['affected_users_count', 'execution_log_display', 'error_message']
        })
    ]

    def status_badge(self, obj):
        colors = {
            'pending': '#FF9800',
            'executing': '#2196F3',
            'completed': '#4CAF50',
            'failed': '#F44336',
            'cancelled': '#757575'
        }
        color = colors.get(obj.status, '#757575')
        return format_html(
            '<span style="color: {}; font-weight: bold;">● {}</span>',
            color, obj.get_status_display()
        )
    status_badge.short_description = '状态'

    def trigger_type_badge(self, obj):
        if obj.trigger_type == 'manual':
            return format_html('<span style="color: #9C27B0;">🔧 手动</span>')
        return format_html('<span style="color: #4CAF50;">⏰ 自动</span>')
    trigger_type_badge.short_description = '触发方式'

    def duration_display(self, obj):
        if obj.duration_seconds:
            return f"{obj.duration_seconds:.2f} 秒"
        return "未完成"
    duration_display.short_description = '执行时长'

    def execution_log_display(self, obj):
        if not obj.execution_log:
            return '无执行日志'

        html = '<div style="max-height: 400px; overflow-y: auto; font-family: monospace; font-size: 12px;">'

        for i, log_entry in enumerate(obj.execution_log, 1):
            effect_type = log_entry.get('effect_type', '未知')
            target_type = log_entry.get('target_type', '未知')
            affected_count = log_entry.get('affected_count', 0)
            total_targets = log_entry.get('total_targets', 0)

            # 状态颜色
            if 'error' in log_entry:
                status_color = '#F44336'
                status_text = '❌ 失败'
            elif affected_count > 0:
                status_color = '#4CAF50'
                status_text = '✅ 成功'
            else:
                status_color = '#FF9800'
                status_text = '⚠️ 无影响'

            html += f'''
            <div style="margin-bottom: 10px; padding: 8px; border: 1px solid #ddd; border-radius: 4px;">
                <div style="font-weight: bold; color: {status_color};">{status_text} 效果 #{i}: {effect_type}</div>
                <div>目标类型: {target_type}</div>
                <div>影响用户: {affected_count}/{total_targets}</div>
            '''

            if 'error' in log_entry:
                html += f'<div style="color: #F44336;">错误: {log_entry["error"]}</div>'

            html += '</div>'

        html += '</div>'
        return mark_safe(html)
    execution_log_display.short_description = '执行日志'

    actions = ['retry_failed_events', 'cancel_pending_events']

    def retry_failed_events(self, request, queryset):
        from .celery_tasks import trigger_manual_event

        failed_events = queryset.filter(status='failed')
        retried = 0

        for occurrence in failed_events:
            trigger_manual_event.delay(str(occurrence.event_definition.id), request.user.id)
            retried += 1

        self.message_user(request, f'已重试 {retried} 个失败事件', messages.INFO)
    retry_failed_events.short_description = '重试失败的事件'

    def cancel_pending_events(self, request, queryset):
        cancelled = queryset.filter(status='pending').update(status='cancelled')
        self.message_user(request, f'已取消 {cancelled} 个待执行事件', messages.SUCCESS)
    cancel_pending_events.short_description = '取消待执行的事件'


@admin.register(EventEffectExecution)
class EventEffectExecutionAdmin(admin.ModelAdmin):
    list_display = [
        'occurrence_link',
        'effect_type_display',
        'target_user',
        'executed_at',
        'status_display',
        'expires_at'
    ]
    list_filter = ['executed_at', 'is_expired', 'is_rolled_back', 'effect__effect_type']
    search_fields = ['target_user__username', 'occurrence__event_definition__name']
    readonly_fields = ['effect_data_display', 'rollback_data_display']
    date_hierarchy = 'executed_at'

    def occurrence_link(self, obj):
        url = reverse('admin:events_eventoccurrence_change', args=[obj.occurrence.id])
        return format_html('<a href="{}">{}</a>', url, obj.occurrence.event_definition.name)
    occurrence_link.short_description = '事件'

    def effect_type_display(self, obj):
        return obj.effect.get_effect_type_display()
    effect_type_display.short_description = '效果类型'

    def status_display(self, obj):
        if obj.is_rolled_back:
            return format_html('<span style="color: #FF9800;">🔄 已回滚</span>')
        elif obj.is_expired:
            return format_html('<span style="color: #757575;">⏰ 已过期</span>')
        elif obj.is_active:
            return format_html('<span style="color: #4CAF50;">✅ 活跃</span>')
        else:
            return format_html('<span style="color: #F44336;">❌ 无效</span>')
    status_display.short_description = '状态'

    def effect_data_display(self, obj):
        import json
        try:
            formatted_data = json.dumps(obj.effect_data, indent=2, ensure_ascii=False)
            return mark_safe(f'<pre style="max-height: 200px; overflow-y: auto;">{formatted_data}</pre>')
        except:
            return str(obj.effect_data)
    effect_data_display.short_description = '效果数据'

    def rollback_data_display(self, obj):
        import json
        try:
            formatted_data = json.dumps(obj.rollback_data, indent=2, ensure_ascii=False)
            return mark_safe(f'<pre style="max-height: 200px; overflow-y: auto;">{formatted_data}</pre>')
        except:
            return str(obj.rollback_data)
    rollback_data_display.short_description = '回滚数据'


@admin.register(UserGameEffect)
class UserGameEffectAdmin(admin.ModelAdmin):
    list_display = ['user', 'effect_type', 'multiplier', 'expires_at', 'is_active_display']
    list_filter = ['effect_type', 'is_active', 'expires_at']
    search_fields = ['user__username']
    readonly_fields = ['event_execution', 'created_at']

    def is_active_display(self, obj):
        if obj.is_valid:
            return format_html('<span style="color: #4CAF50;">✅ 有效</span>')
        return format_html('<span style="color: #F44336;">❌ 无效</span>')
    is_active_display.short_description = '状态'

    actions = ['deactivate_effects']

    def deactivate_effects(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f'已停用 {updated} 个游戏效果', messages.SUCCESS)
    deactivate_effects.short_description = '停用选中的效果'


@admin.register(UserCoinsMultiplier)
class UserCoinsMultiplierAdmin(admin.ModelAdmin):
    list_display = ['user', 'multiplier', 'expires_at', 'is_active_display']
    list_filter = ['is_active', 'expires_at']
    search_fields = ['user__username']
    readonly_fields = ['event_execution', 'created_at']

    def is_active_display(self, obj):
        if obj.is_valid:
            return format_html('<span style="color: #4CAF50;">✅ 有效</span>')
        return format_html('<span style="color: #F44336;">❌ 无效</span>')
    is_active_display.short_description = '状态'

    actions = ['deactivate_multipliers']

    def deactivate_multipliers(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f'已停用 {updated} 个积分倍数', messages.SUCCESS)
    deactivate_multipliers.short_description = '停用选中的倍数'


# 自定义管理站点标题
admin.site.site_header = 'Lockup 事件管理系统'
admin.site.site_title = 'Lockup Events'
admin.site.index_title = '事件系统管理'