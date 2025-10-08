"""Article schemas for API serialization using Pydantic."""

from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field, validator

from apps.users.schemas import UserResponseSchema


class CategoryResponseSchema(BaseModel):
    """Category response schema."""
    id: int
    name: str
    slug: str
    description: str = ''
    sort_order: int = 0
    
    class Config:
        from_attributes = True





class ArticleCreateSchema(BaseModel):
    """Article creation schema."""
    title: str = Field(..., min_length=1, max_length=200, description="文章标题")
    slug: str = Field(..., min_length=1, max_length=200, description="文章别名")
    summary: Optional[str] = Field(None, max_length=500, description="文章摘要")
    content: str = Field(..., min_length=1, description="文章内容")
    category_id: int = Field(..., description="分类ID")
    featured_image: Optional[str] = Field(None, max_length=255, description="特色图片")
    status: Optional[int] = Field(1, description="状态：1草稿，2已发布，3已下线")
    is_featured: Optional[bool] = Field(False, description="是否推荐")
    is_top: Optional[bool] = Field(False, description="是否置顶")
    is_downloadable: Optional[bool] = Field(False, description="是否可下载")
    file_info: Optional[dict] = Field(None, description="文件信息（MD、HTML、META等）")
    publish_time: Optional[datetime] = Field(None, description="发布时间")
    
    @validator('slug')
    def validate_slug(cls, v):
        """Validate slug format."""
        import re
        if not re.match(r'^[a-zA-Z0-9-_]+$', v):
            raise ValueError('别名只能包含字母、数字、连字符和下划线')
        return v
    
    @validator('status')
    def validate_status(cls, v):
        """Validate status value."""
        if v not in [1, 2, 3]:
            raise ValueError('状态值必须是1（草稿）、2（已发布）或3（已下线）')
        return v


class ArticleUpdateSchema(BaseModel):
    """Article update schema."""
    title: Optional[str] = Field(None, min_length=1, max_length=200, description="文章标题")
    slug: Optional[str] = Field(None, min_length=1, max_length=200, description="文章别名")
    summary: Optional[str] = Field(None, min_length=10, max_length=500, description="文章摘要")
    content: Optional[str] = Field(None, min_length=50, description="文章内容")
    category_uuid: Optional[str] = Field(None, description="分类UUID")
    featured_image: Optional[str] = Field(None, description="特色图片路径")
    is_featured: Optional[bool] = Field(None, description="是否推荐")
    is_top: Optional[bool] = Field(None, description="是否置顶")
    allow_download: Optional[bool] = Field(None, description="是否允许下载")
    allow_claim: Optional[bool] = Field(None, description="是否允许领取")
    
    @validator('slug')
    def validate_slug(cls, v):
        """Validate slug format."""
        if v is not None:
            import re
            if not re.match(r'^[a-zA-Z0-9-_]+$', v):
                raise ValueError('别名只能包含字母、数字、连字符和下划线')
        return v


class ArticleResponseSchema(BaseModel):
    """Article response schema."""
    id: int
    title: str
    slug: str
    summary: str
    content: str
    author: UserResponseSchema
    category: CategoryResponseSchema
    featured_image: str
    status: int
    is_featured: bool
    is_top: bool
    view_count: int
    download_count: int
    claim_count: int
    file_attachment: Optional[str]
    file_size: int
    is_downloadable: bool
    is_claimable: bool
    file_info: Optional[dict]
    publish_time: Optional[datetime]
    create_time: datetime
    update_time: datetime
    
    class Config:
        from_attributes = True


class ArticleListItemSchema(BaseModel):
    """Article list item schema (simplified)."""
    id: int
    title: str
    slug: str
    summary: str
    author: UserResponseSchema
    category: CategoryResponseSchema
    featured_image: str
    status: int
    is_featured: bool
    is_top: bool
    view_count: int
    download_count: int
    claim_count: int
    is_claimable: bool
    can_claim: bool = Field(default=False, description="当前用户是否可以领取")
    can_download: bool = Field(default=False, description="当前用户是否可以下载")
    publish_time: Optional[datetime]
    create_time: datetime
    
    class Config:
        from_attributes = True


class PaginationSchema(BaseModel):
    """Pagination schema."""
    page: int
    page_size: int
    total: int
    total_pages: int
    has_next: bool
    has_prev: bool


class ArticleListResponseSchema(BaseModel):
    """Article list response schema."""
    articles: List[ArticleListItemSchema]
    pagination: PaginationSchema





class CategoryCreateSchema(BaseModel):
    """Category creation schema."""
    name: str = Field(..., min_length=1, max_length=100, description="分类名称")
    slug: str = Field(..., min_length=1, max_length=100, description="分类别名")
    description: Optional[str] = Field('', max_length=500, description="分类描述")
    sort_order: Optional[int] = Field(0, description="排序")
    
    @validator('slug')
    def validate_slug(cls, v):
        """Validate slug format."""
        import re
        if not re.match(r'^[a-zA-Z0-9-_]+$', v):
            raise ValueError('别名只能包含字母、数字、连字符和下划线')
        return v


class CategoryUpdateSchema(BaseModel):
    """Category update schema."""
    name: Optional[str] = Field(None, min_length=1, max_length=100, description="分类名称")
    slug: Optional[str] = Field(None, min_length=1, max_length=100, description="分类别名")
    description: Optional[str] = Field(None, max_length=500, description="分类描述")
    sort_order: Optional[int] = Field(None, description="排序")
    
    @validator('slug')
    def validate_slug(cls, v):
        """Validate slug format."""
        if v is not None:
            import re
            if not re.match(r'^[a-zA-Z0-9-_]+$', v):
                raise ValueError('别名只能包含字母、数字、连字符和下划线')
        return v





class ArticleClaimSchema(BaseModel):
    """Article claim schema."""
    article_id: int = Field(..., description="文章ID")
    
    class Config:
        from_attributes = True


class ArticleClaimResponseSchema(BaseModel):
    """Article claim response schema."""
    id: int
    article_id: int
    user_id: int
    claimed_at: datetime
    
    class Config:
        from_attributes = True


class ArticleDownloadSchema(BaseModel):
    """Article download schema."""
    article_id: int = Field(..., description="文章ID")
    
    class Config:
        from_attributes = True


class ArticleDownloadResponseSchema(BaseModel):
    """Article download response schema."""
    id: int
    article_id: int
    user_id: int
    downloaded_at: datetime
    
    class Config:
        from_attributes = True