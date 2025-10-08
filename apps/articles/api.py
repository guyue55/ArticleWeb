"""Article API endpoints using Django Ninja."""

import logging
from typing import Optional
from django.shortcuts import get_object_or_404
from django.db.models import Q
from ninja import Router
from ninja.security import HttpBearer
from ninja.errors import HttpError

from apps.common.exceptions import (
    NotFoundException
)
from apps.common.responses import APIResponse, ErrorCodes
from apps.common.serializers import SerializerMixin
from apps.articles.uuid_serializer import ArticleUUIDSerializer
from .models import Article, Category, ArticleClaim, ArticleDownload
from .schemas import (
    ArticleCreateSchema,
    ArticleUpdateSchema,
    ArticleResponseSchema
)


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
            # Try to get the first active user, or create one if none exists
            user = User.objects.filter(is_active=True).first()
            if not user:
                # Create a default user for development
                user = User.objects.create_user(
                    username='testuser',
                    email='test@example.com',
                    password='testpass123'
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


auth = AuthBearer()
optional_auth = OptionalAuthBearer()

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


@router.get("/slug/{slug}", response=ArticleResponseSchema)
def get_article_by_slug(request, slug: str):
    """Get article by slug and increment view count."""
    try:
        article = get_object_or_404(
            Article.objects.select_related('author', 'category'),
            slug=slug,
            is_active=True,
            status=2  # Only published articles
        )
        
        # Increment view count
        article.increment_view_count()
        
        return article
    
    except Exception as e:
        raise NotFoundException(
            message="文章不存在",
            details={"slug": slug}
        )


@router.post("", response=dict, auth=auth)
def create_article(request, data: ArticleCreateSchema):
    """Create a new article."""
    try:
        # Check if slug already exists
        if Article.objects.filter(slug=data.slug).exists():
            return {
                "code": 400,
                "message": "文章别名已存在",
                "requestId": "",
                "data": None
            }
        
        # Create article
        article = Article.objects.create(
            title=data.title,
            slug=data.slug,
            summary=data.summary or '',
            content=data.content,
            author_uuid=request.auth.uuid,
            category_uuid=data.category_id,
            status=data.status or 1,
            is_featured=data.is_featured or False,
            is_top=data.is_top or False,
            is_downloadable=data.is_downloadable or False,
            file_info=data.file_info
        )
        
        # 返回创建的文章重新加载文章以获取关联数据
        article = Article.objects.get(id=article.id)
        
        # 序列化文章数据 - 使用UUID序列化器
        from apps.articles.uuid_serializer import ArticleUUIDSerializer
        serialized_article = ArticleUUIDSerializer.serialize_article_detail(article)
        
        return APIResponse.success(data=serialized_article)
    
    except Exception as e:
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