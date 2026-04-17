#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
文章生成命令行工具

简化的命令行界面，用于快速生成文章

使用方法:
    python generate_articles.py --type 职场 --count 3
    python generate_articles.py --type 生活 --count 2 --output my_articles.md
    python generate_articles.py --topics-only --type 职场 --count 5
"""

import argparse
import sys
import logging
from pathlib import Path
from datetime import datetime

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from .article_generation_config import get_config, validate_config, ArticleType
from .article_generator import ArticleGenerator


def setup_logging(log_level: str = "INFO", log_file: str = None) -> logging.Logger:
    """
    设置日志配置
    
    Args:
        log_level: 日志级别
        log_file: 日志文件路径
        
    Returns:
        logging.Logger: 配置好的日志器
    """
    # 创建日志目录
    if log_file:
        log_dir = Path(log_file).parent
        log_dir.mkdir(parents=True, exist_ok=True)
    
    # 配置日志格式
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # 设置根日志器
    logger = logging.getLogger()
    logger.setLevel(getattr(logging, log_level.upper()))
    
    # 清除现有处理器
    logger.handlers.clear()
    
    # 控制台处理器
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # 文件处理器
    if log_file:
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    return logger


def generate_topics_only(article_type: str, count: int, output_file: str = None) -> None:
    """
    仅生成主题
    
    Args:
        article_type: 文章类型
        count: 生成数量
        output_file: 输出文件
    """
    logger = logging.getLogger(__name__)
    config = get_config()
    
    # 获取参考文件
    reference_file = config['paths']['reference_files'].get(article_type)
    
    try:
        with ArticleGenerator(config['wenxin']) as generator:
            logger.info(f"开始生成{count}个{article_type}类型的主题...")
            
            topics = generator.generate_topics(
                article_type=article_type,
                count=count,
                reference_file=reference_file
            )
            
            # 输出主题
            print(f"\n成功生成{len(topics)}个主题:")
            print("=" * 60)
            
            topic_lines = []
            for i, topic in enumerate(topics, 1):
                topic_info = f"{i}. {topic.title}"
                print(topic_info)
                topic_lines.append(topic_info)
                
                if topic.description:
                    desc_info = f"   描述: {topic.description}"
                    print(desc_info)
                    topic_lines.append(desc_info)
                
                if topic.keywords:
                    keyword_info = f"   关键词: {', '.join(topic.keywords)}"
                    print(keyword_info)
                    topic_lines.append(keyword_info)
                
                print("-" * 40)
                topic_lines.append("-" * 40)
            
            # 保存到文件
            if output_file:
                output_path = Path(output_file)
                output_path.parent.mkdir(parents=True, exist_ok=True)
                
                with open(output_path, 'w', encoding='utf-8') as f:
                    f.write(f"# {article_type}类型主题生成结果\n\n")
                    f.write(f"创建时间: {datetime.now()}\n\n")
                    f.write("\n".join(topic_lines))
                
                logger.info(f"主题已保存到: {output_file}")
    
    except Exception as e:
        logger.error(f"生成主题失败: {e}")
        raise


def generate_articles(article_type: str, 
                     count: int, 
                     output_file: str = None,
                     config_name: str = None) -> None:
    """
    生成完整文章
    
    Args:
        article_type: 文章类型
        count: 生成数量
        output_file: 输出文件
        config_name: 配置名称
    """
    logger = logging.getLogger(__name__)
    config = get_config()
    
    # 选择文章配置
    if config_name and config_name in config['articles']:
        article_config = config['articles'][config_name]
    else:
        article_config = config['articles'].get(article_type)
        if not article_config:
            raise ValueError(f"不支持的文章类型: {article_type}")
    
    # 获取参考文件
    reference_file = config['paths']['reference_files'].get(article_type)
    
    # 设置输出文件
    if not output_file:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = f"{article_type}_{timestamp}.md"
    
    try:
        with ArticleGenerator(config['wenxin']) as generator:
            logger.info(f"开始生成{count}篇{article_type}类型的文章...")
            
            articles = generator.generate_batch_articles(
                article_type=article_type,
                count=count,
                config=article_config,
                reference_file=reference_file
            )
            
            if not articles:
                logger.warning("没有成功生成任何文章")
                return
            
            # 保存文章
            output_path = Path(output_file)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            # 保存为Markdown格式
            generator.save_articles_to_file(
                articles=articles,
                output_file=str(output_path),
                format_type="markdown"
            )
            
            # 同时保存为JSON格式
            json_file = output_path.with_suffix('.json')
            generator.save_articles_to_file(
                articles=articles,
                output_file=str(json_file),
                format_type="json"
            )
            
            # 输出摘要
            print(f"\n成功生成{len(articles)}篇文章:")
            print("=" * 60)
            
            total_words = 0
            for i, article in enumerate(articles, 1):
                print(f"{i}. {article.title}")
                print(f"   字数: {article.word_count}")
                print(f"   分类: {article.topic.category}")
                total_words += article.word_count
                print("-" * 40)
            
            print(f"\n总字数: {total_words}")
            print(f"平均字数: {total_words // len(articles)}")
            print(f"\n文章已保存到:")
            print(f"  Markdown: {output_path}")
            print(f"  JSON: {json_file}")
    
    except Exception as e:
        logger.error(f"生成文章失败: {e}")
        raise


def main():
    """
    主函数
    """
    parser = argparse.ArgumentParser(
        description="文章生成工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  生成3篇职场文章:
    python generate_articles.py --type 职场 --count 3
  
  仅生成5个生活主题:
    python generate_articles.py --topics-only --type 生活 --count 5
  
  生成文章并指定输出文件:
    python generate_articles.py --type 职场 --count 2 --output my_articles.md
  
  使用特定配置生成文章:
    python generate_articles.py --type 职场 --count 1 --config 职场_短篇
        """
    )
    
    parser.add_argument(
        "--type", 
        required=True,
        choices=[article_type.chinese_name for article_type in ArticleType],
        help="文章类型"
    )
    
    parser.add_argument(
        "--count",
        type=int,
        default=3,
        help="生成数量 (默认: 3)"
    )
    
    parser.add_argument(
        "--output",
        help="输出文件路径"
    )
    
    parser.add_argument(
        "--config",
        help="文章配置名称 (如: 职场_短篇, 生活_感悟)"
    )
    
    parser.add_argument(
        "--topics-only",
        action="store_true",
        help="仅生成主题，不生成文章"
    )
    
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default="INFO",
        help="日志级别 (默认: INFO)"
    )
    
    parser.add_argument(
        "--log-file",
        help="日志文件路径"
    )
    
    parser.add_argument(
        "--validate-config",
        action="store_true",
        help="验证配置并退出"
    )
    
    args = parser.parse_args()
    
    # 设置日志
    logger = setup_logging(args.log_level, args.log_file)
    
    # 验证配置
    if args.validate_config:
        if validate_config():
            print("✓ 配置验证通过")
            sys.exit(0)
        else:
            print("✗ 配置验证失败")
            sys.exit(1)
    
    # 检查配置
    if not validate_config():
        logger.error("配置验证失败，请检查配置文件")
        sys.exit(1)
    
    try:
        print(f"文章生成工具 - {args.type}类型")
        print("=" * 50)
        
        if args.topics_only:
            # 仅生成主题
            generate_topics_only(
                article_type=args.type,
                count=args.count,
                output_file=args.output
            )
        else:
            # 生成完整文章
            generate_articles(
                article_type=args.type,
                count=args.count,
                output_file=args.output,
                config_name=args.config
            )
        
        print("\n✓ 生成完成！")
    
    except KeyboardInterrupt:
        logger.info("用户中断操作")
        print("\n操作已取消")
    except Exception as e:
        logger.error(f"操作失败: {e}")
        print(f"\n✗ 操作失败: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()