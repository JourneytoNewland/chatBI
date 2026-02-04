# 智能问数系统 (Semantic Query System)

基于向量库+图谱的混合语义检索系统，用于企业指标的自然语言查询。

## 技术栈

- **Python**: 3.11+
- **Web框架**: FastAPI
- **向量数据库**: Qdrant
- **图数据库**: Neo4j
- **嵌入模型**: m3e-base
- **测试框架**: pytest

## 项目结构

```
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
```

## 快速开始

### 安装依赖

```bash
# 安装项目依赖
pip install -e .

# 安装开发依赖
pip install -e ".[dev]"

# 安装 pre-commit hooks
pre-commit install
```

### 运行测试

```bash
pytest
```

### 代码格式化

```bash
# 运行 black
black src/ tests/

# 运行 ruff
ruff check src/ tests/ --fix

# 运行 mypy
mypy src/
```

## 开发规范

- 所有函数必须有类型注解
- 文档字符串使用 Google 风格
- 每个模块必须有对应测试
- 单一职责：每个类/函数只做一件事

## 当前阶段

Phase 1: 向量召回基座

## 许可证

MIT
