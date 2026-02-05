"""FastAPI 应用主入口."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.config import settings
from src.recall.graph.neo4j_client import Neo4jClient
from src.recall.vector.qdrant_store import QdrantVectorStore
from src.recall.vector.vectorizer import MetricVectorizer


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理.

    Args:
        app: FastAPI 应用实例
    """
    # 启动时执行
    print(f"🚀 {settings.app_name} 启动中...")
    print(f"📊 Qdrant: {settings.qdrant.http_url}")
    print(f"🧠 模型: {settings.vectorizer.model_name}")

    # 初始化向量化器
    print("⏳ 初始化向量化器...")
    vectorizer = MetricVectorizer(model_name=settings.vectorizer.model_name)
    app.state.vectorizer = vectorizer
    print(f"✅ 向量化器已加载: {settings.vectorizer.model_name}")

    # 初始化 Qdrant Vector Store
    print("⏳ 初始化 Qdrant Vector Store...")
    vector_store = QdrantVectorStore(config=settings.qdrant)

    # 创建 Collection（如果不存在）- 使用实际模型的向量维度
    try:
        vector_size = vectorizer.embedding_dim
        print(f"📐 向量维度: {vector_size}")
        vector_store.create_collection(vector_size=vector_size, recreate=False)
        print(f"✅ Collection 已就绪: {settings.qdrant.collection_name}")
    except Exception as e:
        print(f"⚠️  Collection 创建/检查失败: {e}")

    app.state.vector_store = vector_store
    print(f"✅ Qdrant Vector Store 已连接: {settings.qdrant.http_url}")

    # 初始化 Neo4j Client（如果配置了）
    if settings.neo4j.uri:
        print("⏳ 初始化 Neo4j Client...")
        try:
            neo4j_client = Neo4jClient(
                uri=settings.neo4j.uri,
                user=settings.neo4j.user or "neo4j",
                password=settings.neo4j.password or ""
            )
            # 测试连接
            neo4j_client.close()
            app.state.neo4j_client = neo4j_client
            print(f"✅ Neo4j 已连接: {settings.neo4j.uri}")
        except Exception as e:
            print(f"⚠️  Neo4j 连接失败: {e}")
            print("⚠️  将使用仅向量召回模式")
            app.state.neo4j_client = None
    else:
        print("⚠️  Neo4j 未配置，使用仅向量召回模式")
        app.state.neo4j_client = None

    # 打印服务配置
    print(f"\n📋 服务配置:")
    print(f"   - ZhipuAI: {'✅' if settings.zhipuai.api_key else '❌'}")
    if settings.zhipuai.api_key:
        print(f"   - ZhipuAI Model: {settings.zhipuai.model}")
    print(f"   - 向量召回: ✅")
    print(f"   - 图谱召回: {'✅' if app.state.neo4j_client else '❌'}")
    print(f"   - GLM 摘要: {'✅' if settings.zhipuai.api_key else '❌'}")
    print()

    yield

    # 关闭时执行
    print(f"\n👋 {settings.app_name} 正在关闭...")
    if hasattr(app.state, 'neo4j_client') and app.state.neo4j_client:
        app.state.neo4j_client.close()
    print(f"✅ {settings.app_name} 已关闭")


# 创建 FastAPI 应用
app = FastAPI(
    title=settings.app_name,
    description="基于向量库+图谱的混合语义检索系统",
    version="0.1.0",
    lifespan=lifespan,
)

# 配置 CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境应限制具体域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# 健康检查
@app.get("/health")
async def health_check() -> dict[str, str]:
    """健康检查接口.

    Returns:
        服务状态
    """
    return {
        "status": "healthy",
        "service": settings.app_name,
    }


# 导入路由
from src.api.routes import router
from src.api.management_api import router as management_router
from src.api.debug_routes import router as debug_router

app.include_router(router, prefix="/api/v1", tags=["search"])
app.include_router(management_router, tags=["data-management"])
app.include_router(debug_router, tags=["debug"])
