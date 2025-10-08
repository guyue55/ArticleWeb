"""文章扫描Django管理命令

该命令用于扫描生成的文章目录，将文章数据导入到数据库中，
并将文章文件复制到静态文件目录供下载使用。

使用方法:
    python manage.py scan_articles
    python manage.py scan_articles --generated-dir /path/to/articles
    python manage.py scan_articles --static-dir /path/to/static
    python manage.py scan_articles --dry-run
"""

import os
import json
import re
import shutil
import hashlib
from pathlib import Path
from typing import Dict, List, Optional

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone
from django.conf import settings
from django.contrib.auth import get_user_model
from loguru import logger

from apps.articles.models import Article, Category


User = get_user_model()


class Command(BaseCommand):
    """文章扫描Django管理命令类"""
    
    help = '扫描生成的文章目录，将文章数据导入到数据库中'
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
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
        # 分类映射表（中文分类名 -> 英文目录名）
        self.category_map = {
            value: key for key, value in self.category_mapping.items()
        }
        
        # 分类缓存
        self.category_cache = {}
        
        # 默认作者
        self.default_author = None
        
        # 统计信息
        self.stats = {
            'total_found': 0,
            'total_processed': 0,
            'total_success': 0,
            'total_failed': 0,
            'categories': {}
        }
        
        # 扫描文件处理配置
        self.scanned_file_action = os.getenv('SCANNED_FILE_ACTION', 'move').lower()
        self.ignore_back_directory = os.getenv('IGNORE_BACK_DIRECTORY', 'True').lower() == 'true'
        self.back_directory_name = 'Back'
    
    def add_arguments(self, parser):
        """添加命令行参数"""
        parser.add_argument(
            '--generated-dir',
            type=str,
            default=getattr(settings, 'ARTICLE_GENERATED_DIR', ''),
            help='生成文章的目录路径（默认从settings.ARTICLE_GENERATED_DIR读取）'
        )
        
        parser.add_argument(
            '--static-dir',
            type=str,
            default=getattr(settings, 'ARTICLE_STATIC_DIR', ''),
            help='静态文件存储目录路径（默认从settings.ARTICLE_STATIC_DIR读取）'
        )
        
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='试运行模式，不实际修改数据库和文件'
        )
        
        parser.add_argument(
            '--task-name',
            type=str,
            default=f'scan_articles_{timezone.now().strftime("%Y%m%d_%H%M%S")}',
            help='扫描任务名称（用于跟踪和日志记录）'
        )
        
        parser.add_argument(
            '--limit',
            type=int,
            help='限制处理的文章数量'
        )
        
        parser.add_argument(
            '--force',
            action='store_true',
            help='强制重新处理已存在的文章'
        )
    
    def handle(self, *args, **options):
        """命令处理入口"""
        generated_dir = options['generated_dir']
        static_dir = options['static_dir']
        dry_run = options['dry_run']
        task_name = options['task_name']
        
        # 验证目录参数
        if not generated_dir:
            raise CommandError('必须指定生成目录（通过--generated-dir参数或ARTICLE_GENERATED_DIR环境变量）')
        if not static_dir:
            raise CommandError('必须指定静态文件目录（通过--static-dir参数或ARTICLE_STATIC_DIR环境变量）')
        
        # 开始扫描任务
        self.stdout.write(f'开始扫描任务: {task_name}')
        
        try:
            # 设置目录路径
            self.generated_articles_dir = Path(generated_dir)
            self.static_files_dir = Path(static_dir)
            
            # 确保静态文件目录存在
            self.static_files_dir.mkdir(parents=True, exist_ok=True)
            
            # 初始化默认作者
            if not self._initialize_default_author():
                raise CommandError("无法初始化默认作者")
            
            # 加载分类缓存
            self._load_categories_cache()
            
            # 扫描文章
            self.stdout.write(self.style.SUCCESS('开始扫描文章...'))
            articles = self._scan_articles()
            
            if not articles:
                self.stdout.write(self.style.WARNING('没有找到任何文章'))
                return
            
            # 限制处理数量（如果指定）
            if options.get('limit') and options['limit'] > 0:
                articles = articles[:options['limit']]
                self.stdout.write(
                    self.style.SUCCESS(f"限制处理数量为: {options['limit']}")
                )
            
            # 处理文章
            self._process_articles(
                articles, 
                dry_run=dry_run,
                force=options.get('force', False)
            )
            
            # 任务完成
            
            # 打印统计信息
            self._print_statistics()
            
        except Exception as e:
            # 处理异常
            
            logger.error(f"文章扫描失败: {e}")
            raise CommandError(f"文章扫描失败: {e}")
    
    def _initialize_default_author(self) -> bool:
        """初始化默认作者（使用第一个活跃用户）
        
        Returns:
            bool: 是否初始化成功
        """
        try:
            self.default_author = User.objects.filter(is_active=True).first()
            if not self.default_author:
                logger.error("没有找到活跃用户作为默认作者")
                return False
            
            logger.info(f"使用默认作者: {self.default_author.username}")
            return True
            
        except Exception as e:
            logger.error(f"初始化默认作者失败: {e}")
            return False
    
    def _load_categories_cache(self) -> bool:
        """加载分类缓存
        
        Returns:
            bool: 是否加载成功
        """
        try:
            categories = Category.objects.all()
            for category in categories:
                self.category_cache[category.name] = category.id
            
            logger.info(f"加载了 {len(self.category_cache)} 个分类到缓存")
            return True
            
        except Exception as e:
            logger.error(f"加载分类缓存失败: {e}")
            return False
    
    def _get_or_create_category(self, category_name: str) -> Optional[str]:
        """获取或创建分类
        
        Args:
            category_name: 分类名称
            
        Returns:
            Optional[str]: 分类ID，失败返回None
        """
        try:
            # 先从缓存中查找
            if category_name in self.category_cache:
                return self.category_cache[category_name]
            
            # 尝试从数据库获取
            try:
                category = Category.objects.get(name=category_name)
                self.category_cache[category_name] = category.id
                return category.id
            except Category.DoesNotExist:
                pass
            
            # 创建新分类
            category_slug = self._generate_category_slug(category_name)
            
            # 检查slug是否已存在
            slug_counter = 1
            original_slug = category_slug
            while Category.objects.filter(slug=category_slug).exists():
                category_slug = f"{original_slug}-{slug_counter}"
                slug_counter += 1
            
            category = Category.objects.create(
                name=category_name,
                slug=category_slug,
                description=f"{category_name}相关文章"
            )
            
            self.category_cache[category_name] = category.id
            logger.info(f"创建新分类: {category_name} (ID: {category.id})")
            
            return category.id
            
        except Exception as e:
            logger.error(f"获取或创建分类失败 [{category_name}]: {e}")
            return None
    
    def _generate_category_slug(self, category_name: str) -> str:
        """生成分类slug
        
        Args:
            category_name: 分类名称
            
        Returns:
            str: 生成的slug
        """
        # 简单的中文转拼音映射（可以使用pypinyin库进行更准确的转换）
        pinyin_map = {
            '汽车': 'automotive',
            '日记': 'diary', 
            '教育': 'education',
            '娱乐': 'entertainment',
            '美食': 'food',
            '生活': 'lifestyle',
            '民生': 'livelihood',
            '情书': 'love-letters',
            '旅游': 'travel',
            '冷知识': 'trivia',
            '职场': 'workplace'
        }
        
        return pinyin_map.get(category_name, category_name.lower().replace(' ', '-'))
    
    def _parse_category_name(self, dir_name: str) -> tuple[str, str]:
        """解析分类目录名称
        
        Args:
            dir_name: 目录名称（支持 '分类名称_分类英文' 或 '纯英文' 格式）
            
        Returns:
            tuple[str, str]: (英文分类名, 中文分类名)
        """
        if '_' in dir_name:
            # 新格式：分类名称_分类英文
            parts = dir_name.split('_', 1)
            category_cn = parts[0]
            category_en = parts[1]
            return category_en, category_cn
        else:
            # 旧格式：纯英文
            category_en = dir_name
            category_cn = self.category_mapping.get(category_en)
            # 兼容旧格式
            if not category_cn:
                category_cn = self.category_map.get(category_en)
                category_en, category_cn = category_cn, category_en
            return category_en, category_cn
    
    def _parse_markdown_file(self, md_file: Path, category_en: str, category_cn: str) -> Optional[Dict]:
        """解析markdown文件并生成文章信息
        
        Args:
            md_file: markdown文件路径
            category_en: 英文分类名
            category_cn: 中文分类名
            
        Returns:
            Optional[Dict]: 解析后的文章信息，失败返回None
        """
        try:
            # 读取markdown内容
            with open(md_file, 'r', encoding='utf-8') as f:
                content = f.read().strip()
            
            if not content:
                logger.warning(f"Markdown文件内容为空: {md_file}")
                return None
            
            # 提取标题（第一行的#标题）
            lines = content.split('\n')
            title = None
            for line in lines:
                line = line.strip()
                if line.startswith('# '):
                    title = line[2:].strip()
                    break
            
            if not title:
                # 如果没有找到标题，使用文件名
                title = md_file.stem
                logger.warning(f"未找到标题，使用文件名: {title}")

            # 生成内容哈希用于去重检查
            content_for_hash = f"{title}\n{content}"
            content_hash = hashlib.md5(content_for_hash.encode('utf-8')).hexdigest()[:8]
            # 生成唯一文章ID
            article_id = content_hash  # 8位短UUID
            
            # 生成唯一文件名
            unique_filename = article_id
            
            # 自动生成HTML和meta文件
            self._generate_supporting_files(md_file, content, title, article_id, content_hash)
            
            # 生成摘要
            summary = self._generate_summary(content)
            
            # 生成slug
            slug = self._generate_slug(title, article_id)
            
            # 生成meta文件路径
            meta_file_path = md_file.parent / f"{md_file.stem}.meta"
            
            return {
                'id': article_id,
                'title': title,
                'content': content,
                'summary': summary,
                'slug': slug,
                'category_en': category_en,
                'category_cn': category_cn,
                'file_path': str(md_file),
                'meta_file': str(meta_file_path),
                'word_count': len(content),
                'created_at': timezone.now()
            }
            
        except Exception as e:
            logger.error(f"解析Markdown文件失败 {md_file}: {e}")
            return None
    
    def _generate_supporting_files(self, md_file: Path, content: str, title: str, article_id: str, content_hash: str = None) -> None:
        """为markdown文件生成HTML和meta文件
        
        Args:
            md_file: markdown文件路径
            content: markdown内容
            title: 文章标题
            article_id: 文章ID
            content_hash: 内容哈希值（如果提供，将使用此值而非重新计算）
        """
        try:
            # 使用唯一文件名或原文件名
            base_path = md_file.parent / md_file.stem
            
            # 生成HTML文件
            html_file = base_path.with_suffix('.html')
            if not html_file.exists():
                html_content = self._markdown_to_html(content)
                full_html = self._create_html_template(title, html_content)
                
                with open(html_file, 'w', encoding='utf-8') as f:
                    f.write(full_html)
                
                logger.info(f"已生成HTML文件: {html_file}")
            
            # 生成.meta文件
            meta_file = base_path.with_suffix('.meta')
            if not meta_file.exists():
                # 按照项目规范生成.meta文件结构
                # 使用传入的content_hash或重新计算
                if content_hash is None:
                    content_for_hash = f"{title}\n{content}"
                    content_hash = hashlib.md5(content_for_hash.encode('utf-8')).hexdigest()[:8]
                
                meta_data = {
                    "article_id": article_id,
                    "title": title,
                    "word_count": len(content),
                    "content_hash": content_hash,
                    "generated_at": timezone.now().isoformat(),
                    "article_type": "通用",  # 默认类型，可根据分类调整
                    "topic": {
                        "title": title,
                        "description": f"关于{title}的详细内容",
                        "category": "通用",
                        "keywords": []
                    },
                    "metadata": {
                        "config": {
                            "article_type": "通用",
                            "min_words": len(content),
                            "format_type": "markdown",
                            "perspective": "第三人称",
                            "structure": {},
                            "language_style": "",
                            "catchphrase": ""
                        },
                        "template": {
                            "背景": "内容创作者",
                            "性格特点": "专业、客观、详细",
                            "写作原则": [
                                "内容准确",
                                "逻辑清晰",
                                "表达简洁",
                                "实用性强"
                            ],
                            "常见主题类型": [
                                "知识分享",
                                "经验总结",
                                "技术解析",
                                "实用指南"
                            ],
                            "语言风格": "简洁明了、逻辑清晰",
                            "口头禅": [
                                "需要注意的是",
                                "值得一提的是",
                                "总的来说",
                                "简而言之"
                            ]
                        }
                    },
                    "files": {
                        "markdown": md_file.name,
                        "html": html_file.name
                    }
                }
                
                with open(meta_file, 'w', encoding='utf-8') as f:
                    json.dump(meta_data, f, ensure_ascii=False, indent=2)
                
                logger.info(f"已生成meta文件: {meta_file}")
                
        except Exception as e:
            logger.error(f"生成支持文件失败 {md_file}: {e}")
    
    def _markdown_to_html(self, content: str) -> str:
        """将Markdown内容转换为HTML
        
        Args:
            content: Markdown内容
            
        Returns:
            str: 转换后的HTML内容
        """
        html_lines = []
        lines = content.split('\n')
        
        for line in lines:
            line = line.rstrip()
            
            # 处理标题
            if line.startswith('# '):
                html_lines.append(f'<h1>{line[2:]}</h1>')
            elif line.startswith('## '):
                html_lines.append(f'<h2>{line[3:]}</h2>')
            elif line.startswith('### '):
                html_lines.append(f'<h3>{line[4:]}</h3>')
            elif line.startswith('#### '):
                html_lines.append(f'<h4>{line[5:]}</h4>')
            elif line.startswith('##### '):
                html_lines.append(f'<h5>{line[6:]}</h5>')
            elif line.startswith('###### '):
                html_lines.append(f'<h6>{line[7:]}</h6>')
            # 处理分隔线
            elif line.strip() in ['---', '***', '___']:
                html_lines.append('<hr>')
            # 处理空行
            elif not line.strip():
                html_lines.append('<br>')
            else:
                # 处理普通文本（包括粗体和斜体）
                processed_line = line
                
                # 处理粗体 **text**
                processed_line = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', processed_line)
                
                # 处理斜体 *text*
                processed_line = re.sub(r'\*(.*?)\*', r'<em>\1</em>', processed_line)
                
                html_lines.append(f'<p>{processed_line}</p>')
        
        return '\n'.join(html_lines)
    
    def _generate_summary(self, content: str) -> str:
        """生成文章摘要
        
        Args:
            content: 文章内容
            
        Returns:
            str: 文章摘要
        """
        # 移除markdown标记
        text = re.sub(r'#+\s*', '', content)  # 移除标题标记
        text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)  # 移除粗体标记
        text = re.sub(r'\*(.*?)\*', r'\1', text)  # 移除斜体标记
        text = re.sub(r'\n+', ' ', text)  # 替换换行为空格
        text = text.strip()
        
        # 截取前200个字符作为摘要
        if len(text) > 200:
            summary = text[:200] + '...'
        else:
            summary = text
            
        return summary
    
    def _generate_slug(self, title: str, article_id: str) -> str:
        """生成文章slug
        
        Args:
            title: 文章标题
            article_id: 文章ID
            
        Returns:
            str: 文章slug
        """
        # 使用文章ID作为slug的基础
        slug = article_id.lower()
        
        # 移除特殊字符，只保留字母、数字和连字符
        slug = re.sub(r'[^a-z0-9\-_]', '-', slug)
        slug = re.sub(r'-+', '-', slug)  # 合并多个连字符
        slug = slug.strip('-')  # 移除首尾连字符
        
        return slug or 'article'
    
    def _create_html_template(self, title: str, content: str) -> str:
        """创建完整的HTML模板
        
        Args:
            title: 文章标题
            content: HTML内容
            
        Returns:
            str: 完整的HTML文档
        """
        return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
            background-color: #fff;
        }}
        h1, h2, h3, h4, h5, h6 {{
            color: #2c3e50;
            margin-top: 24px;
            margin-bottom: 16px;
        }}
        h1 {{
            border-bottom: 2px solid #eaecef;
            padding-bottom: 10px;
        }}
        p {{
            margin-bottom: 16px;
        }}
        hr {{
            border: none;
            border-top: 1px solid #eaecef;
            margin: 24px 0;
        }}
        strong {{
            font-weight: 600;
        }}
        em {{
            font-style: italic;
        }}
        br {{
            margin: 8px 0;
        }}
    </style>
