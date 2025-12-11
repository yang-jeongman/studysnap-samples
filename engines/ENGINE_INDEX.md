# StudySnap 엔진 인덱스

## 디렉토리 구조

```
C:\StudySnap-Backend\
├── engines/                          # 엔진 모듈 디렉토리
│   ├── __init__.py                   # 메인 진입점
│   ├── ENGINE_INDEX.md               # 이 문서
│   │
│   ├── common/                       # 공통 엔진 (모든 카테고리에서 사용)
│   │   ├── __init__.py
│   │   └── (기존 모듈들을 import)
│   │
│   ├── election/                     # 선거 홍보물 특화 [구현됨]
│   │   └── __init__.py
│   │
│   ├── church/                       # 교회 주보 특화 [구현됨]
│   │   └── __init__.py
│   │
│   ├── lecture/                      # 대학 강의 자료 [부분 구현]
│   │   └── __init__.py
│   │
│   ├── newsletter/                   # 지자체 소식지 [예정]
│   │   └── __init__.py
│   │
│   ├── catalog/                      # 기업 카탈로그 [예정]
│   │   └── __init__.py
│   │
│   └── language/                     # 외국어 학습기 [예정]
│       └── __init__.py
│
├── vision_ocr.py                     # [공통] Claude Vision OCR
├── universal_parser.py               # [공통] 범용 PDF/이미지 파서
├── pdf_converter.py                  # [공통] PDF 변환 기본 엔진
├── vision_pdf_processor.py           # [공통] Vision 기반 PDF 처리
├── verification_system.py            # [공통] 변환 품질 검증
├── learning_system.py                # [공통] AI 학습 시스템
├── template_engine.py                # [공통] 템플릿 렌더링 엔진
├── localization.py                   # [공통] 다국어 지원
├── intelligent_layout_engine.py      # [공통] 지능형 레이아웃
├── advanced_layout_optimizer.py      # [공통] 레이아웃 최적화
│
├── auto_election_converter.py        # [선거] 선거 홍보물 자동 변환
├── html_generator.py                 # [선거] 선거 HTML 생성기
│
├── church_html_generator.py          # [교회] 교회 주보 HTML 생성기
│
└── lecture_generator.py              # [강의] 강의 자료 생성기
```

---

## 공통 엔진 (engines/common/)

모든 카테고리에서 공통으로 사용되는 핵심 엔진입니다.

### 핵심 모듈

| 모듈 | 설명 | 주요 클래스 |
|------|------|------------|
| `vision_ocr.py` | Claude Vision 기반 OCR | `VisionOCRClient` |
| `universal_parser.py` | 범용 PDF/이미지 파서 | `UniversalParser` |
| `pdf_converter.py` | PDF 기본 변환 | `PDFConverter` |
| `vision_pdf_processor.py` | Vision PDF 처리 | `VisionPDFProcessor` |
| `verification_system.py` | 품질 검증 | `VerificationSystem` |
| `learning_system.py` | AI 학습 시스템 | `LearningSystem` |
| `template_engine.py` | 템플릿 렌더링 | `TemplateEngine` |
| `localization.py` | 다국어 지원 | `LocalizationManager` |
| `intelligent_layout_engine.py` | 지능형 레이아웃 | `IntelligentLayoutEngine` |
| `advanced_layout_optimizer.py` | 레이아웃 최적화 | `AdvancedLayoutOptimizer` |

### 사용법

```python
from engines.common import VisionOCRClient, UniversalParser

# OCR 클라이언트 초기화
ocr = VisionOCRClient()
result = ocr.extract_text(image_path)

# 범용 파서 사용
parser = UniversalParser()
data = parser.parse(pdf_path)
```

---

## 카테고리별 특화 엔진

### 1. 선거 홍보물 (engines/election/) [구현됨]

| 모듈 | 설명 | 주요 클래스 |
|------|------|------------|
| `auto_election_converter.py` | 선거 홍보물 자동 변환 | `AutoElectionConverter` |
| `html_generator.py` | 선거 HTML 생성 | `HTMLGenerator` |

**특징:**
- 후보자 정보, 공약, 약력 자동 추출
- 정당별 색상 및 스타일 자동 적용
- 선거관리위원회 규정 준수

```python
from engines.election import ElectionConverter

converter = ElectionConverter()
result = converter.convert(pdf_path, party="더불어민주당", candidate="홍길동")
```

### 2. 교회 주보 (engines/church/) [구현됨]

| 모듈 | 설명 | 주요 클래스 |
|------|------|------------|
| `church_html_generator.py` | 교회 주보 HTML 생성 | `ChurchBulletinGenerator` |

**특징:**
- 예배 순서, 설교, 교회 소식 자동 추출
- 성경 구절 / 찬송가 팝업
- SNS 링크, 온라인 헌금
- 테마 지원 (기본, 추수감사절, 성탄절, 부활절)

```python
from engines.church import ChurchBulletinGenerator

generator = ChurchBulletinGenerator()
html = generator.generate(extracted_data, title="주보", theme="default")
```

### 3. 대학 강의 자료 (engines/lecture/) [부분 구현]

| 모듈 | 설명 | 주요 클래스 |
|------|------|------------|
| `lecture_generator.py` | 강의 자료 생성기 | `LectureGenerator` |

**계획된 기능:**
- 슬라이드 → 웹 프레젠테이션
- 수식, 도표, 그래프 자동 인식
- 플래시카드 / 퀴즈 자동 생성

### 4. 지자체 소식지 (engines/newsletter/) [예정]

**계획된 기능:**
- 공지사항, 행사 일정 자동 추출
- 주민센터 연락처 자동 링크
- 다국어 자동 번역

### 5. 기업 카탈로그 (engines/catalog/) [예정]

**계획된 기능:**
- 제품 정보 자동 추출
- 제품 비교 기능
- 장바구니/견적 연동

### 6. 외국어 학습기 (engines/language/) [예정]

**계획된 기능:**
- 단어장 자동 추출
- 발음 TTS 연동
- 퀴즈/테스트 자동 생성

---

## 새 카테고리 추가 방법

1. `engines/` 아래에 새 디렉토리 생성
2. `__init__.py` 작성 (문서 및 import 포함)
3. 전용 생성기 모듈 작성
4. `engines/__init__.py`에 import 추가
5. `app.py`에서 content_type 매핑 추가

---

## 다른 프로젝트에서 재사용

공통 엔진만 사용하려면:

```python
import sys
sys.path.append("C:/StudySnap-Backend")

from engines.common import VisionOCRClient, UniversalParser
```

특정 카테고리 엔진 사용:

```python
from engines.church import ChurchBulletinGenerator
from engines.election import ElectionConverter
```

---

*마지막 업데이트: 2025-12-10*
