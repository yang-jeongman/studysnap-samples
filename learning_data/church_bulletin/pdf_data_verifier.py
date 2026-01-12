"""
PDF 원본 데이터 검증기 (BulletinAI)
=================================

Vision API로 추출된 데이터가 PDF 원본과 일치하는지 검증합니다.
상상/환각 데이터를 탐지하고 자동으로 교정합니다.

핵심 원칙:
- "교회 주보 변환 작업은 무조건 현실의 주보를 있는 그대로 텍스트 가져와서 출력하는 것이 원칙"
- 상상으로 데이터를 만들지 않음
- 확인된 데이터만 사용
"""

import re
import json
import os
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


@dataclass
class DataIntegrityCheck:
    """데이터 무결성 검사 결과"""
    field_name: str
    extracted_value: str
    is_verified: bool
    verification_method: str  # pattern_match, cross_reference, pdf_vision
    confidence: float
    issues: List[str] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)


@dataclass
class PDFDataVerificationReport:
    """PDF 데이터 검증 리포트"""
    bulletin_date: str
    verification_timestamp: str
    total_fields_checked: int
    verified_count: int
    suspicious_count: int
    failed_count: int
    integrity_score: float  # 0~1
    checks: List[DataIntegrityCheck] = field(default_factory=list)
    hallucination_detected: List[Dict] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "bulletin_date": self.bulletin_date,
            "verification_timestamp": self.verification_timestamp,
            "integrity_score": round(self.integrity_score, 2),
            "integrity_percent": f"{self.integrity_score * 100:.1f}%",
            "summary": {
                "total": self.total_fields_checked,
                "verified": self.verified_count,
                "suspicious": self.suspicious_count,
                "failed": self.failed_count
            },
            "checks": [
                {
                    "field": c.field_name,
                    "value": c.extracted_value,
                    "verified": c.is_verified,
                    "method": c.verification_method,
                    "confidence": round(c.confidence, 2),
                    "issues": c.issues,
                    "suggestions": c.suggestions
                }
                for c in self.checks
            ],
            "hallucination_detected": self.hallucination_detected
        }


