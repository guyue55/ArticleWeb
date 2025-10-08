"""通用缓存工具，用于提高API性能。"""

import json
import hashlib
from typing import Any, Optional, Callable
from functools import wraps
from django.core.cache import cache
from django.conf import settings


class CacheManager:
    """缓存管理器。"""
    
    # 默认缓存时间（秒）
    DEFAULT_TIMEOUT = 300  # 5分钟
    
    # 缓存键前缀
    CACHE_PREFIX = "api_cache"
    
    @classmethod
    def generate_cache_key(cls, *args, **kwargs) -> str:
        """生成缓存键。
        
        Args:
            *args: 位置参数
            **kwargs: 关键字参数
            
        Returns:
            str: 缓存键
        """
        # 创建一个包含所有参数的字符串
        key_data = {
            'args': args,
            'kwargs': sorted(kwargs.items())
        }
        key_string = json.dumps(key_data, sort_keys=True, default=str)
        
        # 使用MD5哈希生成固定长度的键
        key_hash = hashlib.md5(key_string.encode()).hexdigest()
        
        return f"{cls.CACHE_PREFIX}:{key_hash}"
    
    @classmethod
    def get(cls, key: str) -> Any:
        """获取缓存数据。
        
        Args:
            key: 缓存键
            
        Returns:
            Any: 缓存的数据，如果不存在则返回None
        """
        return cache.get(key)
    
    @classmethod
    def set(cls, key: str, value: Any, timeout: Optional[int] = None) -> None:
        """设置缓存数据。
        
        Args:
            key: 缓存键
            value: 要缓存的数据
            timeout: 缓存超时时间（秒），默认使用DEFAULT_TIMEOUT
        """
        if timeout is None:
            timeout = cls.DEFAULT_TIMEOUT
        cache.set(key, value, timeout)
    
    @classmethod
    def delete(cls, key: str) -> None:
        """删除缓存数据。
        
        Args:
            key: 缓存键
        """
        cache.delete(key)
    
    @classmethod
    def delete_pattern(cls, pattern: str) -> None:
        """删除匹配模式的缓存数据。
        
        Args:
            pattern: 缓存键模式
        """
        # 注意：这个方法需要Redis后端支持
        if hasattr(cache, 'delete_pattern'):
            cache.delete_pattern(f"{cls.CACHE_PREFIX}:{pattern}*")
    
    @classmethod
    def clear_all(cls) -> None:
        """清除所有API缓存。"""
        cls.delete_pattern("")


def cache_result(timeout: Optional[int] = None, key_prefix: str = ""):
    """缓存函数结果的装饰器。
    
    Args:
        timeout: 缓存超时时间（秒）
        key_prefix: 缓存键前缀
        
    Returns:
        装饰器函数
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # 生成缓存键
            cache_key_data = {
                'func_name': func.__name__,
                'key_prefix': key_prefix,
                'args': args,
                'kwargs': kwargs
            }
            cache_key = CacheManager.generate_cache_key(**cache_key_data)
            
            # 尝试从缓存获取结果
            cached_result = CacheManager.get(cache_key)
            if cached_result is not None:
                return cached_result
            
            # 执行函数并缓存结果
            result = func(*args, **kwargs)
            CacheManager.set(cache_key, result, timeout)
            
            return result
        return wrapper
    return decorator


class ArticleCacheManager(CacheManager):
    """文章相关缓存管理器。"""
    
    CACHE_PREFIX = "article_cache"
    
    @classmethod
    def get_article_detail_key(cls, article_id: int) -> str:
        """获取文章详情缓存键。"""
        return f"{cls.CACHE_PREFIX}:detail:{article_id}"
    
    @classmethod
    def get_article_list_key(cls, **params) -> str:
        """获取文章列表缓存键。"""
        return cls.generate_cache_key("list", **params)
    
    @classmethod
    def invalidate_article_cache(cls, article_id: int) -> None:
        """使文章相关缓存失效。"""
        # 删除文章详情缓存
        cls.delete(cls.get_article_detail_key(article_id))
        
        # 删除文章列表缓存
        cls.delete_pattern("list")
    
    @classmethod
    def get_category_list_key(cls) -> str:
        """获取分类列表缓存键。"""
        return f"{cls.CACHE_PREFIX}:categories"
    
    


class UserCacheManager(CacheManager):
    """用户相关缓存管理器。"""
    
    CACHE_PREFIX = "user_cache"
    
    @classmethod
    def get_user_profile_key(cls, user_id: int) -> str:
        """获取用户资料缓存键。"""
        return f"{cls.CACHE_PREFIX}:profile:{user_id}"
    
    @classmethod
    def get_user_list_key(cls, **params) -> str:
        """获取用户列表缓存键。"""
        return cls.generate_cache_key("list", **params)
    
    @classmethod
    def invalidate_user_cache(cls, user_id: int) -> None:
        """使用户相关缓存失效。"""
        # 删除用户资料缓存
        cls.delete(cls.get_user_profile_key(user_id))
        
        # 删除用户列表缓存
        cls.delete_pattern("list")


# 缓存装饰器的便捷函数
def cache_article_detail(timeout: int = 600):  # 10分钟
    """缓存文章详情的装饰器。"""
    return cache_result(timeout=timeout, key_prefix="article_detail")


def cache_article_list(timeout: int = 300):  # 5分钟
    """缓存文章列表的装饰器。"""
    return cache_result(timeout=timeout, key_prefix="article_list")


def cache_user_profile(timeout: int = 600):  # 10分钟
    """缓存用户资料的装饰器。"""
    return cache_result(timeout=timeout, key_prefix="user_profile")


def cache_static_data(timeout: int = 3600):  # 1小时
    """缓存静态数据（如分类、标签）的装饰器。"""
    return cache_result(timeout=timeout, key_prefix="static_data")