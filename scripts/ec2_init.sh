#!/usr/bin/env bash

set -euo pipefail

REPO_URL="https://github.com/seungju12/sodabot2.git"
APP_DIR="$HOME/sodabot2"
BRANCH="main"
ENV_SOURCE=""
SKIP_UP=false
DEFAULT_ENV_SOURCE="/tmp/.env"
COMPOSE_FILE_NAME="docker-compose.yml"

compose_arch() {
  case "$(uname -m)" in
    x86_64|amd64)
      printf '%s' 'x86_64'
      ;;
    aarch64|arm64)
      printf '%s' 'aarch64'
      ;;
    *)
      return 1
      ;;
  esac
}

usage() {
  cat <<'EOF'
Usage: ./scripts/ec2_init.sh [options]

Options:
  --app-dir <path>     배포 디렉터리 (기본: ~/sodabot2)
  --env-source <path>  서버에 둘 .env 파일 원본 경로
  --skip-up            설치/clone까지만 하고 docker compose up은 생략
  -h, --help           도움말 출력

동작:
  1. docker, git 설치
  2. docker 서비스 활성화
  3. 저장소 clone 또는 pull
  4. .env 준비
  5. docker compose up -d --build 실행

예시:
  ./scripts/ec2_init.sh
  ./scripts/ec2_init.sh --env-source /tmp/.env

주의:
  기본 저장소: https://github.com/seungju12/sodabot2.git
  기본 브랜치: main
  --env-source를 주지 않아도 /tmp/.env가 있으면 자동으로 사용합니다.
  .env가 없으면 필요한 값을 입력받아 생성합니다.
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --app-dir)
      APP_DIR="$2"
      shift 2
      ;;
    --env-source)
      ENV_SOURCE="$2"
      shift 2
      ;;
    --skip-up)
      SKIP_UP=true
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

install_docker_and_git() {
  if command -v dnf >/dev/null 2>&1; then
    sudo dnf install -y git docker
  elif command -v yum >/dev/null 2>&1; then
    sudo yum install -y git docker
  elif command -v apt-get >/dev/null 2>&1; then
    sudo apt-get update -y
    sudo apt-get install -y git docker.io docker-compose-plugin
  else
    echo "지원되지 않는 패키지 매니저입니다. docker/git를 수동 설치해주세요." >&2
    exit 1
  fi

  sudo systemctl enable --now docker
  sudo usermod -aG docker "$USER" || true
}

ensure_downloader() {
  if command -v curl >/dev/null 2>&1 || command -v wget >/dev/null 2>&1; then
    return
  fi

  if command -v dnf >/dev/null 2>&1; then
    sudo dnf install -y wget
  elif command -v yum >/dev/null 2>&1; then
    sudo yum install -y wget
  elif command -v apt-get >/dev/null 2>&1; then
    sudo apt-get update -y
    sudo apt-get install -y wget
  else
    echo "curl 또는 wget이 필요합니다. 수동으로 설치해주세요." >&2
    exit 1
  fi
}

download_compose_plugin() {
  local url="$1"
  local output_path="$2"

  if command -v curl >/dev/null 2>&1; then
    sudo curl -fL "$url" -o "$output_path"
    return
  fi

  if command -v wget >/dev/null 2>&1; then
    sudo wget -O "$output_path" "$url"
    return
  fi

  echo "docker compose plugin 다운로드 도구가 없습니다." >&2
  exit 1
}

install_compose_plugin() {
  if docker compose version >/dev/null 2>&1; then
    return
  fi

  ensure_downloader

  if command -v dnf >/dev/null 2>&1; then
    sudo dnf install -y docker-compose-plugin >/dev/null 2>&1 || true
  elif command -v yum >/dev/null 2>&1; then
    sudo yum install -y docker-compose-plugin >/dev/null 2>&1 || true
  elif command -v apt-get >/dev/null 2>&1; then
    sudo apt-get update -y >/dev/null 2>&1 || true
    sudo apt-get install -y docker-compose-plugin >/dev/null 2>&1 || true
  fi

  if docker compose version >/dev/null 2>&1; then
    return
  fi

  local arch
  if ! arch="$(compose_arch)"; then
    echo "지원되지 않는 아키텍처입니다. Docker Compose plugin을 수동 설치해주세요: $(uname -m)" >&2
    exit 1
  fi

  sudo mkdir -p /usr/local/lib/docker/cli-plugins
  download_compose_plugin \
    "https://github.com/docker/compose/releases/latest/download/docker-compose-linux-${arch}" \
    "/usr/local/lib/docker/cli-plugins/docker-compose"
  sudo chmod +x /usr/local/lib/docker/cli-plugins/docker-compose
}

