"""
NewsletterAI OCR 검증 및 자동 교정 시스템
- 텍스트 오류 자동 검출
- 한글 맞춤법 기반 교정
- 학습 데이터 축적 및 개선

Powered by NewsletterAI
"""

import re
import json
import logging
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class OCRValidator:
    """OCR 텍스트 검증 및 교정"""

    # 자주 발생하는 OCR 오류 패턴 (원본 -> 교정)
    COMMON_OCR_ERRORS = {
        # 비슷한 글자 혼동
        "거지고": "커지고",
        "이자행": "이점을",
        "지물으로": "자동으로",
        "운행 할교": "문을 열고",
        "충전 관리가": "청결 관리까지",
        "시작하는 확신": "사용자는 항시",
        "뽑 충이면": "탈 준비만",
        "직접 앞이": "걱정 없이",
        "끌리하게": "편리하게",
        "추행거리가": "주행거리가",
        "시군에까지도": "주말여행에도",
        "출전 요금": "충전 요금",
        "유료 또한": "요금 또한",
        "디자인 서비저가": "다양한 선택지가",
        "대이할": "대여할",
        "기받배나": "기관이나",
        "개인차과": "깨끗하고",
        "성비 서비스를": "정비된 차량을",
        "교통 출장과": "교통 혼잡과",
        "시민봉사기자": "시민홍보기자",
        # 2025-01-09 추가 패턴
        "통계 10월": "오는 10월",
        "통계 11월": "오는 11월",
        "통계 12월": "오는 12월",
        "북원아니": "북풍이나",
        "관미를": "한파를",
        "못해 못해": "잡아 잡아",
        "새 나가는": "새어 나가는",
        "카쿠니티": "커뮤니티",
        "성동에": "성능에",
        # 2025-01-09 2차 추가 패턴
        "시정 지향주치를": "시청 지하주차장을",
        "온영 거점": "운영 거점",
        "목원이나 전면을": "뙤약볕이나 한파를",
        "목원 편마을": "목련 삼거리 등 15개소에",
        "체공하고": "제공하고",
        "온열전싯": "온열의자 등",
        "우무실": "무선",
        "치동상선충기": "자동심장충격기",
        "버스정보안내을": "버스정보안내기를",
        "성북에": "성능에",
        "에너지와 최소화": "에너지량을 최소화",
        # 일반적인 OCR 오류
        "있 다": "있다",
        "없 다": "없다",
        "하 다": "하다",
        "되 다": "되다",
    }

    # 한글 맞춤법 검사용 패턴
    SPELLING_PATTERNS = [
        # 띄어쓰기 오류
        (r'([가-힣])하 고', r'\1하고'),
        (r'([가-힣])할 수', r'\1할 수'),
        (r'([가-힣])를 통해', r'\1을 통해'),
        # 조사 오류
        (r'([가-힣])이 있다', r'\1이 있다'),
    ]

    def __init__(self, learning_data_path: str = None):
        self.learning_data_path = Path(learning_data_path) if learning_data_path else Path(__file__).parent
        self.error_log_path = self.learning_data_path / "ocr_errors.json"
        self.corrections_path = self.learning_data_path / "ocr_corrections.json"

        # 학습된 교정 데이터 로드
        self.learned_corrections = self._load_corrections()

    def _load_corrections(self) -> Dict[str, str]:
        """저장된 교정 데이터 로드"""
        corrections = dict(self.COMMON_OCR_ERRORS)

        if self.corrections_path.exists():
            try:
                with open(self.corrections_path, 'r', encoding='utf-8') as f:
                    learned = json.load(f)
                    corrections.update(learned)
            except Exception as e:
                logger.warning(f"교정 데이터 로드 실패: {e}")

        return corrections

    def _save_corrections(self):
        """교정 데이터 저장"""
        try:
            with open(self.corrections_path, 'w', encoding='utf-8') as f:
                json.dump(self.learned_corrections, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"교정 데이터 저장 실패: {e}")

    def validate_text(self, text: str) -> Dict:
        """
        텍스트 검증 및 오류 검출

        Returns:
            {
                "is_valid": bool,
                "errors": [{"type": str, "original": str, "position": int}],
                "confidence": float (0-1)
            }
        """
        errors = []
        confidence = 1.0

        # 1. 알려진 OCR 오류 패턴 검출
        for wrong, correct in self.learned_corrections.items():
            if wrong in text:
                errors.append({
                    "type": "known_ocr_error",
                    "original": wrong,
                    "suggested": correct,
                    "position": text.find(wrong)
                })
                confidence -= 0.1

        # 2. 불확실한 글자 ([?]) 검출
        uncertain_matches = re.findall(r'\[\?\]', text)
        if uncertain_matches:
            errors.append({
                "type": "uncertain_text",
                "count": len(uncertain_matches),
                "positions": [m.start() for m in re.finditer(r'\[\?\]', text)]
            })
            confidence -= 0.15 * len(uncertain_matches)

        # 3. 비정상적인 문자 조합 검출
        abnormal_patterns = [
            r'[가-힣]{1}[a-zA-Z]{1}[가-힣]{1}',  # 한글-영어-한글 혼용
            r'\d{1}[가-힣]{1}\d{1}',  # 숫자-한글-숫자 혼용
        ]
        for pattern in abnormal_patterns:
            matches = re.findall(pattern, text)
            if matches:
                errors.append({
                    "type": "abnormal_pattern",
                    "matches": matches
                })
                confidence -= 0.05 * len(matches)

        # 4. 문장 완결성 검사
        sentences = re.split(r'[.!?。]', text)
        incomplete_count = sum(1 for s in sentences if s.strip() and len(s.strip()) < 5)
        if incomplete_count > 3:
            errors.append({
                "type": "incomplete_sentences",
                "count": incomplete_count
            })
            confidence -= 0.1

        confidence = max(0, min(1, confidence))

        return {
            "is_valid": len(errors) == 0,
            "errors": errors,
            "confidence": round(confidence, 2),
            "text_length": len(text)
        }

    def auto_correct(self, text: str) -> Tuple[str, List[Dict]]:
        """
        자동 교정 수행

        Returns:
            (교정된 텍스트, 교정 내역)
        """
        corrected = text
        corrections_made = []

        # 알려진 OCR 오류 교정
        for wrong, correct in self.learned_corrections.items():
            if wrong in corrected:
                corrected = corrected.replace(wrong, correct)
                corrections_made.append({
                    "type": "ocr_correction",
                    "original": wrong,
                    "corrected": correct
                })

        # 맞춤법 패턴 교정
        for pattern, replacement in self.SPELLING_PATTERNS:
            new_text = re.sub(pattern, replacement, corrected)
            if new_text != corrected:
                corrections_made.append({
                    "type": "spelling_correction",
                    "pattern": pattern
                })
                corrected = new_text

        return corrected, corrections_made

    def learn_correction(self, wrong: str, correct: str, source: str = "manual"):
        """
        새로운 교정 패턴 학습

        Args:
            wrong: 잘못된 텍스트
            correct: 올바른 텍스트
            source: 교정 출처 (manual, user, auto)
        """
        if wrong and correct and wrong != correct:
            self.learned_corrections[wrong] = correct
            self._save_corrections()

            # 학습 로그 저장
            self._log_learning(wrong, correct, source)

            logger.info(f"새 교정 패턴 학습: '{wrong}' -> '{correct}'")

    def _log_learning(self, wrong: str, correct: str, source: str):
        """학습 로그 저장"""
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "wrong": wrong,
            "correct": correct,
            "source": source
        }

        log_path = self.learning_data_path / "learning_log.json"
        logs = []

        if log_path.exists():
            try:
                with open(log_path, 'r', encoding='utf-8') as f:
                    logs = json.load(f)
            except:
                logs = []

        logs.append(log_entry)

        # 최근 1000개만 유지
        logs = logs[-1000:]

        with open(log_path, 'w', encoding='utf-8') as f:
            json.dump(logs, f, ensure_ascii=False, indent=2)

    def get_quality_score(self, text: str) -> float:
        """
        텍스트 품질 점수 계산 (0-100)
        """
        validation = self.validate_text(text)
        base_score = validation["confidence"] * 100

        # 텍스트 길이 보너스 (너무 짧거나 길면 감점)
        length = len(text)
        if length < 50:
            base_score -= 10
        elif length > 5000:
            base_score -= 5

        # 오류 개수에 따른 감점
        error_count = len(validation["errors"])
        base_score -= error_count * 5

        return max(0, min(100, round(base_score, 1)))


