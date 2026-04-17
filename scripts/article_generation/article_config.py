from typing import Dict
from enum import Enum


class ArticleType(Enum):
    """
    文章类型枚举
    
    定义所有支持的文章类型，包含中文名称和英文目录名
    """
    WORKPLACE = ("职场", "workplace")
    LIFESTYLE = ("生活", "lifestyle")
    LIVELIHOOD = ("民生", "livelihood")
    AUTOMOTIVE = ("汽车", "automotive")
    ENTERTAINMENT = ("娱乐", "entertainment")
    EDUCATION = ("教育", "education")
    LOVE_LETTERS = ("情书", "love_letters")
    FOOD = ("美食", "food")
    TRAVEL = ("旅游", "travel")
    TRIVIA = ("冷知识", "trivia")
    DIARY = ("日记", "diary")
    
    def __init__(self, chinese_name: str, english_name: str):
        """
        初始化文章类型
        
        Args:
            chinese_name: 中文名称
            english_name: 英文目录名
        """
        self.chinese_name = chinese_name
        self.english_name = english_name
    
    @classmethod
    def get_chinese_names(cls) -> list[str]:
        """获取所有中文名称列表"""
        return [article_type.chinese_name for article_type in cls]
    
    @classmethod
    def get_english_names(cls) -> list[str]:
        """获取所有英文名称列表"""
        return [article_type.english_name for article_type in cls]
    
    @classmethod
    def get_type_mapping(cls) -> Dict[str, str]:
        """获取中文名称到英文名称的映射字典"""
        return {article_type.chinese_name: article_type.english_name for article_type in cls}
    
    @classmethod
    def get_reverse_mapping(cls) -> Dict[str, str]:
        """获取英文名称到中文名称的映射字典"""
        return {article_type.english_name: article_type.chinese_name for article_type in cls}
    
    @classmethod
    def from_chinese_name(cls, chinese_name: str) -> 'ArticleType':
        """
        根据中文名称获取文章类型枚举
        
        Args:
            chinese_name: 中文名称
            
        Returns:
            ArticleType: 对应的文章类型枚举
            
        Raises:
            ValueError: 如果找不到对应的文章类型
        """
        for article_type in cls:
            if article_type.chinese_name == chinese_name:
                return article_type
        raise ValueError(f"不支持的文章类型: {chinese_name}")
    
    @classmethod
    def from_english_name(cls, english_name: str) -> 'ArticleType':
        """
        根据英文名称获取文章类型枚举
        
        Args:
            english_name: 英文名称
            
        Returns:
            ArticleType: 对应的文章类型枚举
            
        Raises:
            ValueError: 如果找不到对应的文章类型
        """
        for article_type in cls:
            if article_type.english_name == english_name:
                return article_type
        raise ValueError(f"不支持的文章类型: {english_name}")
    
    def __str__(self) -> str:
        """返回中文名称作为字符串表示"""
        return self.chinese_name
    
    def __repr__(self) -> str:
        """返回详细的字符串表示"""
        return f"ArticleType(chinese_name='{self.chinese_name}', english_name='{self.english_name}')"