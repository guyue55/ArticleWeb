"""
用户模块配置管理
"""
import os
from django.conf import settings


class UserConfig:
    """用户模块配置类"""
    
    # API验证配置
    @staticmethod
    def is_api_authentication_enabled():
        """检查API验证是否启用"""
        return getattr(settings, 'ENABLE_API_AUTHENTICATION', True)
    
    # 用户认证配置
    # 移除了匿名用户和临时用户相关配置，现在只支持真实用户认证
    
    # 受保护的路径配置
    PROTECTED_PATHS = [
        '/admin/',
        '/api/admin/',
        '/api/users/profile/',
        '/api/users/settings/',
    ]
    
    # 受保护的API端点配置 - 只保护需要认证的特定操作
    PROTECTED_API_ENDPOINTS = [
        # 用户相关API - 只保护需要认证的操作
        '/api/v1/users/profile',
        '/api/v1/users/settings',
        '/api/v1/users/logout',
        '/api/v1/users/update',
        '/api/users/profile/',
        '/api/users/settings/',
        '/api/users/logout/',
        '/api/users/update/',
        
        # 文章管理操作 - 需要认证
        '/api/v1/articles/create',
        '/api/v1/articles/update',
        '/api/v1/articles/delete',
        

    ]
    
    # 需要认证的HTTP方法和路径组合
    PROTECTED_OPERATIONS = [
        # 文章相关的写操作
        ('POST', '/api/v1/articles/'),      # 创建文章
        ('PUT', '/api/v1/articles/'),       # 更新文章
        ('DELETE', '/api/v1/articles/'),    # 删除文章
        ('POST', '/api/v1/articles/*/claim'),    # 领取文章
        ('POST', '/api/v1/articles/*/download'), # 下载文章
    ]
    

    
    @classmethod
    def is_protected_path(cls, path):
        """检查路径是否受保护"""
        return any(path.startswith(protected) for protected in cls.PROTECTED_PATHS)
    
    @classmethod
    def is_protected_api(cls, path):
        """检查API端点是否受保护"""
        return any(path.startswith(protected) for protected in cls.PROTECTED_API_ENDPOINTS)
    
    @classmethod
    def is_protected_operation(cls, method, path):
        """检查特定HTTP方法和路径组合是否需要认证"""
        import re
        for protected_method, protected_path in cls.PROTECTED_OPERATIONS:
            if method.upper() == protected_method.upper():
                # 将通配符路径转换为正则表达式
                pattern = protected_path.replace('*', r'[^/]+')
                if re.match(f"^{pattern}", path):
                    return True
        return False
    
    @classmethod
    def should_require_authentication(cls, path, method='GET'):
        """判断路径和方法是否需要认证"""
        if not cls.is_api_authentication_enabled():
            return False
        
        # 检查受保护的页面路径
        if cls.is_protected_path(path):
            return True
            
        # 检查受保护的API端点
        if cls.is_protected_api(path):
            return True
            
        # 检查受保护的操作（方法+路径组合）
        if cls.is_protected_operation(method, path):
            return True
            
        return False


# 配置导出
# 移除了匿名用户相关的常量导出