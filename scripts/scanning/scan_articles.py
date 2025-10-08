#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
文章扫描脚本

功能：
1. 扫描生成的文章目录 /d:/Project/Github/ArticleWeb/generated_articles/
2. 将生成的文章分类记录到数据库中（通过API接口 http://127.0.0.1:9000/）
3. 将文章分类存储到静态路径下用于下载 /d:/Project/Github/ArticleWeb/static/file/

作者: AI Assistant
创建时间: 2025-01-17
"""

import json
import shutil
import hashlib
import logging
import requests
import argparse
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from urllib.parse import urljoin

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('scan_articles.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class ArticleScanner:
    """文章扫描器类，负责扫描和处理生成的文章"""
    
    def __init__(self, 
                 generated_articles_dir: str = "generated_articles/",
                 static_files_dir: str = "static/file/",
                 api_base_url: str = "http://127.0.0.1:8000/api/"):
        """
        初始化文章扫描器
        
        Args:
            generated_articles_dir: 生成文章的目录路径
            static_files_dir: 静态文件存储目录路径
            api_base_url: API基础URL
        """
        self.generated_articles_dir = Path(generated_articles_dir)
        self.static_files_dir = Path(static_files_dir)
        self.api_base_url = api_base_url
        
        # 确保目录存在
        self.static_files_dir.mkdir(parents=True, exist_ok=True)
        
        # 分类映射表（英文目录名 -> 中文分类名）
        self.category_mapping = {
            'automotive': '汽车',
            'diary': '日记',
            'education': '教育',
            'entertainment': '娱乐',
            'food': '美食',
            'lifestyle': '生活',
            'livelihood': '民生',
            'love_letters': '情书',
            'travel': '旅游',
            'trivia': '冷知识',
            'workplace': '职场'
        }
        
        # 分类缓存
        self.category_cache = {}
        
        # 统计信息
        self.stats = {
            'total_found': 0,
            'total_processed': 0,
            'total_success': 0,
            'total_failed': 0,
            'categories': {}
        }
    
    def scan_articles(self) -> List[Dict]:
        """
        扫描生成的文章目录，获取所有文章信息
        
        Returns:
            文章信息列表
        """
        articles = []
        
        logger.info(f"开始扫描文章目录: {self.generated_articles_dir}")
        
        if not self.generated_articles_dir.exists():
            logger.error(f"文章目录不存在: {self.generated_articles_dir}")
            return articles
        
        # 遍历分类目录
        for category_dir in self.generated_articles_dir.iterdir():
            if not category_dir.is_dir():
                continue
                
            category_en = category_dir.name
            category_cn = self.category_mapping.get(category_en, category_en)
            
            logger.info(f"扫描分类: {category_en} ({category_cn})")
            
            # 遍历中文分类子目录
            for subcategory_dir in category_dir.iterdir():
                if not subcategory_dir.is_dir():
                    continue
                
                # 扫描该分类下的所有文章
                category_articles = self._scan_category_articles(
                    subcategory_dir, category_en, category_cn
                )
                articles.extend(category_articles)
                
                # 更新统计信息
                if category_cn not in self.stats['categories']:
                    self.stats['categories'][category_cn] = 0
                self.stats['categories'][category_cn] += len(category_articles)
        
        self.stats['total_found'] = len(articles)
        logger.info(f"扫描完成，共找到 {len(articles)} 篇文章")
        
        return articles
    
    def _scan_category_articles(self, category_dir: Path, category_en: str, category_cn: str) -> List[Dict]:
        """
        扫描指定分类目录下的所有文章
        
        Args:
            category_dir: 分类目录路径
            category_en: 英文分类名
            category_cn: 中文分类名
            
        Returns:
            该分类下的文章信息列表
        """
        articles = []
        
        # 查找所有 .meta 文件
        meta_files = list(category_dir.glob("*.meta"))
        
        for meta_file in meta_files:
            try:
                article_info = self._parse_article_meta(meta_file, category_en, category_cn)
                if article_info:
                    articles.append(article_info)
            except Exception as e:
                logger.error(f"解析文章元数据失败: {meta_file}, 错误: {e}")
        
        return articles
    
    def _parse_article_meta(self, meta_file: Path, category_en: str, category_cn: str) -> Optional[Dict]:
        """
        解析文章元数据文件
        
        Args:
            meta_file: 元数据文件路径
            category_en: 英文分类名
            category_cn: 中文分类名
            
        Returns:
            文章信息字典，如果解析失败返回None
        """
        try:
            with open(meta_file, 'r', encoding='utf-8') as f:
                meta_data = json.load(f)
            
            # 获取文章基本信息
            article_id = meta_data.get('article_id')
            title = meta_data.get('title')
            
            if not article_id or not title:
                logger.warning(f"文章元数据不完整: {meta_file}")
                return None
            
            # 查找对应的内容文件
            base_name = meta_file.stem
            md_file = meta_file.parent / f"{base_name}.md"
            html_file = meta_file.parent / f"{base_name}.html"
            
            # 读取文章内容
            content = ""
            content_file = None
            
            if md_file.exists():
                content_file = md_file
                with open(md_file, 'r', encoding='utf-8') as f:
                    content = f.read()
            elif html_file.exists():
                content_file = html_file
                with open(html_file, 'r', encoding='utf-8') as f:
                    content = f.read()
            else:
                logger.warning(f"找不到文章内容文件: {base_name}")
                return None
            
            # 生成文章摘要（取前200个字符）
            summary = self._generate_summary(content)
            
            # 生成唯一的slug
            slug = self._generate_slug(title, article_id)
            
            # 构建文章信息
            article_info = {
                'meta_file': str(meta_file),
                'content_file': str(content_file),
                'article_id': article_id,
                'title': title,
                'slug': slug,
                'summary': summary,
                'content': content,
                'category_en': category_en,
                'category_cn': category_cn,
                'word_count': meta_data.get('word_count', 0),
                'generated_at': meta_data.get('generated_at'),
                'topic': meta_data.get('topic', {}),
                'metadata': meta_data.get('metadata', {}),
                'files': meta_data.get('files', {})
            }
            
            return article_info
            
        except Exception as e:
            logger.error(f"解析文章元数据失败: {meta_file}, 错误: {e}")
            return None
    
    def _generate_summary(self, content: str, max_length: int = 200) -> str:
        """
        生成文章摘要
        
        Args:
            content: 文章内容
            max_length: 摘要最大长度
            
        Returns:
            文章摘要
        """
        # 移除markdown标记和HTML标签
        import re
        
        # 移除markdown标题标记
        content = re.sub(r'^#+\s*', '', content, flags=re.MULTILINE)
        # 移除HTML标签
        content = re.sub(r'<[^>]+>', '', content)
        # 移除多余的空白字符
        content = re.sub(r'\s+', ' ', content).strip()
        
        # 截取前max_length个字符作为摘要
        if len(content) > max_length:
            summary = content[:max_length] + "..."
        else:
            summary = content
        
        return summary
    
    def _generate_slug(self, title: str, article_id: str) -> str:
        """
        生成文章slug
        
        Args:
            title: 文章标题
            article_id: 文章ID
            
        Returns:
            文章slug
        """
        # 使用文章ID和标题的哈希值生成唯一slug
        title_hash = hashlib.md5(title.encode('utf-8')).hexdigest()[:8]
        return f"{article_id}-{title_hash}"
    
    def load_categories_cache(self) -> bool:
        """
        加载分类缓存
        
        Returns:
            是否加载成功
        """
        try:
            url = urljoin(self.api_base_url, "articles/meta/categories")
            response = requests.get(url, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                if data.get('code') == 0:
                    categories = data.get('data', [])
                    
                    # 构建缓存：按名称和slug索引
                    for category in categories:
                        name = category.get('name')
                        slug = category.get('slug')
                        category_id = category.get('id')
                        
                        if name:
                            self.category_cache[name] = category_id
                        if slug:
                            self.category_cache[slug] = category_id
                    
                    logger.info(f"分类缓存加载成功，共 {len(categories)} 个分类")
                    return True
            
            logger.error(f"加载分类失败: HTTP {response.status_code}")
            return False
            
        except Exception as e:
            logger.error(f"加载分类缓存失败: {e}")
            return False

    def get_or_create_category(self, category_name: str) -> Optional[int]:
        """
        获取或创建分类
        
        Args:
            category_name: 分类名称
            
        Returns:
            分类ID，如果失败返回None
        """
        try:
            # 如果缓存为空，先加载缓存
            if not self.category_cache:
                if not self.load_categories_cache():
                    return None
            
            # 直接查找分类名称
            if category_name in self.category_cache:
                return self.category_cache[category_name]
            
            # 查找对应的英文slug
            english_slug = None
            for eng, chn in self.category_mapping.items():
                if chn == category_name:
                    english_slug = eng
                    break
            
            if english_slug and english_slug in self.category_cache:
                return self.category_cache[english_slug]
            
            # 如果都找不到，使用第一个可用的分类作为默认分类
            if self.category_cache:
                # 优先使用已知的分类
                for known_category in self.category_mapping.values():
                    if known_category in self.category_cache:
                        category_id = self.category_cache[known_category]
                        logger.warning(f"分类 '{category_name}' 不存在，使用默认分类 '{known_category}' (ID: {category_id})")
                        return category_id
                
                # 如果没有已知分类，使用任意一个分类
                first_category_id = next(iter(self.category_cache.values()))
                logger.warning(f"分类 '{category_name}' 不存在，使用第一个可用分类 (ID: {first_category_id})")
                return first_category_id
            
            logger.error(f"无法获取任何分类，请检查数据库中是否存在分类数据")
            return None
            
        except Exception as e:
            logger.error(f"获取分类失败: {category_name}, 错误: {e}")
            return None
    
    def create_article_via_api(self, article_info: Dict) -> bool:
        """
        通过API创建文章
        
        Args:
            article_info: 文章信息字典
            
        Returns:
            是否创建成功
        """
        try:
            # 获取或创建分类
            category_id = self.get_or_create_category(article_info['category_cn'])
            if not category_id:
                logger.error(f"无法获取分类ID: {article_info['category_cn']}")
                return False
            
            # 构建API请求数据 - 使用正确的字段名
            api_data = {
                'title': article_info['title'],
                'slug': article_info['slug'],
                'summary': article_info['summary'],
                'content': article_info['content'],
                'category_id': category_id,
                'status': 2,  # 已发布
                'is_featured': False,
                'is_top': False,
                'is_downloadable': True,  # 设置为可下载
                'file_info': article_info.get('copied_files', {})  # 保存文件信息
            }
            
            # 发送API请求 - 使用任意token，API会自动创建测试用户
            url = urljoin(self.api_base_url, "articles/")
            headers = {
                'Authorization': 'Bearer any-token',  # API会自动处理认证
                'Content-Type': 'application/json'
            }
            
            logger.info(f"正在创建文章: {article_info['title']}")
            logger.debug(f"API URL: {url}")
            logger.debug(f"API数据: {api_data}")
            
            response = requests.post(url, json=api_data, headers=headers, timeout=30)
            
            logger.debug(f"API响应状态: {response.status_code}")
            logger.debug(f"API响应内容: {response.text[:500]}...")
            
            if response.status_code == 200:
                data = response.json()
                if data.get('code') == 0:  # API成功时返回code: 0
                    logger.info(f"文章创建成功: {article_info['title']}")
                    return True
                else:
                    logger.error(f"API返回错误: {data.get('message', '未知错误')}")
                    logger.error(f"完整响应: {data}")
                    return False
            else:
                logger.error(f"API请求失败: {response.status_code}")
                logger.error(f"响应内容: {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"创建文章失败: {article_info['title']}, 错误: {e}")
            import traceback
            logger.error(f"详细错误信息: {traceback.format_exc()}")
            return False
    
    def copy_article_to_static(self, article_info: Dict) -> Optional[Dict[str, str]]:
        """
        将文章文件复制到静态目录，包括MD/HTML文件和.meta文件
        
        Args:
            article_info: 文章信息字典
            
        Returns:
            包含各文件相对路径的字典，如果失败返回None
        """
        try:
            # 创建分类目录
            category_dir = self.static_files_dir / article_info['category_en']
            category_dir.mkdir(parents=True, exist_ok=True)
            
            copied_files = {}
            
            # 复制主要内容文件（MD或HTML）
            source_file = Path(article_info['content_file'])
            target_filename = f"{article_info['article_id']}{source_file.suffix}"
            target_file = category_dir / target_filename
            shutil.copy2(source_file, target_file)
            
            # 记录主要内容文件路径
            main_file_path = f"file/{article_info['category_en']}/{target_filename}"
            copied_files['main'] = main_file_path
            logger.info(f"主要文件已复制: {main_file_path}")
            
            # 复制.meta文件
            meta_source = Path(article_info['meta_file'])
            meta_target_filename = f"{article_info['article_id']}.meta"
            meta_target_file = category_dir / meta_target_filename
            shutil.copy2(meta_source, meta_target_file)
            
            meta_file_path = f"file/{article_info['category_en']}/{meta_target_filename}"
            copied_files['meta'] = meta_file_path
            logger.info(f"元数据文件已复制: {meta_file_path}")
            
            # 查找并复制对应的HTML文件（如果主文件是MD）
            base_name = meta_source.stem
            if source_file.suffix.lower() == '.md':
                html_source = meta_source.parent / f"{base_name}.html"
                if html_source.exists():
                    html_target_filename = f"{article_info['article_id']}.html"
                    html_target_file = category_dir / html_target_filename
                    shutil.copy2(html_source, html_target_file)
                    
                    html_file_path = f"file/{article_info['category_en']}/{html_target_filename}"
                    copied_files['html'] = html_file_path
                    logger.info(f"HTML文件已复制: {html_file_path}")
            
            # 查找并复制对应的MD文件（如果主文件是HTML）
            elif source_file.suffix.lower() == '.html':
                md_source = meta_source.parent / f"{base_name}.md"
                if md_source.exists():
                    md_target_filename = f"{article_info['article_id']}.md"
                    md_target_file = category_dir / md_target_filename
                    shutil.copy2(md_source, md_target_file)
                    
                    md_file_path = f"file/{article_info['category_en']}/{md_target_filename}"
                    copied_files['md'] = md_file_path
                    logger.info(f"Markdown文件已复制: {md_file_path}")
            
            return copied_files
            
        except Exception as e:
            logger.error(f"复制文章文件失败: {article_info['title']}, 错误: {e}")
            return None
    
    def process_articles(self, articles: List[Dict], dry_run: bool = False) -> None:
        """
        处理文章列表
        
        Args:
            articles: 文章信息列表
            dry_run: 是否为试运行模式
        """
        logger.info(f"开始处理 {len(articles)} 篇文章 (试运行: {dry_run})")
        
        for i, article_info in enumerate(articles, 1):
            logger.info(f"处理文章 {i}/{len(articles)}: {article_info['title']}")
            
            self.stats['total_processed'] += 1
            
            if dry_run:
                logger.info(f"[试运行] 跳过实际处理: {article_info['title']}")
                self.stats['total_success'] += 1
                continue
            
            try:
                # 复制文章到静态目录
                copied_files = self.copy_article_to_static(article_info)
                if not copied_files:
                    self.stats['total_failed'] += 1
                    continue
                
                # 将复制的文件信息添加到文章信息中
                article_info['copied_files'] = copied_files
                
                # 通过API创建文章记录
                if self.create_article_via_api(article_info):
                    self.stats['total_success'] += 1
                    logger.info(f"文章处理成功: {article_info['title']}")
                    logger.info(f"已复制文件: {list(copied_files.keys())}")
                else:
                    self.stats['total_failed'] += 1
                    logger.error(f"文章处理失败: {article_info['title']}")
                
            except Exception as e:
                self.stats['total_failed'] += 1
                logger.error(f"处理文章时发生异常: {article_info['title']}, 错误: {e}")
    
    def print_statistics(self) -> None:
        """打印统计信息"""
        logger.info("=" * 50)
        logger.info("处理统计信息:")
        logger.info(f"发现文章总数: {self.stats['total_found']}")
        logger.info(f"处理文章总数: {self.stats['total_processed']}")
        logger.info(f"成功处理数量: {self.stats['total_success']}")
        logger.info(f"失败处理数量: {self.stats['total_failed']}")
        logger.info("")
        logger.info("分类统计:")
        for category, count in self.stats['categories'].items():
            logger.info(f"  {category}: {count} 篇")
        logger.info("=" * 50)


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='文章扫描和导入脚本')
    parser.add_argument('--generated-dir', 
                       default='generated_articles/',
                       help='生成文章的目录路径')
    parser.add_argument('--static-dir', 
                       default='static/file/',
                       help='静态文件存储目录路径')
    parser.add_argument('--api-url', 
                       default='http://127.0.0.1:9000/api/',
                       help='API基础URL')
    parser.add_argument('--dry-run', 
                       action='store_true',
                       help='试运行模式，不实际执行操作')
    parser.add_argument('--category', 
                       help='只处理指定分类的文章')
    parser.add_argument('--limit', 
                       type=int,
                       help='限制处理的文章数量')
    
    args = parser.parse_args()
    
    # 创建扫描器实例
    scanner = ArticleScanner(
        generated_articles_dir=args.generated_dir,
        static_files_dir=args.static_dir,
        api_base_url=args.api_url
    )
    
    try:
        # 扫描文章
        articles = scanner.scan_articles()
        
        if not articles:
            logger.warning("没有找到任何文章")
            return
        
        # 如果指定了分类，过滤文章
        if args.category:
            articles = [a for a in articles if a['category_cn'] == args.category]
            logger.info(f"过滤后剩余 {len(articles)} 篇文章 (分类: {args.category})")
        
        # 如果指定了限制数量，截取文章
        if args.limit:
            articles = articles[:args.limit]
            logger.info(f"限制处理数量为 {args.limit} 篇文章")
        
        # 处理文章
        scanner.process_articles(articles, dry_run=args.dry_run)
        
        # 打印统计信息
        scanner.print_statistics()
        
    except KeyboardInterrupt:
        logger.info("用户中断操作")
    except Exception as e:
        logger.error(f"程序执行失败: {e}")
        raise


if __name__ == '__main__':
    main()