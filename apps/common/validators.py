"""通用验证器，用于规范化API请求数据验证。"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ValidationError
from django.core.exceptions import ValidationError as DjangoValidationError
from .responses import APIResponse, ErrorCodes


class ValidationMixin:
    """验证器混入类，提供通用的数据验证方法。"""
    
    @classmethod
    def validate_data(cls, data: Dict[str, Any], schema_class: BaseModel) -> tuple[bool, Any]:
        """验证请求数据。
        
        Args:
            data: 要验证的数据字典
            schema_class: Pydantic模型类
            
        Returns:
            tuple: (是否验证成功, 验证后的数据或错误响应)
        """
        try:
            validated_data = schema_class.model_validate(data)
            return True, validated_data
        except ValidationError as e:
            error_messages = []
            for error in e.errors():
                field = '.'.join(str(loc) for loc in error['loc'])
                message = error['msg']
                error_messages.append(f"{field}: {message}")
            
            error_response = APIResponse.error(
                code=ErrorCodes.BAD_REQUEST,
                message=f"数据验证失败: {'; '.join(error_messages)}"
            )
            return False, error_response
    
    @classmethod
    def validate_pagination_params(cls, limit: int, offset: int) -> tuple[bool, Any]:
        """验证分页参数。
        
        Args:
            limit: 每页数量
            offset: 偏移量
            
        Returns:
            tuple: (是否验证成功, 验证后的参数或错误响应)
        """
        if limit <= 0 or limit > 100:
            return False, APIResponse.error(
                code=ErrorCodes.BAD_REQUEST,
                message="limit参数必须在1-100之间"
            )
        
        if offset < 0:
            return False, APIResponse.error(
                code=ErrorCodes.BAD_REQUEST,
                message="offset参数不能为负数"
            )
        
        return True, {"limit": limit, "offset": offset}
    
    @classmethod
    def validate_sort_params(cls, sort: Optional[str], allowed_fields: List[str]) -> tuple[bool, Any]:
        """验证排序参数。
        
        Args:
            sort: 排序字符串，格式：field1,field2;desc
            allowed_fields: 允许排序的字段列表
            
        Returns:
            tuple: (是否验证成功, 验证后的排序参数或错误响应)
        """
        if not sort:
            return True, None
        
        try:
            # 解析排序参数
            sort_parts = sort.split(';')
            fields = sort_parts[0].split(',')
            direction = sort_parts[1] if len(sort_parts) > 1 else 'asc'
            
            # 验证排序方向
            if direction not in ['asc', 'desc']:
                return False, APIResponse.error(
                    code=ErrorCodes.BAD_REQUEST,
                    message="排序方向只能是asc或desc"
                )
            
            # 验证排序字段
            invalid_fields = [field for field in fields if field not in allowed_fields]
            if invalid_fields:
                return False, APIResponse.error(
                    code=ErrorCodes.BAD_REQUEST,
                    message=f"不支持的排序字段: {', '.join(invalid_fields)}"
                )
            
            return True, {"fields": fields, "direction": direction}
            
        except Exception:
            return False, APIResponse.error(
                code=ErrorCodes.BAD_REQUEST,
                message="排序参数格式错误，正确格式：field1,field2;desc"
            )
    
    @classmethod
    def validate_id_param(cls, id_value: Any, param_name: str = "id") -> tuple[bool, Any]:
        """验证ID参数。
        
        Args:
            id_value: ID值
            param_name: 参数名称
            
        Returns:
            tuple: (是否验证成功, 验证后的ID或错误响应)
        """
        try:
            id_int = int(id_value)
            if id_int <= 0:
                return False, APIResponse.error(
                    code=ErrorCodes.BAD_REQUEST,
                    message=f"{param_name}必须是正整数"
                )
            return True, id_int
        except (ValueError, TypeError):
            return False, APIResponse.error(
                code=ErrorCodes.BAD_REQUEST,
                message=f"{param_name}必须是有效的整数"
            )
    
    @classmethod
    def validate_search_param(cls, search: Optional[str]) -> tuple[bool, Any]:
        """验证搜索参数。
        
        Args:
            search: 搜索关键词
            
        Returns:
            tuple: (是否验证成功, 验证后的搜索词或错误响应)
        """
        if not search:
            return True, None
        
        # 去除首尾空格
        search = search.strip()
        
        # 检查长度
        if len(search) < 2:
            return False, APIResponse.error(
                code=ErrorCodes.BAD_REQUEST,
                message="搜索关键词至少需要2个字符"
            )
        
        if len(search) > 100:
            return False, APIResponse.error(
                code=ErrorCodes.BAD_REQUEST,
                message="搜索关键词不能超过100个字符"
            )
        
        return True, search