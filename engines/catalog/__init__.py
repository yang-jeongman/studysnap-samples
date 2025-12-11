"""
기업 카탈로그 특화 엔진 (예정)
============================

기업 제품 카탈로그 변환에 특화된 엔진입니다.

주요 기능 (계획):
- 제품 카탈로그 PDF → 인터랙티브 웹 카탈로그 변환
- 제품 이미지, 사양, 가격 자동 추출
- 제품 비교 기능
- 장바구니/견적 요청 연동
- 제품 검색 및 필터링
- QR 코드 자동 생성 (제품별)

사용법 (예정):
    from engines.catalog import CatalogGenerator

    generator = CatalogGenerator()
    html = generator.generate(pdf_path, company="삼성전자")
"""

# 아직 구현되지 않음 - 향후 개발 예정
CatalogGenerator = None

__all__ = [
    "CatalogGenerator",
]
