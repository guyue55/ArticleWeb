#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
文章生成定时任务管理脚本

用于启动、停止和管理文章生成定时任务
"""

import sys
import argparse
import logging
import time
import signal

# 添加项目路径
# sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# # Django设置
# os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'article_web.settings')

# try:
#     import django
#     django.setup()
# except ImportError:
#     pass

from scheduler import ArticleScheduler, get_scheduler, start_default_scheduler
from article_generator import ArticleGenerator
from article_generation_config import get_wenxin_config_from_env, ArticleType


# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('scheduler.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)


def start_scheduler(args):
    """
    启动调度器
    
    Args:
        args: 命令行参数
    """
    try:
        logger.info("正在启动文章生成调度器...")
        
        # 创建调度器实例
        scheduler = ArticleScheduler(
            wenxin_config=get_wenxin_config_from_env(),
            output_dir=args.output_dir
        )
        
        # 启动调度器
        scheduler.start()
        
        # 根据参数添加任务
        if args.default:
            # 使用默认配置
            scheduler.start_default_schedule()
            logger.info("已启动默认定时任务（每1分钟执行，每种类型3篇文章）")
        else:
            # 自定义配置
            article_types = args.types if args.types else None
            
            if args.cron:
                # 定时任务
                job_id = scheduler.add_cron_job(
                    article_types=article_types,
                    articles_per_type=args.count,
                    hour=args.hour,
                    minute=args.minute,
                    day_of_week=args.day_of_week
                )
                logger.info(f"已添加定时任务: {job_id}")
            else:
                # 间隔任务
                job_id = scheduler.add_interval_job(
                    article_types=article_types,
                    articles_per_type=args.count,
                    interval_minutes=args.interval
                )
                logger.info(f"已添加间隔任务: {job_id}")
        
        # 显示任务信息
        jobs = scheduler.get_jobs()
        logger.info(f"当前活动任务数: {len(jobs)}")
        for job in jobs:
            logger.info(f"  - {job['name']} (ID: {job['id']}) - 下次执行: {job['next_run_time']}")
        
        # 设置信号处理器
        def signal_handler(sig, frame):
            logger.info("接收到停止信号，正在关闭调度器...")
            scheduler.shutdown()
            sys.exit(0)
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        logger.info("调度器正在运行，按Ctrl+C停止...")
        
        # 保持主线程运行
        while True:
            time.sleep(10)
            # 每10秒输出一次统计信息
            stats = scheduler.get_stats()
            if stats["total_jobs"] > 0:
                logger.info(f"执行统计 - 总任务: {stats['total_jobs']}, "
                          f"成功: {stats['successful_jobs']}, "
                          f"失败: {stats['failed_jobs']}, "
                          f"生成文章: {stats['articles_generated']}篇")
            
    except KeyboardInterrupt:
        logger.info("用户中断，正在关闭调度器...")
        if 'scheduler' in locals():
            scheduler.shutdown()
    except Exception as e:
        logger.error(f"调度器运行失败: {e}")
        if 'scheduler' in locals():
            scheduler.shutdown()
        raise


def list_jobs(args):
    """
    列出所有任务
    
    Args:
        args: 命令行参数
    """
    try:
        scheduler = get_scheduler()
        jobs = scheduler.get_jobs()
        
        if not jobs:
            print("当前没有活动的任务")
            return
        
        print(f"当前活动任务数: {len(jobs)}")
        print("-" * 80)
        
        for job in jobs:
            print(f"任务ID: {job['id']}")
            print(f"任务名称: {job['name']}")
            print(f"下次执行: {job['next_run_time']}")
            print(f"触发器: {job['trigger']}")
            print("-" * 40)
        
        # 显示统计信息
        stats = scheduler.get_stats()
        print("\n执行统计:")
        print(f"  总任务数: {stats['total_jobs']}")
        print(f"  成功任务: {stats['successful_jobs']}")
        print(f"  失败任务: {stats['failed_jobs']}")
        print(f"  生成文章: {stats['articles_generated']}篇")
        
    except Exception as e:
        logger.error(f"获取任务列表失败: {e}")


def remove_job(args):
    """
    移除指定任务
    
    Args:
        args: 命令行参数
    """
    try:
        scheduler = get_scheduler()
        
        if scheduler.remove_job(args.job_id):
            print(f"成功移除任务: {args.job_id}")
        else:
            print(f"移除任务失败: {args.job_id}")
            
    except Exception as e:
        logger.error(f"移除任务失败: {e}")


def test_generation(args):
    """
    测试文章生成功能
    
    Args:
        args: 命令行参数
    """
    try:
        logger.info("开始测试文章生成功能...")
        
        # 创建文章生成器
        wenxin_config = get_wenxin_config_from_env()
        
        with ArticleGenerator(wenxin_config) as generator:
            # 设置基础输出目录
            generator.base_output_dir = args.output_dir
            
            # 执行生成任务
            article_types = args.types if args.types else [ArticleType.WORKPLACE.chinese_name]
            total_files = 0
            
            for article_type in article_types:
                try:
                    logger.info(f"正在生成{article_type}类型文章...")
                    
                    # 使用新的批量生成方法
                    generated_files = generator.generate_batch_articles(
                        article_type=article_type,
                        count=args.count,
                        output_dir=args.output_dir
                    )
                    
                    if generated_files:
                        total_files += len(generated_files)
                        logger.info(f"成功生成{len(generated_files)}篇{article_type}文章")
                        
                        # 显示生成的文件信息
                        for files_info in generated_files:
                            logger.info(f"已保存文件:")
                            logger.info(f"  Markdown: {files_info.get('markdown', 'N/A')}")
                            logger.info(f"  HTML: {files_info.get('html', 'N/A')}")
                            logger.info(f"  Meta: {files_info.get('meta', 'N/A')}")
                    
                except Exception as e:
                    logger.error(f"生成{article_type}文章失败: {e}")
                    continue
        
        logger.info(f"测试完成，共生成{total_files}篇文章")
        
    except Exception as e:
        logger.error(f"测试失败: {e}")


def main():
    """
    主函数
    """
    parser = argparse.ArgumentParser(description='文章生成定时任务管理工具')
    subparsers = parser.add_subparsers(dest='command', help='可用命令')
    
    # 启动调度器命令
    start_parser = subparsers.add_parser('start', help='启动调度器')
    start_parser.add_argument('--default', action='store_true', 
                            help='使用默认配置（每1分钟执行，每种类型3篇文章）')
    start_parser.add_argument('--types', nargs='+', 
                            choices=[article_type.chinese_name for article_type in ArticleType],
                            help='指定文章类型')
    start_parser.add_argument('--count', type=int, default=3,
                            help='每种类型生成的文章数量（默认3篇）')
    start_parser.add_argument('--interval', type=float, default=1,
                            help='执行间隔（分钟，默认1分钟）')
    start_parser.add_argument('--cron', action='store_true',
                            help='使用定时任务而非间隔任务')
    start_parser.add_argument('--hour', type=int,
                            help='定时任务的小时（0-23）')
    start_parser.add_argument('--minute', type=int,
                            help='定时任务的分钟（0-59）')
    start_parser.add_argument('--day-of-week', type=str,
                            help='定时任务的星期几（mon,tue,wed,thu,fri,sat,sun）')
    start_parser.add_argument('--output-dir', type=str, default='generated_articles',
                            help='文章输出目录（默认: generated_articles）')
    
    # 列出任务命令
    list_parser = subparsers.add_parser('list', help='列出所有任务')
    
    # 移除任务命令
    remove_parser = subparsers.add_parser('remove', help='移除指定任务')
    remove_parser.add_argument('job_id', help='要移除的任务ID')
    
    # 测试生成命令
    test_parser = subparsers.add_parser('test', help='测试文章生成功能')
    test_parser.add_argument('--types', nargs='+', 
                           choices=[article_type.chinese_name for article_type in ArticleType],
                           help='指定文章类型')
    test_parser.add_argument('--count', type=int, default=1,
                           help='每种类型生成的文章数量（默认1篇）')
    test_parser.add_argument('--output-dir', type=str, default='test_articles',
                           help='文章输出目录（默认: test_articles）')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    # 执行对应的命令
    if args.command == 'start':
        start_scheduler(args)
    elif args.command == 'list':
        list_jobs(args)
    elif args.command == 'remove':
        remove_job(args)
    elif args.command == 'test':
        test_generation(args)
    else:
        parser.print_help()


if __name__ == '__main__':
    main()