"""Common utility functions for the application."""

import hashlib
import uuid
from typing import Optional, Any, Dict
from datetime import datetime

from django.core.exceptions import ValidationError
from loguru import logger


def generate_uuid(length=16) -> str:
    """Generate a unique UUID string.

    Args:
        length (int): UUID length.
    
    Returns:
        str: A unique UUID string.
    """
    return hashlib.sha256(uuid.uuid4().bytes).hexdigest()[:length]


def generate_request_id() -> str:
    """生成请求ID.
    
    Returns:
        str: 唯一的请求ID
    """
    return f"req-{generate_uuid(8)}"


def generate_hash(data: str, algorithm: str = 'sha256') -> str:
    """Generate hash for given data.
    
    Args:
        data: The data to hash.
        algorithm: The hash algorithm to use.
        
    Returns:
        str: The generated hash.
        
    Raises:
        ValueError: If the algorithm is not supported.
    """
    try:
        hash_obj = hashlib.new(algorithm)
        hash_obj.update(data.encode('utf-8'))
        return hash_obj.hexdigest()
    except ValueError as e:
        logger.error(f"Unsupported hash algorithm: {algorithm}")
        raise ValueError(f"Unsupported hash algorithm: {algorithm}") from e


def validate_file_size(file_obj: Any, max_size_mb: int = 10) -> None:
    """Validate file size.
    
    Args:
        file_obj: The file object to validate.
        max_size_mb: Maximum file size in MB.
        
    Raises:
        ValidationError: If file size exceeds the limit.
    """
    if not hasattr(file_obj, 'size'):
        return
        
    max_size_bytes = max_size_mb * 1024 * 1024
    if file_obj.size > max_size_bytes:
        raise ValidationError(
            f"文件大小不能超过 {max_size_mb}MB，当前文件大小: {file_obj.size / (1024 * 1024):.2f}MB"
        )


def validate_file_extension(file_obj: Any, allowed_extensions: list) -> None:
    """Validate file extension.
    
    Args:
        file_obj: The file object to validate.
        allowed_extensions: List of allowed file extensions.
        
    Raises:
        ValidationError: If file extension is not allowed.
    """
    if not hasattr(file_obj, 'name'):
        return
        
    file_extension = file_obj.name.split('.')[-1].lower()
    if file_extension not in allowed_extensions:
        raise ValidationError(
            f"不支持的文件格式: .{file_extension}，支持的格式: {', '.join(allowed_extensions)}"
        )


def format_datetime(dt: Optional[datetime], format_str: str = '%Y-%m-%d %H:%M:%S') -> Optional[str]:
    """Format datetime object to string.
    
    Args:
        dt: The datetime object to format.
        format_str: The format string.
        
    Returns:
        str or None: Formatted datetime string or None if dt is None.
    """
    if dt is None:
        return None
    return dt.strftime(format_str)


def get_client_ip(request) -> str:
    """Get client IP address from request.
    
    Args:
        request: Django request object.
        
    Returns:
        str: Client IP address.
    """
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip or ''


def safe_int(value: Any, default: int = 0) -> int:
    """Safely convert value to integer.
    
    Args:
        value: The value to convert.
        default: Default value if conversion fails.
        
    Returns:
        int: Converted integer or default value.
    """
    try:
        return int(value)
    except (ValueError, TypeError):
        return default


def safe_float(value: Any, default: float = 0.0) -> float:
    """Safely convert value to float.
    
    Args:
        value: The value to convert.
        default: Default value if conversion fails.
        
    Returns:
        float: Converted float or default value.
    """
    try:
        return float(value)
    except (ValueError, TypeError):
        return default


def paginate_queryset(queryset, page: int = 1, page_size: int = 20) -> Dict[str, Any]:
    """Paginate queryset and return pagination info.
    
    Args:
        queryset: Django queryset to paginate.
        page: Page number (1-based).
        page_size: Number of items per page.
        
    Returns:
        dict: Pagination information including items, total, page info.
    """
    from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
    
    paginator = Paginator(queryset, page_size)
    total_pages = paginator.num_pages
    total_items = paginator.count
    
    try:
        page_obj = paginator.page(page)
    except PageNotAnInteger:
        page_obj = paginator.page(1)
        page = 1
    except EmptyPage:
        page_obj = paginator.page(total_pages)
        page = total_pages
    
    return {
        'items': list(page_obj),
        'pagination': {
            'current_page': page,
            'total_pages': total_pages,
            'total_items': total_items,
            'page_size': page_size,
            'has_next': page_obj.has_next(),
            'has_previous': page_obj.has_previous(),
        }
    }