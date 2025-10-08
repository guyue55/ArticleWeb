"""Performance monitoring and optimization utilities."""

import time
import functools
from typing import Any, Callable, Optional
from django.core.cache import cache
from django.db import connection
from django.conf import settings
from .logging import APILogger


class PerformanceMonitor:
    """Performance monitoring utilities."""
    
    @staticmethod
    def monitor_execution_time(threshold_ms: int = 1000, log_slow: bool = True):
        """Decorator to monitor function execution time."""
        def decorator(func: Callable) -> Callable:
            @functools.wraps(func)
            def wrapper(*args, **kwargs) -> Any:
                start_time = time.time()
                
                try:
                    result = func(*args, **kwargs)
                    return result
                finally:
                    execution_time = (time.time() - start_time) * 1000
                    
                    if log_slow and execution_time > threshold_ms:
                        APILogger.log_performance(
                            endpoint=func.__name__,
                            execution_time=execution_time,
                            status='slow'
                        )
                    
                    # Store performance metrics in cache for monitoring
                    cache_key = f"perf_metrics:{func.__name__}"
                    metrics = cache.get(cache_key, [])
                    metrics.append({
                        'timestamp': time.time(),
                        'execution_time': execution_time
                    })
                    # Keep only last 100 measurements
                    if len(metrics) > 100:
                        metrics = metrics[-100:]
                    cache.set(cache_key, metrics, 3600)  # 1 hour
            
            return wrapper
        return decorator
    
    @staticmethod
    def monitor_database_queries(func: Callable) -> Callable:
        """Decorator to monitor database query count and time."""
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            initial_queries = len(connection.queries)
            start_time = time.time()
            
            try:
                result = func(*args, **kwargs)
                return result
            finally:
                query_count = len(connection.queries) - initial_queries
                query_time = sum(float(q['time']) for q in connection.queries[initial_queries:])
                execution_time = (time.time() - start_time) * 1000
                
                # Log if too many queries or slow queries
                if query_count > 10 or query_time > 0.1:
                    APILogger.log_database_performance(
                        endpoint=func.__name__,
                        query_count=query_count,
                        query_time=query_time * 1000,  # Convert to ms
                        total_time=execution_time
                    )
        
        return wrapper
    
    @staticmethod
    def get_performance_stats(func_name: str) -> dict:
        """Get performance statistics for a function."""
        cache_key = f"perf_metrics:{func_name}"
        metrics = cache.get(cache_key, [])
        
        if not metrics:
            return {}
        
        execution_times = [m['execution_time'] for m in metrics]
        return {
            'count': len(execution_times),
            'avg_time': sum(execution_times) / len(execution_times),
            'min_time': min(execution_times),
            'max_time': max(execution_times),
            'last_24h': len([m for m in metrics if time.time() - m['timestamp'] < 86400])
        }


class QueryOptimizer:
    """Database query optimization utilities."""
    
    @staticmethod
    def optimize_article_queries(queryset):
        """Optimize article queryset with proper select_related and prefetch_related."""
        return queryset.select_related(
            'author',
            'category',
            'author__userprofile'
        )
    
    @staticmethod
    def optimize_user_queries(queryset):
        """Optimize user queryset with proper select_related and prefetch_related."""
        return queryset.select_related(
            'userprofile'
        ).prefetch_related(
            'article_set'
        )
    



