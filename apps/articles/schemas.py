"""Article schemas for API serialization using Pydantic."""

from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field, validator, ConfigDict

from apps.users.schemas import UserResponseSchema


class CategoryResponseSchema(BaseModel):
    """Category response schema."""
    id: int
    name: str
    slug: str
    description: str = ''
    sort_order: int = 0
    
    model_config = ConfigDict(from_attributes=True)





class ArticleCreateSchema(BaseModel):
    """Article creation schema."""
    title: str = Field(..., min_length=1, max_length=200, description="文章标题")
    slug: str = Field(..., min_length=1, max_length=200, description="文章别名")
    summary: Optional[str] = Field(None, max_length=500, description="文章摘要")
    content: str = Field(..., min_length=1, description="文章内容")
    category_id: str = Field(..., description="分类ID或UUID")
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
    
    model_config = ConfigDict(from_attributes=True)


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
    
    model_config = ConfigDict(from_attributes=True)


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
    
    model_config = ConfigDict(from_attributes=True)


class ArticleClaimResponseSchema(BaseModel):
    """Article claim response schema."""
    id: int
    article_id: int
    user_id: int
    claimed_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class ArticleDownloadSchema(BaseModel):
    """Article download schema."""
    article_id: int = Field(..., description="文章ID")
    
    model_config = ConfigDict(from_attributes=True)


class ArticleDownloadResponseSchema(BaseModel):
    """Article download response schema."""
    id: int
    article_id: int
    user_id: int
    downloaded_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


# --- AI Generation Schemas ---

class AIModelSchema(BaseModel):
    """AI 具体模型 Schema"""
    id: int
    provider_id: int
    name: str
    display_name: str
    description: str
    is_available: bool
    
    model_config = ConfigDict(
        from_attributes=True,
        protected_namespaces=()
    )


class AIProviderSchema(BaseModel):
    """AI供应商 Schema"""
    id: int
    name: str
    api_base: str
    is_active: bool
    config: dict
    is_openapi: bool
    last_scanned_at: Optional[datetime] = None
    create_time: datetime
    
    model_config = ConfigDict(from_attributes=True)


class SystemConfigSchema(BaseModel):
    """系统配置 Schema"""
    id: int
    key: str
    value: str
    description: str
    is_secret: bool
    
    model_config = ConfigDict(from_attributes=True)


class SystemConfigCreateSchema(BaseModel):
    """创建系统配置 Schema"""
    key: str = Field(..., max_length=128)
    value: str
    description: Optional[str] = ""
    is_secret: Optional[bool] = False


class AIProviderCreateSchema(BaseModel):
    """创建 AI 供应商 Schema"""
    name: str = Field(..., max_length=64)
    api_base: str = Field(..., max_length=255)
    api_key: str = Field(..., max_length=255)
    config: Optional[dict] = Field(default_factory=dict)


class AIProviderUpdateSchema(BaseModel):
    """更新 AI 供应商 Schema"""
    name: Optional[str] = Field(None, max_length=64)
    api_base: Optional[str] = Field(None, max_length=255)
    api_key: Optional[str] = Field(None, max_length=255)
    is_active: Optional[bool] = None
    config: Optional[dict] = None


class PromptTemplateSchema(BaseModel):
    """提示词模板 Schema"""
    id: int
    title: str
    category_uuid: str
    content: str
    variables: list
    description: str
    create_time: datetime
    
    model_config = ConfigDict(from_attributes=True)


class PromptTemplateCreateSchema(BaseModel):
    """创建提示词模板 Schema"""
    title: str = Field(..., max_length=128)
    category_uuid: str
    content: str
    variables: Optional[list] = Field(default_factory=list)
    description: Optional[str] = ""


class PromptTemplateUpdateSchema(BaseModel):
    """更新提示词模板 Schema"""
    title: Optional[str] = Field(None, max_length=128)
    category_uuid: Optional[str] = None
    content: Optional[str] = None
    variables: Optional[list] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None


class HotTrendSchema(BaseModel):
    """热门选题 Schema"""
    id: int
    topic: str
    source_urls: list
    summary: str
    category_uuid: str
    discovery_time: datetime
    
    model_config = ConfigDict(from_attributes=True)


class GenerationHistorySchema(BaseModel):
    """生成记录 Schema"""
    id: int
    user_uuid: str
    prompt: str
    result: str
    sources: list
    status: str
    error_message: str
    create_time: datetime
    
    model_config = ConfigDict(from_attributes=True)


class AIArticleGenerateSchema(BaseModel):
    """AI 文章生成请求 Schema"""
    template_id: int = Field(..., description="使用的提示词模板ID")
    provider_id: int = Field(..., description="使用的AI供应商ID")
    model_name: str = Field(..., description="使用的模型名称，如 ernie-bot-4")
    inputs: dict = Field(..., description="模板变量输入值")
    save_to_article: bool = Field(False, description="生成后是否直接存入文章表")
    
    model_config = ConfigDict(protected_namespaces=())


class AIImageGenerateSchema(BaseModel):
    """AI 图片生成请求 Schema"""
    provider_id: int = Field(..., description="使用的AI供应商ID")
    model_name: str = Field(..., description="使用的模型名称，如 dall-e-3")
    prompt: Optional[str] = Field(None, description="图片生成提示词，如果不提供则根据文章内容生成")
    article_content: Optional[str] = Field(None, description="文章内容，用于自动生成提示词")
    article_id: Optional[int] = Field(None, description="文章ID，如果提供则自动关联到该文章")
    size: Optional[str] = Field("1024x1024", description="图片尺寸")
    quality: Optional[str] = Field("standard", description="图片质量")
    
    model_config = ConfigDict(protected_namespaces=())