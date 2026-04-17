# -*- coding: utf-8 -*-
"""
文心智能体Django集成示例

展示如何在Django项目中使用文心智能体API客户端
包含服务层封装、视图函数示例和配置说明
"""

import json
import logging
from typing import Dict, Any, Optional, List, Generator
from django.conf import settings
from django.http import JsonResponse, StreamingHttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.utils.decorators import method_decorator
from django.views import View

from .wenxin_agent_client import (
    WenxinAgentClient, 
    WenxinConfig, 
    WenxinAgentManager,
    ApiResponse
)


logger = logging.getLogger(__name__)


class WenxinService:
    """文心智能体服务层"""
    
    def __init__(self):
        self._client = None
        self._manager = WenxinAgentManager()
    
    def get_client(self) -> WenxinAgentClient:
        """
        获取文心智能体客户端实例
        
        Returns:
            WenxinAgentClient: 客户端实例
        """
        if self._client is None:
            config = WenxinConfig(
                client_id=getattr(settings, 'WENXIN_CLIENT_ID', ''),
                client_secret=getattr(settings, 'WENXIN_CLIENT_SECRET', ''),
                app_id=getattr(settings, 'WENXIN_APP_ID', ''),
                secret_key=getattr(settings, 'WENXIN_SECRET_KEY', ''),
                timeout=getattr(settings, 'WENXIN_TIMEOUT', 30),
                max_retries=getattr(settings, 'WENXIN_MAX_RETRIES', 3)
            )
            self._client = WenxinAgentClient(config)
        return self._client
    
    def simple_chat(self, text: str, user_id: str, is_first: bool = False) -> Dict[str, Any]:
        """
        简单对话
        
        Args:
            text: 用户输入文本
            user_id: 用户ID
            is_first: 是否为首次对话
            
        Returns:
            Dict[str, Any]: 响应数据
        """
        try:
            client = self.get_client()
            response = client.get_answer(
                text=text,
                open_id=user_id,
                is_first_conversation=is_first
            )
            
            return {
                'success': True,
                'data': {
                    'status': response.status,
                    'message': response.message,
                    'logid': response.logid,
                    'content': response.data
                }
            }
            
        except Exception as e:
            logger.error(f"简单对话失败: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def conversation_chat(self, 
                         text: str, 
                         user_id: str, 
                         thread_id: Optional[str] = None,
                         is_first: bool = False) -> Dict[str, Any]:
        """
        多轮对话
        
        Args:
            text: 用户输入文本
            user_id: 用户ID
            thread_id: 会话ID
            is_first: 是否为首次对话
            
        Returns:
            Dict[str, Any]: 响应数据
        """
        try:
            client = self.get_client()
            
            # 收集流式响应
            messages = []
            current_thread_id = thread_id
            
            for chunk in client.conversation_stream(
                text=text,
                open_id=user_id,
                thread_id=thread_id,
                is_first_conversation=is_first
            ):
                messages.append(chunk)
                
                # 获取threadId
                if chunk.get('data', {}).get('message', {}).get('threadId'):
                    current_thread_id = chunk['data']['message']['threadId']
            
            return {
                'success': True,
                'data': {
                    'messages': messages,
                    'thread_id': current_thread_id
                }
            }
            
        except Exception as e:
            logger.error(f"多轮对话失败: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def stream_chat(self, 
                   text: str, 
                   user_id: str, 
                   thread_id: Optional[str] = None,
                   is_first: bool = False) -> Generator[str, None, None]:
        """
        流式对话生成器
        
        Args:
            text: 用户输入文本
            user_id: 用户ID
            thread_id: 会话ID
            is_first: 是否为首次对话
            
        Yields:
            str: JSON格式的响应数据
        """
        try:
            client = self.get_client()
            
            for chunk in client.conversation_stream(
                text=text,
                open_id=user_id,
                thread_id=thread_id,
                is_first_conversation=is_first
            ):
                yield f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n"
                
        except Exception as e:
            logger.error(f"流式对话失败: {e}")
            error_data = {
                'success': False,
                'error': str(e)
            }
            yield f"data: {json.dumps(error_data, ensure_ascii=False)}\n\n"
    
    def get_access_token(self, force_refresh: bool = False) -> Dict[str, Any]:
        """
        获取AccessToken
        
        Args:
            force_refresh: 是否强制刷新
            
        Returns:
            Dict[str, Any]: 响应数据
        """
        try:
            client = self.get_client()
            token = client.get_access_token(force_refresh=force_refresh)
            
            return {
                'success': True,
                'data': {
                    'access_token': token
                }
            }
            
        except Exception as e:
            logger.error(f"获取AccessToken失败: {e}")
            return {
                'success': False,
                'error': str(e)
            }


