# -*- coding: utf-8 -*-
"""
文章生成配置文件

包含文心智能体配置和文章生成相关配置
"""

import os
from typing import Dict, Any

from .article_config import ArticleType
from .wenxin_agent_client import WenxinConfig
from .article_generator import ArticleConfig


# 文心智能体配置
# 注意：请将以下配置替换为您实际的API密钥
WENXIN_CONFIG = WenxinConfig(
    client_id="ag98c7R9xxx",  # 请替换为实际的API Key
    client_secret="qhAkdGHKWuxxxx",  # 请替换为实际的Secret Key
    app_id="ag98c7R9xxx",  # 请替换为实际的智能体ID
    secret_key="qhAkdGHKWuxxxx",  # 请替换为实际的智能体Secret Key
    timeout=60,  # 请求超时时间（秒）
    max_retries=3  # 最大重试次数
)

# 从环境变量读取配置（推荐用于生产环境）
def get_wenxin_config_from_env() -> WenxinConfig:
    """
    从环境变量读取文心智能体配置
    
    环境变量：
    - WENXIN_CLIENT_ID: API Key
    - WENXIN_CLIENT_SECRET: Secret Key
    - WENXIN_APP_ID: 智能体ID
    - WENXIN_SECRET_KEY: 智能体Secret Key
    """
    return WenxinConfig(
        client_id=os.getenv("WENXIN_CLIENT_ID", WENXIN_CONFIG.client_id),
        client_secret=os.getenv("WENXIN_CLIENT_SECRET", WENXIN_CONFIG.client_secret),
        app_id=os.getenv("WENXIN_APP_ID", WENXIN_CONFIG.app_id),
        secret_key=os.getenv("WENXIN_SECRET_KEY", WENXIN_CONFIG.secret_key),
        timeout=int(os.getenv("WENXIN_TIMEOUT", "60")),
        max_retries=int(os.getenv("WENXIN_MAX_RETRIES", "3"))
    )


# 预定义的文章配置
ARTICLE_CONFIGS = {
    ArticleType.WORKPLACE.chinese_name: ArticleConfig(
        article_type=ArticleType.WORKPLACE.chinese_name,
        min_words=1800,
        format_type="markdown",
        perspective="第一人称",
        structure={
            "开头": 300,
            "主体故事": 500,
            "分析部分": 800,
            "结尾": 300
        }
    ),
    f"{ArticleType.WORKPLACE.chinese_name}_短篇": ArticleConfig(
        article_type=ArticleType.WORKPLACE.chinese_name,
        min_words=1200,
        format_type="markdown",
        perspective="第一人称",
        structure={
            "开头": 200,
            "主体故事": 400,
            "分析部分": 500,
            "结尾": 200
        }
    ),
    ArticleType.LIFESTYLE.chinese_name: ArticleConfig(
        article_type=ArticleType.LIFESTYLE.chinese_name,
        min_words=1500,
        format_type="markdown",
        perspective="第一人称",
        structure={
            "引言": 200,
            "个人经历": 400,
            "深度思考": 600,
            "实用建议": 300,
            "总结": 200
        }
    ),
    f"{ArticleType.LIFESTYLE.chinese_name}_感悟": ArticleConfig(
        article_type=ArticleType.LIFESTYLE.chinese_name,
        min_words=1000,
        format_type="markdown",
        perspective="第一人称",
        structure={
            "开篇": 150,
            "故事叙述": 350,
            "感悟思考": 400,
            "结语": 150
        }
    ),
    ArticleType.LIVELIHOOD.chinese_name: ArticleConfig(
        article_type=ArticleType.LIVELIHOOD.chinese_name,
        min_words=1400,
        format_type="markdown",
        perspective="第三人称",
        structure={
            "事件背景": 300,
            "问题分析": 400,
            "影响评估": 400,
            "建议展望": 300
        }
    ),
    ArticleType.AUTOMOTIVE.chinese_name: ArticleConfig(
        article_type=ArticleType.AUTOMOTIVE.chinese_name,
        min_words=1250,
        format_type="markdown",
        perspective="第三人称",
        structure={
            "产品介绍": 300,
            "性能分析": 400,
            "市场对比": 350,
            "购买建议": 200
        }
    ),
    ArticleType.ENTERTAINMENT.chinese_name: ArticleConfig(
        article_type=ArticleType.ENTERTAINMENT.chinese_name,
        min_words=1000,
        format_type="markdown",
        perspective="第一人称",
        structure={
            "热点事件": 200,
            "背景介绍": 250,
            "观点分析": 350,
            "趣味点评": 200
        }
    ),
    ArticleType.EDUCATION.chinese_name: ArticleConfig(
        article_type=ArticleType.EDUCATION.chinese_name,
        min_words=1550,
        format_type="markdown",
        perspective="第三人称",
        structure={
            "教育现象": 300,
            "问题分析": 450,
            "解决方案": 450,
            "实践建议": 350
        }
    ),
    ArticleType.LOVE_LETTERS.chinese_name: ArticleConfig(
        article_type=ArticleType.LOVE_LETTERS.chinese_name,
        min_words=800,
        format_type="markdown",
        perspective="第一人称",
        structure={
            "情感铺垫": 150,
            "回忆描述": 250,
            "情感表达": 250,
            "未来憧憬": 150
        }
    ),
    ArticleType.FOOD.chinese_name: ArticleConfig(
        article_type=ArticleType.FOOD.chinese_name,
        min_words=1200,
        format_type="markdown",
        perspective="第一人称",
        structure={
            "美食介绍": 250,
            "制作过程": 350,
            "品尝体验": 350,
            "营养价值": 250
        }
    ),
    ArticleType.TRAVEL.chinese_name: ArticleConfig(
        article_type=ArticleType.TRAVEL.chinese_name,
        min_words=1400,
        format_type="markdown",
        perspective="第一人称",
        structure={
            "目的地介绍": 300,
            "行程安排": 350,
            "体验分享": 450,
            "实用建议": 300
        }
    ),
    ArticleType.TRIVIA.chinese_name: ArticleConfig(
        article_type=ArticleType.TRIVIA.chinese_name,
        min_words=1000,
        format_type="markdown",
        perspective="第三人称",
        structure={
            "问题提出": 200,
            "科学解释": 400,
            "相关拓展": 250,
            "趣味总结": 150
        }
    ),
    ArticleType.DIARY.chinese_name: ArticleConfig(
        article_type=ArticleType.DIARY.chinese_name,
        min_words=800,
        format_type="markdown",
        perspective="第一人称",
        structure={
            "时间背景": 150,
            "事件记录": 300,
            "感受思考": 250,
            "心情总结": 100
        }
    )
}


