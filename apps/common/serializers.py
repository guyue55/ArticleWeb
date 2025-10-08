"""通用序列化器，用于规范化API请求和响应数据。"""

from typing import List, Optional, Any, Dict
from pydantic import BaseModel, Field
from datetime import datetime


class BaseSerializer(BaseModel):
    """基础序列化器类。"""
    
    class Config:
        from_attributes = True
        arbitrary_types_allowed = True


class UserSerializer(BaseSerializer):
    """用户序列化器。"""
    id: int
    username: str
    email: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None


class CategorySerializer(BaseSerializer):
    """分类序列化器。"""
    id: int
    name: str
    slug: str
    description: Optional[str] = None





class ArticleListSerializer(BaseSerializer):
    """文章列表序列化器。"""
    id: int
    title: str
    slug: str
    summary: Optional[str] = None
    author: UserSerializer
    category: CategorySerializer
    featured_image: Optional[str] = None
    status: int
    is_featured: bool = False
    is_top: bool = False
    view_count: int = 0
    download_count: int = 0
    publish_time: Optional[datetime] = None
    create_time: datetime
    update_time: Optional[datetime] = None


class ArticleDetailSerializer(ArticleListSerializer):
    """文章详情序列化器。"""
    content: str





class UserProfileSerializer(BaseSerializer):
    """用户资料序列化器。"""
    id: int
    username: str
    email: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone: Optional[str] = None
    avatar: Optional[str] = None
    bio: Optional[str] = None
    birth_date: Optional[datetime] = None
    location: Optional[str] = None
    website: Optional[str] = None
    is_active: bool = True
    is_verified: bool = False
    create_time: datetime
    update_time: Optional[datetime] = None


class SerializerMixin:
    """序列化器混入类，提供通用的序列化方法。"""
    
    @classmethod
    def serialize_object(cls, obj, serializer_class: BaseSerializer) -> Dict[str, Any]:
        """序列化单个对象。"""
        if obj is None:
            return None
        return serializer_class.model_validate(obj).model_dump()
    
    @classmethod
    def serialize_queryset(cls, queryset, serializer_class: BaseSerializer) -> List[Dict[str, Any]]:
        """序列化查询集。"""
        return [serializer_class.model_validate(obj).model_dump() for obj in queryset]
    
    @classmethod
    def serialize_article_list(cls, articles) -> List[Dict[str, Any]]:
        """序列化文章列表。"""
        return cls.serialize_queryset(articles, ArticleListSerializer)
    
    @classmethod
    def serialize_article_detail(cls, article) -> Dict[str, Any]:
        """序列化文章详情。"""
        return cls.serialize_object(article, ArticleDetailSerializer)
    
    @classmethod
    def serialize_user_profile(cls, user) -> Dict[str, Any]:
        """序列化用户资料。"""
        return cls.serialize_object(user, UserProfileSerializer)