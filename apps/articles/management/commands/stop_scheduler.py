# -*- coding: utf-8 -*-
"""
Django管理命令：停止文章扫描调度器

用法：
    python manage.py stop_scheduler [选项]

选项：
    --pid-file: 指定PID文件路径
    --force: 强制停止（使用SIGKILL）

示例：
    # 停止调度器
    python manage.py stop_scheduler
    
    # 使用指定的PID文件停止
    python manage.py stop_scheduler --pid-file=/var/run/scheduler.pid
    
    # 强制停止
    python manage.py stop_scheduler --force
"""

import os
import signal
import time
from pathlib import Path
from django.core.management.base import BaseCommand, CommandError
from apps.articles.scheduler import get_scheduler, stop_scheduler


class Command(BaseCommand):
    """
    停止文章扫描调度器的Django管理命令
    
    该命令负责优雅地停止正在运行的文章扫描调度器。
    """
    
    help = '停止文章扫描调度器'
    
    def add_arguments(self, parser):
        """
        添加命令行参数
        
        Args:
            parser: 参数解析器
        """
        parser.add_argument(
            '--pid-file',
            type=str,
            default=None,
            help='指定PID文件路径'
        )
        
        parser.add_argument(
            '--force',
            action='store_true',
            help='强制停止调度器（使用SIGKILL）'
        )
        
        parser.add_argument(
            '--timeout',
            type=int,
            default=30,
            help='等待进程停止的超时时间（秒），默认30秒'
        )
    
    def handle(self, *args, **options):
        """
        命令处理入口
        
        Args:
            *args: 位置参数
            **options: 命令选项
        """
        pid_file = options['pid_file']
        force = options['force']
        timeout = options['timeout']
        
        try:
            if pid_file:
                # 通过PID文件停止
                self._stop_by_pid_file(pid_file, force, timeout)
            else:
                # 停止当前进程中的调度器
                self._stop_current_scheduler()
            
            self.stdout.write(self.style.SUCCESS('调度器已成功停止'))
        
        except Exception as e:
            raise CommandError(f'停止调度器失败: {e}')
    
    def _stop_current_scheduler(self):
        """
        停止当前进程中的调度器
        """
        try:
            scheduler = get_scheduler()
            
            if scheduler._running:
                self.stdout.write('正在停止调度器...')
                scheduler.stop()
                self.stdout.write(self.style.SUCCESS('调度器已停止'))
            else:
                self.stdout.write(self.style.WARNING('调度器未在运行'))
        
        except Exception as e:
            raise CommandError(f'停止当前调度器失败: {e}')
    
    def _stop_by_pid_file(self, pid_file, force=False, timeout=30):
        """
        通过PID文件停止调度器进程
        
        Args:
            pid_file: PID文件路径
            force: 是否强制停止
            timeout: 超时时间
        """
        pid_path = Path(pid_file)
        
        if not pid_path.exists():
            raise CommandError(f'PID文件不存在: {pid_file}')
        
        try:
            # 读取PID
            with open(pid_path, 'r') as f:
                pid = int(f.read().strip())
            
            # 检查进程是否存在
            try:
                os.kill(pid, 0)
            except OSError:
                self.stdout.write(self.style.WARNING(f'进程 {pid} 不存在，删除PID文件'))
                pid_path.unlink()
                return
            
            self.stdout.write(f'正在停止调度器进程 (PID: {pid})...')
            
            if force:
                # 强制停止
                self._kill_process(pid, signal.SIGKILL)
                self.stdout.write(self.style.WARNING('已强制停止进程'))
            else:
                # 优雅停止
                self._graceful_stop(pid, timeout)
            
            # 删除PID文件
            if pid_path.exists():
                pid_path.unlink()
                self.stdout.write(f'已删除PID文件: {pid_file}')
        
        except ValueError:
            raise CommandError(f'PID文件格式无效: {pid_file}')
        except Exception as e:
            raise CommandError(f'停止进程失败: {e}')
    
    def _graceful_stop(self, pid, timeout):
        """
        优雅地停止进程
        
        Args:
            pid: 进程ID
            timeout: 超时时间
        """
        try:
            # 发送SIGTERM信号
            os.kill(pid, signal.SIGTERM)
            
            # 等待进程停止
            start_time = time.time()
            while time.time() - start_time < timeout:
                try:
                    os.kill(pid, 0)
                    time.sleep(1)
                except OSError:
                    # 进程已停止
                    self.stdout.write(self.style.SUCCESS('进程已优雅停止'))
                    return
            
            # 超时，强制停止
            self.stdout.write(self.style.WARNING(f'等待超时 ({timeout}秒)，强制停止进程'))
            self._kill_process(pid, signal.SIGKILL)
        
        except OSError as e:
            if e.errno == 3:  # No such process
                self.stdout.write(self.style.WARNING('进程已不存在'))
            else:
                raise
    
    def _kill_process(self, pid, sig):
        """
        发送信号给进程
        
        Args:
            pid: 进程ID
            sig: 信号
        """
        try:
            os.kill(pid, sig)
            
            # 等待进程停止
            for _ in range(10):
                try:
                    os.kill(pid, 0)
                    time.sleep(0.5)
                except OSError:
                    return
            
            raise CommandError(f'无法停止进程 {pid}')
        
        except OSError as e:
            if e.errno == 3:  # No such process
                return
            else:
                raise CommandError(f'发送信号失败: {e}')