ensure_compose_available() {
  install_compose_plugin

  if docker compose version >/dev/null 2>&1; then
    return
  fi
  echo "docker compose plugin 설치에 실패했습니다. 네트워크 또는 권한 상태를 확인해주세요." >&2
  exit 1
}

prepare_repo() {
  local parent_dir
  parent_dir="$(dirname "$APP_DIR")"
  mkdir -p "$parent_dir"

  if [[ -d "$APP_DIR/.git" ]]; then
    git -C "$APP_DIR" fetch origin
    git -C "$APP_DIR" checkout "$BRANCH"
    git -C "$APP_DIR" pull --ff-only origin "$BRANCH"
    return
  fi

  if [[ -d "$APP_DIR" ]]; then
    echo "디렉터리가 이미 존재하지만 git 저장소가 아닙니다: $APP_DIR" >&2
    exit 1
  fi

  git clone --branch "$BRANCH" "$REPO_URL" "$APP_DIR"
}

prompt_with_default() {
  local prompt="$1"
  local default_value="$2"
  local result
  read -r -p "$prompt [$default_value]: " result
  if [[ -z "$result" ]]; then
    result="$default_value"
  fi
  printf '%s' "$result"
}

create_env_interactively() {
  if [[ ! -t 0 ]]; then
    echo ".env 파일이 없고 현재 터미널이 인터랙티브하지 않습니다." >&2
    echo "--env-source 옵션으로 .env 파일 경로를 전달하세요." >&2
    exit 1
  fi

  local discord_token
  local postgres_db
  local postgres_user
  local postgres_password
  local postgres_port
  local timezone

  echo "운영용 .env 파일을 생성합니다."
  read -r -p "DISCORD_TOKEN: " discord_token
  if [[ -z "$discord_token" ]]; then
    echo "DISCORD_TOKEN은 비워둘 수 없습니다." >&2
    exit 1
  fi
  postgres_db="$(prompt_with_default 'POSTGRES_DB' 'sodabot')"
  postgres_user="$(prompt_with_default 'POSTGRES_USER' 'sodabot')"
  read -r -s -p "POSTGRES_PASSWORD: " postgres_password
  echo
  if [[ -z "$postgres_password" ]]; then
    echo "POSTGRES_PASSWORD는 비워둘 수 없습니다." >&2
    exit 1
  fi
  postgres_port="$(prompt_with_default 'POSTGRES_PORT' '5432')"
  timezone="$(prompt_with_default 'TZ' 'Asia/Seoul')"

  cat > "$APP_DIR/.env" <<EOF
DISCORD_TOKEN=$discord_token
POSTGRES_DB=$postgres_db
POSTGRES_USER=$postgres_user
POSTGRES_PASSWORD=$postgres_password
POSTGRES_PORT=$postgres_port
TZ=$timezone
DATABASE_URL=postgresql://$postgres_user:$postgres_password@localhost:$postgres_port/$postgres_db
EOF
}

prepare_env() {
  if [[ -z "$ENV_SOURCE" && -f "$DEFAULT_ENV_SOURCE" ]]; then
    ENV_SOURCE="$DEFAULT_ENV_SOURCE"
  fi

  if [[ -n "$ENV_SOURCE" ]]; then
    if [[ ! -f "$ENV_SOURCE" ]]; then
      echo "env source file not found: $ENV_SOURCE" >&2
      exit 1
    fi
    echo ".env 파일을 복사합니다: $ENV_SOURCE -> $APP_DIR/.env"
    cp "$ENV_SOURCE" "$APP_DIR/.env"
  fi

  if [[ ! -f "$APP_DIR/.env" ]]; then
    create_env_interactively
  fi
}

compose_file_path() {
  printf '%s' "$APP_DIR/$COMPOSE_FILE_NAME"
}

install_docker_and_git
ensure_compose_available
prepare_repo
prepare_env

cd "$APP_DIR"

if [[ ! -f "$(compose_file_path)" ]]; then
  echo "compose file not found: $(compose_file_path)" >&2
  echo "저장소 루트에 $COMPOSE_FILE_NAME 이 있어야 합니다." >&2
  exit 1
fi

echo "=== docker compose config ==="
docker compose -f "$(compose_file_path)" config >/dev/null

if [[ "$SKIP_UP" == "true" ]]; then
  echo "초기화 완료. docker compose up은 생략했습니다."
  exit 0
fi

echo "=== docker compose up -d --build ==="
docker compose -f "$(compose_file_path)" up -d --build

echo
echo "=== docker compose ps ==="
docker compose -f "$(compose_file_path)" ps

echo
echo "=== bot logs (tail 80) ==="
docker compose -f "$(compose_file_path)" logs --tail=80 bot