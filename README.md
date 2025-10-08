# ArticleWeb

面向"文章领取与发布"的内容平台。支持多分类与多用户协作：从本地自动生成的文章库中识别并入库，用户在站内领取、编辑并发布到外部平台（如博客、微信公众号等）。系统提供稳定的扫描入库机制、唯一标识与文件管理、文章格式化功能，以及便捷的后台调度能力。

## 项目背景与定位

### 解决的问题
本项目旨在解决内容创作者面临的高频次、多平台发布需求，通过自动化生成与管理文章，提高内容生产效率。

### 工作原理
1. **内容生成阶段**：通过本地脚本调用大模型API（如文心一言、ChatGPT等），批量生成多种分类的原始文章，存储在 `generated_articles/<分类>` 目录下
2. **扫描入库阶段**：系统定期扫描文章目录，解析Markdown文件，生成HTML与元数据，分配唯一标识符，并将文件复制到静态目录
3. **领取编辑阶段**：内容编辑人员在平台上按分类浏览、领取文章，进行人工优化、校对和完善
4. **发布导出阶段**：编辑完成后，可通过平台导出或直接发布到各目标平台（如博客、公众号、自媒体账号等）

### 技术特点
- 采用唯一文件命名机制，基于短UUID与内容哈希，确保文件管理的一致性
- 支持多种文件格式（Markdown、HTML、元数据）的协同处理
- 实现文章状态全流程追踪，从待领取到已发布
- 提供文章格式化功能，便于对接不同平台

## 系统架构

### 数据流程
```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│  大模型生成脚本  │───>│  文件系统存储   │───>│  扫描入库系统   │───>│  Web应用平台    │
└─────────────────┘    └─────────────────┘    └─────────────────┘    └─────────────────┘
       │                                              │                       │
       │                                              │                       │
       ▼                                              ▼                       ▼
┌─────────────────┐                        ┌─────────────────┐      ┌─────────────────┐
│ 分类目录结构    │                        │ 数据库存储      │      │ 用户领取   │
│ 中文_英文/      │                        │ - 文章表        │      │ - 领取记录      │
│ *.md文件        │                        │ - 分类表        │      │ - 查看功能      │
└─────────────────┘                        │ - 用户表        │      │ - 下载功能      │
                                           └─────────────────┘      └─────────────────┘
```

### 文件处理流程
1. **源文件处理**：
   - 扫描 `generated_articles/<分类>/*.md` 文件
   - 解析内容，生成唯一标识符（短UUID + 内容哈希）
   - 创建 `.html` 和 `.meta` 文件
   
2. **文件复制与重命名**：
   - 将文件复制到 `static/articles/<英文分类>/`
   - 统一重命名为 `<article_id>.md`、`<article_id>.html`、`<article_id>.meta`
   
3. **源文件归档**：
   - 根据配置将原始文件移动到 `Back` 目录或删除

## 核心功能
- 分类与内容管理：支持"中文分类_英文分类"目录结构，自动解析分类并入库。
- 多用户领取管理：按工作流管理文章（待领取 → 已领取），用户可在领取记录中查看和下载。
- 扫描与入库：将本地生成的 `.md` 解析成 HTML 与 `.meta`，并入库与复制到静态目录。
- 唯一标识与文件命名：基于短 `UUID` 的 `article_id`，复制到静态目录时统一以 `article_id` 命名，避免文件冲突。
- 去重与稳定性：基于标题+正文生成 `MD5` 哈希，降低重复入库概率。
- 后台调度：可启用后台扫描调度器，定时发现并处理新文章。
- 内容导出：支持下载，方便用户在其他平台使用。

## 使用流程

### 1. 本地生成文章
- 使用 `scripts/article_generation/` 下的脚本调用大模型生成内容
```bash
# 示例：使用文心一言生成文章
python scripts/article_generation/generate_articles.py --category "测试_test" --count 5
```
- 文章将输出到 `generated_articles/<中文_英文>/` 目录，如 `generated_articles/测试_test/article_20250825.md`

### 2. 系统扫描入库
- 执行扫描命令，将文章解析、入库并复制到静态目录
```bash
# 扫描并处理所有新文章
python manage.py scan_articles

# 仅测试扫描，不实际处理文件
python manage.py scan_articles --dry-run
```
- 系统会自动为每篇文章生成唯一标识符，创建 HTML 与元数据文件

### 3. 领取与下载
- 用户登录平台，浏览待领取文章列表
- 领取文章后，状态变更为"已领取"，其他用户不可再领取
- 在领取记录中查看已领取的文章
- 支持多种格式下载：Markdown、HTML、富文本
- 用户可将下载的内容用于其他平台发布

## 快速开始
- 环境要求
  - Python ≥ 3.9
  - pip / venv
- 安装依赖
```
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements/base.txt
```
- 初始化与运行
```
python manage.py migrate
python manage.py runserver
```
- 创建管理员（可选）
```
python manage.py createsuperuser
```

## 文章扫描
- 目录结构示例
```
generated_articles/
  测试_test/
    example.md
```
- 扫描命令
```
# 试运行（不改动文件，仅打印计划）
python manage.py scan_articles --dry-run

# 实际运行（生成 html、meta，入库并复制到静态目录）
python manage.py scan_articles
```
- 命名与复制规则
  - 源目录生成阶段采用唯一前缀 `<article_id>_<timestamp>` 产出 `.html` 与 `.meta`。
  - 复制到静态目录时统一重命名为：`<article_id>.md`、`<article_id>.html`、`<article_id>.meta`。
  - 处理完成后，源 `.md` 根据配置移动到 `generated_articles/Back/...` 或删除。

## 配置
- 参考 `.env.example`，常见配置：
  - `ARTICLE_SCAN_ENABLED`：是否启用后台扫描（`true/false`）
  - `ARTICLE_SCAN_INTERVAL`：后台扫描间隔秒数（如 `180`）
  - `SCANNED_FILE_ACTION`：处理已扫描文件策略（`back`/`delete`/`none`）
  - `GENERATED_ARTICLES_DIR`：源文章目录（默认 `generated_articles`）
  - `STATIC_FILES_DIR`：静态复制目标目录（项目内已配置）

## 项目结构
```
apps/
  articles/
    management/commands/scan_articles.py  # 扫描入库、生成、复制与清理
    models.py                             # 文章数据与状态
    api.py                                # 领取发布相关 API（可扩展）
  common/                                 # 通用工具与响应封装
  users/                                  # 用户与认证
static/                                   # 复制后的静态文件（md/html/meta 按分类存放）
scripts/article_generation/               # 本地生成文章脚本
scripts/scanning/                         # 脚本版扫描实现与示例
```

## 常用命令
```
python manage.py runserver      # 启动开发服务器
python manage.py collectstatic  # 生产环境收集静态文件
pytest -q                       # 运行测试
```

## 疑难排查
- 只复制了 `.md`，未复制 `.html/.meta`
  - 复制逻辑已修复：由 `.meta` 文件名提取唯一前缀，确保同名 `.html/.md` 一并复制到静态目录。
- 扫描找不到文章
  - 确认源目录命名为 `中文分类_英文分类` 且文件为 `.md`；`Back` 目录会被忽略。
- 重复文章未入库
  - 基于 `content_hash` 去重，如果标题+正文一致将被判定为重复。

## 贡献
- 欢迎提交 Issue 与 PR。提交前请确保通过本地测试并遵循项目风格。

## 许可
- 如需开放协议，请新增 `LICENSE` 文件并在此声明。