#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
文章生成定时任务使用示例

展示如何使用ArticleScheduler进行文章定时生成
"""

import os
import sys
import logging
import time
from datetime import datetime

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Django设置
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'article_web.settings')

try:
    import django
    django.setup()
except ImportError:
    pass

from apps.common.scheduler import ArticleScheduler
from config.article_generation_config import get_wenxin_config_from_env, ArticleType

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def example_basic_usage():
    """
    基本使用示例
    """
    print("=== 基本使用示例 ===")
    
    # 创建调度器
    scheduler = ArticleScheduler(
        wenxin_config=get_wenxin_config_from_env(),
        output_dir="example_articles"
    )
    
    try:
        # 启动调度器
        scheduler.start()
        
        # 添加间隔任务：每2分钟生成职场和生活类型文章各2篇
        job_id = scheduler.add_interval_job(
            article_types=[ArticleType.WORKPLACE.chinese_name, ArticleType.LIFESTYLE.chinese_name],
            articles_per_type=2,
            interval_minutes=2
        )
        
        print(f"已添加间隔任务: {job_id}")
        
        # 运行5分钟后停止
        print("任务将运行5分钟...")
        time.sleep(300)  # 5分钟
        
    finally:
        scheduler.shutdown()
        print("调度器已关闭")


def example_cron_job():
    """
    定时任务示例
    """
    print("=== 定时任务示例 ===")
    
    scheduler = ArticleScheduler(
        wenxin_config=get_wenxin_config_from_env(),
        output_dir="cron_articles"
    )
    
    try:
        scheduler.start()
        
        # 添加定时任务：每天上午9点生成所有类型文章各1篇
        job_id = scheduler.add_cron_job(
            article_types=None,  # 所有类型
            articles_per_type=1,
            hour=9,
            minute=0
        )
        
        print(f"已添加定时任务: {job_id} (每天9:00执行)")
        
        # 添加工作日定时任务：周一到周五下午6点生成职场文章3篇
        job_id2 = scheduler.add_cron_job(
            article_types=[ArticleType.WORKPLACE.chinese_name],
            articles_per_type=3,
            hour=18,
            minute=0,
            day_of_week="mon-fri"
        )
        
        print(f"已添加工作日任务: {job_id2} (周一到周五18:00执行)")
        
        # 显示所有任务
        jobs = scheduler.get_jobs()
        print(f"\n当前任务列表 ({len(jobs)}个):")
        for job in jobs:
            print(f"  - {job['name']} (ID: {job['id']})")
            print(f"    下次执行: {job['next_run_time']}")
        
        print("\n按Ctrl+C停止...")
        while True:
            time.sleep(10)
            
    except KeyboardInterrupt:
        print("\n用户中断")
    finally:
        scheduler.shutdown()
        print("调度器已关闭")


def example_multiple_jobs():
    """
    多任务管理示例
    """
    print("=== 多任务管理示例 ===")
    
    scheduler = ArticleScheduler(
        wenxin_config=get_wenxin_config_from_env(),
        output_dir="multi_articles"
    )
    
    try:
        scheduler.start()
        
        # 添加多个不同的任务
        jobs = []
        
        # 任务1：每1分钟生成职场文章1篇
        job1 = scheduler.add_interval_job(
            article_types=[ArticleType.WORKPLACE.chinese_name],
            articles_per_type=1,
            interval_minutes=1,
            job_id="workplace_articles"
        )
        jobs.append(job1)
        
        # 任务2：每3分钟生成生活文章2篇
        job2 = scheduler.add_interval_job(
            article_types=[ArticleType.LIFESTYLE.chinese_name],
            articles_per_type=2,
            interval_minutes=3,
            job_id="life_articles"
        )
        jobs.append(job2)
        
        # 任务3：每5分钟生成娱乐和美食文章各1篇
        job3 = scheduler.add_interval_job(
            article_types=[ArticleType.ENTERTAINMENT.chinese_name, ArticleType.FOOD.chinese_name],
            articles_per_type=1,
            interval_minutes=5,
            job_id="entertainment_food_articles"
        )
        jobs.append(job3)
        
        print(f"已添加{len(jobs)}个任务")
        
        # 运行10分钟
        print("任务将运行10分钟...")
        start_time = time.time()
        
        while time.time() - start_time < 600:  # 10分钟
            time.sleep(30)  # 每30秒检查一次
            
            # 显示统计信息
            stats = scheduler.get_stats()
            print(f"\n当前统计 ({datetime.now().strftime('%H:%M:%S')}):")
            print(f"  总任务: {stats['total_jobs']}")
            print(f"  成功: {stats['successful_jobs']}")
            print(f"  失败: {stats['failed_jobs']}")
            print(f"  生成文章: {stats['articles_generated']}篇")
        
        # 演示移除任务
        print("\n移除第一个任务...")
        if scheduler.remove_job(job1):
            print(f"成功移除任务: {job1}")
        
        # 再运行2分钟
        print("继续运行2分钟...")
        time.sleep(120)
        
    finally:
        scheduler.shutdown()
        print("调度器已关闭")


def example_default_scheduler():
    """
    默认调度器示例
    """
    print("=== 默认调度器示例 ===")
    
    from apps.common.scheduler import start_default_scheduler
    
    try:
        # 启动默认调度器（每1分钟执行，每种类型3篇文章）
        scheduler = start_default_scheduler()
        
        print("默认调度器已启动")
        print("配置：每1分钟执行一次，每种类型生成3篇文章")
        print("支持的文章类型：职场、生活、民生、汽车、娱乐、教育、情书、美食、旅游、冷知识、日记")
        
        # 运行3分钟
        print("\n任务将运行3分钟...")
        for i in range(18):  # 3分钟 = 18 * 10秒
            time.sleep(10)
            
            if i % 6 == 0:  # 每分钟显示一次
                stats = scheduler.get_stats()
                print(f"\n第{i//6 + 1}分钟统计:")
                print(f"  执行任务: {stats['total_jobs']}次")
                print(f"  生成文章: {stats['articles_generated']}篇")
        
    except KeyboardInterrupt:
        print("\n用户中断")
    finally:
        if 'scheduler' in locals():
            scheduler.shutdown()
        print("调度器已关闭")


def example_test_generation():
    """
    测试文章生成示例
    """
    print("=== 测试文章生成示例 ===")
    
    scheduler = ArticleScheduler(
        wenxin_config=get_wenxin_config_from_env(),
        output_dir="test_articles"
    )
    
    try:
        print("测试生成职场类型文章1篇...")
        
        # 直接调用生成方法进行测试
        scheduler._generate_articles_job(["职场"], 1)
        
        print("测试完成，请检查 test_articles 目录")
        
        # 显示统计信息
        stats = scheduler.get_stats()
        print(f"\n生成统计:")
        print(f"  执行任务: {stats['total_jobs']}次")
        print(f"  成功任务: {stats['successful_jobs']}次")
        print(f"  生成文章: {stats['articles_generated']}篇")
        
    except Exception as e:
        print(f"测试失败: {e}")


def main():
    """
    主函数 - 选择要运行的示例
    """
    examples = {
        "1": ("基本使用示例", example_basic_usage),
        "2": ("定时任务示例", example_cron_job),
        "3": ("多任务管理示例", example_multiple_jobs),
        "4": ("默认调度器示例", example_default_scheduler),
        "5": ("测试文章生成", example_test_generation)
    }
    
    print("文章生成定时任务示例")
    print("=" * 30)
    
    for key, (name, _) in examples.items():
        print(f"{key}. {name}")
    
    print("\n请选择要运行的示例 (1-5):")
    
    try:
        choice = input().strip()
        
        if choice in examples:
            name, func = examples[choice]
            print(f"\n运行: {name}")
            print("=" * 50)
            func()
        else:
            print("无效选择")
            
    except KeyboardInterrupt:
        print("\n用户取消")
    except Exception as e:
        print(f"\n运行失败: {e}")


if __name__ == "__main__":
    main()