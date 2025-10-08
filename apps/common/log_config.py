"""通用日志工具，用于规范化API日志记录。"""

import logging
import json
import time
from typing import Any, Dict, Optional
from functools import wraps
from django.http import HttpRequest
from common.utils import get_client_ip


class APILogger:
    """API日志记录器。"""
    
    def __init__(self, logger_name: str = "api"):
        self.logger = logging.getLogger(logger_name)
    
    def log_request(self, request: HttpRequest, endpoint: str, **extra_data) -> None:
        """记录API请求日志。
        
        Args:
            request: Django请求对象
            endpoint: API端点名称
            **extra_data: 额外的日志数据
        """
        log_data = {
            "type": "api_request",
            "endpoint": endpoint,
            "method": request.method,
            "path": request.path,
            "client_ip": get_client_ip(request),
            "user_agent": request.META.get('HTTP_USER_AGENT', ''),
            "user_id": getattr(request.user, 'id', None) if hasattr(request, 'user') else None,
            "timestamp": time.time(),
            **extra_data
        }
        
        self.logger.info(f"API Request: {endpoint}", extra=log_data)
    
    def log_response(self, request: HttpRequest, endpoint: str, response_data: Any, 
                    status_code: int = 200, duration: float = 0, **extra_data) -> None:
        """记录API响应日志。
        
        Args:
            request: Django请求对象
            endpoint: API端点名称
            response_data: 响应数据
            status_code: HTTP状态码
            duration: 请求处理时间（秒）
            **extra_data: 额外的日志数据
        """
        log_data = {
            "type": "api_response",
            "endpoint": endpoint,
            "method": request.method,
            "path": request.path,
            "client_ip": get_client_ip(request),
            "user_id": getattr(request.user, 'id', None) if hasattr(request, 'user') else None,
            "status_code": status_code,
            "duration": duration,
            "response_size": len(str(response_data)) if response_data else 0,
            "timestamp": time.time(),
            **extra_data
        }
        
        # 根据状态码选择日志级别
        if status_code >= 500:
            self.logger.error(f"API Response: {endpoint} - {status_code}", extra=log_data)
        elif status_code >= 400:
            self.logger.warning(f"API Response: {endpoint} - {status_code}", extra=log_data)
        else:
            self.logger.info(f"API Response: {endpoint} - {status_code}", extra=log_data)
    
    def log_error(self, request: HttpRequest, endpoint: str, error: Exception, **extra_data) -> None:
        """记录API错误日志。
        
        Args:
            request: Django请求对象
            endpoint: API端点名称
            error: 异常对象
            **extra_data: 额外的日志数据
        """
        log_data = {
            "type": "api_error",
            "endpoint": endpoint,
            "method": request.method,
            "path": request.path,
            "client_ip": get_client_ip(request),
            "user_id": getattr(request.user, 'id', None) if hasattr(request, 'user') else None,
            "error_type": type(error).__name__,
            "error_message": str(error),
            "timestamp": time.time(),
            **extra_data
        }
        
        self.logger.error(f"API Error: {endpoint} - {type(error).__name__}", 
                         extra=log_data, exc_info=True)
    
    def log_performance(self, endpoint: str, duration: float, **metrics) -> None:
        """记录API性能日志。
        
        Args:
            endpoint: API端点名称
            duration: 请求处理时间（秒）
            **metrics: 性能指标
        """
        log_data = {
            "type": "api_performance",
            "endpoint": endpoint,
            "duration": duration,
            "timestamp": time.time(),
            **metrics
        }
        
        # 根据响应时间选择日志级别
        if duration > 5.0:  # 超过5秒
            self.logger.warning(f"Slow API: {endpoint} - {duration:.2f}s", extra=log_data)
        elif duration > 2.0:  # 超过2秒
            self.logger.info(f"API Performance: {endpoint} - {duration:.2f}s", extra=log_data)
        else:
            self.logger.debug(f"API Performance: {endpoint} - {duration:.2f}s", extra=log_data)


