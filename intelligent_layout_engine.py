"""
지능형 레이아웃 엔진
PDF 문서에서 객체를 자동으로 인식, 분류, 그룹화하고
모바일 페이지에 최적으로 배치하는 시스템
"""

import logging
from typing import Dict, List, Tuple, Any, Optional
from dataclasses import dataclass
from enum import Enum
import re

logger = logging.getLogger(__name__)


class ObjectType(Enum):
    """문서 객체 타입"""
    HEADER = "header"  # 헤더 (제목, 상단 정보)
    TITLE = "title"  # 주요 제목
    SUBTITLE = "subtitle"  # 부제목
    PARAGRAPH = "paragraph"  # 본문 단락
    LIST = "list"  # 목록
    TABLE = "table"  # 표
    IMAGE = "image"  # 이미지
    FOOTER = "footer"  # 푸터
    PROFILE = "profile"  # 프로필 정보
    CONTACT = "contact"  # 연락처
    BADGE = "badge"  # 뱃지 (정당, 기호 등)
    CARD = "card"  # 카드 (공약, 경력 등)
    DIVIDER = "divider"  # 구분선


class LayoutPriority(Enum):
    """레이아웃 우선순위"""
    CRITICAL = 1  # 최우선 (이름, 정당 등)
    HIGH = 2  # 높음 (핵심 공약, 주요 경력)
    MEDIUM = 3  # 중간 (상세 설명)
    LOW = 4  # 낮음 (부가 정보)


@dataclass
class DocumentObject:
    """문서 객체"""
    object_id: str
    object_type: ObjectType
    content: Any
    position: Tuple[float, float, float, float]  # (x, y, width, height)
    page_num: int
    priority: LayoutPriority
    metadata: Dict[str, Any]
    group_id: Optional[str] = None


@dataclass
class ObjectGroup:
    """객체 그룹"""
    group_id: str
    group_type: str  # 'profile', 'pledges', 'career', 'contact'
    objects: List[DocumentObject]
    priority: LayoutPriority
    layout_hint: str  # 'hero', 'grid', 'list', 'accordion'


