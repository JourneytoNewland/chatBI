"""初始化PostgreSQL测试数据."""

import logging
import random
from datetime import datetime, timedelta
from typing import List

from src.database.postgres_client import postgres_client


logger = logging.getLogger(__name__)


# ============================================
# 维度表初始化数据
# ============================================

# 地区维度数据
REGIONS = [
    ('region_001', '华东', 1, None, '中国东部地区'),
    ('region_002', '华南', 1, None, '中国南部地区'),
    ('region_003', '华北', 1, None, '中国北部地区'),
    ('region_004', '西南', 2, None, '中国西南地区'),
    ('region_005', '东北', 2, None, '中国东北地区'),
    ('region_006', '华中', 2, None, '中国中部地区'),
    ('region_007', '西北', 3, None, '中国西北地区'),
]

# 品类维度数据
CATEGORIES = [
    ('category_001', '电子产品', None, 1, '电子产品品类'),
    ('category_001_001', '手机', 'category_001', 2, '手机品类'),
    ('category_001_002', '电脑', 'category_001', 2, '电脑品类'),
    ('category_001_003', '平板', 'category_001', 2, '平板品类'),
    ('category_002', '服装鞋帽', None, 1, '服装鞋帽品类'),
    ('category_002_001', '男装', 'category_002', 2, '男装品类'),
    ('category_002_002', '女装', 'category_002', 2, '女装品类'),
    ('category_002_003', '运动鞋', 'category_002', 2, '运动鞋品类'),
    ('category_003', '家居用品', None, 1, '家居用品品类'),
    ('category_003_001', '家具', 'category_003', 2, '家具品类'),
    ('category_003_002', '厨具', 'category_003', 2, '厨具品类'),
]

# 渠道维度数据
CHANNELS = [
    ('channel_001', 'APP', 'mobile', '移动应用APP'),
    ('channel_002', '小程序', 'miniprogram', '微信小程序'),
    ('channel_003', 'H5', 'web', '移动网页H5'),
    ('channel_004', 'PC', 'web', 'PC网页端'),
]

# 用户等级维度数据
USER_LEVELS = [
    ('level_001', '普通会员', 0, 999, '基础会员权益'),
    ('level_002', '黄金会员', 1000, 4999, '黄金会员权益'),
    ('level_003', '铂金会员', 5000, 19999, '铂金会员权益'),
    ('level_004', '钻石会员', 20000, None, '钻石会员权益'),
]


def init_dimension_tables():
    """初始化维度表数据."""
    logger.info("🔄 开始初始化维度表数据...")

    try:
        # 1. 初始化地区维度
        logger.info("  ➤ 初始化地区维度表...")
        postgres_client.execute_update(
            "DELETE FROM dim_region;"
        )
        for region in REGIONS:
            postgres_client.execute_update(
                """INSERT INTO dim_region (region_id, region_name, tier, parent_region_id, description)
                   VALUES (%s, %s, %s, %s, %s)""",
                region
            )
        logger.info(f"  ✅ 地区维度初始化完成: {len(REGIONS)} 条")

        # 2. 初始化品类维度
        logger.info("  ➤ 初始化品类维度表...")
        postgres_client.execute_update(
            "DELETE FROM dim_category;"
        )
        for category in CATEGORIES:
            postgres_client.execute_update(
                """INSERT INTO dim_category (category_id, category_name, parent_category_id, level, description)
                   VALUES (%s, %s, %s, %s, %s)""",
                category
            )
        logger.info(f"  ✅ 品类维度初始化完成: {len(CATEGORIES)} 条")

        # 3. 初始化渠道维度
        logger.info("  ➤ 初始化渠道维度表...")
        postgres_client.execute_update(
            "DELETE FROM dim_channel;"
        )
        for channel in CHANNELS:
            postgres_client.execute_update(
                """INSERT INTO dim_channel (channel_id, channel_name, channel_type, description)
                   VALUES (%s, %s, %s, %s)""",
                channel
            )
        logger.info(f"  ✅ 渠道维度初始化完成: {len(CHANNELS)} 条")

        # 4. 初始化用户等级维度
        logger.info("  ➤ 初始化用户等级维度表...")
        postgres_client.execute_update(
            "DELETE FROM dim_user_level;"
        )
        for level in USER_LEVELS:
            postgres_client.execute_update(
                """INSERT INTO dim_user_level (level_id, level_name, min_points, max_points, benefits)
                   VALUES (%s, %s, %s, %s, %s)""",
                level
            )
        logger.info(f"  ✅ 用户等级维度初始化完成: {len(USER_LEVELS)} 条")

        logger.info("✅ 维度表初始化完成")
        return True

    except Exception as e:
        logger.error(f"❌ 维度表初始化失败: {e}")
        return False


