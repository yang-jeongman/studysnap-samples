# StudySnap-Backend 프로젝트 지침

## 프로젝트 개요
PDF 문서를 인터랙티브 HTML로 변환하는 AI 기반 솔루션

## 핵심 기술 스택
- Backend: Python Flask
- AI: Claude Vision API (Anthropic)
- OCR: PyMuPDF + Claude Vision
- Frontend: Vanilla JS, Mobile-first CSS

## 주요 변환기
1. **교회 주보 변환기** (`/api/church-convert-ai`)
   - 8개국어 자동 번역 (ko, en, zh, ja, id, es, ru, fr)
   - 성경 구절 팝업 (다국어)
   - 찬송가 가사 팝업 (다국어)
   - 인터랙티브 기능 (다크모드, 언어선택, 공유)

2. **선거 공보물 변환기** (`/api/election-convert-ai`)
   - 후보자 정보 자동 추출
   - 공약 구조화
   - 정당별 테마 적용

## 품질 기준 (전문가 수준)
참조 파일: `outputs/Church/여의도순복음교회/fg-2025-12-14_외국어 서비스.html`

### 필수 기능
- [ ] 언어 선택 드롭다운 (8개국어)
- [ ] data-i18n 속성으로 모든 텍스트 번역 가능
- [ ] 폴백 시스템: 선택언어 → 영어 → 한국어
- [ ] 성경 구절 클릭 → 다국어 팝업
- [ ] 찬송가 번호 클릭 → 다국어 가사 팝업
- [ ] 설교 본문 전체 번역
- [ ] 오늘의 양식(묵상) 번역

### 번역 데이터 구조
```javascript
const translations = {
    ko: { verse_text: "...", sermon_intro: "...", ... },
    en: { verse_text: "...", sermon_intro: "...", ... },
    // 8개 언어 모두 포함
};
```

## 핵심 파일
- `church_html_generator.py` - HTML 생성 엔진
- `vision_ocr.py` - Claude Vision OCR + 번역
- `app.py` - Flask API 엔드포인트
- `static/church-converter.html` - 프론트엔드 UI

## 코드 수정 시 주의사항
1. 서버 재시작 필요 (Python 파일 수정 후)
2. 번역은 `translate_church_bulletin_content()` 메서드 사용
3. 성경책 이름 번역은 `BIBLE_BOOK_TRANSLATIONS` 딕셔너리 참조

## API 비용 최적화
- Claude Sonnet 4 사용 (Vision + 번역)
- 페이지당 1회 Vision API 호출
- 번역은 필요한 텍스트만 선별적으로

## 테스트 방법
```bash
python app.py
# http://localhost:5000/static/church-converter.html
# PDF 업로드 → AI 모드 ON → 변환
```

---

## 2025-12-15 작업 기록

### 문제점 및 해결

#### 1. 오늘의 말씀 섹션이 표시되지 않음
- **원인**: `_build_html`에서 `_build_verse_section` 함수가 호출되지 않음
- **해결**: `church_html_generator.py:879`에 `_build_verse_section` 호출 추가

#### 2. 예배 카드에 담당자 정보 누락
- **원인**: `_convert_structured_services`에서 `presider`, `scripture`, `hymn` 필드가 누락
- **해결**: `church_html_generator.py:750-764` 필드 보존하도록 수정

#### 3. 오늘의 말씀 텍스트 오류 (1페이지 불완전한 텍스트 사용)
- **원인**: 1페이지의 짧은 성경구절이 3페이지 전체 말씀보다 우선 사용됨
- **해결**:
  - `app.py:4308-4318` - 더 긴 텍스트 우선 사용하도록 수정
  - `vision_ocr.py:369-388` - 1페이지 프롬프트에서 오늘의 말씀 추출 제거

#### 4. 예배 테이블에 찬송 컬럼 누락
- **원인**: 프롬프트와 파싱 로직에 찬송 필드 없음
- **해결**:
  - `vision_ocr.py:404-417` - 9컬럼 테이블 프롬프트 추가
  - `vision_ocr.py:703-735` - 9컬럼 파싱 로직 추가

