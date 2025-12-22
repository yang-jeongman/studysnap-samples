# Claude Code 서브 에이전트 & 스킬 시스템

이 폴더는 Claude Code의 확장 기능을 담고 있습니다. 서브 에이전트, 스킬, 슬래시 명령어를 통해 반복 작업을 자동화하고 생산성을 극대화할 수 있습니다.

## 폴더 구조

```
.claude/
├── agents/                    # 서브 에이전트 (12개)
│   ├── code-reviewer.md       # 코드 리뷰 전문가
│   ├── file-organizer.md      # 파일/폴더 정리
│   ├── doc-generator.md       # 문서 생성
│   ├── church-bulletin-expert.md  # 교회 주보 전문가
│   ├── fgfc-bulletin-converter.md # 여의도순복음교회 주보 변환
│   ├── kmart-system-expert.md # K-MART 유통관리시스템 전문가
│   ├── api-tester.md          # API 테스트
│   ├── git-helper.md          # Git 작업 도우미
│   │
│   │  # 품질 보증 에이전트 시스템 (NEW)
│   ├── quality-assurance-coordinator.md  # 품질 검증 코디네이터 ⭐
│   ├── ocr-accuracy-verifier.md          # OCR 정확도 검증
│   ├── content-validator.md              # 콘텐츠 무결성/환각 탐지
│   └── learning-feedback-collector.md    # 학습 피드백 수집
│
├── skills/                    # 스킬 패키지
│   ├── subagent-creator/      # 서브 에이전트 생성 스킬
│   ├── skill-creator/         # 스킬 생성 스킬
│   └── slash-command-creator/ # 슬래시 명령어 생성 스킬
│
├── commands/                  # 슬래시 명령어 (11개)
│   ├── review.md              # /review - 코드 리뷰
│   ├── church.md              # /church - 교회 주보 작업
│   ├── test.md                # /test - 서버/API 테스트
│   ├── organize.md            # /organize - 파일 정리
│   ├── deploy.md              # /deploy - 배포
│   ├── agent.md               # /agent - 에이전트 생성
│   ├── skill.md               # /skill - 스킬 생성
│   ├── kmart.md               # /kmart - K-MART 시스템 작업 ⭐
│   ├── kmart-model.md         # /kmart-model - Django 모델 작업
│   ├── kmart-order.md         # /kmart-order - 주문 시스템
│   └── kmart-settlement.md    # /kmart-settlement - 정산 시스템
│
└── settings.local.json        # 로컬 권한 설정
```

---

## 빠른 시작

### 1. 슬래시 명령어 사용

Claude Code에서 `/명령어`를 입력하면 자동으로 프롬프트가 확장됩니다.

```
/review                    # 최근 코드 리뷰
/review 보안 취약점 검토     # 특정 주제로 리뷰
/church 오늘의 말씀 스타일   # 교회 주보 작업
/test API 엔드포인트        # 서버 테스트
/organize outputs 폴더     # 파일 정리
/deploy Railway            # 배포
```

### 2. 서브 에이전트 활용

Claude Code는 작업에 적합한 서브 에이전트를 자동으로 호출합니다:

- **code-reviewer**: 코드 작성/수정 후 자동 리뷰
- **file-organizer**: 파일 정리 요청 시
- **doc-generator**: 문서화 요청 시
- **church-bulletin-expert**: 교회 주보 작업 시
- **api-tester**: API 테스트 요청 시
- **git-helper**: Git 관련 작업 시

### 3. 새 에이전트/스킬 생성

```
/agent PDF 변환 전문가      # 새 에이전트 생성
/skill YouTube 자막 추출    # 새 스킬 생성
```

---

## 서브 에이전트 상세

### code-reviewer
```
역할: 코드 품질, 보안, 성능 검토
도구: Read, Grep, Glob
모델: sonnet
트리거: 코드 작성/수정 후 자동
```

