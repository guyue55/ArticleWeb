"""后台文章扫描调度器

这个模块提供了一个轻量级的后台调度器，用于在Django应用启动后
自动执行定时文章扫描任务，无需数据库记录。
"""

import threading
import time
import logging
from typing import Optional
from django.conf import settings
from django.core.management import call_command
from django.utils import timezone

logger = logging.getLogger(__name__)


class BackgroundArticleScheduler:
    """后台文章扫描调度器
    
    这个调度器在Django应用启动后运行，定期执行文章扫描任务。
    它运行在单独的线程中，不会阻塞主应用。
    """
    
    def __init__(self):
        """初始化调度器"""
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._running = False
        
        # 从设置中获取配置
        self.enabled = getattr(settings, 'ARTICLE_SCAN_ENABLED', True)
        self.interval = getattr(settings, 'ARTICLE_SCAN_INTERVAL', 3600)  # 默认1小时
        self.generated_dir = getattr(settings, 'ARTICLE_GENERATED_DIR', '')
        self.static_dir = getattr(settings, 'ARTICLE_STATIC_DIR', '')
        
        logger.info(f"后台文章扫描调度器初始化 - 启用: {self.enabled}, 间隔: {self.interval}秒")
    
    def start(self) -> None:
        """启动调度器
        
        在单独的线程中启动调度器，开始定期执行扫描任务。
        """
        if not self.enabled:
            logger.info("文章扫描调度器已禁用，跳过启动")
            return
            
        if self._running:
            logger.warning("调度器已在运行中")
            return
            
        self._running = True
        self._stop_event.clear()
        
        self._thread = threading.Thread(
            target=self._run_scheduler,
            name="ArticleSchedulerThread",
            daemon=True
        )
        self._thread.start()
        
        logger.info(f"后台文章扫描调度器已启动，扫描间隔: {self.interval}秒")
    
    def stop(self) -> None:
        """停止调度器
        
        停止调度器线程并等待其完成。
        """
        if not self._running:
            return
            
        logger.info("正在停止后台文章扫描调度器...")
        
        self._stop_event.set()
        self._running = False
        
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=5.0)
            
        logger.info("后台文章扫描调度器已停止")
    
    def _run_scheduler(self) -> None:
        """调度器主循环
        
        在单独的线程中运行，定期执行扫描任务。
        """
        logger.info("调度器线程开始运行")
        
        # 等待Django完全启动（延迟30秒）
        if self._stop_event.wait(30):
            return
            
        while not self._stop_event.is_set():
            try:
                self._execute_scan_task()
            except Exception as e:
                logger.error(f"执行扫描任务时发生错误: {e}", exc_info=True)
            
            # 等待下次执行或停止信号
            if self._stop_event.wait(self.interval):
                break
                
        logger.info("调度器线程结束")
    
    def _execute_scan_task(self) -> None:
        """执行文章扫描任务
        
        调用Django管理命令执行文章扫描。
        """
        try:
            start_time = timezone.now()
            logger.info(f"开始执行定时文章扫描任务 - {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
            
            # 构建扫描命令参数
            command_args = [
                '--task-name', f'定时扫描_{start_time.strftime("%Y%m%d_%H%M%S")}',
                '--limit', '50',  # 限制每次处理50篇文章
            ]
            
            # 添加目录参数（如果配置了）
            if self.generated_dir:
                command_args.extend(['--generated-dir', self.generated_dir])
            if self.static_dir:
                command_args.extend(['--static-dir', self.static_dir])
            
            # 执行扫描命令
            call_command('scan_articles', *command_args)
            
            end_time = timezone.now()
            duration = (end_time - start_time).total_seconds()
            logger.info(f"定时扫描任务完成，耗时: {duration:.2f}秒")
            
        except Exception as e:
            logger.error(f"执行扫描任务失败: {e}", exc_info=True)
    
    def is_running(self) -> bool:
        """检查调度器是否正在运行
        
        Returns:
            bool: 调度器是否正在运行
        """
        return self._running and self._thread and self._thread.is_alive()
    
    def get_status(self) -> dict:
        """获取调度器状态信息
        
        Returns:
            dict: 包含调度器状态的字典
        """
        return {
            'enabled': self.enabled,
            'running': self.is_running(),
            'interval': self.interval,
            'generated_dir': self.generated_dir,
            'static_dir': self.static_dir,
        }


# 全局调度器实例
_scheduler_instance: Optional[BackgroundArticleScheduler] = None


def get_scheduler() -> BackgroundArticleScheduler:
    """获取全局调度器实例
    
    Returns:
        BackgroundArticleScheduler: 调度器实例
    """
    global _scheduler_instance
    if _scheduler_instance is None:
        _scheduler_instance = BackgroundArticleScheduler()
    return _scheduler_instance


def start_background_scheduler() -> None:
    """启动后台调度器
    
    这个函数应该在Django应用启动时调用。
    """
    scheduler = get_scheduler()
    scheduler.start()


def stop_background_scheduler() -> None:
    """停止后台调度器
    
    这个函数应该在Django应用关闭时调用。
    """
    global _scheduler_instance
    if _scheduler_instance:
        _scheduler_instance.stop()
        _scheduler_instance = None