# 全局服务实例
wenxin_service = WenxinService()


# Django视图函数示例

@csrf_exempt
@require_http_methods(["POST"])
def chat_simple_view(request):
    """
    简单对话视图
    
    POST /api/wenxin/chat/simple/
    {
        "text": "你好",
        "user_id": "user123",
        "is_first": false
    }
    """
    try:
        data = json.loads(request.body)
        text = data.get('text', '')
        user_id = data.get('user_id', '')
        is_first = data.get('is_first', False)
        
        if not text or not user_id:
            return JsonResponse({
                'success': False,
                'error': '缺少必要参数: text, user_id'
            }, status=400)
        
        result = wenxin_service.simple_chat(
            text=text,
            user_id=user_id,
            is_first=is_first
        )
        
        return JsonResponse(result)
        
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': '无效的JSON格式'
        }, status=400)
    except Exception as e:
        logger.error(f"简单对话视图错误: {e}")
        return JsonResponse({
            'success': False,
            'error': '服务器内部错误'
        }, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def chat_conversation_view(request):
    """
    多轮对话视图
    
    POST /api/wenxin/chat/conversation/
    {
        "text": "继续刚才的话题",
        "user_id": "user123",
        "thread_id": "thread456",
        "is_first": false
    }
    """
    try:
        data = json.loads(request.body)
        text = data.get('text', '')
        user_id = data.get('user_id', '')
        thread_id = data.get('thread_id')
        is_first = data.get('is_first', False)
        
        if not text or not user_id:
            return JsonResponse({
                'success': False,
                'error': '缺少必要参数: text, user_id'
            }, status=400)
        
        result = wenxin_service.conversation_chat(
            text=text,
            user_id=user_id,
            thread_id=thread_id,
            is_first=is_first
        )
        
        return JsonResponse(result)
        
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': '无效的JSON格式'
        }, status=400)
    except Exception as e:
        logger.error(f"多轮对话视图错误: {e}")
        return JsonResponse({
            'success': False,
            'error': '服务器内部错误'
        }, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def chat_stream_view(request):
    """
    流式对话视图
    
    POST /api/wenxin/chat/stream/
    {
        "text": "请详细介绍Python",
        "user_id": "user123",
        "thread_id": "thread456",
        "is_first": false
    }
    """
    try:
        data = json.loads(request.body)
        text = data.get('text', '')
        user_id = data.get('user_id', '')
        thread_id = data.get('thread_id')
        is_first = data.get('is_first', False)
        
        if not text or not user_id:
            return JsonResponse({
                'success': False,
                'error': '缺少必要参数: text, user_id'
            }, status=400)
        
        def stream_generator():
            yield "data: {\"event\": \"start\"}\n\n"
            
            for chunk in wenxin_service.stream_chat(
                text=text,
                user_id=user_id,
                thread_id=thread_id,
                is_first=is_first
            ):
                yield chunk
            
            yield "data: {\"event\": \"end\"}\n\n"
        
        response = StreamingHttpResponse(
            stream_generator(),
            content_type='text/event-stream'
        )
        response['Cache-Control'] = 'no-cache'
        response['Connection'] = 'keep-alive'
        response['Access-Control-Allow-Origin'] = '*'
        
        return response
        
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': '无效的JSON格式'
        }, status=400)
    except Exception as e:
        logger.error(f"流式对话视图错误: {e}")
        return JsonResponse({
            'success': False,
            'error': '服务器内部错误'
        }, status=500)


@csrf_exempt
@require_http_methods(["GET"])
def get_access_token_view(request):
    """
    获取AccessToken视图
    
    GET /api/wenxin/token/?force_refresh=true
    """
    try:
        force_refresh = request.GET.get('force_refresh', 'false').lower() == 'true'
        
        result = wenxin_service.get_access_token(force_refresh=force_refresh)
        
        return JsonResponse(result)
        
    except Exception as e:
        logger.error(f"获取AccessToken视图错误: {e}")
        return JsonResponse({
            'success': False,
            'error': '服务器内部错误'
        }, status=500)


# Django类视图示例

