"""
고급 레이아웃 최적화 엔진
과거 프로젝트의 ai_layout_optimizer + 현재 intelligent_layout_engine 통합
"""

import logging
from typing import List, Dict, Any, Tuple
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class SectionType(Enum):
    """섹션 타입"""
    HERO = "hero"  # 히어로 섹션 (큰 제목 + 이미지)
    TITLE = "title"  # 제목 섹션
    CONTENT = "content"  # 콘텐츠 섹션
    IMAGE = "image"  # 이미지 섹션
    LIST = "list"  # 리스트 섹션
    CARD = "card"  # 카드 섹션
    FOOTER = "footer"  # 푸터 섹션


class LayoutStrategy(Enum):
    """레이아웃 전략"""
    IMAGE_TOP_TEXT_BOTTOM = "image-top-text-bottom"
    TEXT_TOP_IMAGE_BOTTOM = "text-top-image-bottom"
    TEXT_LEFT_IMAGE_RIGHT = "text-left-image-right"
    IMAGE_LEFT_TEXT_RIGHT = "image-left-text-right"
    TEXT_CENTERED = "text-centered"
    IMAGE_FULL_WIDTH = "image-full-width"
    CARD_GRID = "card-grid"
    LIST_VERTICAL = "list-vertical"


@dataclass
class OptimizedSection:
    """최적화된 섹션"""
    section_id: str
    section_type: SectionType
    layout_strategy: LayoutStrategy
    background_color: str
    blocks: List[Dict[str, Any]]
    priority: int
    mobile_optimized: bool
    metadata: Dict[str, Any]


