---
description: "K-MART 모델 작업 - Django ORM, 마이그레이션"
---

K-MART 모델 관련 작업을 수행합니다.

## 요청사항
$ARGUMENTS

## 핵심 모델 위치
- C:\k-mart\accounts\models.py - Member
- C:\k-mart\products\models.py - Product, RetailerProduct, Category, StockLog
- C:\k-mart\orders\models.py - Order, OrderItem, Cart, CartItem
- C:\k-mart\settlements\models.py - Settlement, DailySettlement

## Member 모델 구조
```python
user_type: 도매점 / 소매점 / 소비자
parent: ForeignKey(Member)  # 상위 거래처 (계층 구조)
discount_rate: DecimalField  # 할인율
settlement_type: 일정산 / 익일정산
```

## Product 모델 구조
```python
owner: ForeignKey(Member)    # 도매점
cost_price → wholesale_price → retail_price
order_code: CharField        # 카톡 주문 링크
```

## Order 모델 구조
```python
trade_type: W2R / W2C / R2C
seller/buyer: ForeignKey(Member)
status: pending→confirmed→preparing→shipped→delivered/cancelled
```

## 작업 후 필수
```bash
python manage.py makemigrations
python manage.py migrate
python manage.py runserver --settings=config.settings_local
```
