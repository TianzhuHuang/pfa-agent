#!/usr/bin/env bash
# 将本地 PFA 代码同步到阿里云 ECS（避免在 ECS 上 git pull 超时）
# 用法: ./scripts/sync-to-aliyun.sh [root@ECS公网IP]
#   或: ALIYUN_HOST=1.2.3.4 ./scripts/sync-to-aliyun.sh
set -e
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_ROOT"

if [ -n "$1" ]; then
  DEST="$1"
elif [ -n "$ALIYUN_HOST" ]; then
  DEST="root@${ALIYUN_HOST}"
else
  echo "Usage: $0 [root@ECS公网IP]"
  echo "   or: ALIYUN_HOST=ECS公网IP $0"
  exit 1
fi

echo "Syncing to $DEST:/opt/pfa/ (excluding .git, node_modules, .next, __pycache__, .env)"
rsync -avz \
  --exclude .git \
  --exclude node_modules \
  --exclude .next \
  --exclude '__pycache__' \
  --exclude .env \
  --exclude .cursor \
  . "$DEST:/opt/pfa/"

echo "Done. SSH to ECS and run: cd /opt/pfa && docker compose --env-file .env up -d --build"
