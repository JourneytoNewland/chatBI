#!/usr/bin/env python3
"""
生产级端到端测试套件
测试所有真实组件:Vector Search, Graph Search, LLM, SQL Generation
"""
import sys
import os
import time
import json
from datetime import datetime

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.recall.vector.qdrant_store import QdrantVectorStore
from src.recall.vector.vectorizer import MetricVectorizer
from src.recall.graph.graph_store import GraphStore
from src.inference.zhipu_intent import ZhipuIntentRecognizer
from src.mql.sql_generator_v2 import SQLGeneratorV2
from src.inference.intent import QueryIntent, TimeGranularity, AggregationType
from src.config.metric_loader import metric_loader

class ProductionTestSuite:
    """生产级测试套件"""
    
    def __init__(self):
        self.results = {
            "vector_search": [],
            "graph_search": [],
            "llm_intent": [],
            "sql_generation": [],
            "e2e_flow": []
        }
        self.total_tests = 0
        self.passed_tests = 0
        self.failed_tests = 0
    
    def test_vector_search(self):
        """测试 Qdrant 向量检索 (真实)"""
        print("\n" + "="*80)
        print("🔍 TEST 1: Vector Search (Qdrant) - Production Component")
        print("="*80)
        
        test_cases = [
            {"query": "销售额", "expected_metric": "GMV", "min_score": 0.3},
            {"query": "日活用户", "expected_metric": "DAU", "min_score": 0.3},
            {"query": "订单数量", "expected_metric": "订单量", "min_score": 0.3},
            {"query": "用户留存", "expected_metric": "留存率", "min_score": 0.2},
            {"query": "投资回报", "expected_metric": "ROI", "min_score": 0.2},
        ]
        
        try:
            vector_store = QdrantVectorStore()
            vectorizer = MetricVectorizer()
            
            for i, case in enumerate(test_cases, 1):
                self.total_tests += 1
                print(f"\n  Test 1.{i}: Query='{case['query']}' -> Expected='{case['expected_metric']}'")
                
                query_vec = vectorizer.model.encode(case['query'], normalize_embeddings=True)
                results = vector_store.search(query_vec, top_k=3, score_threshold=0.1)
                
                if results:
                    top_result = results[0]
                    metric_name = top_result['payload']['name']
                    score = top_result['score']
                    
                    passed = (metric_name == case['expected_metric'] and score >= case['min_score'])
                    
                    print(f"    Result: {metric_name} (score={score:.4f})")
                    print(f"    Status: {'✅ PASS' if passed else '❌ FAIL'}")
                    
                    if passed:
                        self.passed_tests += 1
                    else:
                        self.failed_tests += 1
                    
                    self.results["vector_search"].append({
                        "query": case['query'],
                        "expected": case['expected_metric'],
                        "actual": metric_name,
                        "score": score,
                        "passed": passed
                    })
                else:
                    print(f"    Status: ❌ FAIL (No results)")
                    self.failed_tests += 1
                    
        except Exception as e:
            print(f"  ❌ Vector Search Test Failed: {e}")
            self.failed_tests += len(test_cases)
    
    def test_graph_search(self):
        """测试 Neo4j 图谱检索 (真实)"""
        print("\n" + "="*80)
        print("🕸️  TEST 2: Graph Search (Neo4j) - Production Component")
        print("="*80)
        
        test_cases = [
            {"domain": "电商", "min_metrics": 3},
            {"domain": "用户", "min_metrics": 3},
        ]
        
        try:
            graph_store = GraphStore()
            
            for i, case in enumerate(test_cases, 1):
                self.total_tests += 1
                print(f"\n  Test 2.{i}: Domain='{case['domain']}' -> Min Metrics={case['min_metrics']}")
                
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
        print("🧠 TEST 3: LLM Intent Recognition (ZhipuAI) - Production Component")
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
        ]
        
        try:
            llm_recognizer = ZhipuIntentRecognizer(model="glm-4-flash")
            
            for i, case in enumerate(test_cases, 1):
                self.total_tests += 1
                print(f"\n  Test 3.{i}: Query='{case['query']}'")
                
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
                    print(f"    Tokens: {result.tokens_used.get('total_tokens', 0)}")
                    print(f"    Status: {'✅ PASS' if passed else '❌ FAIL'}")
                    
                    if passed:
                        self.passed_tests += 1
                    else:
                        self.failed_tests += 1
                    
                    self.results["llm_intent"].append({
                        "query": case['query'],
                        "result": {
                            "dimensions": result.dimensions,
                            "time_range": result.time_range,
                            "comparison": result.comparison_type
                        },
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
        print("📝 TEST 4: SQL Generation - Production Component")
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
                print(f"\n  Test 4.{i}: {case['name']}")
                
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
                    "sql_length": len(sql),
                    "passed": passed
                })
                
        except Exception as e:
            print(f"  ❌ SQL Generation Test Failed: {e}")
            import traceback
            traceback.print_exc()
            self.failed_tests += len(test_cases)
    
    def test_e2e_flow(self):
        """测试端到端流程 (真实)"""
        print("\n" + "="*80)
        print("🔄 TEST 5: End-to-End Production Flow")
        print("="*80)
        
        import requests
        
        test_cases = [
            {"query": "最近7天的GMV", "expected_metric": "GMV"},
            {"query": "本月按渠道统计DAU", "expected_metric": "DAU", "expected_dims": ["渠道"]},
            {"query": "电商订单量", "expected_metric": "订单量"},
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
                        "sql_generated": sql_generated,
                        "passed": passed
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
        print(f"生产级测试套件 - Running {iterations} iterations")
        print("🚀"*40)
        
        for iteration in range(1, iterations + 1):
            print(f"\n{'#'*80}")
            print(f"# ITERATION {iteration}/{iterations}")
            print(f"{'#'*80}")
            
            self.test_vector_search()
            self.test_graph_search()
            self.test_llm_intent()
            self.test_sql_generation()
            self.test_e2e_flow()
            
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
        with open('test_results.json', 'w', encoding='utf-8') as f:
            json.dump({
                "summary": {
                    "total": self.total_tests,
                    "passed": self.passed_tests,
                    "failed": self.failed_tests,
                    "success_rate": self.passed_tests/self.total_tests*100
                },
                "details": self.results
            }, f, ensure_ascii=False, indent=2)
        
        print("📄 Detailed results saved to: test_results.json\n")

if __name__ == "__main__":
    suite = ProductionTestSuite()
    suite.run_all_tests(iterations=2)