#### 5. SNS/헌금 섹션 스타일 불일치
- **원인**: `.sns-buttons` 대신 `.sns-grid` 구조 필요
- **해결**: `church_html_generator.py:4841-4913` SNS/헌금 HTML 구조 전문가 결과물과 동일하게 수정

### 주요 수정 파일
| 파일 | 수정 내용 |
|------|----------|
| `church_html_generator.py` | `_build_verse_section` 호출, 예배 카드 구조, SNS/헌금 그리드 |
| `vision_ocr.py` | 프롬프트 개선, 9컬럼 테이블 파싱, JSON 파싱 폴백 |
| `app.py` | 오늘의 말씀 우선순위 (더 긴 텍스트 우선) |

### 예배순서 데이터 구조 (목표)
```
공통순서:
- 예배로 부르심: 요 4:24 (사회자)
- 찬송: 8장(통9장) 4절 (다같이)
- 신앙고백: 사도신경 (다같이)
- 찬송: 1부 301장, 2·3·4부 105장, 주일저녁 94장
- 마지막 찬송: 주기도문(635장)

각 예배별:
- 기도 (대표기도자)
- 성경봉독 (구절 + 사회자)
- 찬양 (찬양대)
- 설교 (제목 + 설교자)
- 기도와 결신 (설교자)
- 헌금기도 (헌금기도자)
- 축도 (설교자)
```

### 다음 작업
- [x] 오늘의 말씀 폰트/색상 스타일 개선
- [x] 예배순서 공통사항 + 개별사항 분리 표시
- [x] 6개 예배 모두 동일한 형식 적용

---

## 2025-12-15 추가 작업 (오후)

### 1. 오늘의 말씀 스타일 개선
- **파일**: `church_html_generator.py:1168-1255`
- **변경 내용**:
  - 카드 테두리 둥글기 16px → 20px
  - 그림자 효과 강화 (box-shadow 추가)
  - 말씀 텍스트 배경 반투명 흰색 (rgba 0.12)
  - 텍스트 그림자 및 backdrop-filter 효과
  - verse-ref 버튼 hover 효과 추가
  - 아이콘 블러 효과로 배경 장식 개선

### 2. 주일예배순 공통순서 + 개별 카드 분리
- **파일**: `church_html_generator.py:3854-3910`
- **새 메서드**: `_build_common_worship_order()`
- **공통순서 섹션 추가**:
  - 예배로 부르심: 요 4:24 (클릭 가능)
  - 찬송: 8장(통9장) 4절 (다같이)
  - 신앙고백: 사도신경 (다같이)
  - ⬇ 개별 예배순서 (강조 표시)
  - 찬송/축도: 635장 주기도문

### 3. 개별 예배 카드 항목 순서 정리
- **파일**: `church_html_generator.py:4046-4128`
- **순서**: 사회 → 기도 → 성경봉독 → 찬양 → 설교 → 기도와 결신 → 헌금기도 → 찬송
- **새 항목 추가**: 찬양(찬양대), 설교, 기도와 결신
- **스타일 개선**:
  - `.sermon-item`: 설교 항목 배경 강조
  - `.mc-item`: 사회자 항목 골드 테두리

### CSS 추가 (1257-1444)
```css
/* 공통 예배순서 */
.common-worship-order { ... }
.common-order-title { ... }
.order-item { ... }
.order-item.highlight-item { ... }

/* 설교/사회자 항목 강조 */
.worship-item.sermon-item { ... }
.worship-item.mc-item { ... }
```

### 테스트 필수
서버 재시작 후 확인:
```bash
python app.py
# http://localhost:5000/static/church-converter.html
```

---

## 2025-12-15 추가 작업 (오후 2차)

### 4. 예배순서 전체 템플릿 추가
- **파일**: `church_html_generator.py:3985-4086`
- **문제**: PDF에서 개별 예배 정보가 추출되지 않으면 개별 카드가 표시되지 않음
- **해결**: 개별 데이터가 없을 때 전체 예배순서 템플릿 표시

