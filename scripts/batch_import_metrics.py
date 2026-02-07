#!/usr/bin/env python3
"""批量导入指标示例脚本.

演示如何使用 Management API 批量导入指标，包括：
1. 生成 GLM 摘要
2. 入库到 Neo4j 图谱
3. 向量化并入库到 Qdrant

Usage:
    # 直接运行（使用示例数据）
    python scripts/batch_import_metrics.py

    # 指定 JSON 文件
    python scripts/batch_import_metrics.py --file metrics.json

    # 不生成 GLM 摘要（仅使用模板）
    python scripts/batch_import_metrics.py --no-summary

    # 仅生成摘要，不入库
    python scripts/batch_import_metrics.py --summary-only
"""

import asyncio
import json
import time
from typing import List

import httpx
import typer


# ========== 示例数据 ==========

EXAMPLE_METRICS = [
    {
        "name": "GMV",
        "code": "gmv",
        "description": "成交总额（Gross Merchandise Volume），指在一定时期内，平台上所有成交订单的总金额",
        "domain": "电商",
        "synonyms": ["成交金额", "交易额", "总交易额", "销售总额"],
        "formula": "SUM(订单金额)",
        "importance": 0.95
    },
    {
        "name": "DAU",
        "code": "dau",
        "description": "日活跃用户数（Daily Active Users），指在统计日内至少访问过一次的用户数量",
        "domain": "用户",
        "synonyms": ["日活", "日活用户", "每日活跃用户"],
        "formula": "COUNT(DISTINCT user_id) WHERE activity_date = TODAY",
        "importance": 0.9
    },
    {
        "name": "MAU",
        "code": "mau",
        "description": "月活跃用户数（Monthly Active Users），指在统计月内至少访问过一次的用户数量",
        "domain": "用户",
        "synonyms": ["月活", "月活用户", "每月活跃用户"],
        "formula": "COUNT(DISTINCT user_id) WHERE activity_month = CURRENT_MONTH",
        "importance": 0.85
    },
    {
        "name": "转化率",
        "code": "conversion_rate",
        "description": "用户从浏览到购买的比例，用于衡量销售漏斗的效率",
        "domain": "营销",
        "synonyms": ["购买转化率", "成交转化率"],
        "formula": "SUM(订单数) / SUM(访问UV)",
        "importance": 0.88
    },
    {
        "name": "客单价",
        "code": "avg_order_value",
        "description": "平均每笔订单的金额，反映用户的消费能力和销售质量",
        "domain": "电商",
        "synonyms": ["平均订单金额", "人均消费"],
        "formula": "SUM(订单金额) / COUNT(订单数)",
        "importance": 0.8
    },
    {
        "name": "复购率",
        "code": "repurchase_rate",
        "description": "在一定时期内，重复购买的用户占所有购买用户的比例",
        "domain": "用户",
        "synonyms": ["重复购买率", "二次购买率"],
        "formula": "COUNT(用户购买次数>=2) / COUNT(DISTINCT 购买用户)",
        "importance": 0.75
    },
    {
        "name": "留存率",
        "code": "retention_rate",
        "description": "在某一时间段后，仍然活跃的用户占初始用户数的比例",
        "domain": "用户",
        "synonyms": ["用户留存", "留存比例"],
        "formula": "COUNT(DayN活跃用户) / COUNT(Day0活跃用户)",
        "importance": 0.82
    },
    {
        "name": "退货率",
        "code": "return_rate",
        "description": "退货订单数占总订单数的比例，用于衡量商品质量和用户满意度",
        "domain": "售后",
        "synonyms": ["退款率", "退货比例"],
        "formula": "COUNT(退货订单) / COUNT(总订单)",
        "importance": 0.7
    }
]


# ========== API 客户端 ==========


class MetricImportClient:
    """指标导入客户端."""

    def __init__(self, base_url: str = "http://localhost:8000"):
        """初始化客户端.

        Args:
            base_url: API 基础 URL
        """
        self.base_url = base_url
        self.client = httpx.AsyncClient(timeout=60.0)

    async def close(self):
        """关闭客户端."""
        await self.client.aclose()

    async def health_check(self) -> dict:
        """健康检查."""
        response = await self.client.get(f"{self.base_url}/health")
        response.raise_for_status()
        return response.json()

    async def management_health_check(self) -> dict:
        """管理服务健康检查."""
        response = await self.client.get(f"{self.base_url}/api/v1/management/health")
        response.raise_for_status()
        return response.json()

    async def batch_import(
        self,
        metrics: List[dict],
        generate_summary: bool = True,
        index_to_graph: bool = True,
        index_to_vector: bool = True,
        batch_size: int = 5
    ) -> dict:
        """批量导入指标.

        Args:
            metrics: 指标列表
            generate_summary: 是否生成 GLM 摘要
            index_to_graph: 是否入库到图谱
            index_to_vector: 是否入库到向量库
            batch_size: 批处理大小

        Returns:
            导入结果
        """
        payload = {
            "metrics": metrics,
            "generate_summary": generate_summary,
            "index_to_graph": index_to_graph,
            "index_to_vector": index_to_vector,
            "batch_size": batch_size
        }

        response = await self.client.post(
            f"{self.base_url}/api/v1/management/metrics/batch-import",
            json=payload
        )
        response.raise_for_status()
        return response.json()

    async def get_task_status(self, task_id: str) -> dict:
        """获取任务状态.

        Args:
            task_id: 任务 ID

        Returns:
            任务状态
        """
        response = await self.client.get(
            f"{self.base_url}/api/v1/management/tasks/{task_id}"
        )
        response.raise_for_status()
        return response.json()

    async def wait_for_task(
        self,
        task_id: str,
        poll_interval: float = 1.0,
        timeout: float = 300.0
    ) -> dict:
        """等待任务完成.

        Args:
            task_id: 任务 ID
            poll_interval: 轮询间隔（秒）
            timeout: 超时时间（秒）

        Returns:
            最终任务状态
        """
        start = time.time()

        while time.time() - start < timeout:
            task_status = await self.get_task_status(task_id)

            if task_status["status"] in ["completed", "failed"]:
                return task_status

            # 显示进度
            progress = task_status.get("progress", 0) * 100
            print(f"  进度: {progress:.1f}% - {task_status.get('message', '')}")

            await asyncio.sleep(poll_interval)

        raise TimeoutError(f"任务 {task_id} 在 {timeout} 秒后仍未完成")


