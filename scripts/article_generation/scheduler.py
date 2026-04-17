# -*- coding: utf-8 -*-
"""
通用定时任务模块

使用APScheduler实现定时生成各类文章的功能
"""

import logging
import os
import time
from datetime import datetime
from typing import Dict, List, Optional

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger
from apscheduler.events import EVENT_JOB_EXECUTED, EVENT_JOB_ERROR
from apscheduler.jobstores.memory import MemoryJobStore
from apscheduler.executors.pool import ThreadPoolExecutor

from .article_generator import ArticleGenerator, ArticleConfig
from .wenxin_agent_client import WenxinConfig
from .article_generation_config import get_wenxin_config_from_env, ARTICLE_CONFIGS
from .article_config import ArticleType

logger = logging.getLogger(__name__)


class ArticleScheduler:
    """
    文章生成定时任务调度器
    
    功能：
    1. 定时生成各类文章
    2. 支持自定义生成间隔和数量
    3. 自动保存生成的文章
    4. 任务执行状态监控
    """
    
    def __init__(self, 
                 wenxin_config: Optional[WenxinConfig] = None,
                 output_dir: str = "generated_articles",
                 db_url: str = "sqlite:///scheduler.db"):
        """
        初始化调度器
        
        Args:
            wenxin_config: 文心智能体配置
            output_dir: 文章输出目录
            db_url: 任务存储数据库URL
        """
        self.wenxin_config = wenxin_config or get_wenxin_config_from_env()
        self.output_dir = output_dir
        self.db_url = db_url
        
        # 确保输出目录存在
        os.makedirs(self.output_dir, exist_ok=True)
        
        # 配置调度器
        jobstores = {
            'default': MemoryJobStore()
        }
        executors = {
            'default': ThreadPoolExecutor(20)
        }
        job_defaults = {
            'coalesce': False,
            'max_instances': 3
        }
        
        self.scheduler = BackgroundScheduler(
            jobstores=jobstores,
            executors=executors,
            job_defaults=job_defaults,
            timezone='Asia/Shanghai'
        )
        
        # 添加事件监听器
        self.scheduler.add_listener(self._job_listener, EVENT_JOB_EXECUTED | EVENT_JOB_ERROR)
        
        # 支持的文章类型
        self.supported_types = [article_type.chinese_name for article_type in ArticleType]
        
        # 参考文件映射
        self.reference_files = {
            ArticleType.WORKPLACE.chinese_name: "d:/Project/Github/ArticleWeb/example/职场赛道.txt",
            ArticleType.LIVELIHOOD.chinese_name: "d:/Project/Github/ArticleWeb/example/民生赛道.txt",
            ArticleType.AUTOMOTIVE.chinese_name: "d:/Project/Github/ArticleWeb/example/汽车赛道.txt",
            ArticleType.ENTERTAINMENT.chinese_name: "d:/Project/Github/ArticleWeb/example/娱乐赛道.txt",
            ArticleType.LOVE_LETTERS.chinese_name: "d:/Project/Github/ArticleWeb/example/情书赛道.txt",
            ArticleType.FOOD.chinese_name: "d:/Project/Github/ArticleWeb/example/美食养号.txt",
            ArticleType.TRAVEL.chinese_name: "d:/Project/Github/ArticleWeb/example/旅游养号.txt",
            ArticleType.TRIVIA.chinese_name: "d:/Project/Github/ArticleWeb/example/冷知识养号.txt",
            ArticleType.DIARY.chinese_name: "d:/Project/Github/ArticleWeb/example/日记养号.txt"
        }
        
        # 任务执行统计
        self.job_stats = {
            "total_jobs": 0,
            "successful_jobs": 0,
            "failed_jobs": 0,
            "articles_generated": 0
        }
        
        logger.info("文章生成调度器初始化完成")
    
    def start(self):
        """启动调度器"""
        try:
            self.scheduler.start()
            logger.info("文章生成调度器已启动")
        except Exception as e:
            logger.error(f"启动调度器失败: {e}")
            raise
    
    def shutdown(self, wait: bool = True):
        """关闭调度器"""
        try:
            self.scheduler.shutdown(wait=wait)
            logger.info("文章生成调度器已关闭")
        except Exception as e:
            logger.error(f"关闭调度器失败: {e}")
    
    def add_interval_job(self, 
                        article_types: List[str] = None,
                        articles_per_type: int = 3,
                        interval_minutes: int = 1,
                        job_id: str = None) -> str:
        """
        添加间隔执行的文章生成任务
        
        Args:
            article_types: 文章类型列表，None表示所有类型
            articles_per_type: 每种类型生成的文章数量
            interval_minutes: 执行间隔（分钟）
            job_id: 任务ID，None表示自动生成
            
        Returns:
            str: 任务ID
        """
        if article_types is None:
            article_types = self.supported_types.copy()
        
        # 验证文章类型
        invalid_types = [t for t in article_types if t not in self.supported_types]
        if invalid_types:
            raise ValueError(f"不支持的文章类型: {invalid_types}")
        
        if job_id is None:
            job_id = f"article_generation_{int(time.time())}"
        
        try:
            self.scheduler.add_job(
                func=self._generate_articles_job,
                trigger=IntervalTrigger(minutes=interval_minutes),
                args=[article_types, articles_per_type],
                id=job_id,
                name=f"文章生成任务-{interval_minutes}分钟间隔",
                replace_existing=True
            )
            
            logger.info(f"已添加间隔任务: {job_id}, 间隔: {interval_minutes}分钟, 类型: {article_types}")
            return job_id
            
        except Exception as e:
            logger.error(f"添加间隔任务失败: {e}")
            raise
    
    def add_cron_job(self,
                    article_types: List[str] = None,
                    articles_per_type: int = 3,
                    hour: int = None,
                    minute: int = None,
                    second: int = 0,
                    day_of_week: str = None,
                    job_id: str = None) -> str:
        """
        添加定时执行的文章生成任务
        
        Args:
            article_types: 文章类型列表，None表示所有类型
            articles_per_type: 每种类型生成的文章数量
            hour: 小时（0-23）
            minute: 分钟（0-59）
            second: 秒（0-59）
            day_of_week: 星期几（mon,tue,wed,thu,fri,sat,sun）
            job_id: 任务ID，None表示自动生成
            
        Returns:
            str: 任务ID
        """
        if article_types is None:
            article_types = self.supported_types.copy()
        
        # 验证文章类型
        invalid_types = [t for t in article_types if t not in self.supported_types]
        if invalid_types:
            raise ValueError(f"不支持的文章类型: {invalid_types}")
        
        if job_id is None:
            job_id = f"article_cron_{int(time.time())}"
        
        try:
            self.scheduler.add_job(
                func=self._generate_articles_job,
                trigger=CronTrigger(
                    hour=hour,
                    minute=minute,
                    second=second,
                    day_of_week=day_of_week
                ),
                args=[article_types, articles_per_type],
                id=job_id,
                name=f"文章生成定时任务-{hour}:{minute}",
                replace_existing=True
            )
            
            logger.info(f"已添加定时任务: {job_id}, 时间: {hour}:{minute}, 类型: {article_types}")
            return job_id
            
        except Exception as e:
            logger.error(f"添加定时任务失败: {e}")
            raise
    
    def remove_job(self, job_id: str) -> bool:
        """
        移除指定任务
        
        Args:
            job_id: 任务ID
            
        Returns:
            bool: 是否成功移除
        """
        try:
            self.scheduler.remove_job(job_id)
            logger.info(f"已移除任务: {job_id}")
            return True
        except Exception as e:
            logger.error(f"移除任务失败: {job_id}, 错误: {e}")
            return False
    
    def get_jobs(self) -> List[Dict]:
        """
        获取所有任务信息
        
        Returns:
            List[Dict]: 任务信息列表
        """
        jobs = []
        for job in self.scheduler.get_jobs():
            jobs.append({
                "id": job.id,
                "name": job.name,
                "next_run_time": job.next_run_time.isoformat() if job.next_run_time else None,
                "trigger": str(job.trigger)
            })
        return jobs
    
    def get_stats(self) -> Dict:
        """
        获取任务执行统计信息
        
        Returns:
            Dict: 统计信息
        """
        return self.job_stats.copy()
    
    def _generate_articles_job(self, article_types: List[str], articles_per_type: int):
        """
        文章生成任务执行函数
        
        Args:
            article_types: 文章类型列表
            articles_per_type: 每种类型生成的文章数量
        """
        job_start_time = datetime.now()
        logger.info(f"开始执行文章生成任务: {article_types}, 每种类型{articles_per_type}篇")
        
        self.job_stats["total_jobs"] += 1
        
        try:
            with ArticleGenerator(self.wenxin_config) as generator:
                total_articles = 0
                
                for article_type in article_types:
                    try:
                        logger.info(f"正在生成{article_type}类型文章...")
                        
                        # 获取配置
                        config = ARTICLE_CONFIGS.get(article_type)
                        if not config:
                            config = ArticleConfig(article_type=article_type)
                        
                        # 获取参考文件
                        reference_file = self.reference_files.get(article_type)
                        
                        # 使用新的批量生成方法（自动保存单独文件）
                        generated_files = generator.generate_batch_articles(
                            article_type=article_type,
                            count=articles_per_type,
                            config=config,
                            reference_file=reference_file,
                            output_dir=self.output_dir
                        )
                        
                        if generated_files:
                            total_articles += len(generated_files)
                            logger.info(f"成功生成并保存{len(generated_files)}篇{article_type}文章")
                            
                            # 记录生成的文件信息
                            for files_info in generated_files:
                                logger.info(f"已保存文件: {files_info.get('markdown', 'N/A')}")
                        
                        # 添加延迟避免API限制
                        time.sleep(3)
                        
                    except Exception as e:
                        logger.error(f"生成{article_type}文章失败: {e}")
                        continue
                
                # 更新统计信息
                self.job_stats["successful_jobs"] += 1
                self.job_stats["articles_generated"] += total_articles
                
                job_duration = (datetime.now() - job_start_time).total_seconds()
                logger.info(f"文章生成任务完成，共生成{total_articles}篇文章，耗时{job_duration:.2f}秒")
                
        except Exception as e:
            self.job_stats["failed_jobs"] += 1
            logger.error(f"文章生成任务执行失败: {e}")
            raise
    
    def _job_listener(self, event):
        """
        任务事件监听器
        
        Args:
            event: 任务事件
        """
        if event.exception:
            logger.error(f"任务执行失败: {event.job_id}, 异常: {event.exception}")
        else:
            logger.info(f"任务执行成功: {event.job_id}")
    
    def start_default_schedule(self):
        """
        启动默认的定时任务配置
        
        默认配置：
        - 每1分钟执行一次
        - 每种类型生成3篇文章
        - 包含所有支持的文章类型
        """
        try:
            job_id = self.add_interval_job(
                article_types=self.supported_types,
                articles_per_type=3,
                interval_minutes=1,
                job_id="default_article_generation"
            )
            
            logger.info(f"已启动默认定时任务: {job_id}")
            return job_id
            
        except Exception as e:
            logger.error(f"启动默认定时任务失败: {e}")
            raise


