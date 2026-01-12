# /convert-bulletin

주보 PDF를 HTML로 변환하는 스킬

## Usage
```
/convert-bulletin [PDF경로] [교회명]
```

## Arguments
- `PDF경로`: 변환할 PDF 파일 경로 (기본: 최근 업로드된 파일)
- `교회명`: 교회 이름 (기본: 여의도순복음교회)

## Process

### 1. 사전 검증
```python
# 학습 규칙 확인
ui_rules = load_json("learning_data/church_bulletin/ui_rules.json")

# BulletinAI 상태 확인
from learning_data.church_bulletin import get_bulletin_ai
ai = get_bulletin_ai()
print(ai.get_status())
```

### 2. PDF 로드 및 섹션 추출
```python
# PDF 로드
ai.load_pdf(pdf_content)

# 모든 섹션 추출 (병렬 가능)
sections = ai.extract_all()
# - today_verse (3페이지)
# - worship_services (2페이지)
# - sermon_word (4페이지)
# - church_news (5페이지)
# - devotional (6페이지)
# - choir (3페이지)
```

### 3. HTML 생성
```python
# BulletinAI가 학습된 규칙에 따라 HTML 생성
from church_html_generator import ChurchBulletinGenerator

generator = ChurchBulletinGenerator(church_name)
html = generator.generate(sections)
```

### 4. 결과 검증
- 섹션 제목이 PDF에서 추출되었는지 확인
- 예배 순서가 정확한지 확인
- 부별 정보가 분리되었는지 확인

## Example
```
/convert-bulletin "C:\Users\jmyang\Downloads\주보\여의도순복음교회\2026-01-04.pdf" 여의도순복음교회
```

## Output
변환된 HTML 파일 경로와 검증 결과 출력
