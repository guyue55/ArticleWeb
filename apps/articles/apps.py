"""Articles app configuration."""

import logging
import os
from django.apps import AppConfig
from django.conf import settings

logger = logging.getLogger(__name__)


class ArticlesConfig(AppConfig):
    """Articles application configuration."""
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.articles'
    verbose_name = '文章管理'
    
    def ready(self):
        """Import signals when app is ready."""
        try:
            import apps.articles.signals  # noqa F401
        except ImportError:
            pass
        
        # 只在主进程中启动调度器（避免在runserver的重载进程中重复启动）
        if os.environ.get('RUN_MAIN') == 'true' or 'runserver' not in os.sys.argv:
            self._start_background_services()
    
    def _start_background_services(self):
        """启动后台服务
        
        启动文章扫描调度器等后台服务。
        """
        try:
            # 检查是否启用了文章扫描
            scan_enabled = getattr(settings, 'ARTICLE_SCAN_ENABLED', True)
            
            if scan_enabled:
                from .background_scheduler import start_background_scheduler
                start_background_scheduler()
                logger.info("Articles应用后台服务已启动")
            else:
                logger.info("文章扫描功能已禁用，跳过后台服务启动")
                
        except Exception as e:
            logger.error(f"启动Articles应用后台服务时发生错误: {e}", exc_info=True)