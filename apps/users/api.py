"""User API endpoints using Django Ninja."""

from typing import Optional
from django.contrib.auth import authenticate, logout
from django.shortcuts import get_object_or_404
from django.utils import timezone
from ninja import Router
from ninja.security import HttpBearer

from apps.articles.models import ArticleClaim, ArticleDownload
from apps.common.responses import APIResponse, ErrorCodes, ErrorMessages
from apps.common.serializers import SerializerMixin
from .models import User
from .schemas import (
    UserCreateSchema,
    UserUpdateSchema,
    LoginSchema
)

router = Router(tags=["Users"])


class AuthBearer(HttpBearer):
    """Custom authentication bearer."""
    
    def authenticate(self, request, token):
        # TODO: Implement JWT token validation
        # For now, return a mock user
        try:
            # This is a placeholder - implement actual JWT validation
            return User.objects.get(id=1)
        except User.DoesNotExist:
            return None


auth = AuthBearer()


@router.post("", response=dict)
def register_user(request, data: UserCreateSchema):
    """Register a new user."""
    try:
        # Check if username already exists
        if User.objects.filter(username=data.username).exists():
            return APIResponse.error(
                code=ErrorCodes.BAD_REQUEST,
                message="用户名已存在"
            )
        
        # Check if email already exists
        if User.objects.filter(email=data.email).exists():
            return APIResponse.error(
                code=ErrorCodes.BAD_REQUEST,
                message="邮箱已存在"
            )
        
        # Create user
        user = User.objects.create_user(
            username=data.username,
            email=data.email,
            password=data.password,
            first_name=data.first_name or '',
            last_name=data.last_name or ''
        )
        
        # 序列化用户数据
        serialized_user = SerializerMixin.serialize_user_profile(user)
        
        return APIResponse.success(data=serialized_user)
    
    except Exception as e:
        return APIResponse.error(
            code=ErrorCodes.INTERNAL_SERVER_ERROR,
            message="注册失败"
        )


@router.post("/login", response=dict)
def login_user(request, data: LoginSchema):
    """User login."""
    try:
        user = authenticate(
            request,
            username=data.email,
            password=data.password
        )
        
        if not user:
            return APIResponse.error(
                code=ErrorCodes.UNAUTHORIZED,
                message="邮箱或密码错误"
            )
        
        if not user.is_active:
            return APIResponse.error(
                code=ErrorCodes.UNAUTHORIZED,
                message="账户已被禁用"
            )
        
        # TODO: Generate JWT token
        token = "mock_jwt_token_" + str(user.id)
        
        # 序列化用户数据
        from apps.common.serializers import UserSerializer
        serialized_user = UserSerializer.model_validate(user).model_dump()
        
        return APIResponse.success(
            data={
                "user": serialized_user,
                "token": token,
                "expires_in": 3600
            }
        )
    
    except Exception as e:
        return APIResponse.error(
            code=ErrorCodes.INTERNAL_SERVER_ERROR,
            message="登录失败"
        )


@router.get("/profile", response=dict, auth=auth)
def get_user_profile(request):
    """Get current user profile."""
    try:
        user = request.auth
        
        # 序列化用户资料数据
        serialized_user = SerializerMixin.serialize_user_profile(user)
        
        return APIResponse.success(data=serialized_user)
    
    except Exception as e:
        return APIResponse.error(
            code=ErrorCodes.INTERNAL_SERVER_ERROR,
            message="获取用户资料失败"
        )


@router.put("/profile", response=dict, auth=auth)
def update_user_profile(request, data: UserUpdateSchema):
    """Update current user profile."""
    try:
        user = request.auth
        
        # Update user fields
        for field, value in data.dict(exclude_unset=True).items():
            if hasattr(user, field) and value is not None:
                setattr(user, field, value)
        
        user.save()
        
        # 序列化用户资料数据
        serialized_user = SerializerMixin.serialize_user_profile(user)
        
        return APIResponse.success(data=serialized_user)
    
    except Exception as e:
        return APIResponse.error(
            code=ErrorCodes.INTERNAL_SERVER_ERROR,
            message="更新用户资料失败"
        )