# 文件路径配置
PATH_CONFIG = {
    "reference_files": {
        ArticleType.WORKPLACE.chinese_name: "d:/Project/Github/ArticleWeb/example/职场赛道.txt",
        ArticleType.LIFESTYLE.chinese_name: "d:/Project/Github/ArticleWeb/example/生活赛道.txt",
        ArticleType.LIVELIHOOD.chinese_name: "d:/Project/Github/ArticleWeb/example/民生赛道.txt",
        ArticleType.AUTOMOTIVE.chinese_name: "d:/Project/Github/ArticleWeb/example/汽车赛道.txt",
        ArticleType.ENTERTAINMENT.chinese_name: "d:/Project/Github/ArticleWeb/example/娱乐赛道.txt",
        ArticleType.EDUCATION.chinese_name: "d:/Project/Github/ArticleWeb/example/教育赛道.txt",
        ArticleType.LOVE_LETTERS.chinese_name: "d:/Project/Github/ArticleWeb/example/情书赛道.txt",
        ArticleType.FOOD.chinese_name: "d:/Project/Github/ArticleWeb/example/美食养号.txt",
        ArticleType.TRAVEL.chinese_name: "d:/Project/Github/ArticleWeb/example/旅游养号.txt",
        ArticleType.TRIVIA.chinese_name: "d:/Project/Github/ArticleWeb/example/冷知识养号.txt",
        ArticleType.DIARY.chinese_name: "d:/Project/Github/ArticleWeb/example/日记养号.txt"
    },
    "output_dir": "d:/Project/Github/ArticleWeb/generated_articles",
    "log_file": "d:/Project/Github/ArticleWeb/logs/article_generation.log"
}


# 生成参数配置
GENERATION_CONFIG = {
    "default_topic_count": 5,  # 默认生成主题数量
    "default_article_count": 3,  # 默认生成文章数量
    "batch_delay": 2,  # 批量生成时的延迟（秒）
    "max_retry_count": 3,  # 最大重试次数
    "enable_auto_save": True,  # 是否自动保存
    "save_formats": ["markdown", "json"],  # 保存格式
}


# 高级配置
ADVANCED_CONFIG = {
    "topic_generation": {
        "use_reference_file": True,  # 是否使用参考文件
        "reference_lines_limit": 50,  # 参考文件读取行数限制
        "topic_length_range": (20, 50),  # 主题长度范围
        "enable_keyword_extraction": True,  # 是否启用关键词提取
    },
    "article_generation": {
        "enable_quality_check": True,  # 是否启用质量检查
        "min_word_count_ratio": 0.8,  # 最小字数比例（相对于要求字数）
        "max_generation_time": 180,  # 最大生成时间（秒）
        "enable_content_filter": True,  # 是否启用内容过滤
    },
    "output": {
        "include_metadata": True,  # 是否包含元数据
        "include_generation_stats": True,  # 是否包含生成统计
        "auto_create_dirs": True,  # 是否自动创建目录
        "backup_existing_files": True,  # 是否备份已存在的文件
    }
}


