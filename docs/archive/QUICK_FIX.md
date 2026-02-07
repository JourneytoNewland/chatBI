# 快速修复 Docker 问题

## 🐛 问题

DNS 无法解析镜像加速器：
```
dial tcp: lookup docker.mirrors.ustc.edu.cn: no such host
```

## ✅ 解决方案（3选1）

### 方案 1: 移除镜像加速器（最简单）

1. 打开 Docker Desktop
2. Settings → Docker Engine
3. 将配置改为：
   ```json
   {
     "dns": ["8.8.8.8", "114.114.114.114"]
   }
   ```
4. Apply & Restart

### 方案 2: 配置系统 DNS

1. 系统设置 → 网络 → Wi-Fi → 详情
2. DNS → 手动
3. 添加：
   - 8.8.8.8
   - 114.114.114.114

### 方案 3: 使用本地代理（如果有）

1. Docker Desktop → Settings → Resources → Proxies
2. 启用 Manual proxy configuration
3. 填入代理地址

---

## 🚀 完成后

运行测试：
```bash
/Applications/Docker.app/Contents/Resources/bin/docker pull alpine:latest
```

成功后启动服务：
```bash
docker compose up -d
```

---

**推荐**: 使用方案 1（移除镜像加速器）
