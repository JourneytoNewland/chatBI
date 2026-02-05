"""PostgreSQL 客户端封装."""

import logging
from contextlib import contextmanager
from typing import Any, Dict, List, Optional

import psycopg2
from psycopg2 import pool
from psycopg2.extras import RealDictCursor
from psycopg2.errors import Error as PostgresError

from src.config import settings

logger = logging.getLogger(__name__)


class PostgreSQLClient:
    """PostgreSQL 客户端封装.

    提供连接池管理、查询执行、错误处理等功能。
    参考Neo4jClient的实现模式。

    Attributes:
        host: PostgreSQL主机地址
        port: PostgreSQL端口
        database: 数据库名称
        user: 用户名
        password: 密码
    """

    def __init__(
        self,
        host: Optional[str] = None,
        port: Optional[int] = None,
        database: Optional[str] = None,
        user: Optional[str] = None,
        password: Optional[str] = None,
    ) -> None:
        """初始化 PostgreSQL 客户端.

        Args:
            host: 主机地址，默认从环境变量读取
            port: 端口，默认从环境变量读取
            database: 数据库名，默认从环境变量读取
            user: 用户名，默认从环境变量读取
            password: 密码，默认从环境变量读取
        """
        config = settings.postgres

        self.host = host or config.host
        self.port = port or config.port
        self.database = database or config.database
        self.user = user or config.user
        self.password = password or config.password

        self._pool: Optional[pool.SimpleConnectionPool] = None
        self._is_connected = False

    def connect(self) -> pool.SimpleConnectionPool:
        """建立连接池.

        Returns:
            连接池实例

        Raises:
            RuntimeError: 连接失败时抛出
        """
        if self._pool is None:
            try:
                self._pool = pool.SimpleConnectionPool(
                    minconn=1,
                    maxconn=settings.postgres.pool_size,
                    host=self.host,
                    port=self.port,
                    database=self.database,
                    user=self.user,
                    password=self.password,
                )
                self._is_connected = True
                logger.info(f"Connected to PostgreSQL at {self.host}:{self.port}")
            except PostgresError as e:
                msg = f"Failed to connect to PostgreSQL: {e}"
                logger.error(msg)
                raise RuntimeError(msg) from e

        return self._pool

    def close(self) -> None:
        """关闭所有连接."""
        if self._pool is not None:
            self._pool.closeall()
            self._pool = None
            self._is_connected = False
            logger.info("PostgreSQL connection pool closed")

    def is_connected(self) -> bool:
        """检查连接状态.

        Returns:
            连接是否正常
        """
        return self._is_connected and self._pool is not None

    @contextmanager
    def get_connection(self):
        """获取数据库连接上下文管理器.

        Yields:
            数据库连接对象
        """
        pool = self.connect()
        conn = pool.getconn()
        try:
            yield conn
        finally:
            pool.putconn(conn)

    @contextmanager
    def get_cursor(self):
        """获取数据库游标上下文管理器.

        Yields:
            游标对象(RealDictCursor，返回字典格式)
        """
        with self.get_connection() as conn:
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            try:
                yield cursor
                conn.commit()
            except Exception:
                conn.rollback()
                raise
            finally:
                cursor.close()

    def execute_query(
        self,
        query: str,
        parameters: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """执行查询语句.

        Args:
            query: SQL 查询语句
            parameters: 查询参数(参数化查询，防止SQL注入)

        Returns:
            查询结果列表

        Raises:
            RuntimeError: 查询失败时抛出
        """
        try:
            with self.get_cursor() as cursor:
                cursor.execute(query, parameters or {})
                return cursor.fetchall()
        except PostgresError as e:
            msg = f"Query execution failed: {e}\nQuery: {query}"
            logger.error(msg)
            raise RuntimeError(msg) from e

    def execute_write(
        self,
        query: str,
        parameters: Optional[Dict[str, Any]] = None,
    ) -> int:
        """执行写入操作.

        Args:
            query: SQL 写入语句
            parameters: 写入参数

        Returns:
            影响的行数

        Raises:
            RuntimeError: 写入失败时抛出
        """
        try:
            with self.get_cursor() as cursor:
                cursor.execute(query, parameters or {})
                return cursor.rowcount
        except PostgresError as e:
            msg = f"Write operation failed: {e}\nQuery: {query}"
            logger.error(msg)
            raise RuntimeError(msg) from e

    def execute_batch(
        self,
        query: str,
        parameters_list: List[Dict[str, Any]],
    ) -> int:
        """批量执行写入操作.

        Args:
            query: SQL 写入语句
            parameters_list: 写入参数列表

        Returns:
            总影响行数

        Raises:
            RuntimeError: 批量执行失败时抛出
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor(cursor_factory=RealDictCursor)
                try:
                    total_rows = 0
                    for params in parameters_list:
                        cursor.execute(query, params)
                        total_rows += cursor.rowcount
                    conn.commit()
                    return total_rows
                except Exception:
                    conn.rollback()
                    raise
                finally:
                    cursor.close()
        except PostgresError as e:
            msg = f"Batch execution failed: {e}"
            logger.error(msg)
            raise RuntimeError(msg) from e

    def health_check(self) -> bool:
        """健康检查.

        Returns:
            连接是否正常
        """
        try:
            result = self.execute_query("SELECT 1")
            return len(result) == 1 and result[0].get("?column?", 1) == 1
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return False


# 测试
if __name__ == "__main__":
    print("\n🧪 测试PostgreSQL客户端")
    print("=" * 60)

    # 创建客户端
    client = PostgreSQLClient()

    try:
        # 测试连接
        print("\n1. 测试连接...")
        if client.is_connected():
            print("   ✅ 连接成功")
        else:
            print("   ❌ 连接失败")

        # 测试健康检查
        print("\n2. 测试健康检查...")
        if client.health_check():
            print("   ✅ 健康检查通过")
        else:
            print("   ❌ 健康检查失败")

        # 测试查询
        print("\n3. 测试查询...")
        result = client.execute_query("SELECT 1 AS test, NOW() AS current_time")
        print(f"   查询结果: {result}")

        print("\n" + "=" * 60)
        print("✅ 所有测试通过")

    except Exception as e:
        print(f"\n❌ 测试失败: {e}")

    finally:
        client.close()
        print("👋 连接已关闭")
