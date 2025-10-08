#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
分类管理脚本

功能：
1. 创建扫描脚本所需的所有分类
2. 检查现有分类
3. 更新分类信息

使用方法：
python manage_categories.py --create-all  # 创建所有分类
python manage_categories.py --list        # 列出现有分类
python manage_categories.py --check       # 检查分类状态
"""

import os
import sys
import django
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# 设置Django环境
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'article_web.settings')
django.setup()

from apps.articles.models import Category
from scan_config import CATEGORY_MAPPING
import argparse
import logging

# # 配置日志
# logging.basicConfig(
#     level=logging.INFO,
#     format='%(asctime)s - %(levelname)s - %(message)s',
#     handlers=[
#         logging.FileHandler('manage_categories.log', encoding='utf-8'),
#         logging.StreamHandler()
#     ]
# )
logger = logging.getLogger(__name__)


class CategoryManager:
    """分类管理器"""
    
    def __init__(self):
        """初始化分类管理器"""
        self.category_mapping = CATEGORY_MAPPING
    
    def create_category(self, name: str, slug: str, description: str = None) -> bool:
        """
        创建分类
        
        Args:
            name: 分类名称
            slug: 分类别名
            description: 分类描述
            
        Returns:
            是否创建成功
        """
        try:
            # 检查分类是否已存在
            if Category.objects.filter(name=name).exists():
                logger.info(f"分类已存在: {name}")
                return True
            
            if Category.objects.filter(slug=slug).exists():
                logger.warning(f"分类别名已存在: {slug}，将使用备用别名")
                slug = f"{slug}-alt"
            
            # 创建分类
            category = Category.objects.create(
                name=name,
                slug=slug,
                description=description or f"{name}相关文章",
                is_active=True,
                sort_order=0
            )
            
            logger.info(f"分类创建成功: {name} (ID: {category.id})")
            return True
            
        except Exception as e:
            logger.error(f"创建分类失败: {name}, 错误: {e}")
            return False
    
    def create_all_categories(self) -> None:
        """创建所有扫描脚本需要的分类"""
        logger.info("开始创建所有分类...")
        
        success_count = 0
        total_count = len(self.category_mapping)
        
        for english_name, chinese_name in self.category_mapping.items():
            if self.create_category(
                name=chinese_name,
                slug=english_name,
                description=f"{chinese_name}类文章，包含{english_name}相关内容"
            ):
                success_count += 1
        
        logger.info(f"分类创建完成: {success_count}/{total_count} 个分类创建成功")
    
    def list_categories(self) -> None:
        """列出所有分类"""
        logger.info("当前数据库中的分类:")
        logger.info("-" * 60)
        
        categories = Category.objects.all().order_by('sort_order', 'name')
        
        if not categories.exists():
            logger.info("数据库中没有分类数据")
            return
        
        for category in categories:
            status = "激活" if category.is_active else "禁用"
            logger.info(f"ID: {category.id:2d} | 名称: {category.name:8s} | "
                       f"别名: {category.slug:12s} | 状态: {status}")
        
        logger.info("-" * 60)
        logger.info(f"总计: {categories.count()} 个分类")
    
    def check_categories(self) -> None:
        """检查分类状态"""
        logger.info("检查分类状态...")
        logger.info("=" * 60)
        
        # 检查扫描脚本需要的分类
        missing_categories = []
        existing_categories = []
        
        for english_name, chinese_name in self.category_mapping.items():
            try:
                category = Category.objects.get(name=chinese_name)
                existing_categories.append((chinese_name, category.id, category.is_active))
                logger.info(f"✅ {chinese_name} (ID: {category.id}, 激活: {category.is_active})")
            except Category.DoesNotExist:
                missing_categories.append((english_name, chinese_name))
                logger.warning(f"❌ {chinese_name} - 不存在")
        
        logger.info("=" * 60)
        logger.info(f"现有分类: {len(existing_categories)} 个")
        logger.info(f"缺失分类: {len(missing_categories)} 个")
        
        if missing_categories:
            logger.info("\n缺失的分类:")
            for english_name, chinese_name in missing_categories:
                logger.info(f"  - {chinese_name} ({english_name})")
            logger.info("\n建议运行: python manage_categories.py --create-all")
        else:
            logger.info("\n✅ 所有需要的分类都已存在！")
    
    def update_category_mapping(self) -> None:
        """更新分类映射，确保所有分类都有正确的slug"""
        logger.info("更新分类映射...")
        
        for english_name, chinese_name in self.category_mapping.items():
            try:
                category = Category.objects.get(name=chinese_name)
                if category.slug != english_name:
                    old_slug = category.slug
                    category.slug = english_name
                    category.save()
                    logger.info(f"更新分类别名: {chinese_name} ({old_slug} -> {english_name})")
                else:
                    logger.info(f"分类别名正确: {chinese_name} ({english_name})")
            except Category.DoesNotExist:
                logger.warning(f"分类不存在: {chinese_name}")
    
    def delete_unused_categories(self, confirm: bool = False) -> None:
        """删除未使用的分类"""
        if not confirm:
            logger.warning("此操作将删除未在映射中的分类，请使用 --confirm 参数确认")
            return
        
        logger.info("查找未使用的分类...")
        
        mapped_names = set(self.category_mapping.values())
        all_categories = Category.objects.all()
        unused_categories = []
        
        for category in all_categories:
            if category.name not in mapped_names:
                unused_categories.append(category)
        
        if not unused_categories:
            logger.info("没有找到未使用的分类")
            return
        
        logger.info(f"找到 {len(unused_categories)} 个未使用的分类:")
        for category in unused_categories:
            logger.info(f"  - {category.name} (ID: {category.id})")
        
        # 这里可以添加删除逻辑，但为了安全起见，暂时只列出
        logger.warning("为了安全，暂不自动删除。请手动确认后删除。")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='分类管理脚本')
    parser.add_argument('--create-all', action='store_true', help='创建所有分类')
    parser.add_argument('--list', action='store_true', help='列出所有分类')
    parser.add_argument('--check', action='store_true', help='检查分类状态')
    parser.add_argument('--update-mapping', action='store_true', help='更新分类映射')
    parser.add_argument('--delete-unused', action='store_true', help='删除未使用的分类')
    parser.add_argument('--confirm', action='store_true', help='确认删除操作')
    
    args = parser.parse_args()
    
    if not any([args.create_all, args.list, args.check, args.update_mapping, args.delete_unused]):
        parser.print_help()
        return
    
    manager = CategoryManager()
    
    try:
        if args.create_all:
            manager.create_all_categories()
        
        if args.list:
            manager.list_categories()
        
        if args.check:
            manager.check_categories()
        
        if args.update_mapping:
            manager.update_category_mapping()
        
        if args.delete_unused:
            manager.delete_unused_categories(args.confirm)
            
    except Exception as e:
        logger.error(f"执行失败: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()