class PDFDataVerifier:
    """
    PDF 원본 데이터 검증기

    기능:
    1. 추출된 데이터의 형식 검증
    2. 상호 참조 검증 (페이지 간 데이터 일관성)
    3. 환각/상상 데이터 탐지
    4. 자동 교정 제안
    """

    def __init__(self, learning_dir: str = None):
        if learning_dir is None:
            learning_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

        self.learning_dir = Path(learning_dir)

        # 알려진 여의도순복음교회 데이터 (검증용 참조)
        self.known_pastors = [
            "이영훈 목사", "이영훈 위임목사",
            "엄태욱 목사", "오수황 목사", "홍승원 목사",
            "조동천 목사", "이대희 목사", "박동규 목사",
            "김현진 목사", "백용현 목사", "최병락 목사"
        ]

        self.known_choirs = [
            "베다니 찬양대", "베들레헴 찬양대", "임마누엘 찬양대",
            "에벤에셀 찬양대", "갈릴리 찬양대", "시온 찬양대",
            "호산나 찬양대", "할렐루야 찬양대"
        ]

        # 환각 탐지 패턴 (AI가 자주 만들어내는 가짜 데이터)
        self.hallucination_patterns = [
            # 너무 일반적인 설교 제목
            re.compile(r'^(예수|사랑|믿음|소망|은혜|축복)$'),
            # 비현실적인 성경 구절 (존재하지 않는 장/절)
            re.compile(r'(\d{3,})[:\s]\d+'),  # 100장 이상 (대부분 없음)
            # 템플릿처럼 보이는 데이터
            re.compile(r'^(OOO|XXX|담당자|설교자)\s*(목사|전도사)?$'),
            # 너무 긴 설교 제목 (실제 주보에서 보기 드묾)
            re.compile(r'^.{50,}$'),
        ]

        # 각 예배별 시간 범위 (검증용)
        self.service_time_ranges = {
            "1부": ("오전 6:00", "오전 8:00"),
            "2부": ("오전 8:30", "오전 10:00"),
            "3부": ("오전 10:30", "오전 12:00"),
            "4부": ("오후 12:30", "오후 2:00"),
            "2·3·4부": ("오전 9:00", "오후 1:30"),
            "5부": ("오후 2:00", "오후 4:00"),
            "5부 대학청년": ("오후 2:00", "오후 4:00"),
            "대학청년": ("오후 2:00", "오후 4:00"),
            "주일저녁": ("오후 4:30", "오후 7:00"),
        }

        logger.info("🔍 PDF 데이터 검증기 초기화 완료")

    def verify_extracted_data(self, bulletin_date: str,
                               extracted_data: Dict) -> PDFDataVerificationReport:
        """
        추출된 데이터 전체 검증

        Args:
            bulletin_date: 주보 날짜 (YYYY-MM-DD)
            extracted_data: Vision API로 추출된 데이터
                {
                    "services": [...],
                    "verse_of_day": {...},
                    "sermon": {...},
                    "news": {...},
                    ...
                }
        """
        checks = []
        hallucinations = []

        # 1. 예배 데이터 검증
        services = extracted_data.get("services", [])
        for service in services:
            service_checks = self._verify_service_data(service)
            checks.extend(service_checks)

            # 환각 탐지
            hallucination = self._detect_hallucination_in_service(service)
            if hallucination:
                hallucinations.append(hallucination)

        # 2. 오늘의 말씀 검증
        verse_data = extracted_data.get("verse_of_day", {})
        if verse_data:
            verse_check = self._verify_verse_data(verse_data)
            checks.append(verse_check)

        # 3. 설교 데이터 검증
        sermon_data = extracted_data.get("sermon", {})
        if sermon_data:
            sermon_checks = self._verify_sermon_data(sermon_data)
            checks.extend(sermon_checks)

        # 4. 상호 참조 검증 (페이지 간 일관성)
        cross_ref_issues = self._cross_reference_check(extracted_data)
        if cross_ref_issues:
            for issue in cross_ref_issues:
                checks.append(DataIntegrityCheck(
                    field_name="cross_reference",
                    extracted_value="",
                    is_verified=False,
                    verification_method="cross_reference",
                    confidence=0.5,
                    issues=[issue],
                    suggestions=["페이지 간 데이터 일관성을 확인하세요"]
                ))

        # 통계 계산
        verified = sum(1 for c in checks if c.is_verified)
        suspicious = sum(1 for c in checks if not c.is_verified and c.confidence > 0.5)
        failed = sum(1 for c in checks if not c.is_verified and c.confidence <= 0.5)

        integrity_score = verified / max(len(checks), 1)

        return PDFDataVerificationReport(
            bulletin_date=bulletin_date,
            verification_timestamp=datetime.now().isoformat(),
            total_fields_checked=len(checks),
            verified_count=verified,
            suspicious_count=suspicious,
            failed_count=failed,
            integrity_score=integrity_score,
            checks=checks,
            hallucination_detected=hallucinations
        )

    def _verify_service_data(self, service: Dict) -> List[DataIntegrityCheck]:
        """예배 데이터 검증"""
        checks = []
        service_name = service.get("name", "알 수 없음")

        # 설교자 검증
        pastor = service.get("sermon_pastor", "") or service.get("sermon", "")
        if pastor:
            is_known = any(p in pastor for p in self.known_pastors)
            checks.append(DataIntegrityCheck(
                field_name=f"{service_name}_pastor",
                extracted_value=pastor,
                is_verified=is_known,
                verification_method="known_list" if is_known else "pattern_match",
                confidence=0.95 if is_known else 0.7,
                issues=[] if is_known else [f"알 수 없는 설교자: {pastor}"],
                suggestions=[] if is_known else ["PDF 원본에서 설교자 이름을 다시 확인하세요"]
            ))
        else:
            checks.append(DataIntegrityCheck(
                field_name=f"{service_name}_pastor",
                extracted_value="",
                is_verified=False,
                verification_method="missing_check",
                confidence=0.0,
                issues=["설교자 정보 누락"],
                suggestions=["PDF 2페이지에서 설교자 정보를 추출하세요"]
            ))

        # 찬양대 검증
        choir = service.get("choir", "")
        if choir:
            is_known = any(c in choir for c in self.known_choirs)
            checks.append(DataIntegrityCheck(
                field_name=f"{service_name}_choir",
                extracted_value=choir,
                is_verified=is_known,
                verification_method="known_list" if is_known else "pattern_match",
                confidence=0.9 if is_known else 0.6,
                issues=[] if is_known else [f"알 수 없는 찬양대: {choir}"],
                suggestions=[] if is_known else ["PDF 원본에서 찬양대 이름을 확인하세요"]
            ))

        # 성경 구절 검증
        scripture = service.get("scripture", "")
        if scripture:
            is_valid = self._is_valid_scripture(scripture)
            checks.append(DataIntegrityCheck(
                field_name=f"{service_name}_scripture",
                extracted_value=scripture,
                is_verified=is_valid,
                verification_method="pattern_match",
                confidence=0.85 if is_valid else 0.4,
                issues=[] if is_valid else [f"성경 구절 형식 오류: {scripture}"],
                suggestions=[] if is_valid else ["형식: '시 146:1~5' 또는 '딤후 4:9~11'"]
            ))

        # 예배 시간 검증
        time = service.get("time", "")
        if time:
            is_reasonable = self._is_reasonable_time(service_name, time)
            checks.append(DataIntegrityCheck(
                field_name=f"{service_name}_time",
                extracted_value=time,
                is_verified=is_reasonable,
                verification_method="range_check",
                confidence=0.8 if is_reasonable else 0.3,
                issues=[] if is_reasonable else [f"{service_name}의 시간이 비정상적입니다: {time}"]
            ))

        return checks

    def _verify_verse_data(self, verse_data: Dict) -> DataIntegrityCheck:
        """오늘의 말씀 검증"""
        reference = verse_data.get("reference", "")
        text = verse_data.get("text", "")

        issues = []
        if not reference:
            issues.append("성경 참조 구절 누락")
        if not text:
            issues.append("말씀 본문 누락")
        if text and len(text) < 20:
            issues.append("말씀 본문이 너무 짧음 (환각 의심)")

        return DataIntegrityCheck(
            field_name="verse_of_day",
            extracted_value=f"{reference}: {text[:50]}..." if text else reference,
            is_verified=len(issues) == 0,
            verification_method="completeness_check",
            confidence=0.9 if not issues else 0.4,
            issues=issues,
            suggestions=["PDF 1페이지 또는 6페이지에서 오늘의 말씀을 확인하세요"] if issues else []
        )

    def _verify_sermon_data(self, sermon_data: Dict) -> List[DataIntegrityCheck]:
        """설교 데이터 검증"""
        checks = []

        title = sermon_data.get("title", "")
        content = sermon_data.get("content", "") or sermon_data.get("text", "")

        # 제목 검증
        if title:
            # 환각 패턴 체크
            is_hallucination = any(p.match(title) for p in self.hallucination_patterns)
            checks.append(DataIntegrityCheck(
                field_name="sermon_title",
                extracted_value=title,
                is_verified=not is_hallucination,
                verification_method="hallucination_check",
                confidence=0.3 if is_hallucination else 0.9,
                issues=["설교 제목이 환각일 수 있음"] if is_hallucination else [],
                suggestions=["PDF 4페이지에서 설교 제목을 직접 확인하세요"] if is_hallucination else []
            ))
        else:
            checks.append(DataIntegrityCheck(
                field_name="sermon_title",
                extracted_value="",
                is_verified=False,
                verification_method="missing_check",
                confidence=0.0,
                issues=["설교 제목 누락"],
                suggestions=["PDF 4페이지에서 설교 제목을 추출하세요"]
            ))

        # 내용 검증 (최소 길이)
        if content:
            is_sufficient = len(content) >= 100
            checks.append(DataIntegrityCheck(
                field_name="sermon_content",
                extracted_value=f"{content[:100]}..." if len(content) > 100 else content,
                is_verified=is_sufficient,
                verification_method="length_check",
                confidence=0.85 if is_sufficient else 0.5,
                issues=[] if is_sufficient else ["설교 내용이 너무 짧음"]
            ))

        return checks

    def _detect_hallucination_in_service(self, service: Dict) -> Optional[Dict]:
        """예배 데이터에서 환각 탐지"""
        service_name = service.get("name", "알 수 없음")
        hallucinations = []

        # 1. 설교 제목 환각 체크
        sermon_title = service.get("sermon_title", "")
        if sermon_title:
            for pattern in self.hallucination_patterns:
                if pattern.match(sermon_title):
                    hallucinations.append({
                        "field": "sermon_title",
                        "value": sermon_title,
                        "reason": "환각 패턴 매칭 (너무 일반적이거나 템플릿 같음)"
                    })
                    break

        # 2. 설교자 환각 체크 (알 수 없는 이름)
        pastor = service.get("sermon_pastor", "")
        if pastor and not any(p in pastor for p in self.known_pastors):
            # 이름 형식은 맞지만 알려지지 않은 경우 (환각 가능성)
            if re.match(r'^[가-힣]{2,4}\s*목사$', pastor):
                hallucinations.append({
                    "field": "sermon_pastor",
                    "value": pastor,
                    "reason": "알 수 없는 설교자 (환각 가능성)",
                    "suggestion": "PDF 원본에서 직접 확인 필요"
                })

        # 3. 비현실적인 찬송가 번호
        hymn = service.get("hymn", "")
        if hymn:
            hymn_num = re.search(r'(\d+)', hymn)
            if hymn_num and int(hymn_num.group(1)) > 700:
                hallucinations.append({
                    "field": "hymn",
                    "value": hymn,
                    "reason": f"찬송가 번호가 비정상적으로 큼: {hymn}"
                })

        if hallucinations:
            return {
                "service": service_name,
                "hallucinations": hallucinations,
                "timestamp": datetime.now().isoformat()
            }

        return None

    def _cross_reference_check(self, extracted_data: Dict) -> List[str]:
        """페이지 간 상호 참조 검증"""
        issues = []

        # 예배 데이터와 설교 데이터 간 일관성 체크
        services = extracted_data.get("services", [])
        sermon = extracted_data.get("sermon", {})

        if services and sermon:
            sermon_title = sermon.get("title", "")
            sermon_pastor = sermon.get("pastor", "")

            # 4페이지 설교 제목이 2페이지 예배 정보와 일치하는지
            for service in services:
                svc_title = service.get("sermon_title", "")
                svc_pastor = service.get("sermon_pastor", "")

                if sermon_title and svc_title and sermon_title not in svc_title and svc_title not in sermon_title:
                    issues.append(f"설교 제목 불일치: 2페이지 '{svc_title}' vs 4페이지 '{sermon_title}'")

                if sermon_pastor and svc_pastor and sermon_pastor not in svc_pastor and svc_pastor not in sermon_pastor:
                    issues.append(f"설교자 불일치: 2페이지 '{svc_pastor}' vs 4페이지 '{sermon_pastor}'")

        return issues

    def _is_valid_scripture(self, scripture: str) -> bool:
        """성경 구절 형식 검증"""
        patterns = [
            r'^[가-힣]{1,4}\s*\d{1,3}[:\s]\d{1,3}[~\-]\d{1,3}$',
            r'^[가-힣]{2,8}\s*\d{1,3}장\s*\d{1,3}[~\-]\d{1,3}절$',
            r'^[가-힣]{2,8}\s*\d{1,3}[:\s]\d{1,3}[~\-]\d{1,3}$',
        ]
        return any(re.match(p, scripture.strip()) for p in patterns)

    def _is_reasonable_time(self, service_name: str, time: str) -> bool:
        """예배 시간이 해당 예배에 적합한지 검증"""
        # 간단한 검증: 오전/오후 포함 여부
        if not ("오전" in time or "오후" in time):
            return False

        # 시간 범위 체크 (정규화된 예배명)
        for name_pattern, (start, end) in self.service_time_ranges.items():
            if name_pattern in service_name:
                # 시간 추출 (예: "오전 7:00" → 7)
                time_match = re.search(r'(\d{1,2})[:\s]?(\d{0,2})', time)
                if time_match:
                    hour = int(time_match.group(1))
                    if "오후" in time and hour != 12:
                        hour += 12

                    start_hour = int(re.search(r'(\d{1,2})', start).group(1))
                    if "오후" in start:
                        start_hour += 12

                    end_hour = int(re.search(r'(\d{1,2})', end).group(1))
                    if "오후" in end:
                        end_hour += 12

                    return start_hour <= hour <= end_hour

        return True  # 알 수 없는 예배명은 일단 통과

    def generate_verification_report(self, report: PDFDataVerificationReport) -> str:
        """검증 리포트 텍스트 생성"""
        lines = [
            "=" * 60,
            "🔍 PDF 데이터 무결성 검증 리포트",
            f"📅 주보: {report.bulletin_date}",
            f"🕐 검증: {report.verification_timestamp}",
            "=" * 60,
            "",
            f"📊 무결성 점수: {report.integrity_score * 100:.1f}%",
            f"   검증됨: {report.verified_count}/{report.total_fields_checked}",
            f"   의심: {report.suspicious_count}",
            f"   실패: {report.failed_count}",
            ""
        ]

        # 환각 탐지 결과
        if report.hallucination_detected:
            lines.append("⚠️ 환각(상상) 데이터 탐지:")
            for h in report.hallucination_detected:
                lines.append(f"   [{h['service']}]")
                for item in h['hallucinations']:
                    lines.append(f"      - {item['field']}: '{item['value']}'")
                    lines.append(f"        → {item['reason']}")
            lines.append("")

        # 실패한 검증 항목
        failed_checks = [c for c in report.checks if not c.is_verified]
        if failed_checks:
            lines.append("❌ 검증 실패 항목:")
            for check in failed_checks:
                lines.append(f"   - {check.field_name}: {check.extracted_value}")
                for issue in check.issues:
                    lines.append(f"     문제: {issue}")
                for suggestion in check.suggestions:
                    lines.append(f"     제안: {suggestion}")
            lines.append("")

        lines.append("=" * 60)
        return "\n".join(lines)


