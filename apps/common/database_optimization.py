"""
数据库优化和缓存策略建议
遵循 Django 最佳实践和 Google Python Style Guide
"""

from django.core.cache import cache
from django.db import models
from django.db.models import Count, Q, Prefetch
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from django.core.cache.utils import make_template_fragment_key
from typing import List, Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


class CacheManager:
    """缓存管理器 - 统一管理应用缓存策略"""
    
    # 缓存键前缀
    CACHE_PREFIX = 'article_web'
    
    # 缓存超时时间（秒）
    CACHE_TIMEOUTS = {
        'categories': 300,      # 5分钟
        'articles_list': 180,   # 3分钟
        'article_detail': 600,  # 10分钟
        'user_stats': 120,      # 2分钟
        'hot_articles': 900,    # 15分钟
    }
    
    @classmethod
    def get_cache_key(cls, key_type: str, *args) -> str:
        """
        生成缓存键
        
        Args:
            key_type: 缓存类型
            *args: 缓存键参数
            
        Returns:
            完整的缓存键
        """
        key_parts = [cls.CACHE_PREFIX, key_type] + [str(arg) for arg in args]
        return ':'.join(key_parts)
    
    @classmethod
    def set_cache(cls, key_type: str, data: Any, *args, timeout: Optional[int] = None) -> bool:
        """
        设置缓存
        
        Args:
            key_type: 缓存类型
            data: 要缓存的数据
            *args: 缓存键参数
            timeout: 超时时间，如果不指定则使用默认值
            
        Returns:
            是否设置成功
        """
        cache_key = cls.get_cache_key(key_type, *args)
        cache_timeout = timeout or cls.CACHE_TIMEOUTS.get(key_type, 300)
        
        try:
            cache.set(cache_key, data, cache_timeout)
            logger.info(f"缓存设置成功: {cache_key}")
            return True
        except Exception as e:
            logger.error(f"缓存设置失败: {cache_key}, 错误: {e}")
            return False
    
    @classmethod
    def get_cache(cls, key_type: str, *args) -> Any:
        """
        获取缓存
        
        Args:
            key_type: 缓存类型
            *args: 缓存键参数
            
        Returns:
            缓存的数据，如果不存在则返回None
        """
        cache_key = cls.get_cache_key(key_type, *args)
        
        try:
            data = cache.get(cache_key)
            if data is not None:
                logger.info(f"缓存命中: {cache_key}")
            return data
        except Exception as e:
            logger.error(f"缓存获取失败: {cache_key}, 错误: {e}")
            return None
    
    @classmethod
    def delete_cache(cls, key_type: str, *args) -> bool:
        """
        删除缓存
        
        Args:
            key_type: 缓存类型
            *args: 缓存键参数
            
        Returns:
            是否删除成功
        """
        cache_key = cls.get_cache_key(key_type, *args)
        
        try:
            cache.delete(cache_key)
            logger.info(f"缓存删除成功: {cache_key}")
            return True
        except Exception as e:
            logger.error(f"缓存删除失败: {cache_key}, 错误: {e}")
            return False
    
    @classmethod
    def clear_pattern(cls, pattern: str) -> bool:
        """
        清除匹配模式的缓存
        
        Args:
            pattern: 缓存键模式
            
        Returns:
            是否清除成功
        """
        try:
            # 注意：这个方法需要Redis后端支持
            cache.delete_pattern(f"{cls.CACHE_PREFIX}:{pattern}*")
            logger.info(f"模式缓存清除成功: {pattern}")
            return True
        except Exception as e:
            logger.error(f"模式缓存清除失败: {pattern}, 错误: {e}")
            return False


