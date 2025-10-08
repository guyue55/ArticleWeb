"""Article models for the application."""

from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import MinLengthValidator
from django.utils import timezone

from apps.common.models import BaseModel, ActiveManager, AllManager

User = get_user_model()


class Category(BaseModel):
    """Article category model."""
    
    name = models.CharField(
        verbose_name="分类名称",
        max_length=64,
        unique=True,
        help_text="文章分类名称",
        db_comment="文章分类的显示名称，必须唯一"
    )
    slug = models.SlugField(
        verbose_name="分类别名",
        max_length=64,
        unique=True,
        help_text="分类URL别名",
        db_comment="分类的URL友好别名，用于生成SEO友好的链接"
    )
    description = models.TextField(
        verbose_name="分类描述",
        max_length=255,
        default='',
        help_text="分类详细描述",
        db_comment="分类的详细描述信息，用于SEO和用户理解"
    )
    parent_uuid = models.CharField(
        verbose_name="父分类UUID",
        max_length=255,
        blank=True,
        default='',
        help_text="父级分类的UUID，为空表示顶级分类",
        db_comment="父级分类的UUID标识，用于构建分类层级结构"
    )
    sort_order = models.PositiveIntegerField(
        verbose_name="排序",
        default=0,
        help_text="分类排序，数字越小越靠前",
        db_comment="分类显示顺序，数值越小排序越靠前"
    )
    
    # Custom managers
    objects = ActiveManager()
    all_objects = AllManager()
    
    class Meta:
        verbose_name = "文章分类"
        verbose_name_plural = "文章分类"
        db_table = 'article_categories'
        ordering = ['sort_order', 'name']
        indexes = [
            models.Index(fields=['slug'], name='idx_category_slug'),
            models.Index(fields=['parent_uuid', 'sort_order'], name='idx_category_parent_sort'),
            models.Index(fields=['is_active', 'create_time'], name='idx_category_active_created'),
        ]
    
    def __str__(self):
        return self.name
    
    @property
    def full_path(self):
        """Return the full category path."""
        if self.parent_uuid:
            # Note: This would require a database query to get parent category
            # For now, just return the current category name
            return f"Parent({self.parent_uuid}) > {self.name}"
        return self.name


