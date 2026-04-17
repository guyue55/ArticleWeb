# 文心智能体平台 API 工具类使用指南

## 概述

本工具类基于文心智能体平台官方API文档开发，提供了完整的Python SDK，支持：

- **AccessToken获取** - 用于API认证
- **getAnswer接口** - 单次问答对话
- **conversation接口** - 流式对话
- **多种消息类型** - 文本、图片、文件、多模态
- **Django集成** - 完整的Web应用集成示例

## 快速开始

### 1. 安装依赖

```bash
pip install requests
pip install django  # 如果使用Django集成
```

### 2. 基本配置

```python
from apps.common.wenxin_agent_client import WenxinConfig, WenxinAgentClient

# 创建配置
config = WenxinConfig(
    client_id="your_client_id",        # 应用的API Key
    client_secret="your_client_secret", # 应用的Secret Key
    app_id="your_app_id",              # 智能体ID
    secret_key="your_secret_key",      # 智能体Secret Key
    timeout=30,                        # 请求超时时间
    max_retries=3                      # 最大重试次数
)

# 创建客户端
client = WenxinAgentClient(config)
```

### 3. 基本使用

```python
# 获取AccessToken
token = client.get_access_token()
print(f"AccessToken: {token}")

# 单次对话
response = client.get_answer(
    text="你好，请介绍一下自己",
    open_id="user123"
)
print(f"响应: {response.data}")

# 流式对话
for chunk in client.conversation_stream(
    text="请详细介绍Python编程语言",
    open_id="user123"
):
    print(f"流式数据: {chunk}")
```

## 核心类说明

### WenxinConfig

配置类，包含所有必要的API配置信息。

```python
@dataclass
class WenxinConfig:
    client_id: str          # 应用的API Key
    client_secret: str      # 应用的Secret Key
    app_id: str            # 智能体ID
    secret_key: str        # 智能体Secret Key
    timeout: int = 30      # 请求超时时间
    max_retries: int = 3   # 最大重试次数
```

### WenxinAgentClient

主要的API客户端类，提供所有核心功能。

#### 主要方法

##### get_access_token(force_refresh=False)

获取AccessToken，支持自动刷新。

```python
# 获取token（自动缓存和刷新）
token = client.get_access_token()

# 强制刷新token
token = client.get_access_token(force_refresh=True)
```

##### get_answer(text, open_id, thread_id=None, is_first_conversation=False)

调用getAnswer接口进行单次对话。

```python
response = client.get_answer(
    text="你好",
    open_id="user123",
    thread_id="thread456",  # 可选，用于多轮对话
    is_first_conversation=True  # 是否为首次对话
)

print(f"状态: {response.status}")
print(f"消息: {response.message}")
print(f"数据: {response.data}")
```

##### conversation_stream(text, open_id, thread_id=None, is_first_conversation=False)

调用conversation接口进行流式对话。

```python
for chunk in client.conversation_stream(
    text="请详细介绍机器学习",
    open_id="user123",
    thread_id="thread456",
    is_first_conversation=False
):
    # 处理流式数据
    if chunk.get('data', {}).get('message', {}).get('content'):
        content = chunk['data']['message']['content']
        for item in content:
            if item.get('dataType') == 'markdown':
                text = item.get('data', {}).get('text', '')
                print(text, end='', flush=True)
```

### 消息类型支持

#### 文本消息

```python
# 直接使用字符串
response = client.get_answer(
    text="你好",
    open_id="user123"
)

# 或使用消息对象
message = client.create_text_message(
    text="你好",
    is_first_conversation=True
)
```

#### 图片消息

```python
message = client.create_image_message(
    image_url="https://example.com/image.png",
    image_name="示例图片",
    image_type="png",
    image_size=1024
)
```

#### 文件消息

```python
message = client.create_file_message(
    file_id="file-123",
    file_url="https://example.com/document.pdf",
    file_name="文档.pdf",
    file_type="pdf",
    file_size=2048
)
```

## Django集成

### 1. 配置设置

在 `settings.py` 中添加配置：

```python
# 文心智能体配置
WENXIN_CLIENT_ID = 'your_client_id'
WENXIN_CLIENT_SECRET = 'your_client_secret'
WENXIN_APP_ID = 'your_app_id'
WENXIN_SECRET_KEY = 'your_secret_key'
WENXIN_TIMEOUT = 30
WENXIN_MAX_RETRIES = 3

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
    },
}
```

### 2. URL配置

在 `urls.py` 中添加路由：

```python
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
```

### 3. 使用服务层

```python
from apps.common.wenxin_usage_example import wenxin_service

# 简单对话
result = wenxin_service.simple_chat(
    text="你好",
    user_id="user123",
    is_first=True
)

# 多轮对话
result = wenxin_service.conversation_chat(
    text="继续刚才的话题",
    user_id="user123",
    thread_id="thread456"
)

# 流式对话
for chunk in wenxin_service.stream_chat(
    text="请详细介绍AI",
    user_id="user123"
):
    print(chunk)
```

## API接口说明

### 1. 简单对话接口

