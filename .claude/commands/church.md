---
description: "교회 주보 시스템 작업 - HTML 생성, 스타일링, 번역"
---

교회 주보 HTML 생성 시스템 작업을 시작합니다.

## 요청사항
$ARGUMENTS

## 핵심 파일
- church_html_generator.py - HTML 생성 엔진
- vision_ocr.py - Claude Vision OCR + 번역
- app.py - Flask API 엔드포인트
- church_bible_hymn_utils.py - 성경/찬송 유틸리티

## 품질 기준 (참조: CLAUDE.md)
- 8개국어 지원 (ko, en, zh, ja, id, es, ru, fr)
- data-i18n 속성으로 모든 텍스트 번역 가능
- 폴백: 선택언어 → 영어 → 한국어
- 성경 구절 클릭 → 다국어 팝업
- 찬송가 번호 클릭 → 다국어 가사 팝업

## 참조 템플릿
outputs/Church/여의도순복음교회/fg-2025-12-14_외국어 서비스.html

CLAUDE.md의 지침을 따라 작업해주세요.
