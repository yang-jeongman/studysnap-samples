# StudySnap Backend - 자기학습 PDF 변환 시스템

## 개요

StudySnap Backend는 PDF 문서를 모바일 최적화 HTML로 자동 변환하는 **자기학습 AI 시스템**입니다.
과거 4주간의 프로젝트 경험을 통합하여, 지속적으로 학습하고 성장하는 엔진으로 발전했습니다.

## 핵심 기술 스택

### 1. PDF 처리 엔진
- **PyMuPDF (fitz)**: PDF 파일 파싱 및 기본 정보 추출
- **Claude Vision (Sonnet 4.5)**: 고급 문서 구조 분석 및 콘텐츠 블록 자동 감지
- **Pillow**: 이미지 처리 및 최적화

### 2. AI 엔진
- **Claude Vision API**: 문서 레이아웃 및 콘텐츠 자동 인식
- **자기학습 AI 에이전트**: 변환 패턴 학습 및 품질 개선
- **지능형 레이아웃 엔진**: 모바일 최적 배치 자동 결정

### 3. 보안 시스템
- **API 키 관리**: 암호화된 키 저장 및 검증
- **접근 제어**: 권한 기반 리소스 접근
- **감사 로깅**: 모든 작업 추적 및 기록
- **데이터 암호화**: Fernet 암호화 (AES-128)

### 4. 웹 프레임워크
- **FastAPI**: 고성능 비동기 웹 서버
- **Uvicorn**: ASGI 서버
- **Jinja2**: HTML 템플릿 엔진

---

## 시스템 아키텍처

```
┌─────────────────────────────────────────────────────────────┐
│                      FastAPI Application                     │
│                         (app.py)                             │
└──────────────────────┬──────────────────────────────────────┘
                       │
       ┌───────────────┼───────────────┐
       │               │               │
       ▼               ▼               ▼
┌──────────┐    ┌──────────┐    ┌──────────┐
│  Vision  │    │  Layout  │    │    AI    │
│   PDF    │    │ Optimizer│    │  Agent   │
│Processor │    │  Engine  │    │  Engine  │
└──────────┘    └──────────┘    └──────────┘
       │               │               │
       └───────────────┼───────────────┘
                       │
                       ▼
              ┌─────────────────┐
              │  Engine API     │
              │   (통합 API)     │
              └─────────────────┘
                       │
       ┌───────────────┼───────────────┐
       │               │               │
       ▼               ▼               ▼
┌──────────┐    ┌──────────┐    ┌──────────┐
│ Security │    │ Knowledge│    │  Audit   │
│  Manager │    │   Base   │    │   Logs   │
└──────────┘    └──────────┘    └──────────┘
```

---

## 주요 모듈

### 1. Vision PDF Processor (`vision_pdf_processor.py`)
**과거 프로젝트 통합: vision_content_detector + advanced_pdf_analyzer**

**기능:**
- Claude Vision을 통한 콘텐츠 블록 자동 감지
- 선거 공보물, 뉴스레터, 일반 문서 타입별 최적화 분석
- 이미지 자동 리사이징 및 압축 (5MB 제한)
- 정확한 픽셀 좌표 기반 레이아웃 추출

**주요 메서드:**
```python
detect_content_blocks(image_path, content_type) -> Dict
analyze_document_structure(image_path, content_type) -> Dict
encode_image_to_base64(image_path, max_size_mb) -> Tuple
```

### 2. Advanced Layout Optimizer (`advanced_layout_optimizer.py`)
**과거 프로젝트 통합: ai_layout_optimizer + intelligent_layout_engine**

**기능:**
- 블록 자동 분석 및 분류 (제목, 본문, 이미지, 아이콘)
- 지능형 섹션 그룹화 (Y 좌표, 폰트 크기, 간격 기반)
- 모바일 최적화 레이아웃 전략 자동 선택
- 컬러 팔레트 자동 적용 (문서 타입별)
- Vision 분석 결과 통합

**섹션 타입:**
- HERO: 큰 제목 + 메인 이미지
- TITLE: 제목 섹션
- CONTENT: 콘텐츠 섹션
- IMAGE: 이미지 섹션
- LIST: 리스트 섹션
- CARD: 카드 섹션
- FOOTER: 푸터 섹션

### 3. Self-Learning AI Agent (`pdf_ai_agent.py`)

**기능:**
- 변환 패턴 자동 학습 및 저장
- 품질 점수 기반 성공률 추적
- 동적 룰 생성 및 개선
- 사용자 피드백 반영
- 학습 인사이트 제공

