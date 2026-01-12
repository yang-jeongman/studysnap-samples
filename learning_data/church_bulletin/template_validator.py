"""
여의도순복음교회 주보 검증 시스템
fgfc_template.json 기반으로 생성된 HTML의 필수 섹션 존재 확인
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Tuple
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


class TemplateValidator:
    """템플릿 기반 HTML 검증기"""

    def __init__(self, template_path: str = None):
        """
        Args:
            template_path: fgfc_template.json 경로
        """
        if template_path is None:
            template_path = Path(__file__).parent / "fgfc_template.json"

        with open(template_path, 'r', encoding='utf-8') as f:
            self.template = json.load(f)

        logger.info(f"템플릿 로드: {template_path}")

    def validate_html(self, html: str) -> Dict:
        """
        생성된 HTML이 템플릿 요구사항을 만족하는지 검증

        Args:
            html: 검증할 HTML 문자열

        Returns:
            {
                "valid": bool,
                "errors": List[str],
                "warnings": List[str],
                "missing_sections": List[str]
            }
        """
        soup = BeautifulSoup(html, 'html.parser')
        errors = []
        warnings = []
        missing_sections = []

        # 페이지별 섹션 검증
        for page_num, page_config in self.template["pdf_structure"]["pages"].items():
            page_name = page_config["name"]
            logger.info(f"페이지 {page_num} ({page_name}) 검증 중...")

            for section in page_config["sections"]:
                section_id = section["id"]
                is_required = section.get("required", False)

                # 섹션 존재 확인
                exists = self._check_section_exists(soup, section_id, section)

                if not exists:
                    if is_required:
                        error_msg = f"[필수] {page_name} - {section_id} 섹션 누락"
                        errors.append(error_msg)
                        missing_sections.append(section_id)
                        logger.error(error_msg)
                    else:
                        warning_msg = f"[선택] {page_name} - {section_id} 섹션 누락"
                        warnings.append(warning_msg)
                        logger.warning(warning_msg)

        # 검증 결과
        is_valid = len(errors) == 0

        result = {
            "valid": is_valid,
            "errors": errors,
            "warnings": warnings,
            "missing_sections": missing_sections,
            "summary": {
                "total_checks": len(errors) + len(warnings),
                "errors_count": len(errors),
                "warnings_count": len(warnings)
            }
        }

        if is_valid:
            logger.info("✅ HTML 검증 통과")
        else:
            logger.error(f"❌ HTML 검증 실패: {len(errors)}개 오류")

        return result

    def _check_section_exists(self, soup: BeautifulSoup, section_id: str, section_config: Dict) -> bool:
        """
        섹션이 HTML에 존재하는지 확인

        Args:
            soup: BeautifulSoup 객체
            section_id: 섹션 ID (예: "sermon_word_content")
            section_config: 섹션 설정

        Returns:
            섹션 존재 여부
        """
        section_type = section_config.get("type")

        # ID 기반 매핑
        selector_mapping = {
            "church_name": ".church-name",
            "church_name_en": ".church-name-en",
            "date": ".jubo-date, .date",
            "volume_issue": ".volume-issue",
            "seasonal_badge": ".seasonal-badge, .slogan-badge",
            "todays_verse": ".verse-section, #todays-word, #todays_verse",
            "service_schedule": ".worship-card",
            "worship_order": ".order-item, .worship-item",
            "sermon_title": ".sermon-title-ko, .sermon-card-title",
            "sermon_scripture": ".sermon-scripture, .verse-ref",
            "sermon_word_title": ".sermon-word-title, .sermon-subtitle",
            "sermon_word_content": ".sermon-full-text, .sermon-content, .sermon-paragraph",
            "sermon_author": ".sermon-pastor, .sermon-author",
            "choir_schedule": ".choir-table, #choir",
            "news_worship": ".news-category-worship, .news-section",
            "news_recruit": ".news-category-recruit",
            "news_info": ".news-category-info",
            "devotional_title": ".devotional-title",
            "devotional_scripture": ".devotional-scripture, .verse-ref",
            "devotional_content": ".devotional-content, .devotional-paragraph"
        }

        # 섹션별 선택자
        selector = selector_mapping.get(section_id)
        if selector:
            # 여러 선택자 중 하나라도 존재하면 OK
            for sel in selector.split(", "):
                elem = soup.select_one(sel.strip())
                if elem:
                    # 내용이 비어있지 않은지 확인
                    text_content = elem.get_text(strip=True)
                    if text_content and text_content not in ["사회자", "-", ""]:
                        return True

        # 타입 기반 검증
        if section_type == "table":
            tables = soup.find_all('table')
            return len(tables) > 0

        elif section_type == "list":
            lists = soup.find_all(['ul', 'ol'])
            return len(lists) > 0

        elif section_type == "text_blocks":
            # 문단이 있는지 확인
            paragraphs = soup.find_all('p')
            return len(paragraphs) > 0

        return False

    def validate_data(self, extracted_data: Dict) -> Dict:
        """
        PDF에서 추출된 데이터가 템플릿 요구사항을 만족하는지 검증

        Args:
            extracted_data: PDF에서 추출한 데이터

        Returns:
            검증 결과
        """
        errors = []
        warnings = []

        # 필수 필드 확인
        required_fields = {
            "date": "날짜",
            "worship_services": "예배 정보",
            "sermon": "설교 정보",
            "devotional": "오늘의 양식"
        }

        for field_key, field_name in required_fields.items():
            if field_key not in extracted_data or not extracted_data[field_key]:
                errors.append(f"필수 필드 누락: {field_name} ({field_key})")

        # 예배 서비스 검증
        services = extracted_data.get("worship_services", [])
        if len(services) == 0:
            errors.append("예배 서비스 데이터 없음")
        else:
            for i, service in enumerate(services):
                # 필수 필드 확인
                service_required = ["part", "presider", "scripture", "prayer"]
                for req_field in service_required:
                    if req_field not in service or not service[req_field]:
                        warnings.append(f"예배 {i+1} - {req_field} 필드 누락")

        # 설교 검증
        sermon = extracted_data.get("sermon", {})
        if sermon:
            if not sermon.get("title"):
                errors.append("설교 제목 누락")
            if not sermon.get("intro"):
                warnings.append("설교 서론 누락")
            if not sermon.get("points"):
                warnings.append("설교 포인트 누락")

        is_valid = len(errors) == 0

        return {
            "valid": is_valid,
            "errors": errors,
            "warnings": warnings,
            "summary": {
                "total_checks": len(errors) + len(warnings),
                "errors_count": len(errors),
                "warnings_count": len(warnings)
            }
        }

    def get_required_sections(self) -> List[str]:
        """필수 섹션 목록 반환"""
        required = []

        for page_num, page_config in self.template["pdf_structure"]["pages"].items():
            for section in page_config["sections"]:
                if section.get("required", False):
                    required.append(section["id"])

        return required

    def suggest_fixes(self, validation_result: Dict) -> List[str]:
        """
        검증 실패 시 수정 제안

        Args:
            validation_result: validate_html() 또는 validate_data() 결과

        Returns:
            수정 제안 목록
        """
        suggestions = []

        for error in validation_result.get("errors", []):
            if "sermon_word_content" in error:
                suggestions.append("설교 본문(생명의 말씀)을 추가하세요. PDF 4페이지에서 추출 가능합니다.")

            elif "worship_services" in error or "service_schedule" in error:
                suggestions.append("예배 정보(사회자, 대표기도 등)를 추가하세요. PDF 2페이지 표에서 추출 가능합니다.")

            elif "devotional_content" in error:
                suggestions.append("오늘의 양식 본문을 추가하세요. PDF 6페이지에서 추출 가능합니다.")

            elif "choir_schedule" in error:
                suggestions.append("금주의 찬양 정보를 추가하세요. PDF 3페이지 표에서 추출 가능합니다.")

        return suggestions


# 편의 함수
def validate_bulletin_html(html: str) -> Dict:
    """
    주보 HTML 검증 (편의 함수)

    Args:
        html: 검증할 HTML

    Returns:
        검증 결과
    """
    validator = TemplateValidator()
    return validator.validate_html(html)


def validate_bulletin_data(extracted_data: Dict) -> Dict:
    """
    추출 데이터 검증 (편의 함수)

    Args:
        extracted_data: 추출된 데이터

    Returns:
        검증 결과
    """
    validator = TemplateValidator()
    return validator.validate_data(extracted_data)
