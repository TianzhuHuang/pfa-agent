# Supabase 存储配置

持仓、账户、对话等数据默认写入 Supabase PostgreSQL。若 Supabase 未正确配置，数据会回退到 SQLite/JSON，且 **Supabase 表将始终为空**。

## 必须配置的环境变量

后端需要以下变量（在 `/opt/pfa/.env` 或 Docker `env_file` 中）：

| 变量 | 说明 | 获取位置 |
|------|------|----------|
| `SUPABASE_URL` | 项目 URL | Supabase Dashboard → Settings → API |
| `SUPABASE_SERVICE_KEY` | Service Role Key（**非** anon key） | Settings → API → `service_role`（secret） |
| `SUPABASE_JWT_SECRET` | JWT 密钥，用于解析前端 token | Settings → API → JWT Secret |

**注意**：`NEXT_PUBLIC_SUPABASE_ANON_KEY` 仅用于前端，后端必须使用 `SUPABASE_SERVICE_KEY` 才能读写数据库。

## 诊断

登录后访问（需带 Authorization 头）：

```
GET /api/portfolio/storage-status
```

返回示例：

```json
{
  "user_id": "uuid-xxx",
  "supabase_configured": true,
  "storage": "supabase",
  "env_check": {
    "SUPABASE_URL": true,
    "SUPABASE_SERVICE_KEY": true
  }
}
```

若 `supabase_configured` 为 `false` 或 `SUPABASE_SERVICE_KEY` 为 `false`，说明后端未使用 Supabase，数据在 SQLite/JSON。

## 迁移脚本

若已在 SQLite/JSON 中有数据，需在 Supabase SQL Editor 执行 `supabase/migrations/001_initial.sql` 创建表结构后，通过应用正常添加持仓，数据会写入 Supabase。
