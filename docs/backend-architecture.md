# PFA 后端架构（FastAPI 迁移）

## 概述

从 Streamlit 内存/JSON 迁移至 FastAPI + SQLite 持久化架构，实现：
- 对话记录持久化（刷新不丢失）
- 多终端同步
- Agent 异步流式（晨报 SSE）

## 端口与路由

| 服务 | 端口 | 说明 |
|------|------|------|
| **FastAPI 后端** | 8000 | 主 API，前端 Next.js 通过 rewrites 代理 `/api/*` |
| Streamlit（旧版） | 8501 | 可选，仅用于遗留面板 |
| Next.js 前端 | 3000 | 主入口 |

前端请求 `/api/xxx` 时，Next.js 会代理到 `http://localhost:8000/api/xxx`（可通过 `NEXT_PUBLIC_API_URL` 改为 5000）。无需请求 Streamlit 8500/8501。

## 数据库层

- **路径**：`data/pfa.db`（SQLite）
- **表**：`chat_messages`（对话）、`accounts`、`holdings`（组合）、`portfolio_meta`（channels/preferences）、`fx_rates`（汇率）
- **环境变量**：`PFA_USE_DB=1`（默认）使用 DB；`PFA_USE_DB=0` 回退到 JSON

### 迁移脚本

```bash
python scripts/migrate_chat_to_db.py   # 对话 JSON → DB
python scripts/sync_fx_rates.py        # 汇率 API → DB（可加入 cron 每日执行）
```

组合：首次 `load_portfolio` 时若 DB 为空且存在 JSON，自动迁移。

## API 一览

| 接口 | 说明 |
|------|------|
| `GET /api/chat/history` | 加载对话，支持 JSON→DB 自动迁移 |
| `POST /api/chat/history` | 保存对话，保留 `\n\n` 换行 |
| `POST /api/chat/stream` | 流式 AI 回复 |
| `POST /api/briefing/generate` | 流式晨报（SSE 状态推送） |

## 启动

```bash
# 后端
uvicorn backend.main:app --reload --port 8000

# 前端
cd frontend && npm run dev
```
