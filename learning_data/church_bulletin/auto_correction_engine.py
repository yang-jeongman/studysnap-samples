"""
자동 교정 엔진 (BulletinAI 핵심)
=============================

오류가 탐지되면 자동으로 수정하고, 수정 결과를 학습 데이터로 저장합니다.
이를 통해 프로그램이 스스로 진화합니다.

핵심 원칙:
- 프로그램이 스스로 오류를 구분하고 수정할 수 있어야 함
- "자동화, AI, 머신러닝, 스스로 진화"
"""

import re
import json
import os
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any, Callable
from dataclasses import dataclass, field, asdict
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


@dataclass
class CorrectionAction:
    """교정 작업"""
    field: str
    original_value: str
    corrected_value: str
    correction_type: str  # auto, rule_based, pattern_match, cross_reference
    confidence: float
    rule_id: Optional[str] = None
    reason: str = ""


@dataclass
class CorrectionResult:
    """교정 결과"""
    service_name: str
    corrections_made: List[CorrectionAction] = field(default_factory=list)
    corrections_suggested: List[CorrectionAction] = field(default_factory=list)
    total_auto_corrected: int = 0
    total_suggested: int = 0


class AutoCorrectionEngine:
    """
    자동 교정 엔진

    기능:
    1. 규칙 기반 자동 교정
    2. 패턴 매칭 교정
    3. 과거 교정 이력 기반 학습
    4. 교정 결과 자동 저장
    """

    def __init__(self, learning_dir: str = None):
        if learning_dir is None:
            learning_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

        self.learning_dir = Path(learning_dir)
        self.rules_file = self.learning_dir / "learned_rules.json"
        self.corrections_log = self.learning_dir / "corrections_history.jsonl"

        # 학습된 규칙 로드
        self.learned_rules = self._load_rules()

        # 내장 교정 규칙 (자주 발생하는 오류)
        self.builtin_corrections = self._init_builtin_corrections()

        # 교정 통계
        self.stats = {
            "total_corrections": 0,
            "auto_corrections": 0,
            "suggested_corrections": 0,
            "rules_applied": {},
            "last_updated": datetime.now().isoformat()
        }

        logger.info("🔧 자동 교정 엔진 초기화 완료")

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
        logger.info(f"✅ learned_rules.json 저장: {len(self.learned_rules)}개 규칙")

    def _init_builtin_corrections(self) -> Dict[str, List[Dict]]:
        """내장 교정 규칙 초기화"""
        return {
            "pastor": [
                # 목사 누락 시 추가
                {"pattern": r"^([가-힣]{2,4})$", "replacement": r"\1 목사", "reason": "'목사' 호칭 추가"},
                # 공백 정리
                {"pattern": r"([가-힣]+)\s{2,}(목사|위임목사)", "replacement": r"\1 \2", "reason": "공백 정리"},
                # 오타 교정: 복사 → 목사
                {"pattern": r"([가-힣]+)\s*복사", "replacement": r"\1 목사", "reason": "'복사'→'목사' 오타 교정"},
            ],
            "scripture": [
                # - 를 ~ 로 변환
                {"pattern": r"(\d+)-(\d+)", "replacement": r"\1~\2", "reason": "하이픈을 물결로 변환"},
                # 전각 콜론을 반각으로
                {"pattern": r"：", "replacement": ":", "reason": "전각 콜론 교정"},
                # 공백 정리
                {"pattern": r"(\d+)\s*:\s*(\d+)", "replacement": r"\1:\2", "reason": "콜론 주변 공백 제거"},
            ],
            "hymn": [
                # 숫자만 있으면 "장" 추가
                {"pattern": r"^(\d{1,3})$", "replacement": r"\1장", "reason": "'장' 추가"},
                # 공백 정리
                {"pattern": r"(\d+)\s+장", "replacement": r"\1장", "reason": "공백 제거"},
            ],
            "time": [
                # 전각 콜론
                {"pattern": r"：", "replacement": ":", "reason": "전각 콜론 교정"},
                # 시간 형식 정규화
                {"pattern": r"오전\s*(\d{1,2})\s*시", "replacement": r"오전 \1:00", "reason": "시간 형식 정규화"},
                {"pattern": r"오후\s*(\d{1,2})\s*시", "replacement": r"오후 \1:00", "reason": "시간 형식 정규화"},
            ],
            "text": [
                # 자주 발생하는 OCR 오류
                {"pattern": r"하렐루야", "replacement": "할렐루야", "reason": "맞춤법 교정"},
                {"pattern": r"여호아", "replacement": "여호와", "reason": "맞춤법 교정"},
                {"pattern": r"아멘", "replacement": "아멘", "reason": "맞춤법 확인"},
            ],
            "today_verse": [
                # 오늘의 말씀 텍스트 정리
                {"pattern": r"\*\*본문:\*\*\s*", "replacement": "", "reason": "마크다운 제거"},
                {"pattern": r"\*\*출처:\*\*\s*", "replacement": "", "reason": "마크다운 제거"},
                {"pattern": r'^\s*"', "replacement": "", "reason": "앞 따옴표 제거"},
                {"pattern": r'"\s*$', "replacement": "", "reason": "뒤 따옴표 제거"},
                {"pattern": r"\s{2,}", "replacement": " ", "reason": "연속 공백 정리"},
                # 2026-01-04 FIX: 말줄임표 교정 (... → …)
                {"pattern": r"\.{3}", "replacement": "…", "reason": "말줄임표 교정 (... → …)"},
                {"pattern": r"…{2,}", "replacement": "…", "reason": "중복 말줄임표 제거"},
            ],
            "verse_reference": [
                # 성경 참조 형식 정규화
                {"pattern": r"(\d+)-(\d+)", "replacement": r"\1~\2", "reason": "하이픈을 물결로"},
                {"pattern": r"：", "replacement": ":", "reason": "전각 콜론 교정"},
                {"pattern": r"\s*\(\s*", "replacement": " (", "reason": "괄호 앞 공백 정리"},
            ]
        }

    def correct_value(self, field: str, value: str,
                      service_name: str = "") -> Tuple[str, List[CorrectionAction]]:
        """
        값 교정

        Args:
            field: 필드명 (pastor, scripture, hymn, time, text)
            value: 원본 값
            service_name: 예배명 (로깅용)

        Returns:
            (교정된 값, 적용된 교정 목록)
        """
        if not value:
            return value, []

        corrections = []
        corrected = value

        # 1. 학습된 규칙 적용 (우선순위 높음)
        corrected, rule_corrections = self._apply_learned_rules(field, corrected, service_name)
        corrections.extend(rule_corrections)

        # 2. 내장 규칙 적용
        if field in self.builtin_corrections:
            for rule in self.builtin_corrections[field]:
                pattern = rule["pattern"]
                replacement = rule["replacement"]
                reason = rule["reason"]

                new_value = re.sub(pattern, replacement, corrected)
                if new_value != corrected:
                    corrections.append(CorrectionAction(
                        field=field,
                        original_value=corrected,
                        corrected_value=new_value,
                        correction_type="builtin",
                        confidence=0.9,
                        reason=reason
                    ))
                    corrected = new_value

        # 3. 교정 기록
        if corrections:
            self._log_corrections(service_name, corrections)
            self._update_stats(corrections)

        return corrected, corrections

    def _apply_learned_rules(self, field: str, value: str,
                              service_name: str) -> Tuple[str, List[CorrectionAction]]:
        """학습된 규칙 적용"""
        corrections = []
        corrected = value

        for rule_id, rule in self.learned_rules.items():
            # 필드 매칭
            if rule.get('field') != field and rule.get('category') != field:
                continue

            # 패턴 매칭
            pattern = rule.get('pattern', '')
            action = rule.get('action', '')

            if not pattern or not action:
                continue

            # 정확히 일치하는 경우
            if pattern == value and action.startswith('replace_with:'):
                replacement = action.split(':', 1)[1]
                corrections.append(CorrectionAction(
                    field=field,
                    original_value=value,
                    corrected_value=replacement,
                    correction_type="rule_based",
                    confidence=rule.get('confidence', 0.8),
                    rule_id=rule_id,
                    reason=f"학습된 규칙 적용: {rule_id}"
                ))
                corrected = replacement

                # 규칙 성공 카운트 증가
                self.learned_rules[rule_id]['success_count'] = \
                    self.learned_rules[rule_id].get('success_count', 0) + 1
                break

        return corrected, corrections

    def correct_service_data(self, service_data: Dict) -> Tuple[Dict, CorrectionResult]:
        """
        예배 데이터 전체 교정

        Args:
            service_data: 원본 예배 데이터

        Returns:
            (교정된 데이터, 교정 결과)
        """
        service_name = service_data.get("name", "알 수 없음")
        corrected_data = service_data.copy()
        all_corrections = []
        all_suggestions = []

        # 각 필드 교정
        field_mappings = {
            "sermon_pastor": "pastor",
            "sermon": "pastor",  # 대체 필드명
            "scripture": "scripture",
            "hymn": "hymn",
            "time": "time",
            "choir": "text",  # 일반 텍스트 규칙 적용
            "sermon_title": "text",
        }

        for data_field, correction_field in field_mappings.items():
            if data_field in corrected_data and corrected_data[data_field]:
                original = corrected_data[data_field]
                corrected, corrections = self.correct_value(
                    correction_field, original, service_name
                )

                if corrected != original:
                    corrected_data[data_field] = corrected
                    all_corrections.extend(corrections)

        return corrected_data, CorrectionResult(
            service_name=service_name,
            corrections_made=all_corrections,
            corrections_suggested=all_suggestions,
            total_auto_corrected=len(all_corrections),
            total_suggested=len(all_suggestions)
        )

    def correct_all_services(self, services: List[Dict]) -> Tuple[List[Dict], List[CorrectionResult]]:
        """모든 예배 데이터 교정"""
        corrected_services = []
        all_results = []

        for service in services:
            corrected, result = self.correct_service_data(service)
            corrected_services.append(corrected)
            all_results.append(result)

        # 교정 후 규칙 저장
        self._save_rules()

        return corrected_services, all_results

    def _log_corrections(self, service_name: str, corrections: List[CorrectionAction]):
        """교정 기록 저장"""
        for correction in corrections:
            log_entry = {
                "timestamp": datetime.now().isoformat(),
                "service": service_name,
                "field": correction.field,
                "original": correction.original_value,
                "corrected": correction.corrected_value,
                "type": correction.correction_type,
                "confidence": correction.confidence,
                "rule_id": correction.rule_id,
                "reason": correction.reason
            }

            with open(self.corrections_log, 'a', encoding='utf-8') as f:
                f.write(json.dumps(log_entry, ensure_ascii=False) + '\n')

    def _update_stats(self, corrections: List[CorrectionAction]):
        """통계 업데이트"""
        self.stats["total_corrections"] += len(corrections)
        for c in corrections:
            if c.correction_type in ["builtin", "rule_based"]:
                self.stats["auto_corrections"] += 1
            else:
                self.stats["suggested_corrections"] += 1

            if c.rule_id:
                self.stats["rules_applied"][c.rule_id] = \
                    self.stats["rules_applied"].get(c.rule_id, 0) + 1

        self.stats["last_updated"] = datetime.now().isoformat()

    # =========================================================================
    # 학습 피드백 루프
    # =========================================================================

    def learn_from_manual_correction(self, field: str, wrong_value: str,
                                       correct_value: str, context: Dict = None):
        """
        수동 교정에서 학습 (피드백 루프)

        사용자가 직접 수정한 경우 이를 학습하여 다음에 자동 적용
        """
        rule_id = f"learned_{field}_{hash(wrong_value) % 100000}"

        # 기존 규칙 업데이트 또는 새 규칙 생성
        if rule_id in self.learned_rules:
            self.learned_rules[rule_id]['success_count'] = \
                self.learned_rules[rule_id].get('success_count', 0) + 1
            self.learned_rules[rule_id]['confidence'] = min(
                0.99,
                self.learned_rules[rule_id].get('confidence', 0.8) + 0.05
            )
            self.learned_rules[rule_id]['updated_at'] = datetime.now().isoformat()
        else:
            self.learned_rules[rule_id] = {
                "rule_id": rule_id,
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat(),
                "category": "learned_correction",
                "field": field,
                "pattern": wrong_value,
                "action": f"replace_with:{correct_value}",
                "confidence": 0.85,
                "success_count": 1,
                "fail_count": 0,
                "source": "manual_correction",
                "context": context or {}
            }

        self._save_rules()
        logger.info(f"🧠 학습 완료: [{field}] '{wrong_value}' → '{correct_value}'")

    def learn_from_validation_failure(self, field: str, value: str,
                                        error_type: str, suggestion: str = ""):
        """
        검증 실패에서 학습

        반복적인 검증 실패 패턴을 기록하여 향후 변환 시 주의
        """
        rule_id = f"validation_warn_{field}_{hash(value) % 100000}"

        if rule_id in self.learned_rules:
            self.learned_rules[rule_id]['fail_count'] = \
                self.learned_rules[rule_id].get('fail_count', 0) + 1
            # 실패가 반복되면 신뢰도 하락
            self.learned_rules[rule_id]['confidence'] = max(
                0.1,
                self.learned_rules[rule_id].get('confidence', 0.5) - 0.1
            )
        else:
            self.learned_rules[rule_id] = {
                "rule_id": rule_id,
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat(),
                "category": "validation_warning",
                "field": field,
                "pattern": value,
                "action": "warn",
                "error_type": error_type,
                "suggestion": suggestion,
                "confidence": 0.5,
                "success_count": 0,
                "fail_count": 1,
                "source": "validation_failure"
            }

        self._save_rules()
        logger.info(f"⚠️ 검증 실패 학습: [{field}] '{value}' - {error_type}")

    def get_correction_stats(self) -> Dict:
        """교정 통계 반환"""
        return {
            **self.stats,
            "learned_rules_count": len(self.learned_rules),
            "high_confidence_rules": len([
                r for r in self.learned_rules.values()
                if r.get('confidence', 0) >= 0.9
            ])
        }

    def generate_correction_report(self, results: List[CorrectionResult]) -> str:
        """교정 결과 리포트 생성"""
        lines = [
            "=" * 60,
            "🔧 자동 교정 리포트",
            f"🕐 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "=" * 60,
            ""
        ]

        total_corrected = sum(r.total_auto_corrected for r in results)
        total_suggested = sum(r.total_suggested for r in results)

        lines.append(f"📊 요약: 자동 교정 {total_corrected}건, 제안 {total_suggested}건")
        lines.append("")

        for result in results:
            if result.corrections_made:
                lines.append(f"📋 {result.service_name}:")
                for c in result.corrections_made:
                    lines.append(f"   ✅ [{c.field}] '{c.original_value}' → '{c.corrected_value}'")
                    lines.append(f"      ({c.reason})")

        lines.append("")
        lines.append("=" * 60)
        return "\n".join(lines)


