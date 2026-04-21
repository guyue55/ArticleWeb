from django.urls import path
from django.views.generic import TemplateView
from . import views

app_name = 'articles'

urlpatterns = [
    # Page routes
    path('', views.article_list, name='article_list'),
    path('ai-create/', views.ai_create, name='ai_create'),
    
    # AI 管理后台
    path('admin/ai/', views.ai_admin_dashboard, name='ai_admin_dashboard'),
    path('admin/ai/configs/', views.ai_admin_configs, name='ai_admin_configs'),
    path('admin/ai/providers/', views.ai_admin_providers, name='ai_admin_providers'),
    path('admin/ai/templates/', views.ai_admin_templates, name='ai_admin_templates'),
    
    path('<int:article_id>/', views.article_detail, name='article_detail'),
    path('categories/', TemplateView.as_view(template_name='categories.html'), name='categories'),
    path('records/', TemplateView.as_view(template_name='records.html'), name='records'),
    path('profile/', TemplateView.as_view(template_name='profile.html'), name='profile'),
    path('format-tool/', TemplateView.as_view(template_name='format_tool.html'), name='format-tool'),
    path('feedback/', TemplateView.as_view(template_name='feedback.html'), name='feedback'),
    path('help/', TemplateView.as_view(template_name='help.html'), name='help')
]