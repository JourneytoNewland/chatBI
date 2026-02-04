#!/usr/bin/env python3
"""开发服务器启动脚本."""

import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

import uvicorn

from src.config import settings
from src.recall.vector.qdrant_store import QdrantVectorStore


def init_vector_store() -> None:
    """初始化向量存储."""
    print("📊 初始化向量存储...")
    store = QdrantVectorStore(config=settings.qdrant)

    if not store.collection_exists():
        print(f"  创建 Collection: {settings.qdrant.collection_name}")
        store.create_collection(vector_size=768, recreate=False)
    else:
        print(f"  Collection 已存在: {settings.qdrant.collection_name}")

    count = store.count()
    print(f"  当前向量数量: {count}")
    print()


def main() -> None:
    """主函数."""
    print("=" * 60)
    print(f"🚀 {settings.app_name} 开发服务器")
    print("=" * 60)
    print()

    # 初始化向量存储
    init_vector_store()

    # 启动服务器
    print("🌐 启动 API 服务器...")
    print(f"   地址: http://localhost:8000")
    print(f"   文档: http://localhost:8000/docs")
    print()

    uvicorn.run(
        "src.api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,  # 开发模式自动重载
        log_level=settings.log_level.lower(),
    )


if __name__ == "__main__":
    main()
