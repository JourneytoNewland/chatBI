# 智能问数系统 - Claude Code 上下文

## 项目概述
基于向量库+图谱的混合语义检索系统，用于企业指标的自然语言查询。

## 技术栈
- Python 3.11+
- 向量数据库: Qdrant (或 Milvus)
- 图数据库: Neo4j
- 嵌入模型: m3e-base
- Web框架: FastAPI
- 测试框架: pytest

## 项目结构
semantic-query/
├── src/
│   ├── recall/           # 召回层
│   │   ├── vector/       # 向量召回
│   │   └── graph/        # 图谱召回
│   ├── rerank/           # 精排层
│   ├── validator/        # 验证层
│   ├── inference/        # 推理引擎
│   └── api/              # API层
├── tests/                # 测试
├── configs/              # 配置
└── scripts/              # 脚本

## 代码规范
- 类型注解: 所有函数必须有类型注解
- 文档字符串: Google风格
- 测试: 每个模块必须有对应测试
- 单一职责: 每个类/函数只做一件事

## 当前阶段
✅ **Phase 1-4 全部完成** (2026-02-05)

### 系统状态
- **向量召回层**: ✅ 完成 (m3e-base + Qdrant)
- **图谱召回层**: ✅ 完成 (Neo4j + 多策略召回)
- **融合精排层**: ✅ 完成 (双路召回 + 11维特征)
- **意图识别层**: ✅ 完成 (7维意图识别 + 47测试)

## 已完成的工作

### Phase 4: 意图识别层 (最新完成)
**完成时间**: 2026-02-04
**提交**: 13f58b0

**核心功能**:
1. **时间范围识别**: 相对时间(最近7天/本周/本月)、绝对时间(2023年5月)、智能边界处理
2. **聚合类型识别**: SUM/AVG/COUNT/MAX/MIN/RATE/RATIO 七种聚合
3. **维度识别**: 用户、地区、品类、渠道
4. **比较类型识别**: 同比/环比/日环比/周环比
5. **过滤条件识别**: 业务域、数据新鲜度
6. **核心查询提取**: 自动过滤时间等干扰词，提取核心查询
7. **意图驱动优化**: 使用核心查询词优化检索策略

**测试覆盖**: 47个测试用例
- 正常用例: 23个
- 边界用例: 11个
- 干扰用例: 13个

**性能指标**: 意图识别耗时 < 10ms

### Phase 1-3 详见 [IMPLEMENTATION_PLAN.md](./IMPLEMENTATION_PLAN.md)

## 已知问题

### 🔧 环境配置问题

#### 1. Docker 镜像拉取失败
**问题**: 无法拉取 qdrant/qdrant 和 neo4j 镜像
**现象**:
```
Error: failed to do request: Head "https://registry-1.docker.io/v2/...
dial tcp: lookup registry-1.docker.io on 192.168.65.7:53: no such host
```

**原因**: 网络限制或代理配置问题

**解决方案**:
- ✅ **短期方案**: 使用演示模式 (`run_demo.sh`)，无需 Docker
- 🔄 **长期方案**:
  1. 配置 Docker Desktop 代理 (Settings → Resources → Proxies)
  2. 使用国内镜像源 (阿里云/中科大)
  3. 手动下载镜像导入 (docker save/load)

**影响**: 演示模式功能完整，仅数据为模拟数据，不影响功能测试

---

### 🐛 功能实现问题

#### 1. 意图识别 - 时间表达冲突
**问题**: 用户查询包含多个时间表达时，识别哪个？
**示例**: "最近7天本月的GMV"

**解决方案**: 优先识别第一个时间表达
```python
# 识别 "最近7天"，忽略 "本月"
core_query = "本月的GMV"
```

**改进方向**: 未来可以理解更复杂的组合逻辑

#### 2. 噪音词过滤
**问题**: 口语化查询包含大量无意义词
**示例**: "嗯那个呃这个GMV总和"

**解决方案**: 移除常见停用词
```python
STOP_WORDS = {"嗯", "那个", "呃", "这个", "一下", "我想"}
```

#### 3. 聚合类型冗余
**问题**: 多个聚合关键词同时出现
**示例**: "GMV总额总计合计"

**解决方案**: 识别第一个匹配的聚合类型 (SUM)

---

### 🧪 测试相关问题

#### 1. 2月份天数处理
**问题**: 时间计算需要正确处理闰年

**解决方案**: 使用 calendar.monthrange 自动计算
```python
import calendar
days_in_month = calendar.monthrange(year, month)[1]
```

#### 2. 时间边界计算
**问题**: 周一/周日、月初/月末等边界处理

**解决方案**: 封装时间计算工具函数
```python
def get_week_range(date: datetime) -> tuple[datetime, datetime]:
    # 周一到周日
    monday = date - timedelta(days=date.weekday())
    sunday = monday + timedelta(days=6)
    return monday, sunday
```

#### 3. 正则表达式覆盖
**问题**: 中文表达多样化，需要全面的正则模式

**解决方案**: 逐步积累模式库，增加测试用例
```python
TIME_PATTERNS = [
    (r'最近(\d+)[天日]', TimeGranularity.DAY, -1),
    (r'最[近经](\d+)[天日]', TimeGranularity.DAY, -1),  # 容错
    # ... 更多模式
]
```

