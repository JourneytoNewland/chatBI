"""Qdrant 向量存储封装.

提供 Qdrant 的连接管理、Collection 创建、批量 upsert 和 ANN 检索功能.
"""

import uuid
from typing import Any, Optional

import numpy as np
from qdrant_client import QdrantClient
from qdrant_client.http.exceptions import UnexpectedResponse
from qdrant_client.http.models import (
    Distance,
    PointStruct,
    UpdateStatus,
    VectorParams,
    HnswConfigDiff,
)

from src.config import QdrantConfig


def _string_to_uuid(s: str) -> uuid.UUID:
    """将字符串转换为一致的 UUID（使用哈希）.

    Args:
        s: 输入字符串

    Returns:
        UUID 对象（相同字符串总是生成相同 UUID）
    """
    import hashlib
    # 使用 SHA-256 哈希将字符串转换为 UUID
    hash_bytes = hashlib.sha256(s.encode()).digest()[:16]
    return uuid.UUID(bytes=hash_bytes)


class QdrantVectorStore:
    """Qdrant 向量存储管理器.

    提供完整的向量存储操作，包括：
    - Collection 创建与管理
    - 批量 upsert 操作
    - ANN 检索（返回 Top-K 相似向量）
    - Collection 删除

    Attributes:
        config: Qdrant 配置
        client: Qdrant 客户端实例
    """

    # 默认 HNSW 索引参数
    DEFAULT_M = 16
    DEFAULT_EF_CONSTRUCTION = 200

    def __init__(self, config: Optional[QdrantConfig] = None) -> None:
        """初始化 Qdrant 客户端.

        Args:
            config: Qdrant 配置，如果不提供则使用默认配置
        """
        self.config = config or QdrantConfig()
        self.client: Optional[QdrantClient] = None

    def connect(self) -> QdrantClient:
        """建立连接.

        优先检查 path/location 配置以启用本地模式，否则使用 HTTP 连接。

        Returns:
            QdrantClient 实例
        """
        if self.client is None:
            if self.config.path or self.config.location:
                print(f"📦 初始化 Qdrant 本地模式: path={self.config.path}, location={self.config.location}")
                self.client = QdrantClient(
                    location=self.config.location,
                    path=self.config.path,
                )
            else:
                self.client = QdrantClient(
                    url=self.config.http_url,
                    api_key=self.config.api_key,
                    timeout=self.config.timeout,
                    prefer_grpc=False,  # 使用 HTTP 而不是 gRPC
                )
        return self.client

    def create_collection(
        self,
        vector_size: int = 768,
        recreate: bool = False,
    ) -> bool:
        """创建 Collection.

        Args:
            vector_size: 向量维度，默认为 768（m3e-base）
            recreate: 如果已存在是否重建

        Returns:
            是否创建成功

        Raises:
            RuntimeError: 创建失败时抛出
        """
        client = self.connect()
        collection_name = self.config.collection_name

        if recreate:
            try:
                client.delete_collection(collection_name)
            except Exception:
                pass

        # 检查 collection 是否存在
        try:
             if client.collection_exists(collection_name):
                 return True
        except Exception:
            pass

        try:
            client.create_collection(
                collection_name=collection_name,
                vectors_config=VectorParams(
                    size=vector_size,
                    distance=Distance.COSINE,
                ),
                hnsw_config=HnswConfigDiff(
                    m=self.DEFAULT_M,
                    ef_construct=self.DEFAULT_EF_CONSTRUCTION,
                ),
            )
            return True
        except Exception as e:
            msg = f"Failed to create collection: {e}"
            raise RuntimeError(msg) from e

    def upsert(
        self,
        ids: list[str],
        vectors: list[list[float] | np.ndarray],
        payloads: list[dict[str, Any]],
        batch_size: int = 64,
    ) -> int:
        """批量插入或更新向量.

        Args:
            ids: 向量 ID 列表
            vectors: 向量列表（每个元素是 768 维向量）
            payloads: payload 列表，每个 payload 是指标元数据
            batch_size: 批处理大小

        Returns:
            成功插入的点数量

        Raises:
            ValueError: 输入数据长度不一致时抛出
            RuntimeError: upsert 失败时抛出

        Example:
            >>> store = QdrantVectorStore()
            >>> ids = ["metric_1", "metric_2"]
            >>> vectors = [[0.1, 0.2, ...], [0.3, 0.4, ...]]
            >>> payloads = [
            ...     {"name": "GMV", "code": "gmv", ...},
            ...     {"name": "DAU", "code": "dau", ...}
            ... ]
            >>> count = store.upsert(ids, vectors, payloads)
        """
        if not (len(ids) == len(vectors) == len(payloads)):
            msg = f"Length mismatch: ids={len(ids)}, vectors={len(vectors)}, payloads={len(payloads)}"
            raise ValueError(msg)

        if not ids:
            return 0

        client = self.connect()

        # 将 numpy 数组转换为列表
        vectors_converted = [
            v.tolist() if isinstance(v, np.ndarray) else v for v in vectors
        ]

        # 构建点列表 - 使用 UUID 字符串格式的 ID（gRPC 要求）
        points = [
            PointStruct(
                id=str(_string_to_uuid(str(idx))),  # 转换为 UUID 字符串
                vector=vec,
                payload=payload,
            )
            for idx, vec, payload in zip(ids, vectors_converted, payloads)
        ]

        # 批量 upsert
        total_upserted = 0
        for i in range(0, len(points), batch_size):
            batch = points[i : i + batch_size]
            try:
                operation_info = client.upsert(
                    collection_name=self.config.collection_name,
                    points=batch,
                )
                if operation_info.status == UpdateStatus.COMPLETED:
                    total_upserted += len(batch)
            except Exception as e:
                msg = f"Failed to upsert batch {i}-{i + len(batch)}: {e}"
                raise RuntimeError(msg) from e

        return total_upserted

    def search(
        self,
        query_vector: list[float] | np.ndarray,
        top_k: int = 10,
        score_threshold: Optional[float] = None,
    ) -> list[dict[str, Any]]:
        """ANN 检索，返回 Top-K 相似向量.

        Args:
            query_vector: 查询向量（768维）
            top_k: 返回前 K 个结果
            score_threshold: 相似度阈值，低于该值的结果将被过滤

        Returns:
            检索结果列表，每个元素包含：
            - id: 向量 ID
            - score: 相似度分数
            - payload: 指标元数据

        Example:
            >>> store = QdrantVectorStore()
            >>> query_vec = [0.1, 0.2, ...]  # 768 维
            >>> results = store.search(query_vec, top_k=5)
            >>> for r in results:
            ...     print(f"{r['payload']['name']}: {r['score']:.3f}")
        """
        client = self.connect()

        # 转换 numpy 数组
        if isinstance(query_vector, np.ndarray):
            query_vector = query_vector.tolist()

        try:
            search_result = client.search(
                collection_name=self.config.collection_name,
                query_vector=query_vector,
                limit=top_k,
                score_threshold=score_threshold,
            )
        except UnexpectedResponse as e:
            msg = f"Search failed: {e}"
            raise RuntimeError(msg) from e

        # 格式化结果
        results = [
            {
                "id": hit.id,
                "score": hit.score,
                "payload": hit.payload,
            }
            for hit in search_result
        ]

        return results

    def count(self) -> int:
        """获取 Collection 中的向量数量.

        Returns:
            向量数量
        """
        client = self.connect()
        try:
            collection_info = client.get_collection(self.config.collection_name)
            return collection_info.points_count or 0
        except Exception:
            return 0

    def delete_collection(self) -> bool:
        """删除 Collection.

        Returns:
            是否删除成功
        """
        client = self.connect()
        collection_name = self.config.collection_name

        if not client.collection_exists(collection_name):
            return True

        try:
            client.delete_collection(collection_name)
            return True
        except Exception as e:
            msg = f"Failed to delete collection: {e}"
            raise RuntimeError(msg) from e

    def collection_exists(self) -> bool:
        """检查 Collection 是否存在.

        Returns:
            Collection 是否存在
        """
        client = self.connect()
        return client.collection_exists(self.config.collection_name)

    def close(self) -> None:
        """关闭连接."""
        if self.client is not None:
            self.client.close()
            self.client = None
