# SodaBot

소다봇 요구사항 정의서를 기준으로 만든 Python(discord.py) 기반 구현 예시입니다.

## 포함 기능
- `/경고 부여 [유저] [사유]`
- `/경고 회수 [유저] [사유]`
- `/경고 조회 [유저]`
- 자동 경고 (`AUTO_ADD`)
- 경고 3회 도달 시 자동 kick
- 경고 로그 임베드 출력
- 인증 기간 종료 3일 전 안내
- 자동 경고 후 `인증 완료` 역할 초기화
- LVP 임시 개인 음성 채널 생성 / 자동 삭제
- `/설정 ...` 명령어 기반 런타임 설정 변경
- SQLite 기반 저장소 + 메모리 캐시

## 실행 방법
```bash
python -m venv .venv
source .venv/bin/activate  # Windows는 .venv\\Scripts\\activate
pip install -r requirements.txt
cp .env.example .env
python main.py
```

## 최초 설정
1. `.env`에 Discord Bot Token 입력
2. `config/default_config.json` 또는 `/설정` 명령어로 ID 입력
3. 봇에 다음 권한 필요
   - Manage Roles
   - Kick Members
   - Move Members
   - Manage Channels
   - Send Messages / Embed Links
   - Use Application Commands

## 주의
- 실제 운영 전 테스트 서버에서 역할/채널 ID를 먼저 검증해야 합니다.
- 슬래시 명령어 동기화는 최초 실행 시 수 초~수 분 걸릴 수 있습니다.
