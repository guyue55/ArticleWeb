# Scripts 目录说明

本目录包含了项目的各种脚本文件，按功能分类组织：

## 目录结构

### article_generation/
文章生成相关脚本
- `generate_articles.py` - 主要的文章生成脚本
- `example_article_generation.py` - 文章生成示例脚本

### scanning/
扫描相关脚本
- `scan_articles.py` - 文章扫描脚本
- `scan_articles_direct.py` - 直接扫描脚本
- `scan_config.py` - 扫描配置文件
- `run_scan_example.py` - 扫描示例脚本
- `scan_articles.bat` - 扫描批处理文件
- `scan_articles_direct.bat` - 直接扫描批处理文件
- `README.md` - 扫描功能说明文档

### database/
数据库相关脚本
- `check_articles_data.py` - 检查文章数据
- `check_category_issue.py` - 检查分类问题
- `fix_category_data.py` - 修复分类数据
- `fix_category_data_correct.py` - 修复分类数据（正确版本）
- `manage_categories.py` - 分类管理脚本
- `sync_categories.py` - 分类同步脚本
- `update_db.cmd` - 数据库更新批处理文件

### deployment/
部署相关脚本
- `gunicorn.conf.py` - Gunicorn配置文件
- `gunicorn-windows.conf.py` - Windows专用Gunicorn配置文件
- `run-gunicorn-windows.cmd` - Windows Gunicorn启动脚本
- `run-ipv6.cmd` - IPv6启动脚本
- `run.cmd` - 运行脚本
- `start.cmd` - 启动脚本

### development/
开发相关脚本
- `debug_related_articles.py` - 调试相关文章脚本
- `final_fix_report.py` - 最终修复报告脚本
- `manage_scheduler.py` - 调度器管理脚本
- `scheduler_example.py` - 调度器示例脚本
- `manage_dependencies.py` - 依赖管理工具脚本
- `manage_dependencies.cmd` - 依赖管理批处理脚本

## 使用说明

1. 所有脚本都应该从项目根目录运行
2. 确保已激活虚拟环境并安装了所需依赖
3. 部分脚本可能需要配置环境变量或修改配置文件
4. 详细使用方法请参考各子目录中的README文件或脚本内的注释