**학습 프로세스:**
```
PDF 분석 → 패턴 매칭 → 변환 실행 → 품질 평가 → 학습 기록 → 패턴 업데이트
```

### 4. Engine Security Manager (`engine_security.py`)

**기능:**
- API 키 생성 및 관리 (암호화 저장)
- 권한 기반 접근 제어
- 감사 로그 자동 기록 (10,000개 유지)
- 데이터 암호화/복호화 (Fernet)
- 보안 리포트 생성

**보안 흐름:**
```
API 요청 → 키 검증 → 권한 확인 → 작업 실행 → 감사 로그 → 응답
```

### 5. Modular Engine API (`engine_api.py`)

**기능:**
- 재사용 가능한 엔진 인터페이스
- 엔진 레지스트리 관리
- 통합 API 제공
- 인증 및 감사 로그 자동 처리

**지원 엔진:**
- Layout Engine: 레이아웃 자동 최적화
- AI Agent Engine: 자기학습 에이전트
- Security Engine: 보안 및 접근 제어

---

## 사용 방법

### 1. 기본 PDF 변환

```python
from engine_api import get_engine_api, EngineType

# 엔진 API 초기화
engine_api = get_engine_api(require_authentication=False)

# PDF 데이터 준비
pdf_data = {
    "structured_data": {...},
    "content_type": "election"
}

# 레이아웃 엔진 사용
result = engine_api.use_engine(
    engine_type=EngineType.LAYOUT,
    input_data=pdf_data
)

print(result['layout_structure'])
```

### 2. Vision 분석 활용

```python
from vision_pdf_processor import get_vision_processor

# Vision 프로세서 초기화
processor = get_vision_processor(api_key="your-key")

# 콘텐츠 블록 감지
blocks = processor.detect_content_blocks(
    image_path="page_1.png",
    content_type="election"
)

# 문서 구조 분석
structure = processor.analyze_document_structure(
    image_path="page_1.png",
    content_type="election"
)
```

### 3. AI 에이전트 학습

```python
from pdf_ai_agent import get_ai_agent

# AI 에이전트 초기화
agent = get_ai_agent()

# PDF 분석
analysis = agent.analyze_pdf(pdf_data, content_type="election")

# 변환 결과로부터 학습
agent.learn_from_conversion(
    pdf_data=pdf_bytes,
    conversion_result=result,
    user_feedback={"rating": 5, "comments": "완벽합니다"}
)

# 학습 인사이트 확인
insights = agent.get_learning_insights()
print(f"총 변환 횟수: {insights['statistics']['total_conversions']}")
print(f"평균 품질 점수: {insights['statistics']['avg_quality_score']:.2f}")
```

### 4. 보안 API 키 생성

```python
from engine_security import get_security_manager

# 보안 관리자 초기화
security = get_security_manager()

# API 키 생성
api_key = security.create_api_key(
    name="프로덕션 키",
    permissions=["use_layout", "use_ai_agent"],
    expires_in_days=90
)

print(f"생성된 API 키: {api_key}")
```

### 5. 인증 모드로 엔진 사용

```python
from engine_api import get_engine_api, EngineType

# 인증 모드 활성화
engine_api = get_engine_api(require_authentication=True)

# API 키로 엔진 사용
result = engine_api.use_engine(
    engine_type=EngineType.LAYOUT,
    input_data=pdf_data,
    api_key="your-generated-api-key"
)
```

---

## 학습 데이터 구조

### 변환 패턴 (`ConversionPattern`)
```python
{
    "pattern_id": "pattern_election_0",
    "pdf_type": "election",
    "object_types": ["profile", "pledges", "career"],
    "layout_structure": {...},
    "success_rate": 0.92,
    "usage_count": 150,
    "created_at": "2025-12-02T10:00:00",
    "last_used": "2025-12-02T15:30:00"
}
```

### 학습 기록 (`LearningRecord`)
```python
{
    "record_id": "lr_20251202_123456_abc12345",
    "pdf_hash": "sha256_hash",
    "conversion_result": {...},
    "user_feedback": {"rating": 5, "is_satisfied": true},
    "quality_score": 0.95,
    "timestamp": "2025-12-02T12:34:56",
    "improvements": ["후보자 이름 인식 개선 필요"]
}
```

---

## 보안 체계

### 1. API 키 관리
- 마스터 키로 암호화된 저장소
- SHA-256 해시로 키 검증
- 만료일 자동 체크
- 사용 통계 추적

