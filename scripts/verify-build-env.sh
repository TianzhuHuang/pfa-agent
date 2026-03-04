#!/bin/bash
# 在 ECS 上运行此脚本，验证前端构建能否获取 Supabase 变量
# 用法: cd /opt/pfa && bash scripts/verify-build-env.sh

set -e
cd "$(dirname "$0")/.."

echo "=== 检查 .env 文件 ==="
if [ ! -f .env ]; then
  echo "错误: .env 不存在"
  exit 1
fi

echo "NEXT_PUBLIC_SUPABASE_URL: $(grep -E '^NEXT_PUBLIC_SUPABASE_URL=' .env | cut -d= -f2- | head -c 50)..."
echo "NEXT_PUBLIC_SUPABASE_ANON_KEY: $(grep -E '^NEXT_PUBLIC_SUPABASE_ANON_KEY=' .env | cut -d= -f2- | head -c 30)..."
echo ""

echo "=== Docker Compose 解析后的 frontend build args ==="
docker compose config 2>/dev/null | grep -A 20 "frontend:" | grep -A 15 "args:" || true
echo ""

echo "=== 若上述变量为空，请检查 .env 格式 ==="
echo "正确格式示例:"
echo "  NEXT_PUBLIC_SUPABASE_URL=https://xxx.supabase.co"
echo "  NEXT_PUBLIC_SUPABASE_ANON_KEY=eyJ..."
echo ""
echo "注意: 等号两侧不要有空格，值不要加引号"
