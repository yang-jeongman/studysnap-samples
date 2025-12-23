# StudySnap 템플릿 관리 시스템

## 개요
StudySnap의 PDF to HTML 변환 시스템을 위한 템플릿 저장소입니다. 머신러닝 기반 템플릿 선택 및 지속적인 품질 개선을 목표로 합니다.

## 폴더 구조

```
sample_templates/
├── election/              # 선거 공보물 템플릿
│   ├── democratic/        # 더불어민주당
│   │   └── templates.json
│   ├── ppp/              # 국민의힘
│   │   └── templates.json
│   └── progressive/      # 진보당
│       └── templates.json
├── church/               # 교회 주보 템플릿
│   ├── general/          # 일반형
│   ├── modern/           # 모던형
│   └── templates.json
├── newsletter/           # 뉴스레터 템플릿
│   └── templates.json
└── README.md            # 이 파일
```

## 템플릿 카테고리

### 1. 선거 공보물 (Election)

#### 1.1 더불어민주당 템플릿
- **ID**: `minjoo_standard_v1`
- **색상**: 파란색 (#004EA2)
- **특징**: 아코디언 공약 카드, 타임라인 경력, 이미지 모달
- **적합**: 국회의원, 시장, 도지사
- **성공률**: 100% (2건)
- **샘플**: 류삼영, 김병욱

#### 1.2 국민의힘 템플릿
- **ID**: `ppp_standard_v1`
- **색상**: 빨간색 (#E61E2B)
- **특징**: 카드 기반 레이아웃, 깔끔한 디자인
- **적합**: 국회의원, 시장, 도지사
- **성공률**: 100% (1건)
- **샘플**: 나경원

#### 1.3 진보당 템플릿
- **ID**: `progressive_standard_v1`
- **색상**: 초록색 (#10B981)
- **특징**: 심플한 카드, 간결한 디자인
- **적합**: 시장, 도지사, 구청장
- **성공률**: 100% (1건)
- **샘플**: 장지화

### 2. 교회 주보 (Church)

#### 2.1 일반형 템플릿
- **ID**: `church_general_v1`
- **특징**: 전통적 레이아웃, 주간 일정 캘린더, 인쇄 최적화
- **적합**: 대형/중형/소형 교회
- **성공률**: 100% (5건)
- **샘플**: 여의도순복음교회

#### 2.2 모던형 템플릿
- **ID**: `church_modern_v1`
- **특징**: 미니멀 디자인, 이미지 중심, 소셜 미디어 연동
- **적합**: 중형/소형/청년 교회
- **성공률**: N/A (신규)

### 3. 뉴스레터 (Newsletter)

#### 3.1 정당 뉴스레터 템플릿
- **ID**: `newsletter_party_v1`
- **특징**: 매거진 스타일, 풍부한 이미지, 다중 섹션
- **적합**: 정당, NGO, 협회
- **성공률**: 100% (2건)
- **샘플**: 진보당 너머로

#### 3.2 심플 뉴스레터 템플릿
- **ID**: `newsletter_simple_v1`
- **특징**: 미니멀 디자인, 텍스트 중심, 이메일 호환
- **적합**: 기업, 스타트업, 개인
- **성공률**: N/A (신규)

## 템플릿 변수 시스템

모든 템플릿은 변수 치환을 통해 커스터마이징됩니다.

### 공통 변수
```javascript
{
  "title": "문서 제목",
  "date": "날짜",
  "theme_color": "#COLOR"
}
```

### 선거 공보물 변수
```javascript
{
  "candidate_name": "후보자 이름",
  "candidate_number": "기호 번호",
  "party_name": "정당명",
  "district": "지역구",
  "slogan": "슬로건",
  "pledges": [
    {
      "category": "카테고리",
      "title": "제목",
      "items": ["항목1", "항목2"]
    }
  ],
  "career_items": [
    {
      "period": "기간",
      "title": "직책/내용"
    }
  ],
  "images": ["image1.jpg", "image2.jpg"],
  "contacts": {
    "office": "사무소 주소",
    "phone": "전화번호",
    "sns": {
      "facebook": "URL",
      "youtube": "URL"
    }
  }
}
```

### 교회 주보 변수
```javascript
{
  "church_name": "교회명",
  "service_date": "예배 날짜",
  "service_theme": "예배 주제",
  "worship_order": ["순서1", "순서2"],
  "sermon": {
    "title": "설교 제목",
    "verse": "본문 말씀",
    "summary": "설교 요약"
  },
  "hymns": ["찬양1", "찬양2"],
  "weekly_schedule": [
    {
      "day": "요일",
      "time": "시간",
      "event": "행사명"
    }
  ]
}
```

## 머신러닝 통합

### 특징 추출 (Feature Extraction)

템플릿 선택을 위한 특징 추출:

#### PDF 특징
- `page_count`: 페이지 수
- `has_images`: 이미지 포함 여부
- `image_count`: 이미지 개수
- `text_density`: 텍스트 밀도 (low/medium/high)
- `dominant_color`: 주요 색상
- `layout_complexity`: 레이아웃 복잡도

#### 콘텐츠 특징
- `organization_type`: 조직 유형 (party/church/company)
- `position`: 직책 (assembly/mayor/pastor)
- `experience_level`: 경력 수준
- `content_volume`: 콘텐츠 양
- `section_count`: 섹션 개수

### 학습 데이터 구조

각 `templates.json`의 `ml_training_data` 섹션에 학습 샘플 저장:

```json
{
  "training_samples": [
    {
      "sample_id": "unique_id",
      "input": {
        "pdf_features": {...},
        "candidate_info": {...},
        "content_features": {...}
      },
      "output": {
        "template_id": "selected_template",
        "customizations": {...},
        "quality_score": 95,
        "user_feedback": "positive"
      }
    }
  ]
}
```

### 템플릿 선택 알고리즘

```python
def select_template(pdf_features, content_features):
    """
    PDF와 콘텐츠 특징을 기반으로 최적의 템플릿 선택
    """
    # 1. 카테고리 분류 (선거/교회/뉴스레터)
    category = classify_category(pdf_features, content_features)

    # 2. 서브카테고리 분류 (정당별, 교회 스타일별 등)
    subcategory = classify_subcategory(category, content_features)

    # 3. 템플릿 매칭 스코어 계산
    templates = load_templates(category, subcategory)
    scores = []
    for template in templates:
        score = calculate_similarity(
            pdf_features,
            content_features,
            template['ml_features']
        )
        scores.append((template, score))

    # 4. 최고 점수 템플릿 선택
    best_template = max(scores, key=lambda x: x[1])
    return best_template[0]
```

## 템플릿 추가 프로세스

새로운 템플릿을 추가하려면:

### 1. HTML 파일 생성
기존 템플릿을 참고하여 변수화된 HTML 생성

### 2. 메타데이터 추가
해당 카테고리의 `templates.json`에 템플릿 정보 추가:

```json
{
  "id": "new_template_v1",
  "name": "새 템플릿 v1.0",
  "description": "템플릿 설명",
  "file": "new_template_v1.html",
  "features": {...},
  "ml_features": {...},
  "recommended_for": {...}
}
```

### 3. 학습 데이터 업데이트
템플릿 사용 시마다 `training_samples`에 새 샘플 추가

### 4. 성능 메트릭 업데이트
```json
{
  "performance_metrics": {
    "usage_count": 증가,
    "success_rate": 재계산,
    "avg_quality_score": 업데이트
  }
}
```

## 품질 관리

### 품질 점수 계산
```python
quality_score = (
    content_coverage * 0.4 +      # 원본 콘텐츠 포함률 (40%)
    design_score * 0.3 +           # 디자인 품질 (30%)
    accessibility_score * 0.2 +    # 접근성 점수 (20%)
    performance_score * 0.1        # 성능 점수 (10%)
)
```

### 성공 기준
- Content Coverage >= 70%
- Quality Score >= 80
- User Feedback: Positive
- Generation Success: True

## 사용 예시

### Python에서 템플릿 사용

```python
import json
from pathlib import Path

def load_template(category, subcategory, template_id):
    """템플릿 메타데이터 로드"""
    path = Path(f"sample_templates/{category}/{subcategory}/templates.json")
    with open(path) as f:
        data = json.load(f)

    for template in data['templates']:
        if template['id'] == template_id:
            return template
    return None

def apply_template(template, variables):
    """변수를 템플릿에 적용"""
    html_path = Path(f"sample_templates/{template['file']}")
    with open(html_path) as f:
        html = f.read()

    # 변수 치환
    for key, value in variables.items():
        html = html.replace(f"{{{{{key}}}}}", str(value))

    return html

# 사용 예
template = load_template('election', 'democratic', 'minjoo_standard_v1')
variables = {
    'candidate_name': '홍길동',
    'candidate_number': '1',
    'party_name': '더불어민주당',
    'district': '서울 강남구',
    'slogan': '변화와 혁신'
}
html = apply_template(template, variables)
```

## 통계

### 현재 상태 (2025-12-23 기준)

| 카테고리 | 템플릿 수 | 샘플 수 | 평균 성공률 |
|---------|----------|---------|------------|
| 선거 공보물 | 3 | 4 | 100% |
| 교회 주보 | 2 | 5 | 100% |
| 뉴스레터 | 2 | 2 | 100% |
| **전체** | **7** | **11** | **100%** |

### 템플릿 사용 현황

#### 선거 공보물
- 민주당: 2건 (류삼영, 김병욱)
- 국민의힘: 1건 (나경원)
- 진보당: 1건 (장지화)

#### 교회 주보
- 일반형: 5건 (여의도순복음교회)

#### 뉴스레터
- 정당형: 2건 (진보당 너머로)

## 향후 계획

### 단기 (1개월)
- [ ] HTML 템플릿 파일 생성 (변수화)
- [ ] 템플릿 선택 자동화 스크립트
- [ ] A/B 테스트 시스템

### 중기 (3개월)
- [ ] 머신러닝 모델 학습
- [ ] 자동 품질 평가 시스템
- [ ] 템플릿 버전 관리

### 장기 (6개월)
- [ ] 실시간 템플릿 추천 시스템
- [ ] 사용자 피드백 통합
- [ ] 자동 템플릿 생성 (Generative AI)

## 기여 가이드

새로운 템플릿을 추가하거나 개선하려면:

1. 기존 템플릿 분석
2. 새 템플릿 HTML 작성 (변수 포함)
3. `templates.json`에 메타데이터 추가
4. 최소 1개의 샘플 출력물 생성
5. 품질 점수 측정 및 기록
6. Pull Request 제출

## 라이선스

StudySnap Internal Use Only

## 연락처

- **개발팀**: dev@studysnap.kr
- **이슈 보고**: https://github.com/studysnap/backend/issues
- **문서**: https://docs.studysnap.kr

---

*Last Updated: 2025-12-23*
*Version: 1.0.0*
