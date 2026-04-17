# -*- coding: utf-8 -*-
"""
文心智能体平台 API 客户端

基于官方API文档开发，支持：
1. AccessToken 获取
2. getAnswer 单次对话
3. conversation 流式对话

官方文档：https://agentapi.baidu.com/
"""

import json
import time
from typing import Dict, Any, Optional, List, Generator, Union
from dataclasses import dataclass
from datetime import datetime, timedelta
import logging

import requests

logger = logging.getLogger(__name__)


@dataclass
class WenxinConfig:
    """文心智能体配置类"""
    client_id: str  # 应用的API Key
    client_secret: str  # 应用的Secret Key
    app_id: str=None  # 智能体ID
    secret_key: str=None  # 智能体Secret Key
    timeout: int = 30  # 请求超时时间
    max_retries: int = 3  # 最大重试次数


@dataclass
class MessageContent:
    """消息内容类"""
    type: str  # text, image, file, multimodal
    value: Union[Dict[str, Any], List[Dict[str, Any]]]
    isFirstConversation: Optional[bool] = None  # 仅text类型使用


@dataclass
class ChatMessage:
    """对话消息类"""
    content: MessageContent


@dataclass
class ConversationRequest:
    """流式对话请求类"""
    message: ChatMessage
    source: str  # 智能体ID
    from_: str = "openapi"  # 固定值
    openId: str = ""  # 外部用户ID
    threadId: Optional[str] = None  # 会话ID

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        data = {
            "message": {
                "content": {
                    "type": self.message.content.type,
                    "value": self.message.content.value
                }
            },
            "source": self.source,
            "from": self.from_,
            "openId": self.openId
        }
        
        if self.message.content.isFirstConversation is not None:
            data["message"]["content"]["isFirstConversation"] = self.message.content.isFirstConversation
            
        if self.threadId:
            data["threadId"] = self.threadId
            
        return data


@dataclass
class GetAnswerRequest:
    """getAnswer请求类"""
    message: ChatMessage
    source: str  # 智能体ID
    from_: str = "openapi"  # 固定值
    openId: str = ""  # 外部用户ID
    threadId: Optional[str] = None  # 会话ID

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        data = {
            "message": {
                "content": {
                    "type": self.message.content.type,
                    "value": self.message.content.value
                }
            },
            "source": self.source,
            "from": self.from_,
            "openId": self.openId
        }
        
        if self.message.content.isFirstConversation is not None:
            data["message"]["content"]["isFirstConversation"] = self.message.content.isFirstConversation
            
        if self.threadId:
            data["threadId"] = self.threadId
            
        return data


@dataclass
class ApiResponse:
    """API响应基类"""
    status: int
    message: str
    logid: str
    data: Optional[Dict[str, Any]] = None


