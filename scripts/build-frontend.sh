#!/bin/bash
# 在 ECS 上构建前端，确保 .env 变量被正确加载
# 用法: cd /opt/pfa && bash scripts/build-frontend.sh

set -e
cd "$(dirname "$0")/.."

if [ ! -f .env ]; then
  echo "错误: .env 不存在，请先创建并填入 NEXT_PUBLIC_SUPABASE_URL 和 NEXT_PUBLIC_SUPABASE_ANON_KEY"
  exit 1
fi

# 将 .env 导出到当前 shell，供 docker compose 变量替换使用
set -a
source .env
set +a

# 校验必要变量
if [ -z "$NEXT_PUBLIC_SUPABASE_URL" ] || [ -z "$NEXT_PUBLIC_SUPABASE_ANON_KEY" ]; then
  echo "错误: .env 中缺少 NEXT_PUBLIC_SUPABASE_URL 或 NEXT_PUBLIC_SUPABASE_ANON_KEY"
  echo "请检查 .env 格式，确保为: KEY=value（等号两侧无空格）"
  exit 1
fi

echo "正在构建前端（Supabase 变量已加载）..."
docker compose build --no-cache frontend
echo "前端构建完成。执行 docker compose up -d 启动服务。"
