"""
지자체 소식지 특화 엔진 (예정)
============================

지방자치단체 소식지 변환에 특화된 엔진입니다.

주요 기능 (계획):
- 지자체 소식지 PDF → 모바일 HTML 변환
- 공지사항, 행사 일정, 민원 정보 자동 추출
- 주민센터 연락처 자동 링크
- 지도/위치 정보 연동
- 다국어 자동 번역 (외국인 주민용)

사용법 (예정):
    from engines.newsletter import NewsletterGenerator

    generator = NewsletterGenerator()
    html = generator.generate(pdf_path, municipality="서울시 강남구")
"""

# 아직 구현되지 않음 - 향후 개발 예정
NewsletterGenerator = None

__all__ = [
    "NewsletterGenerator",
]