def log_api_call(endpoint_name: str = None, log_request: bool = True, 
                log_response: bool = True, log_performance: bool = True):
    """API调用日志装饰器。
    
    Args:
        endpoint_name: API端点名称，默认使用函数名
        log_request: 是否记录请求日志
        log_response: 是否记录响应日志
        log_performance: 是否记录性能日志
        
    Returns:
        装饰器函数
    """
    def decorator(func):
        @wraps(func)
        def wrapper(request, *args, **kwargs):
            endpoint = endpoint_name or func.__name__
            logger = APILogger()
            start_time = time.time()
            
            try:
                # 记录请求日志
                if log_request:
                    logger.log_request(request, endpoint)
                
                # 执行API函数
                response = func(request, *args, **kwargs)
                
                # 计算处理时间
                duration = time.time() - start_time
                
                # 记录响应日志
                if log_response:
                    status_code = getattr(response, 'status_code', 200)
                    logger.log_response(request, endpoint, response, status_code, duration)
                
                # 记录性能日志
                if log_performance:
                    logger.log_performance(endpoint, duration)
                
                return response
                
            except Exception as e:
                # 计算处理时间
                duration = time.time() - start_time
                
                # 记录错误日志
                logger.log_error(request, endpoint, e)
                
                # 记录性能日志（即使出错也要记录）
                if log_performance:
                    logger.log_performance(endpoint, duration, error=True)
                
                # 重新抛出异常
                raise
        
        return wrapper
    return decorator


class DatabaseQueryLogger:
    """数据库查询日志记录器。"""
    
    def __init__(self, logger_name: str = "db_queries"):
        self.logger = logging.getLogger(logger_name)
    
    def log_query(self, query: str, params: tuple = None, duration: float = 0, 
                 result_count: int = 0) -> None:
        """记录数据库查询日志。
        
        Args:
            query: SQL查询语句
            params: 查询参数
            duration: 查询执行时间（秒）
            result_count: 结果数量
        """
        log_data = {
            "type": "db_query",
            "query": query,
            "params": params,
            "duration": duration,
            "result_count": result_count,
            "timestamp": time.time()
        }
        
        # 根据查询时间选择日志级别
        if duration > 1.0:  # 超过1秒
            self.logger.warning(f"Slow Query: {duration:.3f}s", extra=log_data)
        elif duration > 0.1:  # 超过100毫秒
            self.logger.info(f"Query: {duration:.3f}s", extra=log_data)
        else:
            self.logger.debug(f"Query: {duration:.3f}s", extra=log_data)


class SecurityLogger:
    """安全相关日志记录器。"""
    
    def __init__(self, logger_name: str = "security"):
        self.logger = logging.getLogger(logger_name)
    
    def log_authentication_attempt(self, request: HttpRequest, username: str, 
                                  success: bool, reason: str = None) -> None:
        """记录认证尝试日志。
        
        Args:
            request: Django请求对象
            username: 用户名
            success: 是否成功
            reason: 失败原因
        """
        log_data = {
            "type": "authentication_attempt",
            "username": username,
            "success": success,
            "reason": reason,
            "client_ip": get_client_ip(request),
            "user_agent": request.META.get('HTTP_USER_AGENT', ''),
            "timestamp": time.time()
        }
        
        if success:
            self.logger.info(f"Authentication Success: {username}", extra=log_data)
        else:
            self.logger.warning(f"Authentication Failed: {username} - {reason}", extra=log_data)
    
    def log_permission_denied(self, request: HttpRequest, resource: str, 
                            action: str, user_id: int = None) -> None:
        """记录权限拒绝日志。
        
        Args:
            request: Django请求对象
            resource: 资源名称
            action: 操作类型
            user_id: 用户ID
        """
        log_data = {
            "type": "permission_denied",
            "resource": resource,
            "action": action,
            "user_id": user_id,
            "client_ip": get_client_ip(request),
            "path": request.path,
            "timestamp": time.time()
        }
        
        self.logger.warning(f"Permission Denied: {action} on {resource}", extra=log_data)
    
    def log_suspicious_activity(self, request: HttpRequest, activity_type: str, 
                              details: Dict[str, Any]) -> None:
        """记录可疑活动日志。
        
        Args:
            request: Django请求对象
            activity_type: 活动类型
            details: 详细信息
        """
        log_data = {
            "type": "suspicious_activity",
            "activity_type": activity_type,
            "details": details,
            "client_ip": get_client_ip(request),
            "user_agent": request.META.get('HTTP_USER_AGENT', ''),
            "path": request.path,
            "timestamp": time.time()
        }
        
        self.logger.error(f"Suspicious Activity: {activity_type}", extra=log_data)


# 全局日志记录器实例
api_logger = APILogger()
db_logger = DatabaseQueryLogger()
security_logger = SecurityLogger()