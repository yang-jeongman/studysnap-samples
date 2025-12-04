"""
PDF 객체 분류 엔진
30년 PDF 전문가 관점의 지능형 객체 인식 시스템

핵심 원리:
1. 스타일 기반 분류: 폰트 크기, 색상, 굵기로 객체 유형 추론
2. 패턴 기반 분류: 텍스트 내용의 패턴으로 분류 (번호, 불릿, 연도 등)
3. 위치 기반 분류: 좌표와 주변 객체 관계로 분류
4. 학습 기반 분류: 이전 변환 결과에서 학습한 패턴 적용
"""

import re
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from .schema import (
    ObjectType, PDFObject, BoundingBox, TextStyle,
    FontStyle, TextAlignment, HTMLMapping, ELECTION_MAPPINGS
)


@dataclass
class ClassificationRule:
    """분류 규칙"""
    name: str
    object_type: ObjectType
    priority: int  # 높을수록 우선

    # 조건들
    min_font_size: Optional[float] = None
    max_font_size: Optional[float] = None
    font_style: Optional[FontStyle] = None
    color_pattern: Optional[str] = None
    content_pattern: Optional[str] = None
    position_rule: Optional[str] = None  # top, center, bottom

    # 신뢰도
    base_confidence: float = 0.8


class ObjectClassifier:
    """PDF 객체 분류기"""

    def __init__(self):
        self.rules = self._init_classification_rules()
        self.learned_patterns: Dict[str, List[dict]] = {}
        self.classification_history: List[dict] = []

    def _init_classification_rules(self) -> List[ClassificationRule]:
        """분류 규칙 초기화 - 30년 경험 기반"""
        return [
            # === 제목 계층 ===
            ClassificationRule(
                name="main_title_large",
                object_type=ObjectType.MAIN_TITLE,
                priority=100,
                min_font_size=24.0,
                font_style=FontStyle.BOLD,
                position_rule="top",
                base_confidence=0.95
            ),
            ClassificationRule(
                name="main_title_center",
                object_type=ObjectType.MAIN_TITLE,
                priority=95,
                min_font_size=18.0,
                content_pattern=r"^.{2,20}$",  # 짧은 텍스트
                position_rule="center",
                base_confidence=0.85
            ),

            # === 섹션 제목 (파란색 등 컬러 제목) ===
            ClassificationRule(
                name="section_title_blue",
                object_type=ObjectType.SECTION_TITLE,
                priority=90,
                color_pattern=r"#(2563EB|1E40AF|3B82F6|0066CC|0000FF)",  # 파란 계열
                font_style=FontStyle.BOLD,
                base_confidence=0.95
            ),
            ClassificationRule(
                name="section_title_red",
                object_type=ObjectType.SECTION_TITLE,
                priority=90,
                color_pattern=r"#(DC2626|EF4444|B91C1C|FF0000|CC0000)",  # 빨간 계열
                font_style=FontStyle.BOLD,
                base_confidence=0.95
            ),
            ClassificationRule(
                name="section_title_size",
                object_type=ObjectType.SECTION_TITLE,
                priority=85,
                min_font_size=14.0,
                max_font_size=24.0,
                font_style=FontStyle.BOLD,
                base_confidence=0.80
            ),

            # === 리스트 ===
            ClassificationRule(
                name="bullet_list",
                object_type=ObjectType.BULLET_LIST,
                priority=95,
                content_pattern=r"^[\s]*[·•\-▶▷◆◇★☆✓✔→►]",
                base_confidence=0.98
            ),
            ClassificationRule(
                name="numbered_list",
                object_type=ObjectType.NUMBERED_LIST,
                priority=95,
                content_pattern=r"^[\s]*(\d+[\.\)]\s|[①②③④⑤⑥⑦⑧⑨⑩])",
                base_confidence=0.98
            ),

            # === 선거홍보물 특화 ===
            ClassificationRule(
                name="candidate_name",
                object_type=ObjectType.CANDIDATE_NAME,
                priority=100,
                min_font_size=20.0,
                content_pattern=r"^[가-힣]{2,4}$",  # 2-4글자 한글 이름
                position_rule="top",
                base_confidence=0.90
            ),
            ClassificationRule(
                name="party_info",
                object_type=ObjectType.PARTY_INFO,
                priority=95,
                content_pattern=r"(국민의힘|더불어민주당|정의당|녹색당|기본소득당|무소속)",
                base_confidence=0.99
            ),
            ClassificationRule(
                name="slogan",
                object_type=ObjectType.SLOGAN,
                priority=88,
                min_font_size=16.0,
                content_pattern=r"[!]$|함께|약속|미래|변화|희망",
                base_confidence=0.85
            ),
            ClassificationRule(
                name="pledge_number",
                object_type=ObjectType.PROMISE_NUMBER,
                priority=98,
                content_pattern=r"^(공약|약속)?\s*[0-9]+\s*$|^제?\s*[0-9]+\s*(호|번)?공약",
                base_confidence=0.95
            ),
            ClassificationRule(
                name="achievement",
                object_type=ObjectType.ACHIEVEMENT,
                priority=85,
                content_pattern=r"(실적|성과|완료|달성|유치|확보|신설|개통|증가|감소|\d+%|\d+억|\d+만)",
                base_confidence=0.80
            ),

            # === 타임라인 ===
            ClassificationRule(
                name="timeline_year",
                object_type=ObjectType.TIMELINE,
                priority=92,
                content_pattern=r"^(19|20)\d{2}[\s\.\-년]",  # 연도로 시작
                base_confidence=0.95
            ),

            # === 연락처/SNS ===
            ClassificationRule(
                name="contact_phone",
                object_type=ObjectType.CONTACT,
                priority=95,
                content_pattern=r"(전화|TEL|☎|📞)?\s*0\d{1,2}[\-\.\s]?\d{3,4}[\-\.\s]?\d{4}",
                base_confidence=0.98
            ),
            ClassificationRule(
                name="contact_email",
                object_type=ObjectType.CONTACT,
                priority=95,
                content_pattern=r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}",
                base_confidence=0.99
            ),
            ClassificationRule(
                name="sns_link",
                object_type=ObjectType.SNS,
                priority=95,
                content_pattern=r"(facebook|instagram|twitter|youtube|blog|naver|kakao|@)",
                base_confidence=0.95
            ),

            # === 페이지 메타 ===
            ClassificationRule(
                name="page_number",
                object_type=ObjectType.PAGE_NUMBER,
                priority=90,
                content_pattern=r"^[\s]*-?\s*\d{1,3}\s*-?[\s]*$",  # 단순 숫자
                position_rule="bottom",
                base_confidence=0.90
            ),
            ClassificationRule(
                name="header",
                object_type=ObjectType.HEADER,
                priority=80,
                position_rule="top",
                max_font_size=10.0,
                base_confidence=0.75
            ),
            ClassificationRule(
                name="footer",
                object_type=ObjectType.FOOTER,
                priority=80,
                position_rule="bottom",
                max_font_size=10.0,
                base_confidence=0.75
            ),

            # === 인용문 ===
            ClassificationRule(
                name="quote",
                object_type=ObjectType.QUOTE,
                priority=88,
                content_pattern=r'^["\'\"\'].*["\'\"\']$|^「.*」$|^『.*』$',
                base_confidence=0.92
            ),

            # === 기본값 (일반 본문) ===
            ClassificationRule(
                name="paragraph_default",
                object_type=ObjectType.PARAGRAPH,
                priority=1,  # 가장 낮은 우선순위
                base_confidence=0.50
            ),
        ]

    def classify(self, text: str, style: Optional[TextStyle] = None,
                 bbox: Optional[BoundingBox] = None,
                 page_height: float = 842.0) -> Tuple[ObjectType, float]:
        """
        텍스트를 분류하고 객체 유형과 신뢰도 반환

        Args:
            text: 분류할 텍스트
            style: 텍스트 스타일 정보
            bbox: 위치 정보
            page_height: 페이지 높이 (위치 판단용)

        Returns:
            (ObjectType, confidence)
        """
        if not text or not text.strip():
            return ObjectType.PARAGRAPH, 0.0

        text = text.strip()
        matches: List[Tuple[ClassificationRule, float]] = []

        for rule in self.rules:
            confidence = self._evaluate_rule(rule, text, style, bbox, page_height)
            if confidence > 0:
                matches.append((rule, confidence))

        if not matches:
            return ObjectType.PARAGRAPH, 0.5

        # 우선순위와 신뢰도로 정렬
        matches.sort(key=lambda x: (x[0].priority, x[1]), reverse=True)
        best_match = matches[0]

        # 분류 기록 저장
        self.classification_history.append({
            "text": text[:100],
            "result": best_match[0].object_type.value,
            "confidence": best_match[1],
            "rule": best_match[0].name
        })

        return best_match[0].object_type, best_match[1]

    def _evaluate_rule(self, rule: ClassificationRule, text: str,
                       style: Optional[TextStyle], bbox: Optional[BoundingBox],
                       page_height: float) -> float:
        """규칙 평가하여 신뢰도 반환 (0이면 불일치)"""
        confidence = rule.base_confidence
        conditions_met = 0
        conditions_total = 0

        # 내용 패턴 검사
        if rule.content_pattern:
            conditions_total += 1
            if re.search(rule.content_pattern, text, re.IGNORECASE):
                conditions_met += 1
                confidence *= 1.2  # 패턴 일치 보너스
            else:
                return 0  # 패턴 불일치는 즉시 제외

        # 스타일 검사
        if style:
            # 폰트 크기
            if rule.min_font_size is not None:
                conditions_total += 1
                if style.font_size >= rule.min_font_size:
                    conditions_met += 1
                else:
                    confidence *= 0.5

            if rule.max_font_size is not None:
                conditions_total += 1
                if style.font_size <= rule.max_font_size:
                    conditions_met += 1
                else:
                    confidence *= 0.5

            # 폰트 스타일
            if rule.font_style is not None:
                conditions_total += 1
                if style.font_style == rule.font_style:
                    conditions_met += 1
                    confidence *= 1.1
                else:
                    confidence *= 0.7

            # 색상 패턴
            if rule.color_pattern:
                conditions_total += 1
                if re.search(rule.color_pattern, style.color, re.IGNORECASE):
                    conditions_met += 1
                    confidence *= 1.3  # 색상 일치 높은 보너스
                else:
                    return 0  # 색상 패턴 불일치는 제외

        # 위치 검사
        if bbox and rule.position_rule:
            conditions_total += 1
            relative_y = bbox.y / page_height

            if rule.position_rule == "top" and relative_y < 0.2:
                conditions_met += 1
                confidence *= 1.1
            elif rule.position_rule == "center" and 0.3 < relative_y < 0.7:
                conditions_met += 1
            elif rule.position_rule == "bottom" and relative_y > 0.8:
                conditions_met += 1
                confidence *= 1.1

        # 최종 신뢰도 조정
        if conditions_total > 0:
            match_ratio = conditions_met / conditions_total
            confidence *= (0.5 + 0.5 * match_ratio)

        return min(confidence, 1.0)  # 최대 1.0

    def classify_batch(self, objects: List[dict]) -> List[PDFObject]:
        """여러 객체를 일괄 분류"""
        results = []

        for obj in objects:
            text = obj.get("text", "")
            style_data = obj.get("style", {})
            bbox_data = obj.get("bbox", {})

            # 스타일 객체 생성
            style = None
            if style_data:
                style = TextStyle(
                    font_name=style_data.get("font_name", "Unknown"),
                    font_size=style_data.get("font_size", 12.0),
                    font_style=FontStyle(style_data.get("font_style", "regular")),
                    color=style_data.get("color", "#000000"),
                    alignment=TextAlignment(style_data.get("alignment", "left"))
                )

            # 바운딩 박스 생성
            bbox = None
            if bbox_data:
                bbox = BoundingBox(
                    x=bbox_data.get("x", 0),
                    y=bbox_data.get("y", 0),
                    width=bbox_data.get("width", 0),
                    height=bbox_data.get("height", 0),
                    page=bbox_data.get("page", 1)
                )

            # 분류 실행
            obj_type, confidence = self.classify(text, style, bbox)

            # HTML 매핑 적용
            html_info = self._get_html_mapping(obj_type)

            pdf_obj = PDFObject(
                id=obj.get("id", f"obj_{len(results)}"),
                object_type=obj_type,
                content=text,
                bbox=bbox or BoundingBox(0, 0, 0, 0),
                style=style,
                confidence=confidence,
                html_tag=html_info["tag"],
                html_class=html_info["class"],
                source_page=bbox.page if bbox else 1
            )
            results.append(pdf_obj)

        return results

    def _get_html_mapping(self, obj_type: ObjectType) -> dict:
        """객체 유형에 맞는 HTML 매핑 반환"""
        mapping = ELECTION_MAPPINGS.get(obj_type)

        if mapping:
            return {
                "tag": mapping.wrapper_tag,
                "class": mapping.css_class
            }

        # 기본 매핑
        default_mappings = {
            ObjectType.MAIN_TITLE: {"tag": "h2", "class": "main-title"},
            ObjectType.SECTION_TITLE: {"tag": "h3", "class": "section-title"},
            ObjectType.SUB_TITLE: {"tag": "h4", "class": "sub-title"},
            ObjectType.PARAGRAPH: {"tag": "p", "class": "paragraph"},
            ObjectType.BULLET_LIST: {"tag": "ul", "class": "bullet-list"},
            ObjectType.NUMBERED_LIST: {"tag": "ol", "class": "numbered-list"},
            ObjectType.QUOTE: {"tag": "blockquote", "class": "quote"},
            ObjectType.CAPTION: {"tag": "figcaption", "class": "caption"},
            ObjectType.TABLE: {"tag": "table", "class": "data-table"},
            ObjectType.IMAGE: {"tag": "figure", "class": "image-container"},
            ObjectType.CANDIDATE_NAME: {"tag": "h1", "class": "candidate-name"},
            ObjectType.SLOGAN: {"tag": "div", "class": "slogan"},
            ObjectType.CONTACT: {"tag": "address", "class": "contact-info"},
            ObjectType.TIMELINE: {"tag": "div", "class": "timeline-item"},
        }

        return default_mappings.get(obj_type, {"tag": "div", "class": "content"})

    def learn_from_correction(self, original_type: ObjectType,
                              corrected_type: ObjectType,
                              text: str, style: Optional[TextStyle] = None):
        """사용자 수정으로부터 학습"""
        pattern_key = corrected_type.value

        if pattern_key not in self.learned_patterns:
            self.learned_patterns[pattern_key] = []

        # 학습 데이터 저장
        self.learned_patterns[pattern_key].append({
            "text_sample": text[:200],
            "text_length": len(text),
            "style": style.to_dict() if style else None,
            "original_classification": original_type.value,
            "correction_count": 1
        })

        print(f"[학습] {original_type.value} → {corrected_type.value}: {text[:50]}...")

    def get_statistics(self) -> dict:
        """분류 통계 반환"""
        if not self.classification_history:
            return {"total": 0, "by_type": {}}

        by_type = {}
        for record in self.classification_history:
            obj_type = record["result"]
            if obj_type not in by_type:
                by_type[obj_type] = {"count": 0, "avg_confidence": 0}
            by_type[obj_type]["count"] += 1
            by_type[obj_type]["avg_confidence"] += record["confidence"]

        for obj_type in by_type:
            count = by_type[obj_type]["count"]
            by_type[obj_type]["avg_confidence"] /= count

        return {
            "total": len(self.classification_history),
            "by_type": by_type,
            "learned_patterns_count": sum(len(v) for v in self.learned_patterns.values())
        }


