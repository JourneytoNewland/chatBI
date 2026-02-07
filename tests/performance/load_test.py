"""性能基准测试 - 使用Locust进行压力测试."""

import time
import json
from locust import HttpUser, task, between, events
from locust.runners import MasterRunner


# 测试查询集合
TEST_QUERIES = {
    "simple": [
        {"query": "GMV"},
        {"query": "DAU"},
        {"query": "营收"},
        {"query": "转化率"},
    ],
    "time_range": [
        {"query": "最近7天GMV"},
        {"query": "本月营收总和"},
        {"query": "最近30天DAU"},
        {"query": "本周订单量"},
    ],
    "dimension": [
        {"query": "按地区GMV"},
        {"query": "按渠道统计DAU"},
        {"query": "按品类成交金额"},
        {"query": "按用户等级营收"},
    ],
    "complex": [
        {"query": "最近7天按地区统计GMV总和"},
        {"query": "本月按渠道统计DAU环比"},
        {"query": "最近30天按品类转化率"},
    ],
}


class ChatBIUser(HttpUser):
    """chatBI系统用户模拟."""

    # 用户等待时间：1-3秒
    wait_time = between(1, 3)
    
    # 目标主机（由命令行参数 --host 指定）
    host = "http://localhost:8000"

    def on_start(self):
        """用户启动时执行."""
        # 可选：登录操作
        # self.client.post("/login", json={"username": "test", "password": "test"})
        pass

    @task(3)
    def simple_query(self):
        """简单查询（权重3）- 高频操作."""
        import random
        query = random.choice(TEST_QUERIES["simple"])
        self._execute_query(query, "simple")

    @task(2)
    def time_range_query(self):
        """时间范围查询（权重2）."""
        import random
        query = random.choice(TEST_QUERIES["time_range"])
        self._execute_query(query, "time_range")

    @task(1)
    def dimension_query(self):
        """维度查询（权重1）."""
        import random
        query = random.choice(TEST_QUERIES["dimension"])
        self._execute_query(query, "dimension")

    @task(1)
    def complex_query(self):
        """复杂查询（权重1）- 低频但重要的操作."""
        import random
        query = random.choice(TEST_QUERIES["complex"])
        self._execute_query(query, "complex")

    def _execute_query(self, query_data, query_type):
        """执行查询并记录指标.

        Args:
            query_data: 查询数据
            query_type: 查询类型
        """
        start_time = time.time()
        
        with self.client.post(
            "/api/v3/query",
            json=query_data,
            catch_response=True,
            name=f"/api/v3/query [{query_type}]"
        ) as response:
            
            elapsed = (time.time() - start_time) * 1000  # 转换为毫秒
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    
                    # 验证响应格式
                    if "query" in data and "intent" in data:
                        # 记录成功
                        response.success()
                        
                        # 记录自定义指标
                        events.request.fire(
                            request_type="POST",
                            name=f"/api/v3/query [{query_type}]",
                            response_time=elapsed,
                            response_length=len(response.content),
                            context={
                                "query": query_data["query"],
                                "query_type": query_type,
                                "row_count": data.get("row_count", 0),
                                "execution_time_ms": data.get("execution_time_ms", 0),
                                "has_error": data.get("error") is not None
                            }
                        )
                    else:
                        response.failure("Invalid response format")
                        
                except json.JSONDecodeError:
                    response.failure("Invalid JSON response")
                    
            else:
                response.failure(f"HTTP {response.status_code}")


# 性能测试事件处理器
@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """测试结束时的处理."""
    if isinstance(environment.runner, MasterRunner):
        return
    
    print("\n" + "=" * 60)
    print("📊 性能测试完成")
    print("=" * 60)
    
    # 输出统计信息
    stats = environment.stats
    
    print(f"\n总请求数: {stats.total.num_requests}")
    print(f"失败率: {stats.total.fail_ratio * 100:.2f}%")
    print(f"RPS: {stats.total.total_rps:.2f}")
    print(f"\n响应时间统计:")
    print(f"  - 平均: {stats.total.avg_response_time:.2f}ms")
    print(f"  - 中位数: {stats.total.median_response_time:.2f}ms")
    print(f"  - P95: {stats.total.get_response_time_percentile(0.95):.2f}ms")
    print(f"  - P99: {stats.total.get_response_time_percentile(0.99):.2f}ms")
    
    # 按查询类型统计
    print(f"\n按查询类型统计:")
    for name, entry in stats.entries.items():
        if entry.num_requests > 0:
            print(f"  {name}:")
            print(f"    请求数: {entry.num_requests}")
            print(f"    失败率: {entry.fail_ratio * 100:.2f}%")
            print(f"    P95: {entry.get_response_time_percentile(0.95):.2f}ms")
    
    print("\n" + "=" * 60)


if __name__ == "__main__":
    """运行测试的命令行说明."""
    print("""
    🚀 chatBI 性能基准测试
    
    运行方式：
    
    1. 单机测试：
       locust -f tests/performance/load_test.py --host=http://localhost:8000
    
    2. 分布式测试（Master模式）：
       locust -f tests/performance/load_test.py --master --host=http://localhost:8000
    
    3. 分布式测试（Worker模式）：
       locust -f tests/performance/load_test.py --worker --master-host=<master-ip>
    
    4. 无头模式（不启动Web UI）：
       locust -f tests/performance/load_test.py --headless --users=100 --spawn-rate=10 --host=http://localhost:8000
    
    5. 指定运行时间：
       locust -f tests/performance/load_test.py --headless --users=100 --spawn-rate=10 -t 1m --host=http://localhost:8000
    
    参数说明：
    --users:         模拟用户数
    --spawn-rate:    每秒启动用户数
    -t, --run-time:  测试运行时长（如 1m, 5m, 1h）
    --headless:      无头模式（不启动Web UI）
    --host:          目标服务器地址
    
    Web UI访问：
    http://localhost:8089
    """)