@method_decorator(csrf_exempt, name='dispatch')
class WenxinChatView(View):
    """文心智能体对话类视图"""
    
    def post(self, request):
        """处理对话请求"""
        try:
            data = json.loads(request.body)
            chat_type = data.get('type', 'simple')  # simple, conversation, stream
            text = data.get('text', '')
            user_id = data.get('user_id', '')
            thread_id = data.get('thread_id')
            is_first = data.get('is_first', False)
            
            if not text or not user_id:
                return JsonResponse({
                    'success': False,
                    'error': '缺少必要参数: text, user_id'
                }, status=400)
            
            if chat_type == 'simple':
                result = wenxin_service.simple_chat(
                    text=text,
                    user_id=user_id,
                    is_first=is_first
                )
                return JsonResponse(result)
                
            elif chat_type == 'conversation':
                result = wenxin_service.conversation_chat(
                    text=text,
                    user_id=user_id,
                    thread_id=thread_id,
                    is_first=is_first
                )
                return JsonResponse(result)
                
            elif chat_type == 'stream':
                def stream_generator():
                    yield "data: {\"event\": \"start\"}\n\n"
                    
                    for chunk in wenxin_service.stream_chat(
                        text=text,
                        user_id=user_id,
                        thread_id=thread_id,
                        is_first=is_first
                    ):
                        yield chunk
                    
                    yield "data: {\"event\": \"end\"}\n\n"
                
                response = StreamingHttpResponse(
                    stream_generator(),
                    content_type='text/event-stream'
                )
                response['Cache-Control'] = 'no-cache'
                response['Connection'] = 'keep-alive'
                response['Access-Control-Allow-Origin'] = '*'
                
                return response
            
            else:
                return JsonResponse({
                    'success': False,
                    'error': f'不支持的对话类型: {chat_type}'
                }, status=400)
                
        except json.JSONDecodeError:
            return JsonResponse({
                'success': False,
                'error': '无效的JSON格式'
            }, status=400)
        except Exception as e:
            logger.error(f"对话类视图错误: {e}")
            return JsonResponse({
                'success': False,
                'error': '服务器内部错误'
            }, status=500)


# Django配置示例
"""
在 settings.py 中添加以下配置：

# 文心智能体配置
WENXIN_CLIENT_ID = 'your_client_id'  # 应用的API Key
WENXIN_CLIENT_SECRET = 'your_client_secret'  # 应用的Secret Key
WENXIN_APP_ID = 'your_app_id'  # 智能体ID
WENXIN_SECRET_KEY = 'your_secret_key'  # 智能体Secret Key
WENXIN_TIMEOUT = 30  # 请求超时时间（秒）
WENXIN_MAX_RETRIES = 3  # 最大重试次数

# 日志配置
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': 'wenxin.log',
        },
    },
    'loggers': {
        'apps.common.wenxin_agent_client': {
            'handlers': ['file'],
            'level': 'INFO',
            'propagate': True,
        },
        'apps.common.wenxin_usage_example': {
            'handlers': ['file'],
            'level': 'INFO',
            'propagate': True,
        },
    },
}
"""

# URL配置示例
"""
在 urls.py 中添加以下路由：

from django.urls import path
from apps.common.wenxin_usage_example import (
    chat_simple_view,
    chat_conversation_view,
    chat_stream_view,
    get_access_token_view,
    WenxinChatView
)

urlpatterns = [
    # 函数视图
    path('api/wenxin/chat/simple/', chat_simple_view, name='wenxin_chat_simple'),
    path('api/wenxin/chat/conversation/', chat_conversation_view, name='wenxin_chat_conversation'),
    path('api/wenxin/chat/stream/', chat_stream_view, name='wenxin_chat_stream'),
    path('api/wenxin/token/', get_access_token_view, name='wenxin_get_token'),
    
    # 类视图
    path('api/wenxin/chat/', WenxinChatView.as_view(), name='wenxin_chat'),
]
"""


# 测试示例
if __name__ == "__main__":
    import os
    import django
    
    # 设置Django环境
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'article_web.settings')
    django.setup()
    
    # 测试服务
    service = WenxinService()
    
    # 测试简单对话
    print("=== 测试简单对话 ===")
    result = service.simple_chat(
        text="你好，请介绍一下自己",
        user_id="test_user_123",
        is_first=True
    )
    print(f"简单对话结果: {result}")
    
    # 测试多轮对话
    print("\n=== 测试多轮对话 ===")
    result = service.conversation_chat(
        text="请详细介绍Python编程语言",
        user_id="test_user_123"
    )
    print(f"多轮对话结果: {result}")
    
    # 测试流式对话
    print("\n=== 测试流式对话 ===")
    for chunk in service.stream_chat(
        text="请用简洁的语言介绍机器学习",
        user_id="test_user_123"
    ):
        print(f"流式数据: {chunk.strip()}")
    
    # 测试获取AccessToken
    print("\n=== 测试获取AccessToken ===")
    result = service.get_access_token()
    print(f"AccessToken结果: {result}")