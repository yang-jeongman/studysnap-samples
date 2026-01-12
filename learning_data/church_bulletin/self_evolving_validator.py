"""
자가 진화형 교회 주보 검증 시스템 (BulletinAI / 주보지기)
===============================================

PDF 원본 데이터와 추출된 데이터를 비교하여 자동으로 오류를 탐지하고 교정합니다.
수정 결과는 자동으로 learned_rules.json에 저장되어 시스템이 스스로 진화합니다.

핵심 원칙:
1. 상상 금지 - 모든 데이터는 PDF 원본에서 추출
2. 자동 검증 - 패턴 기반 데이터 무결성 검사
3. 자가 학습 - 오류 패턴을 기록하고 다음 변환에 반영
"""

import re
import json
import os
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field, asdict
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


# =========================================================================
# 데이터 패턴 정의 (여의도순복음교회 주보 기준)
# =========================================================================

@dataclass
class FGFCDataPattern:
    """여의도순복음교회 데이터 패턴"""

    # 예배 이름 패턴
    SERVICE_NAMES = [
        "1부", "2부", "3부", "4부", "5부",
        "2·3·4부", "2.3.4부", "대학청년", "주일저녁",
        "5부 대학청년", "청년예배"
    ]

    # 설교자 패턴: "OOO 목사" 또는 "OOO 위임목사"
    PASTOR_PATTERN = re.compile(r'^[가-힣]{2,4}\s*(목사|위임목사|담임목사|원로목사|전도사)$')

    # 성경 구절 패턴
    SCRIPTURE_PATTERNS = [
        # 약어: 딤후 4:9~11, 시 146:1~5, 고전 9:24~27, 히 2:1~4
        re.compile(r'^[가-힣]{1,4}\s*\d{1,3}[:\s]\d{1,3}[~\-]\d{1,3}$'),
        # 전체: 디모데후서 4장 9~11절
        re.compile(r'^[가-힣]{2,8}\s*\d{1,3}장\s*\d{1,3}[~\-]\d{1,3}절$'),
        # 복합: 시편 146:1~5
        re.compile(r'^[가-힣]{2,8}\s*\d{1,3}[:\s]\d{1,3}[~\-]\d{1,3}$'),
    ]

    # 찬송가 패턴: "301장", "21장", "105장"
    HYMN_PATTERN = re.compile(r'^\d{1,3}장(\s*\d{1,3}절)?$')

    # 찬양대 패턴
    CHOIR_NAMES = [
        "베다니 찬양대", "베들레헴 찬양대", "임마누엘 찬양대",
        "에벤에셀 찬양대", "갈릴리 찬양대", "시온 찬양대",
        "호산나 찬양대", "할렐루야 찬양대"
    ]

    # 예배 시간 패턴
    TIME_PATTERN = re.compile(r'^오전\s*\d{1,2}[:\s]?\d{0,2}|오후\s*\d{1,2}[:\s]?\d{0,2}$')

    # 성경책 약어 매핑
    BIBLE_BOOK_ABBREV = {
        "딤후": "디모데후서", "딤전": "디모데전서",
        "시": "시편", "고전": "고린도전서", "고후": "고린도후서",
        "히": "히브리서", "롬": "로마서", "갈": "갈라디아서",
        "엡": "에베소서", "빌": "빌립보서", "골": "골로새서",
        "살전": "데살로니가전서", "살후": "데살로니가후서",
        "벧전": "베드로전서", "벧후": "베드로후서",
        "요": "요한복음", "마": "마태복음", "막": "마가복음", "눅": "누가복음",
        "행": "사도행전", "계": "요한계시록", "창": "창세기", "출": "출애굽기",
        "레": "레위기", "민": "민수기", "신": "신명기", "수": "여호수아",
        "삿": "사사기", "룻": "룻기", "삼상": "사무엘상", "삼하": "사무엘하",
        "왕상": "열왕기상", "왕하": "열왕기하", "대상": "역대상", "대하": "역대하",
        "스": "에스라", "느": "느헤미야", "에": "에스더", "욥": "욥기",
        "잠": "잠언", "전": "전도서", "아": "아가", "사": "이사야",
        "렘": "예레미야", "애": "예레미야애가", "겔": "에스겔", "단": "다니엘",
        "호": "호세아", "욜": "요엘", "암": "아모스", "옵": "오바댜",
        "욘": "요나", "미": "미가", "나": "나훔", "합": "하박국",
        "습": "스바냐", "학": "학개", "슥": "스가랴", "말": "말라기",
    }