# 模板配置扩展
EXTENDED_TEMPLATES = {
    ArticleType.WORKPLACE.chinese_name: {
        "专业领域": [
            "技术开发", "产品管理", "市场营销", "人力资源", 
            "财务会计", "销售业务", "运营管理", "设计创意"
        ],
        "职级层次": [
            "实习生", "初级员工", "中级员工", "高级员工", 
            "主管", "经理", "总监", "VP", "CEO"
        ],
        "公司类型": [
            "互联网公司", "传统企业", "外企", "国企", 
            "创业公司", "上市公司", "民营企业", "事业单位"
        ],
        "热点话题": [
            "996工作制", "远程办公", "职场PUA", "内卷现象",
            "副业发展", "技能提升", "职业规划", "跳槽策略"
        ]
    },
    ArticleType.LIFESTYLE.chinese_name: {
        "生活场景": [
            "家庭生活", "社交圈子", "个人成长", "兴趣爱好",
            "健康养生", "理财投资", "旅行见闻", "学习进修"
        ],
        "情感主题": [
            "亲情", "友情", "爱情", "师生情", 
            "邻里关系", "同事关系", "网友关系", "陌生人善意"
        ],
        "人生阶段": [
            "学生时代", "初入社会", "职场打拼", "成家立业",
            "中年危机", "养老规划", "退休生活", "人生感悟"
        ],
        "生活哲理": [
            "时间管理", "情绪管理", "人际交往", "自我提升",
            "价值观念", "生活态度", "幸福定义", "人生意义"
        ]
    },
    ArticleType.LIVELIHOOD.chinese_name: {
        "关注领域": ["住房", "教育", "医疗", "就业", "养老", "交通", "环保", "食品安全"],
        "政策类型": ["房地产政策", "教育改革", "医保政策", "就业政策", "养老保险", "环保政策"],
        "社会问题": ["房价上涨", "教育公平", "看病难", "就业压力", "养老负担", "环境污染"],
        "民众关切": ["生活成本", "收入水平", "社会保障", "公共服务", "权益保护", "生活质量"]
    },
    ArticleType.AUTOMOTIVE.chinese_name: {
        "车型分类": ["轿车", "SUV", "MPV", "跑车", "皮卡", "新能源车", "混动车", "电动车"],
        "品牌类型": ["豪华品牌", "合资品牌", "自主品牌", "新势力品牌", "进口品牌"],
        "关注要素": ["价格", "性能", "配置", "油耗", "安全", "舒适性", "保值率", "售后服务"],
        "市场趋势": ["降价促销", "新车上市", "技术升级", "政策变化", "市场竞争", "消费趋势"]
    },
    ArticleType.ENTERTAINMENT.chinese_name: {
        "娱乐类型": ["影视", "音乐", "综艺", "游戏", "直播", "短视频", "明星八卦", "网络热点"],
        "内容形式": ["电影", "电视剧", "综艺节目", "音乐作品", "游戏评测", "明星动态"],
        "话题热点": ["新剧上映", "明星恋情", "综艺爆料", "游戏更新", "网络梗", "热搜事件"],
        "观众群体": ["年轻人", "中年人", "学生群体", "上班族", "粉丝群体", "路人观众"]
    },
    ArticleType.EDUCATION.chinese_name: {
        "教育阶段": ["学前教育", "小学教育", "中学教育", "高等教育", "职业教育", "成人教育"],
        "教育问题": ["教育公平", "减负问题", "升学压力", "师资不足", "教育资源", "教育成本"],
        "教育方式": ["传统教育", "在线教育", "素质教育", "应试教育", "国际教育", "家庭教育"],
        "关注焦点": ["教学质量", "学生发展", "教师待遇", "教育改革", "技能培养", "创新能力"]
    },
    ArticleType.LOVE_LETTERS.chinese_name: {
        "情感阶段": ["初恋", "热恋", "长久恋爱", "异地恋", "重逢", "求婚", "结婚纪念", "分别时刻"],
        "表达方式": ["深情告白", "温柔倾诉", "浪漫回忆", "未来憧憬", "思念表达", "感谢话语"],
        "情感元素": ["甜蜜", "思念", "承诺", "感动", "浪漫", "真诚", "温暖", "深情"],
        "场景设定": ["初次相遇", "特殊节日", "纪念日", "分别时刻", "重要时刻", "日常生活"]
    },
    ArticleType.FOOD.chinese_name: {
        "菜系分类": ["川菜", "粤菜", "鲁菜", "苏菜", "浙菜", "闽菜", "湘菜", "徽菜", "西餐", "日料"],
        "食材类型": ["肉类", "海鲜", "蔬菜", "水果", "谷物", "豆类", "调料", "特色食材"],
        "烹饪方式": ["炒", "煮", "蒸", "炖", "烤", "炸", "凉拌", "腌制", "烘焙"],
        "营养价值": ["蛋白质", "维生素", "矿物质", "膳食纤维", "抗氧化", "低脂", "高钙", "补血"]
    },
    ArticleType.TRAVEL.chinese_name: {
        "目的地类型": ["自然风光", "历史古迹", "现代都市", "海滨度假", "山地探险", "文化体验", "美食之旅"],
        "旅行方式": ["自由行", "跟团游", "自驾游", "背包客", "度假村", "邮轮旅行", "商务旅行"],
        "季节特色": ["春季赏花", "夏季避暑", "秋季观叶", "冬季滑雪", "四季皆宜"],
        "体验内容": ["美食品尝", "文化体验", "户外活动", "购物娱乐", "放松休闲", "探险刺激"]
    },
    ArticleType.TRIVIA.chinese_name: {
        "知识领域": ["自然科学", "历史文化", "生物世界", "物理现象", "化学反应", "天文地理", "人体奥秘"],
        "趣味程度": ["令人惊讶", "颠覆认知", "有趣好玩", "实用有用", "神奇奥妙", "意想不到"],
        "科普方式": ["简单解释", "类比说明", "实验证明", "历史追溯", "数据对比", "图文并茂"],
        "应用价值": ["生活常识", "学习知识", "谈资话题", "科学素养", "思维启发", "兴趣培养"]
    },
    ArticleType.DIARY.chinese_name: {
        "记录内容": ["日常生活", "工作学习", "情感变化", "重要事件", "旅行见闻", "读书感悟", "人际交往"],
        "情感色彩": ["开心快乐", "平静安详", "忧愁烦恼", "激动兴奋", "感动温暖", "反思深沉"],
        "写作风格": ["真实记录", "情感流露", "理性分析", "诗意表达", "幽默风趣", "深度思考"],
        "生活场景": ["家庭时光", "工作日常", "学习生活", "社交活动", "独处时刻", "特殊经历"]
    }
}


