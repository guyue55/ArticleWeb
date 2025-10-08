"""
用户工具函数
提供用户相关的辅助功能
"""

from django.contrib.auth import get_user_model
from django.utils import timezone
from apps.common.utils import generate_hash, get_client_ip
import logging

logger = logging.getLogger(__name__)
User = get_user_model()


def get_user_display_name(user):
    """
    获取用户显示名称
    
    Args:
        user: 用户对象
        
    Returns:
        str: 用户显示名称
    """
    if not user:
        return "未知用户"
    
    # 返回用户的显示名称
    if user.first_name and user.last_name:
        return f"{user.first_name}{user.last_name}"
    elif user.first_name:
        return user.first_name
    else:
        return user.username


def validate_user_permissions(user, required_permissions=None):
    """
    验证用户权限
    
    Args:
        user: 用户对象
        required_permissions: 需要的权限列表
        
    Returns:
        bool: 用户是否具有所需权限
    """
    if not user or not user.is_authenticated:
        return False
    
    if not required_permissions:
        return True
    
    # 检查用户是否具有所需权限
    for permission in required_permissions:
        if not user.has_perm(permission):
            return False
    
    return True


def get_user_stats(user):
    """
    获取用户统计信息
    
    Args:
        user: 用户对象
        
    Returns:
        dict: 用户统计信息
    """
    if not user or not user.is_authenticated:
        return {}
    
    try:
        from apps.articles.models import Article, ArticleClaim, ArticleDownload
        
        # 获取用户文章统计
        user_articles = Article.objects.filter(author_uuid=user.uuid)
        
        # 获取用户领取和下载统计
        claimed_count = ArticleClaim.objects.filter(
            user_uuid=user.uuid,
            is_active=True
        ).count()
        
        download_count = ArticleDownload.objects.filter(
            user_uuid=user.uuid,
            is_active=True
        ).count()
        
        stats = {
            'total_articles': user_articles.count(),
            'published_articles': user_articles.filter(status=2).count(),  # 2-已发布
            'draft_articles': user_articles.filter(status=1).count(),  # 1-草稿
            'total_views': sum(article.view_count for article in user_articles),
            'claimed_count': claimed_count,
            'download_count': download_count,
            'join_date': user.date_joined.isoformat() if user.date_joined else None,
            'last_login': user.last_login.isoformat() if user.last_login else None,
        }
        
        return stats
        
    except Exception as e:
        logger.error(f"获取用户统计信息失败: {e}")
        return {}


def update_user_last_activity(user, request=None):
    """
    更新用户最后活动时间
    
    Args:
        user: 用户对象
        request: HTTP请求对象（可选）
    """
    if not user or not user.is_authenticated:
        return
    
    try:
        # 更新最后登录时间
        user.last_login = timezone.now()
        
        # 如果有请求对象，更新IP地址
        if request and hasattr(user, 'last_login_ip'):
            user.last_login_ip = get_client_ip(request)
        
        user.save(update_fields=['last_login', 'last_login_ip'] if request else ['last_login'])
        
    except Exception as e:
        logger.error(f"更新用户活动时间失败: {e}")


def is_user_active(user):
    """
    检查用户是否为活跃用户
    
    Args:
        user: 用户对象
        
    Returns:
        bool: 用户是否活跃
    """
    if not user or not user.is_authenticated:
        return False
    
    return user.is_active and not user.is_staff


def get_user_profile_completion(user):
    """
    计算用户资料完整度
    
    Args:
        user: 用户对象
        
    Returns:
        float: 资料完整度百分比 (0-100)
    """
    if not user or not user.is_authenticated:
        return 0.0
    
    total_fields = 8  # 总字段数
    completed_fields = 0
    
    # 检查各个字段是否完整
    if user.username:
        completed_fields += 1
    if user.email:
        completed_fields += 1
    if user.first_name:
        completed_fields += 1
    if user.last_name:
        completed_fields += 1
    if hasattr(user, 'bio') and user.bio:
        completed_fields += 1
    if hasattr(user, 'avatar') and user.avatar:
        completed_fields += 1
    if hasattr(user, 'birth_date') and user.birth_date:
        completed_fields += 1
    if hasattr(user, 'location') and user.location:
        completed_fields += 1
    
    return (completed_fields / total_fields) * 100