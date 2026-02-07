# 安全配置指南

## 环境变量配置

所有敏感信息必须通过环境变量配置，严禁硬编码。

### 必需的环境变量

```bash
# ZhipuAI API（必需）
export ZHIPUAI_API_KEY=your_api_key_here

# 可选：如果使用OpenAI
export OPENAI_API_KEY=your_openai_key_here
```

### 数据库配置

```bash
# Neo4j（可选）
export NEO4J_URI=bolt://localhost:7687
export NEO4J_USER=neo4j
export NEO4J_PASSWORD=your_password

# PostgreSQL（可选）
export POSTGRES_HOST=localhost
export POSTGRES_PORT=5432
export POSTGRES_DATABASE=chatbi
export POSTGRES_USER=chatbi
export POSTGRES_PASSWORD=your_password
```

### Qdrant配置

```bash
export QDRANT_HOST=localhost
export QDRANT_PORT=6333
# export QDRANT_API_KEY=your_key_if_needed
```

## 安全最佳实践

1. **永远不要提交.env文件**
   - .env已在.gitignore中
   - 使用.env.example作为模板

2. **永远不要硬编码密钥**
   - 使用os.getenv()读取
   - 提供有意义的默认值（非真实密钥）

3. **日志文件管理**
   - 所有.log文件已添加到.gitignore
   - 生产环境使用日志轮转

4. **定期安全审计**
   - 运行scripts/security_check.sh
   - 检查git历史中的敏感信息

## 泄露应急处理

如果怀疑API密钥已泄露：

1. 立即撤销密钥
   ```bash
   # ZhipuAI控制台 -> API密钥 -> 删除
   ```

2. 生成新密钥并更新.env

3. 检查git历史
   ```bash
   git log --all --full-history --source -- "*api_key*"
   git log --all --full-history --source -- "*password*"
   ```

4. 如果历史中包含密钥，必须清理
   ```bash
   # 使用BFG Repo-Cleaner或git filter-repo
   ```
