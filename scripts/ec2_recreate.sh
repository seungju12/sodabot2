#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
COMPOSE_FILE="$ROOT_DIR/docker-compose.yml"
ENV_FILE="$ROOT_DIR/.env"

DROP_DB_VOLUME=false
PULL_IMAGES=false

usage() {
  cat <<'EOF'
Usage: ./scripts/ec2_recreate.sh [options]

Options:
  --drop-db-volume   postgres 볼륨까지 삭제 후 완전히 새로 생성
  --pull             docker image pull 먼저 실행
  -h, --help         도움말 출력

기본 동작:
  1. 기존 compose 서비스 중지 및 제거
  2. bot 이미지 재빌드
  3. postgres, bot 재기동
  4. 상태와 bot 로그 일부 출력

주의:
  --drop-db-volume 옵션을 쓰면 postgres 데이터가 삭제됩니다.
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --drop-db-volume)
      DROP_DB_VOLUME=true
      shift
      ;;
    --pull)
      PULL_IMAGES=true
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown option: $1" >&2
      usage >&2
      exit 1
      ;;
  esac
done

if [[ ! -f "$COMPOSE_FILE" ]]; then
  echo "docker-compose.yml not found: $COMPOSE_FILE" >&2
  exit 1
fi

if [[ ! -f "$ENV_FILE" ]]; then
  echo ".env not found: $ENV_FILE" >&2
  exit 1
fi

if ! docker compose version >/dev/null 2>&1; then
  echo "docker compose plugin이 없습니다. 먼저 ./scripts/ec2_init.sh 를 다시 실행해 Compose plugin을 설치하세요." >&2
  exit 1
fi

cd "$ROOT_DIR"

echo "[1/5] docker compose config 확인"
docker compose config >/dev/null

if [[ "$PULL_IMAGES" == "true" ]]; then
  echo "[2/5] base image pull"
  docker compose pull postgres
else
  echo "[2/5] image pull 생략"
fi

echo "[3/5] 기존 서비스 정리"
if [[ "$DROP_DB_VOLUME" == "true" ]]; then
  docker compose down --remove-orphans --volumes
else
  docker compose down --remove-orphans
fi

echo "[4/5] bot 이미지 빌드"
docker compose build bot

echo "[5/5] postgres, bot 재기동"
docker compose up -d postgres bot

echo
echo "=== docker compose ps ==="
docker compose ps

echo
echo "=== bot logs (tail 80) ==="
docker compose logs --tail=80 bot