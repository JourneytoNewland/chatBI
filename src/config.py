"""项目配置管理.

使用 pydantic-settings 管理环境变量配置，支持从 .env 文件读取.
"""

from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class QdrantConfig(BaseSettings):
    """Qdrant 配置.

    Attributes:
        host: Qdrant 服务器地址
        port: Qdrant 端口
        grpc_port: gRPC 端口
        collection_name: Collection 名称
        api_key: API密钥（可选）
        timeout: 请求超时时间（秒）
    """

    model_config = SettingsConfigDict(env_prefix="QDRANT_", env_file=".env", extra="ignore")

    host: str = Field(default="localhost", description="Qdrant 服务器地址")
    port: int = Field(default=6333, description="Qdrant HTTP 端口")
    grpc_port: int = Field(default=6334, description="Qdrant gRPC 端口")
    collection_name: str = Field(default="metrics", description="Collection 名称")
    api_key: Optional[str] = Field(default=None, description="API密钥")
    timeout: float = Field(default=5.0, description="请求超时时间（秒）")

    @property
    def http_url(self) -> str:
        """获取 HTTP URL."""
        return f"http://{self.host}:{self.port}"

    @property
    def grpc_url(self) -> str:
        """获取 gRPC URL."""
        return f"{self.host}:{self.grpc_port}"


class VectorizerConfig(BaseSettings):
    """向量化器配置.

    Attributes:
        model_name: 预训练模型名称
        device: 运行设备（cpu/cuda）
        batch_size: 批处理大小
    """

    model_config = SettingsConfigDict(env_prefix="VECTORIZER_", env_file=".env", extra="ignore")

    model_name: str = Field(default="m3e-base", description="预训练模型名称")
    device: str = Field(default="cpu", description="运行设备")
    batch_size: int = Field(default=32, description="批处理大小")


class Settings(BaseSettings):
    """全局配置."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    qdrant: QdrantConfig = Field(default_factory=QdrantConfig)
    vectorizer: VectorizerConfig = Field(default_factory=VectorizerConfig)

    # 应用配置
    app_name: str = Field(default="Semantic Query System", description="应用名称")
    debug: bool = Field(default=False, description="调试模式")
    log_level: str = Field(default="INFO", description="日志级别")


# 全局配置实例
settings = Settings()
