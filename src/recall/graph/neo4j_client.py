"""Neo4j 客户端封装."""

from typing import Any, Optional

from neo4j import GraphDatabase
from neo4j.exceptions import ServiceUnavailable

from src.config import settings


class Neo4jClient:
    """Neo4j 客户端封装.

    提供图数据库的连接管理和基础操作。
    """

    def __init__(
        self,
        uri: Optional[str] = None,
        user: Optional[str] = None,
        password: Optional[str] = None,
    ) -> None:
        """初始化 Neo4j 客户端.

        Args:
            uri: Neo4j URI，默认从环境变量读取
            user: 用户名，默认从环境变量读取
            password: 密码，默认从环境变量读取
        """
        self.uri = uri or "bolt://localhost:7687"
        self.user = user or "neo4j"
        self.password = password or "password"
        self.driver: Optional[GraphDatabase.driver] = None

    def connect(self) -> GraphDatabase.driver:
        """建立连接.

        Returns:
            Neo4j driver 实例

        Raises:
            RuntimeError: 连接失败时抛出
        """
        if self.driver is None:
            try:
                self.driver = GraphDatabase.driver(
                    self.uri,
                    auth=(self.user, self.password),
                )
                # 验证连接
                self.driver.verify_connectivity()
            except ServiceUnavailable as e:
                msg = f"Failed to connect to Neo4j at {self.uri}: {e}"
                raise RuntimeError(msg) from e
        return self.driver

    def close(self) -> None:
        """关闭连接."""
        if self.driver is not None:
            self.driver.close()
            self.driver = None

    def execute_query(
        self,
        query: str,
        parameters: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """执行 Cypher 查询.

        Args:
            query: Cypher 查询语句
            parameters: 查询参数

        Returns:
            查询结果列表

        Raises:
            RuntimeError: 查询失败时抛出
        """
        driver = self.connect()

        try:
            with driver.session() as session:
                result = session.run(query, parameters or {})
                return [record.data() for record in result]
        except Exception as e:
            msg = f"Query execution failed: {e}"
            raise RuntimeError(msg) from e

    def execute_write(
        self,
        query: str,
        parameters: dict[str, Any] | None = None,
    ) -> Any:
        """执行写入操作.

        Args:
            query: Cypher 写入语句
            parameters: 查询参数

        Returns:
            写入结果摘要

        Raises:
            RuntimeError: 写入失败时抛出
        """
        driver = self.connect()

        try:
            with driver.session() as session:
                result = session.run(query, parameters or {})
                return result.consume()
        except Exception as e:
            msg = f"Write operation failed: {e}"
            raise RuntimeError(msg) from e