def init_date_dimension(start_date: datetime, end_date: datetime):
    """初始化日期维度表.

    Args:
        start_date: 开始日期
        end_date: 结束日期
    """
    logger.info("🔄 开始初始化日期维度表...")

    try:
        # 清空现有数据
        postgres_client.execute_update("DELETE FROM dim_date;")

        # 生成日期维度数据
        date_list = []
        current_date = start_date

        while current_date <= end_date:
            date_key = int(current_date.strftime('%Y%m%d'))
            year = current_date.year
            quarter = (current_date.month - 1) // 3 + 1
            month = current_date.month
            week = current_date.isocalendar()[1]
            day = current_date.day
            day_of_week = current_date.weekday() + 1  # 1=周一, 7=周日

            day_names = ['周一', '周二', '周三', '周四', '周五', '周六', '周日']
            month_names = ['一月', '二月', '三月', '四月', '五月', '六月',
                          '七月', '八月', '九月', '十月', '十一月', '十二月']

            is_weekend = day_of_week in [6, 7]  # 周六或周日
            is_holiday = False  # 简化处理，不判断节假日
            holiday_name = None

            date_list.append((
                date_key, current_date, year, quarter, month, week, day,
                day_of_week, day_names[day_of_week - 1], month_names[month - 1],
                is_weekend, is_holiday, holiday_name
            ))

            current_date += timedelta(days=1)

        # 批量插入
        postgres_client.execute_batch(
            """INSERT INTO dim_date
               (date_key, date, year, quarter, month, week, day,
                day_of_week, day_name, month_name, is_weekend, is_holiday, holiday_name)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
            date_list
        )

        logger.info(f"✅ 日期维度初始化完成: {len(date_list)} 天")
        return True

    except Exception as e:
        logger.error(f"❌ 日期维度初始化失败: {e}")
        return False


def generate_fact_orders_data(days: int = 30):
    """生成订单事实表测试数据.

    Args:
        days: 生成天数
    """
    logger.info(f"🔄 开始生成订单事实表测试数据（最近{days}天）...")

    try:
        # 清空现有数据
        postgres_client.execute_update("DELETE FROM fact_orders;")

        # 获取维度键值映射
        regions = postgres_client.execute_query("SELECT region_key FROM dim_region;")
        categories = postgres_client.execute_query("SELECT category_key FROM dim_category;")
        channels = postgres_client.execute_query("SELECT channel_key FROM dim_channel;")
        user_levels = postgres_client.execute_query("SELECT level_key FROM dim_user_level;")
        dates = postgres_client.execute_query(
            "SELECT date_key FROM dim_date ORDER BY date DESC LIMIT %s;",
            (days,)
        )

        # 生成测试数据
        data_list = []
        for date_row in dates:
            date_key = date_row['date_key']

            # 每天生成 100-500 条聚合记录
            for _ in range(random.randint(100, 500)):
                order_count = random.randint(1, 1000)
                total_order_amount = random.uniform(10000, 500000)
                total_discount = random.uniform(0, total_order_amount * 0.2)
                gmv = total_order_amount - total_discount

                data_list.append((
                    date_key,
                    random.choice(regions)['region_key'],
                    random.choice(categories)['category_key'],
                    random.choice(channels)['channel_key'],
                    random.choice(user_levels)['level_key'],
                    order_count,
                    round(total_order_amount, 2),
                    round(total_discount, 2),
                    round(gmv, 2)
                ))

        # 批量插入
        postgres_client.execute_batch(
            """INSERT INTO fact_orders
               (date_key, region_key, category_key, channel_key, user_level_key,
                order_count, total_order_amount, total_discount, gmv)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)""",
            data_list
        )

        logger.info(f"✅ 订单事实表数据生成完成: {len(data_list)} 条记录")
        return True

    except Exception as e:
        logger.error(f"❌ 订单事实表数据生成失败: {e}")
        return False


def generate_fact_user_activity_data(days: int = 30):
    """生成用户活跃度事实表测试数据.

    Args:
        days: 生成天数
    """
    logger.info(f"🔄 开始生成用户活跃度事实表测试数据（最近{days}天）...")

    try:
        # 清空现有数据
        postgres_client.execute_update("DELETE FROM fact_user_activity;")

        # 获取维度键值映射
        regions = postgres_client.execute_query("SELECT region_key FROM dim_region;")
        channels = postgres_client.execute_query("SELECT channel_key FROM dim_channel;")
        user_levels = postgres_client.execute_query("SELECT level_key FROM dim_user_level;")
        dates = postgres_client.execute_query(
            "SELECT date_key FROM dim_date ORDER BY date DESC LIMIT %s;",
            (days,)
        )

        # 生成测试数据
        data_list = []
        for date_row in dates:
            date_key = date_row['date_key']

            # 每天生成 50-200 条聚合记录
            for _ in range(random.randint(50, 200)):
                dau = random.randint(1000, 100000)
                mau = random.randint(dau, int(dau * 3))
                new_users = random.randint(100, 10000)
                returning_users = dau - new_users
                session_count = random.randint(dau, dau * 5)
                avg_session_duration = random.uniform(60, 600)  # 1-10分钟
                page_views = random.randint(session_count * 2, session_count * 10)

                data_list.append((
                    date_key,
                    random.choice(regions)['region_key'],
                    random.choice(channels)['channel_key'],
                    random.choice(user_levels)['level_key'],
                    dau,
                    mau,
                    new_users,
                    returning_users,
                    session_count,
                    round(avg_session_duration, 2),
                    page_views,
                    round(random.uniform(0.3, 0.6), 4),  # retention_day1
                    round(random.uniform(0.2, 0.4), 4),  # retention_day7
                    round(random.uniform(0.1, 0.3), 4),  # retention_day30
                ))

        # 批量插入
        postgres_client.execute_batch(
            """INSERT INTO fact_user_activity
               (date_key, region_key, channel_key, user_level_key,
                dau, mau, new_users, returning_users, session_count,
                avg_session_duration, page_views, retention_day1, retention_day7, retention_day30)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
            data_list
        )

        logger.info(f"✅ 用户活跃度事实表数据生成完成: {len(data_list)} 条记录")
        return True

    except Exception as e:
        logger.error(f"❌ 用户活跃度事实表数据生成失败: {e}")
        return False


