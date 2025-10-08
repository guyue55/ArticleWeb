"""User models for the application."""

from django.contrib.auth.models import AbstractUser, UserManager
from django.db import models
from django.core.validators import RegexValidator

from apps.common.models import BaseModel, ActiveManager, AllManager


class CustomUserManager(UserManager):
    """Custom user manager that supports soft delete and active filtering."""
    
    def get_queryset(self):
        """Return only active users by default."""
        return super().get_queryset().filter(is_active=True)
    
    def create_user(self, email, password=None, **extra_fields):
        """Create and return a regular user with an email and password."""
        if not email:
            raise ValueError('The Email field must be set')
        email = self.normalize_email(email)
        
        # Generate user_id if not provided
        if 'user_id' not in extra_fields:
            # Simple user_id generation - you might want to use a more sophisticated method
            last_user = self.model.all_objects.order_by('-user_id').first()
            extra_fields['user_id'] = (last_user.user_id + 1) if last_user else 1000001
        
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user
    
    def create_superuser(self, email, password=None, **extra_fields):
        """Create and return a superuser with an email and password."""
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_verified', True)
        
        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')
        
        return self.create_user(email, password, **extra_fields)


class AllUserManager(UserManager):
    """Manager that returns all users including inactive ones."""
    
    def get_queryset(self):
        """Return all users including inactive ones."""
        return super().get_queryset()


class User(AbstractUser, BaseModel):
    """Custom user model extending Django's AbstractUser."""
    
    # Override Django's built-in fields to add db_comment
    password = models.CharField(
        max_length=128,
        verbose_name='password',
        db_comment='用户密码的哈希值，用于身份验证'
    )
    last_login = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name='last login',
        db_comment='用户最后一次登录的时间戳'
    )
    is_superuser = models.BooleanField(
        default=False,
        help_text='Designates that this user has all permissions without explicitly assigning them.',
        verbose_name='superuser status',
        db_comment='超级用户标识，True表示拥有所有权限'
    )
    username = models.CharField(
        max_length=150,
        unique=True,
        help_text='Required. 150 characters or fewer. Letters, digits and @/./+/-/_ only.',
        verbose_name='username',
        db_comment='用户名，用于登录和显示，必须唯一'
    )
    first_name = models.CharField(
        max_length=150,
        blank=True,
        verbose_name='first name',
        db_comment='用户的名字'
    )
    last_name = models.CharField(
        max_length=150,
        blank=True,
        verbose_name='last name',
        db_comment='用户的姓氏'
    )
    is_staff = models.BooleanField(
        default=False,
        help_text='Designates whether the user can log into this admin site.',
        verbose_name='staff status',
        db_comment='员工状态标识，True表示可以访问管理后台'
    )
    is_active = models.BooleanField(
        default=True,
        help_text='Designates whether this user should be treated as active. Unselect this instead of deleting accounts.',
        verbose_name='active',
        db_comment='用户激活状态，True表示账户可用'
    )
    date_joined = models.DateTimeField(
        auto_now_add=True,
        verbose_name='date joined',
        db_comment='用户注册加入的时间戳'
    )
    
    user_id = models.BigIntegerField(
        verbose_name="用户ID",
        unique=True,
        help_text="业务用户ID，用于业务逻辑",
        db_comment="业务层面的用户唯一标识，用于对外展示和业务逻辑"
    )
    
    # Override groups and user_permissions to avoid conflicts
    groups = models.ManyToManyField(
        'auth.Group',
        verbose_name='groups',
        blank=True,
        help_text='The groups this user belongs to.',
        related_name='custom_user_set',
        related_query_name='custom_user',
        db_comment='用户所属的权限组'
    )
    user_permissions = models.ManyToManyField(
        'auth.Permission',
        verbose_name='user permissions',
        blank=True,
        help_text='Specific permissions for this user.',
        related_name='custom_user_set',
        related_query_name='custom_user',
        db_comment='用户的特定权限'
    )
    email = models.CharField(
        verbose_name="邮箱",
        max_length=64,
        unique=True,
        default='',
        help_text="用户邮箱地址，用于登录和通知",
        db_comment="用户邮箱地址，作为登录凭证和接收通知的渠道"
    )
    phone = models.CharField(
        verbose_name="手机号",
        max_length=20,
        default='',
        help_text="用户手机号码",
        db_comment="用户手机号码，用于身份验证和联系"
    )
    avatar = models.CharField(
        verbose_name="头像路径",
        max_length=255,
        default='',
        help_text="用户头像存储路径",
        db_comment="用户头像图片的存储路径或URL"
    )
    bio = models.CharField(
        verbose_name="个人简介",
        max_length=500,
        default='',
        help_text="用户个人简介",
        db_comment="用户的个人简介和自我描述"
    )
    birth_date = models.DateField(
        verbose_name="出生日期",
        null=True,
        help_text="用户出生日期",
        db_comment="用户的出生日期，用于年龄计算和生日提醒"
    )
    location = models.CharField(
        verbose_name="所在地",
        max_length=100,
        default='',
        help_text="用户所在地区",
        db_comment="用户当前所在的地理位置或居住地"
    )
    website = models.CharField(
        verbose_name="个人网站",
        max_length=255,
        default='',
        help_text="用户个人网站链接",
        db_comment="用户的个人网站或博客链接"
    )
    is_verified = models.BooleanField(
        verbose_name="是否已验证",
        default=False,
        help_text="用户是否已通过邮箱验证",
        db_comment="用户邮箱验证状态，True表示已验证"
    )
    last_login_ip = models.CharField(
        verbose_name="最后登录IP",
        max_length=45,
        default='',
        help_text="用户最后一次登录的IP地址",
        db_comment="用户最近一次登录时的IP地址，用于安全监控"
    )
    
    # Custom managers
    objects = CustomUserManager()
    all_objects = AllUserManager()
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']
    
    class Meta:
        verbose_name = "用户"
        verbose_name_plural = "用户"
        db_table = 'users'
        indexes = [
            models.Index(fields=['user_id'], name='uniq_user_id'),
            models.Index(fields=['email'], name='idx_user_email'),
            models.Index(fields=['phone'], name='idx_user_phone'),
            models.Index(fields=['is_active', 'create_time'], name='idx_user_active_created'),
        ]
    
    def __str__(self):
        return f"{self.username} ({self.email})"
    
    @property
    def full_name(self):
        """Return the user's full name."""
        return f"{self.first_name} {self.last_name}".strip() or self.username
    
    def get_avatar_url(self):
        """Return the user's avatar URL or default avatar."""
        if self.avatar:
            return self.avatar.url
        return '/static/images/default_avatar.png'