**请求**
```http
POST /api/wenxin/chat/simple/
Content-Type: application/json

{
    "text": "你好",
    "user_id": "user123",
    "is_first": true
}
```

**响应**
```json
{
    "success": true,
    "data": {
        "status": 0,
        "message": "success",
        "logid": "123456789",
        "content": {
            "message": {
                "content": [
                    {
                        "dataType": "markdown",
                        "data": {
                            "text": "你好！我是文心智能体..."
                        }
                    }
                ]
            }
        }
    }
}
```

### 2. 多轮对话接口

**请求**
```http
POST /api/wenxin/chat/conversation/
Content-Type: application/json

{
    "text": "继续刚才的话题",
    "user_id": "user123",
    "thread_id": "thread456",
    "is_first": false
}
```

**响应**
```json
{
    "success": true,
    "data": {
        "messages": [
            {
                "status": 0,
                "message": "succ",
                "data": {
                    "message": {
                        "threadId": "thread456",
                        "content": [...]
                    }
                }
            }
        ],
        "thread_id": "thread456"
    }
}
```

### 3. 流式对话接口

**请求**
```http
POST /api/wenxin/chat/stream/
Content-Type: application/json

{
    "text": "请详细介绍Python",
    "user_id": "user123",
    "thread_id": "thread456",
    "is_first": false
}
```

**响应**
```
Content-Type: text/event-stream

data: {"event": "start"}

data: {"status":0,"message":"succ","data":{"message":{"content":[{"dataType":"markdown","data":{"text":"Python是..."}}]}}}

data: {"event": "end"}
```

### 4. 获取AccessToken接口

**请求**
```http
GET /api/wenxin/token/?force_refresh=true
```

**响应**
```json
{
    "success": true,
    "data": {
        "access_token": "24.xxx.xxx"
    }
}
```

## 错误处理

### 错误码说明

| 错误码 | 说明 | 描述 |
|--------|------|------|
| 0 | succ | 请求成功 |
| 1000 | invalid input | 传参错误 |
| 1001 | system error | 服务端内部错误 |
| 1002 | rate limit exceeded | 限流 |
| 1003 | generate failed | 生成失败 |
| 1005 | hit kunlun | 命中昆仑反作弊 |
| 1006 | agent is offline | agent服务已下线 |
| 1113 | query hit 3s dict | 命中3s词表 |
| 1115 | agent usage limit exceeded | agent请求数量超限 |
| 1116 | api access deny | 密钥校验失败 |

### 异常处理示例

```python
try:
    response = client.get_answer(
        text="你好",
        open_id="user123"
    )
    
    if response.status != 0:
        print(f"API错误: {response.message}")
    else:
        print(f"成功: {response.data}")
        
except Exception as e:
    print(f"请求失败: {e}")
```

## 最佳实践

### 1. 连接管理

```python
# 使用上下文管理器
with WenxinAgentClient(config) as client:
    response = client.get_answer("你好", "user123")
    # 自动关闭连接

# 或手动管理
client = WenxinAgentClient(config)
try:
    response = client.get_answer("你好", "user123")
finally:
    client.close()
```

### 2. 多智能体管理

```python
from apps.common.wenxin_agent_client import WenxinAgentManager

with WenxinAgentManager() as manager:
    # 添加多个智能体
    client1 = manager.add_client("agent1", config1)
    client2 = manager.add_client("agent2", config2)
    
    # 使用不同智能体
    response1 = client1.get_answer("问题1", "user123")
    response2 = client2.get_answer("问题2", "user123")
    
    # 自动关闭所有连接
```

### 3. 流式响应处理

```python
def process_stream_response(client, text, user_id):
    """处理流式响应的完整示例"""
    full_text = ""
    thread_id = None
    
    try:
        for chunk in client.conversation_stream(text, user_id):
            # 检查状态
            if chunk.get('status') != 0:
                print(f"错误: {chunk.get('message')}")
                break
            
            # 获取消息数据
            message_data = chunk.get('data', {}).get('message', {})
            
            # 获取threadId
            if message_data.get('threadId'):
                thread_id = message_data['threadId']
            
            # 处理内容
            content_list = message_data.get('content', [])
            for content_item in content_list:
                if content_item.get('dataType') == 'markdown':
                    text_data = content_item.get('data', {}).get('text', '')
                    full_text += text_data
                    print(text_data, end='', flush=True)
            
            # 检查是否结束
            if message_data.get('endTurn'):
                break
                
    except Exception as e:
        print(f"流式处理错误: {e}")
    
    return full_text, thread_id
```

### 4. 错误重试策略

```python
import time
from functools import wraps

def retry_on_error(max_retries=3, delay=1):
    """错误重试装饰器"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if attempt == max_retries - 1:
                        raise
                    print(f"尝试 {attempt + 1} 失败: {e}")
                    time.sleep(delay * (2 ** attempt))
            return None
        return wrapper
    return decorator

@retry_on_error(max_retries=3)
def safe_chat(client, text, user_id):
    return client.get_answer(text, user_id)
```

## 性能优化

### 1. 连接池配置

