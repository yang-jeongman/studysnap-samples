"""
공통 엔진 모듈
=============

모든 카테고리(선거, 교회, 대학강의, 지자체, 기업, 외국어)에서
공통으로 사용되는 핵심 엔진들을 제공합니다.

주요 구성:
- vision_ocr.py: Claude Vision 기반 OCR 엔진
- universal_parser.py: 범용 PDF/이미지 파서
- pdf_converter.py: PDF 변환 기본 엔진
- vision_pdf_processor.py: Vision 기반 PDF 처리
- verification_system.py: 변환 품질 검증 시스템
- learning_system.py: AI 학습 시스템
- template_engine.py: 템플릿 렌더링 엔진
- localization.py: 다국어 지원
- intelligent_layout_engine.py: 지능형 레이아웃 엔진
- advanced_layout_optimizer.py: 고급 레이아웃 최적화
- base_html_generator.py: HTML 생성 기본 클래스
"""

import sys
import os

# 상위 디렉토리를 path에 추가하여 기존 모듈 import 가능하게 함
_parent_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _parent_dir not in sys.path:
    sys.path.insert(0, _parent_dir)

# 기존 모듈에서 import (하위 호환성 유지)
try:
    from vision_ocr import VisionOCRClient, get_vision_ocr_client
except ImportError:
    VisionOCRClient = None
    get_vision_ocr_client = None

try:
    from universal_parser import UniversalParser, get_universal_parser
except ImportError:
    UniversalParser = None
    get_universal_parser = None

try:
    from pdf_converter import PDFConverter
except ImportError:
    PDFConverter = None

try:
    from vision_pdf_processor import VisionPDFProcessor
except ImportError:
    VisionPDFProcessor = None

try:
    from verification_system import VerificationSystem
except ImportError:
    VerificationSystem = None

try:
    from learning_system import LearningSystem
except ImportError:
    LearningSystem = None

try:
    from template_engine import TemplateEngine, get_template_engine
except ImportError:
    TemplateEngine = None
    get_template_engine = None

try:
    from localization import LocalizationManager, get_localization_manager
except ImportError:
    LocalizationManager = None
    get_localization_manager = None

try:
    from intelligent_layout_engine import IntelligentLayoutEngine
except ImportError:
    IntelligentLayoutEngine = None

try:
    from advanced_layout_optimizer import AdvancedLayoutOptimizer
except ImportError:
    AdvancedLayoutOptimizer = None


__all__ = [
    # OCR & 파싱
    "VisionOCRClient",
    "get_vision_ocr_client",
    "UniversalParser",
    "get_universal_parser",
    "PDFConverter",
    "VisionPDFProcessor",

    # 검증 & 학습
    "VerificationSystem",
    "LearningSystem",

    # 템플릿 & 다국어
    "TemplateEngine",
    "get_template_engine",
    "LocalizationManager",
    "get_localization_manager",

    # 레이아웃
    "IntelligentLayoutEngine",
    "AdvancedLayoutOptimizer",
]
