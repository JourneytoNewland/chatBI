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
Phase 1: 向量召回基座

## 已完成的工作
(随进度更新)

## 已知问题
(记录遇到的问题和解决方案)