@router.get("", response=dict)
def list_users(
    request,
    limit: int = 20,
    offset: int = 0,
    search: Optional[str] = None,
    is_active: Optional[bool] = None,
    sort: Optional[str] = None
):
    """List users with pagination and filtering."""
    try:
        from django.db.models import Q
        queryset = User.objects.all()
        
        # Apply filters
        if search:
            queryset = queryset.filter(
                Q(username__icontains=search) |
                Q(email__icontains=search) |
                Q(first_name__icontains=search) |
                Q(last_name__icontains=search)
            )
        
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active)
        
        # Apply sorting
        if sort:
            sort_fields = sort.split(';')
            fields = sort_fields[0].split(',')
            direction = sort_fields[1] if len(sort_fields) > 1 else 'asc'
            
            order_fields = []
            for field in fields:
                if direction == 'desc':
                    order_fields.append(f'-{field}')
                else:
                    order_fields.append(field)
            queryset = queryset.order_by(*order_fields)
        
        # Get total count
        total = queryset.count()
        
        # Apply pagination
        users = list(queryset[offset:offset + limit])
        
        # 序列化用户列表数据
        from apps.common.serializers import UserProfileSerializer
        serialized_users = SerializerMixin.serialize_queryset(users, UserProfileSerializer)
        
        return APIResponse.paginated(
            items=serialized_users,
            total=total,
            limit=limit,
            offset=offset
        )
    
    except Exception as e:
        return APIResponse.error(
            code=ErrorCodes.INTERNAL_SERVER_ERROR,
            message="获取用户列表失败"
        )


@router.get("/{user_id}", response=dict)
def get_user_by_id(request, user_id: int):
    """Get user by ID."""
    try:
        user = get_object_or_404(User, id=user_id, is_active=True)
        
        # 序列化用户数据
        serialized_user = SerializerMixin.serialize_user_profile(user)
        
        return APIResponse.success(data=serialized_user)
    
    except Exception as e:
        return APIResponse.error(
            code=ErrorCodes.NOT_FOUND,
            message=ErrorMessages.NOT_FOUND
        )


@router.put("/{user_id}", response=dict)
def update_user(request, user_id: int, user_data: UserUpdateSchema):
    """Update user information."""
    try:
        user = get_object_or_404(User, id=user_id)
        
        # Check if user can update this profile
        if not request.user.is_authenticated or (request.user.id != user_id and not request.user.is_staff):
            return APIResponse.error(
                code=ErrorCodes.FORBIDDEN,
                message="无权限修改此用户信息"
            )
        
        # Update user fields
        for field, value in user_data.dict(exclude_unset=True).items():
            if hasattr(user, field):
                setattr(user, field, value)
        
        user.save()
        
        # 序列化用户数据
        serialized_user = SerializerMixin.serialize_user_profile(user)
        
        return APIResponse.success(
            message="用户信息更新成功",
            data=serialized_user
        )
    
    except Exception as e:
        return APIResponse.error(
            code=ErrorCodes.INTERNAL_SERVER_ERROR,
            message="更新用户信息失败"
        )


@router.delete("/{user_id}", response=dict)
def delete_user(request, user_id: int):
    """Delete user (soft delete)."""
    try:
        user = get_object_or_404(User, id=user_id)
        
        # Check if user can delete this profile
        if not request.user.is_authenticated or (request.user.id != user_id and not request.user.is_staff):
            return APIResponse.error(
                code=ErrorCodes.FORBIDDEN,
                message="无权限删除此用户"
            )
        
        # Soft delete
        user.is_active = False
        user.save()
        
        # 序列化用户数据
        serialized_user = SerializerMixin.serialize_user_profile(user)
        
        return APIResponse.success(
            message="用户删除成功",
            data=serialized_user
        )
    
    except Exception as e:
        return APIResponse.error(
            code=ErrorCodes.INTERNAL_SERVER_ERROR,
            message="删除用户失败"
        )