class CacheOptimizer:
    """Cache optimization utilities."""
    
    @staticmethod
    def cache_hot_data():
        """Cache frequently accessed data."""
        from apps.articles.models import Article, Category
        from apps.users.models import User
        
        # Cache popular articles
        popular_articles = Article.objects.filter(
            is_active=True, status=2
        ).order_by('-view_count')[:10]
        cache.set('popular_articles', list(popular_articles), 300)  # 5 minutes
        
        # Cache active categories
        categories = Category.objects.filter(is_active=True).order_by('sort_order')
        cache.set('active_categories', list(categories), 1800)  # 30 minutes
        
        # Cache user statistics
        user_stats = {
            'total_users': User.objects.filter(is_active=True).count(),
            'total_articles': Article.objects.filter(is_active=True, status=2).count(),
        }
        cache.set('site_stats', user_stats, 3600)  # 1 hour
    
    @staticmethod
    def get_cached_data(cache_key: str, fetch_func: Callable, timeout: int = 300):
        """Generic cache-or-fetch pattern."""
        data = cache.get(cache_key)
        if data is None:
            data = fetch_func()
            cache.set(cache_key, data, timeout)
        return data
    
    @staticmethod
    def invalidate_related_caches(model_name: str, instance_id: Optional[int] = None):
        """Invalidate caches related to a model instance."""
        patterns_to_clear = {
            'Article': [
                'popular_articles',
                'site_stats',
                f'article_detail_{instance_id}' if instance_id else 'article_detail_*',
                'article_list_*'
            ],
            'User': [
                'site_stats',
                f'user_profile_{instance_id}' if instance_id else 'user_profile_*'
            ],
            'Category': [
                'active_categories',
                'article_list_*'
            ]
        }
        
        patterns = patterns_to_clear.get(model_name, [])
        for pattern in patterns:
            if '*' in pattern:
                # For pattern-based deletion, you'd need a cache backend that supports it
                # or implement a custom solution
                pass
            else:
                cache.delete(pattern)


class RateLimiter:
    """Rate limiting utilities."""
    
    @staticmethod
    def rate_limit(max_requests: int = 100, window: int = 3600, key_func: Optional[Callable] = None):
        """Decorator for rate limiting."""
        def decorator(func: Callable) -> Callable:
            @functools.wraps(func)
            def wrapper(request, *args, **kwargs):
                from apps.common.responses import APIResponse, ErrorCodes
                
                # Generate rate limit key
                if key_func:
                    rate_key = key_func(request)
                else:
                    client_ip = request.META.get('REMOTE_ADDR', 'unknown')
                    user_id = getattr(request.auth, 'id', 'anonymous')
                    rate_key = f"rate_limit:{client_ip}:{user_id}:{func.__name__}"
                
                # Check current request count
                current_requests = cache.get(rate_key, 0)
                
                if current_requests >= max_requests:
                    return APIResponse.error(
                        code=ErrorCodes.TOO_MANY_REQUESTS,
                        message=f"请求过于频繁，请在{window//60}分钟后再试"
                    )
                
                # Increment request count
                cache.set(rate_key, current_requests + 1, window)
                
                return func(request, *args, **kwargs)
            
            return wrapper
        return decorator
    
    @staticmethod
    def get_rate_limit_status(request, func_name: str, max_requests: int = 100) -> dict:
        """Get current rate limit status for a request."""
        client_ip = request.META.get('REMOTE_ADDR', 'unknown')
        user_id = getattr(request.auth, 'id', 'anonymous')
        rate_key = f"rate_limit:{client_ip}:{user_id}:{func_name}"
        
        current_requests = cache.get(rate_key, 0)
        remaining = max(0, max_requests - current_requests)
        
        return {
            'current_requests': current_requests,
            'max_requests': max_requests,
            'remaining': remaining,
            'reset_time': cache.ttl(rate_key) if hasattr(cache, 'ttl') else None
        }


# Convenience decorators combining multiple optimizations
def optimize_api_endpoint(monitor_performance: bool = True, 
                         monitor_queries: bool = True,
                         rate_limit_requests: int = None):
    """Decorator that combines multiple optimizations for API endpoints."""
    def decorator(func: Callable) -> Callable:
        # Apply decorators in reverse order (innermost first)
        optimized_func = func
        
        if rate_limit_requests:
            optimized_func = RateLimiter.rate_limit(rate_limit_requests)(optimized_func)
        
        if monitor_queries:
            optimized_func = PerformanceMonitor.monitor_database_queries(optimized_func)
        
        if monitor_performance:
            optimized_func = PerformanceMonitor.monitor_execution_time()(optimized_func)
        
        return optimized_func
    
    return decorator


# Example usage in views:
# @optimize_api_endpoint(rate_limit_requests=60)  # 60 requests per hour
# def list_articles(request):
#     queryset = Article.objects.all()
#     queryset = QueryOptimizer.optimize_article_queries(queryset)
#     # ... rest of the view logic