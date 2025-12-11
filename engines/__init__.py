"""
StudySnap 엔진 모듈
==================

공통 엔진과 카테고리별 특화 엔진을 분리하여 관리합니다.

디렉토리 구조:
├── common/      - 모든 카테고리에서 공통으로 사용되는 엔진
├── election/    - 선거 홍보물 특화 엔진
├── church/      - 교회 주보 특화 엔진
├── lecture/     - 대학 강의 자료 특화 엔진
├── newsletter/  - 지자체 소식지 특화 엔진
├── catalog/     - 기업 카탈로그 특화 엔진
└── language/    - 외국어 학습기 특화 엔진

사용법:
    from engines.common import VisionOCR, UniversalParser
    from engines.church import ChurchBulletinGenerator
    from engines.election import ElectionConverter
"""

__version__ = "1.0.0"

# 공통 엔진 불러오기
from .common import (
    VisionOCRClient,
    UniversalParser,
    VerificationSystem,
    LearningSystem,
    TemplateEngine,
    LocalizationManager,
)

# 카테고리별 특화 엔진 불러오기
from .election import ElectionConverter
from .church import ChurchBulletinGenerator

__all__ = [
    # 공통 엔진
    "VisionOCRClient",
    "UniversalParser",
    "VerificationSystem",
    "LearningSystem",
    "TemplateEngine",
    "LocalizationManager",
    # 특화 엔진
    "ElectionConverter",
    "ChurchBulletinGenerator",
]
