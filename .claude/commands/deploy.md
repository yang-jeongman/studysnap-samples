---
description: "Railway 또는 서버 배포"
---

프로젝트를 배포합니다.

## 배포 대상
$ARGUMENTS

## Railway 배포 절차
1. 환경변수 확인 (ANTHROPIC_API_KEY 등)
2. requirements.txt 최신화
3. Procfile 확인
4. git commit 및 push
5. Railway 상태 확인

## 원격 서버 배포 (SSH)
1. SSH 접속: ssh jmyang@115.21.251.90
2. git pull
3. 서비스 재시작: sudo systemctl restart kmart

## 필요 파일
- Procfile: web: gunicorn app:app
- railway.json: 빌드/배포 설정
- requirements.txt: 의존성 목록

## 환경변수 (Railway)
```
ANTHROPIC_API_KEY=sk-ant-...
TRIAL_DAYS=15
DAILY_CONVERT_LIMIT=10
PORT=8000
```

배포 전 체크리스트를 확인하고 진행해주세요.
