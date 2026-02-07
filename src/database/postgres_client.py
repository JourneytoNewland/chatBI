"""PostgreSQL数据库客户端."""

from typing import Any, Dict, List, Optional, Tuple
from contextlib import contextmanager
import logging

import psycopg2
from psycopg2 import pool
from psycopg2.extras import RealDictCursor, NamedTupleCursor

from src.config import settings


logger = logging.getLogger(__name__)


class PostgreSQLClient:
    """PostgreSQL客户端管理类."""

    _instance: Optional['PostgreSQLClient'] = None
    _pool: Optional[pool.SimpleConnectionPool] = None

    def __new__(cls) -> 'PostgreSQLClient':
        """单例模式."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        """初始化PostgreSQL连接池."""
        if self._pool is None:
            self._initialize_pool()

    def _initialize_pool(self):
        """初始化连接池."""
        try:
            # 从配置读取数据库连接信息
            db_config = getattr(settings, 'postgres', None)

            if db_config is None:
                logger.warning("PostgreSQL配置未找到，使用默认配置")
                # 默认配置
                db_config = {
                    'host': 'localhost',
                    'port': 5432,
                    'database': 'chatbi',
                    'user': 'postgres',
                    'password': 'postgres'
                }

            self._pool = pool.SimpleConnectionPool(
                minconn=1,
                maxconn=10,
                host=db_config.get('host', 'localhost'),
                port=db_config.get('port', 5432),
                database=db_config.get('database', 'chatbi'),
                user=db_config.get('user', 'postgres'),
                password=db_config.get('password', 'postgres')
            )

            logger.info(f"✅ PostgreSQL连接池已创建: {db_config.get('database')}")

        except Exception as e:
            logger.error(f"❌ PostgreSQL连接池创建失败: {e}")
            self._pool = None

    @contextmanager
    def get_connection(self, autocommit: bool = False):
        """获取数据库连接（上下文管理器）.

        Args:
            autocommit: 是否自动提交

        Yields:
            数据库连接对象

        Raises:
            ConnectionError: 连接失败时抛出
        """
        if self._pool is None:
            raise ConnectionError("PostgreSQL连接池未初始化")

        conn = None
        try:
            conn = self._pool.getconn()
            conn.autocommit = autocommit
            yield conn
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"数据库操作失败: {e}")
            raise
        finally:
            if conn:
                self._pool.putconn(conn)

    def execute_query(
        self,
        query: str,
        params: Optional[Tuple] = None,
        fetch: str = 'all',
        dict_cursor: bool = True
    ) -> Any:
        """执行SQL查询.

        Args:
            query: SQL查询语句
            params: 查询参数
            fetch: 返回类型 ('all', 'one', 'none')
            dict_cursor: 是否使用字典游标（返回字段名）

        Returns:
            查询结果

        Raises:
            Exception: 查询失败时抛出
        """
        cursor_type = RealDictCursor if dict_cursor else NamedTupleCursor

        with self.get_connection() as conn:
            with conn.cursor(cursor_factory=cursor_type) as cursor:
                cursor.execute(query, params)

                if fetch == 'all':
                    return cursor.fetchall()
                elif fetch == 'one':
                    return cursor.fetchone()
                else:
                    return None

    def execute_update(
        self,
        query: str,
        params: Optional[Tuple] = None,
        auto_commit: bool = True
    ) -> int:
        """执行更新操作（INSERT/UPDATE/DELETE）.

        Args:
            query: SQL语句
            params: 参数
            auto_commit: 是否自动提交

        Returns:
            影响的行数
        """
        with self.get_connection(autocommit=auto_commit) as conn:
            with conn.cursor() as cursor:
                cursor.execute(query, params)
                return cursor.rowcount

    def execute_batch(
        self,
        query: str,
        params_list: List[Tuple],
        auto_commit: bool = True
    ) -> int:
        """批量执行SQL.

        Args:
            query: SQL语句
            params_list: 参数列表
            auto_commit: 是否自动提交

        Returns:
            总影响行数
        """
        with self.get_connection(autocommit=auto_commit) as conn:
            with conn.cursor() as cursor:
                total_rows = 0
                for params in params_list:
                    cursor.execute(query, params)
                    total_rows += cursor.rowcount
                return total_rows

    def execute_script(self, script: str) -> bool:
        """执行SQL脚本（多语句）.

        Args:
            script: SQL脚本内容

        Returns:
            是否执行成功
        """
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(script)
                    conn.commit()
                    logger.info("✅ SQL脚本执行成功")
                    return True
        except Exception as e:
            logger.error(f"❌ SQL脚本执行失败: {e}")
            return False

    def test_connection(self) -> bool:
        """测试数据库连接.

        Returns:
            连接是否成功
        """
        try:
            result = self.execute_query("SELECT version()", fetch='one', dict_cursor=False)
            if result:
                logger.info(f"✅ PostgreSQL连接成功: {result[0]}")
                return True
            return False
        except Exception as e:
            logger.error(f"❌ PostgreSQL连接失败: {e}")
            return False

    def get_table_info(self, table_name: str) -> List[Dict[str, Any]]:
        """获取表结构信息.

        Args:
            table_name: 表名

        Returns:
            列信息列表
        """
        query = """
            SELECT
                column_name,
                data_type,
                is_nullable,
                column_default,
                character_maximum_length
            FROM information_schema.columns
            WHERE table_name = %s
            ORDER BY ordinal_position;
        """
        return self.execute_query(query, (table_name,))

    def table_exists(self, table_name: str) -> bool:
        """检查表是否存在.

        Args:
            table_name: 表名

        Returns:
            表是否存在
        """
        query = """
            SELECT EXISTS (
                SELECT FROM information_schema.tables
                WHERE table_name = %s
            );
        """
        result = self.execute_query(query, (table_name,), fetch='one')
        return result['exists'] if result else False

    def close_all(self):
        """关闭所有连接."""
        if self._pool:
            self._pool.closeall()
            logger.info("✅ PostgreSQL连接池已关闭")


# 全局单例
postgres_client = PostgreSQLClient()


if __name__ == "__main__":
    # 测试连接
    logging.basicConfig(level=logging.INFO)
    client = PostgreSQLClient()

    if client.test_connection():
        print("✅ 数据库连接测试成功")

        # 检查表是否存在
        tables = ['dim_date', 'dim_region', 'fact_orders', 'fact_user_activity']
        for table in tables:
            exists = client.table_exists(table)
            print(f"{'✅' if exists else '❌'} 表 {table}: {'存在' if exists else '不存在'}")
    else:
        print("❌ 数据库连接测试失败")
