"""
用户模块性能监控工具
"""
import time
import logging
from functools import wraps
from django.core.cache import cache
from django.db import connection
from .config import UserConfig

logger = logging.getLogger(__name__)


class PerformanceMonitor:
    """性能监控类"""
    
    # 性能指标缓存键
    CACHE_KEY_PREFIX = "perf_monitor"
    CACHE_TIMEOUT = 300  # 5分钟
    
    @classmethod
    def get_cache_key(cls, metric_name):
        """获取缓存键"""
        return f"{cls.CACHE_KEY_PREFIX}:{metric_name}"
    
    @classmethod
    def record_metric(cls, metric_name, value, operation="avg"):
        """记录性能指标"""
        cache_key = cls.get_cache_key(metric_name)
        
        try:
            # 获取现有数据
            existing_data = cache.get(cache_key, {"count": 0, "total": 0, "min": None, "max": None})
            
            # 更新统计数据
            existing_data["count"] += 1
            existing_data["total"] += value
            
            if existing_data["min"] is None or value < existing_data["min"]:
                existing_data["min"] = value
            if existing_data["max"] is None or value > existing_data["max"]:
                existing_data["max"] = value
            
            # 计算平均值
            existing_data["avg"] = existing_data["total"] / existing_data["count"]
            
            # 存储到缓存
            cache.set(cache_key, existing_data, cls.CACHE_TIMEOUT)
            
            # 如果性能异常，记录警告
            if value > 1.0:  # 超过1秒
                logger.warning(f"性能警告: {metric_name} 耗时 {value:.3f}s")
                
        except Exception as e:
            logger.error(f"记录性能指标失败: {e}")
    
    @classmethod
    def get_metrics(cls, metric_name):
        """获取性能指标"""
        cache_key = cls.get_cache_key(metric_name)
        return cache.get(cache_key, {})
    
    @classmethod
    def get_all_metrics(cls):
        """获取所有性能指标"""
        metrics = {}
        
        # 常见的性能指标
        metric_names = [
            "cache_hit_rate",
            "db_query_time",
            "middleware_processing",
            "authentication_check"
        ]
        
        for metric_name in metric_names:
            metrics[metric_name] = cls.get_metrics(metric_name)
        
        return metrics


def monitor_performance(metric_name):
    """性能监控装饰器"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            
            try:
                result = func(*args, **kwargs)
                return result
            finally:
                end_time = time.time()
                execution_time = end_time - start_time
                
                # 记录性能指标
                PerformanceMonitor.record_metric(metric_name, execution_time)
                
                # 记录详细日志（仅在调试模式下）
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug(f"{func.__name__} 执行时间: {execution_time:.3f}s")
        
        return wrapper
    return decorator


def monitor_db_queries(func):
    """数据库查询监控装饰器"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        # 记录查询前的状态
        queries_before = len(connection.queries)
        
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        
        # 计算查询数量和时间
        queries_after = len(connection.queries)
        query_count = queries_after - queries_before
        execution_time = end_time - start_time
        
        # 记录性能指标
        PerformanceMonitor.record_metric("db_query_time", execution_time)
        
        # 如果查询过多，记录警告
        if query_count > 5:
            logger.warning(f"{func.__name__} 执行了 {query_count} 个数据库查询")
        
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f"{func.__name__} - 查询数: {query_count}, 耗时: {execution_time:.3f}s")
        
        return result
    
    return wrapper


class CacheMonitor:
    """缓存监控类"""
    
    @classmethod
    def record_cache_hit(cls, cache_key, hit=True):
        """记录缓存命中情况"""
        metric_name = "cache_hit_rate"
        cache_stats_key = f"cache_stats:{cache_key}"
        
        try:
            # 获取现有统计
            stats = cache.get(cache_stats_key, {"hits": 0, "misses": 0})
            
            if hit:
                stats["hits"] += 1
            else:
                stats["misses"] += 1
            
            # 更新统计
            cache.set(cache_stats_key, stats, 3600)  # 1小时
            
            # 计算命中率
            total = stats["hits"] + stats["misses"]
            hit_rate = stats["hits"] / total if total > 0 else 0
            
            # 记录到性能监控
            PerformanceMonitor.record_metric(metric_name, hit_rate)
            
        except Exception as e:
            logger.error(f"记录缓存统计失败: {e}")
    
    @classmethod
    def get_cache_stats(cls, cache_key):
        """获取缓存统计"""
        cache_stats_key = f"cache_stats:{cache_key}"
        return cache.get(cache_stats_key, {"hits": 0, "misses": 0})


# 性能监控工具已就绪，可用于监控其他关键功能