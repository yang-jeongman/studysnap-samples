"""
교회 주보 특화 엔진
==================

교회 주보 PDF 변환에 특화된 엔진입니다.

주요 기능:
- 교회 주보 PDF → 모바일 HTML 변환
- 예배 순서, 설교 본문, 교회 소식 자동 추출
- 성경 구절 팝업, 찬송가 팝업 지원
- SNS 링크, 온라인 헌금, 설교 다운로드 메뉴
- 테마 지원 (기본, 추수감사절, 성탄절, 부활절)

사용법:
    from engines.church import ChurchBulletinGenerator

    generator = ChurchBulletinGenerator()
    html = generator.generate(extracted_data, title="주보 제목", theme="default")
"""

import sys
import os

# 상위 디렉토리를 path에 추가
_parent_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _parent_dir not in sys.path:
    sys.path.insert(0, _parent_dir)

# 기존 모듈에서 import
try:
    from church_html_generator import (
        ChurchBulletinGenerator,
        get_church_bulletin_generator,
    )
except ImportError:
    ChurchBulletinGenerator = None
    get_church_bulletin_generator = None


__all__ = [
    "ChurchBulletinGenerator",
    "get_church_bulletin_generator",
]
