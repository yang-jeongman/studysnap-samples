---
description: "K-MART 주문 시스템 작업 - 미니쇼핑몰, 장바구니, 주문 처리"
---

K-MART 주문 시스템 관련 작업을 수행합니다.

## 요청사항
$ARGUMENTS

## 주문 흐름
```
카톡 링크 (/order/<order_code>/) 또는 (/order/r/<order_code>/)
  ↓
미니쇼핑몰 표시
  ↓
주문정보 입력
  ↓
Order 생성 (비회원: 자동 Member 생성)
  ↓
상태 관리: pending → confirmed → preparing → shipped → delivered
  ↓
shipped 시 재고 차감 (StockLog)
  ↓
delivered 시 정산 대상
```

## 핵심 파일
- C:\k-mart\orders\views.py (602줄)
- C:\k-mart\orders\models.py
- C:\k-mart\orders\urls.py

## 주요 뷰
- mini_shop() - 도매점 미니쇼핑몰
- retailer_mini_shop() - 소매점 미니쇼핑몰
- order_list() - 주문 목록
- cart_view/add/update/checkout - 장바구니

## 거래 유형
- W2R: 도매점 → 소매점
- W2C: 도매점 → 소비자
- R2C: 소매점 → 소비자

## 주의사항
- trade_type 정확히 설정
- 출고 시 StockLog 필수 기록
- 취소 시 재고 복원
