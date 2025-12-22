"""
여의도순복음교회 주보 검증기 v1.0
- OCR 결과와 HTML 출력물 비교 검증
- 100% 정확도 달성을 위한 자동 검증 시스템
"""

import os
import re
import json
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


@dataclass
class ValidationError:
    """검증 오류"""
    field: str
    expected: str
    actual: str
    severity: str  # 'critical', 'warning', 'info'
    page: int = 0
    suggestion: str = ""


@dataclass
class ValidationResult:
    """검증 결과"""
    job_id: str
    timestamp: str
    church_id: str
    total_fields: int
    passed_fields: int
    accuracy: float
    errors: List[ValidationError] = field(default_factory=list)
    warnings: List[ValidationError] = field(default_factory=list)
    is_valid: bool = True


class ChurchBulletinVerifier:
    """교회 주보 검증기"""

    def __init__(self, template_path: str = None):
        if template_path is None:
            template_path = os.path.join(
                os.path.dirname(__file__),
                "learning_data/church_bulletin/fgfc_template.json"
            )

        self.template = self._load_template(template_path)
        self.validation_rules = self.template.get("validation_rules", {})
        self.ocr_hints = self.template.get("ocr_hints", {})

        # 성경책 이름 목록 (검증용)
        self.bible_books = [
            "창세기", "출애굽기", "레위기", "민수기", "신명기",
            "여호수아", "사사기", "룻기", "사무엘상", "사무엘하",
            "열왕기상", "열왕기하", "역대상", "역대하", "에스라",
            "느헤미야", "에스더", "욥기", "시편", "잠언", "전도서",
            "아가", "이사야", "예레미야", "예레미야애가", "에스겔",
            "다니엘", "호세아", "요엘", "아모스", "오바댜", "요나",
            "미가", "나훔", "하박국", "스바냐", "학개", "스가랴", "말라기",
            "마태복음", "마가복음", "누가복음", "요한복음", "사도행전",
            "로마서", "고린도전서", "고린도후서", "갈라디아서", "에베소서",
            "빌립보서", "골로새서", "데살로니가전서", "데살로니가후서",
            "디모데전서", "디모데후서", "디도서", "빌레몬서", "히브리서",
            "야고보서", "베드로전서", "베드로후서", "요한일서", "요한이서",
            "요한삼서", "유다서", "요한계시록"
        ]

        # 일반 오타 수정 매핑
        self.common_typos = {
            "여의도순북음": "여의도순복음",
            "여의도순복읍": "여의도순복음",
            "대렴절": "대림절",
            "성단절": "성탄절",
            "추수감샤절": "추수감사절",
        }

        logger.info(f"ChurchBulletinVerifier 초기화 완료: {self.template.get('church_name')}")

    def _load_template(self, path: str) -> Dict:
        """템플릿 로드"""
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            logger.warning(f"템플릿 파일 없음: {path}, 기본 템플릿 사용")
            return self._get_default_template()

    def _get_default_template(self) -> Dict:
        """기본 템플릿 반환"""
        return {
            "church_id": "default",
            "church_name": "기본 교회",
            "validation_rules": {},
            "ocr_hints": {}
        }

    def verify_ocr_result(self, ocr_data: Dict, page_num: int = 0) -> ValidationResult:
        """
        OCR 추출 결과 검증

        Args:
            ocr_data: Vision OCR에서 추출된 데이터
            page_num: 페이지 번호

        Returns:
            ValidationResult
        """
        errors = []
        warnings = []
        total_fields = 0
        passed_fields = 0

        # 1. 날짜 형식 검증
        if "date" in ocr_data:
            total_fields += 1
            if self._validate_date(ocr_data["date"]):
                passed_fields += 1
            else:
                errors.append(ValidationError(
                    field="date",
                    expected="YYYY년 MM월 DD일 형식",
                    actual=ocr_data["date"],
                    severity="critical",
                    page=page_num,
                    suggestion="날짜 형식을 확인하세요"
                ))

        # 2. 성경 구절 검증
        scripture_fields = ["verse_ref", "sermon_scripture", "devotional_scripture"]
        for field_name in scripture_fields:
            if field_name in ocr_data and ocr_data[field_name]:
                total_fields += 1
                is_valid, suggestion = self._validate_scripture(ocr_data[field_name])
                if is_valid:
                    passed_fields += 1
                else:
                    errors.append(ValidationError(
                        field=field_name,
                        expected="성경책명 장:절 형식",
                        actual=ocr_data[field_name],
                        severity="critical",
                        page=page_num,
                        suggestion=suggestion
                    ))

        # 3. 찬송가 번호 검증
        if "hymns" in ocr_data:
            for hymn in ocr_data.get("hymns", []):
                total_fields += 1
                if self._validate_hymn_number(hymn):
                    passed_fields += 1
                else:
                    warnings.append(ValidationError(
                        field="hymn",
                        expected="1-645 범위의 찬송가 번호",
                        actual=str(hymn),
                        severity="warning",
                        page=page_num
                    ))

        # 4. 예배 시간 검증
        if "services" in ocr_data:
            for service in ocr_data.get("services", []):
                if "time" in service:
                    total_fields += 1
                    if self._validate_time(service["time"]):
                        passed_fields += 1
                    else:
                        errors.append(ValidationError(
                            field="service_time",
                            expected="HH:MM 형식",
                            actual=service["time"],
                            severity="warning",
                            page=page_num
                        ))

        # 5. 교회 이름 오타 검증
        if "church_name" in ocr_data:
            total_fields += 1
            corrected = self._fix_common_typos(ocr_data["church_name"])
            if corrected == ocr_data["church_name"]:
                passed_fields += 1
            else:
                errors.append(ValidationError(
                    field="church_name",
                    expected=corrected,
                    actual=ocr_data["church_name"],
                    severity="critical",
                    page=page_num,
                    suggestion=f"'{corrected}'로 수정 권장"
                ))

        # 정확도 계산
        accuracy = (passed_fields / total_fields * 100) if total_fields > 0 else 100.0
        is_valid = len([e for e in errors if e.severity == "critical"]) == 0

        return ValidationResult(
            job_id=ocr_data.get("job_id", "unknown"),
            timestamp=datetime.now().isoformat(),
            church_id=self.template.get("church_id", "fgfc"),
            total_fields=total_fields,
            passed_fields=passed_fields,
            accuracy=accuracy,
            errors=errors,
            warnings=warnings,
            is_valid=is_valid
        )

    def verify_html_output(self, html_content: str, ocr_data: Dict) -> ValidationResult:
        """
        생성된 HTML과 OCR 데이터 비교 검증

        Args:
            html_content: 생성된 HTML 문자열
            ocr_data: 원본 OCR 데이터

        Returns:
            ValidationResult
        """
        errors = []
        warnings = []
        total_fields = 0
        passed_fields = 0

        # 1. 날짜 일치 확인
        if "date" in ocr_data:
            total_fields += 1
            if ocr_data["date"] in html_content:
                passed_fields += 1
            else:
                errors.append(ValidationError(
                    field="date",
                    expected=ocr_data["date"],
                    actual="HTML에서 찾을 수 없음",
                    severity="critical",
                    suggestion="날짜가 HTML에 올바르게 표시되는지 확인"
                ))

        # 2. 설교 제목 일치 확인
        if "sermon_title" in ocr_data:
            total_fields += 1
            # HTML에서 일부 특수문자 처리된 버전도 확인
            sermon_title = ocr_data["sermon_title"]
            if sermon_title in html_content or self._normalize_text(sermon_title) in self._normalize_text(html_content):
                passed_fields += 1
            else:
                errors.append(ValidationError(
                    field="sermon_title",
                    expected=sermon_title,
                    actual="HTML에서 찾을 수 없음",
                    severity="critical",
                    suggestion="설교 제목이 누락되었습니다"
                ))

        # 3. 성경 구절 텍스트 일치 확인
        if "verse_text" in ocr_data:
            total_fields += 1
            verse_text = ocr_data["verse_text"]
            # 처음 20자로 비교 (전체 텍스트 비교보다 유연)
            if len(verse_text) > 20:
                if verse_text[:20] in html_content:
                    passed_fields += 1
                else:
                    warnings.append(ValidationError(
                        field="verse_text",
                        expected=verse_text[:50] + "...",
                        actual="HTML에서 일치하지 않음",
                        severity="warning",
                        suggestion="오늘의 말씀 텍스트를 확인하세요"
                    ))
            else:
                if verse_text in html_content:
                    passed_fields += 1

        # 4. 필수 섹션 존재 확인
        required_sections = ["todays-word", "worship", "sermon-word", "news"]
        for section_id in required_sections:
            total_fields += 1
            if f'id="{section_id}"' in html_content or f"id='{section_id}'" in html_content:
                passed_fields += 1
            else:
                warnings.append(ValidationError(
                    field=f"section_{section_id}",
                    expected=f"섹션 ID: {section_id}",
                    actual="HTML에서 찾을 수 없음",
                    severity="warning"
                ))

        # 5. 네비게이션 탭 확인
        nav_tabs = self.template.get("html_structure", {}).get("nav_tabs", [])
        for tab in nav_tabs:
            total_fields += 1
            if tab in html_content:
                passed_fields += 1

        # 정확도 계산
        accuracy = (passed_fields / total_fields * 100) if total_fields > 0 else 100.0
        is_valid = len([e for e in errors if e.severity == "critical"]) == 0

        return ValidationResult(
            job_id=ocr_data.get("job_id", "unknown"),
            timestamp=datetime.now().isoformat(),
            church_id=self.template.get("church_id", "fgfc"),
            total_fields=total_fields,
            passed_fields=passed_fields,
            accuracy=accuracy,
            errors=errors,
            warnings=warnings,
            is_valid=is_valid
        )

    def _validate_date(self, date_str: str) -> bool:
        """날짜 형식 검증"""
        patterns = [
            r"^\d{4}년\s*\d{1,2}월\s*\d{1,2}일$",
            r"^\d{4}-\d{2}-\d{2}$",
            r"^\d{4}\.\d{1,2}\.\d{1,2}$"
        ]
        for pattern in patterns:
            if re.match(pattern, date_str.strip()):
                return True
        return False

    def _validate_scripture(self, scripture: str) -> Tuple[bool, str]:
        """성경 구절 검증"""
        # 패턴: 책이름 장:절(-절)
        pattern = r"^([가-힣]+)\s*(\d+):(\d+)(?:-(\d+))?$"
        match = re.match(pattern, scripture.strip())

        if not match:
            return False, "형식이 올바르지 않습니다. 예: 누가복음 3:4-6"

        book_name = match.group(1)

        # 책 이름 검증
        if book_name not in self.bible_books:
            # 유사한 책 이름 찾기
            similar = self._find_similar_book(book_name)
            if similar:
                return False, f"'{book_name}'을(를) '{similar}'(으)로 수정하세요"
            return False, f"'{book_name}'은(는) 유효한 성경책 이름이 아닙니다"

        return True, ""

    def _find_similar_book(self, book_name: str) -> Optional[str]:
        """유사한 성경책 이름 찾기"""
        for book in self.bible_books:
            # 처음 2글자가 같으면 유사하다고 판단
            if len(book_name) >= 2 and book[:2] == book_name[:2]:
                return book
        return None

    def _validate_hymn_number(self, hymn_str: str) -> bool:
        """찬송가 번호 검증 (1-645)"""
        # 숫자만 추출
        numbers = re.findall(r"\d+", str(hymn_str))
        for num in numbers:
            if 1 <= int(num) <= 645:
                return True
        return False

    def _validate_time(self, time_str: str) -> bool:
        """시간 형식 검증"""
        pattern = r"^\d{1,2}:\d{2}$"
        if re.match(pattern, time_str.strip()):
            parts = time_str.split(":")
            hour = int(parts[0])
            minute = int(parts[1])
            return 0 <= hour <= 23 and 0 <= minute <= 59
        return False

    def _fix_common_typos(self, text: str) -> str:
        """일반적인 오타 수정"""
        result = text
        for typo, correct in self.common_typos.items():
            result = result.replace(typo, correct)
        return result

    def _normalize_text(self, text: str) -> str:
        """텍스트 정규화 (공백, 특수문자 제거)"""
        return re.sub(r"\s+", "", text)

    def auto_correct(self, ocr_data: Dict) -> Tuple[Dict, List[str]]:
        """
        자동 교정 수행

        Returns:
            (교정된 데이터, 교정 내역 목록)
        """
        corrected = ocr_data.copy()
        corrections = []

        # 교회 이름 오타 수정
        if "church_name" in corrected:
            original = corrected["church_name"]
            fixed = self._fix_common_typos(original)
            if fixed != original:
                corrected["church_name"] = fixed
                corrections.append(f"교회명: '{original}' → '{fixed}'")

        # 성경 구절 형식 정규화
        scripture_fields = ["verse_ref", "sermon_scripture"]
        for field in scripture_fields:
            if field in corrected:
                original = corrected[field]
                # 공백 정규화
                normalized = re.sub(r"\s+", " ", original.strip())
                if normalized != original:
                    corrected[field] = normalized
                    corrections.append(f"{field}: 공백 정규화")

        return corrected, corrections

    def get_verification_report(self, result: ValidationResult) -> str:
        """검증 결과 리포트 생성"""
        report = f"""
=== 주보 검증 리포트 ===
검증 시간: {result.timestamp}
교회: {self.template.get('church_name', 'Unknown')}

📊 검증 결과
- 전체 필드: {result.total_fields}개
- 통과 필드: {result.passed_fields}개
- 정확도: {result.accuracy:.1f}%
- 상태: {'✅ 통과' if result.is_valid else '❌ 실패'}

"""
        if result.errors:
            report += "❌ 오류 목록:\n"
            for err in result.errors:
                report += f"  [{err.severity.upper()}] {err.field}: {err.actual}\n"
                report += f"    → 예상: {err.expected}\n"
                if err.suggestion:
                    report += f"    💡 {err.suggestion}\n"

        if result.warnings:
            report += "\n⚠️ 경고 목록:\n"
            for warn in result.warnings:
                report += f"  {warn.field}: {warn.actual}\n"

        return report


