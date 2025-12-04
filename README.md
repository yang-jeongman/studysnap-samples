# StudySnap Backend

선거 홍보물 PDF를 모바일 최적화 웹페이지로 변환하는 FastAPI 기반 백엔드 서버

## 주요 기능

- **PDF 변환**: PDF 파일을 모바일 최적화된 HTML로 변환
- **Claude Vision OCR**: 이미지 기반 PDF에서 텍스트 자동 추출
- **선거 공보물 특화**: 후보자 정보, 공약, 경력 등을 구조화하여 추출
- **모바일 최적화 UI**: 반응형 디자인, 정당별 색상 테마, 확장 가능한 카드 UI
- **다양한 콘텐츠 지원**: 선거 홍보물, 강의자료, 교회 주보, 일반 문서

## 기술 스택

- **Python 3.10+**
- **FastAPI**: 고성능 웹 프레임워크
- **PyMuPDF**: PDF 처리
- **Claude Vision API**: AI 기반 OCR 및 정보 추출
- **Pillow**: 이미지 처리

## 설치 방법

### 1. 저장소 클론

```bash
git clone <repository-url>
cd StudySnap-Backend
```

### 2. 가상환경 생성 및 활성화

**Windows:**
```bash
python -m venv venv
venv\Scripts\activate
```

**Linux/Mac:**
```bash
python -m venv venv
source venv/bin/activate
```

### 3. 의존성 설치

```bash
pip install -r requirements.txt
```

### 4. 환경변수 설정

`.env.example` 파일을 `.env`로 복사하고 API 키를 설정합니다:

```bash
cp .env.example .env
```

`.env` 파일 편집:
```
ANTHROPIC_API_KEY=your_anthropic_api_key_here
```