```python
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# 自定义会话配置
session = requests.Session()

# 配置重试策略
retry_strategy = Retry(
    total=3,
    backoff_factor=1,
    status_forcelist=[429, 500, 502, 503, 504],
)

# 配置适配器
adapter = HTTPAdapter(
    max_retries=retry_strategy,
    pool_connections=10,
    pool_maxsize=20
)

session.mount("http://", adapter)
session.mount("https://", adapter)

# 在客户端中使用自定义会话
client._session = session
```

### 2. 缓存策略

```python
from functools import lru_cache
from datetime import datetime, timedelta

class CachedWenxinClient(WenxinAgentClient):
    """带缓存的文心智能体客户端"""
    
    def __init__(self, config):
        super().__init__(config)
        self._response_cache = {}
    
    @lru_cache(maxsize=100)
    def get_cached_response(self, text_hash, user_id):
        """缓存响应结果"""
        cache_key = f"{text_hash}_{user_id}"
        
        if cache_key in self._response_cache:
            cached_data, timestamp = self._response_cache[cache_key]
            # 缓存5分钟
            if datetime.now() - timestamp < timedelta(minutes=5):
                return cached_data
        
        return None
    
    def set_cached_response(self, text_hash, user_id, response):
        """设置缓存"""
        cache_key = f"{text_hash}_{user_id}"
        self._response_cache[cache_key] = (response, datetime.now())
```

## 安全注意事项

### 1. 密钥管理

```python
import os
from django.conf import settings

# 使用环境变量
config = WenxinConfig(
    client_id=os.getenv('WENXIN_CLIENT_ID'),
    client_secret=os.getenv('WENXIN_CLIENT_SECRET'),
    app_id=os.getenv('WENXIN_APP_ID'),
    secret_key=os.getenv('WENXIN_SECRET_KEY')
)

# 或使用Django设置（确保不提交到版本控制）
config = WenxinConfig(
    client_id=getattr(settings, 'WENXIN_CLIENT_ID'),
    client_secret=getattr(settings, 'WENXIN_CLIENT_SECRET'),
    app_id=getattr(settings, 'WENXIN_APP_ID'),
    secret_key=getattr(settings, 'WENXIN_SECRET_KEY')
)
```

### 2. 输入验证

```python
def validate_input(text, user_id):
    """输入验证"""
    if not text or len(text.strip()) == 0:
        raise ValueError("文本内容不能为空")
    
    if len(text) > 10000:  # 限制文本长度
        raise ValueError("文本内容过长")
    
    if not user_id or len(user_id) > 100:
        raise ValueError("用户ID无效")
    
    # 检查敏感词
    sensitive_words = ['敏感词1', '敏感词2']
    for word in sensitive_words:
        if word in text:
            raise ValueError(f"包含敏感词: {word}")
```

### 3. 限流控制

```python
import time
from collections import defaultdict

class RateLimiter:
    """简单的限流器"""
    
    def __init__(self, max_requests=10, time_window=60):
        self.max_requests = max_requests
        self.time_window = time_window
        self.requests = defaultdict(list)
    
    def is_allowed(self, user_id):
        """检查是否允许请求"""
        now = time.time()
        user_requests = self.requests[user_id]
        
        # 清理过期请求
        user_requests[:] = [req_time for req_time in user_requests 
                           if now - req_time < self.time_window]
        
        # 检查是否超限
        if len(user_requests) >= self.max_requests:
            return False
        
        # 记录当前请求
        user_requests.append(now)
        return True

# 使用限流器
rate_limiter = RateLimiter(max_requests=10, time_window=60)

def protected_chat(client, text, user_id):
    if not rate_limiter.is_allowed(user_id):
        raise Exception("请求过于频繁，请稍后再试")
    
    return client.get_answer(text, user_id)
```

## 故障排除

### 常见问题

1. **AccessToken获取失败**
   - 检查client_id和client_secret是否正确
   - 确认网络连接正常
   - 查看是否有防火墙限制

2. **API调用失败**
   - 检查app_id和secret_key是否正确
   - 确认智能体已发布上线
   - 检查请求参数格式

3. **流式响应中断**
   - 检查网络稳定性
   - 增加超时时间
   - 实现断线重连机制

4. **限流错误**
   - 检查请求频率
   - 实现退避重试
   - 考虑使用多个智能体分散请求

### 调试技巧

```python
import logging

# 启用详细日志
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger('apps.common.wenxin_agent_client')
logger.setLevel(logging.DEBUG)

# 添加请求日志
def log_request(method, url, **kwargs):
    logger.debug(f"请求: {method} {url}")
    logger.debug(f"参数: {kwargs}")

# 添加响应日志
def log_response(response):
    logger.debug(f"响应状态: {response.status_code}")
    logger.debug(f"响应内容: {response.text[:500]}...")  # 只记录前500字符
```

## 更新日志

### v1.0.0 (2024-12-19)
- 初始版本发布
- 支持AccessToken获取
- 支持getAnswer单次对话
- 支持conversation流式对话
- 提供Django集成示例
- 完整的错误处理和重试机制

## 许可证

MIT License

## 联系方式

如有问题或建议，请联系开发团队。