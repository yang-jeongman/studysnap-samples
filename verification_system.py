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


class ChurchBulletinVerifier:
    """교회 주보 전용 검증 시스템 - 원본 PDF와 결과물 비교"""

    def __init__(self):
        # 교회 주보에서 자주 발생하는 OCR 오류 패턴
        self.common_ocr_errors = {
            "예배": "예배",
            "찬송": "찬송",
            "기도": "기도",
            "말씀": "말씀",
            "헌금": "헌금",
            "축도": "축도",
            "성경봉독": "성경봉독",
        }

        # 교회별 중요 키워드
        self.church_keywords = {
            "명성교회": {
                "required": ["김삼환", "김하나", "예배", "찬송"],
                "forbidden": ["오늘의 말씀"],  # 명성교회에는 이 섹션이 없음
            }
        }

    def verify_church_bulletin(
        self,
        original_pdf_path: str,
        generated_html_path: str,
        extracted_data: Dict[str, Any],
        church_name: str = ""
    ) -> Dict[str, Any]:
        """
        교회 주보 변환 결과 검증

        Args:
            original_pdf_path: 원본 PDF 파일 경로
            generated_html_path: 생성된 HTML 파일 경로
            extracted_data: OCR로 추출된 데이터
            church_name: 교회명

        Returns:
            검증 결과 딕셔너리
        """
        logger.info(f"교회 주보 검증 시작: {Path(original_pdf_path).name}")

        result = {
            "original_file": Path(original_pdf_path).name,
            "generated_file": Path(generated_html_path).name,
            "church_name": church_name,
            "status": "pending",
            "errors": [],
            "warnings": [],
            "info": [],
            "statistics": {},
            "comparison": {
                "missing_in_html": [],  # PDF에는 있지만 HTML에 없는 내용
                "extra_in_html": [],     # PDF에는 없지만 HTML에 추가된 내용 (환각)
                "mismatched": []         # 불일치 내용
            }
        }

        try:
            # 1. 원본 PDF 텍스트 추출
            original_text = self._extract_pdf_text(original_pdf_path)
            if not original_text:
                original_text = self._get_text_from_extracted_data(extracted_data)

            # 2. 생성된 HTML에서 텍스트 추출
            html_text = self._extract_html_text(generated_html_path)

            # 3. 핵심 정보 비교
            comparison = self._compare_key_information(
                original_text, html_text, church_name
            )
            result["comparison"] = comparison

            # 4. 교회별 특수 검증
            church_specific = self._verify_church_specific(
                html_text, church_name
            )
            result["errors"].extend(church_specific.get("errors", []))
            result["warnings"].extend(church_specific.get("warnings", []))

            # 5. 환각(Hallucination) 검사 - HTML에만 있고 PDF에 없는 내용
            hallucinations = self._check_hallucinations(original_text, html_text)
            if hallucinations:
                result["errors"].extend(hallucinations)

            # 6. 누락 검사 - PDF에 있지만 HTML에 없는 중요 내용
            missing = self._check_missing_content(original_text, html_text, church_name)
            if missing:
                result["warnings"].extend(missing)

            # 7. 통계 계산
            result["statistics"] = {
                "original_length": len(original_text),
                "html_length": len(html_text),
                "similarity_score": self._calculate_similarity(original_text, html_text),
                "total_errors": len(result["errors"]),
                "total_warnings": len(result["warnings"]),
                "hallucination_count": len([e for e in result["errors"] if e.get("type") == "hallucination"]),
                "missing_count": len([w for w in result["warnings"] if w.get("type") == "missing_content"])
            }

            # 8. 최종 상태 결정
            if len(result["errors"]) == 0 and len(result["warnings"]) <= 2:
                result["status"] = "passed"
                result["info"].append("✅ 검증 통과! 원본과 일치합니다.")
            elif len(result["errors"]) == 0:
                result["status"] = "warning"
                result["info"].append("⚠️ 경미한 경고가 있지만 사용 가능합니다.")
            else:
                result["status"] = "failed"
                result["info"].append("❌ 오류 발견! 수동 검토가 필요합니다.")

            logger.info(f"교회 주보 검증 완료: {result['status']} "
                       f"(오류: {result['statistics']['total_errors']}, "
                       f"경고: {result['statistics']['total_warnings']})")

            return result

        except Exception as e:
            logger.error(f"교회 주보 검증 오류: {str(e)}", exc_info=True)
            result["status"] = "error"
            result["errors"].append({
                "type": "system_error",
                "message": f"검증 시스템 오류: {str(e)}"
            })
            return result

    def _extract_pdf_text(self, pdf_path: str) -> str:
        """PDF에서 텍스트 추출"""
        try:
            import fitz
            doc = fitz.open(pdf_path)
            text = ""
            for page in doc:
                text += page.get_text() + "\n"
            doc.close()
            return text.strip()
        except Exception as e:
            logger.warning(f"PDF 텍스트 추출 실패: {e}")
            return ""

    def _get_text_from_extracted_data(self, extracted_data: Dict) -> str:
        """추출된 데이터에서 텍스트 가져오기"""
        texts = []
        for page in extracted_data.get("pages", []):
            texts.append(page.get("text", ""))
        return "\n".join(texts)

    def _extract_html_text(self, html_path: str) -> str:
        """HTML에서 텍스트 추출 (태그 제거)"""
        try:
            with open(html_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # script, style 태그 제거
            content = re.sub(r'<script[^>]*>.*?</script>', '', content, flags=re.DOTALL)
            content = re.sub(r'<style[^>]*>.*?</style>', '', content, flags=re.DOTALL)
            # HTML 태그 제거
            content = re.sub(r'<[^>]+>', ' ', content)
            # 연속 공백 정리
            content = re.sub(r'\s+', ' ', content).strip()

            return content
        except Exception as e:
            logger.error(f"HTML 텍스트 추출 실패: {e}")
            return ""

    def _compare_key_information(
        self,
        original: str,
        html: str,
        church_name: str
    ) -> Dict[str, List]:
        """핵심 정보 비교"""
        comparison = {
            "missing_in_html": [],
            "extra_in_html": [],
            "mismatched": []
        }

        # 주요 추출 대상 패턴
        patterns = {
            "날짜": r'\d{4}년\s*\d{1,2}월\s*\d{1,2}일',
            "성경구절": r'[가-힣]+\s*\d+[:\s]*\d+[-~\d]*',
            "찬송가": r'찬송가?\s*\d+장',
            "시간": r'\d{1,2}[:\s]*\d{2}',
        }

        for name, pattern in patterns.items():
            original_matches = set(re.findall(pattern, original))
            html_matches = set(re.findall(pattern, html))

            # 원본에만 있는 것 (누락)
            missing = original_matches - html_matches
            if missing:
                comparison["missing_in_html"].append({
                    "type": name,
                    "values": list(missing)
                })

            # HTML에만 있는 것 (추가됨 - 주의 필요)
            extra = html_matches - original_matches
            if extra:
                comparison["extra_in_html"].append({
                    "type": name,
                    "values": list(extra)
                })

        return comparison

    def _verify_church_specific(self, html_text: str, church_name: str) -> Dict:
        """교회별 특수 검증"""
        result = {"errors": [], "warnings": []}

        if church_name not in self.church_keywords:
            return result

        config = self.church_keywords[church_name]

        # 필수 키워드 확인
        for keyword in config.get("required", []):
            if keyword not in html_text:
                result["warnings"].append({
                    "type": "missing_required_keyword",
                    "keyword": keyword,
                    "message": f"필수 키워드 '{keyword}'가 결과물에 없습니다"
                })

        # 금지 키워드 확인 (해당 교회에 없어야 할 내용)
        for keyword in config.get("forbidden", []):
            if keyword in html_text:
                result["errors"].append({
                    "type": "forbidden_content",
                    "keyword": keyword,
                    "message": f"'{keyword}'는 {church_name}에 없어야 할 내용입니다"
                })

        return result

    def _check_hallucinations(self, original: str, html: str) -> List[Dict]:
        """환각(Hallucination) 검사 - HTML에만 있는 의심스러운 내용"""
        errors = []

        # 원본에 없는 목사 이름이 HTML에 있는지 검사
        # 주요 패턴: "OOO 목사", "OOO 전도사" 등
        html_names = set(re.findall(r'([가-힣]{2,4})\s*(?:목사|전도사|장로|권사)', html))
        original_names = set(re.findall(r'([가-힣]{2,4})\s*(?:목사|전도사|장로|권사)', original))

        hallucinated_names = html_names - original_names
        for name in hallucinated_names:
            # 프리셋에서 온 이름은 제외 (김삼환, 김하나 등)
            if name not in ["김삼환", "김하나"]:
                errors.append({
                    "type": "hallucination",
                    "severity": "high",
                    "content": f"{name}",
                    "message": f"원본에 없는 이름 '{name}'이(가) HTML에 있습니다 - 환각 의심"
                })

        return errors

    def _check_missing_content(
        self,
        original: str,
        html: str,
        church_name: str
    ) -> List[Dict]:
        """누락된 중요 내용 검사"""
        warnings = []

        # 원본의 주요 숫자/시간 정보가 HTML에 있는지 확인
        original_times = set(re.findall(r'(\d{1,2}:\d{2})', original))
        html_times = set(re.findall(r'(\d{1,2}:\d{2})', html))

        missing_times = original_times - html_times
        if missing_times:
            warnings.append({
                "type": "missing_content",
                "category": "시간정보",
                "missing": list(missing_times),
                "message": f"원본의 시간 정보 {missing_times}가 누락됨"
            })

        return warnings

    def _calculate_similarity(self, text1: str, text2: str) -> float:
        """텍스트 유사도 계산"""
        if not text1 or not text2:
            return 0.0

        # 공백, 특수문자 정규화
        t1 = re.sub(r'\s+', '', text1.lower())
        t2 = re.sub(r'\s+', '', text2.lower())

        matcher = SequenceMatcher(None, t1, t2)
        return round(matcher.ratio() * 100, 2)

    def generate_report(self, result: Dict) -> str:
        """검증 결과 리포트 생성"""
        lines = [
            "=" * 60,
            "📋 교회 주보 검증 리포트",
            "=" * 60,
            f"교회: {result.get('church_name', 'N/A')}",
            f"원본: {result.get('original_file', 'N/A')}",
            f"결과: {result.get('generated_file', 'N/A')}",
            f"상태: {result.get('status', 'N/A').upper()}",
            "",
            "📊 통계:",
            f"  - 유사도: {result.get('statistics', {}).get('similarity_score', 0)}%",
            f"  - 오류: {result.get('statistics', {}).get('total_errors', 0)}개",
            f"  - 경고: {result.get('statistics', {}).get('total_warnings', 0)}개",
            f"  - 환각: {result.get('statistics', {}).get('hallucination_count', 0)}개",
            f"  - 누락: {result.get('statistics', {}).get('missing_count', 0)}개",
        ]

        if result.get("errors"):
            lines.append("")
            lines.append("❌ 오류:")
            for err in result["errors"]:
                lines.append(f"  - [{err.get('type')}] {err.get('message')}")

        if result.get("warnings"):
            lines.append("")
            lines.append("⚠️ 경고:")
            for warn in result["warnings"]:
                lines.append(f"  - [{warn.get('type')}] {warn.get('message')}")

        if result.get("info"):
            lines.append("")
            for info in result["info"]:
                lines.append(info)

        lines.append("=" * 60)
        return "\n".join(lines)


# 교회 주보 검증 싱글톤
_church_verifier = None

def get_church_bulletin_verifier() -> ChurchBulletinVerifier:
    """교회 주보 검증 시스템 싱글톤"""
    global _church_verifier
    if _church_verifier is None:
        _church_verifier = ChurchBulletinVerifier()
    return _church_verifier