class LayoutAnalyzer:
    """레이아웃 분석기 - 객체 간 관계 파악"""

    def __init__(self):
        self.column_threshold = 50  # 픽셀 단위, 같은 컬럼으로 판단하는 X 차이
        self.group_threshold = 30   # 같은 그룹으로 판단하는 Y 차이

    def analyze_layout(self, objects: List[PDFObject]) -> Dict:
        """페이지 레이아웃 분석"""
        if not objects:
            return {"columns": 1, "groups": [], "reading_order": []}

        # 페이지별로 분리
        by_page = {}
        for obj in objects:
            page = obj.bbox.page
            if page not in by_page:
                by_page[page] = []
            by_page[page].append(obj)

        result = {
            "pages": {},
            "total_objects": len(objects)
        }

        for page, page_objects in by_page.items():
            result["pages"][page] = self._analyze_page(page_objects)

        return result

    def _analyze_page(self, objects: List[PDFObject]) -> Dict:
        """단일 페이지 분석"""
        if not objects:
            return {"columns": 1, "groups": [], "reading_order": []}

        # X 좌표로 컬럼 감지
        x_coords = sorted(set(obj.bbox.x for obj in objects))
        columns = self._detect_columns(x_coords)

        # Y 좌표로 그룹핑
        groups = self._group_by_proximity(objects)

        # 읽기 순서 결정 (위→아래, 왼쪽→오른쪽)
        reading_order = self._determine_reading_order(objects, columns)

        return {
            "columns": len(columns),
            "column_positions": columns,
            "groups": len(groups),
            "reading_order": [obj.id for obj in reading_order]
        }

    def _detect_columns(self, x_coords: List[float]) -> List[float]:
        """컬럼 위치 감지"""
        if len(x_coords) < 2:
            return x_coords

        columns = [x_coords[0]]
        for x in x_coords[1:]:
            if x - columns[-1] > self.column_threshold:
                columns.append(x)

        return columns

    def _group_by_proximity(self, objects: List[PDFObject]) -> List[List[PDFObject]]:
        """근접한 객체들을 그룹화"""
        if not objects:
            return []

        sorted_objects = sorted(objects, key=lambda o: (o.bbox.y, o.bbox.x))
        groups = [[sorted_objects[0]]]

        for obj in sorted_objects[1:]:
            last_group = groups[-1]
            last_obj = last_group[-1]

            # Y 차이가 threshold 이하면 같은 그룹
            if abs(obj.bbox.y - last_obj.bbox.y) <= self.group_threshold:
                last_group.append(obj)
            else:
                groups.append([obj])

        return groups

    def _determine_reading_order(self, objects: List[PDFObject],
                                  columns: List[float]) -> List[PDFObject]:
        """읽기 순서 결정"""
        # 단일 컬럼이면 Y 순서
        if len(columns) <= 1:
            return sorted(objects, key=lambda o: (o.bbox.y, o.bbox.x))

        # 다중 컬럼이면 컬럼별로 정렬 후 합침
        def get_column(obj):
            for i, col_x in enumerate(columns):
                if obj.bbox.x < col_x + self.column_threshold:
                    return i
            return len(columns) - 1

        by_column = {i: [] for i in range(len(columns))}
        for obj in objects:
            col = get_column(obj)
            by_column[col].append(obj)

        # 각 컬럼 내 Y 정렬
        result = []
        for col in sorted(by_column.keys()):
            col_objects = sorted(by_column[col], key=lambda o: o.bbox.y)
            result.extend(col_objects)

        return result

    def detect_card_structure(self, objects: List[PDFObject]) -> List[Dict]:
        """카드형 구조 감지 (공약 카드 등)"""
        cards = []

        # 연속된 관련 객체들을 카드로 그룹화
        i = 0
        while i < len(objects):
            obj = objects[i]

            # 카드 시작 조건: 번호나 제목
            if obj.object_type in [ObjectType.PROMISE_NUMBER, ObjectType.SECTION_TITLE]:
                card = {
                    "header": obj,
                    "content": [],
                    "bbox": obj.bbox
                }

                # 연속된 관련 객체들 수집
                j = i + 1
                while j < len(objects):
                    next_obj = objects[j]

                    # 다음 카드 시작이면 종료
                    if next_obj.object_type in [ObjectType.PROMISE_NUMBER, ObjectType.SECTION_TITLE]:
                        break

                    # 거리가 너무 멀면 종료
                    if next_obj.bbox.y - card["bbox"].y > 200:
                        break

                    card["content"].append(next_obj)
                    j += 1

                cards.append(card)
                i = j
            else:
                i += 1

        return cards