### file-organizer
```
역할: 파일 이동, 폴더 생성, 정리
도구: Read, Glob, Grep, Bash
모델: haiku
트리거: "정리해줘", "organize" 등
```

### doc-generator
```
역할: README, API 문서, 주석 생성
도구: Read, Grep, Glob
모델: sonnet
트리거: "문서화", "README" 등
```

### church-bulletin-expert
```
역할: 교회 주보 HTML 생성 전문가
도구: Read, Grep, Glob
모델: sonnet
트리거: 교회 주보 관련 작업
```

### api-tester
```
역할: Flask API 테스트 및 디버깅
도구: Bash, Read, Grep
모델: haiku
트리거: API 테스트 요청
```

### git-helper
```
역할: Git 브랜치, 머지, 히스토리 관리
도구: Bash, Read, Grep
모델: haiku
트리거: Git 관련 복잡한 작업
```

### kmart-system-expert ⭐
```
역할: K-MART 유통관리시스템 전문가 (B2B2C)
도구: Read, Write, Edit, Grep, Glob, Bash
모델: sonnet
트리거: k-mart, 유통, 도매-소매, Django 모델/주문/정산
프로젝트: C:\k-mart\
```

**핵심 지식:**
- 도매점-소매점-소비자 3단계 계층 구조
- Django 6.0 ORM 패턴
- 거래 유형: W2R(도매→소매), W2C(도매→소비자), R2C(소매→소비자)
- 주문 상태 흐름: pending→confirmed→preparing→shipped→delivered
- 정산 시스템: 일정산/익일정산

### fgfc-bulletin-converter
```
역할: 여의도순복음교회 주보 PDF→HTML 변환
도구: Read, Write, Edit, Grep, Glob, Bash
모델: sonnet
트리거: FGFC, 여의도순복음교회, 주보 변환
```

---

## 품질 보증 에이전트 시스템 (NEW)

PDF→HTML 변환 품질을 100%로 보장하기 위한 자동화된 에이전트 파이프라인입니다.

### quality-assurance-coordinator ⭐
```
역할: 품질 검증 코디네이터 (다른 에이전트들을 조율)
도구: Read, Write, Edit, Grep, Glob, Task
모델: sonnet
트리거: 변환 완료 후 자동, /quality-check 명령어
```

**파이프라인:**
```
[OCR 검증] → [콘텐츠 검증] → [스타일 검증] → [번역 검증] → [학습 피드백]
```

### ocr-accuracy-verifier
```
역할: OCR 텍스트 정확도 검증
도구: Read, Grep, Glob
모델: haiku
기능:
  - PDF 원본 대비 텍스트 일치율 측정
  - 일반적인 OCR 오류 자동 교정 (순북음→순복음)
  - 누락된 필수 필드 탐지
```

### content-validator
```
역할: 콘텐츠 무결성 및 환각(Hallucination) 탐지
도구: Read, Grep, Glob
모델: haiku
기능:
  - 가상 데이터 탐지 ("추수감사절 찬양" 같은 환각)
  - 제목과 내용 매칭 검증
  - 필수 섹션 구조 확인
```

### learning-feedback-collector
```
역할: 학습 피드백 수집 및 규칙 자동 생성
도구: Read, Write, Edit, Grep
모델: haiku
기능:
  - 오류 패턴 저장 (error_patterns.jsonl)
  - 성공 패턴 기록 (success_patterns.jsonl)
  - 3회 이상 반복 오류 → 자동 교정 규칙 생성
  - ActiveLearningEngine 연동
```

**품질 지표:**
| 지표 | 목표 | 설명 |
|------|------|------|
| OCR 정확도 | 99%+ | PDF 원본 대비 텍스트 일치율 |
| 콘텐츠 무결성 | 100% | 환각 0%, 필수 필드 100% |
| 스타일 일관성 | 95%+ | 참조 템플릿 대비 CSS 일치율 |
| 전체 품질 | 98%+ | 위 지표 가중 평균 |

---

## 스킬 상세

