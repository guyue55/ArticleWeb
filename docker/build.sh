#!/bin/bash

# Docker构建脚本
# 从项目根目录构建Docker镜像

echo "Building Docker image..."
cd ..
docker build -f docker/Dockerfile -t article .

echo "Build completed!"
echo "To run the container:"
echo "docker run -d -p 9008:9000 --name article-app article"