class UserProfile(BaseModel):
    """Extended user profile information."""
    
    GENDER_CHOICES = [
        (1, '男'),
        (2, '女'),
        (3, '其他'),
    ]
    
    user_uuid = models.CharField(
        verbose_name="用户UUID",
        max_length=255,
        unique=True,
        help_text="关联用户的UUID",
        db_comment="关联的用户UUID，建立与User表的关系"
    )
    gender = models.PositiveSmallIntegerField(
        verbose_name="性别",
        choices=GENDER_CHOICES,
        default=0,
        help_text="用户性别：0-未设置，1-男，2-女，3-其他",
        db_comment="用户性别标识，0-未设置，1-男，2-女，3-其他"
    )
    occupation = models.CharField(
        verbose_name="职业",
        max_length=100,
        default='',
        help_text="用户职业",
        db_comment="用户的职业或工作岗位"
    )
    education = models.CharField(
        verbose_name="教育背景",
        max_length=100,
        default='',
        help_text="用户教育背景",
        db_comment="用户的教育程度和学历背景"
    )
    interests = models.CharField(
        verbose_name="兴趣爱好",
        max_length=500,
        default='',
        help_text="用户兴趣爱好，用逗号分隔",
        db_comment="用户的兴趣爱好列表，多个兴趣用逗号分隔"
    )
    social_links = models.TextField(
        verbose_name="社交链接",
        default='',
        help_text="用户社交媒体链接，JSON格式字符串",
        db_comment="用户的社交媒体链接，以JSON格式存储"
    )
    preferences = models.TextField(
        verbose_name="用户偏好",
        default='',
        help_text="用户偏好设置，JSON格式字符串",
        db_comment="用户的个性化偏好设置，以JSON格式存储"
    )
    
    # Custom managers
    objects = ActiveManager()
    all_objects = AllManager()
    
    class Meta:
        verbose_name = "用户资料"
        verbose_name_plural = "用户资料"
        db_table = 'user_profiles'
        indexes = [
            models.Index(fields=['user_uuid'], name='idx_profile_user'),
            models.Index(fields=['gender'], name='idx_profile_gender'),
            models.Index(fields=['is_active', 'create_time'], name='idx_profile_active_created'),
        ]
    
    def __str__(self):
        return f"用户资料 {self.id} - 用户UUID: {self.user_uuid}"
    
    def get_interests_list(self):
        """Return interests as a list."""
        if self.interests:
            return [interest.strip() for interest in self.interests.split(',') if interest.strip()]
        return []