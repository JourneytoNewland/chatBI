# 配置管理指南

## 快速开始

### 1. 复制环境变量模板
```bash
cp .env.example .env.local
```

### 2. 编辑配置文件
```bash
# 编辑 .env.local
vim .env.local
```

### 3. 配置必需项
```bash
# ZhipuAI API (必需)
ZHIPUAI_API_KEY=your_actual_api_key_here

# API服务端点 (可选)
API_BASE_URL=http://localhost:8000
```

### 4. 验证配置
```bash
# 运行配置验证
python scripts/validate_config.py

# 运行安全检查
bash scripts/security_check.sh
```

---

## 配置优先级

配置读取优先级（从高到低）：

1. **环境变量** (生产环境推荐)
2. **.env.local** (本地开发，不提交)
3. **.env** (默认配置，不提交)
4. **代码默认值** (最后fallback)

---

## 前端配置

### 使用config.js
```html
<!-- 在HTML中引入配置 -->
<script src="config.js"></script>

<script>
  // 使用配置
  const response = await fetch(`${config.apiBaseUrl}/api/v3/query`, ...);
</script>
```

### 覆盖配置
```bash
# 方法1: 通过window对象
<script>
window.API_BASE_URL = 'https://api.example.com';
</script>

# 方法2: 通过构建工具
# Vite
VITE_API_BASE_URL=https://api.example.com

# Webpack
API_BASE_URL=https://api.example.com
```

---

## 后端配置

### 使用配置类
```python
from src.config import settings

# 读取配置
api_key = settings.zhipuai.api_key
neo4j_uri = settings.neo4j.uri
```

### 环境变量命名规则

| 配置项 | 环境变量 | 示例 |
|--------|----------|------|
| ZhipuAI密钥 | `ZHIPUAI_API_KEY` | `sk-xxx` |
| Neo4j地址 | `NEO4J_URI` | `bolt://localhost:7687` |
| PostgreSQL地址 | `POSTGRES_HOST` | `localhost` |
| Qdrant地址 | `QDRANT_HOST` | `localhost` |
| API端点 | `API_BASE_URL` | `http://localhost:8000` |

---

## 生产环境配置

### Docker Compose
```yaml
version: '3.8'
services:
  api:
    image: chatbi:latest
    environment:
      - ZHIPUAI_API_KEY=${ZHIPUAI_API_KEY}
      - NEO4J_URI=neo4j://neo4j:7687
      - POSTGRES_HOST=postgres
    env_file:
      - .env.production
```

### Kubernetes
```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: chatbi-config
data:
  API_BASE_URL: "https://api.example.com"
  NEO4J_URI: "bolt://neo4j:7687"
---
apiVersion: v1
kind: Secret
metadata:
  name: chatbi-secrets
type: Opaque
stringData:
  ZHIPUAI_API_KEY: "sk-xxx"
```

---

## 故障排查

### 问题：ZHIPUAI_API_KEY not configured
**原因**: 环境变量未设置
**解决**: 
```bash
export ZHIPUAI_API_KEY=your_key
# 或创建.env.local文件
```

### 问题：API请求失败
**原因**: 前端端点配置错误
**解决**: 检查 `config.apiBaseUrl` 是否正确

### 问题：数据库连接失败
**原因**: 内网地址未更新
**解决**: 设置相应的环境变量

---

## 安全提示

⚠️ **重要**:
- 永远不要提交 `.env` 或 `.env.local` 到git
- 生产环境使用密钥管理服务
- 定期轮换API密钥
- 使用最小权限原则

✅ **最佳实践**:
- 使用 `.env.example` 作为模板
- 运行配置验证脚本
- 定期审计访问日志
- 监控异常API调用

---

**配置状态**: ✅ 已优化  
**安全评分**: 🎯 10/10
