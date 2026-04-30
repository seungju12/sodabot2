# EC2 배포 가이드

## 목적

- 새 EC2 인스턴스에서 소다봇을 Docker Compose 기반으로 배포한다.
- 운영 재배포 시 같은 절차를 반복 가능하도록 표준화한다.

## 전제 조건

- `.env` 파일이 준비되어 있어야 한다.
- `DATABASE_URL`이 PostgreSQL 연결 문자열로 설정되어 있어야 한다.
- Docker, Compose plugin, Buildx plugin이 설치 가능해야 한다.

## 사용 스크립트

- [../../scripts/ec2_init.sh](../../scripts/ec2_init.sh)
  - Docker, Compose plugin, Buildx plugin 설치/검증
  - 저장소 clone 또는 pull
  - `.env` 준비
  - `--skip-up` 사용 시 기동 생략
- [../../scripts/ec2_recreate.sh](../../scripts/ec2_recreate.sh)
  - 기존 서비스를 정리하고 bot 이미지를 재빌드 후 postgres, bot 재기동

## 초기 배포 절차

1. `.env` 파일을 서버에 준비한다.
2. 설치 및 배포 환경 준비를 실행한다.

```bash
./scripts/ec2_init.sh
```

3. 설치만 먼저 하고 기동은 나중에 하려면 아래처럼 실행한다.

```bash
./scripts/ec2_init.sh --skip-up
```

## 재배포 절차

```bash
./scripts/ec2_recreate.sh
```

옵션:

- DB 볼륨까지 완전히 비우려면:

```bash
./scripts/ec2_recreate.sh --drop-db-volume
```

- base image를 먼저 pull 하려면:

```bash
./scripts/ec2_recreate.sh --pull
```

## 점검 명령

```bash
docker compose ps
docker compose logs --tail=80 bot
docker compose logs --tail=80 postgres
```

## 운영 메모

- `docker-compose.yml` 기준 서비스는 `postgres`, `bot` 두 개다.
- bot은 Compose 내부에서 `postgres` 호스트로 PostgreSQL에 연결한다.
- EC2에서 수동 수정한 스크립트가 있으면 `git pull` 전에 정리해야 한다.