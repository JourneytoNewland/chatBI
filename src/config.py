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

    model_name: str = Field(default="sentence-transformers/all-MiniLM-L6-v2", description="预训练模型名称")
    device: str = Field(default="cpu", description="运行设备")
    batch_size: int = Field(default=32, description="批处理大小")


class ZhipuAIConfig(BaseSettings):
    """智谱 AI 配置.

    Attributes:
        api_key: 智谱 API Key
        model: 使用的模型名称（glm-4-flash, glm-4-air, glm-4-plus）
        timeout: 请求超时时间（秒）
        batch_size: 批量生成摘要时的批次大小
    """

    model_config = SettingsConfigDict(env_prefix="ZHIPUAI_", env_file=".env", extra="ignore")

    api_key: Optional[str] = Field(default=None, description="智谱 API Key")
    model: str = Field(default="glm-4-flash", description="使用的模型名称")
    timeout: float = Field(default=30.0, description="请求超时时间（秒）")
    batch_size: int = Field(default=5, ge=1, le=10, description="批量生成摘要时的批次大小")


class Neo4jConfig(BaseSettings):
    """Neo4j 图数据库配置.

    Attributes:
        uri: Neo4j 连接 URI
        user: 用户名（环境变量 NEO4J_USER）
        password: 密码
        database: 数据库名称
    """

    model_config = SettingsConfigDict(env_prefix="NEO4J_", env_file=".env", extra="ignore")

    uri: Optional[str] = Field(default=None, description="Neo4j 连接 URI")
    user: Optional[str] = Field(default=None, description="用户名")
    password: Optional[str] = Field(default=None, description="密码")
    database: str = Field(default="neo4j", description="数据库名称")


class PostgreSQLConfig(BaseSettings):
    """PostgreSQL 配置.

    Attributes:
        host: PostgreSQL 主机地址
        port: PostgreSQL 端口
        database: 数据库名称
        user: 用户名
        password: 密码
        pool_size: 连接池大小
        max_overflow: 最大溢出连接数
        pool_timeout: 连接池超时(秒)
        pool_recycle: 连接回收时间(秒)
    """

    model_config = SettingsConfigDict(env_prefix="POSTGRES_", env_file=".env", extra="ignore")

    host: str = Field(default="localhost", description="PostgreSQL 主机地址")
    port: int = Field(default=5432, description="PostgreSQL 端口")
    database: str = Field(default="chatbi", description="数据库名称")
    user: str = Field(default="chatbi", description="用户名")
    password: str = Field(default="chatbi_password", description="密码")
    pool_size: int = Field(default=10, description="连接池大小")
    max_overflow: int = Field(default=20, description="最大溢出连接数")
    pool_timeout: int = Field(default=30, description="连接池超时(秒)")
    pool_recycle: int = Field(default=3600, description="连接回收时间(秒)")

    @property
    def url(self) -> str:
        """获取数据库连接URL."""
        return f"postgresql://{self.user}:{self.password}@{self.host}:{self.port}/{self.database}"


class Settings(BaseSettings):
    """全局配置."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    qdrant: QdrantConfig = Field(default_factory=QdrantConfig)
    vectorizer: VectorizerConfig = Field(default_factory=VectorizerConfig)
    zhipuai: ZhipuAIConfig = Field(default_factory=ZhipuAIConfig)
    neo4j: Neo4jConfig = Field(default_factory=Neo4jConfig)
    postgres: PostgreSQLConfig = Field(default_factory=PostgreSQLConfig)

    # 应用配置
    app_name: str = Field(default="Semantic Query System", description="应用名称")
    debug: bool = Field(default=False, description="调试模式")
    log_level: str = Field(default="INFO", description="日志级别")


# 全局配置实例
settings = Settings()
