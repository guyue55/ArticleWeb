"""
API 层优化建议和示例代码
遵循 Google Python Style Guide
"""

from typing import List, Optional, Dict, Any
from django.db.models import Q, Prefetch
from django.core.cache import cache
from ninja import Router, Query
from ninja.pagination import paginate, PageNumberPagination

from apps.common.responses import APIResponse
from apps.articles.models import Article, Category
from apps.articles.schemas import ArticleFilterSchema


class OptimizedArticleAPI:
    """优化的文章API类，提供更好的性能和可维护性"""
    
    def __init__(self):
        self.cache_timeout = 300  # 5分钟缓存
        
    def get_filtered_articles(
        self, 
        filters: ArticleFilterSchema,
        page: int = 1,
        page_size: int = 20
    ) -> Dict[str, Any]:
        """
        获取筛选后的文章列表
        
        Args:
            filters: 筛选条件对象
            page: 页码
            page_size: 每页数量
            
        Returns:
            包含文章列表和分页信息的字典
            
        Raises:
            ValidationException: 当筛选参数无效时
        """
        # 构建缓存键
        cache_key = self._build_cache_key(filters, page, page_size)
        
        # 尝试从缓存获取
        cached_result = cache.get(cache_key)
        if cached_result:
            return cached_result
            
        # 构建查询集
        queryset = self._build_queryset(filters)
        
        # 执行查询并序列化
        result = self._execute_query_and_serialize(queryset, page, page_size)
        
        # 缓存结果
        cache.set(cache_key, result, self.cache_timeout)
        
        return result
    
    def _build_cache_key(
        self, 
        filters: ArticleFilterSchema, 
        page: int, 
        page_size: int
    ) -> str:
        """
        构建缓存键
        
        Args:
            filters: 筛选条件
            page: 页码
            page_size: 每页数量
            
        Returns:
            缓存键字符串
        """
        filter_str = f"{filters.category}_{filters.search}_{filters.status}"
        return f"articles_list_{filter_str}_{page}_{page_size}"
    
    def _build_queryset(self, filters: ArticleFilterSchema):
        """
        根据筛选条件构建查询集
        
        Args:
            filters: 筛选条件对象
            
        Returns:
            Django QuerySet对象
        """
        queryset = Article.objects.select_related('author').prefetch_related(
            Prefetch('category', queryset=Category.objects.only('name', 'slug'))
        ).filter(is_active=True)
        
        # 应用筛选条件
        if filters.category:
            queryset = self._apply_category_filter(queryset, filters.category)
            
        if filters.search:
            queryset = self._apply_search_filter(queryset, filters.search)
            
        if filters.status is not None:
            queryset = queryset.filter(status=filters.status)
        else:
            queryset = queryset.filter(status=2)  # 默认只显示已发布
            
        return queryset.order_by('-create_time')
    
    def _apply_category_filter(self, queryset, category: str):
        """
        应用分类筛选
        
        Args:
            queryset: 查询集
            category: 分类名称或slug
            
        Returns:
            筛选后的查询集
        """
        try:
            category_obj = Category.objects.get(
                Q(name=category) | Q(slug=category),
                is_active=True
            )
            return queryset.filter(category_uuid=str(category_obj.uuid))
        except Category.DoesNotExist:
            return queryset.none()
    
    def _apply_search_filter(self, queryset, search: str):
        """
        应用搜索筛选
        
        Args:
            queryset: 查询集
            search: 搜索关键词
            
        Returns:
            筛选后的查询集
        """
        return queryset.filter(
            Q(title__icontains=search) |
            Q(summary__icontains=search) |
            Q(content__icontains=search)
        )


class CategoryService:
    """分类服务类，处理分类相关的业务逻辑"""
    
    @staticmethod
    def get_categories_with_article_count() -> List[Dict[str, Any]]:
        """
        获取带文章数量的分类列表
        
        Returns:
            分类列表，包含文章数量统计
        """
        cache_key = "categories_with_count"
        cached_result = cache.get(cache_key)
        
        if cached_result:
            return cached_result
            
        categories = Category.objects.filter(is_active=True).order_by('sort_order', 'name')
        result = []
        
        for category in categories:
            article_count = Article.objects.filter(
                category_uuid=str(category.uuid),
                is_active=True,
                status=2
            ).count()
            
            result.append({
                'id': category.id,
                'name': category.name,
                'slug': category.slug,
                'description': category.description,
                'count': article_count,
                'sort_order': category.sort_order
            })
        
        # 缓存5分钟
        cache.set(cache_key, result, 300)
        return result


# 使用示例
router = Router(tags=["Articles - Optimized"])

@router.get("/optimized", response=dict)
def list_articles_optimized(
    request,
    filters: ArticleFilterSchema = Query(...)
):
    """
    优化的文章列表API
    
    Args:
        request: HTTP请求对象
        filters: 筛选条件
        
    Returns:
        API响应对象
    """
    try:
        api_service = OptimizedArticleAPI()
        result = api_service.get_filtered_articles(filters)
        return APIResponse.success(data=result)
    except Exception as e:
        return APIResponse.error(message="获取文章列表失败")


@router.get("/categories/with-count", response=dict)
def get_categories_with_count(request):
    """
    获取带文章数量的分类列表
    
    Args:
        request: HTTP请求对象
        
    Returns:
        API响应对象
    """
    try:
        categories = CategoryService.get_categories_with_article_count()
        return APIResponse.success(data=categories)
    except Exception as e:
        return APIResponse.error(message="获取分类列表失败")