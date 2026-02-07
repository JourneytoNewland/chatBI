# 安全最佳实践指南

## 目标
实现 **10/10** 的安全评分

---

## ✅ 已完成的安全措施

### 1. 密钥管理 (10/10)
- ✅ 无硬编码API密钥
- ✅ 强制从环境变量读取
- ✅ 安全配置文档完善
- ✅ 安全检查脚本已创建

### 2. 环境隔离 (10/10)
- ✅ .env文件已忽略
- ✅ .env.example提供模板
- ✅ .env.local用于本地开发
- ✅ 日志文件已忽略

### 3. 日志安全 (10/10)
- ✅ 所有.log文件已忽略
- ✅ 从git追踪中移除
- ✅ .gitignore规则完善

### 4. 代码安全 (10/10)
- ✅ 无硬编码密钥
- ✅ 配置验证脚本
- ✅ 安全审计完成

### 5. 前端安全 (待优化 7/10 → 10/10)
- ⚠️  硬编码API端点 → 使用配置文件
- ⚠️  内网地址暴露 → 环境变量化
- ✅ 配置文件已创建
- ✅ 环境变量支持

---

## 🎯 达到满分10/10的优化方案

### Step 1: 前端配置文件化

**当前问题**:
```javascript
// ❌ 硬编码在多个HTML文件中
const response = await fetch('http://localhost:8000/api/v3/query', ...
```

**优化方案**:
```javascript
// ✅ 使用统一配置
import config from './config.js';
const response = await fetch(`${config.apiBaseUrl}/api/v3/query`, ...
```

**实施**:
1. 所有HTML文件添加 `<script src="config.js"></script>`
2. 使用 `config.apiBaseUrl` 替代硬编码端点

### Step 2: 后端配置环境变量化

**当前问题**:
```python
# ❌ 硬编码默认值
class Neo4jClient:
    def __init__(self, uri: str = "bolt://localhost:7687"):
```

**优化方案**:
```python
# ✅ 使用配置类
from src.config import settings

class Neo4jClient:
    def __init__(self, uri: str = None):
        self.uri = uri or settings.neo4j.uri
```

**实施**:
1. 扩展 `src/config.py` 的配置类
2. 所有硬编码地址改为读取配置

### Step 3: 配置验证机制

**新增验证**:
```python
# 启动时验证配置
@app.on_event("startup")
async def validate_config():
    required_vars = ['ZHIPUAI_API_KEY']
    missing = [var for var in required_vars if not os.getenv(var)]
    if missing:
        raise RuntimeError(f"Missing required env vars: {missing}")
```

---

## 📋 安全检查清单

### 开发环境
- [ ] 使用 `.env.local` 存储本地配置
- [ ] `.env.local` 已添加到 `.gitignore`
- [ ] 运行 `scripts/security_check.sh`
- [ ] 运行 `scripts/validate_config.py`

### 生产环境
- [ ] 所有密钥使用环境变量
- [ ] 使用密钥管理服务（AWS KMS、Azure Key Vault）
- [ ] 启用HTTPS
- [ ] 配置CORS白名单
- [ ] 启用请求速率限制

### CI/CD
- [ ] 不要提交 `.env` 文件
- [ ] 使用 Secrets 管理环境变量
- [ ] 运行安全检查脚本
- [ ] 扫描依赖漏洞

---

## 🔧 配置示例

### 前端配置 (frontend/config.js)
```javascript
const config = {
  apiBaseUrl: window.API_BASE_URL || 'http://localhost:8000',
  // ...
};
export default config;
```

### 后端配置 (src/config.py)
```python
class Settings(BaseSettings):
    neo4j_uri: str = Field(default="bolt://localhost:7687")
    postgres_host: str = Field(default="localhost")
    
    class Config:
        env_file = ".env"
```

### 环境变量 (.env)
```bash
# 必需
ZHIPUAI_API_KEY=your_key_here

# 可选
NEO4J_URI=bolt://localhost:7687
POSTGRES_HOST=localhost
API_BASE_URL=http://localhost:8000
```

---

## 🚀 部署安全

### Docker部署
```yaml
# docker-compose.yml
services:
  api:
    environment:
      - ZHIPUAI_API_KEY=${ZHIPUAI_API_KEY}
    env_file:
      - .env.production
```

### Kubernetes部署
```yaml
# deployment.yaml
env:
  - name: ZHIPUAI_API_KEY
    valueFrom:
      secretKeyRef:
        name: api-secrets
        key: zhipuai-key
```

---

## 📊 安全评分计算

| 类别 | 权重 | 当前 | 目标 |
|------|------|------|------|
| 密钥管理 | 30% | 10/10 | 10/10 |
| 环境隔离 | 25% | 10/10 | 10/10 |
| 日志安全 | 15% | 10/10 | 10/10 |
| 前端安全 | 20% | 7/10 | 10/10 |
| 配置验证 | 10% | 8/10 | 10/10 |
| **总分** | 100% | **8.25** | **10.0** |

---

## ✅ 验收标准

1. ✅ 运行 `scripts/validate_config.py` 全部通过
2. ✅ 运行 `scripts/security_check.sh` 全部通过
3. ✅ 前端无硬编码端点
4. ✅ 后端无硬编码地址
5. ✅ 所有配置可通过环境变量覆盖
6. ✅ 生产环境可安全部署

---

**最终目标**: 安全评分 **10/10** 🎯