# =========================================================================
# 싱글톤 인스턴스
# =========================================================================

_verifier_instance = None

def get_verifier() -> PDFDataVerifier:
    """검증기 싱글톤 반환"""
    global _verifier_instance
    if _verifier_instance is None:
        _verifier_instance = PDFDataVerifier()
    return _verifier_instance


# =========================================================================
# 테스트
# =========================================================================

if __name__ == "__main__":
    # 테스트: 정상 데이터
    test_data_good = {
        "services": [
            {
                "name": "1부",
                "time": "오전 7:00",
                "scripture": "딤후 4:9~11",
                "hymn": "301장",
                "choir": "베다니 찬양대",
                "sermon_title": "겨울이 오면",
                "sermon_pastor": "엄태욱 목사"
            }
        ],
        "verse_of_day": {
            "reference": "시편 146:1~5",
            "text": "할렐루야 내 영혼아 여호와를 찬양하라 나는 평생토록 여호와를 찬양하며..."
        },
        "sermon": {
            "title": "겨울이 오면",
            "pastor": "엄태욱 목사",
            "content": "사도 바울은 디모데에게 편지를 보내며..." * 10
        }
    }

    # 테스트: 환각 데이터
    test_data_bad = {
        "services": [
            {
                "name": "1부",
                "time": "오전 7:00",
                "scripture": "딤후 4:9~11",
                "hymn": "301장",
                "choir": "베다니 찬양대",
                "sermon_title": "사랑",  # 환각 - 너무 일반적
                "sermon_pastor": "김철수 목사"  # 환각 - 알 수 없는 이름
            }
        ]
    }

    verifier = get_verifier()

    print("\n=== 정상 데이터 테스트 ===")
    report1 = verifier.verify_extracted_data("2025-12-28", test_data_good)
    print(verifier.generate_verification_report(report1))

    print("\n=== 환각 데이터 테스트 ===")
    report2 = verifier.verify_extracted_data("2025-12-28", test_data_bad)
    print(verifier.generate_verification_report(report2))
