# 文章扫描脚本配置文件

# 目录配置
GENERATED_ARTICLES_DIR = "d:/Project/Github/ArticleWeb/generated_articles/"
STATIC_FILES_DIR = "d:/Project/Github/ArticleWeb/static/file/"

# API配置
API_BASE_URL = "http://127.0.0.1:9000/api/"
API_TIMEOUT = 30

# 分类映射配置
CATEGORY_MAPPING = {
    'automotive': '汽车',
    'diary': '日记', 
    'education': '教育',
    'entertainment': '娱乐',
    'food': '美食',
    'lifestyle': '生活',
    'livelihood': '民生',
    'love_letters': '情书',
    'travel': '旅游',
    'trivia': '冷知识',
    'workplace': '职场'
}

# 文章处理配置
SUMMARY_MAX_LENGTH = 200
DEFAULT_ARTICLE_STATUS = 2  # 已发布
BATCH_SIZE = 10  # 批量处理大小

# 日志配置
LOG_LEVEL = "INFO"
LOG_FILE = "scan_articles.log"
LOG_FORMAT = "%(asctime)s - %(levelname)s - %(message)s"

# 文件处理配置
SUPPORTED_CONTENT_EXTENSIONS = ['.md', '.html']
REQUIRED_META_FIELDS = ['article_id', 'title']

# 重试配置
MAX_RETRIES = 3
RETRY_DELAY = 1  # 秒