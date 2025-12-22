---
description: "새 서브 에이전트 생성"
---

새로운 서브 에이전트를 생성합니다.

## 에이전트 정보
$ARGUMENTS

## 생성 절차
1. 에이전트 목적과 트리거 조건 확인
2. 필요한 도구(tools) 결정
3. 모델 선택 (haiku/sonnet/opus)
4. .claude/agents/{name}.md 파일 생성

## 템플릿
```markdown
---
name: {kebab-case-name}
description: "{설명}. Use PROACTIVELY when {트리거 조건}."
tools:
  - Read
  - Grep
  - Glob
model: sonnet
---

# Role
{역할 설명}

# When Invoked
1. {첫 번째 동작}
2. {두 번째 동작}
3. {세 번째 동작}

# Responsibilities
- {책임 1}
- {책임 2}
- {책임 3}

# Guidelines
- {지침 1}
- {지침 2}

# Output Format
{출력 형식}
```

## 도구 옵션
- Read, Write, Edit: 파일 작업
- Grep, Glob: 검색
- Bash: 시스템 명령
- WebFetch, WebSearch: 웹

에이전트 정보를 바탕으로 생성해주세요.
