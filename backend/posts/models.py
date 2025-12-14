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
    """评论模型 - 支持两层结构的回复系统"""

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

    # 两层结构支持字段
    root_reply_id = models.UUIDField(
        null=True,
        blank=True,
        help_text="根回复ID - 第一层评论为null，第二层评论指向第一层"
    )
    path = models.CharField(
        max_length=255,
        default='',
        help_text="物化路径 - 格式: root_id 或 root_id.child_id"
    )
    depth = models.IntegerField(
        default=0,
        help_text="评论层级深度 - 0为第一层，1为第二层"
    )
    reply_to_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='received_replies',
        help_text="被回复的用户（用于第二层显示 '@用户名'）"
    )

    # 统计信息
    likes_count = models.IntegerField(default=0, help_text="点赞数")
    replies_count = models.IntegerField(default=0, help_text="回复数（仅第一层使用）")

    # 时间戳
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'comments'
        ordering = ['created_at']
        indexes = [
            models.Index(fields=['post', 'root_reply_id']),
            models.Index(fields=['path']),
            models.Index(fields=['depth']),
        ]
        verbose_name = '评论'
        verbose_name_plural = '评论'

    def __str__(self):
        return f"{self.user.username}: {self.content[:30]}..."

    def save(self, *args, **kwargs):
        """重写save方法，自动设置path和depth"""
        is_new = self._state.adding  # 记录是否为新创建的评论

        if is_new:  # 新创建的评论
            if self.parent is None:
                # 第一层评论
                self.depth = 0
                self.root_reply_id = None
                self.reply_to_user = None
                # path将在保存后设置为自己的ID
            else:
                # 有parent的评论，需要设置为第二层
                # 首先确保parent存在并获取完整信息
                try:
                    parent_comment = Comment.objects.get(id=self.parent.id)

                    if parent_comment.depth == 0:
                        # 回复第一层评论
                        self.depth = 1
                        self.root_reply_id = parent_comment.id
                        self.reply_to_user = parent_comment.user
                    else:
                        # 回复第二层评论，强制归属到第一层
                        # 找到根评论
                        if parent_comment.root_reply_id:
                            root_comment = Comment.objects.get(id=parent_comment.root_reply_id)
                        else:
                            # 如果parent的root_reply_id为空，说明数据有问题，尝试修复
                            root_comment = parent_comment
                            while root_comment.parent is not None:
                                root_comment = Comment.objects.get(id=root_comment.parent.id)

                        self.depth = 1
                        self.root_reply_id = root_comment.id
                        self.reply_to_user = parent_comment.user
                        # 更新parent指向第一层评论
                        self.parent = root_comment

                except Comment.DoesNotExist:
                    # 如果parent不存在，作为第一层评论处理
                    self.depth = 0
                    self.root_reply_id = None
                    self.reply_to_user = None
                    self.parent = None

        super().save(*args, **kwargs)

        # 设置path（只对新创建的评论或path为空的评论）
        if is_new or not self.path:
            if self.depth == 0:
                new_path = str(self.id)
            else:
                new_path = f"{self.root_reply_id}.{self.id}"

            # 更新path，避免递归调用save
            Comment.objects.filter(id=self.id).update(path=new_path)
            self.path = new_path  # 更新实例的path属性

        # 更新第一层评论的回复数（只对新创建的第二层评论）
        if is_new and self.depth == 1 and self.root_reply_id:
            Comment.objects.filter(id=self.root_reply_id).update(
                replies_count=models.F('replies_count') + 1
            )

    def delete(self, *args, **kwargs):
        """重写delete方法，更新回复数"""
        if self.depth == 1 and self.root_reply_id:
            Comment.objects.filter(id=self.root_reply_id).update(
                replies_count=models.F('replies_count') - 1
            )
        super().delete(*args, **kwargs)

    @property
    def is_root_comment(self):
        """是否为第一层评论"""
        return self.depth == 0

    @property
    def is_reply(self):
        """是否为第二层回复"""
        return self.depth == 1


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