def get_config(config_type: str = "default") -> Dict[str, Any]:
    """
    获取配置信息
    
    Args:
        config_type: 配置类型 (default, production, development)
        
    Returns:
        Dict[str, Any]: 配置字典
    """
    base_config = {
        "wenxin": get_wenxin_config_from_env(),
        "articles": ARTICLE_CONFIGS,
        "paths": PATH_CONFIG,
        "generation": GENERATION_CONFIG,
        "advanced": ADVANCED_CONFIG,
        "templates": EXTENDED_TEMPLATES
    }
    
    if config_type == "production":
        # 生产环境配置调整
        base_config["generation"]["batch_delay"] = 3
        base_config["generation"]["max_retry_count"] = 5
        base_config["advanced"]["article_generation"]["max_generation_time"] = 300
    elif config_type == "development":
        # 开发环境配置调整
        base_config["generation"]["default_topic_count"] = 2
        base_config["generation"]["default_article_count"] = 1
        base_config["generation"]["batch_delay"] = 1
    
    return base_config


def validate_config() -> bool:
    """
    验证配置是否有效
    
    Returns:
        bool: 配置是否有效
    """
    try:
        config = get_wenxin_config_from_env()
        
        # 检查必要的配置项
        required_fields = ['client_id', 'client_secret', 'app_id', 'secret_key']
        for field in required_fields:
            value = getattr(config, field)
            if not value or value == "your_" + field:
                print(f"警告: {field} 未正确配置")
                return False
        
        print("配置验证通过")
        return True
        
    except Exception as e:
        print(f"配置验证失败: {e}")
        return False


if __name__ == "__main__":
    print("文章生成配置信息")
    print("=" * 50)
    
    # 验证配置
    if validate_config():
        print("✓ 配置验证通过")
    else:
        print("✗ 配置验证失败，请检查配置信息")
    
    # 显示配置摘要
    config = get_config()
    print(f"\n支持的文章类型: {list(config['articles'].keys())}")
    print(f"默认主题生成数量: {config['generation']['default_topic_count']}")
    print(f"默认文章生成数量: {config['generation']['default_article_count']}")
    print(f"输出目录: {config['paths']['output_dir']}")