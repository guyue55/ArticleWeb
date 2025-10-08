"""优化后的文章API示例 - 展示如何应用性能优化。

这个文件展示了如何将性能优化应用到现有的API接口中。
可以参考这些示例来优化实际的 api.py 文件。
"""

from typing import List, Optional
from django.shortcuts import get_object_or_404
from django.db.models import Q, Prefetch
from django.core.cache import cache
from ninja import Router

from apps.common.responses import APIResponse, ErrorCodes
from apps.common.serializers import SerializerMixin
from apps.common.performance import (
    optimize_api_endpoint, 
    QueryOptimizer, 
    CacheOptimizer,
    PerformanceMonitor
)
from apps.common.cache import ArticleCacheManager
from .models import Article, Category
from .schemas import ArticleCreateSchema, ArticleUpdateSchema

router = Router()


# 优化后的文章列表接口
@router.get("", response=dict)
@optimize_api_endpoint(rate_limit_requests=120)  # 每小时120次请求
def list_articles_optimized(
    request,
    limit: int = 20,
    offset: int = 0,
    category_id: Optional[int] = None,
    search: Optional[str] = None,
    sort: str = "latest"
):
    """优化后的文章列表接口。
    
    优化点：
    1. 使用缓存减少数据库查询
    2. 优化数据库查询（select_related, prefetch_related）
    3. 性能监控和速率限制
    4. 智能缓存键生成
    """
    try:
        # 生成缓存键
        cache_key = f"article_list:{limit}:{offset}:{category_id}:{search}:{sort}"
        
        # 尝试从缓存获取数据
        cached_result = cache.get(cache_key)
        if cached_result:
            return APIResponse.paginated(**cached_result)
        
        # 构建查询集
        queryset = Article.objects.filter(is_active=True, status=2)
        
        # 应用过滤器
        if category_id:
            queryset = queryset.filter(category_id=category_id)
        
        if search:
            queryset = queryset.filter(
                Q(title__icontains=search) |
                Q(summary__icontains=search) |
                Q(content__icontains=search)
            )
        
        # 应用排序
        if sort == 'latest':
            queryset = queryset.order_by('-create_time')
        elif sort == 'popular':
            queryset = queryset.order_by('-view_count')
        elif sort == 'discussed':
            queryset = queryset.order_by('-view_count')
        else:
            queryset = queryset.order_by('-is_top', '-create_time')
        
        # 优化查询
        queryset = QueryOptimizer.optimize_article_queries(queryset)
        
        # 获取总数（使用缓存）
        count_cache_key = f"article_count:{category_id}:{search}"
        total = cache.get(count_cache_key)
        if total is None:
            total = queryset.count()
            cache.set(count_cache_key, total, 300)  # 5分钟缓存
        
        # 分页查询
        articles = list(queryset[offset:offset + limit])
        
        # 序列化数据
        serialized_articles = SerializerMixin.serialize_article_list(articles)
        
        # 构建响应数据
        result_data = {
            'items': serialized_articles,
            'total': total,
            'limit': limit,
            'offset': offset
        }
        
        # 缓存结果（根据数据变化频率调整缓存时间）
        cache_timeout = 180 if search else 300  # 搜索结果缓存时间更短
        cache.set(cache_key, result_data, cache_timeout)
        
        return APIResponse.paginated(**result_data)
    
    except Exception as e:
        return APIResponse.error(
            code=ErrorCodes.INTERNAL_SERVER_ERROR,
            message="获取文章列表失败"
        )


# 优化后的文章详情接口
@router.get("/{article_id}", response=dict)
@optimize_api_endpoint(rate_limit_requests=300)  # 详情页访问频率更高
def get_article_detail_optimized(request, article_id: int):
    """优化后的文章详情接口。
    
    优化点：
    1. 多层缓存策略
    2. 异步更新浏览量
    3. 预加载相关数据
    4. 智能缓存失效
    """
    try:
        # 使用专用的文章缓存管理器
        cache_key = f"article_detail_{article_id}"
        cached_article = ArticleCacheManager.get(cache_key)
        
        if cached_article:
            # 异步更新浏览量（不影响响应速度）
            _update_view_count_async(article_id)
            return APIResponse.success(data=cached_article)
        
        # 从数据库获取文章
        article = get_object_or_404(
            Article.objects.select_related(
                'author', 'category', 'author__userprofile'
            ),
            id=article_id,
            is_active=True,
            status=2
        )
        
        # 序列化文章数据
        serialized_article = SerializerMixin.serialize_article_detail(article)
        
        # 缓存文章详情（较长时间，因为内容不经常变化）
        ArticleCacheManager.set(cache_key, serialized_article, timeout=1800)  # 30分钟
        
        # 更新浏览量
        _update_view_count_async(article_id)
        
        return APIResponse.success(data=serialized_article)
    
    except Article.DoesNotExist:
        return APIResponse.error(
            code=ErrorCodes.NOT_FOUND,
            message="文章不存在"
        )
    except Exception as e:
        return APIResponse.error(
            code=ErrorCodes.INTERNAL_SERVER_ERROR,
            message="获取文章详情失败"
        )


