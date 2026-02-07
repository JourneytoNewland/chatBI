"""运行数据库迁移."""

import logging
import os
from pathlib import Path

from src.database.postgres_client import postgres_client


logger = logging.getLogger(__name__)


def run_migration(script_path: str) -> bool:
    """运行数据库迁移脚本.

    Args:
        script_path: SQL脚本路径

    Returns:
        是否执行成功
    """
    if not os.path.exists(script_path):
        logger.error(f"❌ 迁移脚本不存在: {script_path}")
        return False

    logger.info(f"🔄 开始执行数据库迁移: {script_path}")

    try:
        with open(script_path, 'r', encoding='utf-8') as f:
            sql_script = f.read()

        result = postgres_client.execute_script(sql_script)

        if result:
            logger.info(f"✅ 数据库迁移执行成功: {script_path}")
        else:
            logger.error(f"❌ 数据库迁移执行失败: {script_path}")

        return result

    except Exception as e:
        logger.error(f"❌ 数据库迁移执行异常: {e}")
        return False


def run_all_migrations(migrations_dir: str = None) -> bool:
    """运行所有迁移脚本.

    Args:
        migrations_dir: 迁移脚本目录

    Returns:
        是否全部执行成功
    """
    if migrations_dir is None:
        # 默认迁移目录
        current_dir = Path(__file__).parent
        migrations_dir = current_dir / 'migrations'

    migrations_path = Path(migrations_dir)

    if not migrations_path.exists():
        logger.error(f"❌ 迁移目录不存在: {migrations_path}")
        return False

    # 获取所有迁移脚本（按文件名排序）
    migration_files = sorted(migrations_path.glob('*.sql'))

    if not migration_files:
        logger.warning(f"⚠️  未找到迁移脚本: {migrations_path}")
        return True

    logger.info("=" * 60)
    logger.info(f"开始执行数据库迁移，共 {len(migration_files)} 个脚本")
    logger.info("=" * 60)

    results = []
    for migration_file in migration_files:
        result = run_migration(str(migration_file))
        results.append(result)

        if not result:
            logger.error(f"❌ 迁移失败，停止执行: {migration_file.name}")
            return False

    success_count = sum(results)
    logger.info("=" * 60)
    logger.info(f"✅ 所有迁移脚本执行完成: {success_count}/{len(migration_files)}")
    logger.info("=" * 60)

    return all(results)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )

    # 测试数据库连接
    logger.info("测试数据库连接...")
    if not postgres_client.test_connection():
        logger.error("❌ 数据库连接失败，请检查配置")
        exit(1)

    # 运行所有迁移
    if run_all_migrations():
        logger.info("✅ 数据库迁移完成")
        exit(0)
    else:
        logger.error("❌ 数据库迁移失败")
        exit(1)
