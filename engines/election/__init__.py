"""
선거 홍보물 특화 엔진
====================

선거 홍보물(선거 공보, 후보자 포스터 등) 변환에 특화된 엔진입니다.

주요 기능:
- 선거 공보물 PDF → 모바일 HTML 변환
- 후보자 정보, 공약, 약력 자동 추출
- 정당별 색상 및 스타일 자동 적용
- 선거관리위원회 규정 준수 검증

사용법:
    from engines.election import ElectionConverter

    converter = ElectionConverter()
    result = converter.convert(pdf_path, party_name, candidate_name)
"""

import sys
import os

# 상위 디렉토리를 path에 추가
_parent_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _parent_dir not in sys.path:
    sys.path.insert(0, _parent_dir)

# 기존 모듈에서 import
try:
    from auto_election_converter import AutoElectionConverter as ElectionConverter
except ImportError:
    ElectionConverter = None

try:
    from html_generator import HTMLGenerator as ElectionHTMLGenerator
except ImportError:
    ElectionHTMLGenerator = None


__all__ = [
    "ElectionConverter",
    "ElectionHTMLGenerator",
]
