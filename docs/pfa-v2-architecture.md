# PFA v2 架构：Next.js + FastAPI

## 概述

前后端分离架构，对标 Stake + Gemini 的极简深色风格。

- **Frontend**: Next.js (App Router) + Tailwind CSS + Framer Motion
- **Backend**: FastAPI (Python)，复用 pfa/ 与 agents/ 的投研逻辑

## 目录结构

```
PFA/
├── frontend/          # Next.js
│   ├── src/
│   │   ├── app/       # App Router 页面
│   │   └── components/
│   └── public/
│       └── logo.png   # 乌龟 Logo
├── backend/            # FastAPI
│   ├── main.py
│   └── api/
│       ├── portfolio.py  # /api/portfolio
│       └── chat.py       # /api/chat/stream (SSE)
├── pfa/               # 共享逻辑（不变）
├── agents/            # 共享逻辑（不变）
└── config/            # 持仓等配置（不变）
```

## 启动方式

### 1. 后端（项目根目录）

```bash
cd /path/to/PFA
pip install -r backend/requirements.txt
# 确保 pfa、agents 可 import（在根目录运行）
uvicorn backend.main:app --reload --port 8000
```

### 2. 前端

```bash
cd frontend
npm run dev
```

### 3. 环境变量

- `DASHSCOPE_API_KEY`: AI 对话（通义千问）
- `NEXT_PUBLIC_API_URL`: 前端请求后端地址，默认 `http://localhost:8000`

## API

| 端点 | 方法 | 说明 |
|------|------|------|
| `/health` | GET | 健康检查 |
| `/api/portfolio` | GET | 持仓估值（total_value_cny, by_account 等） |
| `/api/portfolio/raw` | GET | 原始 portfolio JSON |
| `/api/chat/stream` | POST | AI 对话流式响应（SSE） |

## 设计规范（Stake + Gemini）

- 背景：`#000000`
- 主文字：`#FFFFFF`
- 次要文字：`#888888`
- 涨：`#00e701`，跌：`#ff4e33`
- 字体：Inter
- Logo：圆形，白色线条，左上角固定
