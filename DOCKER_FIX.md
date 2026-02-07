# Docker 网络问题解决方案

## 🐛 问题诊断

你的系统使用了网络代理，导致 Docker 无法访问 Docker Hub：
```
tls: failed to verify certificate: x509: certificate is valid for *.facebook.com
```

## ✅ 解决方案

### 方案 1: 配置 Docker 镜像加速器（推荐）

#### 步骤：

1. **打开 Docker Desktop 设置**
   ```bash
   open /Applications/Docker.app
   ```

2. **进入 Docker Engine 设置**
   - 点击右上角的齿轮图标 ⚙️
   - 选择左侧菜单的 "Docker Engine"

3. **添加镜像配置**

   将以下 JSON 配置粘贴到编辑器中：
   ```json
   {
     "registry-mirrors": [
       "https://docker.mirrors.ustc.edu.cn",
       "https://hub-mirror.c.163.com",
       "https://mirror.baidubce.com"
     ],
     "dns": ["8.8.8.8", "114.114.114.114"]
   }
   ```

4. **应用并重启**
   - 点击 "Apply & Restart"
   - 等待 Docker 重启完成（约 30 秒）

5. **验证配置**
   ```bash
   docker info | grep -A 5 "Registry Mirrors"
   ```

---

### 方案 2: 配置系统代理

如果你需要使用企业代理：

1. **打开 Docker Desktop 设置**
   ```bash
   open /Applications/Docker.app
   ```

2. **配置代理**
   - 点击设置 ⚙️
   - 选择 "Resources" → "Proxies"
   - 启用 "Manual proxy configuration"
   - 填入代理服务器地址和端口

3. **重启 Docker**

---

### 方案 3: 导入已有镜像（离线方式）

如果有离线镜像文件：

```bash
# 导入镜像
docker load -i qdrant.tar.gz
docker load -i neo4j.tar.gz

# 或者从其他来源
docker pull registry.cn-hangzhou.aliyuncs.com/qdrant/qdrant:latest
docker tag registry.cn-hangzhou.aliyuncs.com/qdrant/qdrant:latest qdrant/qdrant:latest
```

---

### 方案 4: 使用 Podman 替代（高级）

如果 Docker 问题持续存在：

```bash
# 安装 Podman（macOS）
brew install podman

# 初始化
podman machine init

# 启动
podman machine start

# 使用 Podman 代替 Docker
podman compose up -d
```

---

## 🧪 验证 Docker 是否正常

配置完成后，运行以下命令验证：

```bash
# 测试基础连接
docker run --rm hello-world

# 测试拉取镜像
docker pull alpine:latest

# 查看镜像
docker images
```

如果以上命令都成功，说明 Docker 已恢复正常！

---

## 🚀 启动服务

Docker 正常后，执行：

```bash
# 启动数据库服务
docker compose up -d

# 查看服务状态
docker compose ps

# 查看日志
docker compose logs -f
```

---

## 🔧 故障排查

### 问题 1: 配置后仍无法拉取镜像

**解决**: 清理 Docker 缓存
```bash
docker system prune -a
```

### 问题 2: 证书验证失败

**解决**: 临时禁用 TLS 验证（不推荐生产环境）
```json
{
  "insecure-registries": ["registry-1.docker.io"],
  "tls-verify": false
}
```

### 问题 3: DNS 解析问题

**解决**: 配置 DNS 服务器
```json
{
  "dns": ["8.8.8.8", "8.8.4.4", "114.114.114.114"]
}
```

---

## 📞 获取帮助

如果问题仍未解决：

1. 查看 Docker Desktop 日志：
   ```bash
   ~/Library/Containers/com.docker.docker/Data/log/*/console.log
   ```

2. 重置 Docker Desktop：
   - 打开 Docker Desktop
   - 点击故障图标 🐳
   - 选择 "Clean / Purge data"
   - 重新配置

3. 检查网络代理设置：
   ```bash
   scutil --proxy
   ```

---

**最后更新**: 2026-02-04
