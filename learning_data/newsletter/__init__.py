"""
NewsletterAI Learning Data Module
- OCR 검증 및 자동 교정
- 학습 데이터 저장 및 관리
"""

from .ocr_validator import OCRValidator, NewsletterQualityChecker

__all__ = ['OCRValidator', 'NewsletterQualityChecker']
