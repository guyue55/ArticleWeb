#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
文章生成工具使用示例

演示如何使用ArticleGenerator生成职场类型的文章
"""

import sys
import logging
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from wenxin_agent_client import WenxinConfig
from article_generator import ArticleGenerator, ArticleConfig
from article_generation_config import ArticleType


def main():
    """主函数"""
    # 配置日志
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('article_generation.log', encoding='utf-8')
        ]
    )
    
    logger = logging.getLogger(__name__)
    
    # 配置文心智能体（请替换为实际的配置信息）
    wenxin_config = WenxinConfig(
        client_id="ag98c7R9xxx",  # 替换为实际的client_id
        client_secret="qhAkdGHKWuxxxx",  # 替换为实际的client_secret
        app_id="ag98c7R9xxx",  # 替换为实际的app_id
        secret_key="qhAkdGHKWuxxxx",  # 替换为实际的secret_key
        timeout=60,
        max_retries=3
    )
    
    # 职场文章配置
    workplace_config = ArticleConfig(
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
    )
    
    # 参考文件路径
    reference_file = "d:/Project/Github/ArticleWeb/example/职场赛道.txt"
    
    try:
        # 创建文章生成器
        with ArticleGenerator(wenxin_config) as generator:
            logger.info("开始生成职场类型文章...")
            
            # 方法1: 分步生成（先生成主题，再生成文章）
            logger.info("=== 方法1: 分步生成 ===")
            
            # 生成主题
            topics = generator.generate_topics(
                article_type=ArticleType.WORKPLACE.chinese_name,
                count=3,
                reference_file=reference_file
            )
            
            logger.info(f"成功生成{len(topics)}个主题:")
            for i, topic in enumerate(topics, 1):
                logger.info(f"{i}. {topic.title}")
                logger.info(f"   分类: {topic.category}")
                logger.info(f"   描述: {topic.description}")
                logger.info(f"   关键词: {', '.join(topic.keywords)}")
            
            # 选择第一个主题生成文章
            if topics:
                selected_topic = topics[0]
                logger.info(f"\n正在为主题生成文章: {selected_topic.title}")
                
                article = generator.generate_article(
                    topic=selected_topic,
                    config=workplace_config
                )
                
                logger.info(f"文章生成完成，字数: {article.word_count}")
                
                # 保存单篇文章
                generator.save_articles_to_file(
                    articles=[article],
                    output_file="single_article.md",
                    format_type="markdown"
                )
                
                logger.info("单篇文章已保存到: single_article.md")
            
            # 方法2: 批量生成
            logger.info("\n=== 方法2: 批量生成 ===")
            
            batch_articles = generator.generate_batch_articles(
                article_type=ArticleType.WORKPLACE.chinese_name,
                count=2,  # 生成2篇文章
                config=workplace_config,
                reference_file=reference_file
            )
            
            logger.info(f"批量生成完成，共生成{len(batch_articles)}篇文章")
            
            # 保存批量文章（Markdown格式）
            generator.save_articles_to_file(
                articles=batch_articles,
                output_file="batch_articles.md",
                format_type="markdown"
            )
            
            # 保存批量文章（JSON格式）
            generator.save_articles_to_file(
                articles=batch_articles,
                output_file="batch_articles.json",
                format_type="json"
            )
            
            logger.info("批量文章已保存到: batch_articles.md 和 batch_articles.json")
            
            # 输出文章摘要
            logger.info("\n=== 生成的文章摘要 ===")
            for i, article in enumerate(batch_articles, 1):
                logger.info(f"文章{i}: {article.title}")
                logger.info(f"  字数: {article.word_count}")
                logger.info(f"  分类: {article.topic.category}")
                logger.info(f"  创建时间: {article.generated_at}")
                
                # 显示文章开头
                content_preview = article.content[:200].replace('\n', ' ')
                logger.info(f"  内容预览: {content_preview}...")
                logger.info("-" * 50)
    
    except Exception as e:
        logger.error(f"文章生成过程中发生错误: {e}")
        raise


def demo_life_articles():
    """演示生活类型文章生成"""
    logger = logging.getLogger(__name__)
    
    # 配置文心智能体
    wenxin_config = WenxinConfig(
        client_id="ag98c7R9xxx",
        client_secret="qhAkdGHKWuxxxx",
        app_id="ag98c7R9xxx",
        secret_key="qhAkdGHKWuxxxx",
        timeout=60,
        max_retries=3
    )
    
    # 生活文章配置
    life_config = ArticleConfig(
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
    )
    
    try:
        with ArticleGenerator(wenxin_config) as generator:
            logger.info("开始生成生活类型文章...")
            
            # 生成生活类型文章
            life_articles = generator.generate_batch_articles(
                article_type=ArticleType.LIFESTYLE.chinese_name,
                count=2,
                config=life_config
            )
            
            # 保存生活类型文章
            generator.save_articles_to_file(
                articles=life_articles,
                output_file="life_articles.md",
                format_type="markdown"
            )
            
            logger.info(f"生活类型文章生成完成，共{len(life_articles)}篇")
    
    except Exception as e:
        logger.error(f"生活文章生成失败: {e}")


def test_topic_generation_only():
    """仅测试主题生成功能"""
    logger = logging.getLogger(__name__)
    
    wenxin_config = WenxinConfig(
        client_id="ag98c7R9xxx",
        client_secret="qhAkdGHKWuxxxx",
        app_id="ag98c7R9xxx",
        secret_key="qhAkdGHKWuxxxx",
        timeout=30,
        max_retries=3
    )
    
    try:
        with ArticleGenerator(wenxin_config) as generator:
            logger.info("测试主题生成功能...")
            
            # 生成职场主题
            workplace_topics = generator.generate_topics(
                article_type=ArticleType.WORKPLACE.chinese_name,
                count=5,
                reference_file="d:/Project/Github/ArticleWeb/example/职场赛道.txt"
            )
            
            logger.info("职场主题生成结果:")
            print(workplace_topics)
            for i, topic in enumerate(workplace_topics, 1):
                logger.info(f"{i}. {topic.title}")
            
            # 生成生活主题
            life_topics = generator.generate_topics(
                article_type=ArticleType.LIFESTYLE.chinese_name,
                count=3
            )
            
            logger.info("\n生活主题生成结果:")
            for i, topic in enumerate(life_topics, 1):
                logger.info(f"{i}. {topic.title}")
    
    except Exception as e:
        logger.error(f"主题生成测试失败: {e}")


def demo_new_article_types():
    """演示新增文章类型生成"""
    logger = logging.getLogger(__name__)
    
    wenxin_config = WenxinConfig(
        client_id="ag98c7R9xxx",
        client_secret="qhAkdGHKWuxxxx",
        app_id="ag98c7R9xxx",
        secret_key="qhAkdGHKWuxxxx",
        timeout=30,
        max_retries=3
    )
    
    # 新增文章类型列表
    new_types = [
        ArticleType.LIVELIHOOD.chinese_name, 
        ArticleType.AUTOMOTIVE.chinese_name, 
        ArticleType.ENTERTAINMENT.chinese_name, 
        ArticleType.FOOD.chinese_name, 
        ArticleType.TRAVEL.chinese_name
    ]
    
    try:
        with ArticleGenerator(wenxin_config) as generator:
            logger.info("开始演示新增文章类型...")
            
            for article_type in new_types:
                logger.info(f"\n=== {article_type}文章类型演示 ===")
                
                try:
                    # 生成主题
                    topics = generator.generate_topics(
                        article_type=article_type,
                        count=3
                    )
                    
                    logger.info(f"{article_type}主题生成成功:")
                    for i, topic in enumerate(topics, 1):
                        logger.info(f"  {i}. {topic.title}")
                        logger.info(f"     分类: {topic.category}")
                        logger.info(f"     关键词: {', '.join(topic.keywords)}")
                    
                    # 为第一个主题生成文章
                    if topics:
                        config = ArticleConfig(
                            article_type=article_type,
                            min_words=1500,
                            format_type="markdown",
                            perspective="第一人称"
                        )
                        
                        article = generator.generate_article(
                            topic=topics[0],
                            config=config
                        )
                        
                        logger.info(f"文章生成成功: {article.title}")
                        logger.info(f"字数: {article.word_count}")
                        
                        # 保存文章
                        output_file = f"{article_type}_article.md"
                        generator.save_articles_to_file(
                            articles=[article],
                            output_file=output_file,
                            format_type="markdown"
                        )
                        logger.info(f"文章已保存到: {output_file}")
                        
                except Exception as e:
                    logger.error(f"{article_type}文章生成失败: {e}")
                    
    except Exception as e:
        logger.error(f"新增文章类型演示失败: {e}")


if __name__ == "__main__":
    print("文章生成工具使用示例")
    print("=" * 50)
    
    # 选择运行模式
    mode = input("请选择运行模式:\n1. 完整演示（生成职场文章）\n2. 生活文章演示\n3. 仅测试主题生成\n4. 新增文章类型演示\n请输入数字(1-4): ").strip()
    
    if mode == "1":
        print("\n开始完整演示...")
        main()
    elif mode == "2":
        print("\n开始生活文章演示...")
        demo_life_articles()
    elif mode == "3":
        print("\n开始主题生成测试...")
        test_topic_generation_only()
    elif mode == "4":
        print("\n开始新增文章类型演示...")
        demo_new_article_types()
    else:
        print("无效选择，运行默认演示...")
        main()
    
    print("\n演示完成！")