# 싱글톤 인스턴스
_verifier_instance = None

def get_bulletin_verifier() -> ChurchBulletinVerifier:
    """검증기 싱글톤 반환"""
    global _verifier_instance
    if _verifier_instance is None:
        _verifier_instance = ChurchBulletinVerifier()
    return _verifier_instance


# API 엔드포인트용 함수들
def verify_bulletin(ocr_data: Dict, html_content: str = None) -> Dict:
    """
    주보 검증 API 함수

    Args:
        ocr_data: OCR 추출 데이터
        html_content: 생성된 HTML (선택)

    Returns:
        검증 결과 딕셔너리
    """
    verifier = get_bulletin_verifier()

    # OCR 결과 검증
    ocr_result = verifier.verify_ocr_result(ocr_data)

    # HTML 출력 검증 (제공된 경우)
    html_result = None
    if html_content:
        html_result = verifier.verify_html_output(html_content, ocr_data)

    # 자동 교정
    corrected_data, corrections = verifier.auto_correct(ocr_data)

    return {
        "ocr_validation": asdict(ocr_result),
        "html_validation": asdict(html_result) if html_result else None,
        "auto_corrections": corrections,
        "corrected_data": corrected_data,
        "overall_accuracy": ocr_result.accuracy,
        "is_valid": ocr_result.is_valid,
        "report": verifier.get_verification_report(ocr_result)
    }