**여의도순복음교회 예배순서 형식**:
```
1. 예배로 부르심 - 요 4:24 (사회자)
2. 찬송 - 8장(통9장) 4절 (다같이, 일어서서)
3. 신앙고백 - 사도신경 (다같이, 일어서서)
4. 찬송 - 1부: 301장 / 2·3·4부: 105장 (다같이)
5. 기도 - 대표기도자
6. 성경봉독 - 사회자
7. 찬양 - 찬양대
8. 설교 - 담임목사
9. 기도와 결신 - 설교자
10. 헌금기도 - 헌금기도자
11. 찬송 - 635장 주기도문 (다같이, 일어서서)
12. 축도 - 설교자
```

### 5. 수정 원칙 (코드 안정성)
- 특정 위치 수정 시 관련 없는 부분 절대 건드리지 않음
- 기존 기능 유지하면서 새 기능 추가
- CSS 스타일은 기존 클래스에 영향 없이 새 클래스 추가

### 6. 예배별 탭 전환 기능 추가
- **파일**: `church_html_generator.py`
- **CSS**: 1284-1313 (`.service-tabs`, `.service-tab`)
- **HTML**: 4045-4050 (탭 버튼)
- **JavaScript**: 6241-6307 (`switchService()` 함수)

**탭 버튼**:
- 1부 | 2·3·4부 | 5부 대학청년 | 주일저녁

**동적 변경 항목**:
- 찬송 (부별 다른 찬송가)
- 성경봉독 (부별 다른 구절)
- 찬양 (부별 찬양대)
- 기도/헌금기도/설교자

### 다음 작업 (템플릿 시스템)
- [x] 예배별 탭 전환 기능
- [ ] 교회별 프리셋 JSON 구조 설계
- [ ] 여의도순복음교회 전용 템플릿 완성
- [ ] 다른 교회 템플릿 추가 (명성교회, 사랑의교회 등)

---

## 2025-12-15 추가 작업 (오후 3차)

### 7. 오늘의 말씀 컴팩트 아코디언
- **파일**: `church_html_generator.py:1168-1238`
- **변경 내용**:
  - 카드 높이 50% 축소 (padding: 28px → 14px)
  - 한 줄 레이아웃: `오늘의 말씀  누가복음3:4~6 ▼`
  - 클릭 시 아코디언으로 전체 말씀 펼침
  - 터치하여 말씀 보기 힌트 추가

### 8. 📖 생명의 말씀 섹션 추가
- **파일**: `church_html_generator.py:4146-4186`
- **위치**: 예배 안내와 금주의 찬양 사이
- **새 메서드**: `_build_sermon_word_section()`

**구조**:
```
┌─────────────────────────────────────┐
│ 📖 생명의 말씀              ▼      │ (보라색 헤더, 흰색 글씨)
│    The Word of Life                 │
├─────────────────────────────────────┤
│     예수님 오심을 기다리며(Ⅱ)       │
│   (Waiting for Jesus' Coming(Ⅱ))   │
├─────────────────────────────────────┤
│ [아코디언 펼침 시]                  │
│ 1. 마음의 골짜기를 메우라           │ (소제목)
│    본문 텍스트...                   │
│ 2. 교만의 산을 낮추라               │
│    본문 텍스트...                   │
│ 3. 굽은 것을 곧게 하라              │
│    본문 텍스트...                   │
│       여의도순복음교회 이영훈 위임목사│
└─────────────────────────────────────┘
```

### CSS 추가 (1314-1436)
```css
/* 생명의 말씀 섹션 */
.sermon-word-section { ... }
.sermon-word-header { background: var(--primary); color: white; }
.sermon-word-titles .section-title { color: white; }
.sermon-subtitle { font-size: 1.1em; font-weight: 700; }
.sermon-paragraph { text-align: justify; line-height: 1.9; }
.sermon-pastor { text-align: right; font-weight: 600; }
```

### JavaScript 추가 (6326-6329)
```javascript
function toggleSermonWord(element) {
    element.classList.toggle('expanded');
}
```

### 섹션 순서 (현재)
1. 오늘의 말씀 (컴팩트 아코디언)
2. ⛪ 예배 안내
3. 📖 생명의 말씀 ← 새로 추가
4. 🎵 금주의 찬양
5. 📢 교회소식
...

---

## 2025-12-16 작업 기록

### 완료된 작업

#### 1. 설교 버튼 → 생명의 말씀 연결
- **파일**: `church_html_generator.py:4044`
- **변경**: `href="#sermon-detail"` → `href="#sermon-word"`
- 상단 네비게이션 '설교' 버튼 클릭 시 📖 생명의 말씀 섹션으로 이동

