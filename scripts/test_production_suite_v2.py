#!/usr/bin/env python3
"""
生产级端到端测试套件 V2 - 聚焦真实生产流程
只测试E2E流程,不测试孤立的向量检索(因为生产环境使用L1+L2混合策略)
"""
import sys
import os
import time
import json
from datetime import datetime

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.recall.graph.graph_store import GraphStore
from src.inference.zhipu_intent import ZhipuIntentRecognizer
from src.mql.sql_generator_v2 import SQLGeneratorV2
from src.inference.intent import QueryIntent, TimeGranularity, AggregationType

class ProductionTestSuiteV2:
    """生产级测试套件 V2 - 聚焦E2E流程"""
    
    def __init__(self):
        self.results = {
            "graph_search": [],
            "llm_intent": [],
            "sql_generation": [],
            "e2e_flow": []
        }
        self.total_tests = 0
        self.passed_tests = 0
        self.failed_tests = 0
    
    def test_graph_search(self):
        """测试 Neo4j 图谱检索 (真实)"""
        print("\n" + "="*80)
        print("🕸️  TEST 1: Graph Search (Neo4j) - Production Component")
        print("="*80)
        
        test_cases = [
            {"domain": "电商", "min_metrics": 3},
            {"domain": "用户", "min_metrics": 3},
        ]
        
        try:
            graph_store = GraphStore()
            
            for i, case in enumerate(test_cases, 1):
                self.total_tests += 1
                print(f"\n  Test 1.{i}: Domain='{case['domain']}' -> Min Metrics={case['min_metrics']}")
                
                results = graph_store.search_by_domain(case['domain'])
                metric_count = len(results)
                
                passed = metric_count >= case['min_metrics']
                
                print(f"    Found: {metric_count} metrics")
                if results:
                    print(f"    Metrics: {[r['name'] for r in results[:5]]}")
                print(f"    Status: {'✅ PASS' if passed else '❌ FAIL'}")
                
                if passed:
                    self.passed_tests += 1
                else:
                    self.failed_tests += 1
                
                self.results["graph_search"].append({
                    "domain": case['domain'],
                    "expected_min": case['min_metrics'],
                    "actual_count": metric_count,
                    "passed": passed
                })
                
            graph_store.close()
            
        except Exception as e:
            print(f"  ❌ Graph Search Test Failed: {e}")
            self.failed_tests += len(test_cases)
    
    def test_llm_intent(self):
        """测试 ZhipuAI LLM 意图识别 (真实)"""
        print("\n" + "="*80)
        print("🧠 TEST 2: LLM Intent Recognition (ZhipuAI) - Production Component")
        print("="*80)
        
        test_cases = [
            {
                "query": "本月按渠道统计DAU",
                "expected_dimensions": ["渠道"],
                "expected_time": "本月"
            },
            {
                "query": "按地区的成交金额同比",
                "expected_dimensions": ["地区"],
                "expected_comparison": "yoy"
            },
            {
                "query": "最近7天的GMV",
                "expected_time": "7",
                "expected_metric": "GMV"
            },
            {
                "query": "销售额趋势",
                "expected_metric": "销售额"
            },
        ]
        
        try:
            llm_recognizer = ZhipuIntentRecognizer(model="glm-4-flash")
            
            for i, case in enumerate(test_cases, 1):
                self.total_tests += 1
                print(f"\n  Test 2.{i}: Query='{case['query']}'")
                
                result = llm_recognizer.recognize(case['query'])
                
                if result:
                    passed = True
                    
                    # Check dimensions
                    if "expected_dimensions" in case:
                        dims_match = set(result.dimensions) == set(case['expected_dimensions'])
                        passed = passed and dims_match
                        print(f"    Dimensions: {result.dimensions} (Expected: {case['expected_dimensions']}) {'✅' if dims_match else '❌'}")
                    
                    # Check time
                    if "expected_time" in case and result.time_range:
                        time_desc = result.time_range.get('description', '') + result.time_range.get('value', '')
                        time_match = case['expected_time'] in time_desc
                        passed = passed and time_match
                        print(f"    Time: {result.time_range} {'✅' if time_match else '❌'}")
                    
                    # Check comparison
                    if "expected_comparison" in case:
                        comp_match = result.comparison_type == case['expected_comparison']
                        passed = passed and comp_match
                        print(f"    Comparison: {result.comparison_type} {'✅' if comp_match else '❌'}")
                    
                    print(f"    Confidence: {result.confidence}")
                    print(f"    Status: {'✅ PASS' if passed else '❌ FAIL'}")
                    
                    if passed:
                        self.passed_tests += 1
                    else:
                        self.failed_tests += 1
                    
                    self.results["llm_intent"].append({
                        "query": case['query'],
                        "passed": passed
                    })
                else:
                    print(f"    Status: ❌ FAIL (No result)")
                    self.failed_tests += 1
                    
        except Exception as e:
            print(f"  ❌ LLM Intent Test Failed: {e}")
            import traceback
            traceback.print_exc()
            self.failed_tests += len(test_cases)
    
    def test_sql_generation(self):
        """测试 SQL 生成 (真实)"""
        print("\n" + "="*80)
        print("📝 TEST 3: SQL Generation - Production Component")
        print("="*80)
        
        test_cases = [
            {
                "name": "Simple Query",
                "intent": {
                    "query": "GMV",
                    "core_query": "GMV",
                    "time_range": (datetime(2026, 2, 1), datetime(2026, 2, 8)),
                    "time_granularity": TimeGranularity.DAY,
                    "aggregation_type": AggregationType.SUM,
                    "dimensions": [],
                    "comparison_type": None,
                    "filters": {}
                },
                "expected_keywords": ["SELECT", "FROM", "WHERE", "date"]
            },
            {
                "name": "Dimension Query",
                "intent": {
                    "query": "按渠道统计DAU",
                    "core_query": "DAU",
                    "time_range": (datetime(2026, 2, 1), datetime(2026, 2, 8)),
                    "time_granularity": TimeGranularity.DAY,
                    "aggregation_type": AggregationType.AVG,
                    "dimensions": ["渠道"],
                    "comparison_type": None,
                    "filters": {}
                },
                "expected_keywords": ["SELECT", "GROUP BY", "JOIN", "dim_channel"]
            },
        ]
        
        try:
            sql_generator = SQLGeneratorV2()
            
            for i, case in enumerate(test_cases, 1):
                self.total_tests += 1
                print(f"\n  Test 3.{i}: {case['name']}")
                
                query_intent = QueryIntent(**case['intent'])
                sql, params = sql_generator.generate(query_intent)
                
                passed = all(keyword in sql for keyword in case['expected_keywords'])
                
                print(f"    SQL Length: {len(sql)} chars")
                print(f"    Keywords Check: {case['expected_keywords']}")
                for keyword in case['expected_keywords']:
                    found = keyword in sql
                    print(f"      - {keyword}: {'✅' if found else '❌'}")
                
                print(f"    Status: {'✅ PASS' if passed else '❌ FAIL'}")
                
                if passed:
                    self.passed_tests += 1
                else:
                    self.failed_tests += 1
                
                self.results["sql_generation"].append({
                    "name": case['name'],
                    "passed": passed
                })
                
        except Exception as e:
            print(f"  ❌ SQL Generation Test Failed: {e}")
            import traceback
            traceback.print_exc()
            self.failed_tests += len(test_cases)
    
    def test_e2e_flow(self):
        """测试端到端流程 (真实) - 扩展测试用例"""
        print("\n" + "="*80)
        print("🔄 TEST 4: End-to-End Production Flow (Extended)")
        print("="*80)
        
        import requests
        
        test_cases = [
            {"query": "最近7天的GMV", "expected_metric": "GMV"},
            {"query": "本月按渠道统计DAU", "expected_metric": "DAU", "expected_dims": ["渠道"]},
            {"query": "电商订单量", "expected_metric": "订单量"},
            {"query": "销售额", "expected_metric": "GMV"},  # 通过L1同义词匹配
            {"query": "订单数量", "expected_metric": "订单量"},  # 通过L1同义词匹配
            {"query": "用户留存", "expected_metric": "留存率"},  # 通过L1同义词匹配
            {"query": "投资回报", "expected_metric": "ROI"},  # 通过L1同义词匹配
            {"query": "日活用户", "expected_metric": "DAU"},  # 通过L1同义词匹配
        ]
        
        for i, case in enumerate(test_cases, 1):
            self.total_tests += 1
            print(f"\n  Test 4.{i}: Query='{case['query']}'")
            
            try:
                response = requests.post(
                    "http://localhost:8000/api/v3/query",
                    json={"query": case['query']},
                    timeout=30
                )
                
                if response.status_code == 200:
                    data = response.json()
                    
                    # Check metric
                    metric_match = case['expected_metric'] in data['intent']['core_query']
                    print(f"    Metric: {data['intent']['core_query']} {'✅' if metric_match else '❌'}")
                    
                    # Check dimensions
                    dims_match = True
                    if "expected_dims" in case:
                        dims_match = set(data['intent']['dimensions']) == set(case['expected_dims'])
                        print(f"    Dimensions: {data['intent']['dimensions']} {'✅' if dims_match else '❌'}")
                    
                    # Check SQL generated
                    sql_generated = data.get('sql') and data['sql'] != "-- SQL generation failed"
                    print(f"    SQL Generated: {'✅' if sql_generated else '❌'}")
                    
                    # Check data returned
                    data_returned = len(data.get('data', [])) > 0
                    print(f"    Data Returned: {len(data.get('data', []))} records {'✅' if data_returned else '❌'}")
                    
                    passed = metric_match and dims_match and sql_generated and data_returned
                    
                    print(f"    Status: {'✅ PASS' if passed else '❌ FAIL'}")
                    
                    if passed:
                        self.passed_tests += 1
                    else:
                        self.failed_tests += 1
                    
                    self.results["e2e_flow"].append({
                        "query": case['query'],
                        "metric": data['intent']['core_query'],
                        "passed": passed
                    })
                else:
                    print(f"    Status: ❌ FAIL (HTTP {response.status_code})")
                    self.failed_tests += 1
                    
            except Exception as e:
                print(f"    Status: ❌ FAIL ({e})")
                self.failed_tests += 1
    def test_e2e_adversarial_flow(self):
        """测试端到端流程 (干扰性/对抗性测试)"""
        print("\n" + "="*80)
        print("⚔️  TEST 5: E2E Adversarial Flow (High Interference)")
        print("="*80)
        
        import requests
        
        # 干扰性测试用例 (Expect strict Name match)
        test_cases = [
            # 1. 订单量干扰组
            {"query": "有效订单量", "expected_name": "有效订单量", "forbidden_name": "订单量"},
            {"query": "支付订单量", "expected_name": "支付订单量", "forbidden_name": "订单量"},
            {"query": "退款订单量", "expected_name": "退款订单量", "forbidden_name": "订单量"},
            
            # 2. GMV干扰组
            {"query": "预测GMV", "expected_name": "预测GMV", "forbidden_name": "GMV"}, # "GMV" might be substring of "预测GMV", so we need strict check
            {"query": "日均GMV", "expected_name": "日均GMV", "forbidden_name": "GMV"},
            
            # 3. 转化率干扰组
            {"query": "点击转化率", "expected_name": "点击转化率", "forbidden_name": "转化率"},
            {"query": "支付转化率", "expected_name": "支付转化率", "forbidden_name": "转化率"},
            
            # 4. 物流干扰组 (语义相近)
            {"query": "发货时长", "expected_name": "发货时长", "forbidden_name": "配送时长"},
            {"query": "配送时长", "expected_name": "配送时长", "forbidden_name": "发货时长"},
            
            # 5. 财务干扰组
            {"query": "净利", "expected_name": "净利", "forbidden_name": "毛利"},
            {"query": "毛利", "expected_name": "毛利", "forbidden_name": "净利"},
        ]
        
        for i, case in enumerate(test_cases, 1):
            self.total_tests += 1
            print(f"\n  Test 5.{i}: Query='{case['query']}'")
            
            try:
                response = requests.post(
                    "http://localhost:8000/api/v3/query",
                    json={"query": case['query']},
                    timeout=30
                )
                
                if response.status_code == 200:
                    data = response.json()
                    metric_name = data['intent']['core_query']
                    
                    # Strict validation
                    metric_match = metric_name == case['expected_name']
                    
                    # Forbidden check: The identified metric Name should NOT be the forbidden one
                    # e.g. if we want "Valid Order Count", we don't want "Order Count"
                    forbidden_match = metric_name == case['forbidden_name']
                    
                    print(f"    Metric Name: {metric_name}")
                    print(f"    Expected: {case['expected_name']} {'✅' if metric_match else '❌'}")
                    print(f"    Forbidden: {case['forbidden_name']} {'✅' if not forbidden_match else '❌ (Found Forbidden!)'}")
                    
                    passed = metric_match and not forbidden_match
                    
                    print(f"    Status: {'✅ PASS' if passed else '❌ FAIL'}")
                    
                    if passed:
                        self.passed_tests += 1
                    else:
                        self.failed_tests += 1
                    
                    self.results["e2e_flow"].append({
                        "query": case['query'],
                        "metric": metric_name,
                        "passed": passed,
                        "type": "adversarial"
                    })
                else:
                    print(f"    Status: ❌ FAIL (HTTP {response.status_code})")
                    self.failed_tests += 1
                    
            except Exception as e:
                print(f"    Status: ❌ FAIL ({e})")
                self.failed_tests += 1
    def run_all_tests(self, iterations=2):
        """运行所有测试 (指定次数)"""
        print("\n" + "🚀"*40)
        print(f"生产级测试套件 V2 - Running {iterations} iterations")
        print("聚焦E2E流程 - 真实生产场景")
        print("🚀"*40)
        
        for iteration in range(1, iterations + 1):
            print(f"\n{'#'*80}")
            print(f"# ITERATION {iteration}/{iterations}")
            print(f"{'#'*80}")
            
            self.test_graph_search()
            self.test_llm_intent()
            self.test_sql_generation()
            self.test_e2e_flow()
            self.test_e2e_adversarial_flow()
            
            if iteration < iterations:
                print(f"\n⏳ Waiting 3 seconds before next iteration...")
                time.sleep(3)
        
        self.print_summary()
    
    def print_summary(self):
        """打印测试总结"""
        print("\n" + "="*80)
        print("📊 TEST SUMMARY")
        print("="*80)
        
        print(f"\nTotal Tests: {self.total_tests}")
        print(f"✅ Passed: {self.passed_tests}")
        print(f"❌ Failed: {self.failed_tests}")
        print(f"Success Rate: {(self.passed_tests/self.total_tests*100):.1f}%")
        
        print("\n" + "="*80)
        
        if self.failed_tests == 0:
            print("🎉 ALL TESTS PASSED - PRODUCTION READY!")
        else:
            print("⚠️  SOME TESTS FAILED - REVIEW REQUIRED")
        
        print("="*80 + "\n")
        
        # Save results
        with open('test_results_v2.json', 'w', encoding='utf-8') as f:
            json.dump({
                "summary": {
                    "total": self.total_tests,
                    "passed": self.passed_tests,
                    "failed": self.failed_tests,
                    "success_rate": self.passed_tests/self.total_tests*100
                },
                "details": self.results
            }, f, ensure_ascii=False, indent=2)
        
        print("📄 Detailed results saved to: test_results_v2.json\n")

if __name__ == "__main__":
    suite = ProductionTestSuiteV2()
    suite.run_all_tests(iterations=2)
