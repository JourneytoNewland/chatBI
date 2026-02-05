"""测试数据初始化脚本.

为PostgreSQL数据库生成测试数据，包括：
- 维度表数据（已在Schema中初始化）
- 事实表数据（订单、用户活动、流量、营收）
"""

import logging
import random
from datetime import datetime, timedelta

from src.database.postgres_client import PostgreSQLClient
from src.config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TestDataInitializer:
    """测试数据初始化器."""

    def __init__(self):
        """初始化."""
        self.postgres = PostgreSQLClient()

    def init_all_data(self, days: int = 30):
        """初始化所有测试数据.

        Args:
            days: 生成数据的天数（默认30天）
        """
        logger.info(f"开始初始化测试数据（最近{days}天）")

        try:
            # 1. 初始化订单数据
            self._init_order_data(days)
            logger.info("✅ 订单数据初始化完成")

            # 2. 初始化用户活动数据
            self._init_user_activity_data(days)
            logger.info("✅ 用户活动数据初始化完成")

            # 3. 初始化流量数据
            self._init_traffic_data(days)
            logger.info("✅ 流量数据初始化完成")

            # 4. 初始化营收数据
            self._init_revenue_data(days)
            logger.info("✅ 营收数据初始化完成")

            # 5. 初始化财务数据
            self._init_finance_data(days)
            logger.info("✅ 财务数据初始化完成")

            logger.info("\n" + "=" * 60)
            logger.info("所有测试数据初始化完成！")
            logger.info("=" * 60)

        except Exception as e:
            logger.error(f"初始化失败: {e}")
            raise

    def _init_order_data(self, days: int):
        """初始化订单事实表数据.

        生成约10,000条订单记录（约330条/天）
        """
        logger.info("正在生成订单数据...")

        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)

        batch_size = 1000
        batch = []
        order_id = 1000000

        current_date = start_date
        while current_date <= end_date:
            # 每天生成约330条订单
            for _ in range(330):
                order_id += 1

                # 随机生成订单数据
                order_amount = random.uniform(50, 5000)
                # 周末和节假日订单量增加
                if current_date.weekday() >= 5:
                    order_amount *= random.uniform(1.1, 1.3)

                batch.append({
                    "order_id": order_id,
                    "date_id": current_date.strftime("%Y-%m-%d"),
                    "region_id": random.randint(1, 5),  # 5个地区
                    "category_id": random.randint(1, 6),  # 6个品类
                    "channel_id": random.randint(1, 4),  # 4个渠道
                    "user_level_id": random.randint(1, 4),  # 4个用户等级
                    "order_amount": round(order_amount, 2),
                    "quantity": random.randint(1, 5),
                    "is_paid": random.choice([True, True, True, False]),  # 75%支付率
                    "is_refunded": random.choice([True, False, False, False, False])  # 20%退款率
                })

                # 批量插入
                if len(batch) >= batch_size:
                    self._batch_insert_orders(batch)
                    batch = []

            current_date += timedelta(days=1)

        # 插入剩余数据
        if batch:
            self._batch_insert_orders(batch)

    def _batch_insert_orders(self, batch: list):
        """批量插入订单数据."""
        sql = """
            INSERT INTO fact_orders (
                order_id, date_id, region_id, category_id, channel_id,
                user_level_id, order_amount, quantity, is_paid, is_refunded
            ) VALUES (
                %(order_id)s, %(date_id)s, %(region_id)s, %(category_id)s,
                %(channel_id)s, %(user_level_id)s, %(order_amount)s,
                %(quantity)s, %(is_paid)s, %(is_refunded)s
            )
        """
        self.postgres.execute_batch(sql, batch)

    def _init_user_activity_data(self, days: int):
        """初始化用户活动事实表数据.

        生成约50,000条记录（约1,600条/天）
        """
        logger.info("正在生成用户活动数据...")

        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)

        batch_size = 1000
        batch = []
        activity_id = 2000000

        current_date = start_date
        while current_date <= end_date:
            # 每天生成约1,600条活动记录
            for _ in range(1600):
                activity_id += 1

                is_new_user = random.choice([True] * 10 + [False] * 90)  # 10%新用户

                batch.append({
                    "activity_id": activity_id,
                    "date_id": current_date.strftime("%Y-%m-%d"),
                    "region_id": random.randint(1, 5),
                    "channel_id": random.randint(1, 4),
                    "user_level_id": random.randint(1, 4),
                    "user_id": random.randint(10000, 99999),
                    "is_new_user": is_new_user,
                    "activity_count": random.randint(1, 10),
                    "session_duration_seconds": random.randint(30, 3600),
                    "page_views": random.randint(1, 50)
                })

                if len(batch) >= batch_size:
                    self._batch_insert_user_activities(batch)
                    batch = []

            current_date += timedelta(days=1)

        if batch:
            self._batch_insert_user_activities(batch)

    def _batch_insert_user_activities(self, batch: list):
        """批量插入用户活动数据."""
        sql = """
            INSERT INTO fact_user_activity (
                activity_id, date_id, region_id, channel_id, user_level_id,
                user_id, is_new_user, activity_count, session_duration_seconds, page_views
            ) VALUES (
                %(activity_id)s, %(date_id)s, %(region_id)s, %(channel_id)s,
                %(user_level_id)s, %(user_id)s, %(is_new_user)s,
                %(activity_count)s, %(session_duration_seconds)s, %(page_views)s
            )
        """
        self.postgres.execute_batch(sql, batch)

    def _init_traffic_data(self, days: int):
        """初始化流量事实表数据.

        生成约30,000条记录（约1,000条/天）
        """
        logger.info("正在生成流量数据...")

        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)

        batch_size = 1000
        batch = []
        traffic_id = 3000000

        current_date = start_date
        while current_date <= end_date:
            # 每天生成约1,000条流量记录
            for _ in range(1000):
                traffic_id += 1

                visitors = random.randint(100, 1000)
                batch.append({
                    "traffic_id": traffic_id,
                    "date_id": current_date.strftime("%Y-%m-%d"),
                    "region_id": random.randint(1, 5),
                    "category_id": random.randint(1, 6),
                    "channel_id": random.randint(1, 4),
                    "visitors": visitors,
                    "visits": random.randint(visitors, visitors * 2),
                    "page_views": random.randint(visitors * 2, visitors * 10),
                    "unique_visitors": random.randint(int(visitors * 0.8), visitors),
                    "cart_additions": random.randint(0, int(visitors * 0.3)),
                    "orders": random.randint(0, int(visitors * 0.1)),
                    "paid_orders": random.randint(0, int(visitors * 0.08))
                })

                if len(batch) >= batch_size:
                    self._batch_insert_traffic(batch)
                    batch = []

            current_date += timedelta(days=1)

        if batch:
            self._batch_insert_traffic(batch)

    def _batch_insert_traffic(self, batch: list):
        """批量插入流量数据."""
        sql = """
            INSERT INTO fact_traffic (
                traffic_id, date_id, region_id, category_id, channel_id,
                visitors, visits, page_views, unique_visitors,
                cart_additions, orders, paid_orders
            ) VALUES (
                %(traffic_id)s, %(date_id)s, %(region_id)s, %(category_id)s,
                %(channel_id)s, %(visitors)s, %(visits)s, %(page_views)s,
                %(unique_visitors)s, %(cart_additions)s, %(orders)s, %(paid_orders)s
            )
        """
        self.postgres.execute_batch(sql, batch)

    def _init_revenue_data(self, days: int):
        """初始化营收事实表数据.

        生成约1,000条记录（约35条/天，按地区+渠道分组）
        """
        logger.info("正在生成营收数据...")

        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)

        batch_size = 500
        batch = []
        revenue_id = 4000000

        current_date = start_date
        while current_date <= end_date:
            # 每天按地区+渠道组合生成数据（5地区 * 4渠道 = 20条/天）
            for region_id in range(1, 6):
                for channel_id in range(1, 5):
                    for user_level_id in range(1, 5):
                        revenue_id += 1

                        revenue = random.uniform(10000, 100000)
                        cost = revenue * random.uniform(0.3, 0.7)

                        batch.append({
                            "revenue_id": revenue_id,
                            "date_id": current_date.strftime("%Y-%m-%d"),
                            "region_id": region_id,
                            "channel_id": channel_id,
                            "user_level_id": user_level_id,
                            "revenue": round(revenue, 2),
                            "cost": round(cost, 2)
                        })

                        if len(batch) >= batch_size:
                            self._batch_insert_revenue(batch)
                            batch = []

            current_date += timedelta(days=1)

        if batch:
            self._batch_insert_revenue(batch)

    def _batch_insert_revenue(self, batch: list):
        """批量插入营收数据."""
        sql = """
            INSERT INTO fact_revenue (
                revenue_id, date_id, region_id, channel_id, user_level_id,
                revenue, cost
            ) VALUES (
                %(revenue_id)s, %(date_id)s, %(region_id)s, %(channel_id)s,
                %(user_level_id)s, %(revenue)s, %(cost)s
            )
        """
        self.postgres.execute_batch(sql, batch)

    def _init_finance_data(self, days: int):
        """初始化财务事实表数据.

        生成约2,000条记录（约70条/天，按地区+业务线组合）
        """
        logger.info("正在生成财务数据...")

        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)

        batch_size = 500
        batch = []
        finance_id = 5000000

        business_lines = ["电商", "SaaS", "广告", "咨询", "其他"]
        products = ["产品A", "产品B", "产品C", "服务D", "服务E"]

        current_date = start_date
        while current_date <= end_date:
            # 每天按地区+业务线+产品组合生成数据
            for region_id in range(1, 6):
                for business_line in business_lines:
                    for product in products:
                        finance_id += 1

                        revenue = random.uniform(5000, 50000)
                        cost = revenue * random.uniform(0.4, 0.8)

                        batch.append({
                            "finance_id": finance_id,
                            "date_id": current_date.strftime("%Y-%m-%d"),
                            "region_id": region_id,
                            "business_line": business_line,
                            "product_name": product,
                            "revenue": round(revenue, 2),
                            "cost": round(cost, 2)
                        })

                        if len(batch) >= batch_size:
                            self._batch_insert_finance(batch)
                            batch = []

            current_date += timedelta(days=1)

        if batch:
            self._batch_insert_finance(batch)

    def _batch_insert_finance(self, batch: list):
        """批量插入财务数据."""
        sql = """
            INSERT INTO fact_finance (
                finance_id, date_id, region_id, business_line, product_name,
                revenue, cost
            ) VALUES (
                %(finance_id)s, %(date_id)s, %(region_id)s, %(business_line)s,
                %(product_name)s, %(revenue)s, %(cost)s
            )
        """
        self.postgres.execute_batch(sql, batch)


def main():
    """主函数."""
    print("\n🚀 测试数据初始化")
    print("=" * 60)

    initializer = TestDataInitializer()

    try:
        # 生成30天的测试数据
        initializer.init_all_data(days=30)

        print("\n✅ 数据初始化完成！")
        print(f"   订单事实表: ~10,000条")
        print(f"   用户活动事实表: ~50,000条")
        print(f"   流量事实表: ~30,000条")
        print(f"   营收事实表: ~1,000条")
        print(f"   财务事实表: ~2,000条")
        print("\n现在可以开始测试智能问数系统！")
        print("=" * 60 + "\n")

    except Exception as e:
        print(f"\n❌ 初始化失败: {e}\n")
        raise

    finally:
        initializer.postgres.close()


if __name__ == "__main__":
    main()