</head>
<body>
    {content}
</body>
</html>"""
    
    def _scan_articles(self) -> List[Dict]:
        """扫描文章目录
        
        Returns:
            List[Dict]: 扫描到的文章信息列表
        """
        articles = []
        
        if not self.generated_articles_dir.exists():
            logger.warning(f"生成文章目录不存在: {self.generated_articles_dir}")
            return articles
        
        # 遍历分类目录（支持新格式：分类名称_分类英文）
        for category_dir in self.generated_articles_dir.iterdir():
            if not category_dir.is_dir():
                continue
            
            # 忽略Back目录
            if self.ignore_back_directory and category_dir.name == self.back_directory_name:
                logger.info(f"忽略Back目录: {category_dir.name}")
                continue
            
            # 解析目录名称（分类名称_分类英文 或 纯英文）
            category_en, category_cn = self._parse_category_name(category_dir.name)
            if not category_en or not category_cn:
                logger.warning(f"无法解析目录名称: {category_dir.name}")
                continue
            
            logger.info(f"扫描分类目录: {category_en} ({category_cn})")
            
            category_articles = self._scan_category_articles(
                category_dir, category_en, category_cn
            )
            articles.extend(category_articles)
        
        self.stats['total_found'] = len(articles)
        logger.info(f"总共找到 {len(articles)} 篇文章")
        
        return articles
    
    def _scan_category_articles(self, category_dir: Path, category_en: str, category_cn: str) -> List[Dict]:
        """扫描分类目录下的文章
        
        Args:
            category_dir: 分类目录路径
            category_en: 英文分类名
            category_cn: 中文分类名
            
        Returns:
            List[Dict]: 该分类下的文章信息列表
        """
        articles = []
        
        # 遍历文章文件（支持直接的.md文件）
        for item in category_dir.iterdir():
            if item.is_file() and item.suffix == '.md':
                # 处理直接的markdown文件
                article_info = self._parse_markdown_file(item, category_en, category_cn)
                if article_info:
                    articles.append(article_info)
            # elif item.is_dir():
            #     # 处理文章目录（兼容旧格式）
            #     meta_file = item / 'meta.meta'
            #     if meta_file.exists():
            #         article_info = self._parse_article_meta(meta_file, category_en, category_cn)
            #         if article_info:
            #             articles.append(article_info)
            #     else:
            #         logger.warning(f"文章目录缺少meta.meta: {item}")
        
        logger.info(f"分类 {category_cn} 找到 {len(articles)} 篇文章")
        return articles
    
    def _parse_article_meta(self, meta_file: Path, category_en: str, category_cn: str) -> Optional[Dict]:
        """解析文章元数据
        
        Args:
            meta_file: meta.meta文件路径
            category_en: 英文分类名
            category_cn: 中文分类名
            
        Returns:
            Optional[Dict]: 解析后的文章信息，失败返回None
        """
        try:
            with open(meta_file, 'r', encoding='utf-8') as f:
                meta_data = json.load(f)
            
            article_dir = meta_file.parent
            
            # 检查必需字段（适配新的.meta文件结构）
            required_fields = ['article_id', 'title']
            for field in required_fields:
                if field not in meta_data:
                    logger.warning(f"文章元数据缺少必需字段 {field}: {meta_file}")
                    return None
            
            # 从files字段获取markdown文件名
            files_info = meta_data.get('files', {})
            markdown_filename = files_info.get('markdown')
            
            if not markdown_filename:
                logger.warning(f"文章元数据缺少markdown文件信息: {meta_file}")
                return None
            
            # 检查内容文件是否存在
            content_file = article_dir / markdown_filename
            if not content_file.exists():
                logger.warning(f"文章内容文件不存在: {content_file}")
                return None
            
            # 读取文章内容
            try:
                with open(content_file, 'r', encoding='utf-8') as f:
                    content = f.read().strip()
            except Exception as e:
                logger.error(f"读取文章内容失败 {content_file}: {e}")
                return None
            
            if not content:
                logger.warning(f"文章内容为空: {content_file}")
                return None
            
            # 生成摘要
            summary = self._generate_summary(content)
            
            # 生成slug
            slug = self._generate_slug(meta_data['title'], meta_data['article_id'])
            
            return {
                'id': meta_data['article_id'],
                'title': meta_data['title'],
                'content': content,
                'summary': summary,
                'slug': slug,
                'category_en': category_en,
                'category_cn': category_cn,
                'tags': meta_data.get('topic', {}).get('keywords', []),
                'created_at': meta_data.get('generated_at'),
                'updated_at': meta_data.get('generated_at'),
                'source_dir': str(article_dir),
                'content_file': str(content_file),
                'meta_file': str(meta_file),
                'word_count': meta_data.get('word_count', 0),
                'article_type': meta_data.get('article_type', '通用'),
                'topic': meta_data.get('topic', {}),
                'metadata': meta_data.get('metadata', {}),
                'files': files_info
            }
            
        except Exception as e:
            logger.error(f"解析文章元数据失败 {meta_file}: {e}")
            return None
    
    def _generate_summary(self, content: str, max_length: int = 200) -> str:
        """生成文章摘要
        
        Args:
            content: 文章内容
            max_length: 最大长度
            
        Returns:
            str: 生成的摘要
        """
        # 移除多余的空白字符
        content = ' '.join(content.split())
        
        # 如果内容长度小于等于最大长度，直接返回
        if len(content) <= max_length:
            return content
        
        # 截取指定长度并在最后一个完整句子处截断
        truncated = content[:max_length]
        
        # 查找最后一个句号、问号或感叹号
        last_sentence_end = max(
            truncated.rfind('。'),
            truncated.rfind('？'),
            truncated.rfind('！'),
            truncated.rfind('.'),
            truncated.rfind('?'),
            truncated.rfind('!')
        )
        
        if last_sentence_end > max_length * 0.5:  # 如果找到的位置不太靠前
            return truncated[:last_sentence_end + 1]
        else:
            return truncated + '...'
    
    def _generate_slug(self, title: str, article_id: str) -> str:
        """生成文章slug
        
        Args:
            title: 文章标题
            article_id: 文章ID
            
        Returns:
            str: 生成的slug
        """
        # 使用文章ID和标题的哈希值生成slug
        hash_input = f"{article_id}-{title}"
        hash_value = hashlib.md5(hash_input.encode('utf-8')).hexdigest()[:8]
        return f"article-{hash_value}"
    
    def _process_articles(self, articles: List[Dict], dry_run: bool = False, force: bool = False) -> None:
        """处理文章列表
        
        Args:
            articles: 文章信息列表
            dry_run: 是否为试运行模式
            force: 是否强制重新处理已存在的文章
        """
        # 初始化总处理数量统计
        # 初始化总处理文章数统计
        self.stats['total_processed'] = len(articles)
        # 遍历处理每篇文章
        for i, article_info in enumerate(articles, 1):
                # 检查文章是否已存在（除非强制处理）
            
            try:
                # 检查文章是否已存在
                if not force and Article.objects.filter(slug=article_info['slug']).exists():
                    # 处理扫描过的文件（删除或移动到Back目录）
                    self._handle_scanned_files(article_info)
                    continue  # 跳过当前文章，继续处理下一篇
                
                if dry_run:
                    logger.info(f"[试运行] 将创建文章: {article_info['title']}")
                    self.stats['total_success'] += 1
                    continue
                
                # 创建文章到数据库
                if self._create_article_in_database(article_info):
                    # 复制文章文件到静态目录
                    self._copy_article_to_static(article_info)
                    
                    # 处理扫描过的文件（删除或移动到Back目录）
                    self._handle_scanned_files(article_info)
                    
                    self.stats['total_success'] += 1
                    
                    # 更新分类统计
                    category = article_info['category_cn']
                    self.stats['categories'][category] = self.stats['categories'].get(category, 0) + 1
                else:
                    self.stats['total_failed'] += 1
                    
            except Exception as e:
                logger.error(f"处理文章失败 [{article_info['title']}]: {e}")
                self.stats['total_failed'] += 1
    
    def _create_article_in_database(self, article_info: Dict) -> bool:
        """在数据库中创建文章
        
        Args:
            article_info: 文章信息
            
        Returns:
            bool: 是否创建成功
        """
        try:
            with transaction.atomic():
                # 获取或创建分类
                category_id = self._get_or_create_category(article_info['category_cn'])
                if not category_id:
                    logger.error(f"无法获取分类: {article_info['category_cn']}")
                    return False
                
                # 获取分类对象
                category = Category.objects.get(id=category_id)
                
                # 创建文章
                article = Article.objects.create(
                    title=article_info['title'],
                    slug=article_info['slug'],
                    content=article_info['content'],
                    summary=article_info['summary'],
                    author_uuid=self.default_author.uuid,
                    category_uuid=category.uuid,
                    status=2  # 已发布
                )
                
                logger.info(f"成功创建文章: {article.title} (ID: {article.id})")
                return True
                
        except Exception as e:
            logger.error(f"创建文章失败 [{article_info['title']}]: {e}")
            return False
    
    def _copy_article_to_static(self, article_info: Dict) -> Optional[Dict[str, str]]:
        """复制文章文件到静态目录
        
        Args:
            article_info: 文章信息
            
        Returns:
            Optional[Dict[str, str]]: 复制后的文件路径信息，失败返回None
        """
        try:
            # 创建分类目录
            target_category_dir = self.static_files_dir / article_info['category_en']
            target_category_dir.mkdir(parents=True, exist_ok=True)
            
            copied_files = {}
            
            # 复制主要内容文件（MD或HTML）
            source_file = Path(article_info['file_path'])
            target_filename = f"{article_info['id']}{source_file.suffix}"
            target_file = target_category_dir / target_filename
            shutil.copy2(source_file, target_file)
            
            # 记录主要内容文件路径
            main_file_path = f"file/{article_info['category_en']}/{target_filename}"
            copied_files['main'] = main_file_path
            logger.info(f"主要文件已复制: {main_file_path}")
            
            # 复制.meta文件
            meta_source = Path(article_info['meta_file'])
            meta_target_filename = f"{article_info['id']}.meta"
            meta_target_file = target_category_dir / meta_target_filename
            shutil.copy2(meta_source, meta_target_file)
            
            meta_file_path = f"file/{article_info['category_en']}/{meta_target_filename}"
            copied_files['meta'] = meta_file_path
            logger.info(f"元数据文件已复制: {meta_file_path}")
            
            # 查找并复制对应的HTML文件（如果主文件是MD）
            base_name = meta_source.stem
            if source_file.suffix.lower() == '.md':
                html_source = meta_source.parent / f"{base_name}.html"
                if html_source.exists():
                    html_target_filename = f"{article_info['id']}.html"
                    html_target_file = target_category_dir / html_target_filename
                    shutil.copy2(html_source, html_target_file)
                    
                    html_file_path = f"file/{article_info['category_en']}/{html_target_filename}"
                    copied_files['html'] = html_file_path
                    logger.info(f"HTML文件已复制: {html_file_path}")
            
            # 查找并复制对应的MD文件（如果主文件是HTML）
            elif source_file.suffix.lower() == '.html':
                md_source = meta_source.parent / f"{base_name}.md"
                if md_source.exists():
                    md_target_filename = f"{article_info['id']}.md"
                    md_target_file = target_category_dir / md_target_filename
                    shutil.copy2(md_source, md_target_file)
                    
                    md_file_path = f"file/{article_info['category_en']}/{md_target_filename}"
                    copied_files['md'] = md_file_path
                    logger.info(f"Markdown文件已复制: {md_file_path}")
            
            return copied_files
            
        except Exception as e:
            logger.error(f"复制文章文件失败 [{article_info['title']}]: {e}")
            return None
    
    def _handle_scanned_files(self, article_info: Dict) -> None:
        """处理扫描过的文件（删除或移动到Back目录）
        
        Args:
            article_info: 文章信息
        """
        try:
            if self.scanned_file_action == 'none':
                # 不处理文件
                return
            
            # 获取文章文件路径
            file_path = Path(article_info['file_path'])
            if not file_path.exists():
                logger.warning(f"文章文件不存在，无法处理: {file_path}")
                return
            
            # 获取文章所在的分类目录
            category_dir = file_path.parent
            
            # 获取文章的所有相关文件（.md, .html, .meta）
            base_name = file_path.stem
            related_files = []
            
            # 查找所有相关文件
            for suffix in ['.md', '.html', '.meta']:
                related_file = category_dir / f"{base_name}{suffix}"
                if related_file.exists():
                    related_files.append(related_file)
            
            if not related_files:
                logger.warning(f"未找到文章相关文件: {base_name}")
                return
            
            if self.scanned_file_action == 'delete':
                # 删除文件
                self._delete_scanned_files(related_files, article_info['title'])
            elif self.scanned_file_action == 'move':
                # 移动到Back目录
                self._move_scanned_files_to_back(related_files, category_dir, article_info['title'])
            else:
                logger.warning(f"未知的文件处理动作: {self.scanned_file_action}")
                
        except Exception as e:
            logger.error(f"处理扫描文件失败 [{article_info['title']}]: {e}")
    
    def _delete_scanned_files(self, files: List[Path], article_title: str) -> None:
        """删除扫描过的文件
        
        Args:
            files: 要删除的文件列表
            article_title: 文章标题（用于日志）
        """
        try:
            for file_path in files:
                if file_path.exists():
                    file_path.unlink()
                    logger.info(f"已删除文件: {file_path}")
            
            logger.info(f"已删除文章 '{article_title}' 的所有相关文件")
            
        except Exception as e:
            logger.error(f"删除文件失败 [{article_title}]: {e}")
    
    def _move_scanned_files_to_back(self, files: List[Path], category_dir: Path, article_title: str) -> None:
        """将扫描过的文件移动到Back目录
        
        Args:
            files: 要移动的文件列表
            category_dir: 分类目录
            article_title: 文章标题（用于日志）
        """
        try:
            # 创建Back目录结构
            back_root_dir = self.generated_articles_dir / self.back_directory_name
            back_category_dir = back_root_dir / category_dir.name
            back_category_dir.mkdir(parents=True, exist_ok=True)
            
            # 移动文件
            moved_files = []
            for file_path in files:
                if file_path.exists():
                    target_path = back_category_dir / file_path.name
                    
                    # 如果目标文件已存在，添加时间戳后缀
                    if target_path.exists():
                        timestamp = timezone.now().strftime("%Y%m%d_%H%M%S")
                        name_parts = target_path.stem, timestamp, target_path.suffix
                        target_path = back_category_dir / f"{name_parts[0]}_{name_parts[1]}{name_parts[2]}"
                    
                    # 移动文件
                    shutil.move(str(file_path), str(target_path))
                    moved_files.append(target_path)
                    logger.info(f"已移动文件: {file_path} -> {target_path}")
            
            logger.info(f"已将文章 '{article_title}' 的 {len(moved_files)} 个文件移动到Back目录")
            
        except Exception as e:
            logger.error(f"移动文件到Back目录失败 [{article_title}]: {e}")
    
    def _print_statistics(self) -> None:
        """打印统计信息"""
        self.stdout.write(self.style.SUCCESS('\n=== 扫描统计信息 ==='))
        self.stdout.write(f"找到文章总数: {self.stats['total_found']}")
        self.stdout.write(f"处理文章总数: {self.stats['total_processed']}")
        self.stdout.write(f"成功处理: {self.stats['total_success']}")
        self.stdout.write(f"处理失败: {self.stats['total_failed']}")
        
        if self.stats['categories']:
            self.stdout.write("\n=== 分类统计 ===")
            for category, count in self.stats['categories'].items():
                self.stdout.write(f"{category}: {count} 篇")
        
        self.stdout.write(self.style.SUCCESS('\n扫描完成！'))