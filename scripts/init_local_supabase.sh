#!/bin/bash
# 本地 Supabase 调试环境初始化
# 用法: cd 项目根目录 && bash scripts/init_local_supabase.sh
# 不覆盖已有 .env 或 frontend/.env.local

set -e
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

echo ">>> 本地 Supabase 调试环境初始化"
echo ""

# 1. 项目根目录 .env
if [ ! -f .env ]; then
  if [ -f .env.production.example ]; then
    cp .env.production.example .env
    echo "已创建 .env（从 .env.production.example 复制）"
    echo "请编辑 .env 确认 SUPABASE_URL、SUPABASE_SERVICE_KEY、SUPABASE_JWT_SECRET、DASHSCOPE_API_KEY 已填入"
    echo "可选: 添加 PFA_DEBUG_ERRORS=1 便于排查保存失败"
  else
    echo "警告: .env.production.example 不存在，请手动创建 .env"
  fi
else
  echo ".env 已存在，跳过"
fi

echo ""

# 2. 前端 frontend/.env.local
if [ ! -f frontend/.env.local ]; then
  if [ -f frontend/.env.example ]; then
    cp frontend/.env.example frontend/.env.local
    # 确保本地 API 直连
    if ! grep -q '^NEXT_PUBLIC_API_URL=' frontend/.env.local; then
      echo "NEXT_PUBLIC_API_URL=http://localhost:8000" >> frontend/.env.local
    fi
    echo "已创建 frontend/.env.local（从 frontend/.env.example 复制）"
    echo "请编辑 frontend/.env.local 填入 NEXT_PUBLIC_SUPABASE_URL 和 NEXT_PUBLIC_SUPABASE_ANON_KEY"
  else
    echo "警告: frontend/.env.example 不存在，请手动创建 frontend/.env.local"
  fi
else
  echo "frontend/.env.local 已存在，跳过"
fi

echo ""
echo ">>> 完成。启动命令："
echo "  终端 1: uvicorn backend.main:app --reload --port 8000"
echo "  终端 2: cd frontend && npm run dev"
echo "  访问 http://localhost:3000 并登录 Supabase 账号"
echo ""