**Anthropic API 키 발급 방법:**
1. [Anthropic Console](https://console.anthropic.com/) 접속
2. API Keys 메뉴에서 새 키 생성
3. 생성된 키를 `.env` 파일에 입력

## 실행 방법

### 개발 서버 실행

```bash
python app.py
```

또는

```bash
uvicorn app:app --reload --host 0.0.0.0 --port 8000
```

서버가 실행되면 http://localhost:8000 에서 접속 가능합니다.

## API 엔드포인트

### 1. 서버 상태 확인

```http
GET /
```

**응답 예시:**
```json
{
  "status": "running",
  "service": "StudySnap API",
  "version": "1.0.0"
}
```

### 2. PDF 변환

```http
POST /api/convert
```

**요청 파라미터:**
- `file`: PDF 파일 (필수)
- `content_type`: 콘텐츠 유형 (선택, 기본값: "general")
  - `election`: 선거 홍보물
  - `lecture`: 강의자료
  - `church`: 교회 주보
  - `general`: 일반 문서
- `title`: 결과물 제목 (선택)

**요청 예시 (curl):**
```bash
curl -X POST "http://localhost:8000/api/convert" \
  -F "file=@나경원.pdf" \
  -F "content_type=election"
```

**응답 예시:**
```json
{
  "success": true,
  "job_id": "abc12345",
  "message": "변환이 완료되었습니다",
  "result": {
    "url": "/outputs/abc12345_20241201_120000.html",
    "filename": "abc12345_20241201_120000.html",
    "original_filename": "나경원.pdf",
    "content_type": "election",
    "title": "나경원",
    "page_count": 2,
    "created_at": "2024-12-01T12:00:00"
  }
}
```

### 3. 결과 조회

```http
GET /api/result/{job_id}
```

HTML 파일을 직접 반환합니다.

### 4. 결과 삭제

```http
DELETE /api/result/{job_id}
```

### 5. 지원 콘텐츠 유형 조회

```http
GET /api/content-types
```

## 프로젝트 구조

```
StudySnap-Backend/
├── app.py                 # FastAPI 메인 애플리케이션
├── pdf_converter.py       # PDF 변환 모듈
├── html_generator.py      # HTML 생성 모듈
├── vision_ocr.py          # Claude Vision OCR 모듈
├── test_convert.py        # 테스트 스크립트
├── requirements.txt       # Python 의존성
├── .env.example          # 환경변수 템플릿
├── uploads/              # 업로드된 PDF 파일 저장
├── outputs/              # 생성된 HTML 파일 저장
└── README.md             # 프로젝트 문서
```

## 주요 모듈 설명

### 1. PDFConverter (`pdf_converter.py`)

PDF 파일에서 텍스트와 이미지를 추출합니다.

**주요 기능:**
- 텍스트 기반 PDF: 직접 텍스트 추출
- 이미지 기반 PDF: Claude Vision API를 사용한 OCR
- 선거 공보물: 구조화된 데이터 추출 (후보자명, 정당, 공약, 경력 등)

**설정 옵션:**
```python
converter = PDFConverter(
    dpi=150,              # 이미지 렌더링 DPI
    max_width=800,        # 모바일 최적화 최대 너비
    use_vision_ocr=True,  # Vision OCR 사용 여부
    include_images=False  # OCR 사용 시 이미지 포함 여부
)
```

### 2. HTMLGenerator (`html_generator.py`)

모바일 최적화된 HTML을 생성합니다.

**주요 기능:**
- 정당별 색상 테마 자동 적용
- 확장 가능한 공약 카드 UI
- 경력 타임라인
- Bottom Navigation
- 반응형 디자인

### 3. VisionOCR (`vision_ocr.py`)

Claude Vision API를 활용한 OCR 및 정보 추출

**주요 메서드:**
- `extract_text_from_image()`: 이미지에서 텍스트 추출
- `extract_election_info()`: 선거 공보물에서 구조화된 정보 추출

## 테스트

테스트 스크립트를 사용하여 변환 기능을 테스트할 수 있습니다:

```python
# test_convert.py
import requests

pdf_path = r"C:\path\to\your\file.pdf"

with open(pdf_path, 'rb') as f:
    response = requests.post(
        'http://localhost:8000/api/convert',
        files={'file': ('filename.pdf', f, 'application/pdf')},
        data={'content_type': 'election'}
    )
    result = response.json()
    print(f"Status: {result.get('success')}")
    print(f"Job ID: {result.get('job_id')}")
    print(f"URL: http://localhost:8000{result.get('result', {}).get('url')}")
```

## 로깅

애플리케이션은 Python의 `logging` 모듈을 사용하여 상세한 로그를 출력합니다.

**로그 레벨:**
- INFO: 일반적인 작업 진행 상황
- WARNING: 경고 메시지
- ERROR: 에러 발생 시 상세 정보

**로그 예시:**
```
2024-12-01 12:00:00 - INFO - [abc12345] PDF 변환 시작: 나경원.pdf (content_type: election)
2024-12-01 12:00:01 - INFO - 텍스트 50자 - 이미지 기반 PDF로 판단
2024-12-01 12:00:02 - INFO - Claude Vision OCR 사용하여 텍스트 추출 시작
2024-12-01 12:00:05 - INFO - 페이지 1 OCR 처리 시작
2024-12-01 12:00:10 - INFO - 페이지 1: 1234자 추출 완료
2024-12-01 12:00:15 - INFO - [abc12345] PDF 추출 완료: 2페이지
2024-12-01 12:00:16 - INFO - [abc12345] 변환 완료: abc12345_20241201_120000.html
```

## 개발 중단 시점 이슈

이 프로젝트는 3시간 전 작업이 중단되었으며, 다음 사항들이 완료되었습니다:

### 완료된 작업
- ✅ FastAPI 백엔드 서버 구축
- ✅ PDF 변환 기능 구현
- ✅ Claude Vision OCR 통합
- ✅ 선거 공보물 구조화 데이터 추출
- ✅ 모바일 최적화 HTML 생성
- ✅ 나경원 후보 홍보물로 테스트 완료
- ✅ 에러 처리 및 로깅 개선
- ✅ requirements.txt에 anthropic SDK 추가
- ✅ content_type 매개변수 전달 버그 수정
- ✅ 이미지 포함 옵션 추가

### 학습 시스템 (자동 개선 기능)

### 개요
사용할수록 똑똑해지는 자동 학습 시스템이 내장되어 있습니다. 변환 작업과 사용자 피드백을 분석하여 자동으로 성능을 개선합니다.

### 학습 기능

**1. 자동 데이터 수집**
- 모든 변환 작업 자동 기록 (`learning_data/conversions.jsonl`)
- OCR 정확도, 처리 시간, 추출된 데이터 구조 분석
- 콘텐츠 타입별 성공률 추적

**2. 사용자 피드백 시스템**
```bash
# 피드백 제출 API
POST /api/feedback
Content-Type: multipart/form-data

Fields:
- job_id: 변환 작업 ID
- rating: 만족도 (1-5)
- accuracy: OCR 정확도 (1-5)
- completeness: 완성도 (1-5)
- issues: 발견된 문제들 (콤마 구분)
- comment: 상세 코멘트
```

**3. 통계 및 인사이트**
```bash
# 전체 통계 조회
GET /api/statistics

# 학습 인사이트 조회
GET /api/learning/insights

# 학습 데이터 내보내기
POST /api/learning/export
```

**4. 자동 개선 제안**
- OCR 정확도가 낮을 때 프롬프트 개선 제안
- 자주 발생하는 문제 패턴 분석
- 처리 시간 최적화 제안
- 데이터 수집 개선 가이드

### 학습 데이터 구조

```
learning_data/
├── conversions.jsonl    # 모든 변환 작업 기록
├── feedback.jsonl       # 사용자 피드백
├── stats.json          # 실시간 통계
└── learned_patterns.json # 학습된 패턴
```

### 사용 예시

**변환 후 자동 학습:**
```python
# 변환 실행
response = requests.post('http://localhost:8000/api/convert',
                        files={'file': pdf_file},
                        data={'content_type': 'election'})
job_id = response.json()['job_id']

# 시스템이 자동으로 학습 데이터 저장
# - 페이지 수, 처리 시간
# - 추출된 데이터 품질
# - OCR 사용 여부
```

**피드백 제출:**
```python
# 사용자가 결과 확인 후
requests.post('http://localhost:8000/api/feedback',
             data={
                 'job_id': job_id,
                 'rating': 5,
                 'accuracy': 4,
                 'issues': 'SNS링크 누락, 공약 제목 오류',
                 'comment': '전반적으로 좋으나 일부 개선 필요'
             })

# 시스템이 자동으로 패턴 학습 및 개선
```

**통계 확인:**
```python
stats = requests.get('http://localhost:8000/api/statistics').json()
print(f"총 변환: {stats['statistics']['total_conversions']}")
print(f"평균 평점: {stats['statistics']['average_rating']}/5")
print(f"개선 제안: {stats['improvement_suggestions']}")
```

### 학습 시스템의 장점

1. **자동 품질 개선**: 사용자 피드백을 분석하여 OCR 프롬프트 자동 최적화
2. **패턴 인식**: 반복되는 오류 패턴 학습 및 자동 교정
3. **성능 모니터링**: 실시간 통계로 시스템 건강도 추적
4. **데이터 기반 의사결정**: 30일+ 축적 데이터로 신규 기능 우선순위 결정
5. **확장 가능**: 추후 머신러닝 모델 파인튜닝용 데이터로 활용 가능

## 범용 문서 변환 시스템

### 지원 파일 형식 (세계 최고 수준)

StudySnap은 PDF 문서 변환 분야에서 **세상의 어느 솔루션보다 다양한 종류의 파일을 변환**할 수 있는 기술을 보유하고 있습니다.

#### 지원 형식
- **PDF**: `.pdf` - PyMuPDF + Claude Vision OCR
- **한글**: `.hwp`, `.hwpx` - hwp5 + olefile (🇰🇷 대한민국 시장 특화)
- **이미지**: `.jpg`, `.jpeg`, `.png`, `.tiff`, `.bmp`, `.webp` - Claude Vision OCR
- **Word**: `.docx`, `.doc` - python-docx
- **PowerPoint**: `.pptx`, `.ppt` - python-pptx
- **Excel**: `.xlsx`, `.xls`, `.csv` - openpyxl

```bash
# 지원 형식 조회
GET /api/formats/supported
```

### 고객 맞춤형 출력 템플릿

**고객이 원하는 출력문을 최대한 반영**할 수 있는 유연한 템플릿 시스템을 제공합니다.

#### 내장 템플릿 (7종)

1. **mobile_html** - 모바일 최적화 HTML (기본)
   - 반응형 디자인
   - 정당별 색상 테마
   - 확장 가능한 카드 UI

2. **json** - API 연동용 JSON 데이터
   - 구조화된 데이터 출력
   - 다른 시스템과 연동 가능

3. **markdown** - 마크다운 형식
   - 깃허브, 노션 등과 호환
   - 텍스트 기반 편집 용이

4. **print_html** - A4 용지 출력 최적화
   - 프린터 친화적 레이아웃
   - 페이지 나누기 자동 처리

5. **presentation** - 프레젠테이션 슬라이드
   - 발표용 전체화면 레이아웃
   - 페이지별 슬라이드

6. **email** - 이메일 발송용 HTML
   - 이메일 클라이언트 호환
   - 뉴스레터 형식

7. **table_layout** - 테이블 중심 레이아웃
   - 데이터 비교 용이
   - 스프레드시트 스타일

```bash
# 템플릿 목록 조회
GET /api/templates

# 커스텀 템플릿 생성
POST /api/templates/custom
Fields:
- template_id: 템플릿 고유 ID
- name: 템플릿 이름
- description: 설명
- template_content: Jinja2 템플릿 코드
```

### 범용 변환 API

```bash
# 모든 파일 형식을 지원하는 범용 변환 엔드포인트
POST /api/convert/universal

Parameters:
- file: 변환할 파일 (PDF, Word, Excel, PowerPoint, 이미지)
- content_type: 콘텐츠 타입 (election, lecture, church, general)
- output_format: 출력 템플릿 ID (기본: mobile_html)
- title: 문서 제목
- language: 언어 코드 (ko, en, ja, zh, es, fr, de)
- custom_options: JSON 문자열로 추가 옵션 전달

예시:
curl -X POST "http://localhost:8000/api/convert/universal" \
  -F "file=@document.docx" \
  -F "content_type=lecture" \
  -F "output_format=presentation" \
  -F "language=en"
```

### 고급 커스터마이징 API

**최고 수준의 맞춤형 출력**을 위한 고급 API입니다.

```bash
POST /api/convert/custom

Parameters:
- file: 변환할 파일
- content_type: 콘텐츠 타입
- output_format: 출력 템플릿
- title: 문서 제목
- language: 언어
- color_scheme: 색상 테마 (예: "#FF5733", "blue")
- font_family: 폰트 (예: "Malgun Gothic", "Arial")
- include_images: 이미지 포함 여부 (true/false)
- max_image_width: 최대 이미지 너비 (픽셀)
- custom_css: 커스텀 CSS 스타일
- custom_header: 커스텀 헤더 HTML
- custom_footer: 커스텀 푸터 HTML

예시:
curl -X POST "http://localhost:8000/api/convert/custom" \
  -F "file=@election.pdf" \
  -F "content_type=election" \
  -F "color_scheme=#E11D48" \
  -F "font_family=Noto Sans KR" \
  -F "custom_css=.hero { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); }"
```

## 다국어 지원

### 지원 언어 (7개국어)

- 🇰🇷 **한국어** (ko)
- 🇺🇸 **English** (en)
- 🇯🇵 **日本語** (ja)
- 🇨🇳 **中文** (zh)
- 🇪🇸 **Español** (es)
- 🇫🇷 **Français** (fr)
- 🇩🇪 **Deutsch** (de)

```bash
# 지원 언어 목록
GET /api/languages

# 텍스트 언어 자동 감지
POST /api/languages/detect
Fields:
- text: 분석할 텍스트
```

### 다국어 OCR

언어별로 최적화된 OCR 프롬프트를 사용하여 **각 언어에 맞는 정확한 텍스트 추출**을 제공합니다.

```python
# 영어 문서 변환
response = requests.post('http://localhost:8000/api/convert/universal',
                        files={'file': english_doc},
                        data={'language': 'en'})

# 일본어 문서 변환
response = requests.post('http://localhost:8000/api/convert/universal',
                        files={'file': japanese_doc},
                        data={'language': 'ja'})
```

## 추가 개선 가능 사항
- [x] 학습 시스템 구축 (자동 개선)
- [x] 피드백 수집 시스템
- [x] 통계 및 분석 대시보드
- [x] 범용 문서 파서 (PDF, Word, Excel, PPT, 이미지)
- [x] 고객 맞춤형 템플릿 엔진
- [x] 다국어 지원 시스템 (7개 언어)
- [x] 고급 커스터마이징 API
- [ ] 비동기 처리 (대용량 PDF 처리 시)
- [ ] 캐싱 시스템 (중복 변환 방지)
- [ ] 진행 상황 표시 (WebSocket)
- [ ] 사용자 인증 및 권한 관리
- [ ] 프론트엔드 UI 개발

## 라이선스

이 프로젝트는 MIT 라이선스를 따릅니다.

## 문의

프로젝트 관련 문의사항은 이슈를 등록해주세요.