@router.post("/logout", response=dict, auth=auth)
def logout_user(request):
    """User logout."""
    try:
        # Clear session if using session authentication
        logout(request)
        
        return APIResponse.success(
            message="退出登录成功"
        )
    
    except Exception as e:
        return APIResponse.error(
            code=ErrorCodes.INTERNAL_SERVER_ERROR,
            message="退出登录失败"
        )


@router.get("/profile/stats", response=dict, auth=auth)
def get_user_stats(request):
    """Get current user statistics."""
    try:
        user = request.auth
        # Get user statistics        
        claim_count = ArticleClaim.objects.filter(
            user_uuid=user.uuid,
            is_active=True
        ).count()
        
        download_count = ArticleDownload.objects.filter(
            user_uuid=user.uuid,
            is_active=True
        ).count()
        
        # Get recent activity (last 30 days)
        thirty_days_ago = timezone.now() - timezone.timedelta(days=30)
        
        recent_claims = ArticleClaim.objects.filter(
            user_uuid=user.uuid,
            is_active=True,
            create_time__gte=thirty_days_ago
        ).count()
        
        recent_downloads = ArticleDownload.objects.filter(
            user_uuid=user.uuid,
            is_active=True,
            create_time__gte=thirty_days_ago
        ).count()
        
        stats = {
            "total_claims": claim_count,
            "total_downloads": download_count,
            "recent_claims": recent_claims,
            "recent_downloads": recent_downloads,
            "member_since": user.date_joined.isoformat(),
            "last_login": user.last_login.isoformat() if user.last_login else None
        }
        
        return APIResponse.success(data=stats)
    
    except Exception as e:
        return APIResponse.error(
            code=ErrorCodes.INTERNAL_SERVER_ERROR,
            message="获取用户统计数据失败"
        )


# Django视图版本的接口
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.http import JsonResponse
from django.db.models import Q
import logging

logger = logging.getLogger(__name__)


@csrf_exempt
@require_http_methods(["POST"])
def logout_user_view(request):
    """
    用户退出登录
    """
    try:
        # 清除用户会话
        logout(request)
        
        return JsonResponse({
            'code': 0,
            'message': '退出登录成功',
            'data': None
        })
    
    except Exception as e:
        logger.error(f"用户退出登录失败: {e}")
        return JsonResponse({
            'code': 500,
            'message': '退出登录失败',
            'data': None
        })


@csrf_exempt
@require_http_methods(["GET"])
def get_user_stats_view(request):
    """
    获取用户统计数据
    """
    try:
        # 检查用户是否已登录
        if not request.user.is_authenticated:
            return JsonResponse({
                'code': 401,
                'message': '请先登录',
                'data': None
            })
        
        user = request.user
        
        # 获取用户统计数据
        claim_count = ArticleClaim.objects.filter(
            user_uuid=user.uuid,
            is_active=True
        ).count()
        
        download_count = ArticleDownload.objects.filter(
            user_uuid=user.uuid,
            is_active=True
        ).count()
        
        # 获取最近活动（最近30天）
        thirty_days_ago = timezone.now() - timezone.timedelta(days=30)
        
        recent_claims = ArticleClaim.objects.filter(
            user_uuid=user.uuid,
            is_active=True,
            create_time__gte=thirty_days_ago
        ).count()
        
        recent_downloads = ArticleDownload.objects.filter(
            user_uuid=user.uuid,
            is_active=True,
            create_time__gte=thirty_days_ago
        ).count()
        
        stats = {
            "claimed_count": claim_count,
            "download_count": download_count,
            "recent_claims": recent_claims,
            "recent_downloads": recent_downloads,
            "member_since": user.date_joined.isoformat() if user.date_joined else None,
            "last_login": user.last_login.isoformat() if user.last_login else None
        }
        
        return JsonResponse({
            'code': 0,
            'message': '获取用户统计数据成功',
            'data': stats
        })
    
    except Exception as e:
        logger.error(f"获取用户统计数据失败: {e}")
        return JsonResponse({
            'code': 500,
            'message': '获取用户统计数据失败',
            'data': None
        })