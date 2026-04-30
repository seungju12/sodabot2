#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
COMPOSE_FILE="$ROOT_DIR/docker-compose.yml"
ENV_FILE="$ROOT_DIR/.env"

usage() {
  cat <<'EOF'
Usage: ./scripts/ec2_migrate_sqlite.sh <sqlite-file> [--allow-non-empty]

동작:
  1. docker compose로 postgres 서비스 기동
  2. 임시 python 컨테이너에서 SQLite -> PostgreSQL 마이그레이션 실행
  3. 테이블별 row 검증 후 종료

예시:
  ./scripts/ec2_migrate_sqlite.sh /tmp/sodabot.sqlite3

주의:
  sqlite 파일은 읽기 전용으로 컨테이너에 마운트됩니다.
  기본적으로 대상 PostgreSQL 테이블이 비어 있어야 합니다.
EOF
}

if [[ $# -lt 1 ]]; then
  usage >&2
  exit 1
fi

SQLITE_SOURCE="$1"
shift

ALLOW_NON_EMPTY_ARGS=()
if [[ $# -gt 0 ]]; then
  if [[ "$1" == "--allow-non-empty" ]]; then
    ALLOW_NON_EMPTY_ARGS+=("--allow-non-empty")
    shift
  fi
fi

if [[ $# -gt 0 ]]; then
  usage >&2
  exit 1
fi

if [[ ! -f "$SQLITE_SOURCE" ]]; then
  echo "sqlite file not found: $SQLITE_SOURCE" >&2
  exit 1
fi

if [[ ! -f "$COMPOSE_FILE" ]]; then
  echo "docker-compose.yml not found: $COMPOSE_FILE" >&2
  exit 1
fi

if [[ ! -f "$ENV_FILE" ]]; then
  echo ".env not found: $ENV_FILE" >&2
  exit 1
fi

set -a
source "$ENV_FILE"
set +a

if [[ -z "${DATABASE_URL:-}" ]]; then
  echo "DATABASE_URL is not set in $ENV_FILE" >&2
  exit 1
fi

cd "$ROOT_DIR"

echo "=== postgres 시작 ==="
docker compose -f "$COMPOSE_FILE" up -d postgres

echo "=== SQLite -> PostgreSQL 마이그레이션 ==="
docker run --rm \
  --network host \
  -e DATABASE_URL="$DATABASE_URL" \
  -v "$ROOT_DIR:/workspace" \
  -v "$SQLITE_SOURCE:/sqlite/source.db:ro" \
  -w /workspace \
  python:3.12-slim \
  sh -lc "pip install --no-cache-dir 'psycopg[binary]>=3.2.1' >/tmp/pip.log && python scripts/migrate_sqlite_to_postgres.py --sqlite-path /sqlite/source.db ${ALLOW_NON_EMPTY_ARGS[*]}"