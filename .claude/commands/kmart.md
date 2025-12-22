---
description: "K-MART 유통관리시스템 작업 - Django 개발, 도매-소매-소비자 연계"
---

K-MART 유통관리시스템 작업을 시작합니다.

## 요청사항
$ARGUMENTS

## 프로젝트 정보
- **경로**: C:\k-mart\
- **프레임워크**: Django 6.0
- **서버**: 115.21.251.90:8001

## 핵심 앱
- accounts/ - 회원 관리 (Member: 도매점/소매점/소비자)
- products/ - 상품 관리 (Product, RetailerProduct, Category)
- orders/ - 주문 관리 (Order, OrderItem, Cart)
- settlements/ - 정산 관리 (Settlement, DailySettlement)

## 3단계 계층 구조
```
도매점 (Wholesaler)
└── 소매점 (Retailer) ← parent = 도매점
    └── 소비자 (Consumer) ← parent = 소매점
```

## 거래 유형
- W2R: 도매점 → 소매점
- W2C: 도매점 → 소비자 (직영)
- R2C: 소매점 → 소비자

## 개발 명령어
```bash
# 로컬 서버
python manage.py runserver --settings=config.settings_local

# 마이그레이션
python manage.py makemigrations
python manage.py migrate

# 서버 배포
ssh jmyang@115.21.251.90 "cd /home/jmyang/k-mart && git pull && sudo systemctl restart kmart"
```

kmart-system-expert 에이전트의 지식을 활용하여 작업해주세요.
