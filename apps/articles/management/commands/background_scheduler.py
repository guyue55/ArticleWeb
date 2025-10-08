"""后台调度器管理命令

这个命令用于手动控制后台文章扫描调度器，包括启动、停止和查看状态。
"""

import logging
from django.core.management.base import BaseCommand, CommandError
from apps.articles.background_scheduler import get_scheduler

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    """后台调度器管理命令
    
    提供启动、停止和查看后台调度器状态的功能。
    """
    
    help = '管理后台文章扫描调度器'
    
    def add_arguments(self, parser):
        """添加命令行参数
        
        Args:
            parser: 参数解析器
        """
        parser.add_argument(
            'action',
            choices=['start', 'stop', 'status', 'restart'],
            help='要执行的操作: start(启动), stop(停止), status(状态), restart(重启)'
        )
    
    def handle(self, *args, **options):
        """处理命令
        
        Args:
            *args: 位置参数
            **options: 关键字参数
        """
        action = options['action']
        scheduler = get_scheduler()
        
        try:
            if action == 'start':
                self._start_scheduler(scheduler)
            elif action == 'stop':
                self._stop_scheduler(scheduler)
            elif action == 'status':
                self._show_status(scheduler)
            elif action == 'restart':
                self._restart_scheduler(scheduler)
        except Exception as e:
            raise CommandError(f'执行操作 {action} 时发生错误: {e}')
    
    def _start_scheduler(self, scheduler):
        """启动调度器
        
        Args:
            scheduler: 调度器实例
        """
        if scheduler.is_running():
            self.stdout.write(
                self.style.WARNING('调度器已在运行中')
            )
            return
        
        if not scheduler.enabled:
            self.stdout.write(
                self.style.ERROR('调度器已禁用，请检查 ARTICLE_SCAN_ENABLED 设置')
            )
            return
        
        scheduler.start()
        self.stdout.write(
            self.style.SUCCESS('后台调度器已启动')
        )
    
    def _stop_scheduler(self, scheduler):
        """停止调度器
        
        Args:
            scheduler: 调度器实例
        """
        if not scheduler.is_running():
            self.stdout.write(
                self.style.WARNING('调度器未在运行')
            )
            return
        
        scheduler.stop()
        self.stdout.write(
            self.style.SUCCESS('后台调度器已停止')
        )
    
    def _restart_scheduler(self, scheduler):
        """重启调度器
        
        Args:
            scheduler: 调度器实例
        """
        if scheduler.is_running():
            self.stdout.write('正在停止调度器...')
            scheduler.stop()
        
        if scheduler.enabled:
            self.stdout.write('正在启动调度器...')
            scheduler.start()
            self.stdout.write(
                self.style.SUCCESS('后台调度器已重启')
            )
        else:
            self.stdout.write(
                self.style.ERROR('调度器已禁用，无法重启')
            )
    
    def _show_status(self, scheduler):
        """显示调度器状态
        
        Args:
            scheduler: 调度器实例
        """
        status = scheduler.get_status()
        
        self.stdout.write('\n=== 后台调度器状态 ===')
        self.stdout.write(f'启用状态: {"是" if status["enabled"] else "否"}')
        
        if status['enabled']:
            running_status = "运行中" if status['running'] else "已停止"
            style = self.style.SUCCESS if status['running'] else self.style.WARNING
            self.stdout.write(f'运行状态: {style(running_status)}')
            self.stdout.write(f'扫描间隔: {status["interval"]}秒')
            
            if status['generated_dir']:
                self.stdout.write(f'生成目录: {status["generated_dir"]}')
            if status['static_dir']:
                self.stdout.write(f'静态目录: {status["static_dir"]}')
        else:
            self.stdout.write(
                self.style.ERROR('调度器已禁用，请检查 ARTICLE_SCAN_ENABLED 设置')
            )
        
        self.stdout.write('')