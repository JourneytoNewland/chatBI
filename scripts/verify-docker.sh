#!/bin/bash
# Docker 配置验证脚本

echo "=== Docker 配置验证 ==="
echo ""

DOCKER_CMD="/Applications/Docker.app/Contents/Resources/bin/docker"

echo "1️⃣  测试 Docker 基础功能..."
$DOCKER_CMD info > /dev/null 2>&1
if [ $? -eq 0 ]; then
    echo "   ✅ Docker 运行正常"
else
    echo "   ❌ Docker 未运行，请先启动 Docker Desktop"
    exit 1
fi

echo ""
echo "2️⃣ 测试拉取镜像（使用镜像加速）..."
echo "   正在拉取 alpine 镜像..."
$DOCKER_CMD pull alpine:latest > /dev/null 2>&1
if [ $? -eq 0 ]; then
    echo "   ✅ 镜像拉取成功！网络配置正确"
else
    echo "   ❌ 镜像拉取失败"
    echo ""
    echo "💡 建议："
    echo "   1. 检查 Docker Engine 配置是否已保存"
    echo "   2. 确保 DNS 设置为 8.8.8.8 和 114.114.114.114"
    echo "   3. 尝试重启 Docker Desktop"
    exit 1
fi

echo ""
echo "3️⃣ 查看镜像列表..."
$DOCKER_CMD images | head -5

echo ""
echo "4️⃣ 测试运行容器..."
$DOCKER_CMD run --rm alpine echo "Hello from Docker!" > /dev/null 2>&1
if [ $? -eq 0 ]; then
    echo "   ✅ 容器运行成功！"
else
    echo "   ❌ 容器运行失败"
    exit 1
fi

echo ""
echo "=== 🎉 Docker 配置验证成功！ ==="
echo ""
echo "现在可以启动服务了："
echo "  ./start-docker.sh"
echo ""
