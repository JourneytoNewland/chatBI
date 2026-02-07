#!/bin/bash
# Docker 完整诊断和修复脚本

DOCKER="/Applications/Docker.app/Contents/Resources/bin/docker"

echo "=== 🩺 Docker 完整诊断 ==="
echo ""

# 1. 检查 Docker 是否运行
echo "1️⃣ Docker 运行状态:"
$DOCKER info > /dev/null 2>&1
if [ $? -eq 0 ]; then
    echo "   ✅ Docker 正在运行"
else
    echo "   ❌ Docker 未运行，请先启动 Docker Desktop"
    echo "   命令: open /Applications/Docker.app"
    exit 1
fi

# 2. 检查镜像配置
echo ""
echo "2️⃣ 镜像加速配置:"
$DOCKER info | grep -A 3 "Registry Mirrors" | sed 's/^/   /'

# 3. 测试 DNS
echo ""
echo "3️⃣ DNS 配置:"
$DOCKER info | grep -A 2 "DNS" | sed 's/^/   /'

# 4. 测试网络连接
echo ""
echo "4️⃣ 网络连接测试:"
echo -n "   测试 Docker Hub: "
timeout 5 curl -sI https://registry-1.docker.io > /dev/null 2>&1
if [ $? -eq 0 ]; then
    echo "✅ 可访问"
else
    echo "❌ 无法访问"
    echo "   可能原因：代理、防火墙或网络限制"
fi

echo -n "   测试镜像加速器: "
timeout 5 curl -sI https://docker.mirrors.ustc.edu.cn > /dev/null 2>&1
if [ $? -eq 0 ]; then
    echo "✅ 可访问"
else
    echo "❌ 无法访问"
fi

# 5. 尝试拉取测试镜像
echo ""
echo "5️⃣ 镜像拉取测试:"
echo "   正在拉取 alpine:latest (测试镜像)..."
echo "   如果失败，可能需要："
echo "   a) 重启 Docker Desktop"
echo "   b) 配置系统代理"
echo "   c) 使用离线镜像"

$DOCKER pull alpine:latest 2>&1 | tail -5

if [ $? -eq 0 ]; then
    echo ""
    echo "   ✅ 镜像拉取成功！"
    echo ""
    echo "🎉 Docker 配置正常，可以启动服务了！"
    echo ""
    echo "下一步:"
    echo "  docker compose up -d"
else
    echo ""
    echo "   ❌ 镜像拉取失败"
    echo ""
    echo "💡 解决方案："
    echo ""
    echo "方案 A: 重启 Docker Desktop"
    echo "  1. 完全退出 Docker Desktop"
    echo "  2. 重新打开 Docker Desktop"
    echo "  3. 确认 Docker Engine 配置已保存"
    echo "  4. 再次运行此脚本验证"
    echo ""
    echo "方案 B: 配置系统代理"
    echo "  如果你的网络需要代理，在 Docker Desktop 中配置:"
    echo "  Settings → Resources → Proxies → Manual proxy configuration"
    echo ""
    echo "方案 C: 使用演示模式（临时）"
    echo "  在等待 Docker 修复期间，可以使用演示模式测试功能:"
    echo "  ./run_demo.sh"
fi

echo ""
echo "=== 诊断完成 ==="