#### 2. 소식 버튼 → 교회소식 아코디언 (예배/모집/안내)
- **파일**: `church_html_generator.py:5041-5136`
- **새 구조**: 카테고리별 아코디언
  - ⛪ 예배 (펼침 가능)
  - 📝 모집 (펼침 가능)
  - 📢 안내 (펼침 가능)
- **기능**: 각 항목 제목 클릭 시 상세내용 펼침
- **파일**: `vision_ocr.py:404-430` - 5페이지 프롬프트 수정
  - 카테고리별([예배], [모집], [안내]) 뉴스 추출
  - 각 항목의 제목 + 상세내용 함께 추출

#### 3. 다음 주간 대표기도 표 추가
- **파일**: `church_html_generator.py:5139-5210`
- **새 메서드**: `_build_prayer_table_section()`
- **구조**:
```
┌───────────────────────────────────────────┐
│ 🙏 다음 주간 대표기도                      │
├──────┬───────┬───────┬───────┬───────────┤
│ 구분 │ 12/21 │ 12/24 │ 12/25 │ 12/26    │
├──────┼───────┼───────┼───────┼───────────┤
│ 1부  │ OOO   │ OOO   │ OOO   │ OOO      │
│ 2부  │ OOO   │ OOO   │ OOO   │ OOO      │
└──────┴───────┴───────┴───────┴───────────┘
```
- **CSS**: `church_html_generator.py:2400-2521`
  - 가로 스크롤 지원 (모바일)
  - 헤더 보라색 배경
  - 구분 열 강조 스타일

#### 4. 금주의 찬양 - 원본 PDF 표 형식 유지
- **파일**: `church_html_generator.py:5028-5039`
- **변경**: 가상 데이터 제거, 원본 없으면 섹션 미표시
- **파일**: `vision_ocr.py` - `raw_choir_table` 필드 추가
  - headers: ["찬양대", "날짜1", "날짜2", ...]
  - rows: [["1부", "OOO", "OOO", ...], ...]

#### 5. 새벽기도회 섹션 삭제
- **파일**: `church_html_generator.py`
- **변경**: `dawn_prayer.times` 기본값 빈 문자열로 변경
- **결과**: 데이터 없으면 섹션 미표시

### 수정 파일 요약
| 파일 | 수정 내용 |
|------|----------|
| `church_html_generator.py` | 설교 링크, 뉴스 아코디언, 대표기도 표 섹션, CSS 스타일 |
| `vision_ocr.py` | 5페이지 프롬프트, 뉴스 카테고리 파싱, 대표기도 표 파싱 |
| `app.py` | `raw_prayer_table` 병합 로직 추가 |

### 데이터 구조 변경

#### news (교회 소식)
```python
# 이전 형식
"news": ["항목1", "항목2", ...]

# 새 형식
"news": {
    "worship": [{"title": "제목", "detail": "상세내용"}, ...],
    "recruit": [{"title": "제목", "detail": "상세내용"}, ...],
    "info": [{"title": "제목", "detail": "상세내용"}, ...]
}
```

#### raw_prayer_table (대표기도 표)
```python
"raw_prayer_table": {
    "headers": ["구분", "12/21(주)", "12/24(화)", "12/25(수)", "12/26(목)", "12/27(금)"],
    "rows": [
        ["1부", "김OO 장로", "이OO 장로", ...],
        ["2부", "박OO 장로", "최OO 장로", ...],
        ...
    ]
}
```

### 다음 작업
- [ ] 웹 프로그램에서 PDF 변환 테스트
- [ ] 여의도순복음교회 전용 템플릿 최종 검증
- [ ] 학습 데이터 수집 시스템 구현

---

## 2025-12-16 추가 작업 (2차)

### 네비게이션 버튼 재구성

#### 1. 말씀 버튼 → 오늘의 말씀
- **파일**: `church_html_generator.py:4176`
- **변경**: `href="#verse"` → `href="#todays-word"`
- **섹션명 변경**: "생명의 말씀" → "오늘의 말씀" (전체 파일)
- **영문**: "The Word of Life" → "Today's Word"

