# 🔄 작업 이어하기 프롬프트

다음 세션에서 작업을 이어서 진행하려면 아래 프롬프트를 복사하여 사용하세요.

---

## 📋 기본 이어하기 프롬프트

```
이전 세션에서 StudySnap Backend 프로젝트 작업을 진행했습니다.

작업 내용:
1. 선거 공보물(나경원 후보) PDF를 모바일 최적화 HTML로 변환
2. 자기학습 PDF AI 에이전트 시스템 구축
3. 보안 레이어 구현 (암호화, 인증, 감사 로그)
4. 모듈화된 엔진 API 아키텍처 구축
5. 과거 4주간 프로젝트 기술 통합

생성된 핵심 파일:
- pdf_ai_agent.py (자기학습 AI 에이전트)
- engine_security.py (보안 관리 시스템)
- engine_api.py (모듈화된 통합 API)
- vision_pdf_processor.py (Vision PDF 처리)
- advanced_layout_optimizer.py (고급 레이아웃 최적화)

현재 상태 확인: PROJECT_STATUS.md
시스템 아키텍처: SYSTEM_ARCHITECTURE.md

이어서 작업을 진행해주세요.
```

---

## 🎯 구체적인 작업별 프롬프트

### 1. app.py에 새 엔진 통합하기

```
이전 세션에서 만든 PDF AI 엔진들을 app.py에 통합해주세요.

통합할 엔진:
- vision_pdf_processor.py
- advanced_layout_optimizer.py
- pdf_ai_agent.py
- engine_security.py
- engine_api.py

app.py에 다음 기능을 추가해주세요:
1. /api/analyze-vision 엔드포인트 (Vision 분석)
2. /api/optimize-layout 엔드포인트 (레이아웃 최적화)
3. /api/ai-agent/learn 엔드포인트 (AI 학습)
4. /api/ai-agent/insights 엔드포인트 (학습 인사이트)
```

### 2. 테스트 코드 작성

```
이전 세션에서 만든 PDF AI 엔진들의 테스트 코드를 작성해주세요.

테스트 대상:
- pdf_ai_agent.py: 학습 기능, 패턴 매칭, 품질 점수 계산
- engine_security.py: API 키 생성/검증, 권한 확인, 암호화
- engine_api.py: 엔진 등록, 통합 API 호출
- vision_pdf_processor.py: 이미지 인코딩, 블록 감지
- advanced_layout_optimizer.py: 블록 분석, 섹션 그룹화

pytest 형식으로 tests/ 폴더에 작성해주세요.
```

### 3. Docker 컨테이너화

```
이전 세션에서 만든 StudySnap Backend를 Docker로 컨테이너화 해주세요.

필요한 파일:
- Dockerfile
- docker-compose.yml
- .dockerignore

고려사항:
- Python 3.11 기반
- 필요한 의존성 설치
- 볼륨 마운트 (ai_knowledge, security_config, outputs)
- 환경 변수 설정
```

### 4. 다른 문서 타입 지원 추가

```
이전 세션에서 만든 PDF AI 시스템에 새로운 문서 타입 지원을 추가해주세요.

추가할 문서 타입:
1. 이력서 (resume)
2. 계약서 (contract)
3. 보고서 (report)

각 타입별로:
- vision_pdf_processor.py에 분석 프롬프트 추가
- advanced_layout_optimizer.py에 레이아웃 전략 추가
- 적절한 색상 팔레트 정의
```

### 5. 관리자 대시보드 개발

```
이전 세션에서 만든 PDF AI 시스템의 관리자 대시보드를 개발해주세요.

대시보드 기능:
1. AI 학습 통계 시각화 (총 변환 수, 성공률, 품질 점수)
2. API 키 관리 UI (생성, 조회, 비활성화)
3. 감사 로그 조회
4. 보안 리포트

기술 스택:
- FastAPI 템플릿 (Jinja2)
- Chart.js (차트)
- Bootstrap 5 (UI)
```

---

## 🔧 특정 파일 수정 프롬프트

### vision_pdf_processor.py 수정

```
vision_pdf_processor.py 파일을 수정해주세요.

수정 내용:
[수정하고 싶은 내용 작성]

파일 위치: c:\StudySnap-Backend\vision_pdf_processor.py
```

### pdf_ai_agent.py 수정

```
pdf_ai_agent.py 파일을 수정해주세요.

수정 내용:
[수정하고 싶은 내용 작성]

파일 위치: c:\StudySnap-Backend\pdf_ai_agent.py
```

### engine_security.py 수정

```
engine_security.py 파일을 수정해주세요.

수정 내용:
[수정하고 싶은 내용 작성]

파일 위치: c:\StudySnap-Backend\engine_security.py
```

---

## 🐛 버그 수정 프롬프트

```
StudySnap Backend에서 다음 오류가 발생했습니다.

오류 메시지:
[오류 메시지 붙여넣기]

발생 파일:
[파일명]

재현 방법:
[오류 재현 방법]

관련 파일 확인 후 수정해주세요.
프로젝트 상태: PROJECT_STATUS.md 참고
```

---

## 📊 상태 확인 프롬프트

```
StudySnap Backend 프로젝트의 현재 상태를 확인하고 보고해주세요.

확인 항목:
1. 모든 엔진 파일이 정상적으로 존재하는지
2. app.py와의 통합 상태
3. 의존성 설치 상태
4. 보안 설정 상태

PROJECT_STATUS.md 파일을 최신 상태로 업데이트해주세요.
```

---

## 🚀 프로덕션 배포 프롬프트

```
StudySnap Backend를 프로덕션 환경에 배포할 준비를 해주세요.

필요한 작업:
1. 환경 변수 설정 (.env 파일)
2. 프로덕션용 설정 분리
3. 보안 점검 (마스터 키 교체, HTTPS 설정 등)
4. 배포 가이드 문서 작성
5. 헬스체크 엔드포인트 추가
```

---

## 📝 참고 정보

### 프로젝트 경로
```
c:\StudySnap-Backend\
```

### 핵심 파일 위치
```
c:\StudySnap-Backend\app.py                    # FastAPI 메인
c:\StudySnap-Backend\pdf_ai_agent.py           # AI 에이전트
c:\StudySnap-Backend\engine_security.py        # 보안 시스템
c:\StudySnap-Backend\engine_api.py             # 통합 API
c:\StudySnap-Backend\vision_pdf_processor.py   # Vision 처리
c:\StudySnap-Backend\advanced_layout_optimizer.py  # 레이아웃 최적화
c:\StudySnap-Backend\intelligent_layout_engine.py  # 레이아웃 엔진
c:\StudySnap-Backend\PROJECT_STATUS.md         # 프로젝트 상태
c:\StudySnap-Backend\SYSTEM_ARCHITECTURE.md    # 시스템 아키텍처
```

### 과거 프로젝트 참조
```
C:\Users\jmyang\Dropbox\배정우-더소통\StudySnap\src\
C:\Users\jmyang\Dropbox\배정우-더소통\더소통\newsletter_converter\
```
