#!/bin/bash

# Docker构建脚本
# 从项目根目录构建Docker镜像

echo "Building Docker image..."
docker build --no-cache -f docker/Dockerfile -t article-web .

echo "Build completed!"
# echo "To run the container:"
# echo "docker run -d -p 9000:9000 --name article-web article-web"