---
description: "서버 실행 및 API 테스트"
---

Flask 서버를 실행하고 API를 테스트합니다.

## 테스트 대상
$ARGUMENTS

## 테스트 절차
1. 기존 Python 프로세스 확인 및 정리
2. Flask 서버 시작 (python app.py)
3. Health check 실행
4. 요청된 API 테스트

## 주요 엔드포인트
- GET /health - 헬스체크
- POST /api/church-convert-ai - 교회 주보 변환
- POST /api/election-convert-ai - 선거 공보물 변환
- POST /api/license/create-trial - 체험판 라이선스

## 서버 정보
- 기본 포트: 8000
- 테스트 URL: http://localhost:8000

서버 상태를 확인하고 테스트를 실행해주세요.