def generate_fact_traffic_data(days: int = 30):
    """生成流量事实表测试数据.

    Args:
        days: 生成天数
    """
    logger.info(f"🔄 开始生成流量事实表测试数据（最近{days}天）...")

    try:
        postgres_client.execute_update("DELETE FROM fact_traffic;")

        regions = postgres_client.execute_query("SELECT region_key FROM dim_region;")
        channels = postgres_client.execute_query("SELECT channel_key FROM dim_channel;")
        dates = postgres_client.execute_query(
            "SELECT date_key FROM dim_date ORDER BY date DESC LIMIT %s;",
            (days,)
        )

        data_list = []
        for date_row in dates:
            date_key = date_row['date_key']

            for _ in range(random.randint(50, 200)):
                visitors = random.randint(10000, 500000)
                page_views = random.randint(visitors * 2, visitors * 10)
                unique_visitors = random.randint(int(visitors * 0.7), visitors)
                add_to_cart_count = random.randint(int(visitors * 0.1), int(visitors * 0.3))
                checkout_count = random.randint(int(add_to_cart_count * 0.3), int(add_to_cart_count * 0.6))
                order_count = random.randint(int(checkout_count * 0.5), int(checkout_count * 0.8))

                data_list.append((
                    date_key,
                    random.choice(regions)['region_key'],
                    random.choice(channels)['channel_key'],
                    visitors,
                    page_views,
                    unique_visitors,
                    add_to_cart_count,
                    checkout_count,
                    order_count
                ))

        postgres_client.execute_batch(
            """INSERT INTO fact_traffic
               (date_key, region_key, channel_key,
                visitors, page_views, unique_visitors,
                add_to_cart_count, checkout_count, order_count)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)""",
            data_list
        )

        logger.info(f"✅ 流量事实表数据生成完成: {len(data_list)} 条记录")
        return True

    except Exception as e:
        logger.error(f"❌ 流量事实表数据生成失败: {e}")
        return False