# 全局调度器实例
_scheduler_instance = None


def get_scheduler() -> ArticleScheduler:
    """
    获取全局调度器实例（单例模式）
    
    Returns:
        ArticleScheduler: 调度器实例
    """
    global _scheduler_instance
    if _scheduler_instance is None:
        _scheduler_instance = ArticleScheduler()
    return _scheduler_instance


def start_default_scheduler():
    """
    启动默认的文章生成调度器
    
    这是一个便捷函数，用于快速启动默认配置的调度器
    """
    scheduler = get_scheduler()
    scheduler.start()
    scheduler.start_default_schedule()
    logger.info("默认文章生成调度器已启动")
    return scheduler


if __name__ == "__main__":
    # 配置日志
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # 启动默认调度器
    try:
        scheduler = start_default_scheduler()
        
        # 保持程序运行
        import signal
        import sys
        
        def signal_handler(sig, frame):
            logger.info("接收到停止信号，正在关闭调度器...")
            scheduler.shutdown()
            sys.exit(0)
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        logger.info("调度器正在运行，按Ctrl+C停止...")
        
        # 保持主线程运行
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        logger.info("用户中断，正在关闭调度器...")
        if 'scheduler' in locals():
            scheduler.shutdown()
    except Exception as e:
        logger.error(f"调度器运行失败: {e}")
        if 'scheduler' in locals():
            scheduler.shutdown()
        raise