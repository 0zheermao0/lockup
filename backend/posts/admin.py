from django.contrib import admin
from django.utils.html import format_html
from django.db.models import Count
from .models import (
    Post, PostImage, PostLike, Comment,
    CommentImage, CommentLike
)


@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    """动态管理"""

    list_display = [
        'content_preview',
        'user',
        'post_type_badge',
        'verification_badge',
        'stats_info',
        'created_at'
    ]
    list_filter = [
        'post_type',
        'is_verified',
        'created_at',
        'user'
    ]
    search_fields = [
        'content',
        'user__username',
        'location_name'
    ]
    ordering = ['-created_at']
    readonly_fields = ['created_at', 'updated_at']

    fieldsets = (
        ('基本信息', {
            'fields': (
                'user', 'post_type', 'content',
                'is_verified', 'verification_string'
            )
        }),
        ('位置信息', {
            'fields': (
                'latitude', 'longitude', 'location_name'
            ),
            'classes': ('collapse',)
        }),
        ('统计信息', {
            'fields': (
                'likes_count', 'comments_count'
            ),
            'classes': ('collapse',)
        }),
        ('时间信息', {
            'fields': (
                'created_at', 'updated_at'
            )
        }),
    )

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user')

    def content_preview(self, obj):
        """显示内容预览"""
        preview = obj.content[:50]
        if len(obj.content) > 50:
            preview += '...'
        return format_html(
            '<span title="{}">{}</span>',
            obj.content,
            preview
        )
    content_preview.short_description = '内容预览'

    def post_type_badge(self, obj):
        """显示动态类型徽章"""
        colors = {
            'normal': '#007bff',
            'checkin': '#28a745'
        }
        color = colors.get(obj.post_type, '#6c757d')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 2px 8px; '
            'border-radius: 12px; font-size: 11px; font-weight: bold;">{}</span>',
            color,
            obj.get_post_type_display()
        )
    post_type_badge.short_description = '类型'
    post_type_badge.admin_order_field = 'post_type'

    def verification_badge(self, obj):
        """显示验证状态徽章"""
        if obj.post_type != 'checkin':
            return '-'
        if obj.is_verified:
            return format_html(
                '<span style="background-color: #28a745; color: white; padding: 2px 8px; '
                'border-radius: 12px; font-size: 11px; font-weight: bold;">已验证</span>'
            )
        return format_html(
            '<span style="background-color: #dc3545; color: white; padding: 2px 8px; '
            'border-radius: 12px; font-size: 11px; font-weight: bold;">未验证</span>'
        )
    verification_badge.short_description = '验证状态'

    def stats_info(self, obj):
        """显示统计信息"""
        return format_html(
            '<span style="color: #dc3545;">❤️ {}</span> '
            '<span style="color: #007bff;">💬 {}</span>',
            obj.likes_count,
            obj.comments_count
        )
    stats_info.short_description = '统计'

    list_per_page = 20


@admin.register(PostImage)
class PostImageAdmin(admin.ModelAdmin):
    """动态图片管理"""

    list_display = ['post_info', 'image_preview', 'order', 'created_at']
    list_filter = ['order', 'created_at']
    search_fields = ['post__content', 'post__user__username']
    ordering = ['post', 'order']
    readonly_fields = ['created_at']

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('post')

    def post_info(self, obj):
        """显示动态信息"""
        return format_html(
            '<strong>{}</strong><br><small>{}</small>',
            obj.post.user.username,
            obj.post.content[:30] + '...' if len(obj.post.content) > 30 else obj.post.content
        )
    post_info.short_description = '动态'

    def image_preview(self, obj):
        """显示图片预览"""
        if obj.image:
            return format_html(
                '<img src="{}" width="50" height="50" style="object-fit: cover; border-radius: 4px;" />',
                obj.image.url
            )
        return '无图片'
    image_preview.short_description = '图片'


@admin.register(PostLike)
class PostLikeAdmin(admin.ModelAdmin):
    """动态点赞管理"""

    list_display = ['user', 'post_info', 'created_at']
    list_filter = ['created_at']
    search_fields = ['user__username', 'post__content']
    ordering = ['-created_at']

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user', 'post')

    def post_info(self, obj):
        """显示动态信息"""
        return format_html(
            '<strong>{}</strong><br><small>{}</small>',
            obj.post.user.username,
            obj.post.content[:30] + '...' if len(obj.post.content) > 30 else obj.post.content
        )
    post_info.short_description = '动态'


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    """评论管理"""

    list_display = [
        'content_preview',
        'user',
        'post_info',
        'parent_info',
        'stats_info',
        'created_at'
    ]
    list_filter = ['created_at', 'user']
    search_fields = [
        'content',
        'user__username',
        'post__content'
    ]
    ordering = ['-created_at']
    readonly_fields = ['created_at', 'updated_at']

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user', 'post', 'parent')

    def content_preview(self, obj):
        """显示内容预览"""
        preview = obj.content[:30]
        if len(obj.content) > 30:
            preview += '...'
        return format_html(
            '<span title="{}">{}</span>',
            obj.content,
            preview
        )
    content_preview.short_description = '内容'

    def post_info(self, obj):
        """显示动态信息"""
        return format_html(
            '<strong>{}</strong><br><small>{}</small>',
            obj.post.user.username,
            obj.post.content[:30] + '...' if len(obj.post.content) > 30 else obj.post.content
        )
    post_info.short_description = '动态'

    def parent_info(self, obj):
        """显示父评论信息"""
        if obj.parent:
            return format_html(
                '<small>{}</small>',
                obj.parent.content[:20] + '...' if len(obj.parent.content) > 20 else obj.parent.content
            )
        return '-'
    parent_info.short_description = '回复'

    def stats_info(self, obj):
        """显示统计信息"""
        return format_html(
            '<span style="color: #dc3545;">❤️ {}</span>',
            obj.likes_count
        )
    stats_info.short_description = '点赞数'

    list_per_page = 25


@admin.register(CommentImage)
class CommentImageAdmin(admin.ModelAdmin):
    """评论图片管理"""

    list_display = ['comment_info', 'image_preview', 'order', 'created_at']
    list_filter = ['order', 'created_at']
    search_fields = ['comment__content', 'comment__user__username']
    ordering = ['comment', 'order']
    readonly_fields = ['created_at']

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('comment')

    def comment_info(self, obj):
        """显示评论信息"""
        return format_html(
            '<strong>{}</strong><br><small>{}</small>',
            obj.comment.user.username,
            obj.comment.content[:20] + '...' if len(obj.comment.content) > 20 else obj.comment.content
        )
    comment_info.short_description = '评论'

    def image_preview(self, obj):
        """显示图片预览"""
        if obj.image:
            return format_html(
                '<img src="{}" width="50" height="50" style="object-fit: cover; border-radius: 4px;" />',
                obj.image.url
            )
        return '无图片'
    image_preview.short_description = '图片'


@admin.register(CommentLike)
class CommentLikeAdmin(admin.ModelAdmin):
    """评论点赞管理"""

    list_display = ['user', 'comment_info', 'created_at']
    list_filter = ['created_at']
    search_fields = ['user__username', 'comment__content']
    ordering = ['-created_at']

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user', 'comment')

    def comment_info(self, obj):
        """显示评论信息"""
        return format_html(
            '<strong>{}</strong><br><small>{}</small>',
            obj.comment.user.username,
            obj.comment.content[:20] + '...' if len(obj.comment.content) > 20 else obj.comment.content
        )
    comment_info.short_description = '评论'