### 2. 권한 시스템
```python
permissions = [
    "admin",              # 모든 권한
    "use_layout",         # 레이아웃 엔진 사용
    "use_ai_agent",       # AI 에이전트 사용
    "create_api_key",     # API 키 생성
    "view_audit_logs"     # 감사 로그 조회
]
```

### 3. 감사 로그
모든 작업이 자동 기록됨:
- 타임스탬프
- API 키 ID
- 작업 유형 (use_engine, create_api_key 등)
- 리소스 (layout, ai_agent 등)
- 성공/실패 여부
- IP 주소 (선택)
- 상세 정보

---

## 디렉토리 구조

```
c:\StudySnap-Backend\
├── app.py                          # FastAPI 메인 애플리케이션
├── vision_pdf_processor.py         # Vision 기반 PDF 처리
├── advanced_layout_optimizer.py    # 고급 레이아웃 최적화
├── intelligent_layout_engine.py    # 지능형 레이아웃 엔진
├── pdf_ai_agent.py                 # 자기학습 AI 에이전트
├── engine_security.py              # 보안 관리 시스템
├── engine_api.py                   # 모듈화된 엔진 API
├── ai_knowledge/                   # AI 학습 데이터
│   ├── patterns.pkl               # 변환 패턴
│   ├── learning_records.pkl       # 학습 기록
│   └── rules.json                 # 동적 룰
├── security_config/                # 보안 설정
│   ├── .master_key                # 마스터 암호화 키
│   ├── api_keys.enc               # 암호화된 API 키
│   └── audit_logs.enc             # 암호화된 감사 로그
├── uploads/                        # 업로드된 PDF 파일
├── outputs/                        # 생성된 HTML 파일
└── static/                         # 정적 파일
    ├── editor.html                # HTML 에디터
    └── ...
```

---

## 성능 최적화

### 1. 이미지 처리
- 자동 리사이징 (5MB 제한)
- JPEG 압축 (품질 95 → 동적 조정)
- Pillow LANCZOS 리샘플링

### 2. 캐싱
- 싱글톤 패턴으로 엔진 인스턴스 재사용
- 학습 데이터 메모리 캐시
- 최근 1000개 학습 기록만 유지

### 3. 비동기 처리
- FastAPI 비동기 엔드포인트
- Uvicorn ASGI 서버

---

## 확장성

### 새로운 엔진 추가 방법

1. `BaseEngine` 인터페이스 구현:
```python
from engine_api import BaseEngine, EngineInfo

class MyCustomEngine(BaseEngine):
    def get_info(self) -> EngineInfo:
        return EngineInfo(...)

    def validate_input(self, input_data: Any) -> bool:
        return True

    def process(self, input_data: Any, **kwargs) -> Any:
        # 처리 로직
        return result
```

2. 엔진 레지스트리에 등록:
```python
from engine_api import EngineType, get_engine_api

engine_api = get_engine_api()
engine_api.registry.register_engine(
    EngineType.CUSTOM,
    MyCustomEngine()
)
```

---

## 모니터링

### 통계 확인
```python
# AI 에이전트 통계
insights = agent.get_learning_insights()
print(f"총 변환: {insights['statistics']['total_conversions']}")
print(f"성공률: {insights['statistics']['successful_conversions']}")
print(f"학습 패턴: {insights['statistics']['patterns_learned']}")

# 보안 리포트
report = security.get_security_report()
print(f"활성 API 키: {report['active_api_keys']}")
print(f"최근 활동: {len(report['recent_activities'])}")
```

---

## 결론

StudySnap Backend는 **과거 4주간의 프로젝트 경험을 통합**하여 만든 **자기학습 PDF 변환 시스템**입니다.

**핵심 특징:**
1. ✅ **자기학습**: 변환할수록 품질이 향상됨
2. ✅ **보안**: 암호화, 인증, 감사 로그로 보호됨
3. ✅ **모듈화**: 재사용 가능한 엔진 API
4. ✅ **확장성**: 새로운 엔진 쉽게 추가 가능
5. ✅ **고성능**: Vision AI + 지능형 레이아웃 최적화

**과거 프로젝트 기술 통합:**
- `vision_content_detector.py` → `vision_pdf_processor.py`
- `ai_layout_optimizer.py` → `advanced_layout_optimizer.py`
- `advanced_pdf_analyzer.py` → Vision 기능 통합

이제 모든 PDF 변환 서비스에서 **이 엔진을 재사용**할 수 있으며,
**외부 유출 방지 보안**으로 핵심 기술이 보호됩니다.
