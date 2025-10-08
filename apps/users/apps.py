"""Users app configuration."""

from django.apps import AppConfig


class UsersConfig(AppConfig):
    """Users application configuration."""
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.users'
    verbose_name = '用户管理'
    
    def ready(self):
        """Import signals when app is ready."""
        try:
            import apps.users.signals  # noqa F401
        except ImportError:
            pass