class IntelligentLayoutEngine:
    """지능형 레이아웃 엔진"""

    def __init__(self):
        self.objects: List[DocumentObject] = []
        self.groups: List[ObjectGroup] = []

    def analyze_document(self, extracted_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        문서 분석 및 객체 인식

        Args:
            extracted_data: PDF에서 추출된 원본 데이터

        Returns:
            분석된 레이아웃 구조
        """
        logger.info("문서 객체 인식 시작")

        # 1. 객체 인식 및 분류
        self.objects = self._identify_objects(extracted_data)
        logger.info(f"총 {len(self.objects)}개 객체 인식")

        # 2. 객체 그룹화
        self.groups = self._group_objects(self.objects)
        logger.info(f"총 {len(self.groups)}개 그룹 생성")

        # 3. 레이아웃 최적화
        layout_structure = self._optimize_layout(self.groups)
        logger.info("레이아웃 최적화 완료")

        return layout_structure

    def _identify_objects(self, extracted_data: Dict[str, Any]) -> List[DocumentObject]:
        """객체 인식 및 분류"""
        objects = []
        object_counter = 0

        structured = extracted_data.get("structured_data", {})
        content_type = extracted_data.get("content_type", "general")

        # 1. 헤더/프로필 영역
        if content_type == "election":
            # 후보자 프로필
            if structured.get("candidate_name"):
                objects.append(DocumentObject(
                    object_id=f"obj_{object_counter}",
                    object_type=ObjectType.PROFILE,
                    content={
                        "name": structured.get("candidate_name"),
                        "party": structured.get("party"),
                        "number": structured.get("candidate_number"),
                        "district": structured.get("district")
                    },
                    position=(0, 0, 100, 15),
                    page_num=1,
                    priority=LayoutPriority.CRITICAL,
                    metadata={"section": "hero"},
                    group_id="profile"
                ))
                object_counter += 1

        # 2. 핵심 공약/주요 콘텐츠
        if content_type == "election" and structured.get("core_pledges"):
            for idx, pledge in enumerate(structured.get("core_pledges", [])):
                objects.append(DocumentObject(
                    object_id=f"obj_{object_counter}",
                    object_type=ObjectType.CARD,
                    content=pledge,
                    position=(0, 20 + idx*15, 100, 12),
                    page_num=1,
                    priority=LayoutPriority.HIGH,
                    metadata={"section": "pledges", "index": idx},
                    group_id="pledges"
                ))
                object_counter += 1

        # 3. 경력/경험
        if structured.get("career"):
            career_items = structured.get("career", [])
            for idx, career in enumerate(career_items):
                objects.append(DocumentObject(
                    object_id=f"obj_{object_counter}",
                    object_type=ObjectType.LIST,
                    content=career,
                    position=(0, 50 + idx*5, 100, 4),
                    page_num=2,
                    priority=LayoutPriority.MEDIUM,
                    metadata={"section": "career", "index": idx},
                    group_id="career"
                ))
                object_counter += 1

        # 4. 연락처
        if structured.get("contact_info"):
            objects.append(DocumentObject(
                object_id=f"obj_{object_counter}",
                object_type=ObjectType.CONTACT,
                content=structured.get("contact_info"),
                position=(0, 90, 100, 10),
                page_num=1,
                priority=LayoutPriority.LOW,
                metadata={"section": "footer"},
                group_id="contact"
            ))
            object_counter += 1

        # 5. 페이지별 텍스트 분석
        for page in extracted_data.get("pages", []):
            page_num = page.get("page_num", 1)
            text = page.get("text", "")

            # 제목 탐지
            titles = self._detect_titles(text)
            for title in titles:
                objects.append(DocumentObject(
                    object_id=f"obj_{object_counter}",
                    object_type=ObjectType.TITLE,
                    content=title,
                    position=(0, 0, 100, 5),
                    page_num=page_num,
                    priority=LayoutPriority.HIGH,
                    metadata={"detected": True}
                ))
                object_counter += 1

        return objects

    def _detect_titles(self, text: str) -> List[str]:
        """텍스트에서 제목 탐지"""
        titles = []
        lines = text.split('\n')

        for line in lines:
            line = line.strip()
            # 제목 패턴: 짧고, 대문자나 숫자로 시작, 특수문자 포함
            if len(line) < 50 and len(line) > 3:
                # 핵심공약, 주요실적, 경력 등의 키워드
                if any(keyword in line for keyword in ['핵심', '주요', '경력', '공약', '정책']):
                    titles.append(line)
                # 번호로 시작 (1., 2., 등)
                elif re.match(r'^\d+[\.\)]\s*\w+', line):
                    titles.append(line)

        return titles

    def _group_objects(self, objects: List[DocumentObject]) -> List[ObjectGroup]:
        """객체 그룹화"""
        groups_dict = {}

        # group_id로 객체 묶기
        for obj in objects:
            if obj.group_id:
                if obj.group_id not in groups_dict:
                    groups_dict[obj.group_id] = []
                groups_dict[obj.group_id].append(obj)

        # ObjectGroup 생성
        groups = []
        group_config = {
            "profile": {"type": "profile", "priority": LayoutPriority.CRITICAL, "layout": "hero"},
            "pledges": {"type": "pledges", "priority": LayoutPriority.HIGH, "layout": "accordion"},
            "career": {"type": "career", "priority": LayoutPriority.MEDIUM, "layout": "list"},
            "contact": {"type": "contact", "priority": LayoutPriority.LOW, "layout": "footer"}
        }

        for group_id, group_objects in groups_dict.items():
            config = group_config.get(group_id, {
                "type": "unknown",
                "priority": LayoutPriority.MEDIUM,
                "layout": "list"
            })

            groups.append(ObjectGroup(
                group_id=group_id,
                group_type=config["type"],
                objects=group_objects,
                priority=config["priority"],
                layout_hint=config["layout"]
            ))

        # 우선순위로 정렬
        groups.sort(key=lambda g: g.priority.value)

        return groups

    def _optimize_layout(self, groups: List[ObjectGroup]) -> Dict[str, Any]:
        """모바일 레이아웃 최적화"""
        layout_structure = {
            "sections": [],
            "layout_strategy": "mobile_first",
            "responsive": True
        }

        for group in groups:
            section = self._create_section_layout(group)
            layout_structure["sections"].append(section)

        return layout_structure

    def _create_section_layout(self, group: ObjectGroup) -> Dict[str, Any]:
        """섹션 레이아웃 생성"""

        if group.layout_hint == "hero":
            # Hero 섹션 (프로필)
            return {
                "id": group.group_id,
                "type": "hero",
                "component": "ProfileHero",
                "priority": group.priority.value,
                "objects": [self._object_to_dict(obj) for obj in group.objects],
                "mobile_layout": {
                    "display": "flex",
                    "flex_direction": "column",
                    "align_items": "center",
                    "padding": "20px",
                    "background": "gradient"
                }
            }

        elif group.layout_hint == "accordion":
            # Accordion 섹션 (공약)
            return {
                "id": group.group_id,
                "type": "accordion",
                "component": "ExpandableCard",
                "priority": group.priority.value,
                "objects": [self._object_to_dict(obj) for obj in group.objects],
                "mobile_layout": {
                    "display": "grid",
                    "gap": "15px",
                    "card_style": "elevated",
                    "expandable": True
                }
            }

        elif group.layout_hint == "list":
            # List 섹션 (경력)
            return {
                "id": group.group_id,
                "type": "list",
                "component": "TimelineList",
                "priority": group.priority.value,
                "objects": [self._object_to_dict(obj) for obj in group.objects],
                "mobile_layout": {
                    "display": "flex",
                    "flex_direction": "column",
                    "gap": "10px",
                    "list_style": "bullet"
                }
            }

        elif group.layout_hint == "footer":
            # Footer 섹션 (연락처)
            return {
                "id": group.group_id,
                "type": "footer",
                "component": "ContactFooter",
                "priority": group.priority.value,
                "objects": [self._object_to_dict(obj) for obj in group.objects],
                "mobile_layout": {
                    "position": "sticky",
                    "bottom": 0,
                    "background": "solid",
                    "padding": "15px"
                }
            }

        else:
            # 기본 섹션
            return {
                "id": group.group_id,
                "type": "generic",
                "component": "GenericSection",
                "priority": group.priority.value,
                "objects": [self._object_to_dict(obj) for obj in group.objects],
                "mobile_layout": {
                    "display": "block",
                    "padding": "15px"
                }
            }

    def _object_to_dict(self, obj: DocumentObject) -> Dict[str, Any]:
        """객체를 딕셔너리로 변환"""
        return {
            "id": obj.object_id,
            "type": obj.object_type.value,
            "content": obj.content,
            "position": obj.position,
            "page": obj.page_num,
            "priority": obj.priority.value,
            "metadata": obj.metadata
        }

    def generate_mobile_html_structure(self, layout_structure: Dict[str, Any]) -> str:
        """모바일 HTML 구조 생성"""
        html_parts = []

        for section in layout_structure.get("sections", []):
            section_html = self._generate_section_html(section)
            html_parts.append(section_html)

        return "\n".join(html_parts)

    def _generate_section_html(self, section: Dict[str, Any]) -> str:
        """섹션 HTML 생성"""
        section_type = section.get("type")
        section_id = section.get("id")

        if section_type == "hero":
            return self._generate_hero_section(section)
        elif section_type == "accordion":
            return self._generate_accordion_section(section)
        elif section_type == "list":
            return self._generate_list_section(section)
        elif section_type == "footer":
            return self._generate_footer_section(section)
        else:
            return f'<section id="{section_id}" class="section">\n<!-- Generic Section -->\n</section>'

    def _generate_hero_section(self, section: Dict[str, Any]) -> str:
        """Hero 섹션 HTML 생성"""
        return f'''<section id="{section.get('id')}" class="hero-section">
    <div class="hero-content">
        <!-- Profile content here -->
    </div>
</section>'''

    def _generate_accordion_section(self, section: Dict[str, Any]) -> str:
        """Accordion 섹션 HTML 생성"""
        cards_html = []
        for obj in section.get("objects", []):
            cards_html.append(f'''    <div class="promise-card">
        <div class="promise-header">
            <span class="promise-number">{obj.get('metadata', {}).get('index', 0) + 1}</span>
            <div class="promise-title">{obj.get('content', {}).get('title', '')}</div>
        </div>
        <div class="promise-details">
            <!-- Details here -->
        </div>
    </div>''')

        return f'''<section id="{section.get('id')}" class="section">
    <h2 class="section-title">핵심공약</h2>
    <div class="promises-container">
{chr(10).join(cards_html)}
    </div>
</section>'''

    def _generate_list_section(self, section: Dict[str, Any]) -> str:
        """List 섹션 HTML 생성"""
        return f'''<section id="{section.get('id')}" class="section">
    <h2 class="section-title">주요 실적</h2>
    <div class="list-container">
        <!-- List items here -->
    </div>
</section>'''

    def _generate_footer_section(self, section: Dict[str, Any]) -> str:
        """Footer 섹션 HTML 생성"""
        return f'''<footer id="{section.get('id')}" class="footer-section">
    <div class="contact-info">
        <!-- Contact information here -->
    </div>
</footer>'''


# 싱글톤 인스턴스
_layout_engine = None

def get_layout_engine() -> IntelligentLayoutEngine:
    """레이아웃 엔진 싱글톤 인스턴스"""
    global _layout_engine
    if _layout_engine is None:
        _layout_engine = IntelligentLayoutEngine()
    return _layout_engine
