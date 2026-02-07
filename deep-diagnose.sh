#!/bin/bash
# Docker 深度诊断脚本

echo "=== 🔍 Docker 深度网络诊断 ==="
echo ""

DOCKER="/Applications/Docker.app/Contents/Resources/bin/docker"

# 1. 检查 Docker daemon 日志
echo "1️⃣  Docker Daemon 日志（最近10行）:"
if [ -f ~/Library/Containers/com.docker.docker/Data/log/*/com.docker.backend.log ]; then
    tail -10 ~/Library/Containers/com.docker.docker/Data/log/*/com.docker.backend.log 2>/dev/null | grep -i -E "(error|warn|fail|network|proxy)" | tail -5 || echo "   无明显错误"
else
    echo "   日志文件未找到"
fi

echo ""
echo "2️⃣  网络连接测试:"

# 测试 DNS 解析
echo -n "   a) DNS 解析 (registry-1.docker.io): "
if nslookup registry-1.docker.io 8.8.8.8 >/dev/null 2>&1; then
    echo "✅ 可解析"
else
    echo "❌ 无法解析"
fi

# 测试 HTTPS 连接
echo -n "   b) HTTPS 连接 (Docker Hub): "
if timeout 5 curl -sI https://registry-1.docker.io >/dev/null 2>&1; then
    echo "✅ 可访问"
    curl -sI https://registry-1.docker.io | head -2
else
    echo "❌ 无法访问 (超时或证书错误)"
fi

# 测试镜像加速器
echo -n "   c) 镜像加速器 (ustc.edu.cn): "
if timeout 5 curl -sI https://docker.mirrors.ustc.edu.cn >/dev/null 2>&1; then
    echo "✅ 可访问"
else
    echo "❌ 无法访问"
    nslookup docker.mirrors.ustc.edu.cn 8.8.8.8 2>&1 | grep "Server:" | head -1
fi

echo ""
echo "3️⃣ 代理配置检查:"

# 系统代理
echo "   系统代理设置:"
scutil --proxy 2>/dev/null | grep -E "(HTTPEnable|HTTPSEnable|SOCKSEnable)" | head -3

# Docker 内部代理
echo "   Docker 代理:"
$DOCKER info 2>/dev/null | grep -i "HTTPProxy" || echo "   未配置"

# 环境变量
echo "   环境变量:"
env | grep -i proxy | sort || echo "   无代理环境变量"

echo ""
echo "4️⃣ 防火墙检查:"

# macOS 防火墙
if /usr/libexec/ApplicationFirewall/socketfilterfw --getglobalstate 2>/dev/null | grep -q "enabled: 1"; then
    echo "   ⚠️  系统防火墙已启用"
    echo "   这可能会阻止 Docker 连接"
else
    echo "   ✅ 系统防火墙未启用"
fi

echo ""
echo "5️⃣ Docker 网络模式:"
$DOCKER network ls 2>/dev/null || echo "   无法获取网络列表"

echo ""
echo "6️⃣ TLS/证书测试:"
echo "   测试 Docker Hub TLS:"
timeout 5 openssl s_client -connect registry-1.docker.io:443 -servername registry-1.docker.io </dev/null 2>&1 | grep -E "(subject|issuer|Verify return code)" | head -5

echo ""
echo "7️⃣ 实际拉取测试（查看详细错误）:"
echo "   尝试拉取 hello-world 镜像..."
$DOCKER pull hello-world:latest 2>&1 | tail -15

echo ""
echo "=== 诊断完成 ==="
echo ""
echo "💡 根据以上诊断结果，可能的问题："
echo ""
echo "1. 网络代理 - 需要配置 HTTP/HTTPS 代理"
echo "2. DNS 污染 - 使用 8.8.8.8 或 1.1.1.1"
echo "3. 防火墙 - 允许 Docker Desktop 访问网络"
echo "4. TLS 证书 - 可能需要更新根证书"
echo "5. ISP 限制 - 某些网络可能阻止 Docker Hub"
echo ""
