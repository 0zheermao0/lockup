from django.db import models
from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
import uuid


class Post(models.Model):
    """动态模型"""

    POST_TYPES = [
        ('normal', '普通动态'),
        ('checkin', '打卡任务'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='posts',
        help_text="发布用户"
    )
    post_type = models.CharField(
        max_length=10,
        choices=POST_TYPES,
        default='normal',
        help_text="动态类型"
    )
    content = models.TextField(
        max_length=2000,
        help_text="动态内容"
    )

    # 地理位置信息
    latitude = models.DecimalField(
        max_digits=10,
        decimal_places=7,
        null=True,
        blank=True,
        help_text="纬度"
    )
    longitude = models.DecimalField(
        max_digits=10,
        decimal_places=7,
        null=True,
        blank=True,
        help_text="经度"
    )
    location_name = models.CharField(
        max_length=200,
        blank=True,
        help_text="位置名称"
    )

    # 打卡验证（仅用于打卡任务）
    verification_string = models.CharField(
        max_length=50,
        blank=True,
        help_text="验证字符串（用于打卡任务）"
    )
    is_verified = models.BooleanField(
        default=False,
        help_text="是否已验证"
    )

    # 统计信息
    likes_count = models.IntegerField(default=0, help_text="点赞数")
    comments_count = models.IntegerField(default=0, help_text="评论数")

    # 时间戳
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'posts'
        ordering = ['-created_at']
        verbose_name = '动态'
        verbose_name_plural = '动态'

    def __str__(self):
        return f"{self.user.username}: {self.content[:50]}..."


class PostImage(models.Model):
    """动态图片模型"""

    post = models.ForeignKey(
        Post,
        on_delete=models.CASCADE,
        related_name='images',
        help_text="所属动态"
    )
    image = models.ImageField(
        upload_to='posts/images/',
        help_text="图片文件"
    )
    order = models.IntegerField(
        default=0,
        help_text="图片顺序"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'post_images'
        ordering = ['order']
        verbose_name = '动态图片'
        verbose_name_plural = '动态图片'

    def __str__(self):
        return f"{self.post.user.username} - Image {self.order}"


class PostLike(models.Model):
    """动态点赞模型"""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='post_likes',
        help_text="点赞用户"
    )
    post = models.ForeignKey(
        Post,
        on_delete=models.CASCADE,
        related_name='likes',
        help_text="被点赞的动态"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'post_likes'
        unique_together = ['user', 'post']
        verbose_name = '动态点赞'
        verbose_name_plural = '动态点赞'

    def __str__(self):
        return f"{self.user.username} likes {self.post.id}"


class Comment(models.Model):
    """评论模型"""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='comments',
        help_text="评论用户"
    )
    post = models.ForeignKey(
        Post,
        on_delete=models.CASCADE,
        related_name='comments',
        help_text="所属动态"
    )
    content = models.TextField(
        max_length=500,
        help_text="评论内容"
    )
    parent = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='replies',
        help_text="父评论（用于回复）"
    )

    # 统计信息
    likes_count = models.IntegerField(default=0, help_text="点赞数")

    # 时间戳
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'comments'
        ordering = ['created_at']
        verbose_name = '评论'
        verbose_name_plural = '评论'

    def __str__(self):
        return f"{self.user.username}: {self.content[:30]}..."


class CommentImage(models.Model):
    """评论图片模型"""

    comment = models.ForeignKey(
        Comment,
        on_delete=models.CASCADE,
        related_name='images',
        help_text="所属评论"
    )
    image = models.ImageField(
        upload_to='comments/images/',
        help_text="图片文件"
    )
    order = models.IntegerField(
        default=0,
        help_text="图片顺序"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'comment_images'
        ordering = ['order']
        verbose_name = '评论图片'
        verbose_name_plural = '评论图片'

    def __str__(self):
        return f"{self.comment.user.username} - Comment Image {self.order}"


class CommentLike(models.Model):
    """评论点赞模型"""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='comment_likes',
        help_text="点赞用户"
    )
    comment = models.ForeignKey(
        Comment,
        on_delete=models.CASCADE,
        related_name='likes',
        help_text="被点赞的评论"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'comment_likes'
        unique_together = ['user', 'comment']
        verbose_name = '评论点赞'
        verbose_name_plural = '评论点赞'

    def __str__(self):
        return f"{self.user.username} likes comment {self.comment.id}"
