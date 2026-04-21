"""Article models for the application."""

from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import MinLengthValidator
from django.utils import timezone

from apps.common.models import BaseModel, ActiveManager, AllManager
from apps.common.utils import mask_sensitive_data

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


class AIProvider(BaseModel):
    """AI模型供应商模型"""
    
    name = models.CharField(
        verbose_name="供应商名称",
        max_length=64,
        unique=True,
        help_text="如：Baidu, OpenAI, DeepSeek",
        db_comment="AI服务提供商的名称"
    )
    api_base = models.CharField(
        verbose_name="API基础路径",
        max_length=255,
        help_text="API的基础URL路径",
        db_comment="AI服务的API基础URL"
    )
    api_key = models.CharField(
        verbose_name="API密钥",
        max_length=255,
        help_text="访问API的Key (敏感数据，禁止在非脱敏接口返回)",
        db_comment="用于身份验证的API Key"
    )
    config = models.JSONField(
        verbose_name="额外配置",
        default=dict,
        blank=True,
        help_text="特定供应商的额外参数（JSON格式）",
        db_comment="存储特定供应商所需的其他配置信息"
    )
    is_openapi = models.BooleanField(
        verbose_name="是否OpenAPI标准",
        default=True,
        help_text="如果勾选，系统将尝试调用 /v1/models 接口扫描模型",
        db_comment="标识该供应商是否遵循OpenAPI标准协议"
    )
    last_scanned_at = models.DateTimeField(
        verbose_name="最后扫描时间",
        null=True,
        blank=True,
        help_text="上次自动扫描模型的时间",
        db_comment="模型列表最后一次从API同步的时间"
    )
    
    # Custom managers
    objects = ActiveManager()
    all_objects = AllManager()
    
    class Meta:
        verbose_name = "AI模型供应商"
        verbose_name_plural = "AI模型供应商"
        db_table = 'article_ai_providers'
        ordering = ['name']
    
    def __str__(self):
        return f"{self.name} ({mask_sensitive_data(self.api_key)})"

    def mask_api_key(self) -> str:
        """返回脱敏后的 API Key"""
        return mask_sensitive_data(self.api_key)


class AIModel(BaseModel):
    """AI具体模型信息模型"""
    
    provider = models.ForeignKey(
        AIProvider,
        on_delete=models.CASCADE,
        related_name='models',
        verbose_name="所属供应商",
        db_comment="关联的AI服务供应商"
    )
    name = models.CharField(
        verbose_name="模型名称",
        max_length=128,
        help_text="模型的技术标识符，如 gpt-4, ernie-bot-4",
        db_comment="模型在API调用中使用的唯一标识符"
    )
    display_name = models.CharField(
        verbose_name="显示名称",
        max_length=128,
        help_text="页面上显示的名称，如 文心一言 4.0",
        db_comment="模型在前端界面显示的友好名称"
    )
    description = models.TextField(
        verbose_name="模型描述",
        max_length=500,
        default='',
        blank=True,
        help_text="模型的功能和限制说明",
        db_comment="对该模型能力的详细描述"
    )
    is_available = models.BooleanField(
        verbose_name="是否可用",
        default=True,
        help_text="标识该模型当前是否可以调用",
        db_comment="模型当前的服务状态"
    )
    
    # Custom managers
    objects = ActiveManager()
    all_objects = AllManager()
    
    class Meta:
        verbose_name = "AI具体模型"
        verbose_name_plural = "AI具体模型"
        db_table = 'article_ai_models'
        unique_together = ['provider', 'name']
        ordering = ['display_name']
    
    def __str__(self):
        return f"{self.provider.name} - {self.display_name}"


class PromptTemplate(BaseModel):
    """提示词模板模型"""
    
    title = models.CharField(
        verbose_name="模板标题",
        max_length=128,
        help_text="模板的显示名称",
        db_comment="提示词模板的标题"
    )
    category_uuid = models.CharField(
        verbose_name="关联分类UUID",
        max_length=255,
        help_text="模板关联的文章分类UUID",
        db_comment="关联的文章分类UUID"
    )
    content = models.TextField(
        verbose_name="模板内容",
        help_text="基于 Jinja2 语法的模板正文",
        db_comment="提示词模板的实际内容，支持Jinja2语法"
    )
    variables = models.JSONField(
        verbose_name="模板变量",
        default=list,
        blank=True,
        help_text="定义用户需要输入的变量名、类型及默认值",
        db_comment="存储模板中定义的变量信息"
    )
    description = models.TextField(
        verbose_name="模板描述",
        max_length=500,
        default='',
        blank=True,
        help_text="模板功能详细说明",
        db_comment="模板的详细描述信息"
    )
    
    # Custom managers
    objects = ActiveManager()
    all_objects = AllManager()
    
    class Meta:
        verbose_name = "提示词模板"
        verbose_name_plural = "提示词模板"
        db_table = 'article_prompt_templates'
        ordering = ['-create_time']
    
    def __str__(self):
        return self.title


