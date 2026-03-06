#!/bin/bash
# ECS 上一键部署脚本
# 用法: cd /opt/pfa && bash scripts/deploy-ecs.sh
# 解决「每次都报 NEXT_PUBLIC_SUPABASE_* 未设置」：显式用 --env-file 加载 .env

set -e
cd "$(dirname "$0")/.."

if [ ! -f .env ]; then
  echo "错误: .env 不存在"
  echo "请先创建: cp .env.production.example .env && nano .env"
  echo "必须填入: NEXT_PUBLIC_SUPABASE_URL、NEXT_PUBLIC_SUPABASE_ANON_KEY"
  exit 1
fi

# NEXT_PUBLIC_SUPABASE_URL 可用 SUPABASE_URL 替代；anon key 必须其一
if ! grep -qE '^(NEXT_PUBLIC_SUPABASE_URL|SUPABASE_URL)=.+' .env; then
  echo "错误: .env 中缺少 SUPABASE_URL 或 NEXT_PUBLIC_SUPABASE_URL"
  exit 1
fi
if ! grep -qE '^(NEXT_PUBLIC_SUPABASE_ANON_KEY|NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY)=.+' .env; then
  echo "错误: .env 中缺少 NEXT_PUBLIC_SUPABASE_ANON_KEY（Supabase Dashboard → Settings → API → anon public）"
  exit 1
fi

echo ">>> 构建（--env-file .env 确保变量注入，使用缓存加速）..."
docker compose --env-file .env build

# Supabase 已配置时，移除本地 JSON 避免误加载
if grep -qE '^SUPABASE_SERVICE_KEY=.+' .env 2>/dev/null; then
  rm -f config/my-portfolio.json
fi

echo ">>> 启动..."
docker compose up -d

echo ">>> 验证..."
sleep 3
curl -s http://localhost:8000/health && echo ""
curl -sI http://localhost:3000 | head -1
echo "部署完成。"
