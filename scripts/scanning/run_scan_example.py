#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
文章扫描脚本使用示例

这个脚本展示了如何使用 scan_articles.py 来扫描和导入文章。

使用方法:
1. 确保Django服务器在 http://127.0.0.1:9000/ 运行
2. 运行此脚本进行文章导入

作者: AI Assistant
创建时间: 2025-01-17
"""

import os
import sys
import subprocess
from pathlib import Path

def check_django_server():
    """检查Django服务器是否运行"""
    import requests
    try:
        response = requests.get("http://127.0.0.1:9000/api/articles/categories/", timeout=5)
        return response.status_code in [200, 401, 403]  # 200正常，401/403表示服务器运行但需要认证
    except:
        return False

def run_scan_command(command_args):
    """运行扫描命令"""
    try:
        cmd = [sys.executable, "scan_articles.py"] + command_args
        print(f"执行命令: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8')
        
        print("标准输出:")
        print(result.stdout)
        
        if result.stderr:
            print("错误输出:")
            print(result.stderr)
        
        return result.returncode == 0
    except Exception as e:
        print(f"执行命令失败: {e}")
        return False

def main():
    """主函数"""
    print("=" * 60)
    print("文章扫描脚本使用示例")
    print("=" * 60)
    
    # 检查当前目录
    if not Path("scan_articles.py").exists():
        print("错误: 找不到 scan_articles.py 文件")
        print("请确保在正确的目录下运行此脚本")
        return
    
    # 检查Django服务器
    print("1. 检查Django服务器状态...")
    if check_django_server():
        print("✓ Django服务器运行正常")
    else:
        print("✗ Django服务器未运行或无法访问")
        print("请先启动Django服务器: python manage.py runserver 127.0.0.1:9000")
        return
    
    # 显示使用选项
    print("\n2. 选择操作:")
    print("1) 试运行 - 扫描文章但不实际导入")
    print("2) 导入所有文章")
    print("3) 只导入指定分类的文章")
    print("4) 查看帮助信息")
    print("0) 退出")
    
    while True:
        choice = input("\n请选择操作 (0-4): ").strip()
        
        if choice == "0":
            print("退出程序")
            break
        elif choice == "1":
            print("\n执行试运行...")
            success = run_scan_command(["--dry-run"])
            if success:
                print("✓ 试运行完成")
            else:
                print("✗ 试运行失败")
        elif choice == "2":
            print("\n开始导入所有文章...")
            confirm = input("确认要导入所有文章吗? (y/N): ").strip().lower()
            if confirm == 'y':
                success = run_scan_command([])
                if success:
                    print("✓ 文章导入完成")
                else:
                    print("✗ 文章导入失败")
            else:
                print("取消导入")
        elif choice == "3":
            print("\n可用分类:")
            categories = ['汽车', '日记', '教育', '娱乐', '美食', '生活', '民生', '情书', '旅游', '冷知识', '职场']
            for i, cat in enumerate(categories, 1):
                print(f"  {i}) {cat}")
            
            cat_choice = input("请输入分类名称: ").strip()
            if cat_choice in categories:
                print(f"\n开始导入 {cat_choice} 分类的文章...")
                success = run_scan_command(["--category", cat_choice])
                if success:
                    print(f"✓ {cat_choice} 分类文章导入完成")
                else:
                    print(f"✗ {cat_choice} 分类文章导入失败")
            else:
                print("无效的分类名称")
        elif choice == "4":
            print("\n显示帮助信息...")
            run_scan_command(["--help"])
        else:
            print("无效选择，请重新输入")

if __name__ == '__main__':
    main()