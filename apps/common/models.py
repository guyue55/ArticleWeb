"""Common models for the application."""

from django.db import models

from apps.common.utils import generate_uuid



class BaseModel(models.Model):
    """Base model with common fields for all models."""
    
    id = models.BigAutoField(
        primary_key=True,
        verbose_name="主键ID",
        help_text="自增主键ID",
        db_comment="自增主键ID，唯一标识记录"
    )
    uuid = models.CharField(
        max_length=255, 
        unique=True, 
        default=None, 
        editable=False, 
        null=True, 
        blank=True, 
        verbose_name='唯一标识', 
        help_text='版本的唯一标识符，系统自动生成',
        db_comment='全局唯一标识符，用于跨表关联和业务逻辑'
    )
    create_time = models.DateTimeField(
        verbose_name="创建时间",
        auto_now_add=True,
        help_text="记录创建时间",
        db_comment="记录首次创建的时间戳"
    )
    update_time = models.DateTimeField(
        verbose_name="更新时间",
        auto_now=True,
        help_text="记录最后更新时间",
        db_comment="记录最后一次修改的时间戳"
    )
    is_active = models.BooleanField(
        verbose_name="是否激活",
        default=True,
        help_text="标记记录是否处于激活状态",
        db_comment="软删除标记，True表示记录有效，False表示已删除"
    )
    
    class Meta:
        abstract = True
        ordering = ['-create_time']
    
    def save(self, *args, **kwargs):
        """保存时自动生成UUID."""
        if not self.uuid:
            self.uuid = generate_uuid()
        super().save(*args, **kwargs)
    
    def soft_delete(self):
        """Soft delete the record by setting is_active to False."""
        self.is_active = False
        self.save(update_fields=['is_active', 'update_time'])
    
    def restore(self):
        """Restore the soft deleted record."""
        self.is_active = True
        self.save(update_fields=['is_active', 'update_time'])


class ActiveManager(models.Manager):
    """Manager that returns only active records."""
    
    def get_queryset(self):
        return super().get_queryset().filter(is_active=True)


class AllManager(models.Manager):
    """Manager that returns all records including inactive ones."""
    
    def get_queryset(self):
        return super().get_queryset()