class WenxinAgentClient:
    """文心智能体API客户端"""
    
    def __init__(self, config: WenxinConfig):
        self.config = config
        self._access_token = None
        self._token_expires_at = None
        self._session = requests.Session()
        
        # 设置默认请求头
        self._session.headers.update({
            'User-Agent': 'WenxinAgentClient/1.0',
            'Accept': 'application/json'
        })
    
    def get_access_token(self, force_refresh: bool = False) -> str:
        """
        获取AccessToken
        
        Args:
            force_refresh: 是否强制刷新token
            
        Returns:
            str: access_token
            
        Raises:
            Exception: 获取token失败时抛出异常
        """
        # 检查是否需要刷新token
        if not force_refresh and self._access_token and self._token_expires_at:
            if datetime.now() < self._token_expires_at - timedelta(minutes=5):  # 提前5分钟刷新
                return self._access_token
        
        url = "https://openapi.baidu.com/oauth/2.0/token"
        params = {
            "grant_type": "client_credentials",
            "client_id": self.config.client_id,
            "client_secret": self.config.client_secret
        }
        
        try:
            response = self._session.get(
                url, 
                params=params, 
                timeout=self.config.timeout
            )
            response.raise_for_status()
            
            data = response.json()
            
            if "access_token" not in data:
                raise Exception(f"获取access_token失败: {data}")
            
            self._access_token = data["access_token"]
            expires_in = data.get("expires_in", 2592000)  # 默认30天
            self._token_expires_at = datetime.now() + timedelta(seconds=expires_in)
            
            logger.info(f"AccessToken获取成功，有效期至: {self._token_expires_at}")
            return self._access_token
            
        except requests.RequestException as e:
            logger.error(f"获取AccessToken网络请求失败: {e}")
            raise Exception(f"获取AccessToken失败: {e}")
        except Exception as e:
            logger.error(f"获取AccessToken失败: {e}")
            raise
    
    def _make_request(self, method: str, url: str, **kwargs) -> requests.Response:
        """
        发起HTTP请求的通用方法
        
        Args:
            method: HTTP方法
            url: 请求URL
            **kwargs: 其他请求参数
            
        Returns:
            requests.Response: 响应对象
        """
        for attempt in range(self.config.max_retries):
            try:
                response = self._session.request(
                    method=method,
                    url=url,
                    timeout=self.config.timeout,
                    **kwargs
                )
                response.raise_for_status()
                return response
                
            except requests.RequestException as e:
                logger.warning(f"请求失败 (尝试 {attempt + 1}/{self.config.max_retries}): {e}")
                if attempt == self.config.max_retries - 1:
                    raise Exception(f"请求失败，已重试{self.config.max_retries}次: {e}")
                time.sleep(2 ** attempt)  # 指数退避
    
    def get_answer(self, 
                   text: str, 
                   open_id: str,
                   thread_id: Optional[str] = None,
                   is_first_conversation: bool = False) -> ApiResponse:
        """
        调用getAnswer接口进行单次对话
        
        Args:
            text: 用户输入的文本
            open_id: 外部用户ID
            thread_id: 会话ID，可选
            is_first_conversation: 是否为首次对话
            
        Returns:
            ApiResponse: API响应
        """
        # 构建消息内容
        message_content = MessageContent(
            type="text",
            value={"showText": text},
            isFirstConversation=is_first_conversation
        )
        
        chat_message = ChatMessage(content=message_content)
        
        request_data = GetAnswerRequest(
            message=chat_message,
            source=self.config.app_id,
            openId=open_id,
            threadId=thread_id
        )
        
        url = f"https://agentapi.baidu.com/assistant/getAnswer"
        params = {
            "appId": self.config.app_id,
            "secretKey": self.config.secret_key
        }
        
        headers = {
            "Content-Type": "application/json"
        }
        
        try:
            response = self._make_request(
                method="POST",
                url=url,
                params=params,
                headers=headers,
                json=request_data.to_dict()
            )
            
            data = response.json()
            return ApiResponse(
                status=data.get("status", 0),
                message=data.get("message", "success"),
                logid=data.get("logid", ""),
                data=data.get("data")
            )
            
        except Exception as e:
            logger.error(f"getAnswer请求失败: {e}")
            raise
    
    def conversation_stream(self, 
                           text: str, 
                           open_id: str,
                           thread_id: Optional[str] = None,
                           is_first_conversation: bool = False,
                           stream_timeout: Optional[int] = None) -> Generator[Dict[str, Any], None, None]:
        """
        调用conversation接口进行流式对话
        
        Args:
            text: 用户输入的文本
            open_id: 外部用户ID
            thread_id: 会话ID，可选
            is_first_conversation: 是否为首次对话
            stream_timeout: 流式响应超时时间（秒），默认使用配置中的timeout
            
        Yields:
            Dict[str, Any]: 流式响应数据
        """
        # 构建消息内容
        message_content = MessageContent(
            type="text",
            value={"showText": text},
            isFirstConversation=is_first_conversation
        )
        
        chat_message = ChatMessage(content=message_content)
        
        request_data = ConversationRequest(
            message=chat_message,
            source=self.config.app_id,
            openId=open_id,
            threadId=thread_id
        )
        
        url = f"https://agentapi.baidu.com/assistant/conversation"
        params = {
            "appId": self.config.app_id,
            "secretKey": self.config.secret_key
        }
        
        headers = {
            "Content-Type": "application/json",
            "Accept": "text/event-stream",
            "Cache-Control": "no-cache",
            "Connection": "keep-alive"
        }
        
        # 使用更长的超时时间用于流式响应
        timeout = stream_timeout or (self.config.timeout * 3)  # 默认3倍超时时间
        
        for attempt in range(self.config.max_retries):
            try:
                logger.info(f"开始流式对话请求 (尝试 {attempt + 1}/{self.config.max_retries})")
                
                response = self._session.post(
                    url=url,
                    params=params,
                    headers=headers,
                    json=request_data.to_dict(),
                    stream=True,
                    timeout=(10, timeout)  # (连接超时, 读取超时)
                )
                
                # 检查HTTP状态码
                if response.status_code == 499:
                    logger.warning(f"收到499状态码，可能是服务端超时，尝试重试 (尝试 {attempt + 1}/{self.config.max_retries})")
                    if attempt < self.config.max_retries - 1:
                        time.sleep(2 ** attempt)  # 指数退避
                        continue
                
                response.raise_for_status()
                
                # 解析SSE流
                has_data = False
                for line in response.iter_lines(decode_unicode=True, chunk_size=1024):
                    if not line:
                        continue
                        
                    line = line.strip()
                    
                    # 处理SSE事件
                    if line.startswith("event:"):
                        event_type = line[6:].strip()
                        logger.debug(f"收到SSE事件: {event_type}")
                        continue
                    elif line.startswith("data:"):
                        data_str = line[5:].strip()
                        if data_str:
                            try:
                                data = json.loads(data_str)
                                has_data = True
                                yield data
                                
                                # 检查是否有错误状态
                                if data.get('status', 0) != 0:
                                    logger.warning(f"API返回错误状态: {data.get('status')}, 消息: {data.get('message')}")
                                    return
                                    
                                # 检查是否结束（确保data字段存在且不为None）
                                response_data = data.get('data')
                                if response_data:
                                    message_data = response_data.get('message', {})
                                    if message_data.get('endTurn', False):
                                        logger.info("流式对话正常结束")
                                        return
                                    
                            except json.JSONDecodeError as e:
                                logger.warning(f"解析SSE数据失败: {e}, 数据: {data_str[:100]}...")
                                continue
                
                # 如果成功处理了数据，则退出重试循环
                if has_data:
                    return
                else:
                    logger.warning(f"未收到有效数据，尝试重试 (尝试 {attempt + 1}/{self.config.max_retries})")
                    if attempt < self.config.max_retries - 1:
                        time.sleep(2 ** attempt)
                        continue
                        
            except requests.exceptions.Timeout as e:
                logger.warning(f"流式请求超时 (尝试 {attempt + 1}/{self.config.max_retries}): {e}")
                if attempt < self.config.max_retries - 1:
                    time.sleep(2 ** attempt)
                    continue
                else:
                    raise Exception(f"流式对话超时，已重试{self.config.max_retries}次: {e}")
                    
            except requests.exceptions.HTTPError as e:
                if e.response.status_code == 499:
                    logger.warning(f"收到499错误，可能是服务端处理超时 (尝试 {attempt + 1}/{self.config.max_retries})")
                    if attempt < self.config.max_retries - 1:
                        time.sleep(2 ** attempt)
                        continue
                    else:
                        raise Exception(f"流式对话失败，服务端返回499错误，已重试{self.config.max_retries}次")
                else:
                    logger.error(f"HTTP错误: {e}")
                    raise
                    
            except requests.exceptions.ConnectionError as e:
                logger.warning(f"连接错误 (尝试 {attempt + 1}/{self.config.max_retries}): {e}")
                if attempt < self.config.max_retries - 1:
                    time.sleep(2 ** attempt)
                    continue
                else:
                    raise Exception(f"连接失败，已重试{self.config.max_retries}次: {e}")
                    
            except Exception as e:
                logger.error(f"conversation流式请求失败 (尝试 {attempt + 1}/{self.config.max_retries}): {e}")
                if attempt < self.config.max_retries - 1:
                    time.sleep(2 ** attempt)
                    continue
                else:
                    raise
    
    def create_text_message(self, text: str, is_first_conversation: bool = False) -> ChatMessage:
        """
        创建文本消息
        
        Args:
            text: 文本内容
            is_first_conversation: 是否为首次对话
            
        Returns:
            ChatMessage: 聊天消息对象
        """
        content = MessageContent(
            type="text",
            value={"showText": text},
            isFirstConversation=is_first_conversation
        )
        return ChatMessage(content=content)
    
    def create_image_message(self, 
                            image_url: str, 
                            image_name: str = "",
                            image_type: str = "png",
                            image_size: int = 0) -> ChatMessage:
        """
        创建图片消息
        
        Args:
            image_url: 图片URL
            image_name: 图片名称
            image_type: 图片类型
            image_size: 图片大小
            
        Returns:
            ChatMessage: 聊天消息对象
        """
        content = MessageContent(
            type="image",
            value={
                "imageUrl": image_url,
                "imageName": image_name,
                "imageType": image_type,
                "imageSize": image_size
            }
        )
        return ChatMessage(content=content)
    
    def create_file_message(self, 
                           file_id: str,
                           file_url: str, 
                           file_name: str,
                           file_type: str,
                           file_size: int) -> ChatMessage:
        """
        创建文件消息
        
        Args:
            file_id: 文件ID
            file_url: 文件URL
            file_name: 文件名称
            file_type: 文件类型
            file_size: 文件大小
            
        Returns:
            ChatMessage: 聊天消息对象
        """
        content = MessageContent(
            type="file",
            value={
                "fileId": file_id,
                "fileUrl": file_url,
                "fileName": file_name,
                "fileType": file_type,
                "fileSize": file_size
            }
        )
        return ChatMessage(content=content)
    
    def extract_stream_text(self, stream_data: Dict[str, Any]) -> str:
        """
        从流式响应数据中提取文本内容
        
        Args:
            stream_data: 流式响应数据
            
        Returns:
            str: 提取的文本内容
        """
        text_content = ""
        
        # 检查data字段是否存在且不为None
        data = stream_data.get('data')
        if not data:
            return text_content
            
        # 获取消息内容
        message_data = data.get('message', {})
        content_list = message_data.get('content', [])
        
        if isinstance(content_list, list):
            for content_item in content_list:
                if isinstance(content_item, dict):
                    # 处理txt类型内容
                    if content_item.get('dataType') == 'txt':
                        text = content_item.get('data', '')
                        if text:
                            text_content += text
                    # 处理markdown类型内容
                    elif content_item.get('dataType') == 'markdown':
                        data_obj = content_item.get('data', {})
                        if isinstance(data_obj, dict) and 'text' in data_obj:
                            text = data_obj['text']
                            if text:
                                text_content += text
        
        return text_content
    
    def is_stream_finished(self, stream_data: Dict[str, Any]) -> bool:
        """
        检查流式响应是否已结束
        
        Args:
            stream_data: 流式响应数据
            
        Returns:
            bool: 是否已结束
        """
        data = stream_data.get('data')
        if not data:
            return False
            
        message_data = data.get('message', {})
        return message_data.get('endTurn', False)
    
    def conversation_complete(self, 
                            text: str, 
                            open_id: str,
                            thread_id: Optional[str] = None,
                            is_first_conversation: bool = False,
                            stream_timeout: Optional[int] = None) -> str:
        """
        调用conversation接口进行流式对话并返回完整回答
        
        Args:
            text: 用户输入的文本
            open_id: 外部用户ID
            thread_id: 会话ID，可选
            is_first_conversation: 是否为首次对话
            stream_timeout: 流式响应超时时间（秒），默认使用配置中的timeout
            
        Returns:
            str: 完整的回答文本
            
        Raises:
            Exception: 当流式对话失败时抛出异常
        """
        complete_response = ""
        chunk_count = 0
        try:
            for chunk in self.conversation_stream(
                text=text,
                open_id=open_id,
                thread_id=thread_id,
                is_first_conversation=is_first_conversation,
                stream_timeout=stream_timeout
            ):
                # 提取文本内容
                text_content = self.extract_stream_text(chunk)
                if text_content:
                    complete_response += text_content
                    chunk_count += 1
                    # logger.info(f"收到第{chunk_count}个数据块: {chunk}")
                    logger.info(f"收到第{chunk_count}个数据块....")
                
                # 检查是否结束
                if self.is_stream_finished(chunk):
                    break
            logger.info(f"\n流式对话完成，共收到{chunk_count}个数据块")
            
            return complete_response
            
        except Exception as e:
            logger.error(f"流式对话获取完整回答失败: {e}")
            raise Exception(f"获取完整回答失败: {e}")
    
    def close(self):
        """关闭客户端连接"""
        if self._session:
            self._session.close()
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


