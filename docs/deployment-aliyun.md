# PFA 阿里云 Docker 部署

本文档为 PFA v2（Next.js + FastAPI）部署到阿里云 ECS 的快速参考。完整步骤见项目根目录下的部署计划。

## 已实现改动

- **backend/main.py**：CORS 支持通过 `CORS_ORIGINS` 环境变量配置生产域名
- **frontend/next.config.ts**：`output: "standalone"` 以减小 Docker 镜像
- **backend/Dockerfile**：FastAPI 后端镜像
- **frontend/Dockerfile**：Next.js 前端多阶段构建
- **docker-compose.yml**：本地验证与 ECS 部署编排
- **.dockerignore**：排除无关文件，加速构建

## 本地验证

```bash
# 确保 .env 中有 SUPABASE_URL、NEXT_PUBLIC_SUPABASE_URL、NEXT_PUBLIC_SUPABASE_ANON_KEY
docker compose up --build
# 访问 http://localhost:3000 和 http://localhost:8000/health
```

## 生产部署要点

1. 在 ECS 上创建 `.env`，包含 `DASHSCOPE_API_KEY`、`SUPABASE_*`、`CORS_ORIGINS`
2. 构建时传入 `NEXT_PUBLIC_API_URL`（如 `https://你的域名`）
3. 使用 Nginx 反向代理 80/443 → 3000（前端）、`/api/` → 8000（后端）
4. 定时任务：`crontab` 调用 `docker exec <backend容器> python -m pfa.scheduler --run-now`
