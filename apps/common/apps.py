"""Common app configuration."""

from django.apps import AppConfig


class CommonConfig(AppConfig):
    """Common application configuration."""
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.common'
    verbose_name = '通用模块'