class WenxinAgentManager:
    """文心智能体管理器，支持多个智能体实例"""
    
    def __init__(self):
        self._clients: Dict[str, WenxinAgentClient] = {}
    
    def add_client(self, name: str, config: WenxinConfig) -> WenxinAgentClient:
        """
        添加智能体客户端
        
        Args:
            name: 客户端名称
            config: 配置对象
            
        Returns:
            WenxinAgentClient: 客户端实例
        """
        client = WenxinAgentClient(config)
        self._clients[name] = client
        return client
    
    def get_client(self, name: str) -> Optional[WenxinAgentClient]:
        """
        获取智能体客户端
        
        Args:
            name: 客户端名称
            
        Returns:
            Optional[WenxinAgentClient]: 客户端实例
        """
        return self._clients.get(name)
    
    def remove_client(self, name: str) -> bool:
        """
        移除智能体客户端
        
        Args:
            name: 客户端名称
            
        Returns:
            bool: 是否成功移除
        """
        if name in self._clients:
            self._clients[name].close()
            del self._clients[name]
            return True
        return False
    
    def close_all(self):
        """关闭所有客户端"""
        for client in self._clients.values():
            client.close()
        self._clients.clear()
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close_all()


# 使用示例
if __name__ == "__main__":
    # 配置日志
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    
    # 配置信息
    config = WenxinConfig(
        client_id="ag98c7R9xxx",
        client_secret="qhAkdGHKWuxxxx",
        app_id="ag98c7R9xxx",
        secret_key="qhAkdGHKWuxxxx",
        timeout=30,
        max_retries=3
    )

    text = """
    你是一名资深的职场专栏作者，根据提供的背景、性格特点、写作原则等，帮助用户解决职场问题根据提供的背景、性格特点、写作原则等，
    写一篇关于”大半夜接到前领导电话，说帮他证明下工作经历，我想都没想就拒了，结果第二天HR在发消息问我，说前领导想进我们公司，你觉得他人咋样？”这个主题的文章。
    要求：
    - 字数不少于1800字- 使用markdown格式
    - 第一人称视角- 按照给定的文章结构写作- 包含开头(300字)、主体故事(500字)、分析部分(800字)、结尾(300字)
    - 要融入指定的口头禅和语言风格
    """
    
    # 创建客户端
    with WenxinAgentClient(config) as client:
        # try:
        #     # 获取AccessToken
        #     token = client.get_access_token()
        #     print(f"AccessToken获取成功: {token[:20]}...")
            
        #     # 单次对话
        #     print("\n=== 单次对话测试 ===")
        #     response = client.get_answer(
        #         text="你好，请介绍一下自己",
        #         open_id="user123"
        #     )
        #     print(f"单次对话响应: {response}")
            
        # except Exception as e:
        #     print(f"单次对话失败: {e}")
        
        # try:
        #     # 流式对话
        #     print("\n=== 流式对话测试 ===")
        #     response_text = ""
        #     chunk_count = 0
            
        #     for chunk in client.conversation_stream(
        #         text="请简单介绍一下Python编程语言的特点",
        #         open_id="user123",
        #         stream_timeout=60  # 设置更长的超时时间
        #     ):
        #         chunk_count += 1
        #         print(f"收到第{chunk_count}个数据块: {chunk}")
                
        #         # 使用辅助方法提取文本内容
        #         text_content = client.extract_stream_text(chunk)
        #         if text_content:
        #             response_text += text_content
        #             print(f"提取到文本: {text_content}")
        #             print(f"累积文本: {response_text}")
                
        #         # 检查是否结束
        #         if client.is_stream_finished(chunk):
        #             print("流式对话正常结束")
        #             break
            
        #     print(f"\n流式对话完成，共收到{chunk_count}个数据块")
        #     print(f"完整回复: {response_text}")
            
        # except Exception as e:
        #     print(f"流式对话失败: {e}")
        #     print("这可能是由于网络超时、服务端处理时间过长或其他网络问题导致的")
        #     print("建议检查网络连接或稍后重试")
        
        try:
            # 完整流式对话（一次获取完整回答）
            print("\n=== 完整流式对话测试 ===")
            complete_answer = client.conversation_complete(
                # text="请用一句话总结Python的主要优势",
                text=text,
                open_id="user123",
                stream_timeout=60
            )
            print(f"完整回答: {complete_answer}")
            
        except Exception as e:
            print(f"完整流式对话失败: {e}")