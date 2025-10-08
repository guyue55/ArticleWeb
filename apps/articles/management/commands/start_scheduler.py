# -*- coding: utf-8 -*-
"""
Django管理命令：启动文章扫描调度器

用法：
    python manage.py start_scheduler [选项]

选项：
    --daemon: 以守护进程模式运行
    --pid-file: 指定PID文件路径
    --log-file: 指定日志文件路径

示例：
    # 启动调度器
    python manage.py start_scheduler
    
    # 以守护进程模式启动
    python manage.py start_scheduler --daemon
    
    # 指定PID文件和日志文件
    python manage.py start_scheduler --daemon --pid-file=/var/run/scheduler.pid --log-file=/var/log/scheduler.log
"""

import os
import sys
import signal
import time
import logging
from pathlib import Path
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from apps.articles.scheduler import get_scheduler, start_scheduler

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    """
    启动文章扫描调度器的Django管理命令
    
    该命令负责启动和管理文章扫描的定时任务调度器，支持守护进程模式运行。
    """
    
    help = '启动文章扫描调度器'
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.scheduler = None
        self.pid_file = None
        self.daemon_mode = False
    
    def add_arguments(self, parser):
        """
        添加命令行参数
        
        Args:
            parser: 参数解析器
        """
        parser.add_argument(
            '--daemon',
            action='store_true',
            help='以守护进程模式运行调度器'
        )
        
        parser.add_argument(
            '--pid-file',
            type=str,
            default=None,
            help='指定PID文件路径（守护进程模式下使用）'
        )
        
        parser.add_argument(
            '--log-file',
            type=str,
            default=None,
            help='指定日志文件路径'
        )
        
        parser.add_argument(
            '--check-interval',
            type=int,
            default=60,
            help='调度器检查间隔时间（秒），默认60秒'
        )
    
    def handle(self, *args, **options):
        """
        命令处理入口
        
        Args:
            *args: 位置参数
            **options: 命令选项
        """
        # 检查是否启用了文章扫描功能
        if not getattr(settings, 'ARTICLE_SCAN_ENABLED', True):
            raise CommandError('文章扫描功能已禁用，无法启动调度器')
        
        self.daemon_mode = options['daemon']
        self.pid_file = options['pid_file']
        log_file = options['log_file']
        check_interval = options['check_interval']
        
        # 配置日志
        self._setup_logging(log_file)
        
        # 设置信号处理
        self._setup_signal_handlers()
        
        try:
            if self.daemon_mode:
                self._run_as_daemon(check_interval)
            else:
                self._run_foreground(check_interval)
        
        except KeyboardInterrupt:
            self.stdout.write(self.style.WARNING('\n收到中断信号，正在停止调度器...'))
            self._stop_scheduler()
        
        except Exception as e:
            logger.error(f"调度器运行失败: {e}")
            raise CommandError(f'调度器运行失败: {e}')
    
    def _setup_logging(self, log_file=None):
        """
        配置日志记录
        
        Args:
            log_file: 日志文件路径
        """
        if log_file:
            # 确保日志目录存在
            log_path = Path(log_file)
            log_path.parent.mkdir(parents=True, exist_ok=True)
            
            # 配置文件日志处理器
            file_handler = logging.FileHandler(log_file, encoding='utf-8')
            file_handler.setLevel(logging.INFO)
            file_handler.setFormatter(
                logging.Formatter(
                    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
                )
            )
            
            # 添加到根日志记录器
            root_logger = logging.getLogger()
            root_logger.addHandler(file_handler)
            
            logger.info(f"日志将写入文件: {log_file}")
    
    def _setup_signal_handlers(self):
        """
        设置信号处理器
        
        注册SIGTERM和SIGINT信号的处理函数，用于优雅地停止调度器。
        """
        def signal_handler(signum, frame):
            logger.info(f"收到信号 {signum}，正在停止调度器...")
            self._stop_scheduler()
            sys.exit(0)
        
        # 注册信号处理器
        signal.signal(signal.SIGTERM, signal_handler)
        signal.signal(signal.SIGINT, signal_handler)
        
        # Windows系统不支持SIGHUP
        if hasattr(signal, 'SIGHUP'):
            signal.signal(signal.SIGHUP, signal_handler)
    
    def _run_as_daemon(self, check_interval):
        """
        以守护进程模式运行调度器
        
        Args:
            check_interval: 检查间隔时间
        """
        # 创建PID文件
        if self.pid_file:
            self._create_pid_file()
        
        try:
            self.stdout.write(self.style.SUCCESS('调度器正在以守护进程模式启动...'))
            
            # 启动调度器
            self._start_scheduler(check_interval)
            
            # 保持进程运行
            while True:
                time.sleep(60)
                
                # 检查调度器状态
                if self.scheduler and not self.scheduler._running:
                    logger.warning("调度器已停止，正在重新启动...")
                    self._start_scheduler(check_interval)
        
        finally:
            # 清理PID文件
            if self.pid_file:
                self._remove_pid_file()
    
    def _run_foreground(self, check_interval):
        """
        在前台运行调度器
        
        Args:
            check_interval: 检查间隔时间
        """
        self.stdout.write(self.style.SUCCESS('调度器正在前台启动...'))
        
        # 启动调度器
        self._start_scheduler(check_interval)
        
        # 显示状态信息
        self._show_status()
        
        # 保持进程运行
        try:
            while True:
                time.sleep(30)
                
                # 定期显示状态
                if int(time.time()) % 300 == 0:  # 每5分钟显示一次
                    self._show_status()
        
        except KeyboardInterrupt:
            pass
    
    def _start_scheduler(self, check_interval):
        """
        启动调度器
        
        Args:
            check_interval: 检查间隔时间
        """
        self.scheduler = get_scheduler()
        
        # 设置检查间隔
        if hasattr(self.scheduler, '_check_interval'):
            self.scheduler._check_interval = check_interval
        
        # 启动调度器
        self.scheduler.start()
        
        logger.info("文章扫描调度器已启动")
        self.stdout.write(self.style.SUCCESS('调度器启动成功'))
    
    def _stop_scheduler(self):
        """
        停止调度器
        """
        if self.scheduler:
            self.scheduler.stop()
            logger.info("文章扫描调度器已停止")
            self.stdout.write(self.style.SUCCESS('调度器已停止'))
    
    def _show_status(self):
        """
        显示调度器状态信息
        """
        if self.scheduler:
            status = self.scheduler.get_status()
            
            self.stdout.write(f"\n调度器状态:")
            self.stdout.write(f"  运行状态: {'运行中' if status['running'] else '已停止'}")
            self.stdout.write(f"  活跃任务数: {status['schedules_count']}")
            self.stdout.write(f"  检查间隔: {status['check_interval']}秒")
            
            if status['active_schedules']:
                self.stdout.write(f"\n活跃的调度任务:")
                for schedule in status['active_schedules']:
                    next_run = schedule['next_run'] or '无'
                    last_run = schedule['last_run'] or '从未执行'
                    self.stdout.write(
                        f"  - {schedule['name']} ({schedule['schedule_type']})\n"
                        f"    下次执行: {next_run}\n"
                        f"    上次执行: {last_run}"
                    )
    
    def _create_pid_file(self):
        """
        创建PID文件
        """
        try:
            pid_path = Path(self.pid_file)
            pid_path.parent.mkdir(parents=True, exist_ok=True)
            
            # 检查是否已有进程在运行
            if pid_path.exists():
                with open(pid_path, 'r') as f:
                    old_pid = int(f.read().strip())
                
                # 检查进程是否还在运行
                try:
                    os.kill(old_pid, 0)
                    raise CommandError(f'调度器已在运行 (PID: {old_pid})')
                except OSError:
                    # 进程不存在，删除旧的PID文件
                    pid_path.unlink()
            
            # 写入当前进程PID
            with open(pid_path, 'w') as f:
                f.write(str(os.getpid()))
            
            logger.info(f"PID文件已创建: {self.pid_file}")
        
        except Exception as e:
            raise CommandError(f'创建PID文件失败: {e}')
    
    def _remove_pid_file(self):
        """
        删除PID文件
        """
        try:
            if self.pid_file and Path(self.pid_file).exists():
                Path(self.pid_file).unlink()
                logger.info(f"PID文件已删除: {self.pid_file}")
        
        except Exception as e:
            logger.error(f"删除PID文件失败: {e}")