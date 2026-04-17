# -*- coding: utf-8 -*-
"""
文章生成工具类

基于文心智能体API，支持：
1. 根据文章类型生成主题/标题
2. 根据标题生成完整文章
3. 支持多种文章类型（职场、生活等）
"""

import json
import logging
import random
import time
import os
import uuid
import hashlib
from pathlib import Path
from typing import List, Dict, Any, Optional, Set
from dataclasses import dataclass, asdict
from datetime import datetime
from difflib import SequenceMatcher

from .wenxin_agent_client import WenxinAgentClient, WenxinConfig
from config.article_config import ArticleType

logger = logging.getLogger(__name__)


@dataclass
class ArticleConfig:
    """文章生成配置"""
    article_type: str  # 文章类型：职场、生活等
    min_words: int = 1800  # 最少字数
    format_type: str = "markdown"  # 格式类型
    perspective: str = "第一人称"  # 视角
    structure: Dict[str, int] = None  # 文章结构
    language_style: str = ""  # 语言风格
    catchphrase: str = ""  # 口头禅
    
    def __post_init__(self):
        if self.structure is None:
            self.structure = {
                "开头": 300,
                "主体故事": 500,
                "分析部分": 800,
                "结尾": 300
            }


@dataclass
class GeneratedTopic:
    """生成的主题"""
    title: str
    description: str = ""
    category: str = ""
    keywords: List[str] = None
    
    def __post_init__(self):
        if self.keywords is None:
            self.keywords = []


@dataclass
class GeneratedArticle:
    """生成的文章"""
    title: str
    content: str
    word_count: int
    topic: GeneratedTopic
    generated_at: datetime
    article_id: str = None  # 唯一标识符
    content_hash: str = None  # 内容哈希值
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
        if self.generated_at is None:
            self.generated_at = datetime.now()
        # if self.article_id is None:
        #     self.article_id = str(uuid.uuid4())[:8]  # 8位短UUID
        if self.content_hash is None:
            # 生成标题+内容的哈希值用于去重
            content_for_hash = f"{self.title}\n{self.content}"
            self.content_hash = hashlib.md5(content_for_hash.encode('utf-8')).hexdigest()[:16]
        self.article_id = self.content_hash


