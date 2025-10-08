"""Custom exceptions for the application."""

from typing import Optional, Any, Dict


class BaseAPIException(Exception):
    """Base exception for API errors."""
    
    default_message = "An error occurred"
    default_code = "error"
    default_status_code = 500
    
    def __init__(
        self,
        message: Optional[str] = None,
        code: Optional[str] = None,
        status_code: Optional[int] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        self.message = message or self.default_message
        self.code = code or self.default_code
        self.status_code = status_code or self.default_status_code
        self.details = details or {}
        super().__init__(self.message)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary."""
        result = {
            'error': {
                'code': self.code,
                'message': self.message,
            }
        }
        if self.details:
            result['error']['details'] = self.details
        return result


class ValidationException(BaseAPIException):
    """Exception for validation errors."""
    
    default_message = "Validation failed"
    default_code = "validation_error"
    default_status_code = 400


class AuthenticationException(BaseAPIException):
    """Exception for authentication errors."""
    
    default_message = "Authentication failed"
    default_code = "authentication_error"
    default_status_code = 401


class PermissionException(BaseAPIException):
    """Exception for permission errors."""
    
    default_message = "Permission denied"
    default_code = "permission_error"
    default_status_code = 403


class NotFoundException(BaseAPIException):
    """Exception for resource not found errors."""
    
    default_message = "Resource not found"
    default_code = "not_found"
    default_status_code = 404


class ConflictException(BaseAPIException):
    """Exception for resource conflict errors."""
    
    default_message = "Resource conflict"
    default_code = "conflict"
    default_status_code = 409


class RateLimitException(BaseAPIException):
    """Exception for rate limit errors."""
    
    default_message = "Rate limit exceeded"
    default_code = "rate_limit_exceeded"
    default_status_code = 429


class ServerException(BaseAPIException):
    """Exception for internal server errors."""
    
    default_message = "Internal server error"
    default_code = "server_error"
    default_status_code = 500


class ExternalServiceException(BaseAPIException):
    """Exception for external service errors."""
    
    default_message = "External service error"
    default_code = "external_service_error"
    default_status_code = 502


class ServiceUnavailableException(BaseAPIException):
    """Exception for service unavailable errors."""
    
    default_message = "Service temporarily unavailable"
    default_code = "service_unavailable"
    default_status_code = 503