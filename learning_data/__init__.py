"""
StudySnap Learning Data Module
PDF 모바일 최적화를 위한 학습 시스템

모듈 구성:
- schema: 데이터 구조 정의
- classifier: 객체 분류 엔진
- validator: 텍스트 검증 시스템
"""

from .schema import (
    ObjectType,
    FontStyle,
    TextAlignment,
    BoundingBox,
    TextStyle,
    PDFObject,
    HTMLMapping,
    DocumentStructure,
    LearningExample,
    ValidationResult,
    ELECTION_MAPPINGS,
    save_learning_data,
    load_learning_data
)

from .classifier import (
    ClassificationRule,
    ObjectClassifier,
    LayoutAnalyzer
)

from .validator import (
    ValidationError,
    ValidationReport,
    TextValidator,
    BatchValidator
)

__all__ = [
    # Schema
    'ObjectType',
    'FontStyle',
    'TextAlignment',
    'BoundingBox',
    'TextStyle',
    'PDFObject',
    'HTMLMapping',
    'DocumentStructure',
    'LearningExample',
    'ValidationResult',
    'ELECTION_MAPPINGS',
    'save_learning_data',
    'load_learning_data',

    # Classifier
    'ClassificationRule',
    'ObjectClassifier',
    'LayoutAnalyzer',

    # Validator
    'ValidationError',
    'ValidationReport',
    'TextValidator',
    'BatchValidator',
]

__version__ = '1.0.0'
