# 使用官方Python运行时作为基础镜像
FROM python:3.11-slim

# 设置工作目录
WORKDIR /app

# 设置环境变量
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DJANGO_SETTINGS_MODULE=article_web.settings \
    GUNICORN_BIND=0.0.0.0:9000

# 使用国内镜像源加速安装系统依赖
# RUN sed -i 's/deb.debian.org/mirrors.aliyun.com/g' /etc/apt/sources.list.d/debian.sources \
#     && sed -i 's/security.debian.org/mirrors.aliyun.com/g' /etc/apt/sources.list.d/debian.sources \
#     && apt-get update \
#     && apt-get install -y --no-install-recommends \
#         gcc \
#         libc6-dev \
#         pkg-config \
#         curl \
#     && rm -rf /var/lib/apt/lists/*

# 复制requirements文件
COPY requirements/ requirements/

# 使用国内PyPI镜像源加速安装Python依赖
RUN pip install --no-cache-dir -r requirements/base.txt -i https://mirrors.aliyun.com/pypi/simple/

# 复制项目文件
COPY . .

# 复制启动脚本
COPY docker/start.sh /app/start.sh

# 创建日志目录
RUN mkdir -p /app/logs && chmod 755 /app/logs

# 收集静态文件
RUN python manage.py collectstatic --noinput

# 设置启动脚本权限
RUN chmod +x /app/start.sh

# 暴露端口
EXPOSE 9000

# 健康检查
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:9000/health/ || exit 1

# 启动命令
CMD ["/app/start.sh"]