# =========================================================================
# 싱글톤
# =========================================================================

_engine_instance = None

def get_correction_engine() -> AutoCorrectionEngine:
    """교정 엔진 싱글톤 반환"""
    global _engine_instance
    if _engine_instance is None:
        _engine_instance = AutoCorrectionEngine()
    return _engine_instance


# =========================================================================
# 테스트
# =========================================================================

if __name__ == "__main__":
    engine = get_correction_engine()

    # 테스트 데이터 (오류 포함)
    test_services = [
        {
            "name": "1부",
            "time": "오전 7：00",  # 전각 콜론
            "scripture": "딤후 4:9-11",  # 하이픈 사용
            "hymn": "301",  # "장" 누락
            "choir": "베다니 찬양대",
            "sermon_title": "겨울이 오면",
            "sermon_pastor": "엄태욱"  # "목사" 누락
        },
        {
            "name": "2·3·4부",
            "time": "오전 9 시",  # 비표준 형식
            "scripture": "시 146：1~5",  # 전각 콜론
            "hymn": "21 장",  # 공백 있음
            "choir": "베들레헴 찬양대",
            "sermon_title": "하나님께 소망을 두는 자",
            "sermon_pastor": "이영훈 복사"  # 오타
        }
    ]

    print("=== 자동 교정 테스트 ===\n")

    corrected_services, results = engine.correct_all_services(test_services)

    print(engine.generate_correction_report(results))

    print("\n=== 교정된 데이터 ===")
    for svc in corrected_services:
        print(f"\n[{svc['name']}]")
        for key, value in svc.items():
            if key != "name":
                print(f"  {key}: {value}")
