"""演示服务器 - 使用模拟数据测试意图识别和前端."""

from datetime import datetime, timedelta
import time
import uuid
import random
from typing import Any, Optional, List, Dict
import sys
import os

# Ensure project root is in python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

# 保持原有的简单 IntentRecognizer 引用，后续可能会用它作为 fallback 或基础
# from src.inference.intent import IntentRecognizer 
# 但为了 Demo 效果，我们将实现一个更强大的 DemoHybridIntentRecognizer

from src.config.metric_loader import metric_loader
from src.inference.intent import QueryIntent, TimeGranularity, AggregationType
from src.recall.vector.qdrant_store import QdrantVectorStore
from src.recall.vector.vectorizer import MetricVectorizer
from src.recall.graph.graph_store import GraphStore
from src.inference.zhipu_intent import ZhipuIntentRecognizer
from src.mql.sql_generator_v2 import SQLGeneratorV2
from src.inference.intent import QueryIntent, TimeGranularity, AggregationType
from src.mql.intelligent_interpreter import IntelligentInterpreter
# from src.mql.mql_engine import MQLEngine # Removed to avoid error if not used or wrong name

# 是否启用真实 LLM(可通过环境变量控制)
import os
USE_REAL_LLM = os.getenv("USE_REAL_LLM", "true").lower() == "true"

# 加载指标数据
MOCK_METRICS = metric_loader.get_all_metrics()

# 创建 FastAPI 应用
app = FastAPI(
    title="智能问数系统 - 演示模式",
    description="使用模拟数据测试意图识别和前端界面",
    version="1.0.0-demo",
)

# 添加 CORS 支持
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """全局异常处理."""
    import traceback
    error_msg = str(exc)
    error_trace = traceback.format_exc()
    print(f"❌ Unhandled Exception: {error_msg}")
    print(error_trace)
    
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "code": 500,
            "message": "Internal Server Error",
            "error": error_msg,
        }
    )

# --- 数据模型定义 (匹配 frontend/index.html) ---

class LayerInfo(BaseModel):
    """层级执行信息."""
    layer_name: str
    confidence: float
    duration: float
    status: str = "success"
    success: bool = True
    metadata: Dict[str, Any] = Field(default_factory=dict)

class Interpretation(BaseModel):
    """智能解读."""
    summary: str
    trend: str
    key_findings: List[str]
    error: Optional[str] = None

class IntentResult(BaseModel):
    """意图识别结果."""
    core_query: str
    source_layer: str
    confidence: float
    time_range: Optional[List[str]] = None # [start, end]
    time_granularity: Optional[str] = None
    aggregation_type: Optional[str] = None
    dimensions: List[str] = Field(default_factory=list)
    filters: Dict[str, Any] = Field(default_factory=dict)
    comparison_type: Optional[str] = None

class RootCauseAnalysis(BaseModel):
    """根因分析结果."""
    report: str
    anomalies: List[Dict[str, Any]]
    trends: Dict[str, Any]
    dimensions: List[Dict[str, Any]]

class QueryRequestV3(BaseModel):
    """V3 查询请求."""
    query: str
    conversation_id: Optional[str] = None

class QueryResponseV3(BaseModel):
    """V3 查询响应."""
    conversation_id: str
    query: str
    intent: IntentResult
    data: List[Dict[str, Any]]
    execution_time_ms: float
    all_layers: List[LayerInfo]
    mql: str
    sql: str
    interpretation: Interpretation
    root_cause_analysis: Optional[RootCauseAnalysis] = None


# --- Demo 核心逻辑 ---

