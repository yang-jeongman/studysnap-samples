"""
StudySnap Learning Data Schema
PDF 모바일 최적화 변환을 위한 학습 데이터 구조 정의

30년 PDF 전문가 관점의 객체 분류 체계:
- PDF는 "객체(Object)"들의 집합
- 각 객체는 위치(좌표), 유형, 스타일, 관계를 가짐
- 변환의 핵심은 "객체 인식 → 분류 → 관계 파악 → HTML 매핑"
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from enum import Enum
from datetime import datetime
import json


class ObjectType(Enum):
    """PDF 객체 유형 분류 체계"""

    # 텍스트 계층
    MAIN_TITLE = "H1"           # 메인 제목 (문서 최상위)
    SECTION_TITLE = "H2"        # 섹션 제목 (파란색 굵은 글씨)
    SUB_TITLE = "H3"            # 부제목 (작은 회색)
    PARAGRAPH = "P"             # 일반 본문
    BULLET_LIST = "BL"          # 불릿 리스트 (·, -, •)
    NUMBERED_LIST = "NL"        # 번호 리스트 (1., 2.)
    QUOTE = "QT"                # 인용문 ("따옴표")
    CAPTION = "CAP"             # 캡션 (이미지/표 설명)

    # 구조 객체
    CARD = "CARD"               # 카드형 컨테이너 (공약 카드 등)
    TIMELINE = "TL"             # 타임라인 (연도 + 내용)
    TABLE = "TB"                # 표
    BOX = "BOX"                 # 박스/컨테이너

    # 시각 객체
    IMAGE = "IMG"               # 이미지
    SIGNATURE = "SIG"           # 서명/손글씨
    LOGO = "LOGO"               # 로고
    ICON = "ICON"               # 아이콘
    PHOTO = "PHOTO"             # 인물/풍경 사진
    CHART = "CHART"             # 차트/그래프

    # 메타 정보
    HEADER = "HDR"              # 페이지 헤더
    FOOTER = "FTR"              # 페이지 푸터
    PAGE_NUMBER = "PNUM"        # 페이지 번호
    CONTACT = "CONTACT"         # 연락처 정보
    SNS = "SNS"                 # SNS 링크

    # 선거홍보물 특화
    CANDIDATE_NAME = "CAND"     # 후보자 이름
    PARTY_INFO = "PARTY"        # 정당 정보
    SLOGAN = "SLOGAN"           # 슬로건
    PLEDGE = "PLEDGE"           # 공약
    ACHIEVEMENT = "ACHV"        # 실적/성과
    PROMISE_NUMBER = "PNUM"     # 공약 번호
    PROMISE_TITLE = "PTITLE"    # 공약 제목 (교육, 교통 등 카테고리)
    DISTRICT_INFO = "DIST"      # 지역/동 정보


class FontStyle(Enum):
    """폰트 스타일"""
    REGULAR = "regular"
    BOLD = "bold"
    ITALIC = "italic"
    BOLD_ITALIC = "bold_italic"


class TextAlignment(Enum):
    """텍스트 정렬"""
    LEFT = "left"
    CENTER = "center"
    RIGHT = "right"
    JUSTIFY = "justify"


@dataclass
class BoundingBox:
    """객체의 위치 정보 (PDF 좌표계)"""
    x: float          # 왼쪽 상단 X
    y: float          # 왼쪽 상단 Y
    width: float      # 너비
    height: float     # 높이
    page: int = 1     # 페이지 번호

    def to_dict(self) -> dict:
        return {
            "x": self.x,
            "y": self.y,
            "width": self.width,
            "height": self.height,
            "page": self.page
        }

    def overlaps_with(self, other: 'BoundingBox', threshold: float = 0.5) -> bool:
        """다른 객체와 겹치는지 확인"""
        x_overlap = max(0, min(self.x + self.width, other.x + other.width) - max(self.x, other.x))
        y_overlap = max(0, min(self.y + self.height, other.y + other.height) - max(self.y, other.y))
        overlap_area = x_overlap * y_overlap
        self_area = self.width * self.height
        return overlap_area / self_area > threshold if self_area > 0 else False


@dataclass
class TextStyle:
    """텍스트 스타일 정보"""
    font_name: str = "Unknown"
    font_size: float = 12.0
    font_style: FontStyle = FontStyle.REGULAR
    color: str = "#000000"          # Hex 색상
    background: Optional[str] = None
    alignment: TextAlignment = TextAlignment.LEFT
    line_height: float = 1.5

    def to_dict(self) -> dict:
        return {
            "font_name": self.font_name,
            "font_size": self.font_size,
            "font_style": self.font_style.value,
            "color": self.color,
            "background": self.background,
            "alignment": self.alignment.value,
            "line_height": self.line_height
        }

    def is_title_style(self) -> bool:
        """제목 스타일인지 판단"""
        return (
            self.font_size >= 14.0 or
            self.font_style in [FontStyle.BOLD, FontStyle.BOLD_ITALIC] or
            self.color != "#000000"
        )


@dataclass
class PDFObject:
    """PDF 문서 내 개별 객체"""
    id: str                              # 고유 ID
    object_type: ObjectType              # 객체 유형
    content: str                         # 텍스트 내용 또는 이미지 경로
    bbox: BoundingBox                    # 위치 정보
    style: Optional[TextStyle] = None    # 스타일 정보
    confidence: float = 1.0              # 인식 신뢰도 (0~1)

    # 관계 정보
    parent_id: Optional[str] = None      # 부모 객체 ID
    children_ids: List[str] = field(default_factory=list)  # 자식 객체 ID
    related_ids: List[str] = field(default_factory=list)   # 관련 객체 ID

    # 변환 정보
    html_tag: str = "div"                # 변환될 HTML 태그
    html_class: str = ""                 # CSS 클래스
    html_style: str = ""                 # 인라인 스타일

    # 메타데이터
    source_page: int = 1                 # 원본 페이지
    extraction_method: str = "ocr"       # 추출 방법 (ocr, native, hybrid)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "object_type": self.object_type.value,
            "content": self.content,
            "bbox": self.bbox.to_dict(),
            "style": self.style.to_dict() if self.style else None,
            "confidence": self.confidence,
            "parent_id": self.parent_id,
            "children_ids": self.children_ids,
            "related_ids": self.related_ids,
            "html_tag": self.html_tag,
            "html_class": self.html_class,
            "html_style": self.html_style,
            "source_page": self.source_page,
            "extraction_method": self.extraction_method
        }


@dataclass
class HTMLMapping:
    """객체 유형별 HTML 변환 매핑"""
    object_type: ObjectType
    html_template: str              # HTML 템플릿
    css_class: str                  # 기본 CSS 클래스
    wrapper_tag: str = "div"        # 래퍼 태그

    # 스타일 조건
    min_font_size: Optional[float] = None
    max_font_size: Optional[float] = None
    color_pattern: Optional[str] = None     # 색상 패턴 (정규식)
    content_pattern: Optional[str] = None   # 내용 패턴 (정규식)

    def to_dict(self) -> dict:
        return {
            "object_type": self.object_type.value,
            "html_template": self.html_template,
            "css_class": self.css_class,
            "wrapper_tag": self.wrapper_tag,
            "min_font_size": self.min_font_size,
            "max_font_size": self.max_font_size,
            "color_pattern": self.color_pattern,
            "content_pattern": self.content_pattern
        }


@dataclass
class DocumentStructure:
    """문서 전체 구조"""
    doc_id: str
    title: str
    doc_type: str                        # election, lecture, church, general
    page_count: int
    objects: List[PDFObject]

    # 문서 메타데이터
    created_at: datetime = field(default_factory=datetime.now)
    language: str = "ko"

    # 분석 결과
    structure_tree: Dict = field(default_factory=dict)  # 계층 구조
    style_patterns: List[Dict] = field(default_factory=list)  # 발견된 스타일 패턴

    def to_dict(self) -> dict:
        return {
            "doc_id": self.doc_id,
            "title": self.title,
            "doc_type": self.doc_type,
            "page_count": self.page_count,
            "objects": [obj.to_dict() for obj in self.objects],
            "created_at": self.created_at.isoformat(),
            "language": self.language,
            "structure_tree": self.structure_tree,
            "style_patterns": self.style_patterns
        }


@dataclass
class LearningExample:
    """학습 예제 데이터"""
    example_id: str

    # 입력 (원본)
    pdf_path: str
    original_text: str              # 원본 텍스트
    object_type_detected: ObjectType
    detected_style: TextStyle

    # 출력 (변환 결과)
    html_output: str               # 생성된 HTML
    applied_css_class: str
    applied_inline_style: str

    # 평가
    is_correct: bool = True        # 정확한 변환인지
    user_correction: Optional[str] = None  # 사용자 수정 내용
    correction_type: Optional[str] = None  # 수정 유형

    # 메타
    created_at: datetime = field(default_factory=datetime.now)
    doc_type: str = "election"

    def to_dict(self) -> dict:
        return {
            "example_id": self.example_id,
            "pdf_path": self.pdf_path,
            "original_text": self.original_text,
            "object_type_detected": self.object_type_detected.value,
            "detected_style": self.detected_style.to_dict(),
            "html_output": self.html_output,
            "applied_css_class": self.applied_css_class,
            "applied_inline_style": self.applied_inline_style,
            "is_correct": self.is_correct,
            "user_correction": self.user_correction,
            "correction_type": self.correction_type,
            "created_at": self.created_at.isoformat(),
            "doc_type": self.doc_type
        }


@dataclass
class ValidationResult:
    """텍스트 검증 결과"""
    original_text: str
    converted_text: str

    # 오류 분류
    missing_chars: List[str] = field(default_factory=list)      # 누락된 문자
    extra_chars: List[str] = field(default_factory=list)        # 추가된 문자
    wrong_chars: List[Tuple[str, str]] = field(default_factory=list)  # (원본, 오인식)
    split_errors: List[str] = field(default_factory=list)       # 분리 오류
    merge_errors: List[str] = field(default_factory=list)       # 병합 오류

    # 점수
    accuracy_score: float = 0.0     # 정확도 (0~1)
    similarity_score: float = 0.0   # 유사도 (0~1)

    # 자동 수정 제안
    suggested_corrections: List[Dict] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "original_text": self.original_text,
            "converted_text": self.converted_text,
            "missing_chars": self.missing_chars,
            "extra_chars": self.extra_chars,
            "wrong_chars": self.wrong_chars,
            "split_errors": self.split_errors,
            "merge_errors": self.merge_errors,
            "accuracy_score": self.accuracy_score,
            "similarity_score": self.similarity_score,
            "suggested_corrections": self.suggested_corrections
        }


# 선거홍보물 특화 매핑 템플릿
ELECTION_MAPPINGS = {
    ObjectType.MAIN_TITLE: HTMLMapping(
        object_type=ObjectType.MAIN_TITLE,
        html_template='<h2 style="text-align: center; margin: 30px 0 10px; font-size: 1.8em; color: #1a1a1a;">{content}</h2>',
        css_class="main-title",
        min_font_size=20.0
    ),
    ObjectType.SECTION_TITLE: HTMLMapping(
        object_type=ObjectType.SECTION_TITLE,
        html_template='<h3 style="margin: 0 0 5px 0; color: #2563EB; font-size: 1.2em; font-weight: 700;">{title} <span style="font-size: 0.7em; font-weight: 400; color: #666;">{subtitle}</span></h3>',
        css_class="section-title",
        color_pattern=r"#[0-9A-Fa-f]{6}"  # 색상이 있는 제목
    ),
    ObjectType.BULLET_LIST: HTMLMapping(
        object_type=ObjectType.BULLET_LIST,
        html_template='<ul style="margin: 10px 0 0 0; padding-left: 20px; color: #333; font-size: 0.9em; line-height: 1.8;"><li>{content}</li></ul>',
        css_class="bullet-list",
        content_pattern=r"^[·\-•]\s*"  # 불릿으로 시작
    ),
    ObjectType.PLEDGE: HTMLMapping(
        object_type=ObjectType.PLEDGE,
        html_template='''<div class="promise-card">
<div class="promise-header">
<span class="promise-number">{number}</span>
<div class="promise-header-text">
<div class="promise-title">{title}</div>
</div>
</div>
<div class="promise-details">{details}</div>
<div class="expand-btn">상세 보기</div>
</div>''',
        css_class="promise-card"
    ),
    ObjectType.SIGNATURE: HTMLMapping(
        object_type=ObjectType.SIGNATURE,
        html_template='<div style="margin: 20px 0; padding: 20px; background: #fff; border-radius: 12px; text-align: center;"><img src="{src}" alt="{alt}" style="max-width: 100%; height: auto;"></div>',
        css_class="signature-section"
    ),
    ObjectType.TIMELINE: HTMLMapping(
        object_type=ObjectType.TIMELINE,
        html_template='''<div class="timeline-item">
<div class="timeline-year">{year}</div>
<div class="timeline-content">{content}</div>
</div>''',
        css_class="timeline-item",
        content_pattern=r"^\d{4}"  # 연도로 시작
    ),
}


def save_learning_data(data: dict, filepath: str):
    """학습 데이터 저장"""
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def load_learning_data(filepath: str) -> dict:
    """학습 데이터 로드"""
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)