def generate_fact_revenue_data(days: int = 30):
    """生成收入事实表测试数据.

    Args:
        days: 生成天数
    """
    logger.info(f"🔄 开始生成收入事实表测试数据（最近{days}天）...")

    try:
        postgres_client.execute_update("DELETE FROM fact_revenue;")

        regions = postgres_client.execute_query("SELECT region_key FROM dim_region;")
        user_levels = postgres_client.execute_query("SELECT level_key FROM dim_user_level;")
        dates = postgres_client.execute_query(
            "SELECT date_key FROM dim_date ORDER BY date DESC LIMIT %s;",
            (days,)
        )

        data_list = []
        for date_row in dates:
            date_key = date_row['date_key']

            for _ in range(random.randint(30, 100)):
                total_users = random.randint(10000, 100000)
                paying_users = random.randint(int(total_users * 0.1), int(total_users * 0.3))
                total_revenue = random.uniform(100000, 5000000)

                data_list.append((
                    date_key,
                    random.choice(regions)['region_key'],
                    random.choice(user_levels)['level_key'],
                    round(total_revenue, 2),
                    total_users,
                    paying_users,
                    round(random.uniform(100, 1000), 2),  # ltv_30d
                    round(random.uniform(500, 3000), 2),  # ltv_90d
                    round(random.uniform(1000, 10000), 2),  # ltv_365d
                ))

        postgres_client.execute_batch(
            """INSERT INTO fact_revenue
               (date_key, region_key, user_level_key,
                total_revenue, total_users, paying_users, ltv_30d, ltv_90d, ltv_365d)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)""",
            data_list
        )

        logger.info(f"✅ 收入事实表数据生成完成: {len(data_list)} 条记录")
        return True

    except Exception as e:
        logger.error(f"❌ 收入事实表数据生成失败: {e}")
        return False


def generate_fact_finance_data(days: int = 30):
    """生成财务事实表测试数据.

    Args:
        days: 生成天数
    """
    logger.info(f"🔄 开始生成财务事实表测试数据（最近{days}天）...")

    try:
        postgres_client.execute_update("DELETE FROM fact_finance;")

        regions = postgres_client.execute_query("SELECT region_key FROM dim_region;")
        dates = postgres_client.execute_query(
            "SELECT date_key FROM dim_date ORDER BY date DESC LIMIT %s;",
            (days,)
        )

        data_list = []
        for date_row in dates:
            date_key = date_row['date_key']

            for _ in range(len(regions)):
                revenue = random.uniform(500000, 10000000)
                cost_of_goods_sold = random.uniform(revenue * 0.3, revenue * 0.5)
                operating_expense = random.uniform(revenue * 0.2, revenue * 0.4)
                marketing_cost = random.uniform(revenue * 0.1, revenue * 0.3)

                data_list.append((
                    date_key,
                    random.choice(regions)['region_key'],
                    round(revenue, 2),
                    round(cost_of_goods_sold, 2),
                    round(operating_expense, 2),
                    round(marketing_cost, 2)
                ))

        postgres_client.execute_batch(
            """INSERT INTO fact_finance
               (date_key, region_key, revenue, cost_of_goods_sold, operating_expense, marketing_cost)
               VALUES (%s, %s, %s, %s, %s, %s)""",
            data_list
        )

        logger.info(f"✅ 财务事实表数据生成完成: {len(data_list)} 条记录")
        return True

    except Exception as e:
        logger.error(f"❌ 财务事实表数据生成失败: {e}")
        return False


def init_all_test_data(days: int = 30):
    """初始化所有测试数据.

    Args:
        days: 生成天数
    """
    logger.info("=" * 60)
    logger.info("开始初始化PostgreSQL测试数据")
    logger.info("=" * 60)

    # 1. 初始化维度表
    if not init_dimension_tables():
        logger.error("❌ 维度表初始化失败，终止流程")
        return False

    # 2. 初始化日期维度（最近1年）
    end_date = datetime.now()
    start_date = end_date - timedelta(days=365)
    if not init_date_dimension(start_date, end_date):
        logger.error("❌ 日期维度初始化失败，终止流程")
        return False

    # 3. 生成事实表测试数据
    results = []
    results.append(generate_fact_orders_data(days))
    results.append(generate_fact_user_activity_data(days))
    results.append(generate_fact_traffic_data(days))
    results.append(generate_fact_revenue_data(days))
    results.append(generate_fact_finance_data(days))

    if all(results):
        logger.info("=" * 60)
        logger.info("✅ 所有测试数据初始化完成")
        logger.info("=" * 60)
        return True
    else:
        logger.error("❌ 部分事实表数据初始化失败")
        return False


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # 测试数据库连接
    if not postgres_client.test_connection():
        logger.error("❌ 数据库连接失败，请检查配置")
        exit(1)

    # 初始化测试数据（最近30天）
    init_all_test_data(days=30)
