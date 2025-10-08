#!/usr/bin/env python
"""
分类同步脚本

根据配置文件中的ArticleType枚举同步数据库中的分类数据
"""

import os
import sys
import django

# 设置Django环境
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'article_web.settings')
django.setup()

from apps.articles.models import Category
from config.article_config import ArticleType


def sync_categories():
    """同步分类数据到数据库"""
    print("开始同步分类数据...")
    
    # 获取配置文件中的所有文章类型
    config_categories = {}
    for article_type in ArticleType:
        config_categories[article_type.english_name] = {
            'name': article_type.chinese_name,
            'description': f'{article_type.chinese_name}相关文章内容',
            'slug': article_type.english_name
        }
    
    print(f"配置文件中共有 {len(config_categories)} 个分类")
    
    # 获取数据库中现有的分类
    existing_categories = {cat.slug: cat for cat in Category.objects.all()}
    print(f"数据库中现有 {len(existing_categories)} 个分类")
    
    created_count = 0
    updated_count = 0
    
    # 同步配置文件中的分类到数据库
    for i, (slug, cat_data) in enumerate(config_categories.items(), 1):
        if slug in existing_categories:
            # 更新现有分类
            category = existing_categories[slug]
            category.name = cat_data['name']
            category.description = cat_data['description']
            category.sort_order = i
            category.is_active = True
            category.save()
            print(f"更新分类: {category.name} ({category.slug})")
            updated_count += 1
        else:
            # 创建新分类
            category = Category.objects.create(
                name=cat_data['name'],
                slug=cat_data['slug'],
                description=cat_data['description'],
                sort_order=i,
                is_active=True
            )
            print(f"创建分类: {category.name} ({category.slug})")
            created_count += 1
    
    # 禁用配置文件中不存在的分类
    disabled_count = 0
    for slug, category in existing_categories.items():
        if slug not in config_categories:
            category.is_active = False
            category.save()
            print(f"禁用分类: {category.name} ({category.slug})")
            disabled_count += 1
    
    print(f"\n同步完成:")
    print(f"- 创建: {created_count} 个")
    print(f"- 更新: {updated_count} 个")
    print(f"- 禁用: {disabled_count} 个")
    print(f"- 总计: {Category.objects.filter(is_active=True).count()} 个活跃分类")


if __name__ == '__main__':
    sync_categories()