### subagent-creator
새로운 서브 에이전트를 생성하는 가이드 스킬

**사용법:**
```
"새 에이전트 만들어줘: 이미지 최적화 전문가"
```

### skill-creator
새로운 스킬 패키지를 생성하는 가이드 스킬

**사용법:**
```
"스킬 만들어줘: PDF 텍스트 추출"
```

### slash-command-creator
새로운 슬래시 명령어를 생성하는 가이드 스킬

**사용법:**
```
"명령어 만들어줘: /backup"
```

---

## 슬래시 명령어 상세

| 명령어 | 설명 | 예시 |
|--------|------|------|
| `/review` | 코드 리뷰 | `/review 보안 점검` |
| `/church` | 교회 주보 작업 | `/church 오늘의 말씀 수정` |
| `/test` | 서버/API 테스트 | `/test health check` |
| `/organize` | 파일 정리 | `/organize outputs 폴더` |
| `/deploy` | 배포 | `/deploy Railway` |
| `/agent` | 에이전트 생성 | `/agent PDF 변환기` |
| `/skill` | 스킬 생성 | `/skill 이미지 처리` |
| `/kmart` | K-MART 시스템 작업 | `/kmart 소매점 할인율 수정` |
| `/kmart-model` | Django 모델 작업 | `/kmart-model Member에 필드 추가` |
| `/kmart-order` | 주문 시스템 | `/kmart-order 미니쇼핑몰 수정` |
| `/kmart-settlement` | 정산 시스템 | `/kmart-settlement 일별 정산 로직` |
| `/quality-check` | 품질 검증 (NEW) | `/quality-check 2025-12-19.html` |

---

## 병렬 에이전트 실행

복잡한 작업을 여러 에이전트가 동시에 처리하도록 할 수 있습니다:

```
"코드 리뷰, 문서화, 테스트를 병렬로 실행해줘"
```

Claude Code는 자동으로:
1. code-reviewer 에이전트로 코드 검토
2. doc-generator 에이전트로 문서 생성
3. api-tester 에이전트로 테스트 실행

---

## 컨텍스트 엔지니어링 팁

### 1. 스크립트로 분리
반복되는 작업은 Python 스크립트로 분리하면 LLM 컨텍스트를 절약합니다.

```python
# .claude/skills/my-skill/scripts/process.py
def main():
    # 복잡한 로직을 스크립트로
    pass
```

### 2. 레퍼런스 문서 활용
자주 참조하는 정보는 references/ 폴더에 저장:

```
.claude/skills/my-skill/references/
├── api-schema.md
├── data-format.md
└── examples.md
```

### 3. 프롬프트 재사용
자주 쓰는 프롬프트는 슬래시 명령어로 저장:

```markdown
# .claude/commands/my-command.md
---
description: "자주 쓰는 작업"
---
{프롬프트 내용}
$ARGUMENTS
```

---

## 새 에이전트 만들기 (예시)

### 1. 파일 생성
`.claude/agents/my-agent.md`:

```markdown
---
name: my-agent
description: "내 커스텀 에이전트. Use when user asks for X."
tools:
  - Read
  - Grep
  - Glob
model: sonnet
---

# Role
당신은 X 전문가입니다.

# When Invoked
1. 먼저 Y를 확인
2. 그 다음 Z를 수행
3. 결과 보고

# Guidelines
- 항상 A를 먼저 체크
- B는 피하기
```

### 2. 자동 활성화
description에 명시된 트리거 조건에 맞으면 자동으로 호출됩니다.

---

## 참고 자료

- [영상] 클로드 코드 서브 에이전트 활용법
- [GitHub] https://github.com/greatSumini/cc-system
- [Monet] https://www.monet.design/

---

## 문의

문제가 있거나 새로운 에이전트/스킬이 필요하면 Claude Code에서 직접 요청하세요:

```
"새 에이전트 만들어줘: [원하는 기능]"
"이 작업을 자동화하고 싶어"
```
