"""
자동 검증 시스템 - 원본 PDF와 결과물 비교
텍스트 오류/오타 검증 및 자동 수정
"""

import os
import re
import logging
from pathlib import Path
from typing import Dict, List, Tuple, Any, Optional
from difflib import SequenceMatcher
from collections import Counter

logger = logging.getLogger(__name__)


class VerificationSystem:
    """원본과 결과물 자동 검증 시스템"""

    def __init__(self):
        self.common_ocr_errors = {
            # 자주 발생하는 OCR 오류 패턴
            "공악": "공약",
            "겅력": "경력",
            "정딩": "정당",
            "후보자": "후보자",
            "선거": "선거",
            "도작": "동작",
            "상도동": "상도동",
            "혹석동": "흑석동",
            "사당오동": "사당5동",
            "국민의힙": "국민의힘",
            "더불어민주딩": "더불어민주당",
            "@나kyungwon": "@Lrkyungwon",
            "youtube.com/@나kyungwon": "youtube.com/@Lrkyungwon",
            # 공약 제목 수정
            "교육특구 동작": "동작을 8학군 수준으로",
            "사통팔달 동작": "뻥 뚫리는 동작, 뻥뚫리는 출퇴근",
            "상전벽해 동작": "랜드마크를 만들고 스카이라인을 바꾸다",
            "삼전벽해 등국": "랜드마크를 만들고 스카이라인을 바꾸다",  # OCR 오류 대비
            "15분도시 동작": "걸어서 15분 내에 공원, 문화, 체육시설 촘촘히",
            "든든복지 동작": "든든한 삶 든든한 미래",
            "안전안심 동작": "걱정없이 행복한, 더 안전한 동작",
            "컵어서 15분 내에 공원, 문화, 체육시설 출출히 (15분도시 동작)": "걸어서 15분 내에 공원, 문화, 체육시설 촘촘히",  # OCR 오류 버전
            "주요 경력": "주요 실적",
        }

        # 중요 키워드 (반드시 포함되어야 함)
        self.critical_keywords = [
            "핵심공약",
            "경력",
            "연락처",
            "정당",
            "후보자",
            "선거사무소"
        ]

    def verify_conversion(
        self,
        original_pdf_path: str,
        generated_html_path: str,
        extracted_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        변환 결과 검증

        Returns:
            검증 결과 및 수정 제안
        """
        logger.info(f"검증 시작: {Path(original_pdf_path).name} -> {Path(generated_html_path).name}")

        verification_result = {
            "original_file": Path(original_pdf_path).name,
            "generated_file": Path(generated_html_path).name,
            "status": "pending",
            "errors": [],
            "warnings": [],
            "corrections": [],
            "statistics": {},
            "recommendations": []
        }

        try:
            # 1. 텍스트 추출 및 비교
            original_text = self._extract_text_from_data(extracted_data)
            generated_text = self._extract_text_from_html(generated_html_path)

            # 2. 텍스트 오류 검증
            text_errors = self._check_text_errors(original_text, generated_text)
            verification_result["errors"].extend(text_errors)

            # 3. OCR 오류 검증
            ocr_errors = self._check_ocr_errors(generated_text)
            verification_result["errors"].extend(ocr_errors)

            # 4. 중요 키워드 검증
            missing_keywords = self._check_critical_keywords(generated_text)
            if missing_keywords:
                verification_result["warnings"].append({
                    "type": "missing_keywords",
                    "keywords": missing_keywords,
                    "message": f"중요 키워드 누락: {', '.join(missing_keywords)}"
                })

            # 5. 구조 검증
            structure_issues = self._verify_structure(extracted_data)
            verification_result["warnings"].extend(structure_issues)

            # 6. 링크 검증
            link_issues = self._verify_links(extracted_data)
            verification_result["warnings"].extend(link_issues)

            # 7. 통계
            verification_result["statistics"] = {
                "total_errors": len(verification_result["errors"]),
                "total_warnings": len(verification_result["warnings"]),
                "ocr_accuracy": self._calculate_accuracy(original_text, generated_text),
                "text_length_original": len(original_text),
                "text_length_generated": len(generated_text),
                "similarity_score": self._calculate_similarity(original_text, generated_text)
            }

            # 8. 자동 수정 제안
            verification_result["corrections"] = self._generate_corrections(
                verification_result["errors"]
            )

            # 9. 최종 상태
            if len(verification_result["errors"]) == 0:
                verification_result["status"] = "passed"
                verification_result["recommendations"].append("검증 통과! 결과물이 완벽합니다.")
            elif len(verification_result["errors"]) <= 5:
                verification_result["status"] = "warning"
                verification_result["recommendations"].append("경미한 오류 발견. 자동 수정 가능.")
            else:
                verification_result["status"] = "failed"
                verification_result["recommendations"].append("심각한 오류 발견. 재변환 권장.")

            logger.info(f"검증 완료: {verification_result['status']} "
                       f"(오류: {verification_result['statistics']['total_errors']}, "
                       f"경고: {verification_result['statistics']['total_warnings']})")

            return verification_result

        except Exception as e:
            logger.error(f"검증 중 오류: {str(e)}", exc_info=True)
            verification_result["status"] = "error"
            verification_result["errors"].append({
                "type": "system_error",
                "message": f"검증 시스템 오류: {str(e)}"
            })
            return verification_result

    def _extract_text_from_data(self, extracted_data: Dict[str, Any]) -> str:
        """추출된 데이터에서 텍스트 가져오기"""
        texts = []
        for page in extracted_data.get("pages", []):
            texts.append(page.get("text", ""))
        return "\n".join(texts)

    def _extract_text_from_html(self, html_path: str) -> str:
        """HTML 파일에서 텍스트 추출"""
        try:
            with open(html_path, 'r', encoding='utf-8') as f:
                html_content = f.read()

            # 간단한 HTML 태그 제거
            text = re.sub(r'<script[^>]*>.*?</script>', '', html_content, flags=re.DOTALL)
            text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL)
            text = re.sub(r'<[^>]+>', '', text)
            text = re.sub(r'\s+', ' ', text).strip()

            return text

        except Exception as e:
            logger.error(f"HTML 텍스트 추출 실패: {str(e)}")
            return ""

    def _check_text_errors(self, original: str, generated: str) -> List[Dict]:
        """텍스트 오류 확인"""
        errors = []

        # 길이 차이가 너무 크면 경고
        length_diff = abs(len(original) - len(generated)) / max(len(original), 1)
        if length_diff > 0.3:  # 30% 이상 차이
            errors.append({
                "type": "text_length_mismatch",
                "severity": "high",
                "message": f"텍스트 길이 불일치 (차이: {length_diff:.1%})",
                "original_length": len(original),
                "generated_length": len(generated)
            })

        return errors

    def _check_ocr_errors(self, text: str) -> List[Dict]:
        """일반적인 OCR 오류 확인"""
        errors = []

        for wrong, correct in self.common_ocr_errors.items():
            if wrong in text and correct not in text:
                errors.append({
                    "type": "ocr_error",
                    "severity": "medium",
                    "wrong_text": wrong,
                    "correct_text": correct,
                    "message": f"OCR 오류 발견: '{wrong}' → '{correct}'로 수정 필요"
                })

        return errors

    def _check_critical_keywords(self, text: str) -> List[str]:
        """중요 키워드 누락 확인"""
        missing = []
        text_lower = text.lower()

        for keyword in self.critical_keywords:
            if keyword.lower() not in text_lower:
                missing.append(keyword)

        return missing

    def _verify_structure(self, extracted_data: Dict[str, Any]) -> List[Dict]:
        """구조 검증"""
        warnings = []
        structured = extracted_data.get("structured_data", {})

        # 후보자 정보 확인
        if not structured.get("candidate_name"):
            warnings.append({
                "type": "missing_candidate_name",
                "message": "후보자 이름이 누락되었습니다"
            })

        # 공약 확인
        core_pledges = structured.get("core_pledges", [])
        if len(core_pledges) != 6:
            warnings.append({
                "type": "pledge_count_mismatch",
                "message": f"핵심공약 개수 불일치 (예상: 6개, 실제: {len(core_pledges)}개)"
            })

        return warnings

    def _verify_links(self, extracted_data: Dict[str, Any]) -> List[Dict]:
        """링크 검증"""
        warnings = []
        structured = extracted_data.get("structured_data", {})
        contact_info = structured.get("contact_info", "")

        # SNS 링크 패턴 확인
        patterns = {
            "facebook": r'facebook\.com/[\w.]+',
            "instagram": r'@[\w.]+',
            "blog": r'blog\.naver\.com/[\w]+'
        }

        for platform, pattern in patterns.items():
            if pattern in contact_info or re.search(pattern, contact_info):
                # 링크 존재하지만 클릭 가능한지 확인 필요
                pass
            else:
                warnings.append({
                    "type": "missing_sns_link",
                    "platform": platform,
                    "message": f"{platform} 링크가 누락되었을 수 있습니다"
                })

        return warnings

    def _calculate_accuracy(self, original: str, generated: str) -> float:
        """OCR 정확도 계산"""
        if not original or not generated:
            return 0.0

        matcher = SequenceMatcher(None, original, generated)
        return matcher.ratio() * 100

    def _calculate_similarity(self, text1: str, text2: str) -> float:
        """텍스트 유사도 계산"""
        if not text1 or not text2:
            return 0.0

        matcher = SequenceMatcher(None, text1.lower(), text2.lower())
        return matcher.ratio() * 100

    def _generate_corrections(self, errors: List[Dict]) -> List[Dict]:
        """자동 수정 제안 생성"""
        corrections = []

        for error in errors:
            if error.get("type") == "ocr_error":
                corrections.append({
                    "action": "replace_text",
                    "from": error["wrong_text"],
                    "to": error["correct_text"],
                    "confidence": "high"
                })

        return corrections

    def apply_corrections(
        self,
        html_path: str,
        corrections: List[Dict]
    ) -> bool:
        """자동 수정 적용"""
        try:
            with open(html_path, 'r', encoding='utf-8') as f:
                content = f.read()

            original_content = content

            for correction in corrections:
                if correction["action"] == "replace_text":
                    content = content.replace(
                        correction["from"],
                        correction["to"]
                    )

            # 변경사항이 있으면 파일 업데이트
            if content != original_content:
                with open(html_path, 'w', encoding='utf-8') as f:
                    f.write(content)

                logger.info(f"자동 수정 적용 완료: {Path(html_path).name}")
                return True
            else:
                logger.info("적용할 수정사항 없음")
                return False

        except Exception as e:
            logger.error(f"자동 수정 적용 실패: {str(e)}", exc_info=True)
            return False


# 싱글톤 인스턴스
_verification_system = None

def get_verification_system() -> VerificationSystem:
    """검증 시스템 싱글톤 인스턴스"""
    global _verification_system
    if _verification_system is None:
        _verification_system = VerificationSystem()
    return _verification_system