class OptimizedQueryManager:
    """优化的查询管理器 - 提供高效的数据库查询方法"""
    
    @staticmethod
    def get_categories_with_stats() -> List[Dict[str, Any]]:
        """
        获取带统计信息的分类列表
        
        Returns:
            包含统计信息的分类列表
        """
        # 尝试从缓存获取
        cached_data = CacheManager.get_cache('categories', 'with_stats')
        if cached_data:
            return cached_data
        
        # 使用注解查询优化性能
        from apps.articles.models import Category, Article
        
        categories = Category.objects.filter(
            is_active=True
        ).annotate(
            article_count=Count(
                'articles',
                filter=Q(articles__is_active=True, articles__status=2)
            )
        ).order_by('sort_order', 'name')
        
        # 序列化数据
        result = []
        for category in categories:
            result.append({
                'id': category.id,
                'name': category.name,
                'slug': category.slug,
                'description': category.description,
                'article_count': category.article_count,
                'sort_order': category.sort_order,
                'created_at': category.create_time.isoformat() if hasattr(category, 'create_time') else None
            })
        
        # 缓存结果
        CacheManager.set_cache('categories', result, 'with_stats')
        
        return result
    
    @staticmethod
    def get_articles_optimized(
        category_slug: Optional[str] = None,
        search: Optional[str] = None,
        limit: int = 20,
        offset: int = 0
    ) -> Dict[str, Any]:
        """
        优化的文章查询方法
        
        Args:
            category_slug: 分类slug
            search: 搜索关键词
            limit: 限制数量
            offset: 偏移量
            
        Returns:
            包含文章列表和分页信息的字典
        """
        # 构建缓存键
        cache_params = [category_slug or 'all', search or 'none', limit, offset]
        cached_data = CacheManager.get_cache('articles_list', *cache_params)
        if cached_data:
            return cached_data
        
        from apps.articles.models import Article, Category
        
        # 构建基础查询集，使用select_related和prefetch_related优化
        queryset = Article.objects.select_related(
            'author'
        ).prefetch_related(
            Prefetch(
                'category',
                queryset=Category.objects.only('id', 'name', 'slug')
            )
        ).filter(
            is_active=True,
            status=2  # 已发布
        )
        
        # 应用筛选条件
        if category_slug:
            try:
                category = Category.objects.get(slug=category_slug, is_active=True)
                queryset = queryset.filter(category_uuid=str(category.uuid))
            except Category.DoesNotExist:
                queryset = queryset.none()
        
        if search:
            queryset = queryset.filter(
                Q(title__icontains=search) |
                Q(summary__icontains=search) |
                Q(content__icontains=search)
            )
        
        # 获取总数（在应用limit之前）
        total_count = queryset.count()
        
        # 应用分页和排序
        articles = queryset.order_by('-create_time')[offset:offset + limit]
        
        # 序列化文章数据
        serialized_articles = []
        for article in articles:
            serialized_articles.append({
                'id': article.id,
                'title': article.title,
                'slug': article.slug,
                'summary': article.summary,
                'author': article.author.username if article.author else 'Unknown',
                'category': article.category.name if hasattr(article, 'category') else 'Uncategorized',
                'view_count': getattr(article, 'view_count', 0),
                'download_count': getattr(article, 'download_count', 0),
                'created_at': article.create_time.isoformat() if hasattr(article, 'create_time') else None
            })
        
        # 计算分页信息
        page = (offset // limit) + 1
        total_pages = (total_count + limit - 1) // limit
        
        result = {
            'articles': serialized_articles,
            'pagination': {
                'page': page,
                'page_size': limit,
                'total': total_count,
                'total_pages': total_pages,
                'has_next': offset + limit < total_count,
                'has_prev': offset > 0
            }
        }
        
        # 缓存结果
        CacheManager.set_cache('articles_list', result, *cache_params)
        
        return result
    
    @staticmethod
    def get_hot_articles(limit: int = 10) -> List[Dict[str, Any]]:
        """
        获取热门文章
        
        Args:
            limit: 限制数量
            
        Returns:
            热门文章列表
        """
        # 尝试从缓存获取
        cached_data = CacheManager.get_cache('hot_articles', limit)
        if cached_data:
            return cached_data
        
        from apps.articles.models import Article
        
        # 根据浏览量和点赞数排序
        hot_articles = Article.objects.filter(
            is_active=True,
            status=2
        ).order_by(
            '-view_count',
            '-create_time'
        )[:limit]
        
        # 序列化数据
        result = []
        for article in hot_articles:
            result.append({
                'id': article.id,
                'title': article.title,
                'slug': article.slug,
                'view_count': getattr(article, 'view_count', 0),
                'created_at': article.create_time.isoformat() if hasattr(article, 'create_time') else None
            })
        
        # 缓存结果（较长时间）
        CacheManager.set_cache('hot_articles', result, limit)
        
        return result


class DatabaseIndexOptimizer:
    """数据库索引优化建议"""
    
    @staticmethod
    def get_recommended_indexes() -> List[str]:
        """
        获取推荐的数据库索引
        
        Returns:
            推荐的索引SQL语句列表
        """
        return [
            # 文章表索引
            "CREATE INDEX IF NOT EXISTS idx_articles_category_status ON articles_article(category_uuid, status);",
            "CREATE INDEX IF NOT EXISTS idx_articles_status_active ON articles_article(status, is_active);",
            "CREATE INDEX IF NOT EXISTS idx_articles_create_time ON articles_article(create_time DESC);",
            "CREATE INDEX IF NOT EXISTS idx_articles_view_count ON articles_article(view_count DESC);",
            "CREATE INDEX IF NOT EXISTS idx_articles_title_search ON articles_article(title);",
            
            # 分类表索引
            "CREATE INDEX IF NOT EXISTS idx_categories_slug ON articles_category(slug);",
            "CREATE INDEX IF NOT EXISTS idx_categories_active_sort ON articles_category(is_active, sort_order);",
            
            # 用户表索引
            "CREATE INDEX IF NOT EXISTS idx_users_email ON users_user(email);",
            "CREATE INDEX IF NOT EXISTS idx_users_active ON users_user(is_active);",
            
            # 复合索引
            "CREATE INDEX IF NOT EXISTS idx_articles_category_time ON articles_article(category_uuid, create_time DESC);",
            "CREATE INDEX IF NOT EXISTS idx_articles_author_status ON articles_article(author_uuid, status);",
        ]
    
    @staticmethod
    def analyze_query_performance() -> Dict[str, str]:
        """
        分析查询性能建议
        
        Returns:
            性能优化建议字典
        """
        return {
            'select_related': '使用 select_related() 减少数据库查询次数，特别是对于外键关系',
            'prefetch_related': '使用 prefetch_related() 优化多对多和反向外键查询',
            'only_defer': '使用 only() 或 defer() 只获取需要的字段',
            'bulk_operations': '使用 bulk_create(), bulk_update() 进行批量操作',
            'database_functions': '使用数据库函数如 Count(), Sum() 在数据库层面进行计算',
            'pagination': '对大数据集使用分页，避免一次性加载过多数据',
            'caching': '对频繁查询的数据使用缓存',
            'indexing': '为经常查询的字段添加数据库索引'
        }


class CacheInvalidationManager:
    """缓存失效管理器 - 管理缓存的自动失效"""
    
    @staticmethod
    def invalidate_article_caches(article_id: int) -> None:
        """
        文章相关缓存失效
        
        Args:
            article_id: 文章ID
        """
        # 删除文章详情缓存
        CacheManager.delete_cache('article_detail', article_id)
        
        # 删除文章列表缓存（可能需要清除多个分页）
        CacheManager.clear_pattern('articles_list')
        
        # 删除热门文章缓存
        CacheManager.clear_pattern('hot_articles')
        
        logger.info(f"文章 {article_id} 相关缓存已失效")
    
    @staticmethod
    def invalidate_category_caches(category_id: int) -> None:
        """
        分类相关缓存失效
        
        Args:
            category_id: 分类ID
        """
        # 删除分类列表缓存
        CacheManager.clear_pattern('categories')
        
        # 删除相关文章列表缓存
        CacheManager.clear_pattern('articles_list')
        
        logger.info(f"分类 {category_id} 相关缓存已失效")
    
    @staticmethod
    def setup_cache_signals() -> None:
        """
        设置缓存信号处理器
        """
        from django.db.models.signals import post_save, post_delete
        from apps.articles.models import Article, Category
        
        def article_cache_handler(sender, instance, **kwargs):
            CacheInvalidationManager.invalidate_article_caches(instance.id)
        
        def category_cache_handler(sender, instance, **kwargs):
            CacheInvalidationManager.invalidate_category_caches(instance.id)
        
        # 连接信号
        post_save.connect(article_cache_handler, sender=Article)
        post_delete.connect(article_cache_handler, sender=Article)
        post_save.connect(category_cache_handler, sender=Category)
        post_delete.connect(category_cache_handler, sender=Category)


# 使用示例
def example_usage():
    """使用示例"""
    
    # 获取优化的分类列表
    categories = OptimizedQueryManager.get_categories_with_stats()
    
    # 获取优化的文章列表
    articles_data = OptimizedQueryManager.get_articles_optimized(
        category_slug='workplace',
        search='Python',
        limit=20,
        offset=0
    )
    
    # 获取热门文章
    hot_articles = OptimizedQueryManager.get_hot_articles(limit=10)
    
    # 设置缓存信号处理器
    CacheInvalidationManager.setup_cache_signals()
    
    return {
        'categories': categories,
        'articles': articles_data,
        'hot_articles': hot_articles
    }