"""
URL configuration for article_web project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.shortcuts import redirect
from django.views.generic import TemplateView
from django.views.decorators.csrf import csrf_exempt
from ninja import NinjaAPI

# 导入用户视图
from apps.users.views import (
    register_view, login_view, logout_view, 
    profile_view, stats_view, update_profile_view, check_auth_view, get_csrf_token
)
from apps.users.health import HealthCheckView

# 创建API实例，不使用全局认证，让每个端点自己处理
api = NinjaAPI(title="Article Web API", version="1.0.0", csrf=False)

# 导入API路由
from apps.articles.api import router as articles_router
# from apps.users.api import router as users_router  # 暂时注释掉，使用Django视图

# 注册API路由
api.add_router("/articles/", articles_router)
# api.add_router("/users/", users_router)  # 暂时注释掉，使用Django视图


def home_redirect(request):
    """重定向到文章列表页面"""
    return redirect('/articles/')


urlpatterns = [
    path('admin/', admin.site.urls),
    
    # API路由
    path("api/v1/", api.urls),
    
    # 健康检查端点
    path('health/', HealthCheckView.as_view(), name='health_check'),
    
    # 用户认证API（Django视图版本）
    path('api/v1/users/csrf/', get_csrf_token, name='get_csrf_token'),
    path('api/v1/users/register/', register_view, name='api_register'),
    path('api/v1/users/login/', login_view, name='api_login'),
    path('api/v1/users/logout/', logout_view, name='api_logout'),
    path('api/v1/users/profile/', profile_view, name='api_profile'),
    path('api/v1/users/stats/', stats_view, name='api_stats'),
    path('api/v1/users/update/', update_profile_view, name='api_update_profile'),
    path('api/v1/users/check-auth/', check_auth_view, name='api_check_auth'),
    
    # 认证页面路由
    path('auth/login/', TemplateView.as_view(template_name='auth/login.html'), name='login'),
    path('auth/register/', TemplateView.as_view(template_name='auth/register.html'), name='register'),
    
    # 用户页面路由
    path('profile/', TemplateView.as_view(template_name='profile.html'), name='profile'),
    
    # 文章应用路由
    path('articles/', include('apps.articles.urls')),
    
    # 示例页面
    path('categories/', TemplateView.as_view(template_name='categories.html'), name='categories'),
    path('records/', TemplateView.as_view(template_name='records.html'), name='records'),
    
    # 测试页面
    path('test-auth/', TemplateView.as_view(template_name='test_auth.html'), name='test_auth'),
    
    # 根URL重定向到文章列表
    path('', home_redirect, name='home'),
]

# 开发环境下的媒体文件和静态文件服务
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)