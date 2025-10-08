#!/usr/bin/env python
"""
检查分类数据问题的脚本
"""
import os
import django

# 设置Django环境
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'article_web.settings')
django.setup()

from apps.articles.models import Article, Category

def main():
    """主函数：检查分类数据问题"""
    print("=== 分类UUID对照表 ===")
    categories = Category.objects.all().order_by('name')
    for category in categories:
        count = Article.objects.filter(category_uuid=category.uuid).count()
        print(f"{category.name}: {category.uuid} ({count}篇文章)")
    
    print("\n=== 检查职场类文章的分类情况 ===")
    # 查找标题包含职场关键词的文章
    workplace_keywords = ['职场', '加班', '升职', '面试', '程序员', '中层', '管理', '裁员', '求职']
    
    for keyword in workplace_keywords:
        articles = Article.objects.filter(title__icontains=keyword)[:3]
        if articles:
            print(f"\n包含关键词 '{keyword}' 的文章:")
            for article in articles:
                print(f"  标题: {article.title[:50]}...")
                print(f"  当前分类UUID: {article.category_uuid}")
                try:
                    category = Category.objects.get(uuid=article.category_uuid)
                    print(f"  当前分类名称: {category.name}")
                except Category.DoesNotExist:
                    print(f"  当前分类名称: 未找到")
                print()
    
    print("\n=== 检查汽车类文章的分类情况 ===")
    # 查找标题包含汽车关键词的文章
    automotive_keywords = ['汽车', '车', '买车', '预算', '驾驶', '保养']
    
    for keyword in automotive_keywords:
        articles = Article.objects.filter(title__icontains=keyword)[:3]
        if articles:
            print(f"\n包含关键词 '{keyword}' 的文章:")
            for article in articles:
                print(f"  标题: {article.title[:50]}...")
                print(f"  当前分类UUID: {article.category_uuid}")
                try:
                    category = Category.objects.get(uuid=article.category_uuid)
                    print(f"  当前分类名称: {category.name}")
                except Category.DoesNotExist:
                    print(f"  当前分类名称: 未找到")
                print()

if __name__ == "__main__":
    main()