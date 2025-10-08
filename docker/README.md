# Docker 部署指南

本项目支持使用 Docker 进行容器化部署，使用 Gunicorn 作为 WSGI 服务器，默认运行在 9000 端口。

## 快速开始

### 1. 构建 Docker 镜像

```bash
docker build -t article-web .
```

### 2. 运行容器

```bash
docker run -d \
  --name article-web \
  -p 9000:9000 \
  -e SECRET_KEY="your-secret-key-here" \
  -e DEBUG=False \
  -v $(pwd)/db.sqlite3:/app/db.sqlite3 \
  -v $(pwd)/media:/app/media \
  article-web
```

### 3. 使用 Docker Compose（推荐）

```bash
# 启动服务
docker-compose up -d

# 查看日志
docker-compose logs -f

# 停止服务
docker-compose down
```

## 环境变量配置

### Django 配置

- `SECRET_KEY`: Django 密钥（生产环境必须设置）
- `DEBUG`: 调试模式（默认: False）
- `ALLOWED_HOSTS`: 允许的主机列表

### Gunicorn 配置

- `GUNICORN_BIND`: 绑定地址（默认: 0.0.0.0:9000）
- `GUNICORN_WORKERS`: 工作进程数（默认: 1）
- `GUNICORN_THREADS`: 每个进程的线程数（默认: 1）
- `GUNICORN_WORKER_CLASS`: 工作进程类型（默认: gthread）
- `GUNICORN_TIMEOUT`: 请求超时时间（默认: 30秒）
- `GUNICORN_KEEPALIVE`: Keep-alive 时间（默认: 2秒）
- `GUNICORN_MAX_REQUESTS`: 每个进程处理的最大请求数（默认: 0，不重启）
- `GUNICORN_PRELOAD_APP`: 预加载应用（默认: False）
- `GUNICORN_LOGLEVEL`: 日志级别（默认: info）

## 生产环境部署建议

### 1. 性能优化

```bash
docker run -d \
  --name article-web \
  -p 9000:9000 \
  -e SECRET_KEY="your-production-secret-key" \
  -e DEBUG=False \
  -e GUNICORN_WORKERS=4 \
  -e GUNICORN_THREADS=2 \
  -e GUNICORN_WORKER_CLASS=gthread \
  -e GUNICORN_PRELOAD_APP=True \
  -e GUNICORN_MAX_REQUESTS=1000 \
  -e GUNICORN_MAX_REQUESTS_JITTER=100 \
  -v $(pwd)/db.sqlite3:/app/db.sqlite3 \
  -v $(pwd)/media:/app/media \
  -v $(pwd)/logs:/var/log/article-web \
  --restart unless-stopped \
  article-web
```

### 2. 资源限制

```bash
docker run -d \
  --name article-web \
  -p 9000:9000 \
  --memory=512m \
  --cpus=1.0 \
  -e SECRET_KEY="your-production-secret-key" \
  article-web
```

### 3. 健康检查

容器内置了健康检查，会定期检查应用状态：

```bash
# 查看健康状态
docker ps

# 查看健康检查日志
docker inspect --format='{{json .State.Health}}' article-web
```

## 数据持久化

### 数据库

```bash
# 挂载 SQLite 数据库文件
-v $(pwd)/db.sqlite3:/app/db.sqlite3
```

### 媒体文件

```bash
# 挂载媒体文件目录
-v $(pwd)/media:/app/media
```

### 日志文件

```bash
# 挂载日志目录
-v $(pwd)/logs:/var/log/article-web
```

## 故障排除

### 查看容器日志

```bash
# 查看实时日志
docker logs -f article-web

# 查看最近的日志
docker logs --tail 100 article-web
```

### 进入容器调试

```bash
# 进入运行中的容器
docker exec -it article-web bash

# 运行 Django 管理命令
docker exec -it article-web python manage.py shell
```

### 重新构建镜像

```bash
# 清理缓存重新构建
docker build --no-cache -t article-web .
```

## 安全注意事项

1. **生产环境必须设置强密钥**：
   ```bash
   -e SECRET_KEY="$(openssl rand -base64 32)"
   ```

2. **关闭调试模式**：
   ```bash
   -e DEBUG=False
   ```

3. **限制允许的主机**：
   ```bash
   -e ALLOWED_HOSTS="yourdomain.com,www.yourdomain.com"
   ```

4. **使用非 root 用户运行**（已内置）

5. **定期更新基础镜像和依赖**

## 监控和日志

### 应用监控

- 健康检查端点：`http://localhost:9000/health/`
- 应用状态：通过 Docker 健康检查

### 日志管理

- Gunicorn 访问日志：`/var/log/article-web/access.log`
- Gunicorn 错误日志：`/var/log/article-web/error.log`
- Django 应用日志：通过标准输出

## 扩展部署

### 使用 Nginx 反向代理

取消注释 `docker-compose.yml` 中的 nginx 服务配置，并创建相应的 nginx 配置文件。

### 集群部署

可以使用 Docker Swarm 或 Kubernetes 进行集群部署，实现高可用和负载均衡。