#### 2. 찬양 버튼 → 금주의 찬양
- **상태**: 이미 구현됨 (`href="#choir"` → `id="choir"`)
- **3페이지 표 추출**: `raw_choir_table` 필드로 원본 PDF 표 그대로 유지

#### 3. 소식 버튼 → 교회소식 (5페이지 전체)
- **파일**: `church_html_generator.py:5164-5259`
- **구조**: 카테고리별 아코디언 (예배/모집/안내)
- **각 항목**: 제목 클릭 시 상세내용 펼침
- **CSS 추가**: `church_html_generator.py:2678-2748`
  - `.news-item-detail-accordion`
  - `.news-item-summary`
  - `.news-item-detail-content`
  - `.news-item-simple`
  - `.news-num`

#### 4. 양식 버튼 → 오늘의 양식 (6페이지 전체)
- **파일**: `vision_ocr.py:527-541`
- **프롬프트 강화**: 문단별 추출, 전체 내용 필수
- **파싱 로직**: `vision_ocr.py:946-971`
  - `문단1:`, `문단2:` 형식 지원
  - 긴 줄은 자동으로 내용에 추가

### 네비게이션 탭 순서 (현재)
```
말씀 | 예배 | 찬양 | 소식 | 양식 | SNS | 헌금
```

### 섹션 ID 매핑
| 버튼 | href | 섹션 ID |
|------|------|---------|
| 말씀 | #todays-word | todays-word |
| 예배 | #worship | worship |
| 찬양 | #choir | choir |
| 소식 | #news | news |
| 양식 | #devotional | devotional |
| SNS | #sns | sns |
| 헌금 | #offering | offering |

---

## 2025-12-16 여의도순복음교회 미팅 결과 및 기능 고도화 계획

### 미팅 결과 요약
- **일자**: 2025-12-16 화요일 오후
- **대상**: 여의도순복음교회 IT팀 실무자
- **결과**: 매우 긍정적 반응, 내부 테스트 프로그램 제공 요청
- **배경**: 자료 3번 전송 후 첫 미팅

### 핵심 요구사항

#### 1. 15일 체험판 프로그램 제공
- 교회 내부 테스트용 프로그램 제공
- **수신일로부터 15일** 사용 기간 제한
- 여의도순복음교회 전용 템플릿 포함

#### 2. 성경/찬송 검색 및 다운로드 연동
- 교회 보유 라이선스 활용
- 성경 구절 검색 → 팝업 표시
- 찬송가 검색 → 가사 + 악보 **다운로드/저장** 기능
- **연동 방식**: 교회 내부 API 또는 라이선스 DB 연결

#### 3. FG라디오/FGTV OTT 연동
- **FGTV** + **FG라디오** 서비스 연동
- OTT/셋톱박스 연계 모바일 최적화
- 모바일 주보에서 FG라디오 채널 바로 청취 가능

#### 4. ARS 헌금 연동 (중요)
- 여의도순복음교회 홈페이지 ARS 시스템 그대로 연동
- 모바일 헌금 버튼 → ARS 전화 연결
- **추가 요구**: ARS 연결 시 **헌금자 식별 기능** 필요
  - 누가 헌금했는지 추적 가능하도록 업데이트

#### 5. 절기별 템플릿 시스템
- 대림절, 성탄절, 사순절, 부활절, 추수감사절 등
- 시즌별 테마 색상 및 레이아웃
- 관리자가 절기 선택 가능

#### 6. 주보 전용 HTML 편집기
- 기능 제한된 편집기 (주보 편집 업무만)
- 실무 담당자 업무 편의성 향상
- 텍스트, 이미지, 링크 편집만 허용

### 보류 사항
- **다국어 번역**: 영어 외 번역 불확실성으로 현재 보류
- 추후 검증된 번역 품질 확보 시 재검토

---

## 기능 고도화 구현 계획

### Phase 1: 핵심 인프라 (1주)

#### 1.1 라이선스 시스템
```python
# database/license_manager.py
class LicenseManager:
    def create_trial_license(church_id, days=30):
        """30일 체험판 라이선스 생성"""

    def validate_license(license_key):
        """라이선스 유효성 검증"""

    def get_remaining_days(license_key):
        """남은 사용일 반환"""
```

