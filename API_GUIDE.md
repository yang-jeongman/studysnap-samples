# StudySnap API 완벽 가이드

## 📋 목차

1. [시스템 개요](#시스템-개요)
2. [API 엔드포인트 목록](#api-엔드포인트-목록)
3. [기본 변환 API](#기본-변환-api)
4. [범용 변환 API](#범용-변환-api)
5. [고급 커스터마이징 API](#고급-커스터마이징-api)
6. [학습 시스템 API](#학습-시스템-api)
7. [다국어 지원 API](#다국어-지원-api)
8. [템플릿 관리 API](#템플릿-관리-api)
9. [사용 예시](#사용-예시)

---

## 시스템 개요

StudySnap은 **세계 최고 수준의 문서 변환 플랫폼**입니다.

### 🌟 핵심 강점

1. **다양한 파일 형식 지원**
   - PDF, Word, Excel, PowerPoint, 이미지 (JPG, PNG, TIFF 등)
   - 5개 이상의 주요 문서 형식 완벽 지원

2. **고객 맞춤형 출력**
   - 7가지 내장 템플릿
   - 커스텀 템플릿 생성 가능
   - CSS, 헤더, 푸터 커스터마이징

3. **다국어 지원**
   - 7개 언어 지원 (한국어, 영어, 일본어, 중국어, 스페인어, 프랑스어, 독일어)
   - 언어별 최적화된 OCR

4. **자동 학습 시스템**
   - 모든 변환 작업 자동 기록
   - 사용자 피드백 기반 품질 개선
   - 실시간 통계 및 인사이트

---

## API 엔드포인트 목록

### 기본 API
- `GET /` - 서버 상태 확인
- `GET /api/content-types` - 지원 콘텐츠 유형 조회

### 변환 API
- `POST /api/convert` - 기본 PDF 변환
- `POST /api/convert/universal` - 범용 문서 변환
- `POST /api/convert/custom` - 고급 커스터마이징 변환

### 결과 관리
- `GET /api/result/{job_id}` - 변환 결과 조회
- `DELETE /api/result/{job_id}` - 변환 결과 삭제

### 형식 & 템플릿
- `GET /api/formats/supported` - 지원 파일 형식 조회
- `GET /api/templates` - 출력 템플릿 목록
- `POST /api/templates/custom` - 커스텀 템플릿 생성

### 학습 시스템
- `POST /api/feedback` - 피드백 제출
- `GET /api/statistics` - 통계 조회
- `GET /api/learning/insights` - 인사이트 조회
- `POST /api/learning/export` - 학습 데이터 내보내기

### 다국어 지원
- `GET /api/languages` - 지원 언어 목록
- `POST /api/languages/detect` - 언어 자동 감지

---

## 기본 변환 API

### POST /api/convert

PDF 파일을 모바일 최적화 HTML로 변환합니다.

#### 요청 파라미터

| 파라미터 | 타입 | 필수 | 설명 | 기본값 |
|---------|------|------|------|--------|
| file | File | ✅ | 변환할 PDF 파일 | - |
| content_type | String | ❌ | 콘텐츠 타입 | general |
| title | String | ❌ | 결과물 제목 | 파일명 |

#### content_type 옵션

- `election` - 선거 공보물
- `lecture` - 강의자료
- `church` - 교회 주보
- `general` - 일반 문서

#### 예시 요청

```bash
curl -X POST "http://localhost:8000/api/convert" \
  -F "file=@document.pdf" \
  -F "content_type=lecture" \
  -F "title=미적분학 강의노트"
```

#### 응답 예시

```json
{
  "success": true,
  "job_id": "a1b2c3d4",
  "message": "변환이 완료되었습니다",
  "result": {
    "url": "/outputs/a1b2c3d4_20241201_120000.html",
    "filename": "a1b2c3d4_20241201_120000.html",
    "original_filename": "document.pdf",
    "content_type": "lecture",
    "title": "미적분학 강의노트",
    "page_count": 15,
    "created_at": "2024-12-01T12:00:00"
  }
}
```

---

## 범용 변환 API

### POST /api/convert/universal

**모든 파일 형식을 지원하는 범용 변환 API**

#### 지원 파일 형식

- **PDF**: `.pdf`
- **Word**: `.docx`, `.doc`
- **Excel**: `.xlsx`, `.xls`, `.csv`
- **PowerPoint**: `.pptx`, `.ppt`
- **이미지**: `.jpg`, `.jpeg`, `.png`, `.tiff`, `.bmp`, `.webp`

#### 요청 파라미터

| 파라미터 | 타입 | 필수 | 설명 | 기본값 |
|---------|------|------|------|--------|
| file | File | ✅ | 변환할 파일 | - |
| content_type | String | ❌ | 콘텐츠 타입 | general |
| output_format | String | ❌ | 출력 템플릿 ID | mobile_html |
| title | String | ❌ | 문서 제목 | 파일명 |
| language | String | ❌ | 언어 코드 | ko |
| custom_options | JSON String | ❌ | 추가 옵션 | {} |

#### 예시 요청

```bash
# Word 문서를 프레젠테이션 형식으로 변환
curl -X POST "http://localhost:8000/api/convert/universal" \
  -F "file=@lecture.docx" \
  -F "content_type=lecture" \
  -F "output_format=presentation" \
  -F "language=en"

# Excel을 테이블 레이아웃으로 변환
curl -X POST "http://localhost:8000/api/convert/universal" \
  -F "file=@data.xlsx" \
  -F "output_format=table_layout"

# 이미지를 JSON으로 변환 (OCR)
curl -X POST "http://localhost:8000/api/convert/universal" \
  -F "file=@document.jpg" \
  -F "output_format=json" \
  -F "language=ja"
```

---

## 고급 커스터마이징 API

### POST /api/convert/custom

**최고 수준의 맞춤형 출력을 위한 고급 API**

#### 요청 파라미터

| 파라미터 | 타입 | 필수 | 설명 | 기본값 |
|---------|------|------|------|--------|
| file | File | ✅ | 변환할 파일 | - |
| content_type | String | ❌ | 콘텐츠 타입 | general |
| output_format | String | ❌ | 출력 템플릿 | mobile_html |
| title | String | ❌ | 문서 제목 | 파일명 |
| language | String | ❌ | 언어 코드 | ko |
| color_scheme | String | ❌ | 색상 테마 | null |
| font_family | String | ❌ | 폰트 | null |
| include_images | Boolean | ❌ | 이미지 포함 | true |
| max_image_width | Integer | ❌ | 최대 이미지 너비 | 800 |
| custom_css | String | ❌ | 커스텀 CSS | null |
| custom_header | String | ❌ | 커스텀 헤더 HTML | null |
| custom_footer | String | ❌ | 커스텀 푸터 HTML | null |

#### 예시 요청

```bash
# 색상과 폰트 커스터마이징
curl -X POST "http://localhost:8000/api/convert/custom" \
  -F "file=@election.pdf" \
  -F "content_type=election" \
  -F "color_scheme=#E11D48" \
  -F "font_family=Noto Sans KR"

# 완전 커스터마이징
curl -X POST "http://localhost:8000/api/convert/custom" \
  -F "file=@document.pdf" \
  -F "custom_css=.hero { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); }" \
  -F "custom_header=<div class='my-header'>My Custom Header</div>" \
  -F "custom_footer=<div class='my-footer'>© 2024 My Company</div>"
```

#### 응답 예시

```json
{
  "success": true,
  "job_id": "x9y8z7w6",
  "message": "고급 커스터마이징 변환이 완료되었습니다",
  "result": {
    "url": "/outputs/x9y8z7w6_20241201_120000.html",
    "filename": "x9y8z7w6_20241201_120000.html",
    "original_filename": "document.pdf",
    "title": "맞춤형 문서",
    "customizations": {
      "color_scheme": "#E11D48",
      "font_family": "Noto Sans KR",
      "include_images": true,
      "has_custom_css": true,
      "has_custom_header": true,
      "has_custom_footer": true
    },
    "created_at": "2024-12-01T12:00:00"
  }
}
```

---

## 학습 시스템 API

### POST /api/feedback

변환 결과에 대한 피드백을 제출합니다.

#### 요청 파라미터

| 파라미터 | 타입 | 필수 | 설명 |
|---------|------|------|------|
| job_id | String | ✅ | 변환 작업 ID |
| rating | Integer | ✅ | 만족도 (1-5) |
| accuracy | Integer | ❌ | OCR 정확도 (1-5) |
| completeness | Integer | ❌ | 완성도 (1-5) |
| issues | String | ❌ | 발견된 문제들 (콤마 구분) |
| comment | String | ❌ | 상세 코멘트 |

#### 예시

```bash
curl -X POST "http://localhost:8000/api/feedback" \
  -F "job_id=a1b2c3d4" \
  -F "rating=5" \
  -F "accuracy=4" \
  -F "completeness=5" \
  -F "issues=일부 표 누락" \
  -F "comment=전반적으로 훌륭합니다"
```

### GET /api/statistics

전체 통계 및 개선 제안을 조회합니다.

#### 응답 예시

```json
{
  "success": true,
  "statistics": {
    "total_conversions": 156,
    "average_rating": 4.5,
    "success_rate": 92.3,
    "ocr_usage_rate": 68.5,
    "feedback_count": 89,
    "common_issues": {
      "표 누락": 12,
      "이미지 품질": 8
    },
    "top_parties": {
      "국민의힘": 45,
      "더불어민주당": 38
    }
  },
  "improvement_suggestions": [
    "OCR 정확도 개선 필요 - 평균 평점 4.3",
    "더 많은 변환 데이터 수집이 필요합니다"
  ]
}
```

---

## 다국어 지원 API

### GET /api/languages

지원하는 모든 언어 목록을 조회합니다.

#### 응답 예시

```json
{
  "success": true,
  "languages": [
    {"code": "ko", "name": "한국어", "native": "한국어"},
    {"code": "en", "name": "English", "native": "English"},
    {"code": "ja", "name": "Japanese", "native": "日本語"},
    {"code": "zh", "name": "Chinese", "native": "中文"},
    {"code": "es", "name": "Spanish", "native": "Español"},
    {"code": "fr", "name": "French", "native": "Français"},
    {"code": "de", "name": "German", "native": "Deutsch"}
  ],
  "count": 7
}
```

### POST /api/languages/detect

텍스트에서 언어를 자동 감지합니다.

#### 예시

```bash
curl -X POST "http://localhost:8000/api/languages/detect" \
  -F "text=안녕하세요 반갑습니다"
```

#### 응답

```json
{
  "success": true,
  "detected_language": "ko"
}
```

---

## 템플릿 관리 API

### GET /api/templates

사용 가능한 모든 출력 템플릿을 조회합니다.

#### 응답 예시

```json
{
  "success": true,
  "templates": [
    {
      "id": "mobile_html",
      "name": "모바일 최적화 HTML",
      "description": "반응형 디자인의 모바일 친화적 HTML",
      "type": "builtin"
    },
    {
      "id": "json",
      "name": "JSON 형식",
      "description": "API 연동용 JSON 데이터",
      "type": "builtin"
    }
  ],
  "count": 7
}
```

### POST /api/templates/custom

커스텀 템플릿을 생성합니다.

#### 요청 파라미터

| 파라미터 | 타입 | 필수 | 설명 |
|---------|------|------|------|
| template_id | String | ✅ | 템플릿 고유 ID |
| name | String | ✅ | 템플릿 이름 |
| description | String | ✅ | 설명 |
| template_content | String | ✅ | Jinja2 템플릿 코드 |

#### 예시

```bash
curl -X POST "http://localhost:8000/api/templates/custom" \
  -F "template_id=my_custom" \
  -F "name=My Custom Template" \
  -F "description=나만의 커스텀 템플릿" \
  -F "template_content=<html><body>{{ content }}</body></html>"
```

---

## 사용 예시

### Python 예시

```python
import requests

# 1. 기본 변환
with open('document.pdf', 'rb') as f:
    response = requests.post(
        'http://localhost:8000/api/convert',
        files={'file': ('document.pdf', f, 'application/pdf')},
        data={'content_type': 'lecture', 'title': '강의노트'}
    )
    result = response.json()
    print(f"변환 완료: {result['result']['url']}")

# 2. 범용 변환 (Word → Presentation)
with open('lecture.docx', 'rb') as f:
    response = requests.post(
        'http://localhost:8000/api/convert/universal',
        files={'file': f},
        data={
            'content_type': 'lecture',
            'output_format': 'presentation',
            'language': 'en'
        }
    )

# 3. 고급 커스터마이징
with open('election.pdf', 'rb') as f:
    response = requests.post(
        'http://localhost:8000/api/convert/custom',
        files={'file': f},
        data={
            'content_type': 'election',
            'color_scheme': '#E11D48',
            'font_family': 'Noto Sans KR',
            'custom_css': '.hero { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); }'
        }
    )

# 4. 피드백 제출
requests.post(
    'http://localhost:8000/api/feedback',
    data={
        'job_id': 'a1b2c3d4',
        'rating': 5,
        'accuracy': 4,
        'comment': '훌륭합니다!'
    }
)

# 5. 통계 조회
stats = requests.get('http://localhost:8000/api/statistics').json()
print(f"총 변환 수: {stats['statistics']['total_conversions']}")
print(f"평균 평점: {stats['statistics']['average_rating']}")
```

### JavaScript 예시

```javascript
// 1. 기본 변환
const formData = new FormData();
formData.append('file', fileInput.files[0]);
formData.append('content_type', 'lecture');
formData.append('title', '강의노트');

const response = await fetch('http://localhost:8000/api/convert', {
  method: 'POST',
  body: formData
});

const result = await response.json();
console.log('변환 완료:', result.result.url);

// 2. 통계 조회
const stats = await fetch('http://localhost:8000/api/statistics')
  .then(res => res.json());
console.log('총 변환 수:', stats.statistics.total_conversions);
```

---

## 에러 처리

모든 API는 에러 발생 시 다음 형식으로 응답합니다:

```json
{
  "detail": "에러 메시지"
}
```

### HTTP 상태 코드

- `200 OK` - 성공
- `400 Bad Request` - 잘못된 요청
- `404 Not Found` - 리소스를 찾을 수 없음
- `500 Internal Server Error` - 서버 내부 오류

---

## 성능 최적화 팁

1. **이미지 크기 조절**: `max_image_width` 파라미터로 이미지 크기 제한
2. **이미지 제외**: 텍스트만 필요한 경우 `include_images=false`
3. **적절한 템플릿 선택**: JSON 출력이 HTML보다 빠름
4. **언어 지정**: 자동 감지 대신 정확한 언어 코드 제공

---

## 문의 및 지원

- **GitHub Issues**: 버그 리포트 및 기능 제안
- **Email**: support@studysnap.com (가상 예시)

---

## 라이선스

MIT License

**© 2024 StudySnap - 세계 최고 수준의 문서 변환 플랫폼**
