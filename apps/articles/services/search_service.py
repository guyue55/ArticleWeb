# -*- coding: utf-8 -*-
"""
联网搜索与热点发现服务
集成 Tavily Search API 获取实时热点并存入数据库
"""

import logging
from typing import List, Dict, Any, Optional
from tavily import TavilyClient
from django.conf import settings
from ..models import HotTrend, Category, SystemConfig

logger = logging.getLogger(__name__)

class SearchService:
    """联网搜索与热点发现服务"""

    def __init__(self, api_key: str = None):
        """
        初始化搜索服务
        
        Args:
            api_key: Tavily API Key，优先从参数获取，其次数据库，最后 settings
        """
        self.api_key = api_key or SystemConfig.get_value('TAVILY_API_KEY') or getattr(settings, 'TAVILY_API_KEY', None)
        self.client = TavilyClient(api_key=self.api_key) if self.api_key else None

    def discover_hot_trends(self, category_uuid: str, query: str = None) -> List[Dict[str, Any]]:
        """
        根据分类发现当前热门热点并存入数据库
        
        Args:
            category_uuid: 分类 UUID
            query: 搜索关键词，如果为空则根据分类名称自动生成
            
        Returns:
            List[Dict]: 发现的热点列表
        """
        if not self.client:
            logger.error("Tavily API Key 未配置，请在 settings.py 中设置 TAVILY_API_KEY")
            return []

        try:
            # 获取分类名称用于构建搜索词
            category = Category.objects.get(uuid=category_uuid)
            search_query = query or f"近期 {category.name} 领域热门选题 热点资讯"
            
            logger.info(f"正在为分类 {category.name} 搜索热点: {search_query}")
            
            # 调用 Tavily 搜索接口
            # include_answer=True 可以让 AI 自动生成一个简要回答
            response = self.client.search(
                query=search_query,
                search_depth="advanced",
                max_results=5,
                include_answer=True
            )
            
            results = []
            for result in response.get('results', []):
                # 创建热门选题记录
                trend = HotTrend.objects.create(
                    topic=result['title'],
                    source_urls=[{
                        'url': result['url'],
                        'title': result['title'],
                        'source': result.get('score', 'Search Result')
                    }],
                    summary=result.get('content', '')[:500],
                    category_uuid=category_uuid
                )
                
                results.append({
                    "id": trend.id,
                    "topic": trend.topic,
                    "sources": trend.source_urls,
                    "summary": trend.summary,
                    "discovery_time": trend.discovery_time
                })
                
            return results

        except Category.DoesNotExist:
            logger.error(f"分类 UUID {category_uuid} 不存在")
            return []
        except Exception as e:
            logger.error(f"热点发现失败: {type(e).__name__}")
            return []

    def get_trends_by_category(self, category_uuid: str, limit: int = 10) -> List[HotTrend]:
        """
        获取数据库中已有的热门选题
        
        Args:
            category_uuid: 分类 UUID
            limit: 返回数量限制
        """
        return HotTrend.objects.filter(
            category_uuid=category_uuid
        ).order_by('-discovery_time')[:limit]
