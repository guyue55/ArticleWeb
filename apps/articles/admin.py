"""Articles admin configuration."""

from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe

from .models import Category, Article, ArticleClaim, ArticleDownload


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    """Category admin configuration."""
    list_display = ('name', 'slug', 'article_count', 'sort_order', 'is_active', 'create_time')
    list_filter = ('is_active', 'create_time')
    search_fields = ('name', 'slug', 'description')
    prepopulated_fields = {'slug': ('name',)}
    ordering = ('sort_order', 'name')
    list_editable = ('sort_order', 'is_active')
    
    fieldsets = (
        ('基本信息', {
            'fields': ('name', 'slug', 'description')
        }),
        ('设置', {
            'fields': ('sort_order', 'is_active')
        }),
    )
    
    def article_count(self, obj):
        """Display article count for category."""
        count = Article.objects.filter(category_uuid=obj.uuid, is_active=True).count()
        if count > 0:
            url = reverse('admin:articles_article_changelist') + f'?category_uuid={obj.uuid}'
            return format_html('<a href="{}">{} 篇文章</a>', url, count)
        return '0 篇文章'
    
    article_count.short_description = '文章数量'





# CommentInline removed due to UUID-based relationships


@admin.register(Article)
class ArticleAdmin(admin.ModelAdmin):
    """Article admin configuration."""
    list_display = (
        'title', 'author_uuid', 'category_uuid', 'status_display', 'is_featured', 'is_top',
        'view_count', 'published_at', 'create_time'
    )
    list_filter = (
        'status', 'is_featured', 'is_top', 'category_uuid',
        'create_time', 'published_at', 'author_uuid'
    )
    search_fields = ('title', 'slug', 'summary', 'content', 'author_uuid')
    prepopulated_fields = {'slug': ('title',)}
    date_hierarchy = 'create_time'
    ordering = ('-create_time',)
    list_editable = ('is_featured', 'is_top')
    
    fieldsets = (
        ('基本信息', {
            'fields': ('title', 'slug', 'summary', 'content')
        }),
        ('分类', {
            'fields': ('category_uuid',)
        }),
        ('媒体', {
            'fields': ('featured_image',)
        }),
        ('发布设置', {
            'fields': ('status', 'is_featured', 'is_top', 'published_at')
        }),
        ('统计信息', {
            'fields': ('view_count',),
            'classes': ('collapse',)
        }),
        ('系统信息', {
            'fields': ('author_uuid', 'is_active'),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ('view_count',)
    # inlines = [CommentInline]  # Removed due to UUID-based relationships
    
    def status_display(self, obj):
        """Display status with color."""
        status_colors = {
            1: '#ffc107',  # 草稿 - 黄色
            2: '#28a745',  # 已发布 - 绿色
            3: '#dc3545',  # 已下线 - 红色
        }
        status_names = {
            1: '草稿',
            2: '已发布',
            3: '已下线'
        }
        color = status_colors.get(obj.status, '#6c757d')
        name = status_names.get(obj.status, '未知')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 2px 8px; border-radius: 3px;">{}</span>',
            color,
            name
        )
    
    status_display.short_description = '状态'
    
    def save_model(self, request, obj, form, change):
        """Set author when creating new article."""
        if not change:  # Creating new article
            obj.author_uuid = str(request.user.uuid)
        super().save_model(request, obj, form, change)
    
    def get_queryset(self, request):
        """Return base queryset."""
        return super().get_queryset(request)








@admin.register(ArticleClaim)
class ArticleClaimAdmin(admin.ModelAdmin):
    """ArticleClaim admin configuration."""
    list_display = ('user_uuid', 'article_uuid', 'claimed_at', 'is_active', 'create_time')
    list_filter = ('is_active', 'claimed_at', 'create_time')
    search_fields = ('user_uuid', 'article_uuid')
    ordering = ('-claimed_at',)
    list_editable = ('is_active',)
    readonly_fields = ('claimed_at',)
    
    def has_add_permission(self, request):
        """Disable adding claims through admin."""
        return False
    
    def get_queryset(self, request):
        """Return base queryset."""
        return super().get_queryset(request)


@admin.register(ArticleDownload)
class ArticleDownloadAdmin(admin.ModelAdmin):
    """ArticleDownload admin configuration."""
    list_display = ('user_uuid', 'article_uuid', 'downloaded_at', 'ip_address', 'is_active', 'create_time')
    list_filter = ('is_active', 'downloaded_at', 'create_time')
    search_fields = ('user_uuid', 'article_uuid', 'ip_address')
    ordering = ('-downloaded_at',)
    list_editable = ('is_active',)
    readonly_fields = ('downloaded_at', 'ip_address', 'user_agent')
    
    def has_add_permission(self, request):
        """Disable adding downloads through admin."""
        return False
    
    def get_queryset(self, request):
        """Return base queryset."""
        return super().get_queryset(request)