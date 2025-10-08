#!/usr/bin/env python
"""
检查文章数据脚本
"""
import os
import sys
import django

# 设置Django环境
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'article_web.settings')
django.setup()

from apps.articles.models import Article, Category

def check_articles_data():
    """检查文章数据"""
    print("=== 数据库文章检查 ===")
    
    # 检查文章总数
    total_articles = Article.objects.count()
    print(f"文章总数: {total_articles}")
    
    # 检查已发布文章
    published_articles = Article.objects.filter(status=2).count()
    print(f"已发布文章数: {published_articles}")
    
    # 检查分类
    total_categories = Category.objects.count()
    print(f"分类总数: {total_categories}")
    
    print("\n=== 最近5篇文章 ===")
    articles = Article.objects.all().order_by('-create_time')[:5]
    for article in articles:
        # 获取分类信息
        category_name = "无"
        if article.category_uuid:
            try:
                category = Category.objects.get(uuid=article.category_uuid)
                category_name = category.name
            except Category.DoesNotExist:
                category_name = f"分类不存在({article.category_uuid[:8]}...)"
        
        print(f"ID: {article.id}")
        print(f"标题: {article.title[:50]}...")
        print(f"分类UUID: {article.category_uuid}")
        print(f"分类: {category_name}")
        print(f"状态: {article.status}")
        print(f"创建时间: {article.create_time}")
        print("-" * 50)
    
    print("\n=== 分类信息 ===")
    categories = Category.objects.all()[:5]
    for category in categories:
        # 通过category_uuid统计文章数
        article_count = Article.objects.filter(category_uuid=category.uuid, status=2).count()
        print(f"分类: {category.name} (ID: {category.id}, UUID: {category.uuid}) - 已发布文章数: {article_count}")

if __name__ == "__main__":
    check_articles_data()