class ArticleGenerator:
    """文章生成器"""
    
    def __init__(self, wenxin_config: WenxinConfig):
        self.wenxin_client = WenxinAgentClient(wenxin_config)
        self.topic_templates = self._load_topic_templates()
        # 支持的文章类型
        self.supported_types = [article_type.chinese_name for article_type in ArticleType]
        
        # 去重相关
        self.generated_hashes: Set[str] = set()  # 已生成文章的哈希值
        self.generated_titles: Set[str] = set()  # 已生成文章的标题
        self.similarity_threshold = 0.8  # 相似度阈值
        
        # 文件管理
        self.base_output_dir = "articles"  # 基础输出目录
        self._load_existing_articles()  # 加载已存在的文章信息
        
    def _load_topic_templates(self) -> Dict[str, Dict[str, Any]]:
        """加载主题模板"""
        return {
            ArticleType.WORKPLACE.chinese_name: {
                "背景": "资深职场专栏作者，具有丰富的职场经验和深刻的职场洞察",
                "性格特点": "理性分析、实用主义、善于从具体案例中提炼普遍规律",
                "写作原则": [
                    "以真实案例为基础",
                    "提供实用的解决方案",
                    "避免空洞的理论说教",
                    "关注职场人的真实困境"
                ],
                "常见主题类型": [
                    "薪资待遇纠纷",
                    "职场人际关系",
                    "跳槽与职业发展",
                    "裁员与失业",
                    "工作压力与平衡",
                    "职场歧视与不公",
                    "领导管理问题",
                    "同事关系处理"
                ],
                "语言风格": "直接、犀利、有温度，善用具体数据和案例",
                "口头禅": ["说实话", "我见过太多这样的情况", "职场就是这样", "关键在于"]
            },
            ArticleType.LIFESTYLE.chinese_name: {
                "背景": "生活观察家，关注普通人的日常生活和情感体验",
                "性格特点": "细腻敏感、善于观察、富有同理心",
                "写作原则": [
                    "贴近生活实际",
                    "关注情感共鸣",
                    "提供正能量引导",
                    "避免说教式表达"
                ],
                "常见主题类型": [
                    "家庭关系",
                    "婚恋情感",
                    "育儿教育",
                    "人际交往",
                    "个人成长",
                    "生活哲理",
                    "健康养生",
                    "兴趣爱好"
                ],
                "语言风格": "温暖、亲切、有感染力，善用生活化的比喻",
                "口头禅": ["生活就是这样", "我觉得", "其实", "说到底"]
            },
            ArticleType.LIVELIHOOD.chinese_name: {
                "背景": "民生观察员，关注社会热点和民生问题",
                "性格特点": "客观理性、关注社会公平、具有社会责任感",
                "写作原则": [
                    "客观报道事实",
                    "关注弱势群体",
                    "提供建设性建议",
                    "促进社会进步"
                ],
                "常见主题类型": [
                    "教育公平",
                    "医疗保障",
                    "住房问题",
                    "就业民生",
                    "社会保障",
                    "环境保护",
                    "食品安全",
                    "交通出行"
                ],
                "语言风格": "客观、严谨、有温度，善用数据和事实说话",
                "口头禅": ["从数据来看", "事实上", "我们需要关注", "这关系到每个人"]
            },
            ArticleType.AUTOMOTIVE.chinese_name: {
                "背景": "汽车行业专家，对汽车技术和市场有深入了解",
                "性格特点": "专业严谨、热爱汽车、善于分析技术趋势",
                "写作原则": [
                    "专业知识准确",
                    "贴近用户需求",
                    "关注行业发展",
                    "提供实用建议"
                ],
                "常见主题类型": [
                    "新车评测",
                    "购车指南",
                    "汽车保养",
                    "驾驶技巧",
                    "行业动态",
                    "新能源汽车",
                    "汽车科技",
                    "二手车市场"
                ],
                "语言风格": "专业、详细、实用，善用技术参数和对比分析",
                "口头禅": ["从技术角度来说", "这款车的亮点是", "值得注意的是", "综合来看"]
            },
            ArticleType.ENTERTAINMENT.chinese_name: {
                "背景": "娱乐圈观察者，对明星动态和娱乐产业有敏锐洞察",
                "性格特点": "敏感时尚、善于捕捉热点、具有娱乐精神",
                "写作原则": [
                    "紧跟热点话题",
                    "保持客观态度",
                    "尊重艺人隐私",
                    "传播正能量"
                ],
                "常见主题类型": [
                    "明星动态",
                    "影视作品",
                    "音乐推荐",
                    "综艺节目",
                    "时尚潮流",
                    "娱乐八卦",
                    "粉丝文化",
                    "行业分析"
                ],
                "语言风格": "轻松、有趣、时尚，善用网络流行语和表情包",
                "口头禅": ["说真的", "太绝了", "这波操作", "不得不说"]
            },
            ArticleType.EDUCATION.chinese_name: {
                "背景": "教育工作者，关注教育改革和学生成长",
                "性格特点": "耐心细致、富有爱心、具有教育情怀",
                "写作原则": [
                    "以学生为中心",
                    "科学教育理念",
                    "关注全面发展",
                    "促进教育公平"
                ],
                "常见主题类型": [
                    "学习方法",
                    "家庭教育",
                    "升学指导",
                    "素质教育",
                    "教育政策",
                    "师生关系",
                    "心理健康",
                    "特长培养"
                ],
                "语言风格": "温和、专业、启发性，善用教育案例和理论",
                "口头禅": ["教育的本质是", "每个孩子都是独特的", "我们要相信", "关键在于引导"]
            },
            ArticleType.LOVE_LETTERS.chinese_name: {
                "背景": "情感作家，擅长表达内心情感和爱意",
                "性格特点": "浪漫细腻、情感丰富、善于用文字传达爱意",
                "写作原则": [
                    "真挚表达情感",
                    "个性化定制",
                    "优美文字表达",
                    "触动内心深处"
                ],
                "常见主题类型": [
                    "初恋表白",
                    "恋爱纪念",
                    "异地恋情",
                    "求婚告白",
                    "道歉挽回",
                    "结婚誓言",
                    "思念之情",
                    "感谢表达"
                ],
                "语言风格": "浪漫、温柔、诗意，善用比喻和情感描述",
                "口头禅": ["我想对你说", "在我心中", "每当想起", "愿我们"]
            },
            ArticleType.FOOD.chinese_name: {
                "背景": "美食达人，对各地美食和烹饪技巧有深入研究",
                "性格特点": "热爱生活、善于发现、乐于分享",
                "写作原则": [
                    "详细制作过程",
                    "突出美食特色",
                    "分享烹饪心得",
                    "传承饮食文化"
                ],
                "常见主题类型": [
                    "家常菜谱",
                    "地方特色",
                    "节日美食",
                    "健康饮食",
                    "烘焙甜品",
                    "餐厅推荐",
                    "食材选购",
                    "营养搭配"
                ],
                "语言风格": "生动、详细、诱人，善用感官描述和制作技巧",
                "口头禅": ["这道菜的精髓在于", "口感层次丰富", "制作要点是", "味道真的很棒"]
            },
            ArticleType.TRAVEL.chinese_name: {
                "背景": "旅行达人，走遍大江南北，善于发现旅行中的美好",
                "性格特点": "热爱探索、乐观开朗、善于观察和记录",
                "写作原则": [
                    "真实旅行体验",
                    "实用攻略信息",
                    "文化深度挖掘",
                    "激发旅行热情"
                ],
                "常见主题类型": [
                    "目的地攻略",
                    "旅行日记",
                    "美食探店",
                    "文化体验",
                    "摄影分享",
                    "住宿推荐",
                    "交通指南",
                    "预算规划"
                ],
                "语言风格": "生动、详细、富有画面感，善用描述和攻略",
                "口头禅": ["这个地方真的很棒", "强烈推荐", "不容错过", "值得一去"]
            },
            ArticleType.TRIVIA.chinese_name: {
                "背景": "知识达人，对各种有趣的冷门知识有广泛了解",
                "性格特点": "好奇心强、博学多才、善于发现有趣事物",
                "写作原则": [
                    "知识准确可靠",
                    "有趣易懂表达",
                    "激发求知欲",
                    "拓展知识面"
                ],
                "常见主题类型": [
                    "科学现象",
                    "历史趣闻",
                    "生活常识",
                    "动物世界",
                    "宇宙奥秘",
                    "人体奥秘",
                    "技术原理",
                    "文化知识"
                ],
                "语言风格": "有趣、通俗、启发性，善用比喻和举例",
                "口头禅": ["你知道吗", "有趣的是", "科学家发现", "原来如此"]
            },
            ArticleType.DIARY.chinese_name: {
                "背景": "生活记录者，善于观察和记录日常生活的点点滴滴",
                "性格特点": "细腻敏感、善于反思、热爱生活",
                "写作原则": [
                    "真实记录生活",
                    "表达内心感受",
                    "反思成长经历",
                    "珍惜美好时光"
                ],
                "常见主题类型": [
                    "日常生活",
                    "情感体验",
                    "工作感悟",
                    "人际关系",
                    "个人成长",
                    "梦想追求",
                    "困难挫折",
                    "快乐时光"
                ],
                "语言风格": "真诚、自然、有温度，善用内心独白和情感表达",
                "口头禅": ["今天", "我觉得", "突然想到", "回想起来"]
            }
        }
    
    def _load_existing_articles(self):
        """加载已存在的文章信息，用于去重"""
        try:
            # 扫描输出目录下的所有.meta文件
            if os.path.exists(self.base_output_dir):
                for root, dirs, files in os.walk(self.base_output_dir):
                    for file in files:
                        if file.endswith('.meta'):
                            meta_path = os.path.join(root, file)
                            try:
                                with open(meta_path, 'r', encoding='utf-8') as f:
                                    meta_data = json.load(f)
                                    if 'content_hash' in meta_data:
                                        self.generated_hashes.add(meta_data['content_hash'])
                                    if 'title' in meta_data:
                                        self.generated_titles.add(meta_data['title'])
                            except Exception as e:
                                logger.warning(f"读取元数据文件失败 {meta_path}: {e}")
            
            logger.info(f"已加载 {len(self.generated_hashes)} 个已生成文章的哈希值")
            
        except Exception as e:
            logger.error(f"加载已存在文章信息失败: {e}")
    
    def _is_duplicate_content(self, article: GeneratedArticle) -> bool:
        """检查文章是否重复"""
        # 检查哈希值
        if article.content_hash in self.generated_hashes:
            return True
        
        # 检查标题完全相同
        if article.title in self.generated_titles:
            return True
        
        # 检查标题相似度
        for existing_title in self.generated_titles:
            similarity = SequenceMatcher(None, article.title, existing_title).ratio()
            if similarity > self.similarity_threshold:
                logger.warning(f"发现相似标题: '{article.title}' vs '{existing_title}' (相似度: {similarity:.2f})")
                return True
        
        return False
    
    def _calculate_content_similarity(self, content1: str, content2: str) -> float:
        """计算两个内容的相似度"""
        # 简化内容，去除标点和空格
        clean_content1 = ''.join(c for c in content1 if c.isalnum())
        clean_content2 = ''.join(c for c in content2 if c.isalnum())
        
        return SequenceMatcher(None, clean_content1, clean_content2).ratio()
    
    def _create_output_directory(self, article_type: str, base_dir: str = None) -> str:
        """创建输出目录结构"""
        if base_dir is None:
            base_dir = self.base_output_dir
        
        # 创建层级目录结构: base_dir/category/type/
        # 查找对应的枚举值
        category = "others"
        for article_enum in ArticleType:
            if article_enum.chinese_name == article_type:
                category = article_enum.english_name
                break
        output_dir = os.path.join(base_dir, category, article_type)
        
        # 创建目录
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        
        return output_dir
    
    def _generate_filename(self, article: GeneratedArticle, article_type: str) -> str:
        """生成文件名"""
        return f"{article_type}_{article.article_id}"
    
    def _save_article_files(self, article: GeneratedArticle, article_type: str, output_dir: str) -> Dict[str, str]:
        """保存文章的所有文件（.md, .html, .meta）"""
        filename = self._generate_filename(article, article_type)
        output_path = os.path.join(output_dir, filename)
        
        files_created = {}
        
        try:
            # 1. 保存Markdown文件（仅标题和内容）
            md_file = f"{output_path}.md"
            with open(md_file, 'w', encoding='utf-8') as f:
                f.write(f"# {article.title}\n\n")
                f.write(article.content)
            files_created['markdown'] = md_file
            
            # 2. 保存HTML文件（仅标题和内容）
            html_file = f"{output_path}.html"
            html_content = self._create_clean_html(article.title, article.content)
            with open(html_file, 'w', encoding='utf-8') as f:
                f.write(html_content)
            files_created['html'] = html_file
            
            # 3. 保存元数据文件
            meta_file = f"{output_path}.meta"
            meta_data = {
                "article_id": article.article_id,
                "title": article.title,
                "word_count": article.word_count,
                "content_hash": article.content_hash,
                "generated_at": article.generated_at.isoformat(),
                "article_type": article_type,
                "topic": {
                    "title": article.topic.title,
                    "description": article.topic.description,
                    "category": article.topic.category,
                    "keywords": article.topic.keywords
                },
                "metadata": article.metadata,
                "files": {
                    "markdown": os.path.basename(md_file),
                    "html": os.path.basename(html_file)
                }
            }
            
            with open(meta_file, 'w', encoding='utf-8') as f:
                json.dump(meta_data, f, ensure_ascii=False, indent=2)
            files_created['meta'] = meta_file
            
            # 更新去重缓存
            self.generated_hashes.add(article.content_hash)
            self.generated_titles.add(article.title)
            
            logger.info(f"文章文件已保存: {filename}")
            return files_created
            
        except Exception as e:
            logger.error(f"保存文章文件失败: {e}")
            # 清理已创建的文件
            for file_path in files_created.values():
                try:
                    if os.path.exists(file_path):
                        os.remove(file_path)
                except:
                    pass
            raise
    
    def _create_clean_html(self, title: str, content: str) -> str:
        """创建简洁的HTML文件（仅标题和内容）"""
        # 处理内容，移除重复的标题
        lines = content.split('\n')
        processed_lines = []
        
        # 跳过第一个与title相同的标题行
        title_found = False
        for line in lines:
            line = line.strip()
            if not title_found and (line == f"# {title}" or line == f"### {title}"):
                title_found = True
                continue
            processed_lines.append(line)
        
        # 重新组合内容
        processed_content = '\n'.join(processed_lines).strip()
        
        # 转换为HTML
        html_content = self._markdown_to_html(processed_content)
        
        return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <style>
        body {{
            font-family: 'Microsoft YaHei', Arial, sans-serif;
            line-height: 1.6;
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f5f5f5;
        }}
        .container {{
            background-color: white;
            padding: 30px;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}
        h1 {{
            color: #2c3e50;
            border-bottom: 3px solid #3498db;
            padding-bottom: 10px;
            margin-bottom: 30px;
        }}
        h2 {{
            color: #34495e;
            margin-top: 30px;
        }}
        h3 {{
            color: #7f8c8d;
        }}
        h4 {{
            color: #95a5a6;
        }}
        p {{
            text-align: justify;
            margin-bottom: 15px;
        }}
        strong {{
            color: #e74c3c;
        }}
        hr {{
            border: none;
            height: 2px;
            background: linear-gradient(to right, #3498db, #2ecc71);
            margin: 30px 0;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>{title}</h1>
        {html_content}
    </div>
</body>
</html>"""
    
    def generate_topics(self, 
                       article_type: str, 
                       count: int = 5,
                       reference_file: Optional[str] = None) -> List[GeneratedTopic]:
        """
        生成指定数量的主题/标题
        
        Args:
            article_type: 文章类型
            count: 生成数量
            reference_file: 参考文件路径
            
        Returns:
            List[GeneratedTopic]: 生成的主题列表
        """
        if article_type not in self.topic_templates:
            raise ValueError(f"不支持的文章类型: {article_type}")
        
        template = self.topic_templates[article_type]
        
        # 构建主题生成提示词
        prompt = self._build_topic_generation_prompt(
            template, count, reference_file
        )
        
        try:
            # 调用AI生成主题
            response = self.wenxin_client.conversation_complete(
                text=prompt,
                open_id=f"topic_gen_{int(time.time())}",
                is_first_conversation=True,
                stream_timeout=60
            )
            
            # 解析生成的主题
            topics = self._parse_generated_topics(response, article_type)
            
            logger.info(f"成功生成{len(topics)}个{article_type}类型的主题")
            return topics
            
        except Exception as e:
            logger.error(f"生成主题失败: {e}")
            raise
    
    def _build_topic_generation_prompt(self, 
                                     template: Dict[str, Any], 
                                     count: int,
                                     reference_file: Optional[str] = None) -> str:
        """构建主题生成提示词"""
        
        reference_content = ""
        if reference_file:
            try:
                with open(reference_file, 'r', encoding='utf-8') as f:
                    # 读取前50行作为参考
                    lines = f.readlines()[:50]
                    reference_content = "\n参考示例：\n" + "".join(lines)
            except Exception as e:
                logger.warning(f"读取参考文件失败: {e}")
        
        prompt = f"""
你是一名{template['背景']}，具有以下特点：
- 性格特点：{template['性格特点']}
- 写作原则：{', '.join(template['写作原则'])}
- 语言风格：{template['语言风格']}

请根据以下要求生成{count}个具有吸引力的文章标题：

要求：
1. 标题要具体、有冲突感、能引起读者共鸣
2. 涵盖以下主题类型：{', '.join(template['常见主题类型'])}
3. 标题长度控制在20-50字之间
4. 要包含具体的数字、场景或对话
5. 体现真实的职场/生活场景

{reference_content}

请按以下JSON格式输出：
{{
  "topics": [
    {{
      "title": "标题内容",
      "description": "简短描述",
      "category": "具体分类",
      "keywords": ["关键词1", "关键词2"]
    }}
  ]
}}

请确保输出的是有效的JSON格式。
"""
        
        return prompt
    
    def _parse_generated_topics(self, response: str, article_type: str) -> List[GeneratedTopic]:
        """解析生成的主题"""
        topics = []
        
        try:
            # 尝试解析JSON格式
            if "```json" in response:
                json_start = response.find("```json") + 7
                json_end = response.find("```", json_start)
                json_content = response[json_start:json_end].strip()
            elif "{" in response and "}" in response:
                json_start = response.find("{")
                json_end = response.rfind("}") + 1
                json_content = response[json_start:json_end]
            else:
                raise ValueError("未找到有效的JSON格式")
            
            data = json.loads(json_content)
            
            for topic_data in data.get("topics", []):
                topic = GeneratedTopic(
                    title=topic_data.get("title", ""),
                    description=topic_data.get("description", ""),
                    category=topic_data.get("category", article_type),
                    keywords=topic_data.get("keywords", [])
                )
                topics.append(topic)
                
        except Exception as e:
            logger.warning(f"JSON解析失败，尝试文本解析: {e}")
            # 备用文本解析方法
            topics = self._parse_topics_from_text(response, article_type)
        
        return topics
    
    def _parse_topics_from_text(self, response: str, article_type: str) -> List[GeneratedTopic]:
        """从文本中解析主题（备用方法）"""
        topics = []
        lines = response.split('\n')
        
        for line in lines:
            line = line.strip()
            if line and (line.startswith('标题：') or line.startswith('题目：') or 
                        line.startswith('主题：') or '：' in line):
                # 提取标题
                if '：' in line:
                    title = line.split('：', 1)[1].strip()
                else:
                    title = line.strip()
                
                if title and len(title) > 10:  # 过滤太短的标题
                    topic = GeneratedTopic(
                        title=title,
                        category=article_type
                    )
                    topics.append(topic)
        
        return topics
    
    def generate_article(self, 
                        topic: GeneratedTopic, 
                        config: ArticleConfig,
                        max_retries: int = 3) -> GeneratedArticle:
        """
        根据主题生成文章
        
        Args:
            topic: 主题对象
            config: 文章配置
            max_retries: 最大重试次数（用于去重）
            
        Returns:
            GeneratedArticle: 生成的文章
        """
        template = self.topic_templates.get(config.article_type)
        if not template:
            raise ValueError(f"不支持的文章类型: {config.article_type}")
        
        for attempt in range(max_retries):
            try:
                # 构建文章生成提示词
                prompt = self._build_article_generation_prompt(topic, config, template)
                
                # 调用AI生成文章
                response = self.wenxin_client.conversation_complete(
                    text=prompt,
                    open_id=f"article_gen_{int(time.time())}_{attempt}",
                    is_first_conversation=True,
                    stream_timeout=120  # 文章生成需要更长时间
                )
                
                # 计算字数
                word_count = len(response.replace(' ', '').replace('\n', ''))
                
                article = GeneratedArticle(
                    title=topic.title,
                    content=response,
                    word_count=word_count,
                    topic=topic,
                    generated_at=datetime.now(),
                    metadata={
                        "config": config.__dict__,
                        "template": template
                    }
                )
                
                # 检查是否重复
                if self._is_duplicate_content(article):
                    logger.warning(f"检测到重复内容，尝试重新生成 (第{attempt + 1}次)")
                    if attempt < max_retries - 1:
                        # 修改主题描述以获得不同的内容
                        topic.description = f"{topic.description} (变体{attempt + 1})"
                        time.sleep(1)  # 短暂延迟
                        continue
                    else:
                        logger.warning(f"达到最大重试次数，使用当前文章: {topic.title}")
                
                logger.info(f"成功生成文章: {topic.title}，字数: {word_count}")
                return article
                
            except Exception as e:
                logger.error(f"生成文章失败 (第{attempt + 1}次): {e}")
                if attempt == max_retries - 1:
                    raise
                time.sleep(2)  # 重试前等待
    
    def _build_article_generation_prompt(self, 
                                       topic: GeneratedTopic, 
                                       config: ArticleConfig,
                                       template: Dict[str, Any]) -> str:
        """构建文章生成提示词"""
        
        # 随机选择口头禅
        catchphrase = random.choice(template['口头禅']) if template['口头禅'] else ""
        
        structure_desc = "\n".join([
            f"- {part}({words}字)" 
            for part, words in config.structure.items()
        ])
        
        prompt = f"""
你是一名{template['背景']}，根据提供的背景、性格特点、写作原则等，帮助用户解决{config.article_type}问题。

你的特点：
- 背景：{template['背景']}
- 性格特点：{template['性格特点']}
- 写作原则：{', '.join(template['写作原则'])}
- 语言风格：{template['语言风格']}
- 常用口头禅：{catchphrase}

现在请写一篇关于"{topic.title}"这个主题的文章。

要求：
- 字数不少于{config.min_words}字
- 使用{config.format_type}格式
- {config.perspective}视角
- 按照给定的文章结构写作：
{structure_desc}
- 要融入指定的口头禅和语言风格
- 内容要真实可信，有具体的细节和场景描述
- 要有明确的观点和实用的建议

请开始写作：
"""
        
        return prompt
    
    def generate_batch_articles(self, 
                              article_type: str, 
                              count: int = 5,
                              config: Optional[ArticleConfig] = None,
                              reference_file: Optional[str] = None,
                              output_dir: Optional[str] = None) -> List[Dict[str, str]]:
        """
        批量生成文章
        
        Args:
            article_type: 文章类型
            count: 生成数量
            config: 文章配置
            reference_file: 参考文件路径
            output_dir: 输出目录（如果不指定则使用默认目录）
            
        Returns:
            List[Dict[str, str]]: 生成的文章文件信息列表
        """
        if config is None:
            config = ArticleConfig(article_type=article_type)
        
        # 创建输出目录
        if output_dir:
            target_output_dir = self._create_output_directory(article_type, output_dir)
        else:
            target_output_dir = self._create_output_directory(article_type)
        
        # 生成主题
        topics = self.generate_topics(
            article_type=article_type,
            count=count,
            reference_file=reference_file
        )
        
        generated_files = []
        successful_count = 0
        
        for i, topic in enumerate(topics):
            try:
                logger.info(f"正在生成第{i+1}/{len(topics)}篇文章: {topic.title}")
                
                article = self.generate_article(topic, config)
                
                # 保存文章文件
                files_created = self._save_article_files(article, article_type, target_output_dir)
                generated_files.append(files_created)
                successful_count += 1
                
                logger.info(f"文章已保存: {files_created['markdown']}")
                
                # 添加延迟避免API限制
                if i < len(topics) - 1:
                    time.sleep(2)
                    
            except Exception as e:
                logger.error(f"生成文章失败: {topic.title}, 错误: {e}")
                continue
        
        logger.info(f"批量生成完成，成功生成{successful_count}篇文章，保存到: {target_output_dir}")
        return generated_files
    
    def _markdown_to_html(self, markdown_content: str) -> str:
        """
        将Markdown内容转换为HTML
        
        Args:
            markdown_content: Markdown内容
            
        Returns:
            str: HTML内容
        """
        import re
        
        # 分行处理
        lines = markdown_content.split('\n')
        html_lines = []
        
        for line in lines:
            line = line.strip()
            if not line:
                html_lines.append('')
                continue
            
            # 转换标题
            if line.startswith('#### '):
                html_lines.append(f'<h4>{line[5:]}</h4>')
            elif line.startswith('### '):
                html_lines.append(f'<h3>{line[4:]}</h3>')
            elif line.startswith('## '):
                html_lines.append(f'<h2>{line[3:]}</h2>')
            elif line.startswith('# '):
                html_lines.append(f'<h1>{line[2:]}</h1>')
            # 转换分隔线
            elif line.startswith('---') or line.startswith('===') or line == '=' * len(line):
                html_lines.append('<hr>')
            else:
                # 普通段落，处理内联格式
                processed_line = line
                
                # 转换粗体
                processed_line = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', processed_line)
                
                # 转换斜体（避免与粗体冲突）
                processed_line = re.sub(r'(?<!\*)\*([^*]+?)\*(?!\*)', r'<em>\1</em>', processed_line)
                
                html_lines.append(f'<p>{processed_line}</p>')
        
        # 合并连续的空行
        html_content = '\n'.join(html_lines)
        html_content = re.sub(r'\n\s*\n', '\n\n', html_content)
        
        return html_content
    
    def _create_html_template(self, title: str, content: str) -> str:
        """
        创建完整的HTML文档
        
        Args:
            title: 文档标题
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
            font-family: 'Microsoft YaHei', Arial, sans-serif;
            line-height: 1.6;
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f5f5f5;
        }}
        .container {{
            background-color: white;
            padding: 30px;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}
        h1 {{
            color: #2c3e50;
            border-bottom: 3px solid #3498db;
            padding-bottom: 10px;
        }}
        h2 {{
            color: #34495e;
            margin-top: 30px;
        }}
        h3 {{
            color: #7f8c8d;
        }}
        h4 {{
            color: #95a5a6;
        }}
        p {{
            text-align: justify;
            margin-bottom: 15px;
        }}
        strong {{
            color: #e74c3c;
        }}
        hr {{
            border: none;
            height: 2px;
            background: linear-gradient(to right, #3498db, #2ecc71);
            margin: 30px 0;
        }}
        .meta-info {{
            background-color: #ecf0f1;
            padding: 15px;
            border-radius: 5px;
            margin-bottom: 20px;
            border-left: 4px solid #3498db;
        }}
        .meta-info strong {{
            color: #2c3e50;
        }}
    </style>
</head>
<body>
    <div class="container">
        {content}
    </div>
</body>
</html>"""
    
    def save_articles_individually(self, 
                                 articles: List[GeneratedArticle], 
                                 article_type: str,
                                 output_dir: Optional[str] = None) -> List[Dict[str, str]]:
        """
        单独保存每篇文章（新的保存方式）
        
        Args:
            articles: 文章列表
            article_type: 文章类型
            output_dir: 输出目录（如果不指定则使用默认目录）
            
        Returns:
            List[Dict[str, str]]: 生成的文章文件信息列表
        """
        # 创建输出目录
        if output_dir:
            target_output_dir = self._create_output_directory(article_type, output_dir)
        else:
            target_output_dir = self._create_output_directory(article_type)
        
        generated_files = []
        
        for article in articles:
            try:
                # 检查是否重复
                if self._is_duplicate_content(article):
                    logger.warning(f"跳过重复文章: {article.title}")
                    continue
                
                # 保存文章文件
                files_created = self._save_article_files(article, article_type, target_output_dir)
                generated_files.append(files_created)
                
                logger.info(f"文章已保存: {files_created['markdown']}")
                
            except Exception as e:
                logger.error(f"保存文章失败: {article.title}, 错误: {e}")
                continue
        
        logger.info(f"单独保存完成，成功保存{len(generated_files)}篇文章到: {target_output_dir}")
        return generated_files
    
    def save_articles_to_file(self, 
                            articles: List[GeneratedArticle], 
                            output_file: str,
                            format_type: str = "markdown",
                            generate_html: bool = True) -> None:
        """
        保存文章到文件，支持同时生成HTML文件
        
        Args:
            articles: 文章列表
            output_file: 输出文件路径
            format_type: 输出格式
            generate_html: 是否同时生成HTML文件
        """
        try:
            # 保存原始格式文件
            with open(output_file, 'w', encoding='utf-8') as f:
                if format_type.lower() == "json":
                    # JSON格式
                    articles_data = []
                    for article in articles:
                        articles_data.append({
                            "title": article.title,
                            "content": article.content,
                            "word_count": article.word_count,
                            "topic": {
                                "title": article.topic.title,
                                "description": article.topic.description,
                                "category": article.topic.category,
                                "keywords": article.topic.keywords
                            },
                            "generated_at": article.generated_at.isoformat(),
                            "metadata": article.metadata
                        })
                    json.dump(articles_data, f, ensure_ascii=False, indent=2)
                else:
                    # Markdown格式
                    markdown_content = ""
                    for i, article in enumerate(articles):
                        article_md = f"# 文章 {i+1}: {article.title}\n\n"
                        article_md += f"**字数**: {article.word_count}\n\n"
                        article_md += f"**创建时间**: {article.generated_at}\n\n"
                        article_md += f"**分类**: {article.topic.category}\n\n"
                        if article.topic.keywords:
                            article_md += f"**关键词**: {', '.join(article.topic.keywords)}\n\n"
                        article_md += "---\n\n"
                        article_md += article.content
                        article_md += "\n\n" + "="*50 + "\n\n"
                        
                        f.write(article_md)
                        markdown_content += article_md
                    
                    # 如果是Markdown格式且需要生成HTML
                    if generate_html:
                        html_file = os.path.splitext(output_file)[0] + '.html'
                        self._save_html_file(markdown_content, html_file, "文章合集")
            
            logger.info(f"文章已保存到: {output_file}")
            
            # 如果是单篇文章的Markdown，也生成对应的HTML
            if generate_html and format_type.lower() == "markdown" and len(articles) == 1:
                html_file = os.path.splitext(output_file)[0] + '.html'
                if not os.path.exists(html_file):  # 避免重复生成
                    article = articles[0]
                    single_md = f"# {article.title}\n\n"
                    single_md += f"**字数**: {article.word_count}\n\n"
                    single_md += f"**创建时间**: {article.generated_at}\n\n"
                    single_md += f"**分类**: {article.topic.category}\n\n"
                    if article.topic.keywords:
                        single_md += f"**关键词**: {', '.join(article.topic.keywords)}\n\n"
                    single_md += "---\n\n"
                    single_md += article.content
                    
                    self._save_html_file(single_md, html_file, article.title)
            
        except Exception as e:
            logger.error(f"保存文章失败: {e}")
            raise
    
    def _save_html_file(self, markdown_content: str, html_file: str, title: str) -> None:
        """
        保存HTML文件
        
        Args:
            markdown_content: Markdown内容
            html_file: HTML文件路径
            title: 文档标题
        """
        try:
            html_content = self._markdown_to_html(markdown_content)
            full_html = self._create_html_template(title, html_content)
            
            with open(html_file, 'w', encoding='utf-8') as f:
                f.write(full_html)
            
            logger.info(f"HTML文件已保存到: {html_file}")
            
        except Exception as e:
            logger.error(f"保存HTML文件失败: {e}")
            raise
    
    def close(self):
        """关闭客户端"""
        if self.wenxin_client:
            self.wenxin_client.close()
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


# 使用示例
if __name__ == "__main__":
    # 配置日志
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    
    # 配置文心智能体
    wenxin_config = WenxinConfig(
        client_id="your_client_id",
        client_secret="your_client_secret",
        app_id="your_app_id",
        secret_key="your_secret_key",
        timeout=30,
        max_retries=3
    )
    
    # 创建文章生成器
    with ArticleGenerator(wenxin_config) as generator:
        try:
            # 生成职场类型的文章
            articles = generator.generate_batch_articles(
                article_type="职场",
                count=3,
                reference_file="d:/Project/Github/ArticleWeb/example/职场赛道.txt"
            )
            
            # 保存文章
            generator.save_articles_to_file(
                articles=articles,
                output_file="generated_articles.md",
                format_type="markdown"
            )
            
            print(f"成功生成{len(articles)}篇文章")
            
        except Exception as e:
            print(f"生成文章失败: {e}")