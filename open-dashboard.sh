#!/bin/bash

# 智能问数系统 - 快速启动脚本

echo "=========================================="
echo "🚀 智能问数系统 - 快速启动"
echo "=========================================="
echo ""

# 检查服务是否运行
echo "📊 检查服务状态..."
echo ""

# 检查后端
if curl -s http://localhost:8000/health > /dev/null 2>&1; then
    echo "✅ 后端服务运行中 (http://localhost:8000)"
else
    echo "❌ 后端服务未运行"
    echo "   请先启动: python -m uvicorn src.api.main:app --host 0.0.0.0 --port 8000"
fi

# 检查前端
if lsof -ti:8080 > /dev/null 2>&1; then
    echo "✅ 前端服务运行中 (http://localhost:8080)"
else
    echo "❌ 前端服务未运行"
    echo "   请先启动: cd frontend && python -m http.server 8080"
fi

echo ""
echo "=========================================="
echo "🌐 访问地址"
echo "=========================================="
echo ""
echo "🌟 统一管理平台 (推荐):"
echo "   http://localhost:8080/dashboard.html"
echo ""
echo "📄 其他界面:"
echo "   智能检索: http://localhost:8080/index.html"
echo "   图谱管理: http://localhost:8080/graph-management.html"
echo "   意图分析: http://localhost:8080/intent-visualization.html"
echo ""
echo "📚 API 文档:"
echo "   http://localhost:8000/docs"
echo ""
echo "=========================================="

# 自动打开浏览器（MacOS）
if [[ "$OSTYPE" == "darwin"* ]]; then
    echo "📱 正在打开浏览器..."
    sleep 1
    open http://localhost:8080/dashboard.html
fi
