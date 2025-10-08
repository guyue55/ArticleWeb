# gunicorn.conf.py 
"""
Gunicorn 配置文件 - 完整环境变量版本
支持通过环境变量灵活配置所有参数
"""

# import multiprocessing
import os


# 进程名称
proc_name = "article-web"

# 默认工作进程数 (默认: CPU核心数 * 2 + 1)
# default_workers = multiprocessing.cpu_count() * 2 + 1
default_workers = 1

# 工作进程类型
# 可选值: sync, eventlet, gevent, tornado, gthread
worker_class = os.environ.get('GUNICORN_WORKER_CLASS', 'gthread')

# 每个worker的线程数 (仅对gthread worker有效)
threads = int(os.environ.get('GUNICORN_THREADS', '1'))


# =============================================================================
# 服务器套接字配置
# =============================================================================

# 监听地址和端口
bind = os.environ.get('GUNICORN_BIND', '0.0.0.0:9000')

# 请求队列大小
backlog = int(os.environ.get('GUNICORN_BACKLOG', '2048'))

# 允许内核复用端口
reuse_port = os.environ.get('GUNICORN_REUSE_PORT', 'True').lower() == 'true'

# =============================================================================
# 工作进程配置
# =============================================================================

# 工作进程数 (默认: CPU核心数 * 2 + 1)
workers = int(os.environ.get('GUNICORN_WORKERS', str(default_workers)))

# 每个worker的最大并发连接数 (仅对异步worker有效)
worker_connections = int(os.environ.get('GUNICORN_WORKER_CONNECTIONS', '1000'))

# Worker生命周期管理
# 处理多少请求后重启worker (防止内存泄漏)
max_requests = int(os.environ.get('GUNICORN_MAX_REQUESTS', '0'))  # 0表示不重启

# max_requests的随机抖动范围
max_requests_jitter = int(os.environ.get('GUNICORN_MAX_REQUESTS_JITTER', '0'))

# 请求超时时间 (秒)
timeout = int(os.environ.get('GUNICORN_TIMEOUT', '30'))

# Keep-Alive时间 (秒)
keepalive = int(os.environ.get('GUNICORN_KEEPALIVE', '2'))

# 优雅关闭超时时间 (秒)
graceful_timeout = int(os.environ.get('GUNICORN_GRACEFUL_TIMEOUT', '30'))

# =============================================================================
# 预加载配置
# =============================================================================

# 预加载应用
# True: master进程加载应用，然后fork worker (内存效率高)
# False: 每个worker独立加载应用 (更稳定，支持代码重载)
preload_app = os.environ.get('GUNICORN_PRELOAD_APP', 'False').lower() == 'true'

# =============================================================================
# 安全配置
# =============================================================================

# 运行用户和组
# 开发环境注释掉用户设置，避免权限问题
# user = os.environ.get('GUNICORN_USER', 'www-data')
# group = os.environ.get('GUNICORN_GROUP', 'www-data')

# 文件权限掩码
umask = int(os.environ.get('GUNICORN_UMASK', '0o002'), 8)

# 临时上传目录
tmp_upload_dir = os.environ.get('GUNICORN_TMP_UPLOAD_DIR') or None

# Worker临时目录 (建议使用内存文件系统提高性能 /dev/shm)
# 开发环境使用当前目录避免权限问题
worker_tmp_dir = os.environ.get('GUNICORN_WORKER_TMP_DIR', '/tmp')

# =============================================================================
# 日志配置
# =============================================================================

# 访问日志文件路径
accesslog = os.environ.get('GUNICORN_ACCESSLOG', "logs/access.log")

# 错误日志文件路径
errorlog = os.environ.get('GUNICORN_ERRORLOG', "logs/error.log")

# 日志级别: debug, info, warning, error, critical
loglevel = os.environ.get('GUNICORN_LOGLEVEL', 'info')

# 访问日志格式
access_log_format = os.environ.get('GUNICORN_ACCESS_LOG_FORMAT', 
    '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s')

# 捕获stdout/stderr到日志文件
capture_output = os.environ.get('GUNICORN_CAPTURE_OUTPUT', 'False').lower() == 'true'

# 启用stdio继承
enable_stdio_inheritance = os.environ.get('GUNICORN_ENABLE_STDIO_INHERITANCE', 'False').lower() == 'true'

# =============================================================================
# 性能调优
# =============================================================================

# HTTP请求行大小限制
limit_request_line = int(os.environ.get('GUNICORN_LIMIT_REQUEST_LINE', '4094'))

# HTTP请求头字段数限制
limit_request_fields = int(os.environ.get('GUNICORN_LIMIT_REQUEST_FIELDS', '100'))

# HTTP请求头字段大小限制
limit_request_field_size = int(os.environ.get('GUNICORN_LIMIT_REQUEST_FIELD_SIZE', '8190'))

# =============================================================================
# 开发相关
# =============================================================================

# 代码更改时自动重载 (开发环境用)
reload = os.environ.get('GUNICORN_RELOAD', 'False').lower() == 'true'

# 重载时额外监控的文件
# reload_extra_files = os.environ.get('GUNICORN_RELOAD_EXTRA_FILES', '').split(',')

# =============================================================================
# 后台运行
# =============================================================================

# 后台运行
daemon = os.environ.get('GUNICORN_DAEMON', 'False').lower() == 'true'

# PID文件路径
pidfile = os.environ.get('GUNICORN_PIDFILE') or None

# =============================================================================
# 环境变量传递
# =============================================================================

# 原始环境变量
raw_env = os.environ.get('GUNICORN_RAW_ENV', '').split(',') if os.environ.get('GUNICORN_RAW_ENV') else []

# =============================================================================
# 钩子函数
# =============================================================================

def when_ready(server):
    """服务器启动完成后的回调"""
    server.log.info("Server is ready. Spawning workers")
    if os.environ.get('GUNICORN_WHEN_READY'):
        server.log.info(os.environ.get('GUNICORN_WHEN_READY'))

def pre_fork(server, worker):
    """worker fork前的回调"""
    server.log.info("Worker spawned (pid: %s)", worker.pid)

def pre_exec(server):
    """master进程重启前的回调"""
    server.log.info("Forked child, re-executing.")

def post_fork(server, worker):
    """worker fork后的回调"""
    server.log.info("Worker spawned (pid: %s)", worker.pid)

def post_worker_init(worker):
    """worker初始化完成后的回调"""
    worker.log.info("Worker initialized (pid: %s)", worker.pid)

def worker_int(worker):
    """worker接收到INT或QUIT信号时的回调"""
    worker.log.info("worker received INT or QUIT signal")

def worker_abort(worker):
    """worker接收到ABORT信号时的回调"""
    worker.log.info("worker received SIGABRT signal")

def pre_request(worker, req):
    """处理请求前的回调"""
    worker.log.debug("%s %s" % (req.method, req.path))

def post_request(worker, req, environ, resp):
    """处理请求后的回调"""
    pass

def child_exit(server, worker):
    """子进程退出时的回调"""
    server.log.info("Worker exiting (pid: %s)", worker.pid)

def worker_exit(server, worker):
    """worker退出时的回调"""
    server.log.info("Worker exiting (pid: %s)", worker.pid)

def nworkers_changed(server, new_value, old_value):
    """worker数量改变时的回调"""
    server.log.info("Worker count changed from %s to %s", old_value, new_value)

def on_exit(server):
    """服务器退出时的回调"""
    server.log.info("Server shutting down")