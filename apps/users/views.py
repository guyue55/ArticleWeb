"""
用户认证相关的Django视图API
提供登录、注册、用户资料等功能
"""

import json
import logging
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt, ensure_csrf_cookie
from django.views.decorators.http import require_http_methods
from django.http import JsonResponse
from django.utils import timezone
from django.db.models import Q
from django.middleware.csrf import get_token
from apps.users.models import User
from apps.users.utils import get_user_stats, update_user_last_activity

logger = logging.getLogger(__name__)


@ensure_csrf_cookie
@require_http_methods(["GET"])
def get_csrf_token(request):
    """
    获取CSRF token
    """
    return JsonResponse({
        'code': 0,
        'message': 'success',
        'data': {
            'csrf_token': get_token(request)
        }
    })


@csrf_exempt
@require_http_methods(["POST"])
def register_view(request):
    """
    用户注册
    """
    try:
        data = json.loads(request.body)
        
        # 验证必填字段
        required_fields = ['username', 'email', 'password']
        for field in required_fields:
            if not data.get(field):
                return JsonResponse({
                    'code': 400,
                    'message': f'{field} 不能为空',
                    'data': None
                })
        
        username = data['username']
        email = data['email']
        password = data['password']
        first_name = data.get('first_name', '')
        last_name = data.get('last_name', '')
        
        # 检查用户名是否已存在
        if User.objects.filter(username=username).exists():
            return JsonResponse({
                'code': 400,
                'message': '用户名已存在',
                'data': None
            })
        
        # 检查邮箱是否已存在
        if User.objects.filter(email=email).exists():
            return JsonResponse({
                'code': 400,
                'message': '邮箱已存在',
                'data': None
            })
        
        # 创建用户
        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name
        )
        
        # 自动登录
        login(request, user)
        
        # 更新用户活动信息
        update_user_last_activity(user, request)
        
        return JsonResponse({
            'code': 0,
            'message': '注册成功',
            'data': {
                'user_id': user.id,
                'username': user.username,
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name
            }
        })
    
    except json.JSONDecodeError:
        return JsonResponse({
            'code': 400,
            'message': '请求数据格式错误',
            'data': None
        })
    except Exception as e:
        logger.error(f"用户注册失败: {e}")
        return JsonResponse({
            'code': 500,
            'message': '注册失败，请稍后重试',
            'data': None
        })


@csrf_exempt
@require_http_methods(["POST"])
def login_view(request):
    """
    用户登录
    """
    try:
        data = json.loads(request.body)
        
        # 验证必填字段
        email = data.get('email')
        password = data.get('password')
        
        if not email or not password:
            return JsonResponse({
                'code': 400,
                'message': '邮箱和密码不能为空',
                'data': None
            })
        
        # 直接使用邮箱进行认证（因为USERNAME_FIELD = 'email'）
        user = authenticate(request, username=email, password=password)
        
        if not user:
            return JsonResponse({
                'code': 401,
                'message': '邮箱或密码错误',
                'data': None
            })
        
        if not user.is_active:
            return JsonResponse({
                'code': 401,
                'message': '账户已被禁用',
                'data': None
            })
        
        # 登录用户
        login(request, user)
        
        # 更新用户活动信息
        update_user_last_activity(user, request)
        
        return JsonResponse({
            'code': 0,
            'message': '登录成功',
            'data': {
                'user_id': user.id,
                'username': user.username,
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name
            }
        })
    
    except json.JSONDecodeError:
        return JsonResponse({
            'code': 400,
            'message': '请求数据格式错误',
            'data': None
        })
    except Exception as e:
        logger.error(f"用户登录失败: {e}")
        return JsonResponse({
            'code': 500,
            'message': '登录失败，请稍后重试',
            'data': None
        })


@csrf_exempt
@require_http_methods(["POST"])
def logout_view(request):
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
def profile_view(request):
    """
    获取用户资料
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
        
        # 构建用户资料数据
        profile_data = {
            'user_id': user.id,
            'username': user.username,
            'email': user.email,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'avatar': user.avatar.url if user.avatar else None,
            'bio': user.bio,
            'birth_date': user.birth_date.isoformat() if user.birth_date else None,
            'location': user.location,
            'website': user.website,
            'is_verified': user.is_verified,
            'date_joined': user.date_joined.isoformat() if user.date_joined else None,
            'last_login': user.last_login.isoformat() if user.last_login else None
        }
        
        return JsonResponse({
            'code': 0,
            'message': '获取用户资料成功',
            'data': profile_data
        })
    
    except Exception as e:
        logger.error(f"获取用户资料失败: {e}")
        return JsonResponse({
            'code': 500,
            'message': '获取用户资料失败',
            'data': None
        })


@csrf_exempt
@require_http_methods(["GET"])
def stats_view(request):
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
        stats = get_user_stats(user)
        
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


@csrf_exempt
@require_http_methods(["PUT"])
def update_profile_view(request):
    """
    更新用户资料
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
        data = json.loads(request.body)
        
        # 允许更新的字段
        allowed_fields = [
            'first_name', 'last_name', 'bio', 'birth_date', 
            'location', 'website'
        ]
        
        # 更新用户字段
        updated_fields = []
        for field in allowed_fields:
            if field in data:
                value = data[field]
                if hasattr(user, field):
                    setattr(user, field, value)
                    updated_fields.append(field)
        
        if updated_fields:
            user.save(update_fields=updated_fields)
        
        # 构建更新后的用户资料数据
        profile_data = {
            'user_id': user.id,
            'username': user.username,
            'email': user.email,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'avatar': user.avatar.url if user.avatar else None,
            'bio': user.bio,
            'birth_date': user.birth_date.isoformat() if user.birth_date else None,
            'location': user.location,
            'website': user.website,
            'is_verified': user.is_verified,
            'date_joined': user.date_joined.isoformat() if user.date_joined else None,
            'last_login': user.last_login.isoformat() if user.last_login else None
        }
        
        return JsonResponse({
            'code': 0,
            'message': '更新用户资料成功',
            'data': profile_data
        })
    
    except json.JSONDecodeError:
        return JsonResponse({
            'code': 400,
            'message': '请求数据格式错误',
            'data': None
        })
    except Exception as e:
        logger.error(f"更新用户资料失败: {e}")
        return JsonResponse({
            'code': 500,
            'message': '更新用户资料失败',
            'data': None
        })


@csrf_exempt
@require_http_methods(["GET"])
def check_auth_view(request):
    """
    检查用户登录状态
    """
    try:
        # 检查用户是否已登录
        if request.user.is_authenticated:
            return JsonResponse({
                'code': 0,
                'message': '用户已登录',
                'data': {
                    'is_authenticated': True,
                    'user_id': request.user.id,
                    'username': request.user.username
                }
            })
        else:
            # 未登录用户返回401状态码
            return JsonResponse({
                'code': 401,
                'message': '用户未登录',
                'data': {
                    'is_authenticated': False
                }
            }, status=401)
    
    except Exception as e:
        logger.error(f"检查用户登录状态失败: {e}")
        return JsonResponse({
            'code': 500,
            'message': '检查登录状态失败',
            'data': None
        })