class HotTrend(BaseModel):
    """热门选题与溯源模型"""
    
    topic = models.CharField(
        verbose_name="话题标题",
        max_length=255,
        help_text="热门话题标题或关键词",
        db_comment="从联网搜索获取的热门话题标题"
    )
    source_urls = models.JSONField(
        verbose_name="来源链接",
        default=list,
        help_text="存储来源链接列表（URL、标题、来源平台）",
        db_comment="热门话题的相关来源链接信息"
    )
    summary = models.TextField(
        verbose_name="热点摘要",
        default='',
        blank=True,
        help_text="AI 对该热点的简要分析/摘要",
        db_comment="对热点话题的AI分析摘要"
    )
    category_uuid = models.CharField(
        verbose_name="分类UUID",
        max_length=255,
        help_text="话题所属分类的UUID",
        db_comment="话题关联的分类UUID"
    )
    discovery_time = models.DateTimeField(
        verbose_name="发现时间",
        default=timezone.now,
        help_text="话题被系统发现的时间",
        db_comment="热点话题的抓取/发现时间"
    )
    
    # Custom managers
    objects = ActiveManager()
    all_objects = AllManager()
    
    class Meta:
        verbose_name = "热门选题"
        verbose_name_plural = "热门选题"
        db_table = 'article_hot_trends'
        ordering = ['-discovery_time']
        indexes = [
            models.Index(fields=['category_uuid', 'discovery_time'], name='idx_trend_cat_time'),
        ]
    
    def __str__(self):
        return self.topic


class GenerationHistory(BaseModel):
    """AI 生成记录模型"""
    
    STATUS_CHOICES = [
        ('pending', '生成中'),
        ('success', '成功'),
        ('failed', '失败'),
    ]
    
    user_uuid = models.CharField(
        verbose_name="用户UUID",
        max_length=255,
        help_text="执行生成操作的用户UUID",
        db_comment="操作用户的UUID"
    )
    prompt = models.TextField(
        verbose_name="最终提示词",
        help_text="最终发送给 AI 的完整提示词",
        db_comment="发送给AI的完整Prompt内容"
    )
    result = models.TextField(
        verbose_name="生成结果",
        default='',
        blank=True,
        help_text="AI 返回的原始文本内容",
        db_comment="AI生成文章的内容结果"
    )
    sources = models.JSONField(
        verbose_name="参考来源",
        default=list,
        blank=True,
        help_text="生成该文章时参考的来源链接",
        db_comment="文章生成过程中参考的外部链接信息"
    )
    status = models.CharField(
        verbose_name="生成状态",
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        help_text="AI 生成状态",
        db_comment="生成状态：pending-生成中，success-成功，failed-失败"
    )
    error_message = models.TextField(
        verbose_name="错误信息",
        default='',
        blank=True,
        help_text="生成失败时的错误描述",
        db_comment="生成过程中出现的错误详情"
    )
    
    # Custom managers
    objects = ActiveManager()
    all_objects = AllManager()
    
    class Meta:
        verbose_name = "AI生成记录"
        verbose_name_plural = "AI生成记录"
        db_table = 'article_generation_history'
        ordering = ['-create_time']
        indexes = [
            models.Index(fields=['user_uuid', 'status'], name='idx_gen_user_status'),
        ]
    
    def __str__(self):
        return f"生成记录 {self.id} - 用户: {self.user_uuid} - 状态: {self.status}"


class SystemConfig(BaseModel):
    """系统全局配置模型（如 API Key）"""
    
    key = models.CharField(
        verbose_name="配置键",
        max_length=128,
        unique=True,
        help_text="配置的唯一标识，如 TAVILY_API_KEY",
        db_comment="配置项的唯一键名"
    )
    value = models.TextField(
        verbose_name="配置值",
        help_text="配置的具体内容 (若为敏感数据请勾选'是否敏感')",
        db_comment="配置项的具体数值或内容"
    )
    description = models.CharField(
        verbose_name="配置描述",
        max_length=255,
        default='',
        blank=True,
        help_text="配置项的用途说明",
        db_comment="对该配置项用途的详细描述"
    )
    is_secret = models.BooleanField(
        verbose_name="是否敏感",
        default=False,
        help_text="敏感信息在前端将脱敏显示",
        db_comment="标识该配置是否为敏感信息，如API Key"
    )
    
    # Custom managers
    objects = ActiveManager()
    all_objects = AllManager()
    
    class Meta:
        verbose_name = "系统配置"
        verbose_name_plural = "系统配置"
        db_table = 'article_system_configs'
        ordering = ['key']
    
    def __str__(self):
        val = mask_sensitive_data(self.value) if self.is_secret else self.value
        return f"{self.key}: {val[:30]}..."
    
    def mask_value(self) -> str:
        """返回脱敏后的配置值"""
        if self.is_secret:
            return mask_sensitive_data(self.value)
        return self.value
    
    @classmethod
    def get_value(cls, key: str, default: str = None) -> str:
        """获取配置值，优先从数据库获取，失败则返回默认值"""
        try:
            config = cls.objects.get(key=key, is_active=True)
            return config.value
        except cls.DoesNotExist:
            return default