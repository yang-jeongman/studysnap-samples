"""
대학 강의 자료 특화 엔진 (예정)
============================

대학 강의 PDF 자료 변환에 특화된 엔진입니다.

주요 기능 (계획):
- 강의 자료 PDF → 인터랙티브 HTML 변환
- 슬라이드 → 웹 프레젠테이션 변환
- 수식, 도표, 그래프 자동 인식 및 변환
- 강의 노트 자동 생성
- 플래시카드 자동 생성 (학습용)
- 퀴즈 자동 생성

사용법 (예정):
    from engines.lecture import LectureGenerator

    generator = LectureGenerator()
    html = generator.generate(pdf_path, subject="mathematics")
"""

import sys
import os

# 상위 디렉토리를 path에 추가
_parent_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _parent_dir not in sys.path:
    sys.path.insert(0, _parent_dir)

# 기존 모듈에서 import
try:
    from lecture_generator import LectureGenerator
except ImportError:
    LectureGenerator = None


__all__ = [
    "LectureGenerator",
]