class DemoHybridIntentRecognizer:
    """演示用混合意图识别器."""
    
    def __init__(self, metrics: List[Dict[str, Any]]):
        self.metrics = metrics
        # 建立更丰富的索引：名称、同义词 -> 指标信息
        self.index = {}
        for m in self.metrics:
            self.index[m['name'].lower()] = m
            for syn in m.get('synonyms', []):
                self.index[syn.lower()] = m
        
        # 扩展的语义映射 (保留作为高置信度规则)
        self.semantic_map = {
            "用户活跃度": "DAU",
            "活跃用户": "DAU",
            "user activity": "DAU",
            "active users": "DAU",
            "销售额": "GMV",
            "成交额": "GMV",
            "sales": "GMV",
            "gmv": "GMV",
            "营收": "Revenue",
            "revenue": "Revenue"
        }
        
        # 初始化向量和图谱组件
        try:
            self.vector_store = QdrantVectorStore()
            self.vectorizer = MetricVectorizer()
            self.graph_store = GraphStore()
            print("🚀 [DemoHybridIntentRecognizer] Vector Store, Vectorizer & Graph Store Initialized")
        except Exception as e:
            print(f"⚠️ [DemoHybridIntentRecognizer] Failed to initialize stores: {e}")
            self.vector_store = None
            self.vectorizer = None
            self.graph_store = None
        
        # 初始化 LLM 识别器
        if USE_REAL_LLM:
            try:
                self.llm_recognizer = ZhipuIntentRecognizer(model="glm-4-flash")
                print("🧠 [DemoHybridIntentRecognizer] ZhipuAI LLM Recognizer Initialized")
            except Exception as e:
                print(f"⚠️ [DemoHybridIntentRecognizer] Failed to initialize LLM: {e}")
                self.llm_recognizer = None
        else:
            self.llm_recognizer = None
            print("🔇 [DemoHybridIntentRecognizer] Real LLM disabled (USE_REAL_LLM=false)")

    def recognize(self, query: str) -> dict:
        """识别意图，返回详细的层级信息."""
        start_time = time.time()
        layers = []
        best_metric = None
        confidence = 0.0
        
        # 1. L1 精确匹配层 (Exact + Synonym Matching - PRODUCTION with Scoring)
        l1_start = time.time()
        exact_match = None
        query_lower = query.lower()
        matched_by = "unknown"
        best_score = 0  # 用于选择最佳匹配
        
        # 1.1 精确名称/编码匹配 (最高优先级,得分100)
        for metric in self.metrics:
            if metric['name'].lower() == query_lower or metric['code'].lower() == query_lower:
                exact_match = metric
                matched_by = "exact_name"
                best_score = 100
                print(f"   ✅ L1 Exact Match: {metric['name']}")
                break
        
        # 1.2 同义词精确匹配 (次高优先级,得分90)
        if best_score < 90:
            for metric in self.metrics:
                synonyms = metric.get('synonyms', [])
                for syn in synonyms:
                    if syn.lower() == query_lower:
                        exact_match = metric
                        matched_by = f"synonym_exact:{syn}"
                        best_score = 90
                        print(f"   ✅ L1 Synonym Exact Match: {metric['name']} (via '{syn}')")
                        break
                if best_score >= 90:
                    break
        
        # 1.3 查询词完整包含指标名 (得分80)
        if best_score < 80:
            for metric in self.metrics:
                metric_name_lower = metric['name'].lower()
                # 查询词包含完整指标名(作为独立词)
                if metric_name_lower in query_lower:
                    # 检查是否是独立词
                    # 对于英文指标(如DAU, GMV),只需检查前后不是ASCII字母数字
                    idx = query_lower.find(metric_name_lower)
                    
                    # 检查前一个字符
                    char_before_ok = (idx == 0 or not query_lower[idx-1].isascii() or not query_lower[idx-1].isalnum())
                    # 检查后一个字符
                    char_after_ok = (idx + len(metric_name_lower) == len(query_lower) or \
                                    not query_lower[idx + len(metric_name_lower)].isascii() or \
                                    not query_lower[idx + len(metric_name_lower)].isalnum())
                    
                    if char_before_ok and char_after_ok:
                        exact_match = metric
                        matched_by = f"query_contains_metric:{metric_name_lower}"
                        best_score = 80
                        print(f"   ✅ L1 Query Contains Metric: {metric['name']}")
                        break

        
        # 1.4 同义词部分匹配 (得分60-70,按匹配长度)
        if best_score < 70:
            for metric in self.metrics:
                synonyms = metric.get('synonyms', [])
                for syn in synonyms:
                    syn_lower = syn.lower()
                    # 同义词包含在查询中 或 查询包含同义词
                    if syn_lower in query_lower:
                        score = 60 + min(10, len(syn_lower))  # 越长的同义词得分越高
                        if score > best_score:
                            exact_match = metric
                            matched_by = f"synonym_partial:{syn}"
                            best_score = score
                            print(f"   ✅ L1 Synonym Partial Match: {metric['name']} (via '{syn}', score={score})")
        
        l1_duration = (time.time() - l1_start) * 1000
        
        if exact_match and best_score >= 60:  # 至少60分才算匹配成功
            layers.append(LayerInfo(
                layer_name="L1 精确匹配",
                confidence=min(1.0, best_score / 100.0),
                duration=l1_duration,
                success=True,
                metadata={"match_type": matched_by, "metric": exact_match['name'], "score": best_score}
            ))
            best_metric = exact_match
            confidence = min(1.0, best_score / 100.0)
        else:
            layers.append(LayerInfo(
                layer_name="L1 精确匹配",
                confidence=0.0,
                duration=l1_duration,
                success=False,
                metadata={"match_type": "none", "best_score": best_score}
            ))
        
        # 2. L2 向量/图谱召回层 (仅在L1未匹配时执行)
        l2_start = time.time()
        
        # 2.1 向量检索 (Real Vector Search - 仅在L1失败时)

        if not best_metric and self.vector_store:
            try:
                # 向量化查询
                query_vec = self.vectorizer.model.encode(query, normalize_embeddings=True)
                # 检索 Top-1
                results = self.vector_store.search(query_vec, top_k=1, score_threshold=0.15)
                
                if results:
                    top_result = results[0]
                    payload = top_result['payload']
                    target_metric = self._find_metric_by_name(payload['name'])
                    
                    if target_metric:
                        best_metric = target_metric
                        matched_by = "vector_search"
                        # 归一化分数 (Qdrant Cosine is -1 to 1, usually 0-1 for text)
                        confidence = float(top_result['score'])
                        print(f"   vector search found: {target_metric['name']} with score: {confidence}")
                        # 提升一点信心
                        if confidence > 0.15: 
                            confidence = min(0.9, confidence + 0.4) 
            except Exception as e:
                print(f"⚠️ Vector search error: {e}")

        # 并行尝试图谱召回 (Domain Search)
        # 这里的逻辑是：如果 query 包含 domain 关键词 (e.g. "电商", "用户")，
        # 则从图谱找回相关指标。如果 vector 没找到，或者分数低，可以利用 graph 结果增强。
        # 简单 Demo: 如果匹配到 Domain，则看看 Domain 下是否有指标匹配 query 的部分？
        # 或者仅仅作为 candidates 提供给 Debug。
        graph_candidates = []
        if self.graph_store:
            try:
                # 简单关键词提取 Domain
                target_domain = None
                if "电商" in query: target_domain = "电商"
                elif "用户" in query: target_domain = "用户"
                
                if target_domain:
                    # 从图谱查该 Domain 下的所有指标
                    domain_metrics = self.graph_store.search_by_domain(target_domain)
                    for dm in domain_metrics:
                        graph_candidates.append(dm)
                    print(f"   graph search found {len(domain_metrics)} metrics in domain '{target_domain}'")
                    
                    # 如果还没有 best_metric，看看能否从 graph 结果里撞上?
                    if not best_metric and domain_metrics:
                        # 简单的包含匹配
                        for dm in domain_metrics:
                            if dm['name'] in query:
                                best_metric = self._find_metric_by_name(dm['name'])
                                matched_by = "graph_domain_match"
                                confidence = 0.9
                                break
            except Exception as e:
                print(f"⚠️ Graph search error: {e}")

        # 最后尝试模糊匹配 (Fallback)
        if not best_metric:
            for metric in self.metrics:
                if metric['name'].lower() in query_lower:
                    best_metric = metric
                    matched_by = "fuzzy_match"
                    confidence = 0.85
                    break

        # 默认 GMV (Failover)
        if not best_metric:
            best_metric = self._find_metric_by_name("GMV") if self._find_metric_by_name("GMV") else self.metrics[0]
            matched_by = "default"
            confidence = 0.6

        l2_duration = (time.time() - l2_start) * 1000
        
        # 构造 L2 元数据
        candidates = []
        if best_metric:
            candidates.append({
                "rank": 1,
                "name": best_metric['name'],
                "source": matched_by,
                "final_score": confidence,
                "feature_scores": {
                    "VectorSimilarity": {"value": 0.9, "weight": 0.3, "score": 0.27},
                    "ExactMatch": {"value": 1.0 if matched_by == "keyword_match" else 0.0, "weight": 0.15, "score": 0.15},
                }
            })
            
        layers.append(LayerInfo(
            layer_name="L2 向量/图谱召回",
            confidence=confidence,
            duration=l2_duration,
            success=True,
            metadata={
                "recall_type": "dual_recall",
                "candidates": candidates,
                "fusion_stats": {
                    "total_candidates": len(candidates) + len(graph_candidates),
                    "vector_avg_score": 0.8,
                    "graph_hit": len(graph_candidates) > 0
                },
                "graph_candidates": [c['name'] for c in graph_candidates[:5]] # Debug info
            }
        ))

        # 3. LLM 层 (L3) - 解析时间范围/维度 (Real or Mock)
        l3_start = time.time()
        llm_result = None
        
        if self.llm_recognizer:
            try:
                # 将 candidates 传递给 LLM 让它根据实际候选指标进行选择
                candidate_list = [{'name': best_metric['name'], 'code': best_metric['code']}] if best_metric else []
                llm_result = self.llm_recognizer.recognize(query, candidates=candidate_list)
                
                if llm_result:
                    # 使用 LLM 解析的维度
                    dimensions = llm_result.dimensions if llm_result.dimensions else []
                    
                    # LLM 解析的时间范围
                    if llm_result.time_range:
                        time_info = llm_result.time_range
                        now = datetime.now()
                        # 简化处理: 假设 LLM 返回 "7d" 或 "this_month" 等
                        time_value = time_info.get('value', '')
                        if time_value == '7d' or '7' in time_value:
                            start_date = now - timedelta(days=7)
                            end_date = now
                        elif 'this_month' in time_value or '本月' in time_info.get('description', ''):
                            start_date = now.replace(day=1)
                            end_date = now
                        else:
                            start_date = now - timedelta(days=7)
                            end_date = now
                    else:
                        start_date = datetime.now() - timedelta(days=7)
                        end_date = datetime.now()
                    
                    print(f"   LLM parsed: dimensions={dimensions}, time_range={llm_result.time_range}")
                else:
                    # LLM 返回 None，回退到 Mock
                    now = datetime.now()
                    start_date = now - timedelta(days=7)
                    end_date = now
                    dimensions = []
                    if "地区" in query: dimensions.append("地区")
                    if "渠道" in query: dimensions.append("渠道")
            except Exception as e:
                print(f"⚠️ LLM recognition error: {e}")
                now = datetime.now()
                start_date = now - timedelta(days=7)
                end_date = now
                dimensions = []
                if "地区" in query: dimensions.append("地区")
                if "渠道" in query: dimensions.append("渠道")
        else:
            # Mock time range logic (LLM disabled)
            now = datetime.now()
            start_date = now - timedelta(days=7)
            end_date = now
            dimensions = []
            if "地区" in query:
                dimensions.append("地区")
            if "渠道" in query:
                dimensions.append("渠道")
        
        l3_duration = (time.time() - l3_start) * 1000
        layers.append(LayerInfo(
            layer_name="L3 LLM增强",
            confidence=llm_result.confidence if llm_result else 0.95,
            duration=l3_duration,
            success=True,
            metadata={
                "llm_model": "glm-4-flash" if self.llm_recognizer else "mock",
                "tokens": llm_result.tokens_used.get('total_tokens', 0) if llm_result else 0,
                "real_llm": self.llm_recognizer is not None
            }
        ))

        return {
            "metric": best_metric,
            "layers": layers,
            "dimensions": dimensions,
            "time_range": (start_date, end_date),
            "confidence": confidence
        }

    def _find_metric_by_name(self, name: str):
        for m in self.metrics:
            if m['name'].upper() == name.upper():
                return m
            if m['code'].upper() == name.upper():
                return m
        return None

