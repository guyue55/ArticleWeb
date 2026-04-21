"""Article API endpoints using Django Ninja."""

import logging
from typing import Optional, List

from django.shortcuts import get_object_or_404
from django.db.models import Q
from django.utils import timezone
from django.conf import settings
from ninja import Router, Body
from ninja.security import HttpBearer, django_auth
from ninja.errors import HttpError

from apps.common.exceptions import (
    NotFoundException
)
from apps.common.responses import APIResponse, ErrorCodes
from apps.common.serializers import SerializerMixin
from apps.articles.uuid_serializer import ArticleUUIDSerializer
from .models import (
    Article, 
    Category, 
    ArticleClaim, 
    ArticleDownload,
    AIProvider,
    AIModel,
    PromptTemplate,
    HotTrend,
    GenerationHistory
)
from .schemas import (
    ArticleCreateSchema,
    ArticleUpdateSchema,
    ArticleResponseSchema,
    AIProviderSchema,
    AIProviderCreateSchema,
    AIProviderUpdateSchema,
    AIModelSchema,
    SystemConfigSchema,
    SystemConfigCreateSchema,
    PromptTemplateSchema,
    PromptTemplateCreateSchema,
    PromptTemplateUpdateSchema,
    HotTrendSchema,
    GenerationHistorySchema,
    AIArticleGenerateSchema,
    AIImageGenerateSchema,
)
from .services.ai_service import AIService
from .services.search_service import SearchService


logger = logging.getLogger(__name__)

router = Router(tags=["Articles"])


def get_current_user(request):
    """
    获取当前用户，只返回已登录的真实用户
    
    Args:
        request: HTTP请求对象
        
    Returns:
        User: 用户对象，如果未登录则返回None
    """
    # 检查是否有已登录的用户
    if hasattr(request, 'user') and request.user.is_authenticated:
        return request.user
    
    return None


class HTTPException(HttpError):
    """Custom HTTP Exception for compatibility."""
    def __init__(self, status_code: int, detail: str):
        super().__init__(status_code, detail)


class AuthBearer(HttpBearer):
    """Custom authentication bearer."""
    
    def authenticate(self, request, token):
        # TODO: Implement JWT token validation
        # For now, return a mock user for development
        try:
            from apps.users.models import User
            # Try to get the first active staff user, or create one if none exists
            user = User.objects.filter(is_active=True, is_staff=True).first()
            if not user:
                # Create a default admin user for development
                user = User.objects.create_superuser(
                    username='admin',
                    email='admin@example.com',
                    password='adminpassword'
                )
            return user
        except Exception as e:
            print(f"Authentication error: {e}")
            return None


# Create a more flexible auth that doesn't require token for some endpoints
class OptionalAuthBearer(HttpBearer):
    """Optional authentication - allows both authenticated and anonymous access."""
    
    def authenticate(self, request, token):
        if not token:
            return None  # Allow anonymous access
        
        try:
            from apps.users.models import User
            user = User.objects.filter(is_active=True).first()
            if not user:
                user = User.objects.create_user(
                    username='testuser',
                    email='test@example.com',
                    password='testpass123'
                )
            return user
        except Exception as e:
            print(f"Authentication error: {e}")
            return None


auth = django_auth

@router.get("/meta/categories", response=dict)
def get_meta_categories(request):
    """Get all active categories with article counts."""
    try:
        categories = Category.objects.filter(is_active=True).order_by('sort_order', 'name')
        
        # 手动构建包含文章数量的分类数据
        categories_data = []
        for category in categories:
            # 计算该分类下已发布文章的数量
            article_count = Article.objects.filter(
                category_uuid=category.uuid,
                is_active=True,
                status=2,  # 只计算已发布的文章
                is_claimable=True  # 只计算未领取的文章
            ).count()
            
            category_data = {
                'id': category.id,
                'uuid': category.uuid,
                'name': category.name,
                'slug': category.slug,
                'description': category.description,
                'count': article_count  # 添加文章数量
            }
            categories_data.append(category_data)
        
        return APIResponse.success(data=categories_data)
    
    except Exception as e:
        return APIResponse.error(
            code=ErrorCodes.INTERNAL_SERVER_ERROR,
            message="获取分类列表失败"
        )


@router.get("/meta/categories/filtered", response=dict)
def get_filtered_categories(
    request,
    search: Optional[str] = None,
    only_claimed: Optional[bool] = None
):
    """
    Get active categories with article counts based on current filters.
    
    Args:
        request: HTTP请求对象
        search: 搜索关键词
        only_claimed: 是否仅显示已领取的文章
    
    Returns:
        包含基于筛选条件的分类列表和文章数量的响应
    """
    try:
        categories = Category.objects.filter(is_active=True).order_by('sort_order', 'name')
        
        # 获取当前用户
        current_user = get_current_user(request)
        
        # 手动构建包含文章数量的分类数据，只返回有文章的分类
        categories_data = []
        for category in categories:
            # 构建基础查询集
            queryset = Article.objects.filter(
                category_uuid=category.uuid,
                is_active=True,
                status=2  # 只计算已发布的文章
            )
            
            # 应用搜索筛选
            if search:
                queryset = queryset.filter(
                    Q(title__icontains=search) |
                    Q(summary__icontains=search) |
                    Q(content__icontains=search)
                )
            
            # 应用已领取筛选
            if only_claimed is True:
                if current_user:
                    # 获取当前用户已领取的文章UUID列表
                    claimed_article_uuids = ArticleClaim.objects.filter(
                        user_uuid=current_user.uuid,
                        is_active=True
                    ).values_list('article_uuid', flat=True)
                    
                    # 只计算已领取的文章
                    queryset = queryset.filter(uuid__in=claimed_article_uuids)
                else:
                    # 如果用户未登录但要求显示已领取文章，返回空结果
                    queryset = queryset.none()
            else:
                # 只计算可领取的文章
                queryset = queryset.filter(is_claimable=True)
            
            # 计算该分类下符合条件的文章数量
            article_count = queryset.count()
            
            # 只有当分类下有文章时才添加到结果中
            if article_count > 0:
                category_data = {
                    'id': category.id,
                'uuid': category.uuid,
                    'name': category.name,
                    'slug': category.slug,
                    'description': category.description,
                    'count': article_count  # 添加文章数量
                }
                categories_data.append(category_data)
        
        return APIResponse.success(data=categories_data)
    
    except Exception as e:
        return APIResponse.error(
            code=ErrorCodes.INTERNAL_SERVER_ERROR,
            message="获取筛选分类列表失败"
        )


