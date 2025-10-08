#!/usr/bin/env python3
"""
修复文章分类数据不一致问题
将文章的category_uuid从数字ID转换为正确的UUID格式
"""

import os
import django

# 设置Django环境
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'article_web.settings')
django.setup()

from apps.articles.models import Article, Category


def fix_category_data():
    """修复分类数据不一致问题"""
    print("=== 开始修复分类数据 ===")
    
    # 获取所有分类，建立名称到UUID的映射
    categories = Category.objects.all()
    name_to_uuid_map = {}
    
    print("分类映射关系：")
    for i, category in enumerate(categories, 1):
        # 假设原来的category_uuid存储的是分类的序号或ID
        name_to_uuid_map[str(i)] = category.uuid
        name_to_uuid_map[category.name] = category.uuid
        print(f"分类序号 {i} / 名称 {category.name} -> UUID {category.uuid}")
    
    # 获取所有需要修复的文章
    articles_to_fix = Article.objects.all()
    fixed_count = 0
    
    print(f"\n开始修复 {articles_to_fix.count()} 篇文章...")
    
    for article in articles_to_fix:
        old_category_uuid = article.category_uuid
        
        # 如果category_uuid是数字，尝试转换为UUID
        if old_category_uuid in name_to_uuid_map:
            new_category_uuid = name_to_uuid_map[old_category_uuid]
            article.category_uuid = new_category_uuid
            article.save(update_fields=['category_uuid'])
            fixed_count += 1
            
            if fixed_count <= 5:  # 只显示前5个示例
                print(f"修复文章: {article.title[:30]} - {old_category_uuid} -> {new_category_uuid}")
    
    print(f"\n修复完成！共修复了 {fixed_count} 篇文章")
    
    # 验证修复结果
    print("\n=== 验证修复结果 ===")
    for category in categories:
        article_count = Article.objects.filter(category_uuid=category.uuid).count()
        print(f"{category.name}: {article_count}篇文章")


if __name__ == "__main__":
    fix_category_data()