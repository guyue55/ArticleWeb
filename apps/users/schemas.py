"""Pydantic schemas for user API."""

from datetime import datetime, date
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, EmailStr, Field, validator


class UserCreateSchema(BaseModel):
    """Schema for user creation."""
    
    username: str = Field(..., min_length=3, max_length=150, description="用户名")
    email: EmailStr = Field(..., description="邮箱地址")
    password: str = Field(..., min_length=8, description="密码")
    first_name: Optional[str] = Field(None, max_length=30, description="名")
    last_name: Optional[str] = Field(None, max_length=30, description="姓")
    
    @validator('username')
    def validate_username(cls, v):
        """Validate username format."""
        if not v.replace('_', '').replace('-', '').isalnum():
            raise ValueError('用户名只能包含字母、数字、下划线和连字符')
        return v
    
    @validator('password')
    def validate_password(cls, v):
        """Validate password strength."""
        if len(v) < 8:
            raise ValueError('密码长度至少8位')
        if not any(c.isdigit() for c in v):
            raise ValueError('密码必须包含至少一个数字')
        if not any(c.isalpha() for c in v):
            raise ValueError('密码必须包含至少一个字母')
        return v


class UserUpdateSchema(BaseModel):
    """Schema for user update."""
    
    first_name: Optional[str] = Field(None, max_length=30, description="名")
    last_name: Optional[str] = Field(None, max_length=30, description="姓")
    phone: Optional[str] = Field(None, description="手机号")
    bio: Optional[str] = Field(None, max_length=500, description="个人简介")
    birth_date: Optional[date] = Field(None, description="出生日期")
    location: Optional[str] = Field(None, max_length=100, description="所在地")
    website: Optional[str] = Field(None, description="个人网站")


class UserProfileSchema(BaseModel):
    """Schema for user profile."""
    
    gender: Optional[str] = Field(None, description="性别")
    occupation: Optional[str] = Field(None, max_length=100, description="职业")
    education: Optional[str] = Field(None, max_length=100, description="教育背景")
    interests: Optional[str] = Field(None, description="兴趣爱好")
    social_links: Optional[Dict[str, str]] = Field(None, description="社交链接")
    preferences: Optional[Dict[str, Any]] = Field(None, description="用户偏好")
    
    class Config:
        from_attributes = True


class UserResponseSchema(BaseModel):
    """Schema for user response."""
    
    id: int = Field(..., description="用户ID")
    username: str = Field(..., description="用户名")
    email: str = Field(..., description="邮箱地址")
    first_name: Optional[str] = Field(None, description="名")
    last_name: Optional[str] = Field(None, description="姓")
    phone: Optional[str] = Field(None, description="手机号")
    bio: Optional[str] = Field(None, description="个人简介")
    birth_date: Optional[date] = Field(None, description="出生日期")
    location: Optional[str] = Field(None, description="所在地")
    website: Optional[str] = Field(None, description="个人网站")
    is_verified: bool = Field(..., description="是否已验证")
    is_active: bool = Field(..., description="是否激活")
    date_joined: datetime = Field(..., description="注册时间")
    last_login: Optional[datetime] = Field(None, description="最后登录时间")
    avatar_url: Optional[str] = Field(None, description="头像URL")
    full_name: str = Field(..., description="全名")
    profile: Optional[UserProfileSchema] = Field(None, description="用户资料")
    
    @validator('avatar_url', pre=True, always=True)
    def get_avatar_url(cls, v, values):
        """Get avatar URL from user object."""
        # This will be handled by the serialization logic
        return v
    
    @validator('full_name', pre=True, always=True)
    def get_full_name(cls, v, values):
        """Get full name from user object."""
        # This will be handled by the serialization logic
        return v
    
    class Config:
        from_attributes = True


class LoginSchema(BaseModel):
    """Schema for user login."""
    
    email: EmailStr = Field(..., description="邮箱地址")
    password: str = Field(..., description="密码")


class LoginResponseSchema(BaseModel):
    """Schema for login response."""
    
    user: UserResponseSchema = Field(..., description="用户信息")
    token: str = Field(..., description="访问令牌")
    token_type: str = Field(..., description="令牌类型")


class PaginationSchema(BaseModel):
    """Schema for pagination information."""
    
    current_page: int = Field(..., description="当前页码")
    total_pages: int = Field(..., description="总页数")
    total_items: int = Field(..., description="总条目数")
    page_size: int = Field(..., description="每页条目数")
    has_next: bool = Field(..., description="是否有下一页")
    has_previous: bool = Field(..., description="是否有上一页")


class UserListResponseSchema(BaseModel):
    """Schema for user list response."""
    
    users: List[UserResponseSchema] = Field(..., description="用户列表")
    pagination: PaginationSchema = Field(..., description="分页信息")


class PasswordChangeSchema(BaseModel):
    """Schema for password change."""
    
    old_password: str = Field(..., description="旧密码")
    new_password: str = Field(..., min_length=8, description="新密码")
    confirm_password: str = Field(..., description="确认新密码")
    
    @validator('confirm_password')
    def passwords_match(cls, v, values):
        """Validate that passwords match."""
        if 'new_password' in values and v != values['new_password']:
            raise ValueError('两次输入的密码不一致')
        return v
    
    @validator('new_password')
    def validate_new_password(cls, v):
        """Validate new password strength."""
        if len(v) < 8:
            raise ValueError('密码长度至少8位')
        if not any(c.isdigit() for c in v):
            raise ValueError('密码必须包含至少一个数字')
        if not any(c.isalpha() for c in v):
            raise ValueError('密码必须包含至少一个字母')
        return v


class PasswordResetRequestSchema(BaseModel):
    """Schema for password reset request."""
    
    email: EmailStr = Field(..., description="邮箱地址")


class PasswordResetSchema(BaseModel):
    """Schema for password reset."""
    
    token: str = Field(..., description="重置令牌")
    new_password: str = Field(..., min_length=8, description="新密码")
    confirm_password: str = Field(..., description="确认新密码")
    
    @validator('confirm_password')
    def passwords_match(cls, v, values):
        """Validate that passwords match."""
        if 'new_password' in values and v != values['new_password']:
            raise ValueError('两次输入的密码不一致')
        return v
    
    @validator('new_password')
    def validate_new_password(cls, v):
        """Validate new password strength."""
        if len(v) < 8:
            raise ValueError('密码长度至少8位')
        if not any(c.isdigit() for c in v):
            raise ValueError('密码必须包含至少一个数字')
        if not any(c.isalpha() for c in v):
            raise ValueError('密码必须包含至少一个字母')
        return v