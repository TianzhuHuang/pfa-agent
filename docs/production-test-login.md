# 生产环境登录注册测试步骤

## 前置准备

### 1. 同步代码到服务器

在**本地**项目根目录执行：

```bash
cd /Users/huangtianzhu5746/PFA
rsync -av --exclude node_modules --exclude .next --exclude __pycache__ --exclude .git --exclude .env \
  . root@47.110.250.228:/opt/pfa/
```

输入 root 密码后等待同步完成。

### 2. 确认 Supabase 配置

登录 [Supabase Dashboard](https://supabase.com/dashboard) → 选择项目：

- **Authentication** → **URL Configuration**：
  - **Site URL**：`https://pfa.shareyourhealth.cn`（必须为生产域名，禁止 0.0.0.0 或 localhost）
  - **Redirect URLs**：包含 `https://pfa.shareyourhealth.cn/**` 和 `https://pfa.shareyourhealth.cn/auth/callback`
- **邮件确认**：若不需要邮箱验证，可在 **Authentication** → **Providers** → **Email** 中关闭「Confirm email」，注册后即可直接登录

### 3. 确认 ECS 环境变量（必做）

SSH 登录后检查 `/opt/pfa/.env` 是否包含以下变量（构建时注入前端，缺一不可）：

```
NEXT_PUBLIC_SITE_URL=https://pfa.shareyourhealth.cn
SITE_URL=https://pfa.shareyourhealth.cn
NEXT_PUBLIC_SUPABASE_URL=https://你的项目.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=eyJ...（anon key）
```

若出现「Supabase 未配置」错误，说明 `.env` 中缺少上述变量或构建时未加载。**必须**在 `.env` 中补全后执行 `docker compose build --no-cache frontend` 重新构建。

---

## 部署与启动

### 4. 构建并启动

在 ECS 上执行（**推荐**使用脚本，确保 .env 被正确加载）：

```bash
cd /opt/pfa
bash scripts/build-frontend.sh
docker compose build --no-cache backend
docker compose up -d
```

或手动构建（**必须**用 `--env-file .env`，否则 build args 为空）：

```bash
cd /opt/pfa
docker compose --env-file .env build --no-cache
docker compose up -d
```

或一键部署：`bash scripts/deploy-ecs.sh`

### 5. 验证服务

```bash
curl -I http://localhost:3000
curl http://localhost:8000/health
```

若 Nginx 已配置，也可访问：

```bash
curl -I https://pfa.shareyourhealth.cn
```

---

## 测试流程

### 6. 注册流程（无需邮件确认）

1. 打开 https://pfa.shareyourhealth.cn/login
2. 切换到「注册」Tab
3. 输入邮箱、密码（至少 6 位）、确认密码
4. 点击「注册」
5. **预期**：注册成功即已登录，自动跳转到首页

### 7. 登录流程

1. 打开 https://pfa.shareyourhealth.cn/login
2. 输入邮箱和密码
3. 点击「登录」
4. **预期**：跳转到首页，已登录

### 8. 异常情况检查

- 若登录失败：检查 Supabase Dashboard → Authentication → Users 中该用户是否存在

---

## 常见问题

**Q: 点击注册显示「Supabase 未配置」**

A: 生产环境 **不会** 读取 `frontend/.env.local`，该文件仅用于本地开发。Docker 构建时从项目根目录 `/opt/pfa/.env` 读取变量。请按以下步骤排查：

1. **使用构建脚本**（推荐，会显式加载 .env）：
   ```bash
   cd /opt/pfa
   bash scripts/build-frontend.sh
   docker compose up -d
   ```

2. **或手动加载后构建**：Docker Compose 可能未自动加载 .env，可先导出再构建：
   ```bash
   cd /opt/pfa
   set -a && source .env && set +a
   docker compose build --no-cache frontend
   docker compose up -d
   ```

3. **验证 .env 格式**：`KEY=value`，等号两侧无空格，值不要加引号（除非值内含空格）

4. **清除浏览器缓存**：部署后强制刷新（Ctrl+Shift+R）或使用无痕模式

---

## 快速回滚

若构建失败或需回滚：

```bash
cd /opt/pfa
docker compose down
docker compose up -d
```

若需恢复旧镜像，可先 `docker images` 查看历史镜像，再 `docker compose up -d` 使用已构建的镜像。
