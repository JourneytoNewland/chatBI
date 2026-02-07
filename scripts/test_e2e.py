#!/usr/bin/env python3
"""端到端测试脚本 - 验证整个系统的功能."""

import asyncio
import json
import sys
import time
from typing import Dict, List

import httpx


# ========== 测试配置 ==========

BASE_URL = "http://localhost:8000"

# 测试指标数据
TEST_METRICS = [
    {
        "name": "GMV",
        "code": "gmv_test",
        "description": "成交总额（Gross Merchandise Volume）",
        "domain": "电商",
        "synonyms": ["成交金额", "交易额"],
        "formula": "SUM(订单金额)",
        "importance": 0.95
    },
    {
        "name": "DAU",
        "code": "dau_test",
        "description": "日活跃用户数",
        "domain": "用户",
        "synonyms": ["日活"],
        "formula": "COUNT(DISTINCT user_id) WHERE date = TODAY",
        "importance": 0.9
    }
]


# ========== 测试函数 ==========


class Colors:
    """终端颜色."""
    GREEN = "\033[92m"
    RED = "\033[91m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    ENDC = "\033[0m"
    BOLD = "\033[1m"


def print_success(msg: str):
    """打印成功消息."""
    print(f"{Colors.GREEN}✅{Colors.ENDC} {msg}")


def print_error(msg: str):
    """打印错误消息."""
    print(f"{Colors.RED}❌{Colors.ENDC} {msg}")


def print_info(msg: str):
    """打印信息消息."""
    print(f"{Colors.BLUE}ℹ️{Colors.ENDC} {msg}")


def print_warning(msg: str):
    """打印警告消息."""
    print(f"{Colors.YELLOW}⚠️{Colors.ENDC} {msg}")


def print_section(title: str):
    """打印章节标题."""
    print(f"\n{Colors.BOLD}{'='*60}{Colors.ENDC}")
    print(f"{Colors.BOLD}{title.center(60)}{Colors.ENDC}")
    print(f"{Colors.BOLD}{'='*60}{Colors.ENDC}\n")


async def test_health_check(client: httpx.AsyncClient) -> bool:
    """测试健康检查."""
    print_section("1. 健康检查")

    try:
        # 主服务健康检查
        response = await client.get(f"{BASE_URL}/health")
        response.raise_for_status()
        data = response.json()
        print_success(f"主服务状态: {data['status']}")

        # 管理服务健康检查
        response = await client.get(f"{BASE_URL}/api/v1/management/health")
        response.raise_for_status()
        data = response.json()
        print_success(f"管理服务状态: {data['status']}")

        # 打印功能配置
        features = data.get('features', {})
        print_info("功能配置:")
        for feature, enabled in features.items():
            status = "✅" if enabled else "❌"
            print(f"   {status} {feature}")

        return True

    except Exception as e:
        print_error(f"健康检查失败: {e}")
        return False


async def test_single_metric_import(client: httpx.AsyncClient) -> bool:
    """测试单个指标导入."""
    print_section("2. 单个指标导入")

    try:
        metric = TEST_METRICS[0]
        print_info(f"导入指标: {metric['name']} ({metric['code']})")

        response = await client.post(
            f"{BASE_URL}/api/v1/management/metrics/single",
            json=metric
        )
        response.raise_for_status()
        data = response.json()

        print_success(f"指标创建成功: {data['metric_id']}")

        if 'summary' in data and data['summary']:
            summary = data['summary']
            print_info("GLM 摘要已生成:")
            if 'business_summary' in summary:
                print(f"   业务摘要: {summary['business_summary'][:50]}...")

        return True

    except Exception as e:
        print_error(f"单个指标导入失败: {e}")
        return False


async def test_batch_import(client: httpx.AsyncClient) -> bool:
    """测试批量导入."""
    print_section("3. 批量导入")

    try:
        print_info(f"批量导入 {len(TEST_METRICS)} 个指标...")

        response = await client.post(
            f"{BASE_URL}/api/v1/management/metrics/batch-import",
            json={
                "metrics": TEST_METRICS,
                "generate_summary": True,
                "index_to_graph": True,
                "index_to_vector": True,
                "batch_size": 2
            }
        )
        response.raise_for_status()
        data = response.json()

        task_id = data.get('task_id')
        print_success(f"批量导入任务已提交: {task_id}")
        print_info(f"总指标数: {data['total']}")

        # 等待任务完成
        print_info("等待任务完成...")
        max_wait = 60  # 最多等待60秒
        start = time.time()

        while time.time() - start < max_wait:
            response = await client.get(f"{BASE_URL}/api/v1/management/tasks/{task_id}")
            response.raise_for_status()
            task_data = response.json()

            status = task_data.get('status')
            progress = task_data.get('progress', 0) * 100

            if status == 'completed':
                print_success(f"任务完成！进度: {progress:.1f}%")

                result = task_data.get('result')
                if result:
                    print_info(f"成功: {result['success']}, 失败: {result['failed']}")

                return True

            elif status == 'failed':
                print_error(f"任务失败: {task_data.get('error')}")
                return False

            else:
                print_info(f"任务进行中... 状态: {status}, 进度: {progress:.1f}%")

            await asyncio.sleep(2)

        print_error("任务超时")
        return False

    except Exception as e:
        print_error(f"批量导入失败: {e}")
        return False


async def test_query_metric(client: httpx.AsyncClient) -> bool:
    """测试查询指标."""
    print_section("4. 查询指标")

    try:
        metric_code = TEST_METRICS[0]['code']
        print_info(f"查询指标: {metric_code}")

        response = await client.get(f"{BASE_URL}/api/v1/management/metrics/{metric_code}")
        response.raise_for_status()
        data = response.json()

        print_success(f"查询成功: {data['name']}")
        print_info(f"编码: {data['code']}")
        print_info(f"描述: {data['description']}")
        print_info(f"业务域: {data['domain']}")

        return True

    except Exception as e:
        print_error(f"查询指标失败: {e}")
        return False


async def test_vector_search(client: httpx.AsyncClient) -> bool:
    """测试向量搜索."""
    print_section("5. 向量搜索")

    try:
        query_text = "GMV是多少"
        print_info(f"搜索查询: {query_text}")

        response = await client.post(
            f"{BASE_URL}/api/v1/search",
            json={
                "query": query_text,
                "top_k": 5
            }
        )
        response.raise_for_status()
        data = response.json()

        print_success(f"搜索完成，找到 {data['total']} 个结果")

        # 显示意图识别结果
        if 'intent' in data and data['intent']:
            intent = data['intent']
            print_info("意图识别:")
            print(f"   核心查询: {intent.get('core_query')}")

        # 显示候选结果
        candidates = data.get('candidates', [])
        if candidates:
            print_info("Top 候选:")
            for i, candidate in enumerate(candidates[:3], 1):
                print(f"   {i}. {candidate['name']} ({candidate['code']}) - 相似度: {candidate['score']:.3f}")

        return True

    except Exception as e:
        print_error(f"向量搜索失败: {e}")
        return False


async def run_all_tests():
    """运行所有测试."""
    print(f"\n{Colors.BOLD}{'🚀 开始端到端测试'}{Colors.ENDC}")
    print(f"{Colors.BOLD}{'服务地址: '}{BASE_URL}{Colors.ENDC}\n")

    async with httpx.AsyncClient(timeout=30.0) as client:
        results = []

        # 1. 健康检查
        results.append(await test_health_check(client))

        # 2. 单个指标导入
        results.append(await test_single_metric_import(client))

        # 3. 批量导入
        results.append(await test_batch_import(client))

        # 4. 查询指标
        results.append(await test_query_metric(client))

        # 5. 向量搜索
        results.append(await test_vector_search(client))

        # 汇总结果
        print_section("测试结果汇总")

        total = len(results)
        passed = sum(results)

        if all(results):
            print_success(f"所有测试通过！({passed}/{total})")
            return 0
        else:
            print_error(f"部分测试失败 ({passed}/{total} 通过)")
            return 1


if __name__ == "__main__":
    try:
        exit_code = asyncio.run(run_all_tests())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print_warning("\n测试被用户中断")
        sys.exit(1)
    except Exception as e:
        print_error(f"\n测试执行出错: {e}")
        sys.exit(1)
