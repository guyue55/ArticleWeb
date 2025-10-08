"""Users admin configuration."""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe

from .models import User, UserProfile


# UserProfileInline removed due to UUID-based relationships


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """User admin configuration."""
    list_display = (
        'username', 'email', 'phone', 'is_verified', 'is_active',
        'is_staff', 'last_login', 'create_time'
    )
    list_filter = (
        'is_active', 'is_staff', 'is_superuser', 'is_verified',
        'create_time', 'last_login'
    )
    search_fields = ('username', 'email', 'phone', 'first_name', 'last_name')
    ordering = ('-create_time',)
    list_editable = ('is_active', 'is_verified')
    
    fieldsets = (
        ('登录信息', {
            'fields': ('username', 'password')
        }),
        ('个人信息', {
            'fields': ('first_name', 'last_name', 'email', 'phone')
        }),
        ('头像和简介', {
            'fields': ('avatar', 'bio')
        }),
        ('位置和网站', {
            'fields': ('birth_date', 'location', 'website')
        }),
        ('权限', {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions'),
            'classes': ('collapse',)
        }),
        ('验证状态', {
            'fields': ('is_verified',)
        }),
        ('重要日期', {
            'fields': ('last_login', 'date_joined'),
            'classes': ('collapse',)
        }),
        ('系统信息', {
            'fields': ('user_id', 'last_login_ip'),
            'classes': ('collapse',)
        }),
    )
    
    add_fieldsets = (
        ('创建用户', {
            'classes': ('wide',),
            'fields': ('username', 'email', 'password1', 'password2'),
        }),
    )
    
    readonly_fields = ('user_id', 'last_login', 'date_joined', 'create_time', 'update_time')
    # inlines = [UserProfileInline]  # Removed due to UUID-based relationships
    
    def get_queryset(self, request):
        """Optimize queryset with select_related."""
        return super().get_queryset(request).select_related('userprofile')
    
    def save_model(self, request, obj, form, change):
        """Custom save logic."""
        super().save_model(request, obj, form, change)
        
        # Create UserProfile if it doesn't exist
        if not hasattr(obj, 'userprofile'):
            UserProfile.objects.create(user=obj)


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    """UserProfile admin configuration."""
    list_display = (
        'user_uuid', 'gender_display', 'occupation',
        'education', 'is_active', 'create_time'
    )
    list_filter = ('gender', 'education', 'is_active', 'create_time')
    search_fields = (
        'user__username', 'user__email', 'occupation',
        'interests', 'social_links'
    )
    ordering = ('-create_time',)
    list_editable = ('is_active',)
    
    fieldsets = (
        ('关联用户', {
            'fields': ('user',)
        }),
        ('个人信息', {
            'fields': ('user_uuid', 'gender', 'occupation', 'education')
        }),
        ('兴趣和社交', {
            'fields': ('interests', 'social_links')
        }),
        ('偏好设置', {
            'fields': ('preferences',)
        }),
        ('系统信息', {
            'fields': ('is_active',),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ('create_time', 'update_time')
    
    def gender_display(self, obj):
        """Display gender with icon."""
        gender_icons = {
            0: ('未知', '#6c757d', '❓'),
            1: ('男', '#007bff', '👨'),
            2: ('女', '#e83e8c', '👩'),
        }
        if obj.gender in gender_icons:
            name, color, icon = gender_icons[obj.gender]
            return format_html(
                '<span style="color: {};">{} {}</span>',
                color, icon, name
            )
        return '未知'
    
    gender_display.short_description = '性别'
    
    def get_queryset(self, request):
        """Optimize queryset with select_related."""
        return super().get_queryset(request).select_related('user')


# Customize admin site
admin.site.site_header = 'ArticleWeb 管理后台'
admin.site.site_title = 'ArticleWeb'
admin.site.index_title = '欢迎使用 ArticleWeb 管理后台'