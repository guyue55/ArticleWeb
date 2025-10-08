"""
用户认证中间件
提供全局的用户登录验证功能
"""

from django.http import JsonResponse
from django.shortcuts import redirect
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.conf import settings
from apps.users.config import UserConfig
import logging

logger = logging.getLogger(__name__)
User = get_user_model()


class AuthenticationMiddleware:
    """
    用户认证中间件
    处理用户登录状态检查和临时用户创建
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        
        # 需要登录的页面路径
        self.protected_pages = [
            '/profile/',
            '/user/',
            '/settings/',
        ]
        
        # 需要登录的API路径
        self.protected_apis = [
            '/api/users/profile/',
            '/api/users/stats/',
            '/api/users/logout/',
            '/api/users/update/',
        ]
        
        # 需要登录的文章操作API
        self.protected_article_operations = [
            '/claim',
            '/download',
            '/claim-status',
        ]
        
        # 不需要认证的路径
        self.public_paths = [
            '/articles/',
            '/auth/login/',
            '/auth/register/',
            '/static/',
            '/media/',
            '/api/v1/users/login/',
            '/api/v1/users/register/',
            '/api/v1/users/csrf/',
            '/api/users/login/',
            '/api/users/register/',
            '/api/users/csrf/',
        ]
        
        # 精确匹配的公共路径
        self.exact_public_paths = [
            '/',
        ]

    def __call__(self, request):
        # 处理请求前的认证逻辑
        early_response = self.process_request(request)
        if early_response:
            return early_response
        
        # 获取响应
        response = self.get_response(request)
        
        return response

    def process_request(self, request):
        """处理请求，根据API验证设置决定是否需要认证"""
        
        # 检查API验证是否启用
        if not UserConfig.is_api_authentication_enabled():
            # API验证关闭时，允许所有请求通过
            return None
        
        # API验证开启时的逻辑
        path = request.path_info
        method = request.method
        
        # 检查是否为公共路径
        if self.is_public_path(path):
            # 公共路径允许访问
            return None
        
        # 检查是否需要认证
        if UserConfig.should_require_authentication(path, method):
            if not request.user.is_authenticated:
                logger.warning(f"未认证用户尝试访问受保护资源: {method} {path}")
                # 返回认证错误响应
                if path.startswith('/api/'):
                    return JsonResponse({
                        'error': '认证失败',
                        'message': '访问此资源需要登录',
                        'code': 'AUTHENTICATION_REQUIRED'
                    }, status=401)
                else:
                    # 对于页面请求，重定向到登录页面
                    return redirect(reverse('login'))
        
        return None

    def is_public_path(self, path):
        """
        检查是否为公共路径
        """
        # 检查精确匹配的公共路径
        if path in self.exact_public_paths:
            return True
        
        # 检查前缀匹配的公共路径
        for public_path in self.public_paths:
            if path.startswith(public_path):
                return True
        
        return False

    def is_protected_page(self, path):
        """
        检查是否为需要登录的页面
        """
        for protected_page in self.protected_pages:
            if path.startswith(protected_page):
                return True
        return False

    def is_protected_api(self, path, method='GET'):
        """
        检查是否为需要登录的API
        """
        # 检查常规需要登录的API
        for protected_api in self.protected_apis:
            if path.startswith(protected_api):
                return True
        
        # 对于文章API的特殊处理
        if path.startswith('/api/articles/'):
            # GET请求允许访问（查看文章列表、详情等）
            if method == 'GET':
                # 但是某些GET请求需要登录（如查看领取状态）
                for operation in self.protected_article_operations:
                    if operation in path:
                        return True
                return False
            
            # POST请求需要检查是否为需要登录的操作
            if method == 'POST':
                for operation in self.protected_article_operations:
                    if operation in path:
                        return True
                return False
        
        return False


class UserSessionMiddleware:
    """
    用户会话中间件
    处理用户会话管理和状态维护
    """
    
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # 处理请求前的会话逻辑
        self.process_request(request)
        
        # 获取响应
        response = self.get_response(request)
        
        # 处理响应后的会话逻辑
        self.process_response(request, response)
        
        return response

    def process_request(self, request):
        """
        处理请求前的会话逻辑
        """
        # 记录用户访问信息
        if hasattr(request, 'user') and request.user.is_authenticated:
            # 更新最后访问时间
            try:
                user = request.user
                if hasattr(user, 'last_login_ip'):
                    user.last_login_ip = self.get_client_ip(request)
                    user.save(update_fields=['last_login_ip'])
            except Exception as e:
                logger.warning(f"更新用户访问信息失败: {e}")

    def process_response(self, request, response):
        """
        处理响应后的会话逻辑
        """
        # 这里可以添加响应后的处理逻辑
        pass

    def get_client_ip(self, request):
        """
        获取客户端IP地址
        """
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


class APIResponseMiddleware:
    """
    API响应中间件
    统一处理API响应格式和错误处理
    """
    
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        
        # 处理API响应
        if request.path.startswith('/api/'):
            response = self.process_api_response(request, response)
        
        return response

    def process_api_response(self, request, response):
        """
        处理API响应
        """
        # 添加CORS头
        response['Access-Control-Allow-Origin'] = '*'
        response['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
        response['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
        
        return response