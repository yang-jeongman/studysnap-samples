---
name: parse-table
description: "OCR 테이블 파싱 분석 및 디버깅. vision_ocr.py의 테이블 컬럼 매핑 문제를 진단하고 수정합니다."
---

# /parse-table

OCR에서 추출된 테이블 데이터의 파싱 문제를 분석하고 수정합니다.

## 실행 시

1. **현재 파싱 로직 확인**
   - `vision_ocr.py` 라인 786-858 읽기
   - 테이블 파싱 조건문 분석

2. **테스트 실행**
   ```bash
   cd C:\StudySnap-Backend
   python test_api_flow.py
   ```

3. **결과 분석**
   - `worship_services` 배열 검증
   - 각 필드(scripture, sermon_title, sermon_pastor) 확인
   - 누락 또는 잘못된 매핑 식별

4. **수정 적용**
   - 컬럼 수별 처리 로직 개선
   - 헤더 기반 매핑 추가 (필요시)
   - 콘텐츠 기반 감지 추가 (필요시)

## 예상 출력

```
## 테이블 파싱 분석 결과

### 감지된 테이블 형식
- 컬럼 수: 4개
- 헤더: [구분, 찬양, 설교제목, 설교자]
- 유형: 찬양대 포함 형식

### 매핑 상태
| 필드 | 값 | 상태 |
|------|-----|------|
| name | 1부 | ✅ |
| scripture | - | ⚠️ 별도 섹션에서 추출 필요 |
| sermon_title | 겨울이 오면 | ✅ |
| sermon_pastor | 엄태욱 목사 | ✅ |

### 권장 수정
- vision_ocr.py:820-835 컬럼 감지 로직 개선
```

## 관련 에이전트

이 명령은 `table-column-parser` 에이전트와 연동됩니다.
복잡한 파싱 문제는 에이전트를 직접 호출하세요:
```
@table-column-parser 6컬럼 테이블 파싱 문제 해결
```
