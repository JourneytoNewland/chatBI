"""性能基准测试 - 建立性能baseline."""

import time
import statistics
from typing import Dict, List, Any
from dataclasses import dataclass
import json


@dataclass
class BenchmarkResult:
    """基准测试结果."""
    
    name: str
    total_runs: int
    successful_runs: int
    failed_runs: int
    
    # 延迟统计（毫秒）
    p50: float
    p75: float
    p95: float
    p99: float
    avg: float
    min: float
    max: float
    
    # 吞吐量
    rps: float  # Requests Per Second
    
    # 错误信息
    errors: List[str]
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典."""
        return {
            "name": self.name,
            "total_runs": self.total_runs,
            "successful_runs": self.successful_runs,
            "failed_runs": self.failed_runs,
            "success_rate": f"{(self.successful_runs / self.total_runs * 100):.2f}%" if self.total_runs > 0 else "N/A",
            "latency_ms": {
                "p50": f"{self.p50:.2f}",
                "p75": f"{self.75:.2f}",
                "p95": f"{self.p95:.2f}",
                "p99": f"{self.p99:.2f}",
                "avg": f"{self.avg:.2f}",
                "min": f"{self.min:.2f}",
                "max": f"{self.max:.2f}",
            },
            "throughput_rps": f"{self.rps:.2f}",
            "errors": self.errors[:5]  # 只保留前5个错误
        }


class PerformanceBenchmark:
    """性能基准测试工具."""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        """初始化基准测试工具.
        
        Args:
            base_url: API基础URL
        """
        self.base_url = base_url
        self.session = None
        
    def _get_session(self):
        """获取HTTP会话."""
        if self.session is None:
            import requests
            self.session = requests.Session()
        return self.session
    
    def run_benchmark(
        self,
        query: str,
        warmup_runs: int = 5,
        benchmark_runs: int = 50,
        timeout: int = 30
    ) -> BenchmarkResult:
        """运行单个查询的基准测试.
        
        Args:
            query: 测试查询
            warmup_runs: 预热次数
            benchmark_runs: 基准测试次数
            timeout: 超时时间（秒）
        
        Returns:
            BenchmarkResult: 基准测试结果
        """
        print(f"\n🔄 运行基准测试: {query}")
        print(f"   预热: {warmup_runs} 次")
        print(f"   基准测试: {benchmark_runs} 次")
        
        session = self._get_session()
        latencies = []
        errors = []
        
        # 1. 预热（避免冷启动影响）
        print("   ⏳ 预热中...")
        for i in range(warmup_runs):
            try:
                start = time.time()
                response = session.post(
                    f"{self.base_url}/api/v3/query",
                    json={"query": query},
                    timeout=timeout
                )
                elapsed = (time.time() - start) * 1000
                print(f"     预热 {i+1}/{warmup_runs}: {elapsed:.2f}ms")
            except Exception as e:
                print(f"     预热失败: {e}")
        
        # 2. 基准测试
        print(f"   ⏳ 基准测试中...")
        total_start = time.time()
        
        for i in range(benchmark_runs):
            try:
                start = time.time()
                response = session.post(
                    f"{self.base_url}/api/v3/query",
                    json={"query": query},
                    timeout=timeout
                )
                elapsed = (time.time() - start) * 1000
                
                if response.status_code == 200:
                    latencies.append(elapsed)
                    if (i + 1) % 10 == 0:
                        print(f"     进度: {i+1}/{benchmark_runs}")
                else:
                    errors.append(f"HTTP {response.status_code}")
                    
            except Exception as e:
                errors.append(str(e))
        
        total_time = time.time() - total_start
        
        # 3. 计算统计指标
        if latencies:
            latencies_sorted = sorted(latencies)
            
            result = BenchmarkResult(
                name=query,
                total_runs=benchmark_runs,
                successful_runs=len(latencies),
                failed_runs=len(errors),
                p50=latencies_sorted[int(len(latencies_sorted) * 0.50)],
                p75=latencies_sorted[int(len(latencies_sorted) * 0.75)],
                p95=latencies_sorted[int(len(latencies_sorted) * 0.95)],
                p99=latencies_sorted[int(len(latencies_sorted) * 0.99)],
                avg=statistics.mean(latencies),
                min=min(latencies),
                max=max(latencies),
                rps=len(latencies) / total_time if total_time > 0 else 0,
                errors=errors
            )
        else:
            result = BenchmarkResult(
                name=query,
                total_runs=benchmark_runs,
                successful_runs=0,
                failed_runs=len(errors),
                p50=0, p75=0, p95=0, p99=0, avg=0, min=0, max=0,
                rps=0,
                errors=errors
            )
        
        # 4. 输出结果
        print(f"\n   ✅ 测试完成")
        print(f"   成功率: {result.successful_runs}/{result.total_runs} ({result.successful_runs/result.total_runs*100 if result.total_runs > 0 else 0:.1f}%)")
        print(f"   延迟统计:")
        print(f"     P50:  {result.p50:.2f}ms")
        print(f"     P75:  {result.p75:.2f}ms")
        print(f"     P95:  {result.p95:.2f}ms")
        print(f"     P99:  {result.p99:.2f}ms")
        print(f"     平均: {result.avg:.2f}ms")
        print(f"   吞吐量: {result.rps:.2f} RPS")
        
        if result.errors:
            print(f"   错误数: {len(result.errors)}")
            print(f"   错误示例: {result.errors[:3]}")
        
        return result
    
    def run_suite(self, queries: List[str], **kwargs) -> List[BenchmarkResult]:
        """运行完整基准测试套件.
        
        Args:
            queries: 测试查询列表
            **kwargs: 传递给run_benchmark的参数
        
        Returns:
            List[BenchmarkResult]: 所有测试结果
        """
        print("=" * 60)
        print("🚀 chatBI 性能基准测试套件")
        print("=" * 60)
        print(f"目标服务器: {self.base_url}")
        print(f"测试查询数: {len(queries)}")
        print()
        
        results = []
        
        for i, query in enumerate(queries):
            print(f"\n[{i+1}/{len(queries)}]", end=" ")
            result = self.run_benchmark(query, **kwargs)
            results.append(result)
        
        # 生成汇总报告
        self._print_summary(results)
        
        return results
    
    def _print_summary(self, results: List[BenchmarkResult]):
        """打印测试汇总报告.
        
        Args:
            results: 测试结果列表
        """
        print("\n" + "=" * 60)
        print("📊 性能基准测试汇总报告")
        print("=" * 60)
        
        print(f"\n{'查询':<30} {'P50':<10} {'P95':<10} {'P99':<10} {'成功率':<10}")
        print("-" * 70)
        
        for result in results:
            success_rate = f"{result.successful_runs/result.total_runs*100:.1f}%" if result.total_runs > 0 else "N/A"
            print(f"{result.name:<30} {result.p50:<10.2f} {result.p95:<10.2f} {result.p99:<10.2f} {success_rate:<10}")
        
        # 整体统计
        all_p95 = [r.p95 for r in results if r.successful_runs > 0]
        all_p99 = [r.p99 for r in results if r.successful_runs > 0]
        
        if all_p95:
            print("\n整体性能:")
            print(f"  平均P95延迟: {statistics.mean(all_p95):.2f}ms")
            print(f"  最大P95延迟: {max(all_p95):.2f}ms")
            print(f"  平均P99延迟: {statistics.mean(all_p99):.2f}ms")
            print(f"  最大P99延迟: {max(all_p99):.2f}ms")
        
        # 性能评级
        print("\n性能评级:")
        avg_p95 = statistics.mean(all_p95) if all_p95 else 0
        
        if avg_p95 < 100:
            grade = "✅ 优秀 (<100ms)"
        elif avg_p95 < 300:
            grade = "🟡 良好 (<300ms)"
        elif avg_p95 < 500:
            grade = "🟠 一般 (<500ms)"
        else:
            grade = "🔴 需优化 (>500ms)"
        
        print(f"  {grade}")
        
        print("\n" + "=" * 60)
    
    def save_results(self, results: List[BenchmarkResult], filename: str):
        """保存测试结果到JSON文件.
        
        Args:
            results: 测试结果列表
            filename: 文件名
        """
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(
                [r.to_dict() for r in results],
                f,
                ensure_ascii=False,
                indent=2
            )
        
        print(f"\n💾 测试结果已保存到: {filename}")


# 预定义测试查询套件
BENCHMARK_QUERIES = [
    # 简单查询
    "GMV",
    "DAU",
    "营收",
    "转化率",
    
    # 时间范围查询
    "最近7天GMV",
    "本月营收总和",
    "最近30天DAU",
    "本周订单量",
    
    # 维度查询
    "按地区GMV",
    "按渠道统计DAU",
    "按品类成交金额",
    
    # 复杂查询
    "最近7天按地区统计GMV总和",
    "本月按渠道统计DAU",
]


if __name__ == "__main__":
    import sys
    
    # 配置
    BASE_URL = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000"
    WARMUP_RUNS = 5
    BENCHMARK_RUNS = 50
    
    print("📋 配置:")
    print(f"  服务器: {BASE_URL}")
    print(f"  预热次数: {WARMUP_RUNS}")
    print(f"  基准测试次数: {BENCHMARK_RUNS}")
    print()
    
    # 运行基准测试
    benchmark = PerformanceBenchmark(BASE_URL)
    results = benchmark.run_suite(
        BENCHMARK_QUERIES,
        warmup_runs=WARMUP_RUNS,
        benchmark_runs=BENCHMARK_RUNS
    )
    
    # 保存结果
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    output_file = f"tests/performance/results/benchmark_{timestamp}.json"
    benchmark.save_results(results, output_file)
    
    print("\n✅ 性能基准测试完成！")