demo_recognizer = DemoHybridIntentRecognizer(MOCK_METRICS)
intelligent_interpreter = IntelligentInterpreter()


def _generate_intelligent_interpretation(query: str, metric: Dict, data: List[Dict], sql: str, start_time: float) -> Interpretation:
    """生成智能解读(使用LLM)."""
    try:
        # 规范化数据字段名(intelligent_interpreter期望"value"字段)
        normalized_data = []
        for row in data:
            normalized_row = row.copy()
            if "metric_value" in normalized_row and "value" not in normalized_row:
                normalized_row["value"] = normalized_row["metric_value"]
            normalized_data.append(normalized_row)
        
        # 构建mql_result供interpret方法使用
        mql_result_for_interpret = {
            "result": normalized_data,
            "row_count": len(normalized_data),
            "sql": sql,
            "execution_time_ms": (time.time() - start_time) * 1000
        }
        
        # 获取metric_def
        metric_def = {
            "name": metric['name'],
            "code": metric['code'],
            "unit": metric.get('unit', '未知'),
            "description": metric.get('description', '')
        }
        
        # 调用智能解读器
        interpretation_result = intelligent_interpreter.interpret(
            query=query,
            mql_result=mql_result_for_interpret,
            metric_def=metric_def
        )
        
        return Interpretation(
            summary=interpretation_result.summary,
            trend=interpretation_result.trend,
            key_findings=interpretation_result.key_findings,
            error=None
        )
    except Exception as e:
        import traceback
        print(f"❌ Intelligent Interpretation failed: {str(e)}")
        traceback.print_exc()
        
        # 降级到默认模板
        return Interpretation(
            summary=f"查询 {metric['name']} 的数据",
            trend="stable",
            key_findings=[f"共 {len(data)} 条记录"],
            error=str(e)
        )


