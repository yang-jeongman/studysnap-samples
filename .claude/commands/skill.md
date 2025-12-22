---
description: "새 스킬 패키지 생성"
---

새로운 스킬 패키지를 생성합니다.

## 스킬 정보
$ARGUMENTS

## 생성 절차
1. 스킬 목적과 워크플로우 확인
2. 필요한 스크립트/레퍼런스 결정
3. 폴더 구조 생성
4. SKILL.md 및 관련 파일 작성

## 폴더 구조
```
.claude/skills/{skill-name}/
├── SKILL.md              # 필수: 메인 지침
├── scripts/              # 선택: 실행 스크립트
│   └── main.py
├── references/           # 선택: 참조 문서
│   └── schema.md
└── assets/              # 선택: 템플릿, 이미지
    └── template.html
```

## SKILL.md 템플릿
```markdown
---
name: {skill-name}
description: "{설명}. Use when {트리거 조건}."
---

# {스킬 이름}

## 개요
{스킬 설명}

## 워크플로우
1. {단계 1}
2. {단계 2}
3. {단계 3}

## 스크립트
- scripts/main.py - {기능}

## 출력
{결과물}
```

스킬 정보를 바탕으로 생성해주세요.
