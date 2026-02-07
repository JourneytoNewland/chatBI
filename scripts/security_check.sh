#!/bin/bash
echo "🔍 运行安全检查..."
# 检查硬编码密钥
if grep -rn "api_key\s*=\s*['\"][^'\"]{20,}['\"]" --include="*.py" src/ 2>/dev/null | grep -v "os.getenv"; then
    echo "❌ 发现硬编码API密钥"
    exit 1
fi
# 检查日志文件
if git ls-files | grep -q "\.log$"; then
    echo "❌ 日志文件被git追踪"
    exit 1
fi
echo "✅ 安全检查通过"