#### 1.2 교회 자산 연동 API
```python
# integrations/fg_church_api.py
class FGChurchAPI:
    def search_bible(reference):
        """성경 구절 검색 (교회 라이선스)"""

    def search_hymn(number):
        """찬송가 검색 + 다운로드 링크"""

    def get_radio_stream_url():
        """FG라디오 스트리밍 URL"""
```

### Phase 2: 미디어 연동 (1주)

#### 2.1 FG라디오/FGTV 연동
```html
<!-- 모바일 주보 내 라디오 플레이어 -->
<section id="fg-radio" class="section">
    <div class="radio-player">
        <button onclick="playFGRadio()">🎙️ FG라디오 듣기</button>
        <audio id="fg-radio-stream" src="..."></audio>
    </div>
</section>
```

#### 2.2 ARS 헌금 연동
```html
<!-- 헌금 섹션 - ARS 연동 -->
<div class="offering-ars">
    <a href="tel:ARS번호" class="ars-btn">
        📞 ARS 헌금 (1588-XXXX)
    </a>
    <a href="교회홈페이지헌금URL" class="web-offering-btn">
        💳 온라인 헌금
    </a>
</div>
```

### Phase 3: 절기별 템플릿 (1주)

#### 3.1 절기 프리셋 구조
```python
SEASONAL_PRESETS = {
    "advent": {
        "name": "대림절",
        "period": "12월 첫째 주 ~ 성탄절 전",
        "colors": {"primary": "#5B2C6F", "accent": "#8E44AD"},
        "icon": "🕯️",
        "greeting": "대림절을 맞이하여..."
    },
    "christmas": {
        "name": "성탄절",
        "period": "12월 25일",
        "colors": {"primary": "#C0392B", "accent": "#27AE60"},
        "icon": "🎄",
        "greeting": "메리 크리스마스!"
    },
    "lent": {
        "name": "사순절",
        "period": "재의 수요일 ~ 부활절 전",
        "colors": {"primary": "#4A235A", "accent": "#6C3483"},
        "icon": "✝️"
    },
    "easter": {
        "name": "부활절",
        "colors": {"primary": "#F4D03F", "accent": "#FFFFFF"},
        "icon": "🐣"
    },
    "thanksgiving": {
        "name": "추수감사절",
        "colors": {"primary": "#8B6914", "accent": "#D4883E"},
        "icon": "🌾"
    }
}
```

### Phase 4: 주보 편집기 (1주)

#### 4.1 제한된 HTML 편집기
```javascript
// static/bulletin-editor.js
class BulletinEditor {
    // 허용된 편집 기능만
    allowedFeatures = [
        'editText',      // 텍스트 수정
        'editImage',     // 이미지 교체
        'editLink',      // 링크 수정
        'editSchedule',  // 예배시간 수정
        'editStaff'      // 담당자 수정
    ];

    // 금지된 기능
    blockedFeatures = [
        'editCSS',       // 스타일 수정 불가
        'addScript',     // 스크립트 추가 불가
        'deleteSection'  // 섹션 삭제 불가
    ];
}
```

### 파일 구조 (예정)
```
StudySnap-Backend/
├── integrations/
│   ├── fg_church_api.py      # 교회 자산 API 연동
│   ├── fg_radio.py           # FG라디오 스트리밍
│   └── ars_offering.py       # ARS 헌금 연동
├── templates/
│   └── seasons/
│       ├── advent.json       # 대림절 템플릿
│       ├── christmas.json    # 성탄절 템플릿
│       ├── lent.json         # 사순절 템플릿
│       ├── easter.json       # 부활절 템플릿
│       └── thanksgiving.json # 추수감사절 템플릿
├── static/
│   ├── bulletin-editor.html  # 주보 편집기 UI
│   └── bulletin-editor.js    # 편집기 로직
└── database/
    └── license_manager.py    # 라이선스 관리
```

### 우선순위
1. **긴급**: 15일 체험판 + 여의도순복음교회 템플릿
2. **높음**: 성경/찬송 검색 연동, ARS 헌금 (헌금자 추적)
3. **중간**: FG라디오 연동, 절기별 템플릿
4. **낮음**: HTML 편집기 (마지막 단계)

---

## 🔐 체험판 제공 전략 및 기술 보호