class NewsletterQualityChecker:
    """소식지 전체 품질 검사"""

    def __init__(self):
        self.validator = OCRValidator()
        self.quality_threshold = 70  # 최소 품질 점수

    def check_page_quality(self, page_data: Dict) -> Dict:
        """
        페이지 데이터 품질 검사

        Returns:
            {
                "page_num": int,
                "quality_score": float,
                "needs_reprocess": bool,
                "issues": []
            }
        """
        issues = []
        scores = []

        # 기사 텍스트 검사
        for article in page_data.get("articles", []):
            content = article.get("summary", "") or article.get("content", "")
            if content:
                score = self.validator.get_quality_score(content)
                scores.append(score)

                if score < self.quality_threshold:
                    issues.append({
                        "type": "low_quality_article",
                        "title": article.get("title", "제목 없음"),
                        "score": score
                    })

        # 현장취재 텍스트 검사
        for report in page_data.get("field_reports", []):
            content = report.get("content", "")
            if content:
                score = self.validator.get_quality_score(content)
                scores.append(score)

                if score < self.quality_threshold:
                    issues.append({
                        "type": "low_quality_report",
                        "title": report.get("title", "제목 없음"),
                        "score": score
                    })

        avg_score = sum(scores) / len(scores) if scores else 100

        return {
            "page_num": page_data.get("page_num", 0),
            "quality_score": round(avg_score, 1),
            "needs_reprocess": avg_score < self.quality_threshold,
            "issues": issues,
            "article_count": len(page_data.get("articles", [])),
            "report_count": len(page_data.get("field_reports", []))
        }

    def check_newsletter_quality(self, all_pages_data: List[Dict]) -> Dict:
        """
        전체 소식지 품질 검사

        Returns:
            {
                "overall_score": float,
                "pages_needing_reprocess": [int],
                "page_reports": [],
                "recommendation": str
            }
        """
        page_reports = []
        pages_needing_reprocess = []

        for page_data in all_pages_data:
            structured = page_data.get("structured", page_data)
            report = self.check_page_quality(structured)
            page_reports.append(report)

            if report["needs_reprocess"]:
                pages_needing_reprocess.append(report["page_num"])

        # 전체 점수 계산
        scores = [r["quality_score"] for r in page_reports]
        overall_score = sum(scores) / len(scores) if scores else 0

        # 권장 사항 생성
        if overall_score >= 90:
            recommendation = "품질 우수 - 검수 후 배포 가능"
        elif overall_score >= 70:
            recommendation = "품질 양호 - 일부 페이지 수동 검토 권장"
        elif overall_score >= 50:
            recommendation = "품질 미흡 - 재변환 또는 수동 교정 필요"
        else:
            recommendation = "품질 불량 - 원본 PDF 확인 및 전체 재변환 필요"

        return {
            "overall_score": round(overall_score, 1),
            "pages_needing_reprocess": pages_needing_reprocess,
            "page_reports": page_reports,
            "recommendation": recommendation,
            "total_pages": len(all_pages_data)
        }


# 테스트
if __name__ == "__main__":
    validator = OCRValidator()

    # 테스트 텍스트 (OCR 오류 포함)
    test_text = """편리한은 거지고 탄소 배출은 줄이는 '전기차 카셰어링'
    '전기차 카셰어링'을 직접 이용해 보니 스마트한 공유경제가 가져다 전기차의 이자행 피부로 느낄 수 있었다."""

    # 검증
    result = validator.validate_text(test_text)
    print("검증 결과:", json.dumps(result, ensure_ascii=False, indent=2))

    # 자동 교정
    corrected, corrections = validator.auto_correct(test_text)
    print("\n교정된 텍스트:", corrected)
    print("교정 내역:", corrections)

    # 품질 점수
    score = validator.get_quality_score(test_text)
    print(f"\n품질 점수: {score}/100")