@dataclass
class ValidationResult:
    """검증 결과"""
    field_name: str
    is_valid: bool
    original_value: str
    validated_value: str
    error_type: str = ""  # pattern_mismatch, missing, invalid_format, suspicious
    suggestion: str = ""
    confidence: float = 1.0
    auto_corrected: bool = False


@dataclass
class ServiceValidation:
    """예배 데이터 검증 결과"""
    service_name: str
    is_valid: bool
    validations: List[ValidationResult] = field(default_factory=list)
    error_count: int = 0
    warning_count: int = 0


# =========================================================================
# 자가 진화형 검증 엔진
# =========================================================================

class SelfEvolvingValidator:
    """
    자가 진화형 검증 엔진 (BulletinAI 핵심)

    기능:
    1. PDF 원본 데이터 추출값 검증
    2. 패턴 기반 데이터 형식 검사
    3. 오류 자동 탐지 및 교정 제안
    4. 학습 데이터 자동 저장 (진화)
    """

    def __init__(self, learning_dir: str = None):
        if learning_dir is None:
            learning_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

        self.learning_dir = Path(learning_dir)
        self.rules_file = self.learning_dir / "learned_rules.json"
        self.patterns = FGFCDataPattern()

        # 학습된 규칙 로드
        self.learned_rules = self._load_rules()

        # 검증 히스토리 (세션 내)
        self.validation_history: List[Dict] = []

        logger.info("🤖 BulletinAI 자가 진화형 검증 엔진 초기화 완료")

    def _load_rules(self) -> Dict:
        """학습된 규칙 로드"""
        if self.rules_file.exists():
            try:
                with open(self.rules_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    return {r['rule_id']: r for r in data.get('rules', [])}
            except Exception as e:
                logger.warning(f"규칙 로드 실패: {e}")
        return {}

    def _save_rules(self):
        """학습된 규칙 저장"""
        data = {
            "updated_at": datetime.now().isoformat(),
            "rules_count": len(self.learned_rules),
            "rules": list(self.learned_rules.values())
        }
        with open(self.rules_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        logger.info(f"✅ learned_rules.json 저장 완료: {len(self.learned_rules)}개 규칙")

    # =========================================================================
    # 1. 데이터 형식 검증
    # =========================================================================

    def validate_pastor_name(self, value: str) -> ValidationResult:
        """설교자 이름 검증"""
        if not value:
            return ValidationResult(
                field_name="pastor",
                is_valid=False,
                original_value=value,
                validated_value="",
                error_type="missing",
                suggestion="설교자 정보가 누락되었습니다"
            )

        # 패턴 매칭
        if self.patterns.PASTOR_PATTERN.match(value.strip()):
            return ValidationResult(
                field_name="pastor",
                is_valid=True,
                original_value=value,
                validated_value=value.strip()
            )

        # 자동 교정 시도
        corrected = self._try_correct_pastor(value)
        if corrected:
            return ValidationResult(
                field_name="pastor",
                is_valid=True,
                original_value=value,
                validated_value=corrected,
                error_type="auto_corrected",
                suggestion=f"'{value}' → '{corrected}'",
                auto_corrected=True
            )

        return ValidationResult(
            field_name="pastor",
            is_valid=False,
            original_value=value,
            validated_value=value,
            error_type="pattern_mismatch",
            suggestion=f"설교자 형식이 올바르지 않습니다: '{value}' (예: '이영훈 목사', '엄태욱 목사')",
            confidence=0.7
        )

    def _try_correct_pastor(self, value: str) -> Optional[str]:
        """설교자 이름 자동 교정"""
        # "목사" 누락 시 추가
        if re.match(r'^[가-힣]{2,4}$', value.strip()):
            return f"{value.strip()} 목사"

        # 공백 정리
        cleaned = re.sub(r'\s+', ' ', value.strip())
        if self.patterns.PASTOR_PATTERN.match(cleaned):
            return cleaned

        return None

    def validate_scripture(self, value: str) -> ValidationResult:
        """성경 구절 검증"""
        if not value:
            return ValidationResult(
                field_name="scripture",
                is_valid=False,
                original_value=value,
                validated_value="",
                error_type="missing",
                suggestion="성경봉독 정보가 누락되었습니다"
            )

        # 패턴 매칭
        for pattern in self.patterns.SCRIPTURE_PATTERNS:
            if pattern.match(value.strip()):
                return ValidationResult(
                    field_name="scripture",
                    is_valid=True,
                    original_value=value,
                    validated_value=value.strip()
                )

        # 자동 교정 시도
        corrected = self._try_correct_scripture(value)
        if corrected:
            return ValidationResult(
                field_name="scripture",
                is_valid=True,
                original_value=value,
                validated_value=corrected,
                error_type="auto_corrected",
                suggestion=f"'{value}' → '{corrected}'",
                auto_corrected=True
            )

        return ValidationResult(
            field_name="scripture",
            is_valid=False,
            original_value=value,
            validated_value=value,
            error_type="pattern_mismatch",
            suggestion=f"성경 구절 형식이 올바르지 않습니다: '{value}' (예: '시 146:1~5', '딤후 4:9~11')",
            confidence=0.7
        )

    def _try_correct_scripture(self, value: str) -> Optional[str]:
        """성경 구절 자동 교정"""
        value = value.strip()

        # 공백 정리
        value = re.sub(r'\s+', ' ', value)

        # "-" → "~" 변환
        value = value.replace('-', '~')

        # 콜론 정규화
        value = re.sub(r'[：]', ':', value)

        # 다시 패턴 매칭
        for pattern in self.patterns.SCRIPTURE_PATTERNS:
            if pattern.match(value):
                return value

        return None

    def validate_hymn(self, value: str) -> ValidationResult:
        """찬송가 검증"""
        if not value:
            return ValidationResult(
                field_name="hymn",
                is_valid=True,  # 찬송은 없을 수 있음
                original_value=value,
                validated_value=""
            )

        if self.patterns.HYMN_PATTERN.match(value.strip()):
            return ValidationResult(
                field_name="hymn",
                is_valid=True,
                original_value=value,
                validated_value=value.strip()
            )

        # 자동 교정
        corrected = self._try_correct_hymn(value)
        if corrected:
            return ValidationResult(
                field_name="hymn",
                is_valid=True,
                original_value=value,
                validated_value=corrected,
                error_type="auto_corrected",
                suggestion=f"'{value}' → '{corrected}'",
                auto_corrected=True
            )

        return ValidationResult(
            field_name="hymn",
            is_valid=False,
            original_value=value,
            validated_value=value,
            error_type="pattern_mismatch",
            suggestion=f"찬송가 형식이 올바르지 않습니다: '{value}' (예: '301장', '21장 4절')"
        )

    def _try_correct_hymn(self, value: str) -> Optional[str]:
        """찬송가 자동 교정"""
        # 숫자만 있으면 "장" 추가
        if re.match(r'^\d{1,3}$', value.strip()):
            return f"{value.strip()}장"

        # "장" 앞에 공백 있으면 제거
        cleaned = re.sub(r'(\d+)\s+장', r'\1장', value)
        if self.patterns.HYMN_PATTERN.match(cleaned):
            return cleaned

        return None

    def validate_choir(self, value: str) -> ValidationResult:
        """찬양대 검증"""
        if not value:
            return ValidationResult(
                field_name="choir",
                is_valid=True,  # 없을 수 있음
                original_value=value,
                validated_value=""
            )

        # 알려진 찬양대 이름과 비교
        for choir_name in self.patterns.CHOIR_NAMES:
            if choir_name in value or value in choir_name:
                return ValidationResult(
                    field_name="choir",
                    is_valid=True,
                    original_value=value,
                    validated_value=choir_name
                )

        # "찬양대" 포함하면 유효로 간주
        if "찬양대" in value:
            return ValidationResult(
                field_name="choir",
                is_valid=True,
                original_value=value,
                validated_value=value.strip()
            )

        return ValidationResult(
            field_name="choir",
            is_valid=False,
            original_value=value,
            validated_value=value,
            error_type="suspicious",
            suggestion=f"찬양대 이름이 올바르지 않을 수 있습니다: '{value}'",
            confidence=0.6
        )

    def validate_service_time(self, value: str) -> ValidationResult:
        """예배 시간 검증"""
        if not value:
            return ValidationResult(
                field_name="time",
                is_valid=False,
                original_value=value,
                validated_value="",
                error_type="missing",
                suggestion="예배 시간 정보가 누락되었습니다"
            )

        # 여러 시간이 / 로 구분될 수 있음
        times = value.split('/')
        all_valid = True
        for t in times:
            t = t.strip()
            if t and not self.patterns.TIME_PATTERN.match(t):
                all_valid = False
                break

        if all_valid:
            return ValidationResult(
                field_name="time",
                is_valid=True,
                original_value=value,
                validated_value=value.strip()
            )

        return ValidationResult(
            field_name="time",
            is_valid=False,
            original_value=value,
            validated_value=value,
            error_type="pattern_mismatch",
            suggestion=f"예배 시간 형식이 올바르지 않습니다: '{value}' (예: '오전 7:00', '오후 5:00')"
        )

    # =========================================================================
    # 2. 예배 전체 검증
    # =========================================================================

    def validate_service(self, service_data: Dict) -> ServiceValidation:
        """
        예배 데이터 전체 검증

        Args:
            service_data: {
                "name": "1부",
                "time": "오전 7:00",
                "scripture": "딤후 4:9~11",
                "hymn": "301장",
                "choir": "베다니 찬양대",
                "sermon_title": "겨울이 오면",
                "sermon_pastor": "엄태욱 목사"
            }
        """
        service_name = service_data.get("name", "알 수 없음")
        validations = []
        error_count = 0
        warning_count = 0

        # 각 필드 검증
        validations.append(self.validate_pastor_name(service_data.get("sermon_pastor", "")))
        validations.append(self.validate_scripture(service_data.get("scripture", "")))
        validations.append(self.validate_hymn(service_data.get("hymn", "")))
        validations.append(self.validate_choir(service_data.get("choir", "")))
        validations.append(self.validate_service_time(service_data.get("time", "")))

        # 설교 제목 (기본 검증 - 비어있으면 오류)
        sermon_title = service_data.get("sermon_title", "")
        if not sermon_title:
            validations.append(ValidationResult(
                field_name="sermon_title",
                is_valid=False,
                original_value="",
                validated_value="",
                error_type="missing",
                suggestion="설교 제목이 누락되었습니다"
            ))
            error_count += 1
        else:
            validations.append(ValidationResult(
                field_name="sermon_title",
                is_valid=True,
                original_value=sermon_title,
                validated_value=sermon_title
            ))

        # 오류/경고 카운트
        for v in validations:
            if not v.is_valid:
                if v.error_type in ["missing", "pattern_mismatch"]:
                    error_count += 1
                else:
                    warning_count += 1

        return ServiceValidation(
            service_name=service_name,
            is_valid=(error_count == 0),
            validations=validations,
            error_count=error_count,
            warning_count=warning_count
        )

    def validate_all_services(self, services: List[Dict]) -> Dict:
        """
        모든 예배 데이터 검증 및 자동 교정

        Returns:
            {
                "is_valid": True/False,
                "total_errors": 0,
                "total_warnings": 0,
                "services": [...],
                "corrections_made": [...],
                "suggestions": [...]
            }
        """
        results = {
            "is_valid": True,
            "total_errors": 0,
            "total_warnings": 0,
            "services": [],
            "corrections_made": [],
            "suggestions": []
        }

        for service_data in services:
            validation = self.validate_service(service_data)

            service_result = {
                "name": validation.service_name,
                "is_valid": validation.is_valid,
                "error_count": validation.error_count,
                "warning_count": validation.warning_count,
                "fields": []
            }

            for v in validation.validations:
                field_result = {
                    "field": v.field_name,
                    "is_valid": v.is_valid,
                    "value": v.validated_value,
                    "original": v.original_value
                }

                if v.auto_corrected:
                    results["corrections_made"].append({
                        "service": validation.service_name,
                        "field": v.field_name,
                        "original": v.original_value,
                        "corrected": v.validated_value,
                        "suggestion": v.suggestion
                    })
                    field_result["auto_corrected"] = True

                if not v.is_valid and v.suggestion:
                    results["suggestions"].append({
                        "service": validation.service_name,
                        "field": v.field_name,
                        "error_type": v.error_type,
                        "suggestion": v.suggestion,
                        "confidence": v.confidence
                    })

                service_result["fields"].append(field_result)

            results["services"].append(service_result)
            results["total_errors"] += validation.error_count
            results["total_warnings"] += validation.warning_count

            if not validation.is_valid:
                results["is_valid"] = False

        # 자동 교정 기록 (학습)
        if results["corrections_made"]:
            self._learn_from_corrections(results["corrections_made"])

        return results

    # =========================================================================
    # 3. 자가 학습 (진화)
    # =========================================================================

    def _learn_from_corrections(self, corrections: List[Dict]):
        """자동 교정에서 학습"""
        for correction in corrections:
            rule_id = f"auto_correction_{correction['field']}_{hash(correction['original']) % 10000}"

            if rule_id in self.learned_rules:
                # 기존 규칙 강화
                self.learned_rules[rule_id]['success_count'] = \
                    self.learned_rules[rule_id].get('success_count', 0) + 1
                self.learned_rules[rule_id]['updated_at'] = datetime.now().isoformat()
            else:
                # 새 규칙 생성
                self.learned_rules[rule_id] = {
                    "rule_id": rule_id,
                    "created_at": datetime.now().isoformat(),
                    "updated_at": datetime.now().isoformat(),
                    "category": "auto_correction",
                    "field": correction['field'],
                    "pattern": correction['original'],
                    "action": f"replace_with:{correction['corrected']}",
                    "confidence": 0.8,
                    "success_count": 1,
                    "fail_count": 0,
                    "source_feedbacks": []
                }

        # 저장
        self._save_rules()
        logger.info(f"🧠 {len(corrections)}개 자동 교정 학습 완료")

    def record_manual_correction(self, service_name: str, field: str,
                                   wrong_value: str, correct_value: str,
                                   source: str = "manual"):
        """수동 교정 기록 (학습)"""
        rule_id = f"manual_correction_{field}_{hash(wrong_value) % 10000}"

        self.learned_rules[rule_id] = {
            "rule_id": rule_id,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "category": "manual_correction",
            "field": field,
            "pattern": wrong_value,
            "action": f"replace_with:{correct_value}",
            "confidence": 0.95,  # 수동 교정은 높은 신뢰도
            "success_count": 1,
            "fail_count": 0,
            "source": source,
            "context": {
                "service": service_name,
                "timestamp": datetime.now().isoformat()
            }
        }

        self._save_rules()
        logger.info(f"🧠 수동 교정 학습: [{field}] '{wrong_value}' → '{correct_value}'")

    def get_correction_suggestion(self, field: str, value: str) -> Optional[str]:
        """학습된 규칙에서 교정 제안 찾기"""
        for rule in self.learned_rules.values():
            if rule.get('field') == field and rule.get('pattern') == value:
                action = rule.get('action', '')
                if action.startswith('replace_with:'):
                    return action.split(':', 1)[1]
        return None

    # =========================================================================
    # 4. 리포트 생성
    # =========================================================================

    def generate_validation_report(self, bulletin_date: str,
                                    validation_results: Dict) -> str:
        """검증 결과 리포트 생성"""
        report_lines = [
            "=" * 60,
            f"🤖 BulletinAI 자가 검증 리포트",
            f"📅 주보 날짜: {bulletin_date}",
            f"🕐 검증 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "=" * 60,
            "",
            f"📊 전체 결과: {'✅ 유효' if validation_results['is_valid'] else '❌ 오류 발견'}",
            f"   - 오류: {validation_results['total_errors']}건",
            f"   - 경고: {validation_results['total_warnings']}건",
            f"   - 자동 교정: {len(validation_results['corrections_made'])}건",
            ""
        ]

        # 예배별 결과
        report_lines.append("📋 예배별 검증 결과:")
        for svc in validation_results['services']:
            status = "✅" if svc['is_valid'] else "❌"
            report_lines.append(f"   {status} {svc['name']}: 오류 {svc['error_count']}, 경고 {svc['warning_count']}")

        # 자동 교정 목록
        if validation_results['corrections_made']:
            report_lines.append("")
            report_lines.append("🔧 자동 교정 내역:")
            for c in validation_results['corrections_made']:
                report_lines.append(f"   - [{c['service']}] {c['field']}: '{c['original']}' → '{c['corrected']}'")

        # 제안 사항
        if validation_results['suggestions']:
            report_lines.append("")
            report_lines.append("💡 수정 제안:")
            for s in validation_results['suggestions']:
                report_lines.append(f"   - [{s['service']}] {s['field']}: {s['suggestion']}")

        report_lines.append("")
        report_lines.append("=" * 60)

        return "\n".join(report_lines)


# =========================================================================
# 싱글톤 인스턴스
# =========================================================================

_validator_instance = None

def get_validator() -> SelfEvolvingValidator:
    """검증기 싱글톤 반환"""
    global _validator_instance
    if _validator_instance is None:
        _validator_instance = SelfEvolvingValidator()
    return _validator_instance


# =========================================================================
# 테스트 / 예제
# =========================================================================

if __name__ == "__main__":
    # 테스트 데이터 (2025-12-28 주보 기준)
    test_services = [
        {
            "name": "1부",
            "time": "오전 7:00",
            "scripture": "딤후 4:9~11",
            "hymn": "301장",
            "choir": "베다니 찬양대",
            "sermon_title": "겨울이 오면",
            "sermon_pastor": "엄태욱 목사"
        },
        {
            "name": "2·3·4부",
            "time": "오전 9:00 / 11:00 / 오후 1:00",
            "scripture": "시 146:1~5",
            "hymn": "21장",
            "choir": "베들레헴 찬양대",
            "sermon_title": "하나님께 소망을 두는 자",
            "sermon_pastor": "이영훈 목사"
        },
        {
            "name": "5부 대학청년",
            "time": "오후 2:30",
            "scripture": "고전 9:24~27",
            "hymn": "",
            "choir": "임마누엘 찬양대",
            "sermon_title": "이와 같이 달음질하라",
            "sermon_pastor": "오수황 목사"
        },
        {
            "name": "주일저녁",
            "time": "오후 5:00",
            "scripture": "히 2:1~4",
            "hymn": "288장",
            "choir": "에벤에셀 찬양대",
            "sermon_title": "이같이 큰 구원",
            "sermon_pastor": "홍승원 목사"
        }
    ]

    validator = get_validator()
    results = validator.validate_all_services(test_services)

    report = validator.generate_validation_report("2025-12-28", results)
    print(report)
