# SQLite -> PostgreSQL 이관 가이드

## 목적

- 기존 SQLite 기반 운영 EC2에서 데이터를 백업한 뒤 새 PostgreSQL 기반 EC2로 1회 이관한다.

## 사용 스크립트

- 기존 EC2:
  - [../../scripts/export_sqlite_backup.py](../../scripts/export_sqlite_backup.py)
- 새 EC2:
  - [../../scripts/ec2_migrate_sqlite.sh](../../scripts/ec2_migrate_sqlite.sh)
  - [../../scripts/migrate_sqlite_to_postgres.py](../../scripts/migrate_sqlite_to_postgres.py)

## 이관 원칙

- 기존 EC2는 SQLite 시점 코드를 그대로 유지해도 된다.
- 새 EC2는 PostgreSQL 전용 코드만으로 운영 가능하다.
- 실제 데이터 연결 고리는 SQLite 백업 파일 1개다.
- 최종 전환 직전에는 기존 EC2 bot을 중지한 뒤 마지막 백업을 떠야 한다.

## 기존 EC2 절차

1. 운영 SQLite 파일 경로를 확인한다.

```bash
find ~/ -type f \( -name "*.sqlite3" -o -name "*.db" \) 2>/dev/null
```

2. 최종 전환 직전에 기존 bot을 중지한다.
3. SQLite 백업을 생성한다.

```bash
python3 scripts/export_sqlite_backup.py --source 기존_SQLite_경로 --output /tmp/sodabot-final.sqlite3
```

4. 백업 파일을 새 EC2로 복사한다.

## 새 EC2 절차

1. PostgreSQL과 배포 환경만 먼저 준비한다.

```bash
./scripts/ec2_init.sh --skip-up
```

2. 비어 있는 PostgreSQL로 마이그레이션한다.

```bash
./scripts/ec2_migrate_sqlite.sh /tmp/sodabot-final.sqlite3 --reset-db-volume
```

3. 마이그레이션이 끝나면 bot을 기동한다.

```bash
./scripts/ec2_recreate.sh
```

## 옵션 설명

- `--reset-db-volume`
  - 기존 PostgreSQL 볼륨을 지우고 완전히 빈 DB로 다시 시작한 뒤 이관한다.
- `--allow-non-empty`
  - 대상 PostgreSQL에 이미 데이터가 있어도 강제로 넣는다.
  - 일반적인 교체 이관에서는 권장하지 않는다.

## 마이그레이션 후 검증

### 역할 설정 검증 키

- `auth_completed_role_id`
- `acquaintance_role_id`
- `onboarding_gender_male_role_id`
- `onboarding_gender_female_role_id`
- `onboarding_game_lol_role_id`
- `onboarding_game_overwatch_role_id`
- `onboarding_game_battlegrounds_role_id`
- `onboarding_game_other_role_id`
- `bot_role_id`
- `warning_role_1_id`
- `warning_role_2_id`
- `warning_role_3_id`

### 채널 설정 검증 키

- `warning_channel_id`
- `auth_channel_id`
- `onboarding_channel_id`
- `voice_create.trigger_channel_id`
- `voice_create.category_id`

### PostgreSQL에서 설정 직접 조회

역할 설정:

```bash
docker exec -it sodabot-postgres psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -P pager=off -c "
SELECT
  guild_id,
  split_part(key, ':', 3) AS config_key,
  trim(both '"' from value) AS role_id,
  updated_at
FROM config
WHERE split_part(key, ':', 3) LIKE '%role_id'
  AND trim(both '"' from value) <> '0'
ORDER BY guild_id, config_key;
"
```

채널 설정:

```bash
docker exec -it sodabot-postgres psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -P pager=off -c "
SELECT
  guild_id,
  split_part(key, ':', 3) AS config_key,
  trim(both '"' from value) AS channel_id,
  updated_at
FROM config
WHERE split_part(key, ':', 3) LIKE '%channel_id'
  AND trim(both '"' from value) <> '0'
ORDER BY guild_id, config_key;
"
```

### SQLite 백업본과 비교

```bash
sqlite3 /tmp/sodabot-final.sqlite3 "
SELECT key, value
FROM config
WHERE key LIKE '%role_id'
  AND value <> '"0"'
ORDER BY key;
"
```

## 정상 기준

- PostgreSQL `config` 테이블에 `g:<guild_id>:<key>` 형식으로 값이 저장되어 있어야 한다.
- 역할/채널 ID가 `"0"`이 아니고 기존 SQLite 값과 동일하면 설정 이관은 정상으로 본다.
- bot 기동 후 `/설정` 명령 및 실제 역할/채널 동작이 정상이어야 한다.