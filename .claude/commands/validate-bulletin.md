# /validate-bulletin

변환된 주보 HTML의 품질을 검증하는 스킬

## Usage
```
/validate-bulletin [HTML파일경로]
```

## Arguments
- `HTML파일경로`: 검증할 HTML 파일 경로

## Validation Checklist

### 1. 섹션 제목 검증
- [ ] 섹션 제목이 PDF 원본에서 추출되었는가?
- [ ] 하드코딩된 제목이 없는가?
- [ ] 절기/행사별 제목이 정확한가? (성찬예배순, 송구영신예배순 등)

### 2. 예배 순서 검증
- [ ] 예배 순서가 PDF 원본과 동일한가?
- [ ] 위→아래 순서가 정확한가?
- [ ] 성찬 항목이 성찬주일에만 포함되는가?

### 3. 부별 정보 검증
- [ ] 부별 찬송이 정확히 분리되었는가?
- [ ] 부별 성경봉독 구절이 정확한가?
- [ ] 부별 설교 제목/설교자가 정확한가?

### 4. 데이터 재활용 검증
- [ ] 이전 주보의 데이터가 재활용되지 않았는가?
- [ ] 모든 데이터가 현재 PDF에서 추출되었는가?

### 5. UI 규칙 준수 검증
- [ ] 오늘의 말씀: 따옴표, 좌측정렬, 괄호, 흰색, 아코디언
- [ ] 예배순서: 동적 제목, 탭 형식, 설교 강조

## Process

### 1. HTML 파일 읽기
```python
with open(html_path, 'r', encoding='utf-8') as f:
    html_content = f.read()
```

### 2. 섹션 추출 및 검증
```python
from bs4 import BeautifulSoup
soup = BeautifulSoup(html_content, 'html.parser')

# 각 섹션 검증
sections = {
    'todays-word': soup.find(id='todays-word'),
    'worship': soup.find(id='worship'),
    'sermon-word': soup.find(id='sermon-word'),
    'news': soup.find(id='news'),
    'devotional': soup.find(id='devotional')
}
```

### 3. PDF 원본과 비교
```python
# PDF에서 추출된 데이터와 HTML 비교
for section_id, element in sections.items():
    if element:
        validate_section(section_id, element, pdf_data)
```

## Output Format
```
## 주보 검증 결과

**파일**: [HTML 파일명]
**검증 시간**: [시간]

### 섹션별 결과
| 섹션 | 상태 | 비고 |
|------|------|------|
| 오늘의 말씀 | ✅ | 규칙 준수 |
| 예배순서 | ✅ | 성찬예배순 정확 |
| 생명의 말씀 | ⚠️ | 소제목 누락 |
| ... | ... | ... |

### 발견된 문제
1. [문제 설명]
   - 원인: ...
   - 해결: ...

### 권장 조치
- [ ] ...
```

## Example
```
/validate-bulletin "C:\StudySnap-Backend\outputs\Church\여의도순복음교회\2026-01-04.html"
```