---

## 📅 今日工作完成 (2026-02-05)

### Phase 5: 意图识别增强（MVP完成）

**完成时间**: 2026-02-05
**提交**: 待提交

#### ✅ 已完成任务

1. **趋势分析意图识别** (15个测试用例)
   - ✅ 实现 TrendType 枚举（UPWARD/DOWNWARD/FLUCTUATING/STABLE）
   - ✅ 添加15个正则表达式模式
   - ✅ 支持10种指标（GMV/DAU/营收/销量/用户/转化率/客单价/增长率/活跃用户/留存率）
   - ✅ 15个测试用例全部通过

2. **排序需求识别** (12个测试用例)
   - ✅ 实现 SortOrder 枚举和 SortRequirement 数据类
   - ✅ 支持 Top N/Bottom N 识别（前10/后5个）
   - ✅ 支持中英文表达（Top/Bottom/最高/最低）
   - ✅ 支持无数字排序（前几个）
   - ✅ 12个测试用例全部通过

3. **阈值过滤识别** (10个测试用例)
   - ✅ 实现 ThresholdFilter 数据类
   - ✅ 支持中文运算符（大于/小于/超过/至少等）
   - ✅ 支持符号运算符（>/< />=/<=）
   - ✅ 支持单位识别（万/百万/亿/k/M/B）
   - ✅ 10个测试用例全部通过

4. **会话上下文框架** (8个测试用例)
   - ✅ 实现 ConversationContext 类
   - ✅ 实现 ConversationManager 单例管理器
   - ✅ 支持多轮对话（最多5轮历史）
   - ✅ 支持代词解析（它/这个/那个）
   - ✅ 支持会话过期清理（24小时）
   - ✅ 8个测试用例全部通过

#### 📊 成果统计

**新增代码**:
- 枚举类型: 3个（TrendType, SortOrder）
- 数据类: 2个（SortRequirement, ThresholdFilter）
- 新模块: 1个（src/inference/context.py，150行）
- 识别方法: 3个（_extract_trend_type, _extract_sort_requirement, _extract_threshold_filters）
- 扩展 QueryIntent: +3个字段

**测试覆盖**:
- 新增测试文件: 4个
- 新增测试用例: 45个（15 + 12 + 10 + 8）
- 测试通过率: 100%（45/45）
- 总测试用例数: 101个（原有56 + 新增45）

**性能指标**:
- 意图识别耗时: < 10ms（新增3种意图后）
- 单次查询响应时间: < 600ms（包含检索）

#### 🎯 技术亮点

1. **向后兼容**: 所有新字段都是可选的（默认None）
2. **中文支持**: 完整的中文运算符映射（大于→>）
3. **TDD实践**: 先写测试，再实现功能
4. **代码质量**: 完整类型注解，符合 Google 文档字符串规范

#### 📝 待完成任务

- [ ] Stage 5: API集成和前端展示
- [ ] 修复原有测试失败（6个test_intent.py测试）
- [ ] 代码审查和格式化
- [ ] Git commit

---

## 明日工作计划 (2026-02-06)

### 功能增强方向

#### 1. API集成和前端展示 ⭐ (优先级最高)
**预估**: 1天

- [ ] 扩展 IntentInfo 响应模型
  - 添加 trend_type, sort_requirement, threshold_filters 字段
- [ ] 扩展 SearchRequest 模型
  - 添加 conversation_id 字段
- [ ] 更新前端展示
  - 趋势卡片（上升↗ / 下降↘）
  - 排序卡片（Top N / 降序升序）
  - 阈值卡片（GMV > 100万）
  - 会话历史展示
- [ ] 向后兼容测试

#### 2. 意图识别增强扩展 ⭐ (可选)
**优先级**: 中
**预估**: 1-2天

- [ ] 数据导出需求（导出Excel/PDF）
- [ ] 口语化表达扩展
  - 更多同义词库
  - 错别字容错

#### 3. 检索策略优化 (可选)
**优先级**: 中
**预估**: 1-2天

- [ ] 意图驱动的检索策略
  - 根据时间范围调整权重
  - 根据聚合类型调整排序
  - 根据维度预过滤

#### 4. 性能优化 (可选)
**优先级**: 低
**预估**: 1天

- [ ] 缓存优化
  - 意图识别结果缓存
  - 常见查询结果缓存

- [ ] 并发优化
  - 增加并发处理能力
  - 连接池优化

---

### 技术债务

1. **测试覆盖率**: 当前覆盖率约 70%，目标 80%+
2. **原有测试修复**: 6个test_intent.py测试失败（周时间计算、绝对时间年份等）
3. **文档完善**: 部分代码缺少详细注释
4. **日志系统**: 需要结构化日志
5. **监控告警**: 生产环境监控

---

## 快速启动

### 演示模式（推荐）
```bash
./run_demo.sh
# 打开 frontend/index.html
```

### 完整模式（需要修复 Docker）
```bash
docker compose up -d
python scripts/init_seed_data.py
python scripts/init_graph.py
uvicorn src.api.main:app --reload
```

详见 [START_GUIDE.md](./START_GUIDE.md)