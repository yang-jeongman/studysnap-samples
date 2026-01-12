"""
BulletinAI (주보지기) v4.0 - Vision API 통합
=====================================================

PDF를 직접 분석하여 섹션별 데이터를 추출합니다.

사용법:
    from learning_data.church_bulletin import get_bulletin_ai

    ai = get_bulletin_ai()
    ai.load_pdf(pdf_bytes)

    # 섹션별 직접 추출 (v4.0 방식)
    verse = ai.extract_today_verse()
    services = ai.extract_worship_services()

    # 또는 전체 추출
    all_data = ai.extract_all()
"""

from .bulletin_ai import BulletinAI, get_bulletin_ai, reset_bulletin_ai

__all__ = [
    "BulletinAI",
    "get_bulletin_ai",
    "reset_bulletin_ai",
]

__version__ = "4.0.0"
__name__ = "BulletinAI"
__name_kr__ = "주보지기"
