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
        """분류 규칙 초기화 - 선거공보물 특화 고도화 버전"""
        return [
            # =====================================================
            # 선거공보물 핵심 요소 (최우선)
            # =====================================================

            # 후보자 이름 - 최우선 (짧고 큰 폰트)
            ClassificationRule(
                name="candidate_name_large",
                object_type=ObjectType.CANDIDATE_NAME,
                priority=200,
                min_font_size=28.0,
                content_pattern=r"^[가-힣]{2,4}$",  # 정확히 2-4글자만
                base_confidence=0.99
            ),
            ClassificationRule(
                name="candidate_name_pattern",
                object_type=ObjectType.CANDIDATE_NAME,
                priority=195,
                content_pattern=r"^(나경원|이재명|윤석열|한동훈|이준석|홍준표|유승민|안철수|심상정|조국)$",  # 정확히 이름만
                base_confidence=0.99
            ),

            # 정당 정보
            ClassificationRule(
                name="party_info_major",
                object_type=ObjectType.PARTY_INFO,
                priority=190,
                content_pattern=r"(국민의힘|더불어민주당|조국혁신당|개혁신당|진보당|녹색정의당)",
                base_confidence=0.99
            ),
            ClassificationRule(
                name="party_info_minor",
                object_type=ObjectType.PARTY_INFO,
                priority=185,
                content_pattern=r"(정의당|녹색당|기본소득당|노동당|무소속|기호\s*\d+)",
                base_confidence=0.98
            ),

            # 선거구 정보
            ClassificationRule(
                name="election_district",
                object_type=ObjectType.PARTY_INFO,
                priority=180,
                content_pattern=r"(제?\s*\d+대\s*(국회의원|지방|대통령)|선거(구|공보)|동작구|관악구|강남구|서초구|[가-힣]+구\s*[가-힣을갑])",
                base_confidence=0.97
            ),

            # =====================================================
            # 공약 카테고리 분류 (핵심 차별화)
            # =====================================================

            # 교육 공약
            ClassificationRule(
                name="pledge_education",
                object_type=ObjectType.PROMISE_TITLE,
                priority=175,
                content_pattern=r"(교육|학교|학군|입시|대학|학원|등록금|장학|8학군|명문|IB|바칼로레아|과학중점|교육특구)",
                base_confidence=0.92
            ),

            # 교통/인프라 공약
            ClassificationRule(
                name="pledge_transport",
                object_type=ObjectType.PROMISE_TITLE,
                priority=175,
                content_pattern=r"(교통|철도|지하철|버스|터널|도로|고속|순환|출퇴근|사통팔달|급행|노선|역세권)",
                base_confidence=0.92
            ),

            # 도시개발 공약
            ClassificationRule(
                name="pledge_development",
                object_type=ObjectType.PROMISE_TITLE,
                priority=175,
                content_pattern=r"(개발|재건축|재개발|도시|스카이라인|랜드마크|용적률|상업지역|복합)",
                base_confidence=0.92
            ),

            # 복지 공약
            ClassificationRule(
                name="pledge_welfare",
                object_type=ObjectType.PROMISE_TITLE,
                priority=175,
                content_pattern=r"(복지|돌봄|양육|보육|어르신|노인|경로|요양|연금|장애인|든든복지)",
                base_confidence=0.92
            ),

            # 저출산/가족 공약
            ClassificationRule(
                name="pledge_family",
                object_type=ObjectType.PROMISE_TITLE,
                priority=175,
                content_pattern=r"(저출산|출산|아이|육아|가족|부모|엄마|아빠|신혼|결혼|양육비)",
                base_confidence=0.92
            ),

            # 문화/생활 공약
            ClassificationRule(
                name="pledge_culture",
                object_type=ObjectType.PROMISE_TITLE,
                priority=170,
                content_pattern=r"(문화|도서관|체육|공원|휴양|축제|15분도시|생활권)",
                base_confidence=0.90
            ),

            # 안전 공약
            ClassificationRule(
                name="pledge_safety",
                object_type=ObjectType.PROMISE_TITLE,
                priority=170,
                content_pattern=r"(안전|범죄|치안|경찰|소방|재난|방범|CCTV|흉악)",
                base_confidence=0.90
            ),

            # 경제 공약
            ClassificationRule(
                name="pledge_economy",
                object_type=ObjectType.PROMISE_TITLE,
                priority=170,
                content_pattern=r"(경제|일자리|창업|기업|소상공인|시장|상권|활성화|투자)",
                base_confidence=0.90
            ),

            # =====================================================
            # 실적/성과 분류
            # =====================================================

            ClassificationRule(
                name="achievement_quantified",
                object_type=ObjectType.ACHIEVEMENT,
                priority=165,
                content_pattern=r"(\d+억|\d+조|\d+만|\d+천|\d+%|[0-9,]+원|[0-9,]+명|[0-9,]+개)",
                base_confidence=0.95
            ),
            ClassificationRule(
                name="achievement_action",
                object_type=ObjectType.ACHIEVEMENT,
                priority=160,
                content_pattern=r"(완료|달성|유치|확보|신설|개통|건립|조성|개관|착공|준공|개선|확대|증가|감소|해결|성공)",
                base_confidence=0.88
            ),
            ClassificationRule(
                name="achievement_result",
                object_type=ObjectType.ACHIEVEMENT,
                priority=155,
                content_pattern=r"(바꾼|만든|이룬|세운|열어|뚫어|실현|해냈|해낸)",
                base_confidence=0.85
            ),

            # =====================================================
            # 슬로건/캠페인 문구
            # =====================================================

            ClassificationRule(
                name="slogan_exclamation",
                object_type=ObjectType.SLOGAN,
                priority=150,
                content_pattern=r"^.{5,30}[!]$",
                base_confidence=0.90
            ),
            ClassificationRule(
                name="slogan_campaign",
                object_type=ObjectType.SLOGAN,
                priority=148,
                content_pattern=r"(나만\s*믿어|함께|약속|미래|변화|희망|새로운|일잘하는|진심|통합|상생)",
                base_confidence=0.88
            ),
            ClassificationRule(
                name="slogan_appeal",
                object_type=ObjectType.SLOGAN,
                priority=145,
                content_pattern=r"(하겠습니다|드리겠습니다|만들겠습니다|지키겠습니다|섭니다|됩니다|입니다)$",
                base_confidence=0.85
            ),

            # =====================================================
            # 섹션 제목 (카테고리 라벨) - 높은 우선순위
            # =====================================================

            ClassificationRule(
                name="section_category_label",
                object_type=ObjectType.SECTION_TITLE,
                priority=210,  # 후보자 이름보다 높게
                content_pattern=r"^(교육동작|문화동작|복지동작|안전동작|경제동작|동별\s*성과|주민밀착\s*공약)$",
                base_confidence=0.99
            ),
            ClassificationRule(
                name="section_title_keyword",
                object_type=ObjectType.SECTION_TITLE,
                priority=205,
                content_pattern=r"^[가-힣\s]{2,10}(동작|대한민국|미래|정책|공약|실적)$",
                base_confidence=0.95
            ),

            # 색상 기반 섹션 제목
            ClassificationRule(
                name="section_title_blue",
                object_type=ObjectType.SECTION_TITLE,
                priority=130,
                color_pattern=r"#(2563EB|1E40AF|3B82F6|0066CC|0000FF|1a5fb4|1c71d8)",
                font_style=FontStyle.BOLD,
                base_confidence=0.95
            ),
            ClassificationRule(
                name="section_title_red",
                object_type=ObjectType.SECTION_TITLE,
                priority=130,
                color_pattern=r"#(DC2626|EF4444|B91C1C|FF0000|CC0000|c01c28|e01b24)",
                font_style=FontStyle.BOLD,
                base_confidence=0.95
            ),

            # =====================================================
            # 지역/동별 정보 - 높은 우선순위
            # =====================================================

            ClassificationRule(
                name="district_dong",
                object_type=ObjectType.SECTION_TITLE,
                priority=208,  # 섹션 제목과 비슷하게
                content_pattern=r"^(사당|흑석|상도|노량진|대방|신대방|동작)[0-9가-힣]*동?$",
                base_confidence=0.98
            ),
            ClassificationRule(
                name="district_general",
                object_type=ObjectType.SECTION_TITLE,
                priority=203,
                content_pattern=r"^[가-힣]{1,4}(동|구|시|군)\s*(성과|공약|현황)?$",
                base_confidence=0.92
            ),

            # =====================================================
            # 제목 계층
            # =====================================================

            ClassificationRule(
                name="main_title_large",
                object_type=ObjectType.MAIN_TITLE,
                priority=115,
                min_font_size=24.0,
                font_style=FontStyle.BOLD,
                base_confidence=0.95
            ),
            ClassificationRule(
                name="main_title_pattern",
                object_type=ObjectType.MAIN_TITLE,
                priority=110,
                content_pattern=r"^.{2,15}(을|를|의|로)\s*.{2,15}$",
                min_font_size=18.0,
                base_confidence=0.85
            ),
            ClassificationRule(
                name="sub_title_size",
                object_type=ObjectType.SUB_TITLE,
                priority=105,
                min_font_size=14.0,
                max_font_size=18.0,
                font_style=FontStyle.BOLD,
                base_confidence=0.80
            ),

            # =====================================================
            # 리스트 (불릿/번호) - 공약보다 높은 우선순위
            # =====================================================

            ClassificationRule(
                name="bullet_list_symbol",
                object_type=ObjectType.BULLET_LIST,
                priority=180,  # 공약 카테고리(175)보다 높게
                content_pattern=r"^[\s]*[·•▶▷◆◇★☆✓✔→►■□●○◎]",  # - 제거 (별도 처리)
                base_confidence=0.98
            ),
            ClassificationRule(
                name="bullet_list_dash",
                object_type=ObjectType.BULLET_LIST,
                priority=178,
                content_pattern=r"^\s*[-–—]\s+[가-힣]",  # 대시 뒤에 한글이 오는 경우
                base_confidence=0.95
            ),
            ClassificationRule(
                name="numbered_list_digit",
                object_type=ObjectType.NUMBERED_LIST,
                priority=100,
                content_pattern=r"^[\s]*\d+[\.\)]\s",
                base_confidence=0.98
            ),
            ClassificationRule(
                name="numbered_list_circle",
                object_type=ObjectType.NUMBERED_LIST,
                priority=100,
                content_pattern=r"^[\s]*[①②③④⑤⑥⑦⑧⑨⑩⑪⑫⑬⑭⑮]",
                base_confidence=0.98
            ),

            # =====================================================
            # 공약 번호
            # =====================================================

            ClassificationRule(
                name="promise_number_explicit",
                object_type=ObjectType.PROMISE_NUMBER,
                priority=95,
                content_pattern=r"^(공약|약속|정책)\s*[0-9]+|^[0-9]+\s*(호|번)?\s*(공약|정책)",
                base_confidence=0.98
            ),
            ClassificationRule(
                name="promise_number_card",
                object_type=ObjectType.PROMISE_NUMBER,
                priority=93,
                content_pattern=r"^[1-9]\s+[가-힣]",  # "1 교육특구" 형태
                base_confidence=0.90
            ),

            # =====================================================
            # 타임라인
            # =====================================================

            ClassificationRule(
                name="timeline_year_start",
                object_type=ObjectType.TIMELINE,
                priority=90,
                content_pattern=r"^(19|20)\d{2}[\s\.\-년]",
                base_confidence=0.95
            ),
            ClassificationRule(
                name="timeline_period",
                object_type=ObjectType.TIMELINE,
                priority=88,
                content_pattern=r"(제?\s*\d+대|[0-9]+년간|[0-9]+년\s*[~\-]\s*[0-9]+년)",
                base_confidence=0.90
            ),

            # =====================================================
            # 연락처/SNS - 높은 우선순위
            # =====================================================

            ClassificationRule(
                name="contact_phone",
                object_type=ObjectType.CONTACT,
                priority=185,  # 높은 우선순위
                content_pattern=r"(전화|TEL|☎|📞|연락처)?\s*0\d{1,2}[\-\.\s]?\d{3,4}[\-\.\s]?\d{4}",
                base_confidence=0.98
            ),
            ClassificationRule(
                name="contact_address",
                object_type=ObjectType.CONTACT,
                priority=185,
                content_pattern=r"(선거사무소|사무실|주소)\s*[:：]?\s*[가-힣]+시",
                base_confidence=0.95
            ),
            ClassificationRule(
                name="contact_email",
                object_type=ObjectType.CONTACT,
                priority=185,
                content_pattern=r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}",
                base_confidence=0.99
            ),
            ClassificationRule(
                name="sns_link",
                object_type=ObjectType.SNS,
                priority=185,  # 높은 우선순위
                content_pattern=r"(facebook\.com|instagram\.com|twitter\.com|youtube\.com|blog\.naver\.com|@[a-zA-Z0-9_]+)",
                base_confidence=0.98
            ),

            # =====================================================
            # 인용문/메시지
            # =====================================================

            ClassificationRule(
                name="quote_marks",
                object_type=ObjectType.QUOTE,
                priority=80,
                content_pattern=r'^["\'\"\'].*["\'\"\']$|^「.*」$|^『.*』$|^".*"$',
                base_confidence=0.95
            ),
            ClassificationRule(
                name="quote_testimonial",
                object_type=ObjectType.QUOTE,
                priority=78,
                content_pattern=r"(라고|말씀하셨|감사합니다|고마워요|힘이\s*됩니다)",
                base_confidence=0.85
            ),

            # =====================================================
            # 페이지 메타
            # =====================================================

            ClassificationRule(
                name="page_number",
                object_type=ObjectType.PAGE_NUMBER,
                priority=75,
                content_pattern=r"^[\s]*-?\s*\d{1,3}\s*-?[\s]*$",
                position_rule="bottom",
                base_confidence=0.90
            ),
            ClassificationRule(
                name="header_meta",
                object_type=ObjectType.HEADER,
                priority=70,
                position_rule="top",
                max_font_size=10.0,
                content_pattern=r"(책자형\s*선거공보|제\d+대|선거구)",
                base_confidence=0.85
            ),
            ClassificationRule(
                name="footer_print",
                object_type=ObjectType.FOOTER,
                priority=70,
                position_rule="bottom",
                content_pattern=r"(인쇄|발행|제작|디자인)",
                base_confidence=0.90
            ),

            # =====================================================
            # 테이블/통계
            # =====================================================

            ClassificationRule(
                name="table_header",
                object_type=ObjectType.TABLE,
                priority=65,
                content_pattern=r"(재산상황|납부실적|인적사항|경력|학력)",
                base_confidence=0.90
            ),
            ClassificationRule(
                name="statistics_number",
                object_type=ObjectType.TABLE,
                priority=60,
                content_pattern=r"^[\s]*[\d,\.]+[\s]*(원|억|만|%|명|건|개)?[\s]*$",
                base_confidence=0.75
            ),

            # =====================================================
            # 일반 본문 (기본값)
            # =====================================================

            ClassificationRule(
                name="paragraph_long",
                object_type=ObjectType.PARAGRAPH,
                priority=10,
                content_pattern=r"^.{50,}$",  # 50자 이상
                base_confidence=0.70
            ),
            ClassificationRule(
                name="paragraph_default",
                object_type=ObjectType.PARAGRAPH,
                priority=1,
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
    """레이아웃 분석기 - 선거공보물 특화 고도화 버전"""

    def __init__(self):
        self.column_threshold = 50  # 픽셀 단위, 같은 컬럼으로 판단하는 X 차이
        self.group_threshold = 30   # 같은 그룹으로 판단하는 Y 차이

        # 선거공보물 페이지 유형 패턴
        self.page_patterns = {
            'cover': {
                'keywords': ['후보', '새로운', '함께', '약속', '선거구'],
                'max_objects': 5,
                'has_large_title': True
            },
            'profile': {
                'keywords': ['인적사항', '학력', '경력', '재산', '납부', '병역'],
                'has_table': True
            },
            'pledge': {
                'keywords': ['공약', '정책', '약속', '계획', '추진'],
                'has_numbered_list': True
            },
            'achievement': {
                'keywords': ['실적', '성과', '완료', '달성', '바꾼'],
                'has_bullet_list': True
            },
            'contact': {
                'keywords': ['연락처', '사무소', 'facebook', 'youtube', '@'],
                'position': 'last_page'
            }
        }

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
            "total_objects": len(objects),
            "document_structure": self._analyze_document_structure(by_page)
        }

        for page, page_objects in by_page.items():
            result["pages"][page] = self._analyze_page(page_objects)

        return result

    def _analyze_document_structure(self, by_page: Dict[int, List[PDFObject]]) -> Dict:
        """문서 전체 구조 분석"""
        structure = {
            "total_pages": len(by_page),
            "page_types": {},
            "sections": [],
            "has_toc": False
        }

        for page_num, objects in by_page.items():
            page_type = self._detect_page_type(objects, page_num, len(by_page))
            structure["page_types"][page_num] = page_type

            # 섹션 감지
            for obj in objects:
                if obj.object_type in [ObjectType.SECTION_TITLE, ObjectType.PROMISE_TITLE]:
                    structure["sections"].append({
                        "page": page_num,
                        "title": obj.content[:50],
                        "type": obj.object_type.value
                    })

        return structure

    def _detect_page_type(self, objects: List[PDFObject],
                          page_num: int, total_pages: int) -> str:
        """페이지 유형 감지"""
        texts = " ".join(obj.content for obj in objects).lower()

        # 첫 페이지는 표지 가능성 높음
        if page_num == 1 and len(objects) <= 5:
            return "cover"

        # 마지막 페이지는 연락처 가능성 높음
        if page_num == total_pages:
            for keyword in self.page_patterns['contact']['keywords']:
                if keyword in texts:
                    return "contact"

        # 키워드 기반 감지
        for page_type, pattern in self.page_patterns.items():
            keyword_matches = sum(1 for kw in pattern['keywords'] if kw in texts)
            if keyword_matches >= 2:
                return page_type

        # 객체 유형 기반 감지
        obj_types = [obj.object_type for obj in objects]
        if ObjectType.TABLE in obj_types:
            return "profile"
        if ObjectType.PROMISE_NUMBER in obj_types or ObjectType.PROMISE_TITLE in obj_types:
            return "pledge"
        if ObjectType.ACHIEVEMENT in obj_types:
            return "achievement"

        return "content"

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

        # 콘텐츠 영역 분석
        content_zones = self._detect_content_zones(objects)

        return {
            "columns": len(columns),
            "column_positions": columns,
            "groups": len(groups),
            "reading_order": [obj.id for obj in reading_order],
            "content_zones": content_zones,
            "object_type_summary": self._summarize_object_types(objects)
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

    def _detect_content_zones(self, objects: List[PDFObject]) -> List[Dict]:
        """콘텐츠 영역 감지 (헤더, 본문, 푸터 등)"""
        if not objects:
            return []

        # Y 좌표 기준 분류
        y_coords = [obj.bbox.y for obj in objects]
        min_y, max_y = min(y_coords), max(y_coords)
        page_height = max_y - min_y if max_y > min_y else 842

        zones = []

        # 상단 영역 (헤더)
        header_objects = [o for o in objects if o.bbox.y < min_y + page_height * 0.1]
        if header_objects:
            zones.append({
                "type": "header",
                "objects_count": len(header_objects),
                "y_range": (min_y, min_y + page_height * 0.1)
            })

        # 중앙 영역 (본문)
        body_objects = [o for o in objects
                       if min_y + page_height * 0.1 <= o.bbox.y <= min_y + page_height * 0.9]
        if body_objects:
            zones.append({
                "type": "body",
                "objects_count": len(body_objects),
                "y_range": (min_y + page_height * 0.1, min_y + page_height * 0.9)
            })

        # 하단 영역 (푸터)
        footer_objects = [o for o in objects if o.bbox.y > min_y + page_height * 0.9]
        if footer_objects:
            zones.append({
                "type": "footer",
                "objects_count": len(footer_objects),
                "y_range": (min_y + page_height * 0.9, max_y)
            })

        return zones

    def _summarize_object_types(self, objects: List[PDFObject]) -> Dict:
        """객체 유형 요약"""
        summary = {}
        for obj in objects:
            type_name = obj.object_type.value
            if type_name not in summary:
                summary[type_name] = 0
            summary[type_name] += 1
        return summary

    def detect_card_structure(self, objects: List[PDFObject]) -> List[Dict]:
        """카드형 구조 감지 (공약 카드 등) - 고도화 버전"""
        cards = []

        # 연속된 관련 객체들을 카드로 그룹화
        i = 0
        while i < len(objects):
            obj = objects[i]

            # 카드 시작 조건: 번호, 제목, 또는 공약 관련 유형
            card_start_types = [
                ObjectType.PROMISE_NUMBER,
                ObjectType.SECTION_TITLE,
                ObjectType.PROMISE_TITLE,
                ObjectType.MAIN_TITLE
            ]

            if obj.object_type in card_start_types:
                card = {
                    "header": obj,
                    "header_type": obj.object_type.value,
                    "content": [],
                    "bbox": obj.bbox,
                    "category": self._detect_card_category(obj.content)
                }

                # 연속된 관련 객체들 수집
                j = i + 1
                while j < len(objects):
                    next_obj = objects[j]

                    # 다음 카드 시작이면 종료
                    if next_obj.object_type in card_start_types:
                        break

                    # 거리가 너무 멀면 종료 (300픽셀로 확대)
                    if next_obj.bbox.y - card["bbox"].y > 300:
                        break

                    card["content"].append(next_obj)
                    j += 1

                # 카드 메타데이터 추가
                card["content_count"] = len(card["content"])
                card["content_types"] = list(set(o.object_type.value for o in card["content"]))

                cards.append(card)
                i = j
            else:
                i += 1

        return cards

    def _detect_card_category(self, content: str) -> str:
        """카드 카테고리 감지"""
        content_lower = content.lower()

        categories = {
            "education": ["교육", "학교", "학군", "입시", "대학", "학원"],
            "transport": ["교통", "철도", "지하철", "버스", "터널", "도로"],
            "welfare": ["복지", "돌봄", "양육", "어르신", "장애인"],
            "development": ["개발", "재건축", "도시", "용적률"],
            "culture": ["문화", "도서관", "체육", "공원"],
            "safety": ["안전", "범죄", "치안"],
            "economy": ["경제", "일자리", "창업", "기업"],
            "family": ["저출산", "출산", "아이", "육아", "가족"]
        }

        for category, keywords in categories.items():
            if any(kw in content_lower for kw in keywords):
                return category

        return "general"

    def generate_mobile_layout(self, objects: List[PDFObject]) -> Dict:
        """모바일 최적화 레이아웃 생성 - 개선 버전"""
        cards = self.detect_card_structure(objects)

        mobile_layout = {
            "hero_section": None,
            "quick_highlights": [],
            "pledge_cards": [],
            "timeline_items": [],
            "contact_section": None,
            "fulltext_pages": [],
            "achievements": [],
            "district_pledges": {}  # 동별 공약
        }

        # 제외할 키워드 (학력, 경력 등 인적사항)
        exclude_keywords = ['대학교', '대학원', '법학과', '박사', '석사', '학사',
                           '국회의원', '원내대표', '위원장', '의원']

        # 제외할 이름 패턴 (일반 명사나 정당명 등)
        invalid_names = ['생년월일', '후보자', '성명', '성별', '직업', '학력', '경력',
                        '국민의힘', '더불어민주당', '조국혁신당', '개혁신당', '정의당', '무소속',
                        '정당인', '기호', '소속', '일잘하는', '교육동작', '문화동작',
                        '신고거부', '소명서', '세금납부']

        # 알려진 후보자 이름 (우선 처리)
        known_candidates = ['나경원', '이재명', '윤석열', '한동훈', '이준석', '홍준표',
                           '유승민', '안철수', '심상정', '조국', '오세훈', '박영선']

        # 유효한 후보자 이름 패턴 (성+이름, 2-4글자 한글)
        import re
        valid_name_pattern = re.compile(r'^[가-힣]{2,4}$')
        korean_surnames = ['김', '이', '박', '최', '정', '강', '조', '윤', '장', '임',
                          '한', '오', '서', '신', '권', '황', '안', '송', '류', '홍',
                          '나', '전', '문', '양', '배', '백', '허', '유', '고', '노']

        # 먼저 알려진 후보자 이름 찾기
        for obj in objects:
            if obj.content in known_candidates:
                if mobile_layout["hero_section"] is None:
                    mobile_layout["hero_section"] = {
                        "candidate": None,
                        "slogan": None,
                        "party": None
                    }
                if mobile_layout["hero_section"]["candidate"] is None:
                    mobile_layout["hero_section"]["candidate"] = obj.content
                    break

        for obj in objects:
            # 히어로 섹션 (후보자 이름, 슬로건)
            if obj.object_type == ObjectType.CANDIDATE_NAME:
                name = obj.content
                # 유효한 이름 조건: 2-4글자, 제외 목록에 없음, 유효한 성으로 시작
                if (valid_name_pattern.match(name) and
                    name not in invalid_names and
                    len(name) >= 2 and name[0] in korean_surnames):
                    if mobile_layout["hero_section"] is None:
                        mobile_layout["hero_section"] = {
                            "candidate": None,
                            "slogan": None,
                            "party": None
                        }
                    if mobile_layout["hero_section"]["candidate"] is None:
                        mobile_layout["hero_section"]["candidate"] = name

            elif obj.object_type == ObjectType.SLOGAN:
                # 짧은 슬로건만 (5-50자)
                if 5 <= len(obj.content) <= 50 and '!' in obj.content:
                    if mobile_layout["hero_section"] is None:
                        mobile_layout["hero_section"] = {
                            "candidate": None,
                            "slogan": None,
                            "party": None
                        }
                    if mobile_layout["hero_section"]["slogan"] is None:
                        mobile_layout["hero_section"]["slogan"] = obj.content

            # 정당 정보 (주요 정당만)
            elif obj.object_type == ObjectType.PARTY_INFO:
                if mobile_layout["hero_section"] and mobile_layout["hero_section"]["party"] is None:
                    if any(party in obj.content for party in ['국민의힘', '더불어민주당', '조국혁신당']):
                        mobile_layout["hero_section"]["party"] = obj.content

            # 타임라인 (연도 포함 텍스트)
            elif obj.object_type == ObjectType.TIMELINE:
                mobile_layout["timeline_items"].append({
                    "content": obj.content,
                    "page": obj.source_page
                })

            # 실적
            elif obj.object_type == ObjectType.ACHIEVEMENT:
                mobile_layout["achievements"].append({
                    "content": obj.content,
                    "page": obj.source_page
                })

            # 연락처
            elif obj.object_type in [ObjectType.CONTACT, ObjectType.SNS]:
                if mobile_layout["contact_section"] is None:
                    mobile_layout["contact_section"] = []
                mobile_layout["contact_section"].append({
                    "type": obj.object_type.value,
                    "content": obj.content
                })

            # 동별 정보
            elif obj.object_type == ObjectType.SECTION_TITLE:
                # 동 이름 패턴 확인
                import re
                dong_match = re.match(r'^(사당|흑석|상도|노량진|대방|신대방|동작)[0-9가-힣]*동?$', obj.content)
                if dong_match:
                    dong_name = obj.content
                    if dong_name not in mobile_layout["district_pledges"]:
                        mobile_layout["district_pledges"][dong_name] = []

        # 카드 구조에서 실제 공약만 추출
        for card in cards:
            title = card["header"].content
            category = card["category"]

            # 제외 조건
            if category == "general":
                continue
            if any(kw in title for kw in exclude_keywords):
                continue
            if len(title) < 5:  # 너무 짧은 제목 제외
                continue

            # 실제 공약으로 보이는 것만 추가
            mobile_layout["pledge_cards"].append({
                "title": title,
                "category": category,
                "content_count": card["content_count"],
                "page": card["bbox"].page
            })

        # 중복 제거 및 정렬
        seen_titles = set()
        unique_cards = []
        for card in mobile_layout["pledge_cards"]:
            if card["title"] not in seen_titles:
                seen_titles.add(card["title"])
                unique_cards.append(card)
        mobile_layout["pledge_cards"] = unique_cards

        # 퀵 하이라이트 - 핵심 키워드가 있는 공약 우선
        highlight_keywords = ['8학군', '철도', '터널', '복지', '저출산', '안전', '도시']
        highlighted = []
        others = []

        for card in mobile_layout["pledge_cards"]:
            if any(kw in card["title"] for kw in highlight_keywords):
                highlighted.append(card)
            else:
                others.append(card)

        mobile_layout["quick_highlights"] = (highlighted + others)[:6]

        return mobile_layout


# =========================================================================
# 학습 데이터 연동 - 능동형 학습 엔진과 분류기 통합
# =========================================================================

class LearningIntegratedClassifier(ObjectClassifier):
    """학습 데이터를 활용하는 통합 분류기"""

    def __init__(self):
        super().__init__()
        self.learning_engine = None
        self._load_learning_engine()

    def _load_learning_engine(self):
        """학습 엔진 로드"""
        try:
            from .active_learning import get_learning_engine
            self.learning_engine = get_learning_engine()
            print("[분류기] 학습 엔진 연동 완료")
        except Exception as e:
            print(f"[분류기] 학습 엔진 로드 실패: {e}")

    def classify_with_learning(self, text: str, style=None, bbox=None,
                               page_height: float = 842.0):
        """학습된 규칙을 적용하여 분류"""
        # 기본 분류
        obj_type, confidence = self.classify(text, style, bbox, page_height)

        # 학습된 규칙 적용 (신뢰도 보정)
        if self.learning_engine:
            applicable_rules = self.learning_engine.get_applicable_rules(
                category=obj_type.value,
                min_confidence=0.7
            )

            # 규칙이 있으면 신뢰도 상향
            if applicable_rules:
                confidence = min(confidence * 1.1, 0.99)

        return obj_type, confidence

    def apply_learned_patterns(self, html: str) -> str:
        """학습된 패턴을 HTML에 적용"""
        if not self.learning_engine:
            return html

        modified_html, applied_rules = self.learning_engine.apply_rules_to_html(html)

        if applied_rules:
            print(f"[분류기] {len(applied_rules)}개 학습 규칙 적용됨")

        return modified_html

    def get_learning_status(self) -> dict:
        """학습 상태 반환"""
        if not self.learning_engine:
            return {"status": "not_connected", "rules_count": 0}

        stats = self.learning_engine.get_learning_stats()
        return {
            "status": "connected",
            "active_rules": stats.get("active_rules", 0),
            "high_confidence_rules": stats.get("high_confidence_rules", 0),
            "total_feedbacks": stats.get("total_feedbacks", 0),
            "corrections_count": stats.get("corrections_count", 0)
        }


# 싱글톤 인스턴스
_integrated_classifier = None

def get_integrated_classifier() -> LearningIntegratedClassifier:
    """학습 통합 분류기 싱글톤 반환"""
    global _integrated_classifier
    if _integrated_classifier is None:
        _integrated_classifier = LearningIntegratedClassifier()
    return _integrated_classifier
