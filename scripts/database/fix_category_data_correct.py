#!/usr/bin/env python
"""
重新修复分类数据的脚本
根据文章内容重新正确分配分类
"""
import os
import django

# 设置Django环境
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'article_web.settings')
django.setup()

from apps.articles.models import Article, Category

def main():
    """主函数：重新修复分类数据"""
    print("=== 开始重新修复分类数据 ===")
    
    # 获取所有分类的UUID映射
    categories = Category.objects.all()
    category_map = {cat.name: cat.uuid for cat in categories}
    
    print("分类UUID映射:")
    for name, uuid in category_map.items():
        print(f"  {name}: {uuid}")
    
    # 定义关键词到分类的映射
    keyword_to_category = {
        # 职场相关关键词
        '职场': ['职场', '加班', '升职', '面试', '程序员', '中层', '管理', '裁员', '求职', '工作', '同事', '领导', '项目', '效率'],
        
        # 汽车相关关键词  
        '汽车': ['汽车', '买车', '购车', '驾驶', '保养', '4S店', '爱车', 'SUV', '车型', '预算买车'],
        
        # 旅游相关关键词
        '旅游': ['旅游', '云南', '丽江', '攻略', '美食住宿', '畅游', '独闯'],
        
        # 情书相关关键词
        '情书': ['情书', '爱情', '恋爱', '表白', '心动', '喜欢你', '爱你'],
        
        # 娱乐相关关键词
        '娱乐': ['娱乐', '明星', '电影', '综艺', '八卦', '影视'],
        
        # 美食相关关键词
        '美食': ['美食', '菜谱', '做菜', '烹饪', '食材', '餐厅'],
        
        # 教育相关关键词
        '教育': ['教育', '学习', '考试', '学校', '老师', '学生'],
        
        # 冷知识相关关键词
        '冷知识': ['冷知识', '科普', '历史', '文化', '知识', '揭秘'],
        
        # 日记相关关键词
        '日记': ['日记', '今天', '心情', '生活记录'],
        
        # 生活相关关键词
        '生活': ['生活', '家庭', '日常'],
        
        # 民生相关关键词
        '民生': ['民生', '社会', '政策', '新闻']
    }
    
    # 统计修复情况
    fix_count = 0
    total_articles = Article.objects.count()
    
    print(f"\n开始处理 {total_articles} 篇文章...")
    
    # 遍历所有文章
    for article in Article.objects.all():
        title = article.title.lower()
        content = (article.content or '').lower()
        text = title + ' ' + content
        
        # 找到最匹配的分类
        best_category = None
        max_matches = 0
        
        for category_name, keywords in keyword_to_category.items():
            matches = sum(1 for keyword in keywords if keyword in text)
            if matches > max_matches:
                max_matches = matches
                best_category = category_name
        
        # 如果找到了匹配的分类且当前分类不正确
        if best_category and best_category in category_map:
            correct_uuid = category_map[best_category]
            if article.category_uuid != correct_uuid:
                old_category = None
                try:
                    old_category = Category.objects.get(uuid=article.category_uuid).name
                except:
                    old_category = "未知"
                
                article.category_uuid = correct_uuid
                article.save()
                fix_count += 1
                
                if fix_count <= 10:  # 只显示前10个修复示例
                    print(f"修复文章: {article.title[:40]}...")
                    print(f"  从 '{old_category}' 改为 '{best_category}'")
                    print(f"  匹配关键词数: {max_matches}")
    
    print(f"\n=== 修复完成 ===")
    print(f"总共修复了 {fix_count} 篇文章")
    
    # 验证修复结果
    print("\n=== 修复后的分类统计 ===")
    for category in categories:
        count = Article.objects.filter(category_uuid=category.uuid).count()
        print(f"{category.name}: {count}篇文章")
    
    # 检查未分类文章
    uncategorized = 0
    for article in Article.objects.all():
        try:
            Category.objects.get(uuid=article.category_uuid)
        except Category.DoesNotExist:
            uncategorized += 1
    
    print(f"\n未分类文章: {uncategorized}篇")

if __name__ == "__main__":
    main()