# /update-ui-rule

BulletinAI UI 규칙을 업데이트하는 스킬

## Usage
```
/update-ui-rule [섹션명] [규칙설명]
```

## Arguments
- `섹션명`: 업데이트할 섹션 (todays_verse, worship_order, sermon_word, etc.)
- `규칙설명`: 새로운 규칙에 대한 설명

## Core Principle
**전문가가 직접 코드를 수정하지 않고 BulletinAI가 학습하여 작업한다**

## Process

### 1. 기존 규칙 확인
```python
# ui_rules.json 읽기
rules = load_json("learning_data/church_bulletin/ui_rules.json")
section_rules = rules["sections"].get(section_name, {})
```

### 2. 규칙 업데이트
```python
# 새 규칙 추가
rules["sections"][section_name]["rules"][new_rule_key] = {
    "value": new_value,
    "description": description
}

# 저장
save_json("learning_data/church_bulletin/ui_rules.json", rules)
```

### 3. BulletinAI 메서드 확인
해당 섹션의 generate 메서드가 새 규칙을 읽도록 확인:
- `generate_todays_verse_html()` - todays_verse 규칙
- `generate_worship_order_html()` - worship_order 규칙

### 4. improvement_log.json 기록
```python
# 학습 기록 추가
log["development_phases"].append({
    "phase": "UI 규칙 업데이트",
    "date": today,
    "issues": [issue],
    "solutions": [solution],
    "result": result,
    "learning_notes": [notes]
})
```

## Example
```
/update-ui-rule todays_verse "말씀 텍스트를 이탤릭체로 표시"
```

## Available Sections
| 섹션명 | 설명 |
|--------|------|
| todays_verse | 오늘의 말씀 (아코디언) |
| worship_order | 예배순서 (탭 형식) |
| sermon_word | 생명의 말씀 |
| church_news | 교회소식 |
| devotional | 오늘의 양식 |
| choir | 금주의 찬양 |
