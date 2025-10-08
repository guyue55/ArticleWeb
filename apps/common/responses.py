"""Common response utilities for API endpoints."""

from typing import Any, Optional, Dict, List
from uuid import uuid4


class APIResponse:
    """Standard API response wrapper."""
    
    @staticmethod
    def success(
        data: Any = None,
        message: str = "",
        request_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create a successful response.
        
        Args:
            data: Response data
            message: Success message
            request_id: Request ID for tracking
            
        Returns:
            dict: Standardized success response
        """
        return {
            "code": 0,
            "message": message,
            "requestId": request_id or str(uuid4()),
            "data": data
        }
    
    @staticmethod
    def error(
        code: int = -1,
        message: str = "error",
        data: Any = None,
        request_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create an error response.
        
        Args:
            code: Error code
            message: Error message
            data: Additional error data
            request_id: Request ID for tracking
            
        Returns:
            dict: Standardized error response
        """
        return {
            "code": code,
            "message": message,
            "requestId": request_id or str(uuid4()),
            "data": data
        }
    
    @staticmethod
    def paginated(
        items: List[Any],
        total: int,
        limit: int,
        offset: int,
        message: str = "",
        request_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create a paginated response.
        
        Args:
            items: List of items
            total: Total number of items
            limit: Items per page
            offset: Offset for pagination
            message: Success message
            request_id: Request ID for tracking
            
        Returns:
            dict: Standardized paginated response
        """
        return APIResponse.success(
            data={
                "items": items,
                "total": total,
                "limit": limit,
                "offset": offset
            },
            message=message,
            request_id=request_id
        )


class ErrorCodes:
    """标准化错误码"""
    
    # Client errors (4xx)
    BAD_REQUEST = 400
    UNAUTHORIZED = 401
    FORBIDDEN = 403
    NOT_FOUND = 404
    METHOD_NOT_ALLOWED = 405
    CONFLICT = 409
    VALIDATION_ERROR = 422
    TOO_MANY_REQUESTS = 429
    
    # Server errors (5xx)
    INTERNAL_SERVER_ERROR = 500
    NOT_IMPLEMENTED = 501
    BAD_GATEWAY = 502
    SERVICE_UNAVAILABLE = 503
    GATEWAY_TIMEOUT = 504


class ErrorMessages:
    """Standard error messages."""
    
    # Authentication and authorization
    UNAUTHORIZED = "未授权访问"
    FORBIDDEN = "权限不足"
    TOKEN_EXPIRED = "令牌已过期"
    TOKEN_INVALID = "令牌无效"
    
    # Resource errors
    NOT_FOUND = "资源不存在"
    ALREADY_EXISTS = "资源已存在"
    
    # Validation errors
    VALIDATION_ERROR = "数据验证失败"
    REQUIRED_FIELD_MISSING = "必填字段缺失"
    INVALID_FORMAT = "数据格式无效"
    
    # Server errors
    INTERNAL_ERROR = "服务器内部错误"
    SERVICE_UNAVAILABLE = "服务暂时不可用"
    
    # Business logic errors
    OPERATION_FAILED = "操作失败"
    DUPLICATE_OPERATION = "重复操作"
    RATE_LIMIT_EXCEEDED = "请求频率超限"