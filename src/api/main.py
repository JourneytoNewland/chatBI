"""FastAPI 应用主入口."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.config import settings


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
    yield
    # 关闭时执行
    print(f"👋 {settings.app_name} 已关闭")


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

app.include_router(router, prefix="/api/v1", tags=["search"])