### 핵심 고민사항
1. **기술 유출/노출 우려**: 설치형 프로그램 제공 시 소스코드 노출 위험
2. **호스팅 환경 미비**: 현재 Netlify, ngrok 등 무료 서비스만 사용 가능
3. **설치형 vs 클라우드**: 어떤 방식이 적합한가?

### 📋 배포 방식 비교

| 방식 | 장점 | 단점 | 기술 보호 |
|------|------|------|----------|
| **설치형 (로컬)** | 교회 자체 운영 가능, 데이터 보안 | 소스코드 노출, 업데이트 어려움 | ❌ 낮음 |
| **클라우드 (SaaS)** | 기술 보호, 자동 업데이트 | 호스팅 비용, 인터넷 필수 | ✅ 높음 |
| **하이브리드** | 프론트엔드만 제공, 백엔드는 API | 복잡한 구조 | ⚠️ 중간 |

### 🛡️ 권장 전략: 클라우드 기반 체험판

#### 1단계: 임시 클라우드 호스팅 (15일 체험판)
```
[교회 사용자] → [웹 브라우저] → [클라우드 서버 (AWS/GCP Free Tier)]
                                        ↓
                              [백엔드 API + DB]
                                        ↓
                              [기술 보호됨]
```

**장점**:
- 소스코드 노출 없음
- 15일 후 자동 만료 가능
- 사용 통계 수집 가능
- 업데이트 즉시 적용

#### 추천 무료/저가 호스팅 옵션
| 서비스 | 무료 티어 | 적합도 | 비고 |
|--------|----------|--------|------|
| **Railway** | $5/월 크레딧 | ⭐⭐⭐ | Python 지원, 간편 배포 |
| **Render** | 무료 (제한적) | ⭐⭐⭐ | 자동 배포, SSL 포함 |
| **Fly.io** | 무료 (3VM) | ⭐⭐ | Docker 기반 |
| **Oracle Cloud** | 영구 무료 | ⭐⭐⭐ | 2 VM, 안정적 |
| **AWS Free Tier** | 12개월 무료 | ⭐⭐ | EC2 t2.micro |

### 🔒 설치형 제공 시 보호 방안

만약 설치형을 제공해야 한다면:

#### A. 코드 난독화 (Obfuscation)
```bash
# PyArmor로 Python 코드 보호
pip install pyarmor
pyarmor obfuscate app.py
```

#### B. 바이너리 패키징
```bash
# PyInstaller로 실행 파일 생성
pip install pyinstaller
pyinstaller --onefile --add-data "templates;templates" app.py
```

#### C. 라이선스 키 검증 (필수)
```python
# 온라인 라이선스 서버에서 검증
class LicenseValidator:
    LICENSE_SERVER = "https://your-license-server.com/api"

    def validate(self, license_key):
        # 서버에서 검증 (만료일, 사용 횟수, IP 제한)
        response = requests.post(f"{self.LICENSE_SERVER}/validate", {
            "key": license_key,
            "machine_id": get_machine_id()
        })
        return response.json()["valid"]
```

#### D. 핵심 기능 API 분리
```
[설치형 프로그램]  ←→  [클라우드 API 서버]
     ↓                       ↓
 - UI/프론트엔드         - AI 변환 엔진
 - 로컬 캐시             - 성경/찬송 DB
 - 오프라인 뷰어         - 라이선스 검증
```

### 📊 데이터베이스 전략

#### 체험판용 경량 DB
```python
# SQLite 사용 (설치 불필요)
DATABASE_URL = "sqlite:///church_bulletin.db"

# 테이블 구조
- users (교회 관리자)
- bulletins (생성된 주보)
- offerings (헌금 기록 - ARS 연동)
- licenses (라이선스 정보)
```

#### 정식 도입 시 확장
```python
# PostgreSQL 마이그레이션
DATABASE_URL = "postgresql://user:pass@host/dbname"
```

### ✅ 최종 권장안

**15일 체험판 제공 방식**:

```
1. 클라우드 호스팅 (Railway/Render)
   - URL: https://fg-bulletin-trial.railway.app
   - 교회별 서브도메인: https://fgfc.fg-bulletin.com

2. 접근 제어
   - 교회 전용 로그인 ID/PW 발급
   - 15일 자동 만료
   - IP 기반 접속 제한 (선택)

3. 기능 제한 (체험판)
   - PDF 변환: 1일 10회 제한
   - 저장: 최대 30개 주보
   - 편집기: 읽기 전용 미리보기

4. 정식 도입 시
   - 전용 서버 또는 교회 인프라 설치
   - 무제한 사용
   - DB 마이그레이션 지원
```

### 💡 ARS 헌금자 추적 구현

```python
# 헌금 연동 플로우
class ARSOfferingTracker:
    def initiate_offering(self, user_id, amount, offering_type):
        """ARS 헌금 시작 - 고유 세션 생성"""
        session_id = generate_unique_session()

        # DB에 헌금 의향 기록
        db.offerings.insert({
            "session_id": session_id,
            "user_id": user_id,
            "phone": user.phone,
            "amount": amount,
            "type": offering_type,  # 십일조, 감사, 선교 등
            "status": "initiated",
            "created_at": datetime.now()
        })

        # ARS 번호에 세션 ID 포함
        return f"tel:1588-XXXX,{session_id}#"

    def confirm_offering(self, session_id, ars_callback_data):
        """ARS 완료 콜백 수신 (교회 시스템 연동 필요)"""
        db.offerings.update(
            {"session_id": session_id},
            {"status": "completed", "confirmed_at": datetime.now()}
        )
```

**참고**: ARS 헌금자 추적은 교회 ARS 시스템과의 API 연동이 필요합니다.
교회 IT팀에 ARS 콜백 API 제공 가능 여부 확인 필요.

---

## 🚀 Railway 배포 환경 구축 (2025-12-17)

### 생성된 파일

| 파일 | 용도 |
|------|------|
| `Procfile` | Railway/Heroku 시작 명령어 |
| `railway.json` | Railway 빌드/배포 설정 |
| `.env.example` | 환경변수 템플릿 |
| `database/license_manager.py` | 15일 체험판 라이선스 시스템 |

### Railway 배포 절차

```bash
# 1. Railway CLI 설치
npm install -g @railway/cli

# 2. 로그인
railway login

# 3. 프로젝트 초기화
railway init

# 4. 환경변수 설정
railway variables set ANTHROPIC_API_KEY=your_key_here
railway variables set TRIAL_DAYS=15
railway variables set DAILY_CONVERT_LIMIT=10

# 5. 배포
railway up

# 6. 도메인 확인
railway domain
```

### 라이선스 API 엔드포인트

| 엔드포인트 | 메서드 | 설명 |
|------------|--------|------|
| `/api/license/create-trial` | POST | 체험판 라이선스 생성 |
| `/api/license/status/{key}` | GET | 라이선스 상태 조회 |
| `/api/license/validate` | POST | 라이선스 유효성 검증 |
| `/api/license/fgfc-trial` | POST | 여의도순복음교회 전용 체험판 |
| `/api/license/list` | GET | 모든 라이선스 목록 (관리자) |
| `/api/license/extend` | POST | 라이선스 연장 |

### 라이선스 사용 예시

```javascript
// 1. 여의도순복음교회 체험판 생성
const response = await fetch('/api/license/fgfc-trial', { method: 'POST' });
const { license } = await response.json();
console.log(license.license_key);  // "FGFC-XXXXXXXX-XXXXXXXX"

// 2. 주보 변환 시 라이선스 키 포함
const formData = new FormData();
formData.append('file', pdfFile);
formData.append('church_name', '여의도순복음교회');
formData.append('bulletin_date', '2025-12-14');
formData.append('license_key', license.license_key);  // 라이선스 키 추가

await fetch('/api/church-convert-ai', {
    method: 'POST',
    body: formData
});
```

### 환경변수 설정 (Railway)

```env
# 필수
ANTHROPIC_API_KEY=sk-ant-...

# 체험판 설정
TRIAL_DAYS=15
DAILY_CONVERT_LIMIT=10
MAX_BULLETINS=30

# 서버 설정
PORT=8000
DEBUG=False
```

### 헬스체크

```bash
curl https://your-app.railway.app/health
# {"status":"healthy","version":"1.0.0","service":"StudySnap Backend"}
```
