---
description: "K-MART 정산 시스템 작업 - 일별/기간별 정산, 리포트"
---

K-MART 정산 시스템 관련 작업을 수행합니다.

## 요청사항
$ARGUMENTS

## 정산 흐름
```
주문 완료 (status=delivered)
  ↓
DailySettlement 생성 (일별)
  ↓
Settlement 생성 (기간별)
  ↓
상태: pending → confirmed → paid/cancelled
  ↓
SettlementLog 기록
```

## 핵심 파일
- C:\k-mart\settlements\views.py (734줄)
- C:\k-mart\settlements\models.py

## 주요 뷰
- settlement_dashboard() - 대시보드
- daily_settlement_list/generate() - 일별 정산
- settlement_list/create/detail() - 기간별 정산
- settlement_report() - 리포트

## 정산 타입
- 일정산: 당일 주문 → 당일 정산
- 익일정산: 당일 주문 → 익일 정산

## 정산 계산
```python
total_sales: 총매출
commission: 수수료 (total_sales × commission_rate%)
settlement_amount: 정산금액 (total_sales - commission)
```

## 주의사항
- delivered 상태 주문만 정산 대상
- 정산-주문 연결 (SettlementOrder) 유지
- 이력 기록 (SettlementLog)
