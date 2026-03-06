# PFA 阿里云首次部署指南

面向首次部署用户，从阿里云控制台配置到最终访问的完整步骤。

## 架构示意

```
用户 → HTTPS :443 → Nginx → / → Next.js :3000
                        → /api/* → FastAPI :8000
```

---

## 第一步：阿里云控制台配置

### 1.1 安全组放行端口

1. 登录 [阿里云控制台](https://ecs.console.aliyun.com)
2. 左侧 **实例与镜像** → **实例**，找到你的 ECS
3. 点击实例 ID 进入详情 → **安全组** → 点击安全组 ID
4. **入方向** → **手动添加**，添加以下规则：

| 端口范围 | 授权对象 | 说明 |
|----------|----------|------|
| 22/22 | 0.0.0.0/0 | SSH |
| 80/80 | 0.0.0.0/0 | HTTP |
| 443/443 | 0.0.0.0/0 | HTTPS |

### 1.2 域名解析

1. 进入 **云解析 DNS** 或你的域名服务商
2. 添加 A 记录：主机记录 `@` 或 `www`，记录值填 **ECS 公网 IP**
3. 等待解析生效（通常几分钟）

---

## 第二步：Supabase 配置

1. 打开 [Supabase Dashboard](https://supabase.com/dashboard) → 选择项目
2. **Authentication** → **URL Configuration**：
   - **Site URL**：必须为生产域名（如 `https://pfa.shareyourhealth.cn`），**禁止**使用 `http://0.0.0.0:3000`
   - **Redirect URLs**：添加 `https://你的域名/**`、`https://你的域名/auth/callback`
3. **邮件确认**：若不需要邮箱验证，可在 **Providers** → **Email** 中关闭「Confirm email」，注册后即可直接登录
4. 确认 `supabase/migrations/001_initial.sql` 已在 SQL Editor 中执行过

---

## 第三步：SSH 登录 ECS 并安装 Docker

在本地终端执行（将 `你的ECS公网IP` 替换为实际 IP）：

```bash
ssh root@47.110.250.228
```

输入 root 密码后，在 ECS 上执行：

```bash
# 安装 Docker
curl -fsSL https://get.docker.com | sh

# 安装 Docker Compose 插件
apt update && apt install -y docker-compose-plugin

# 验证
docker --version
docker compose version
```

---

## 第四步：在本地准备并上传代码

### 4.1 创建生产 .env

参考项目根目录 `.env.production.example`，在 ECS 上创建 `/opt/pfa/.env`。Supabase 的 Key 可在 [Supabase Dashboard](https://supabase.com/dashboard) → Project Settings → API 中获取。

**JWT 验证**：后端优先使用 JWKS（ES256）验证 JWT。若 ECS 访问 Supabase JWKS 失败（如网络限制），可配置 `SUPABASE_JWT_SECRET`（Supabase Dashboard → Settings → API → JWT Secret，长字符串）作为 HS256 回退。

### 4.2 上传代码到 ECS

在**本地**项目根目录执行（替换 `你的ECS公网IP`）：

```bash
# 务必排除 .env，避免用本地配置覆盖 ECS 上的生产 .env
rsync -avz --exclude node_modules --exclude .next --exclude __pycache__ --exclude .git --exclude .env \
  . root@你的ECS公网IP:/opt/pfa/
```

### 4.3 在 ECS 上创建 .env

SSH 登录 ECS 后：

```bash
cd /opt/pfa
nano .env
```

按 `Ctrl+Shift+V` 粘贴内容（参考 4.1 的变量），保存：`Ctrl+O` 回车，`Ctrl+X` 退出。

```bash
chmod 600 .env
```

> **若之前 rsync 未排除 .env**：可能已用本地空/错误配置覆盖了生产 .env。需重新创建：`cp .env.production.example .env && nano .env` 填入实际值。

---

## 第五步：构建并启动容器

在 ECS 上执行：

```bash
cd /opt/pfa

# 必须用 --env-file 显式加载 .env，否则 build args 为空导致构建失败
# 若报错 "unable to open env file"，说明 .env 不存在，请先按 4.3 创建
docker compose --env-file .env build --no-cache
docker compose up -d

# 验证
curl http://localhost:8000/health
curl -I http://localhost:3000
```

若返回 `{"status":"ok"}` 和 `200 OK`，说明容器正常。

**一键部署**（推荐）：`bash scripts/deploy-ecs.sh`，会校验 .env 并用 `--env-file` 构建。

---

## 第六步：安装 Nginx 并配置反向代理

在 ECS 上执行：

```bash
apt install -y nginx
nano /etc/nginx/sites-available/pfa
```

将 `你的域名` 替换为实际域名，粘贴以下内容：

```nginx
server {
    listen 80;
    server_name 你的域名;

    location / {
        proxy_pass http://127.0.0.1:3000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
        proxy_read_timeout 300;
    }

    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_read_timeout 300;
    }
}
```

保存后执行：

```bash
ln -sf /etc/nginx/sites-available/pfa /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default
nginx -t
systemctl reload nginx
```

---

## 第七步：配置 HTTPS（推荐）

在 ECS 上执行：

```bash
apt install -y certbot python3-certbot-nginx
certbot --nginx -d 你的域名
```

按提示输入邮箱、同意条款。完成后会自动配置 HTTPS。

---

## 验证清单

- [ ] 浏览器访问 `https://你的域名` 能打开登录页
- [ ] 能完成注册和登录
- [ ] 持仓、AI 对话、晨报生成可正常使用

---

## 常见问题

| 问题 | 排查 |
|------|------|
| 502 Bad Gateway | 检查 `docker compose ps` 确认容器在运行；`curl localhost:3000` 和 `curl localhost:8000/health` |
| 登录后跳转失败 | 检查 Supabase Redirect URLs 是否包含 `https://你的域名/**` |
| CORS 报错 | 确认 `.env` 中 `CORS_ORIGINS` 包含 `https://你的域名` |
| 添加持仓显示「数据保存失败」 | 1. 在 `.env` 添加 `PFA_DEBUG_ERRORS=1`，重启 backend，再次添加持仓，弹窗会显示具体错误<br>2. 检查 `docker logs pfa-backend-1 2>&1 | tail -30` 中的 `add_holding 失败` 或 `JWT` 相关日志<br>3. 测试 ECS 能否访问 JWKS：`curl -s "https://你的SUPABASE_URL/auth/v1/.well-known/jwks.json"`（若超时，JWKS 不可用，需配置 `SUPABASE_JWT_SECRET` 作为 HS256 回退；注意：若项目已迁移至 ECC，新 token 必须通过 JWKS 验证，Legacy Secret 仅对旧 token 有效） |