class AdvancedLayoutOptimizer:
    """
    고급 레이아웃 최적화 엔진

    기능:
    1. 과거 프로젝트의 섹션 그룹화 알고리즘
    2. 컬러 팔레트 자동 적용
    3. 모바일 최적화 레이아웃 전략
    4. Vision 분석 결과 통합
    """

    def __init__(self):
        # 폰트 크기 기준
        self.TITLE_FONT_SIZE = 14  # 제목
        self.SUBTITLE_FONT_SIZE = 11  # 부제
        self.BODY_FONT_SIZE = 9  # 본문

        # 이미지 크기 기준
        self.MAIN_IMAGE_WIDTH = 300  # 메인 이미지
        self.ICON_WIDTH = 100  # 아이콘

        # 배경색 팔레트 (선거 공보물 최적화)
        self.ELECTION_COLORS = [
            '#E11D48',  # 빨강 (주제색)
            '#DC2626',  # 진한 빨강
            '#F59E0B',  # 주황
            '#10B981',  # 녹색
            '#3B82F6',  # 파랑
        ]

        # 뉴스레터 색상
        self.NEWSLETTER_COLORS = [
            '#4CAF50',  # 녹색
            '#2196F3',  # 파란색
            '#FF9800',  # 주황색
            '#9C27B0',  # 보라색
            '#00BCD4',  # 청록색
        ]

    def analyze_blocks(self, blocks: List[Dict]) -> Dict[str, List]:
        """
        블록 분석 및 분류

        Args:
            blocks: 원본 블록 리스트

        Returns:
            분류된 블록 딕셔너리
        """
        result = {
            'titles': [],
            'subtitles': [],
            'body_texts': [],
            'main_images': [],
            'icons': [],
            'unknown': []
        }

        for block in blocks:
            block_type = block.get('type', 'unknown')

            if block_type == 'text':
                font_size = block.get('font_size', 10)

                if font_size >= self.TITLE_FONT_SIZE:
                    result['titles'].append(block)
                elif font_size >= self.SUBTITLE_FONT_SIZE:
                    result['subtitles'].append(block)
                elif font_size >= self.BODY_FONT_SIZE:
                    result['body_texts'].append(block)
                else:
                    result['unknown'].append(block)

            elif block_type == 'image':
                width = block.get('width', 0)

                if width >= self.MAIN_IMAGE_WIDTH:
                    result['main_images'].append(block)
                elif width >= self.ICON_WIDTH:
                    result['icons'].append(block)
                else:
                    result['unknown'].append(block)

            else:
                result['unknown'].append(block)

        logger.info(f"블록 분석 완료: 제목 {len(result['titles'])}, 본문 {len(result['body_texts'])}, 이미지 {len(result['main_images'])}")

        return result

    def group_into_sections(self, blocks: List[Dict]) -> List[Dict]:
        """
        블록을 섹션으로 그룹화 (과거 프로젝트 알고리즘 개선)

        섹션 분리 기준:
        1. Y 좌표 간격이 30pt 이상
        2. 제목 크기 변화 (큰 제목 → 작은 본문)
        3. 큰 텍스트 블록 (500자 이상) 후 분리
        4. 메인 이미지 전후 분리
        """
        if not blocks:
            return []

        # Y 좌표로 정렬
        sorted_blocks = sorted(blocks, key=lambda b: b.get('y', 0))

        sections = []
        current_section = {
            'blocks': [sorted_blocks[0]],
            'y_start': sorted_blocks[0].get('y', 0),
            'y_end': sorted_blocks[0].get('y', 0) + sorted_blocks[0].get('height', 0)
        }

        for i, block in enumerate(sorted_blocks[1:], 1):
            prev_block = sorted_blocks[i - 1]
            block_y = block.get('y', 0)
            gap = block_y - current_section['y_end']

            should_split = self._should_split_section(prev_block, block, gap)

            if should_split:
                # 새 섹션 시작
                sections.append(current_section)
                current_section = {
                    'blocks': [block],
                    'y_start': block_y,
                    'y_end': block_y + block.get('height', 0)
                }
            else:
                # 같은 섹션에 추가
                current_section['blocks'].append(block)
                current_section['y_end'] = block_y + block.get('height', 0)

        # 마지막 섹션 추가
        if current_section['blocks']:
            sections.append(current_section)

        logger.info(f"섹션 그룹화 완료: {len(sections)}개 섹션 생성")

        return sections

    def _should_split_section(
        self,
        prev_block: Dict,
        curr_block: Dict,
        gap: float
    ) -> bool:
        """섹션 분리 여부 판단"""

        # 1. 간격이 30pt 이상
        if gap >= 30:
            return True

        # 2. 제목 크기 텍스트 → 작은 텍스트 변화
        if (prev_block['type'] == 'text' and curr_block['type'] == 'text'):
            prev_font = prev_block.get('font_size', 10)
            curr_font = curr_block.get('font_size', 10)
            if prev_font >= self.TITLE_FONT_SIZE and curr_font < self.SUBTITLE_FONT_SIZE:
                return True

        # 3. 큰 텍스트 블록 (500자 이상) 후에는 분리
        if (prev_block['type'] == 'text' and
            len(prev_block.get('content', '')) >= 500 and gap >= 20):
            return True

        # 4. 메인 이미지 뒤에 텍스트
        if (prev_block['type'] == 'image' and curr_block['type'] == 'text' and
            prev_block.get('width', 0) >= self.MAIN_IMAGE_WIDTH and gap >= 20):
            return True

        # 5. 메인 이미지 뒤에 작은 이미지
        if (prev_block['type'] == 'image' and curr_block['type'] == 'image' and
            prev_block.get('width', 0) >= self.MAIN_IMAGE_WIDTH and
            curr_block.get('width', 0) < self.ICON_WIDTH and gap >= 15):
            return True

        return False

    def optimize_for_mobile(
        self,
        blocks: List[Dict],
        content_type: str = "general",
        page_width: int = 375,
        vision_data: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        모바일 최적화 레이아웃 생성

        Args:
            blocks: 원본 블록 리스트
            content_type: 문서 타입
            page_width: 모바일 화면 너비
            vision_data: Vision 분석 결과 (선택)

        Returns:
            최적화된 레이아웃 구조
        """
        logger.info(f"모바일 최적화 시작: {content_type}, {len(blocks)}개 블록")

        # 1. 블록 분석
        analyzed = self.analyze_blocks(blocks)

        # 2. 섹션 그룹화
        sections = self.group_into_sections(blocks)

        # 3. 색상 팔레트 선택
        if content_type == "election":
            color_palette = self.ELECTION_COLORS
        else:
            color_palette = self.NEWSLETTER_COLORS

        # 4. 각 섹션 최적화
        optimized_sections = []
        color_index = 0

        for idx, section in enumerate(sections):
            section_blocks = section['blocks']

            # 섹션 타입 결정
            section_type, layout_strategy = self._determine_section_type(
                section_blocks,
                analyzed
            )

            # 배경색 결정
            if section_type in [SectionType.HERO, SectionType.TITLE]:
                background = color_palette[color_index % len(color_palette)]
                color_index += 1
            elif section_type == SectionType.CARD:
                background = '#FFFBF5'  # 베이지색 카드
            else:
                background = '#FFFFFF'  # 흰색

            # 최적화된 섹션 생성
            optimized_section = OptimizedSection(
                section_id=f"section_{idx}",
                section_type=section_type,
                layout_strategy=layout_strategy,
                background_color=background,
                blocks=section_blocks,
                priority=self._calculate_priority(section_type),
                mobile_optimized=True,
                metadata={
                    "y_start": section['y_start'],
                    "y_end": section['y_end'],
                    "block_count": len(section_blocks)
                }
            )

            optimized_sections.append(optimized_section)

        # 5. Vision 데이터 통합 (있을 경우)
        if vision_data:
            optimized_sections = self._integrate_vision_data(
                optimized_sections,
                vision_data
            )

        # 6. 레이아웃 정보 생성
        layout_info = {
            "page_width": page_width,
            "total_sections": len(optimized_sections),
            "content_type": content_type,
            "has_hero": any(s.section_type == SectionType.HERO for s in optimized_sections),
            "color_sections": sum(1 for s in optimized_sections if s.background_color != '#FFFFFF'),
            "analyzed_blocks": {
                "titles": len(analyzed['titles']),
                "subtitles": len(analyzed['subtitles']),
                "body_texts": len(analyzed['body_texts']),
                "main_images": len(analyzed['main_images']),
                "icons": len(analyzed['icons'])
            }
        }

        logger.info(f"모바일 최적화 완료: {len(optimized_sections)}개 섹션")

        return {
            "sections": [self._section_to_dict(s) for s in optimized_sections],
            "layout_info": layout_info
        }

    def _determine_section_type(
        self,
        section_blocks: List[Dict],
        analyzed: Dict[str, List]
    ) -> Tuple[SectionType, LayoutStrategy]:
        """섹션 타입 및 레이아웃 전략 결정"""

        has_title = any(
            b['type'] == 'text' and b.get('font_size', 0) >= self.TITLE_FONT_SIZE
            for b in section_blocks
        )
        has_main_image = any(
            b['type'] == 'image' and b.get('width', 0) >= self.MAIN_IMAGE_WIDTH
            for b in section_blocks
        )

        # 히어로 섹션 (큰 제목 + 메인 이미지)
        if has_title and has_main_image:
            return SectionType.HERO, LayoutStrategy.IMAGE_TOP_TEXT_BOTTOM

        # 제목 섹션
        elif has_title:
            return SectionType.TITLE, LayoutStrategy.TEXT_CENTERED

        # 이미지 섹션
        elif has_main_image:
            return SectionType.IMAGE, LayoutStrategy.IMAGE_FULL_WIDTH

        # 리스트 섹션 (여러 텍스트 블록)
        elif len(section_blocks) >= 3 and all(b['type'] == 'text' for b in section_blocks):
            return SectionType.LIST, LayoutStrategy.LIST_VERTICAL

        # 카드 섹션
        else:
            return SectionType.CARD, LayoutStrategy.TEXT_CENTERED

    def _calculate_priority(self, section_type: SectionType) -> int:
        """섹션 우선순위 계산"""
        priority_map = {
            SectionType.HERO: 1,
            SectionType.TITLE: 2,
            SectionType.CARD: 3,
            SectionType.IMAGE: 4,
            SectionType.LIST: 5,
            SectionType.CONTENT: 6,
            SectionType.FOOTER: 7,
        }
        return priority_map.get(section_type, 5)

    def _integrate_vision_data(
        self,
        sections: List[OptimizedSection],
        vision_data: Dict
    ) -> List[OptimizedSection]:
        """Vision 분석 결과를 섹션에 통합"""

        # Vision에서 감지한 블록과 섹션 매칭
        vision_blocks = vision_data.get('content_blocks', [])

        for section in sections:
            # 섹션의 Y 범위
            y_start = section.metadata['y_start']
            y_end = section.metadata['y_end']

            # 해당 범위에 속하는 Vision 블록 찾기
            matching_vision_blocks = [
                vb for vb in vision_blocks
                if y_start <= vb.get('position', {}).get('y', 0) <= y_end
            ]

            if matching_vision_blocks:
                # Vision 데이터 메타데이터에 추가
                section.metadata['vision_blocks'] = matching_vision_blocks
                section.metadata['vision_confidence'] = sum(
                    vb.get('confidence', 0) for vb in matching_vision_blocks
                ) / len(matching_vision_blocks)

        return sections

    def _section_to_dict(self, section: OptimizedSection) -> Dict[str, Any]:
        """OptimizedSection을 딕셔너리로 변환"""
        return {
            "id": section.section_id,
            "type": section.section_type.value,
            "layout_strategy": section.layout_strategy.value,
            "background": section.background_color,
            "blocks": section.blocks,
            "priority": section.priority,
            "mobile_optimized": section.mobile_optimized,
            "metadata": section.metadata
        }


# 싱글톤 인스턴스
_layout_optimizer = None

def get_layout_optimizer() -> AdvancedLayoutOptimizer:
    """레이아웃 최적화 엔진 싱글톤 인스턴스"""
    global _layout_optimizer
    if _layout_optimizer is None:
        _layout_optimizer = AdvancedLayoutOptimizer()
    return _layout_optimizer