@router.get("", response=dict)
def list_articles(
    request,
    limit: int = 20,
    offset: int = 0,
    category_id: Optional[int] = None,
    category: Optional[str] = None,
    search: Optional[str] = None,
    status: Optional[int] = None,
    is_featured: Optional[bool] = None,
    sort_field: Optional[str] = None,
    sort_order: Optional[str] = None,
    only_claimed: Optional[bool] = None
):
    """
    List articles with pagination and filtering.
    
    Args:
        request: HTTP请求对象
        limit: 每页文章数量，默认20
        offset: 偏移量，用于分页
        category_id: 分类ID筛选
        category: 分类名称或slug筛选
        search: 搜索关键词
        status: 文章状态筛选
        is_featured: 是否精选文章
        sort_field: 排序字段 (create_time, update_time, view_count, title)
        sort_order: 排序方式 (asc=升序, desc=降序, none=无序/默认)
        only_claimed: 是否仅显示已领取的文章，默认False
    
    Returns:
        包含文章列表和分页信息的响应
    """
    try:
        queryset = Article.objects.filter(is_active=True, is_claimable=True if only_claimed is not True else False)
        
        # Apply filters
        if category_id:
            # Find category by ID and use its UUID
            try:
                category_obj = Category.objects.get(id=category_id, is_active=True)
                queryset = queryset.filter(category_uuid=category_obj.uuid)
            except Category.DoesNotExist:
                queryset = queryset.none()
        
        if category:
            # Support filtering by category name or slug
            try:
                category_obj = Category.objects.get(
                    Q(name=category) | Q(slug=category),
                    is_active=True
                )
                queryset = queryset.filter(category_uuid=category_obj.uuid)
            except Category.DoesNotExist:
                # If category not found, return empty result
                queryset = queryset.none()
        
        if search:
            queryset = queryset.filter(
                Q(title__icontains=search) |
                Q(summary__icontains=search) |
                Q(content__icontains=search)
            )
        
        if status is not None:
            queryset = queryset.filter(status=status)
        else:
            # Default to published articles for public API
            queryset = queryset.filter(status=2)
        
        if is_featured is not None:
            queryset = queryset.filter(is_featured=is_featured)
        
        # 获取当前用户
        current_user = get_current_user(request)
        
        # 筛选已领取的文章
        if only_claimed is True:
            if current_user:
                # 获取当前用户已领取的文章UUID列表
                claimed_article_uuids = ArticleClaim.objects.filter(
                    user_uuid=current_user.uuid,
                    is_active=True
                ).values_list('article_uuid', flat=True)
                
                # 只显示已领取的文章
                queryset = queryset.filter(uuid__in=claimed_article_uuids)
            else:
                # 如果用户未登录但要求显示已领取文章，返回空结果
                queryset = queryset.none()
        
        # Apply sorting - 优化的排序逻辑
        if sort_field and sort_order and sort_order != 'none':
            # 验证排序字段的有效性
            valid_sort_fields = [
        'create_time', 'update_time', 'view_count', 
        'title', 'publish_time'
    ]
            
            if sort_field in valid_sort_fields:
                if sort_order == 'desc':
                    queryset = queryset.order_by(f'-{sort_field}')
                elif sort_order == 'asc':
                    queryset = queryset.order_by(sort_field)
                else:
                    # 如果排序方式无效，使用默认排序
                    queryset = queryset.order_by('id')
            else:
                # 如果字段无效，使用默认排序
                queryset = queryset.order_by('id')
        elif sort_order == 'none':
            # 无序排序 - 使用随机排序，每次返回不同的顺序
            queryset = queryset.order_by('?')
        elif not sort_field or not sort_order:
            # 参数不完整时，按ID排序以保证一致性
            queryset = queryset.order_by('id')
        else:
            # 其他情况，使用默认排序
            queryset = queryset.order_by('id')
        
        # Get total count
        total = queryset.count()
        
        # Apply pagination
        articles = list(queryset[offset:offset + limit])
        
        # Get related objects
        from apps.users.models import User
        
        # Collect UUIDs
        author_uuids = [article.author_uuid for article in articles]
        category_uuids = [article.category_uuid for article in articles]
        # Fetch related objects
        authors = {user.uuid: user for user in User.objects.filter(uuid__in=author_uuids)}
        categories = {cat.uuid: cat for cat in Category.objects.filter(uuid__in=category_uuids)}
        
        # Get user claims for current user (if authenticated)
        user_claims = set()
        if current_user:
            article_uuids = [article.uuid for article in articles]
            claimed_articles = ArticleClaim.objects.filter(
                article_uuid__in=article_uuids,
                user_uuid=current_user.uuid,
                is_active=True
            ).values_list('article_uuid', flat=True)
            user_claims = set(claimed_articles)
        
        # Convert to ArticleListItemSchema objects
        articles_data = []
        for article in articles:
            # Get related objects with defaults
            author = authors.get(article.author_uuid)
            category = categories.get(article.category_uuid)
            
            # Create article item with proper defaults
            article_item = {
                'id': article.id,
                'title': article.title,
                'slug': article.slug,
                'summary': article.summary,
                'author': {
                    'id': author.id if author else 0,
                    'username': author.username if author else 'Unknown',
                    'email': author.email if author else '',
                    'first_name': author.first_name if author else '',
                    'last_name': author.last_name if author else '',
                    'avatar': getattr(author, 'avatar', '') if author else '',
                    'bio': getattr(author, 'bio', '') if author else '',
                    'is_active': author.is_active if author else True,
                    'date_joined': author.date_joined if author else article.create_time,
                },
                'category': {
                    'id': category.id if category else 0,
                    'name': category.name if category else 'Unknown',
                    'slug': category.slug if category else 'unknown',
                    'description': category.description if category else '',
                    'sort_order': category.sort_order if category else 0,
                },
                'featured_image': article.featured_image,
                'status': article.status,
                'is_featured': article.is_featured,
                'is_top': article.is_top,
                'view_count': article.view_count,
                'download_count': article.download_count,
                'claim_count': article.claim_count,
                'is_claimable': article.is_claimable,
                'can_claim': article.is_claimable and article.uuid not in user_claims,
                'can_download': article.is_downloadable,
                'publish_time': article.published_at,
                'create_time': article.create_time,
            }
            articles_data.append(article_item)
        
        # 计算分页信息
        current_page = (offset // limit) + 1
        total_pages = (total + limit - 1) // limit
        
        pagination_data = {
            'page': current_page,
            'page_size': limit,
            'total': total,
            'total_pages': total_pages,
            'has_next': offset + limit < total,
            'has_previous': offset > 0
        }
        
        # 返回标准的API响应格式
        return APIResponse.success(data={
            'articles': articles_data,
            'pagination': pagination_data
        })
    
    except Exception as e:
        logger.error(f"获取文章列表失败: {str(e)}")
        return APIResponse.error(message="获取文章列表失败")


@router.get("/records", response=dict)
def get_user_claim_records(request, page: int = 1, page_size: int = 10):
    """
    Get user's claim records with pagination.
    
    Args:
        request: HTTP请求对象
        page: 页码，从1开始
        page_size: 每页记录数，默认10条
        
    Returns:
        包含用户领取记录的API响应
    """
    try:
        # 检查用户是否已登录
        if not request.user.is_authenticated:
            return APIResponse.error(
                code=ErrorCodes.UNAUTHORIZED,
                message="请先登录后再查看领取记录"
            )
        
        user = request.user
        
        # 验证分页参数
        if page < 1:
            page = 1
        if page_size < 1 or page_size > 100:
            page_size = 10
        
        # 计算偏移量
        offset = (page - 1) * page_size
        
        # 获取用户的领取记录（分页）
        claims = ArticleClaim.objects.filter(
            user_uuid=user.uuid,
            is_active=True
        ).order_by('-claimed_at')[offset:offset + page_size]
        
        records = []
        for claim in claims:
            try:
                # 根据article_uuid获取文章
                article = Article.objects.filter(
                    uuid=claim.article_uuid,
                    is_active=True
                ).first()
                
                if not article:
                    continue
                
                # 获取分类信息
                category = None
                if article.category_uuid:
                    category = Category.objects.filter(
                        uuid=article.category_uuid,
                        is_active=True
                    ).first()
                
                # 所有领取的文章都显示为可下载状态，不区分是否已下载
                status = 'claimed'
                
                record = {
                    'id': claim.id,
                    'article_id': article.id,
                    'title': article.title,
                    'category': category.slug if category else 'uncategorized',
                    'category_name': category.name if category else '未分类',
                    'status': status,
                    'created_at': claim.claimed_at.isoformat(),
                    'views': article.view_count
                }
                records.append(record)
                
            except Exception as e:
                print(f"处理领取记录时出错: {e}")
                continue
        
        return APIResponse.success(data=records)
    
    except Exception as e:
        print(f"获取领取记录失败: {str(e)}")
        return APIResponse.error(
            code=ErrorCodes.INTERNAL_SERVER_ERROR,
            message="获取领取记录失败"
        )


@router.post("/records/{record_id}/download", response=dict)
def download_claimed_record(request, record_id: int):
    """
    Download a claimed article record.
    
    Args:
        request: HTTP请求对象
        record_id: 领取记录ID
        
    Returns:
        包含下载结果的API响应
    """
    try:
        # 检查用户是否已登录
        if not request.user.is_authenticated:
            return APIResponse.error(
                code=ErrorCodes.UNAUTHORIZED,
                message="请先登录后再下载文章"
            )
        
        user = request.user
        
        # 获取领取记录
        claim = get_object_or_404(
            ArticleClaim,
            id=record_id,
            user_uuid=user.uuid,
            is_active=True
        )
        
        # 获取文章
        article = Article.objects.filter(
            uuid=claim.article_uuid,
            is_active=True
        ).first()
        
        if not article:
            return APIResponse.error(
                code=ErrorCodes.NOT_FOUND,
                message="文章不存在"
            )
        
        # 获取文件信息
        file_info = article.file_info or {}
        file_type = "html"  # 默认下载html格式
        
        # 确定下载文件路径和名称
        file_path = None
        file_name = None
        
        if file_type in file_info:
            file_path = file_info[file_type]
            file_name = f"{article.slug}.{file_type}"
        elif "main" in file_info:
            file_path = file_info["main"]
            file_name = f"{article.slug}.md"
        elif "md_file" in file_info:
            file_path = file_info["md_file"]
            file_name = f"{article.slug}.md"
        elif article.file_attachment:
            file_path = article.file_attachment.url
            file_name = article.file_attachment.name.split('/')[-1]
        else:
            return APIResponse.error(
                code=ErrorCodes.BAD_REQUEST,
                message="该文章没有可下载的文件"
            )
        
        # 获取客户端信息
        client_ip = request.META.get('HTTP_X_FORWARDED_FOR')
        if client_ip:
            client_ip = client_ip.split(',')[0].strip()
        else:
            client_ip = request.META.get('REMOTE_ADDR')
        
        user_agent = request.META.get('HTTP_USER_AGENT', '')
        
        # 创建下载记录
        download = ArticleDownload.objects.create(
            article_uuid=article.uuid,
            user_uuid=user.uuid,
            ip_address=client_ip,
            user_agent=user_agent,
            file_type=file_type
        )
        
        # 更新文章下载计数
        article.download_count = ArticleDownload.objects.filter(
            article_uuid=article.uuid,
            is_active=True
        ).count()
        article.save(update_fields=['download_count'])
        
        print("*"*100)
        print(file_path)
        # 计算文件大小
        file_size = 0
        try:
            import os
            from django.conf import settings
            full_path = os.path.join(settings.MEDIA_ROOT, file_path.replace('/media/', ''))
            if os.path.exists(full_path):
                file_size = os.path.getsize(full_path)
        except:
            file_size = article.file_size or 0
        
        # 构建正确的静态文件URL
        from django.conf import settings
        if file_path.startswith('/'):
            download_url = file_path
        else:
            # 如果是相对路径，添加静态文件URL前缀
            download_url = f"{settings.STATIC_URL}{file_path}"
        
        return APIResponse.success(
            data={
                "download_url": download_url,
                "file_name": file_name,
                "file_type": file_type,
                "file_size": file_size,
                "download_count": article.download_count,
                "downloaded_at": download.downloaded_at,
                "message": "下载成功"
            }
        )
    
    except Exception as e:
        print(f"下载记录失败: {str(e)}")
        return APIResponse.error(
            code=ErrorCodes.INTERNAL_SERVER_ERROR,
            message="下载失败"
        )


@router.get("/{article_id}", response=dict)
def get_article_by_id(request, article_id: int):
    """Get article by ID and increment view count."""
    try:
        article = get_object_or_404(
            Article.objects.all(),
            id=article_id,
            is_active=True,
            status=2  # Only published articles
        )
        
        # Increment view count
        article.increment_view_count()
        
        # Serialize article using UUID serializer
        serialized_article = ArticleUUIDSerializer.serialize_article_detail(article)
        
        return APIResponse.success(data=serialized_article)
    
    except Exception as e:
        return APIResponse.error(
            code=ErrorCodes.NOT_FOUND,
            message="文章不存在"
        )


@router.get("/slug/{slug}", response=dict)
def get_article_by_slug(request, slug: str):
    """Get article by slug and increment view count."""
    try:
        article = get_object_or_404(
            Article.objects.all(),
            slug=slug,
            is_active=True,
            status=2  # Only published articles
        )
        
        # Increment view count
        article.increment_view_count()
        
        # Serialize article using UUID serializer
        from apps.articles.uuid_serializer import ArticleUUIDSerializer
        serialized_article = ArticleUUIDSerializer.serialize_article_detail(article)
        
        return APIResponse.success(data=serialized_article)
    
    except Exception as e:
        return APIResponse.error(
            code=ErrorCodes.NOT_FOUND,
            message="文章不存在"
        )


@router.post("", response=dict, auth=auth)
def create_article(request, data: ArticleCreateSchema):
    """Create a new article."""
    try:
        # Check if slug already exists
        if Article.objects.filter(slug=data.slug).exists():
            return APIResponse.error(
                code=ErrorCodes.BAD_REQUEST,
                message="文章别名已存在"
            )

        category_uuid = data.category_id
        if str(category_uuid).isdigit():
            category = Category.objects.filter(id=int(category_uuid), is_active=True).first()
            if not category:
                return APIResponse.error(
                    code=ErrorCodes.BAD_REQUEST,
                    message="分类不存在"
                )
            category_uuid = category.uuid
        
        # Create article
        article = Article.objects.create(
            title=data.title,
            slug=data.slug,
            summary=data.summary or '',
            content=data.content,
            author_uuid=request.auth.uuid,
            category_uuid=category_uuid,
            featured_image=data.featured_image or '',
            status=data.status or 1,
            is_featured=data.is_featured or False,
            is_top=data.is_top or False,
            is_downloadable=data.is_downloadable or False,
            file_info=data.file_info or {}
        )
        
        # 返回创建的文章重新加载文章以获取关联数据
        article = Article.objects.get(id=article.id)
        
        # 序列化文章数据 - 使用UUID序列化器
        from apps.articles.uuid_serializer import ArticleUUIDSerializer
        serialized_article = ArticleUUIDSerializer.serialize_article_detail(article)
        
        return APIResponse.success(data=serialized_article)
    
    except Exception as e:
        logger.exception("创建文章失败")
        return APIResponse.error(
            code=ErrorCodes.INTERNAL_SERVER_ERROR,
            message="创建文章失败"
        )


@router.put("/{article_id}", response=dict, auth=auth)
def update_article(request, article_id: int, data: ArticleUpdateSchema):
    """Update an existing article."""
    try:
        article = get_object_or_404(Article, id=article_id, is_active=True)
        
        # Check if user has permission to edit
        if article.author != request.auth and not request.auth.is_staff:
            return APIResponse.error(
                code=ErrorCodes.FORBIDDEN,
                message="没有权限编辑此文章"
            )
        
        # Check slug uniqueness if changed
        if data.slug and data.slug != article.slug:
            if Article.objects.filter(slug=data.slug).exclude(id=article_id).exists():
                return APIResponse.error(
                    code=ErrorCodes.BAD_REQUEST,
                    message="文章别名已存在"
                )
        
        # Update article fields
        for field, value in data.dict(exclude_unset=True).items():
            if hasattr(article, field) and value is not None:
                setattr(article, field, value)
        
        article.save()
        
        # Reload article to get updated data with relations
        article.refresh_from_db()
        serialized_article = SerializerMixin.serialize_article_detail(article)
        return APIResponse.success(data=serialized_article)
    
    except Exception as e:
        return APIResponse.error(
            code=ErrorCodes.INTERNAL_SERVER_ERROR,
            message="更新文章失败"
        )


@router.delete("/{article_id}", response=dict, auth=auth)
def delete_article(request, article_id: int):
    """Soft delete an article."""
    try:
        article = get_object_or_404(Article, id=article_id, is_active=True)
        
        # Check if user has permission to delete
        if article.author != request.auth and not request.auth.is_staff:
            return APIResponse.error(
                code=ErrorCodes.FORBIDDEN,
                message="没有权限删除此文章"
            )
        
        article.soft_delete()
        
        return APIResponse.success(
            data={
                "id": article_id
            }
        )
    
    except Exception as e:
        return APIResponse.error(
            code=ErrorCodes.INTERNAL_SERVER_ERROR,
            message="删除文章失败"
        )








@router.post("/{article_id}/claim", response=dict)
def claim_article(request, article_id: int):
    """
    Claim an article - requires user authentication.
    
    Args:
        request: HTTP请求对象
        article_id: 文章ID
        
    Returns:
        包含领取结果的API响应
    """
    try:
        # 检查用户是否已登录
        if not request.user.is_authenticated:
            return APIResponse.error(
                code=ErrorCodes.UNAUTHORIZED,
                message="请先登录后再领取文章"
            )
        
        article = get_object_or_404(Article, id=article_id, is_active=True, status=2)
        
        # 使用已登录的用户
        user = request.user
        
        # Check if article is claimable
        if not article.is_claimable:
            return APIResponse.error(
                code=ErrorCodes.BAD_REQUEST,
                message="此文章不支持领取"
            )
        
        # Check if user has already claimed this article
        existing_claim = ArticleClaim.objects.filter(
            article_uuid=article.uuid,
            user_uuid=user.uuid,
            is_active=True
        ).first()
        
        if existing_claim:
            return APIResponse.error(
                code=ErrorCodes.BAD_REQUEST,
                message="您已经领取过此文章"
            )
        
        # Create claim record
        claim = ArticleClaim.objects.create(
            article_uuid=article.uuid,
            user_uuid=user.uuid
        )
        
        # Update article claim count
        article.claim_count = ArticleClaim.objects.filter(
            article_uuid=article.uuid,
            is_active=True
        ).count()
        article.is_claimable = False
        article.save(update_fields=['claim_count', 'is_claimable'])
        
        return APIResponse.success(
            data={
                "claimed": True,
                "claim_count": article.claim_count,
                "claimed_at": claim.claimed_at
            }
        )
    
    except Article.DoesNotExist:
        return APIResponse.error(
            code=ErrorCodes.NOT_FOUND,
            message="文章不存在"
        )
    except Exception as e:
        print(f"领取文章失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return APIResponse.error(
            code=ErrorCodes.INTERNAL_SERVER_ERROR,
            message="领取文章失败"
        )


@router.post("/{article_id}/download", response=dict)
def download_article(request, article_id: int, file_type: str = "html"):
    """
    Download an article file - requires user authentication.
    
    Args:
        request: HTTP请求对象
        article_id: 文章ID
        file_type: 文件类型 (md, html, meta, all)
        
    Returns:
        包含下载信息的API响应
    """
    try:
        # 检查用户是否已登录
        if not request.user.is_authenticated:
            return APIResponse.error(
                code=ErrorCodes.UNAUTHORIZED,
                message="请先登录后再下载文章"
            )
        
        article = get_object_or_404(Article, id=article_id, is_active=True, status=2)
        
        # 使用已登录的用户
        user = request.user
        
        # # Check if article is downloadable
        # if not article.is_downloadable:
        #     return APIResponse.error(
        #         code=ErrorCodes.BAD_REQUEST,
        #         message="此文章不支持下载"
        #     )
        
        # 移除领取验证要求，允许直接下载
        # 注释掉原有的领取检查逻辑
        # has_claimed = ArticleClaim.objects.filter(
        #     article_uuid=article.uuid,
        #     user_uuid=user.uuid,
        #     is_active=True
        # ).exists()
        # 
        # require_claim = getattr(article, 'require_claim_to_download', False)
        # if require_claim and not has_claimed:
        #     return APIResponse.error(
        #         code=ErrorCodes.BAD_REQUEST,
        #         message="请先领取文章后再下载"
        #     )
        
        # Get file info from article
        file_info = article.file_info or {}
        
        # Determine which file to download based on file_type
        file_path = None
        file_name = None
        
        # 修复文件类型映射 - 使用实际的file_info键名
        if file_type == "md":
            # 尝试多种可能的键名
            if "main" in file_info:
                file_path = file_info["main"]
                file_name = f"{article.slug}.md"
            elif "md_file" in file_info:
                file_path = file_info["md_file"]
                file_name = f"{article.slug}.md"
        elif file_type == "html":
            if "html" in file_info:
                file_path = file_info["html"]
                file_name = f"{article.slug}.html"
            elif "html_file" in file_info:
                file_path = file_info["html_file"]
                file_name = f"{article.slug}.html"
        elif file_type == "meta":
            if "meta" in file_info:
                file_path = file_info["meta"]
                file_name = f"{article.slug}.meta"
            elif "meta_file" in file_info:
                file_path = file_info["meta_file"]
                file_name = f"{article.slug}.meta"
        elif file_type == "all":
            # Return all available files info
            available_files = []
            if "main" in file_info or "md_file" in file_info:
                path = file_info.get("main") or file_info.get("md_file")
                available_files.append({
                    "type": "md",
                    "path": path,
                    "name": f"{article.slug}.md"
                })
            if "html" in file_info or "html_file" in file_info:
                path = file_info.get("html") or file_info.get("html_file")
                available_files.append({
                    "type": "html",
                    "path": path,
                    "name": f"{article.slug}.html"
                })
            if "meta" in file_info or "meta_file" in file_info:
                path = file_info.get("meta") or file_info.get("meta_file")
                available_files.append({
                    "type": "meta",
                    "path": path,
                    "name": f"{article.slug}.meta"
                })
            
            return APIResponse.success(
                data={
                    "available_files": available_files,
                    "article_title": article.title,
                    "article_slug": article.slug
                }
            )
        else:
            # Fallback to original file_attachment if available
            if article.file_attachment:
                file_path = article.file_attachment.url
                file_name = article.file_attachment.name.split('/')[-1]
            else:
                return APIResponse.error(
                    code=ErrorCodes.BAD_REQUEST,
                    message=f"请求的文件类型 '{file_type}' 不可用"
                )
        
        if not file_path:
            return APIResponse.error(
                code=ErrorCodes.BAD_REQUEST,
                message=f"请求的文件类型 '{file_type}' 不可用"
            )
        
        # Get client IP and user agent
        client_ip = request.META.get('HTTP_X_FORWARDED_FOR')
        if client_ip:
            client_ip = client_ip.split(',')[0].strip()
        else:
            client_ip = request.META.get('REMOTE_ADDR')
        
        user_agent = request.META.get('HTTP_USER_AGENT', '')
        
        # Create download record
        download = ArticleDownload.objects.create(
            article_uuid=article.uuid,
            user_uuid=user.uuid,
            ip_address=client_ip,
            user_agent=user_agent,
            file_type=file_type  # Add file_type to track what was downloaded
        )
        
        # Update article download count
        article.download_count = ArticleDownload.objects.filter(
            article_uuid=article.uuid,
            is_active=True
        ).count()
        article.save(update_fields=['download_count'])
        
        # Calculate file size if possible
        file_size = 0
        try:
            import os
            from django.conf import settings
            full_path = os.path.join(settings.MEDIA_ROOT, file_path.replace('/media/', ''))
            if os.path.exists(full_path):
                file_size = os.path.getsize(full_path)
        except:
            file_size = article.file_size or 0
        
        return APIResponse.success(
            data={
                "download_url": file_path,
                "file_name": file_name,
                "file_type": file_type,
                "file_size": file_size,
                "download_count": article.download_count,
                "downloaded_at": download.downloaded_at
            }
        )
    
    except Article.DoesNotExist:
        return APIResponse.error(
            code=ErrorCodes.NOT_FOUND,
            message="文章不存在"
        )
    except Exception as e:
        print(f"下载文章失败: {str(e)}")
        return APIResponse.error(
            code=ErrorCodes.INTERNAL_SERVER_ERROR,
            message="下载文章失败"
        )


@router.get("/{article_id}/claim-status", response=dict)
def get_article_claim_status(request, article_id: int):
    """
    Get article claim status - requires user authentication.
    
    Args:
        request: HTTP请求对象
        article_id: 文章ID
        
    Returns:
        包含文章领取状态的API响应
    """
    try:
        # 检查用户是否已登录
        if not request.user.is_authenticated:
            return APIResponse.error(
                code=ErrorCodes.UNAUTHORIZED,
                message="请先登录后再查看文章状态"
            )
        
        article = get_object_or_404(Article, id=article_id, is_active=True, status=2)
        
        # 使用已登录的用户
        user = request.user
        
        # Check if user has claimed this article
        claim = ArticleClaim.objects.filter(
            article_uuid=article.uuid,
            user_uuid=user.uuid,
            is_active=True
        ).first()
        
        # Check if user has downloaded this article
        has_downloaded = ArticleDownload.objects.filter(
            article_uuid=article.uuid,
            user_uuid=user.uuid,
            is_active=True
        ).exists()
        
        return APIResponse.success(
            data={
                "is_claimed": claim is not None,
                "claimed_at": claim.claimed_at if claim else None,
                "has_downloaded": has_downloaded,
                "is_claimable": article.is_claimable,
                "is_downloadable": article.is_downloadable,
                "claim_count": article.claim_count,
                "download_count": article.download_count
            }
        )
    
    except Exception as e:
        return APIResponse.error(
            code=ErrorCodes.INTERNAL_SERVER_ERROR,
            message="获取文章状态失败"
        )


# --- 系统配置接口 ---

@router.get("/system/configs", response=dict, auth=auth)
def list_system_configs(request):
    """获取所有系统配置"""
    try:
        if not request.auth.is_staff:
            return APIResponse.error(code=ErrorCodes.FORBIDDEN, message="权限不足")
        
        from .models import SystemConfig
        configs = SystemConfig.objects.filter(is_active=True)
        data = []
        for c in configs:
            item = SystemConfigSchema.model_validate(c).model_dump()
            # 使用模型自带的脱敏逻辑
            item['value'] = c.mask_value()
            data.append(item)
        return APIResponse.success(data=data)
    except Exception as e:
        logger.error(f"获取系统配置失败: {type(e).__name__}")
        return APIResponse.error(
            code=ErrorCodes.INTERNAL_SERVER_ERROR,
            message="获取系统配置失败"
        )


@router.post("/system/configs", response=dict, auth=auth)
def create_system_config(request, data: SystemConfigCreateSchema):
    """创建或更新系统配置"""
    try:
        if not request.auth.is_staff:
            return APIResponse.error(code=ErrorCodes.FORBIDDEN, message="权限不足")
        
        from .models import SystemConfig
        config, created = SystemConfig.objects.update_or_create(
            key=data.key,
            defaults={
                "value": data.value,
                "description": data.description,
                "is_secret": data.is_secret,
                "is_active": True
            }
        )
        # 返回脱敏后的数据
        res_data = SystemConfigSchema.model_validate(config).model_dump()
        res_data['value'] = config.mask_value()
        return APIResponse.success(data=res_data)
    except Exception as e:
        logger.error(f"保存系统配置失败: {type(e).__name__}")
        return APIResponse.error(
            code=ErrorCodes.INTERNAL_SERVER_ERROR,
            message="保存系统配置失败"
        )


# --- AI 在线生成模块接口 ---

@router.post("/ai/providers/{provider_id}/scan", response=dict, auth=auth)
def scan_ai_models(request, provider_id: int):
    """扫描并同步 AI 供应商的模型列表"""
    if not request.auth.is_staff:
        return APIResponse.error(code=ErrorCodes.FORBIDDEN, message="权限不足")
    
    result = AIService.scan_provider_models(provider_id)
    if not result["success"]:
        return APIResponse.error(message=result.get("error", "扫描失败"))
    
    return APIResponse.success(data=result)


@router.get("/ai/providers", response=dict)
def list_ai_providers(request):
    """获取所有活跃的 AI 供应商（含模型列表）"""
    providers = AIProvider.objects.filter(is_active=True).prefetch_related('models')
    data = []
    for p in providers:
        # 排除 models 字段进行初步验证
        item = AIProviderSchema.model_validate(p).model_dump(exclude={'models'})
        # 手动补充模型列表
        item['models'] = [AIModelSchema.model_validate(m).model_dump() for m in p.models.filter(is_active=True, is_available=True)]
        data.append(item)
    return APIResponse.success(data=data)


@router.post("/ai/providers", response=dict, auth=auth)
def create_ai_provider(request, data: AIProviderCreateSchema):
    """创建 AI 供应商 (仅管理员)"""
    if not request.auth.is_staff:
        return APIResponse.error(code=ErrorCodes.FORBIDDEN, message="权限不足")
    
    provider = AIProvider.objects.create(**data.dict())
    # 转换为 Schema 时手动处理 models 列表，因为刚创建时肯定为空
    res_data = AIProviderSchema.model_validate(provider).model_dump()
    res_data['models'] = []
    return APIResponse.success(data=res_data)


@router.put("/ai/providers/{provider_id}", response=dict, auth=auth)
def update_ai_provider(request, provider_id: int, data: AIProviderUpdateSchema):
    """更新 AI 供应商 (仅管理员)"""
    if not request.auth.is_staff:
        return APIResponse.error(code=ErrorCodes.FORBIDDEN, message="权限不足")
    
    provider = get_object_or_404(AIProvider, id=provider_id)
    for attr, value in data.dict(exclude_unset=True).items():
        setattr(provider, attr, value)
    provider.save()
    
    res_data = AIProviderSchema.model_validate(provider).model_dump()
    res_data['models'] = [AIModelSchema.model_validate(m).model_dump() for m in provider.models.all()]
    return APIResponse.success(data=res_data)


@router.delete("/ai/providers/{provider_id}", response=dict, auth=auth)
def delete_ai_provider(request, provider_id: int):
    """删除 AI 供应商 (仅管理员)"""
    if not request.auth.is_staff:
        return APIResponse.error(code=ErrorCodes.FORBIDDEN, message="权限不足")
    
    provider = get_object_or_404(AIProvider, id=provider_id)
    provider.soft_delete()
    return APIResponse.success(message="删除成功")


@router.get("/ai/templates", response=dict)
def list_prompt_templates(request, category_uuid: Optional[str] = None):
    """获取提示词模板列表"""
    queryset = PromptTemplate.objects.filter(is_active=True)
    if category_uuid:
        queryset = queryset.filter(category_uuid=category_uuid)
    
    data = [PromptTemplateSchema.model_validate(t).model_dump() for t in queryset]
    return APIResponse.success(data=data)


@router.post("/ai/templates", response=dict, auth=auth)
def create_prompt_template(request, data: PromptTemplateCreateSchema):
    """创建提示词模板"""
    if not request.auth.is_staff:
        return APIResponse.error(code=ErrorCodes.FORBIDDEN, message="权限不足")
    template = PromptTemplate.objects.create(**data.dict())
    return APIResponse.success(data=PromptTemplateSchema.model_validate(template).model_dump())


@router.get("/ai/templates/export", response=dict, auth=auth)
def export_prompt_templates(request):
    """导出所有提示词模板为 JSON"""
    if not request.auth.is_staff:
        return APIResponse.error(code=ErrorCodes.FORBIDDEN, message="权限不足")
    templates = PromptTemplate.objects.filter(is_active=True)
    data = []
    for t in templates:
        data.append({
            "title": t.title,
            "category_uuid": t.category_uuid,
            "content": t.content,
            "variables": t.variables,
            "description": t.description
        })
    return APIResponse.success(data=data)


@router.post("/ai/templates/import", response=dict, auth=auth)
def import_prompt_templates(request, data: List[dict] = Body(...)):
    """从 JSON 导入提示词模板"""
    if not request.auth.is_staff:
        return APIResponse.error(code=ErrorCodes.FORBIDDEN, message="权限不足")
    created_count = 0
    for item in data:
        try:
            PromptTemplate.objects.create(
                title=item.get("title"),
                category_uuid=item.get("category_uuid"),
                content=item.get("content"),
                variables=item.get("variables", []),
                description=item.get("description", "")
            )
            created_count += 1
        except Exception as e:
            logger.error(f"导入模板失败: {str(e)}")
            continue
            
    return APIResponse.success(data={"created": created_count}, message=f"成功导入 {created_count} 个模板")


@router.put("/ai/templates/{template_id}", response=dict, auth=auth)
def update_prompt_template(request, template_id: int, data: PromptTemplateUpdateSchema):
    """更新提示词模板"""
    if not request.auth.is_staff:
        return APIResponse.error(code=ErrorCodes.FORBIDDEN, message="权限不足")
    template = get_object_or_404(PromptTemplate, id=template_id)
    # 这里可以增加权限检查，比如只能编辑自己创建的，目前先允许登录用户编辑
    for attr, value in data.dict(exclude_unset=True).items():
        setattr(template, attr, value)
    template.save()
    return APIResponse.success(data=PromptTemplateSchema.model_validate(template).model_dump())


@router.delete("/ai/templates/{template_id}", response=dict, auth=auth)
def delete_prompt_template(request, template_id: int):
    """删除提示词模板"""
    if not request.auth.is_staff:
        return APIResponse.error(code=ErrorCodes.FORBIDDEN, message="权限不足")
    template = get_object_or_404(PromptTemplate, id=template_id)
    template.soft_delete()
    return APIResponse.success(message="删除成功")


@router.post("/ai/generate", response=dict, auth=auth)
def generate_ai_article(request, data: AIArticleGenerateSchema):
    """在线生成 AI 文章"""
    # 调用 AI 服务
    result = AIService.generate_from_template(
        template_id=data.template_id,
        provider_id=data.provider_id,
        model_name=data.model_name,
        inputs=data.inputs,
        user_uuid=request.auth.uuid
    )

    if not result["success"]:
        return APIResponse.error(message=result.get("error", "生成失败"))

    # 如果需要直接存入文章表
    article_id = None
    if data.save_to_article:
        try:
            # 这里简单实现，实际可能需要更复杂的逻辑处理分类等
            template = PromptTemplate.objects.get(id=data.template_id)
            title = data.inputs.get("title", f"AI生成文章_{timezone.now().strftime('%Y%m%d%H%M')}")
            
            # 生成唯一 slug
            import uuid
            slug = f"ai-{str(uuid.uuid4())[:8]}"
            
            article = Article.objects.create(
                title=title,
                slug=slug,
                content=result["result"],
                summary=data.inputs.get("summary", result["result"][:200]),
                author_uuid=request.auth.uuid,
                category_uuid=template.category_uuid,
                status=1 # 默认为草稿
            )
            article_id = article.id
        except Exception as e:
            logger.error(f"保存 AI 文章失败: {str(e)}")

    return APIResponse.success(data={
        "content": result["result"],
        "history_id": result.get("history_id"),
        "article_id": article_id
    })


@router.post("/ai/generate-image", response=dict, auth=auth)
def generate_ai_image(request, data: AIImageGenerateSchema):
    """在线生成 AI 文章配图"""
    prompt = data.prompt
    
    # 如果没有提供提示词，则根据文章内容生成
    if not prompt:
        if not data.article_content:
            return APIResponse.error(message="必须提供提示词或文章内容")
        
        # 使用默认文本模型生成提示词 (这里可以根据需要优化，比如让用户选模型)
        # 简单起见，这里假设用户传入了 provider_id 和 model_name 是用于图片的
        # 实际上生成提示词可能需要一个文本模型
        # 我们先尝试找一个该供应商的文本模型，或者让用户传两个模型 ID？
        # 为了简单，我们先要求必须传 prompt，或者在这里直接用传入的模型（如果它支持文本的话）
        # 更好的做法是：如果没传 prompt，先调用一个默认的文本模型生成 prompt
        
        # 临时方案：如果没传 prompt，直接报错提示需要 prompt (前端负责生成 prompt)
        return APIResponse.error(message="当前版本请提供图片生成提示词")

    # 调用 AI 服务生成图片
    result = AIService.generate_image(
        provider_id=data.provider_id,
        model_name=data.model_name,
        prompt=prompt,
        user_uuid=request.auth.uuid,
        size=data.size,
        quality=data.quality
    )

    if not result["success"]:
        return APIResponse.error(message=result.get("error", "图片生成失败"))

    # 如果提供了文章 ID，则更新文章的特色图片
    if data.article_id:
        try:
            article = Article.objects.get(id=data.article_id)
            # 这里简单保存 URL，实际生产环境建议下载图片到本地存储
            article.featured_image = result["image_url"]
            article.save(update_fields=['featured_image'])
        except Article.DoesNotExist:
            logger.warning(f"更新配图时文章 ID {data.article_id} 不存在")

    return APIResponse.success(data={
        "image_url": result["image_url"],
        "history_id": result.get("history_id")
    })


@router.post("/ai/generate-image-prompt", response=dict, auth=auth)
def generate_image_prompt(request, data: dict = Body(...)):
    """根据文章内容生成图片提示词"""
    article_content = data.get("content")
    provider_id = data.get("provider_id")
    model_name = data.get("model_name")
    
    if not all([article_content, provider_id, model_name]):
        return APIResponse.error(message="缺少必要参数")
    
    result = AIService.generate_image_prompt(
        provider_id=provider_id,
        model_name=model_name,
        article_content=article_content,
        user_uuid=request.auth.uuid
    )
    
    if not result["success"]:
        return APIResponse.error(message=result.get("error", "生成提示词失败"))
        
    return APIResponse.success(data={"prompt": result["prompt"]})


@router.post("/ai/polish", response=dict, auth=auth)
def polish_article(request, data: dict = Body(...)):
    """根据用户指令润色文章内容"""
    content = data.get("content")
    instruction = data.get("instruction")
    provider_id = data.get("provider_id")
    model_name = data.get("model_name")
    
    if not all([content, instruction, provider_id, model_name]):
        return APIResponse.error(message="缺少必要参数")
    
    result = AIService.polish_content(
        provider_id=provider_id,
        model_name=model_name,
        content=content,
        instruction=instruction,
        user_uuid=request.auth.uuid
    )
    
    if not result["success"]:
        return APIResponse.error(message=result.get("error", "润色失败"))
        
    return APIResponse.success(data={"content": result["result"]})


@router.post("/ai/trends/discover", response=dict, auth=auth)
def discover_trends(request, category_uuid: str, query: Optional[str] = None):
    """联网发现热门选题"""
    search_service = SearchService()
    trends = search_service.discover_hot_trends(category_uuid, query)
    return APIResponse.success(data=trends)


# --- OpenAI Mock Endpoints for Development ---

if settings.DEBUG:
    @router.get("/v1/models", tags=["Mock"], auth=None)
    def mock_v1_models(request):
        """Mock OpenAI models endpoint"""
        return {
            "object": "list",
            "data": [
                {"id": "gpt-3.5-turbo", "object": "model", "created": 1677610602, "owned_by": "openai"},
                {"id": "gpt-4", "object": "model", "created": 1687882411, "owned_by": "openai"},
                {"id": "dall-e-3", "object": "model", "created": 1698785189, "owned_by": "openai"}
            ]
        }


    @router.post("/v1/chat/completions", tags=["Mock"], auth=None)
    def mock_chat_completions(request, data: dict = Body(...)):
        """Mock OpenAI chat completions endpoint"""
        messages = data.get("messages", [])
        prompt = messages[-1]["content"] if messages else ""
        
        # Simulate different responses based on prompt
        if "图片" in prompt and "提示词" in prompt:
            result = "A beautiful scenery of mountains at sunset, cinematic lighting, 8k resolution"
        elif "润色" in prompt or "修改" in prompt:
            result = "这是润色后的内容：\n\n今天天气真不错，阳光明媚，微风徐徐，非常适合户外活动。"
        else:
            result = f"这是一篇关于 {prompt[:20]}... 的 AI 生成文章内容。\n\n随着人工智能技术的发展，创作变得更加高效..."

        return {
            "id": "chatcmpl-mock",
            "object": "chat.completion",
            "created": int(timezone.now().timestamp()),
            "model": data.get("model", "gpt-3.5-turbo"),
            "choices": [
                {
                    "index": 0,
                    "message": {"role": "assistant", "content": result},
                    "finish_reason": "stop"
                }
            ]
        }


    @router.post("/v1/images/generations", tags=["Mock"], auth=None)
    def mock_image_generations(request, data: dict = Body(...)):
        """Mock OpenAI image generations endpoint"""
        return {
            "created": int(timezone.now().timestamp()),
            "data": [
                {"url": "https://picsum.photos/1024/1024"}
            ]
        }


@router.get("/ai/trends", response=dict, auth=auth)
def list_trends(request, category_uuid: str, limit: int = 10):
    """获取已发现的热门选题"""
    search_service = SearchService()
    trends = search_service.get_trends_by_category(category_uuid, limit)
    data = [HotTrendSchema.model_validate(t).model_dump() for t in trends]
    return APIResponse.success(data=data)


@router.get("/ai/history", response=dict, auth=auth)
def list_generation_history(request, limit: int = 20, offset: int = 0):
    """获取用户的生成记录"""
    queryset = GenerationHistory.objects.filter(
        user_uuid=request.auth.uuid,
        is_active=True
    ).order_by('-create_time')
    
    total = queryset.count()
    history = queryset[offset:offset+limit]
    
    data = [GenerationHistorySchema.model_validate(h).model_dump() for h in history]
    return APIResponse.success(data={
        "items": data,
        "total": total
    })