class Article(BaseModel):
    """Article model."""
    
    STATUS_CHOICES = [
        (1, '草稿'),
        (2, '已发布'),
        (3, '已下线'),
    ]
    
    title = models.CharField(
        verbose_name="文章标题",
        max_length=255,
        validators=[MinLengthValidator(5)],
        help_text="文章标题，最少5个字符",
        db_comment="文章的标题，用于显示和SEO，最少5个字符"
    )
    slug = models.SlugField(
        verbose_name="文章别名",
        max_length=255,
        unique=True,
        help_text="文章URL别名",
        db_comment="文章的URL友好别名，用于生成SEO友好的链接，必须唯一"
    )
    summary = models.TextField(
        verbose_name="文章摘要",
        max_length=500,
        default='',
        help_text="文章摘要，最多500字符",
        db_comment="文章的简要摘要，用于列表页显示和SEO描述"
    )
    content = models.TextField(
        verbose_name="文章内容",
        help_text="文章正文内容",
        db_comment="文章的完整正文内容，支持HTML格式"
    )
    author_uuid = models.CharField(
        verbose_name="作者UUID",
        max_length=255,
        help_text="文章作者的UUID",
        db_comment="文章作者的UUID标识，关联到用户表"
    )
    category_uuid = models.CharField(
        verbose_name="分类UUID",
        max_length=255,
        help_text="文章所属分类的UUID",
        db_comment="文章所属分类的UUID标识，关联到分类表"
    )
    featured_image = models.CharField(
        verbose_name="特色图片",
        max_length=255,
        blank=True,
        default='',
        help_text="文章特色图片路径",
        db_comment="文章的特色图片路径或URL，用于列表页和详情页展示"
    )
    status = models.PositiveSmallIntegerField(
        verbose_name="状态",
        choices=STATUS_CHOICES,
        default=1,
        help_text="文章状态",
        db_comment="文章发布状态：1-草稿，2-已发布，3-已下线"
    )
    is_featured = models.BooleanField(
        verbose_name="是否推荐",
        default=False,
        help_text="是否为推荐文章",
        db_comment="是否为推荐文章，True表示推荐显示"
    )
    is_top = models.BooleanField(
        verbose_name="是否置顶",
        default=False,
        help_text="是否置顶显示",
        db_comment="是否置顶显示，True表示在列表顶部显示"
    )
    view_count = models.PositiveIntegerField(
        verbose_name="浏览次数",
        default=0,
        help_text="文章浏览次数",
        db_comment="文章的浏览次数统计，每次访问自动增加"
    )
    download_count = models.PositiveIntegerField(
        verbose_name="下载次数",
        default=0,
        help_text="文章下载次数",
        db_comment="文章附件的下载次数统计"
    )
    claim_count = models.PositiveIntegerField(
        verbose_name="领取次数",
        default=0,
        help_text="文章领取次数",
        db_comment="文章的领取次数统计，用户领取时增加"
    )
    file_attachment = models.FileField(
        verbose_name="附件文件",
        upload_to='articles/files/%Y/%m/',
        blank=True,
        null=True,
        help_text="可下载的附件文件",
        db_comment="文章的附件文件，存储在指定目录下"
    )
    file_size = models.PositiveIntegerField(
        verbose_name="文件大小",
        default=0,
        help_text="附件文件大小（字节）",
        db_comment="附件文件的大小，以字节为单位"
    )
    file_info = models.JSONField(
        verbose_name="文件信息",
        default=dict,
        blank=True,
        help_text="文章相关文件信息（MD、HTML、META等）",
        db_comment="存储文章相关的多个文件信息，包括MD、HTML、META文件的路径等"
    )
    is_downloadable = models.BooleanField(
        verbose_name="是否可下载",
        default=False,
        help_text="是否提供文件下载",
        db_comment="是否允许用户下载附件，True表示可下载"
    )
    is_claimable = models.BooleanField(
        verbose_name="是否可领取",
        default=True,
        help_text="是否允许用户领取",
        db_comment="是否允许用户领取文章，True表示可领取"
    )
    published_at = models.DateTimeField(
        verbose_name="发布时间",
        null=True,
        blank=True,
        help_text="文章发布时间",
        db_comment="文章的发布时间，状态变为已发布时自动设置"
    )
    
    # Custom managers
    objects = ActiveManager()
    all_objects = AllManager()
    
    class Meta:
        verbose_name = "文章"
        verbose_name_plural = "文章"
        db_table = 'articles'
        ordering = ['-is_top', '-published_at', '-create_time']
        indexes = [
            models.Index(fields=['slug'], name='idx_article_slug'),
            models.Index(fields=['author_uuid', 'status'], name='idx_article_author_status'),
            models.Index(fields=['category_uuid', 'status'], name='idx_article_category_status'),
            models.Index(fields=['status', 'published_at'], name='idx_article_status_published'),
            models.Index(fields=['is_featured', 'status'], name='idx_article_featured_status'),
            models.Index(fields=['is_top', 'status'], name='idx_article_top_status'),
            models.Index(fields=['is_active', 'create_time'], name='idx_article_active_created'),
        ]
    
    def __str__(self):
        return self.title
    
    def save(self, *args, **kwargs):
        """Override save to set published_at when status changes to published."""
        if self.status == 2 and not self.published_at:
            self.published_at = timezone.now()
        super().save(*args, **kwargs)
    
    @property
    def is_published(self):
        """Check if article is published."""
        return self.status == 2 and self.is_active
    
    def get_absolute_url(self):
        """Return the absolute URL for the article."""
        return f"/articles/{self.slug}/"
    
    def increment_view_count(self):
        """Increment view count."""
        self.view_count += 1
        self.save(update_fields=['view_count'])