# ========== 主函数 ==========


app = typer.Typer(help="批量导入指标工具")


@app.command()
def main(
    file: str = typer.Option(None, "--file", "-f", help="指标数据 JSON 文件路径"),
    no_summary: bool = typer.Option(False, "--no-summary", help="不生成 GLM 摘要"),
    summary_only: bool = typer.Option(False, "--summary-only", help="仅生成摘要，不入库"),
    batch_size: int = typer.Option(5, "--batch-size", "-b", help="批处理大小"),
    url: str = typer.Option("http://localhost:8000", "--url", "-u", help="API 服务地址")
):
    """批量导入指标到系统."""
    # 加载数据
    if file:
        print(f"📂 从文件加载指标数据: {file}")
        with open(file, "r", encoding="utf-8") as f:
            metrics = json.load(f)
    else:
        print("📋 使用示例指标数据")
        metrics = EXAMPLE_METRICS

    print(f"✅ 共加载 {len(metrics)} 个指标")

    # 运行异步导入
    asyncio.run(import_metrics(
        metrics=metrics,
        base_url=url,
        generate_summary=not no_summary,
        index_to_graph=not summary_only,
        index_to_vector=not summary_only,
        batch_size=batch_size
    ))


async def import_metrics(
    metrics: List[dict],
    base_url: str,
    generate_summary: bool,
    index_to_graph: bool,
    index_to_vector: bool,
    batch_size: int
):
    """执行导入逻辑."""
    client = MetricImportClient(base_url)

    try:
        # 1. 健康检查
        print("\n1️⃣  检查服务状态...")
        health = await client.health_check()
        print(f"   ✅ 主服务: {health['status']}")

        mgmt_health = await client.management_health_check()
        print(f"   ✅ 管理服务: {mgmt_health['status']}")
        print(f"   📊 GLM 摘要: {'✅' if mgmt_health['services']['glm_summary'] else '❌'}")
        print(f"   🧠 图谱库: {'✅' if mgmt_health['services']['graph_store'] else '❌'}")
        print(f"   🔍 向量库: {'✅' if mgmt_health['services']['vector_store'] else '❌'}")

        # 2. 批量导入
        print("\n2️⃣  开始批量导入...")
        print(f"   - 指标数量: {len(metrics)}")
        print(f"   - 生成摘要: {'是' if generate_summary else '否'}")
        print(f"   - 入库图谱: {'是' if index_to_graph else '否'}")
        print(f"   - 入库向量: {'是' if index_to_vector else '否'}")
        print(f"   - 批处理大小: {batch_size}")

        start = time.time()
        result = await client.batch_import(
            metrics=metrics,
            generate_summary=generate_summary,
            index_to_graph=index_to_graph,
            index_to_vector=index_to_vector,
            batch_size=batch_size
        )

        task_id = result.get("task_id")
        print(f"   ✅ 任务已提交: {task_id}")

        # 3. 等待完成
        print("\n3️⃣  等待任务完成...")
        final_status = await client.wait_for_task(task_id)

        elapsed = time.time() - start

        # 4. 显示结果
        print("\n4️⃣  导入结果:")
        print(f"   - 状态: {final_status['status']}")
        print(f"   - 总数: {final_status['result']['total'] if final_status['result'] else 'N/A'}")
        print(f"   - 成功: {final_status['result']['succeeded'] if final_status['result'] else 'N/A'}")
        print(f"   - 失败: {final_status['result']['failed'] if final_status['result'] else 'N/A'}")
        print(f"   - 耗时: {elapsed:.2f} 秒")

        if final_status['result'] and final_status['result'].get('errors'):
            print("\n⚠️  错误列表:")
            for error in final_status['result']['errors'][:5]:  # 只显示前5个
                print(f"   - {error}")

        print("\n✨ 导入完成!")

    except httpx.HTTPError as e:
        print(f"\n❌ HTTP 请求失败: {e}")
        raise typer.Exit(code=1)
    except Exception as e:
        print(f"\n❌ 导入失败: {e}")
        raise typer.Exit(code=1)
    finally:
        await client.close()


# ========== 导出示例数据 ==========


@app.command()
def export_example(output: str = typer.Option("metrics_example.json", "--output", "-o", help="输出文件路径")):
    """导出示例指标数据到 JSON 文件."""
    with open(output, "w", encoding="utf-8") as f:
        json.dump(EXAMPLE_METRICS, f, ensure_ascii=False, indent=2)
    print(f"✅ 已导出 {len(EXAMPLE_METRICS)} 个示例指标到: {output}")
    print(f"\n📝 编辑该文件后，使用以下命令导入:")
    print(f"   python scripts/batch_import_metrics.py --file {output}")


if __name__ == "__main__":
    app()