# 优化后的分类列表接口 - 已移动到主API文件
# @router.get("/categories", response=dict)
# @optimize_api_endpoint(rate_limit_requests=60)
# def list_categories_optimized(request):
#     """优化后的分类列表接口。
#     
#     优化点：
#     1. 长时间缓存（分类数据变化不频繁）
#     2. 预热缓存策略
#     3. 批量序列化
#     """
#     try:
#         # 使用通用缓存获取模式
#         def fetch_categories():
#             categories = Category.objects.filter(is_active=True).order_by('sort_order', 'name')
#             return SerializerMixin.serialize_queryset(categories, CategorySerializer)
#         
#         serialized_categories = CacheOptimizer.get_cached_data(
#             cache_key='active_categories_serialized',
#             fetch_func=fetch_categories,
#             timeout=1800  # 30分钟缓存
#         )
#         
#         return APIResponse.success(data=serialized_categories)
#     
#     except Exception as e:
#         return APIResponse.error(
#             code=ErrorCodes.INTERNAL_SERVER_ERROR,
#             message="获取分类列表失败"
#         )


# 优化后的文章创建接口
@router.post("", response=dict, auth=auth)
@optimize_api_endpoint(rate_limit_requests=20)  # 创建操作限制更严格
def create_article_optimized(request, data: ArticleCreateSchema):
    """优化后的文章创建接口。
    
    优化点：
    1. 事务处理
    2. 缓存失效策略
    3. 异步任务处理
    4. 数据验证优化
    """
    try:
        from django.db import transaction
        
        with transaction.atomic():
            # 创建文章
            article = Article.objects.create(
                author=request.auth,
                title=data.title,
                slug=data.slug,
                summary=data.summary,
                content=data.content,
                category_id=data.category_id,
                status=data.status,
                is_featured=data.is_featured,
                is_top=data.is_top
            )
            
            # 重新加载文章以获取关联数据
            article = Article.objects.select_related(
                'author', 'category', 'author__userprofile'
            ).get(id=article.id)
            
            # 序列化文章数据
            serialized_article = SerializerMixin.serialize_article_detail(article)
            
            # 清除相关缓存
            CacheOptimizer.invalidate_related_caches('Article')
            
            # 异步处理（如发送通知、更新搜索索引等）
            _handle_article_created_async(article.id)
            
            return APIResponse.success(
                data=serialized_article,
                message="文章创建成功"
            )
    
    except Exception as e:
        return APIResponse.error(
            code=ErrorCodes.INTERNAL_SERVER_ERROR,
            message="创建文章失败"
        )


# 辅助函数
def _update_view_count_async(article_id: int):
    """异步更新文章浏览量。
    
    在实际项目中，这里可以使用 Celery 或其他异步任务队列。
    这里使用简单的缓存计数器模拟。
    """
    from django.core.cache import cache
    
    # 使用缓存计数器，定期批量更新数据库
    cache_key = f"view_count_{article_id}"
    current_count = cache.get(cache_key, 0)
    cache.set(cache_key, current_count + 1, 3600)  # 1小时
    
    # 每10次浏览更新一次数据库
    if (current_count + 1) % 10 == 0:
        try:
            article = Article.objects.get(id=article_id)
            article.view_count += 10
            article.save(update_fields=['view_count'])
            cache.delete(cache_key)
        except Article.DoesNotExist:
            pass


def _handle_article_created_async(article_id: int):
    """处理文章创建后的异步任务。
    
    在实际项目中，这里可以包括：
    - 发送通知给关注者
    - 更新搜索索引
    - 生成文章摘要
    - 社交媒体分享
    等等
    """
    # 这里可以使用 Celery 任务
    # send_article_notifications.delay(article_id)
    # update_search_index.delay(article_id)
    pass


# 性能监控端点（仅管理员可访问）
@router.get("/performance-stats", response=dict)
def get_performance_stats(request):
    """获取API性能统计信息。"""
    if not request.user.is_staff:
        return APIResponse.error(
            code=ErrorCodes.FORBIDDEN,
            message="无权限访问"
        )
    
    stats = {
        'list_articles': PerformanceMonitor.get_performance_stats('list_articles_optimized'),
        'get_article_detail': PerformanceMonitor.get_performance_stats('get_article_detail_optimized'),
        'create_article': PerformanceMonitor.get_performance_stats('create_article_optimized'),
    }
    
    return APIResponse.success(data=stats)


# 缓存管理端点（仅管理员可访问）
@router.post("/clear-cache", response=dict)
def clear_cache(request):
    """清除所有缓存。"""
    if not request.user.is_staff:
        return APIResponse.error(
            code=ErrorCodes.FORBIDDEN,
            message="无权限访问"
        )
    
    try:
        ArticleCacheManager.clear_all()
        CacheOptimizer.cache_hot_data()  # 重新缓存热点数据
        
        return APIResponse.success(
            message="缓存清除成功，热点数据已重新缓存"
        )
    except Exception as e:
        return APIResponse.error(
            code=ErrorCodes.INTERNAL_SERVER_ERROR,
            message="清除缓存失败"
        )


"""
使用说明：

1. 将这些优化应用到实际的 api.py 文件中：
   - 复制相关的装饰器和优化逻辑
   - 根据实际需求调整缓存时间和速率限制
   - 添加必要的导入语句

2. 在 Django settings.py 中配置缓存：
   CACHES = {
       'default': {
           'BACKEND': 'django.core.cache.backends.redis.RedisCache',
           'LOCATION': 'redis://127.0.0.1:6379/1',
           'OPTIONS': {
               'CLIENT_CLASS': 'django_redis.client.DefaultClient',
           }
       }
   }

3. 监控性能：
   - 定期检查 /api/articles/performance-stats 端点
   - 根据统计数据调整缓存策略和优化参数

4. 缓存管理：
   - 在数据更新后及时清除相关缓存
   - 使用 /api/articles/clear-cache 端点进行缓存管理
   - 考虑实施自动缓存预热策略
"""