class ArticleClaim(BaseModel):
    """Article claim model for tracking user claims."""
    
    article_uuid = models.CharField(
        verbose_name="文章UUID",
        max_length=255,
        help_text="领取的文章UUID",
        db_comment="被领取文章的UUID标识，关联到文章表"
    )
    user_uuid = models.CharField(
        verbose_name="用户UUID",
        max_length=255,
        help_text="领取的用户UUID",
        db_comment="领取用户的UUID标识，关联到用户表"
    )
    claimed_at = models.DateTimeField(
        verbose_name="领取时间",
        auto_now_add=True,
        help_text="文章领取时间",
        db_comment="用户领取文章的具体时间戳"
    )
    
    # Custom managers
    objects = ActiveManager()
    all_objects = AllManager()
    
    class Meta:
        verbose_name = "文章领取"
        verbose_name_plural = "文章领取"
        db_table = 'article_claims'
        unique_together = ['article_uuid', 'user_uuid']
        indexes = [
            models.Index(fields=['article_uuid', 'claimed_at'], name='idx_claim_article_claimed'),
            models.Index(fields=['user_uuid', 'claimed_at'], name='idx_claim_user_claimed'),
            models.Index(fields=['is_active', 'create_time'], name='idx_claim_active_created'),
        ]
    
    def __str__(self):
        return f"领取 {self.id} - 文章UUID: {self.article_uuid}"


class ArticleDownload(BaseModel):
    """Article download model for tracking downloads."""
    
    article_uuid = models.CharField(
        verbose_name="文章UUID",
        max_length=255,
        help_text="下载的文章UUID",
        db_comment="被下载文章的UUID标识，关联到文章表"
    )
    user_uuid = models.CharField(
        verbose_name="用户UUID",
        max_length=255,
        help_text="下载的用户UUID",
        db_comment="下载用户的UUID标识，关联到用户表"
    )
    file_type = models.CharField(
        verbose_name="文件类型",
        max_length=20,
        default="md",
        help_text="下载的文件类型（md/html/meta）",
        db_comment="下载的文件类型，用于统计不同类型文件的下载情况"
    )
    downloaded_at = models.DateTimeField(
        verbose_name="下载时间",
        auto_now_add=True,
        help_text="文章下载时间",
        db_comment="用户下载文章的具体时间戳"
    )
    ip_address = models.GenericIPAddressField(
        verbose_name="IP地址",
        null=True,
        blank=True,
        help_text="下载时的IP地址",
        db_comment="用户下载时的IP地址，用于统计和安全监控"
    )
    user_agent = models.TextField(
        verbose_name="用户代理",
        blank=True,
        help_text="下载时的用户代理信息",
        db_comment="用户下载时的浏览器用户代理字符串"
    )
    
    # Custom managers
    objects = ActiveManager()
    all_objects = AllManager()
    
    class Meta:
        verbose_name = "文章下载"
        verbose_name_plural = "文章下载"
        db_table = 'article_downloads'
        indexes = [
            models.Index(fields=['article_uuid', 'downloaded_at'], name='idx_dl_article_downloaded'),
            models.Index(fields=['user_uuid', 'downloaded_at'], name='idx_dl_user_downloaded'),
            models.Index(fields=['ip_address', 'downloaded_at'], name='idx_dl_ip_downloaded'),
            models.Index(fields=['file_type', 'downloaded_at'], name='idx_dl_filetype_downloaded'),
            models.Index(fields=['is_active', 'create_time'], name='idx_dl_active_created'),
        ]
    
    def __str__(self):
        return f"下载 {self.id} - 文章UUID: {self.article_uuid} - 文件类型: {self.file_type}"