@app.post("/api/v3/query", response_model=QueryResponseV3)
async def query_v3(request: QueryRequestV3):
    """全功能查询接口 (模拟)."""
    start_time = time.time()
    
    # 1. 意图识别
    recognition_result = demo_recognizer.recognize(request.query)
    metric = recognition_result['metric']
    start_date, end_date = recognition_result['time_range']
    dimensions = recognition_result['dimensions']
    
    # 2. 生成 SQL (Real SQL Generation)
    generated_sql = None
    sql_params = {}
    try:
        # 构造 QueryIntent 对象
        query_intent = QueryIntent(
            query=request.query,
            core_query=metric['name'],
            time_range=(start_date, end_date),
            time_granularity=TimeGranularity.DAY,
            aggregation_type=AggregationType.SUM,
            dimensions=dimensions,
            comparison_type=None,
            filters={}
        )
        
        # 生成 SQL
        sql_generator = SQLGeneratorV2()
        generated_sql, sql_params = sql_generator.generate(query_intent)
        print(f"   ✅ Generated SQL ({len(generated_sql)} chars)")
    except Exception as e:
        print(f"   ⚠️ SQL generation error: {e}")
        generated_sql = None
    
    # 3. 构造意图结果
    intent_result = IntentResult(
        core_query=metric['name'],
        source_layer="L2 向量/图谱召回" if recognition_result['confidence'] > 0.8 else "L3 LLM增强",
        confidence=recognition_result['confidence'],
        time_range=[start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d")],
        time_granularity="day",
        aggregation_type="SUM",
        dimensions=dimensions
    )
    
    # 4. 生成 Mock 数据 (TODO: 替换为真实数据库查询)
    data = []
    current = start_date
    while current <= end_date:
        date_str = current.strftime("%Y-%m-%d")
        base_value = random.randint(1000, 5000)
        
        if dimensions:
            for dim in ["华东", "华南", "华北"]: # Mock 维度值
                data.append({
                    "date": date_str,
                    dimensions[0]: dim,
                    "metric_value": base_value * random.uniform(0.8, 1.2),
                    "metric": metric['name']
                })
        else:
            data.append({
                "date": date_str,
                "metric_value": base_value * random.uniform(0.8, 1.2),
                "metric": metric['name']
            })
        current += timedelta(days=1)

    # 4. 生成 Interpretation
    interpretation = Interpretation(
        summary=f"{metric['name']} 在过去7天表现平稳。",
        trend="stable",
        key_findings=[
            f"{metric['name']} 均值为 {sum(d['metric_value'] for d in data)/len(data):.2f}",
            "未发现明显异常波动"
        ]
    )
    
    # 5. 生成 MQL/SQL (Mock)
    mql_str = f"SELECT {metric['name']} BY {','.join(dimensions) if dimensions else 'overall'} FROM {start_date.strftime('%Y-%m-%d')} TO {end_date.strftime('%Y-%m-%d')}"
    sql_str = f"SELECT dd.date, {', '.join([d+'.name' for d in dimensions] + ['']) if dimensions else ''} SUM(f.{metric['column']}) \nFROM {metric.get('table', 'fact_table')} f \nJOIN dim_date dd ON f.date_key = dd.date_key \nWHERE dd.date BETWEEN '{start_date.strftime('%Y-%m-%d')}' AND '{end_date.strftime('%Y-%m-%d')}' \nGROUP BY dd.date {', ' + ','.join([d+'.name' for d in dimensions]) if dimensions else ''}"

    # 6. 根因分析 (如果查询包含关键词)
    rca = None
    if any(k in request.query for k in ["为什么", "分析", "原因"]):
        rca = RootCauseAnalysis(
            report=f"{metric['name']} 的变化主要受季节性因素影响。",
            anomalies=[
                {"timestamp": start_date.strftime("%Y-%m-%d"), "value": 1200, "expected": 1500, "severity": "medium", "type": "dip", "deviation_pct": -20.0}
            ],
            trends={"trend_type": "stable", "trend_strength": 0.8, "slope": 0.1, "r_squared": 0.95},
            dimensions=[
                {"dimension_name": "地区", "analysis": "华东地区贡献最大", "top_contributors": [{"name": "华东", "contribution_pct": 45}]}
            ]
        )

    execution_time = (time.time() - start_time) * 1000

    # 5. 返回响应 (包含生成的 SQL)
    return QueryResponseV3(
        conversation_id=request.conversation_id or str(uuid.uuid4()),
        query=request.query,
        intent=intent_result,
        data=data,
        execution_time_ms=int((time.time() - start_time) * 1000),
        all_layers=recognition_result['layers'],
        mql=f"Query(metric='{metric['name']}', dimensions={dimensions})",
        sql=generated_sql if generated_sql else "-- SQL generation failed",
        interpretation=_generate_intelligent_interpretation(request.query, metric, data, generated_sql if generated_sql else sql_str, start_time),
        root_cause_analysis=None
    )


# 保持 /api/v1/search 以兼容旧脚本 (Optional)
# ... code omitted for brevity but keeping it simple ...
# 为了避免冲突，我们不再定义旧的 search_request/response class, 
# 但如果旧脚本模拟的是 vector search，我们可以保留一个简化版

class SearchRequestV1(BaseModel):
    query: str
    top_k: int = 10

class SearchResponseV1(BaseModel):
    query: str
    candidates: List[Dict[str, Any]]

@app.post("/api/v1/search", response_model=SearchResponseV1)
async def search_v1(request: SearchRequestV1):
    """兼容旧版检索接口."""
    # 复用 DemoHybridIntentRecognizer 的 L2 逻辑
    recog = demo_recognizer.recognize(request.query)
    metric = recog['metric']
    
    return SearchResponseV1(
        query=request.query,
        candidates=[{
            "id": metric['id'],
            "metric_id": metric['id'], # Compat
            "name": metric['name'],
            "code": metric['code'],
            "description": metric['description'],
            "domain": metric['domain'],
            "score": recog['confidence'],
            "synonyms": metric.get('synonyms', []),
            "formula": metric.get('formula')
        }]
    )

@app.get("/")
async def root():
    return {
        "message": "智能问数系统 - 演示模式 (V3 API Enabled)",
        "version": "1.0.0-demo-v3",
        "docs": "/docs",
    }

@app.get("/health")
async def health_check():
    return {"status": "healthy", "mode": "demo"}

if __name__ == "__main__":
    import uvicorn
    print("""
    🚀 智能问数系统 - 演示模式 (V3 API Enabled)
    =====================================
    服务地址: http://localhost:8000
    API 文档: http://localhost:8000/docs
    前端界面: 在浏览器中打开 frontend/index.html
    =====================================
    """)
    uvicorn.run("scripts.run_demo_server:app", host="0.0.0.0", port=8000, reload=True)
