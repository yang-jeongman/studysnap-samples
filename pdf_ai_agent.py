"""
자기학습 PDF AI 에이전트
PDF 변환 과정에서 학습하고 지속적으로 성장하는 AI 시스템
"""

import logging
import json
import pickle
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
import hashlib
from collections import defaultdict
import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class ConversionPattern:
    """변환 패턴"""
    pattern_id: str
    pdf_type: str  # 'election', 'resume', 'document', etc.
    object_types: List[str]
    layout_structure: Dict[str, Any]
    success_rate: float
    usage_count: int
    created_at: str
    last_used: str
    metadata: Dict[str, Any]


@dataclass
class LearningRecord:
    """학습 기록"""
    record_id: str
    pdf_hash: str
    conversion_result: Dict[str, Any]
    user_feedback: Optional[Dict[str, Any]]
    quality_score: float
    timestamp: str
    improvements: List[str]


class PDFAIAgent:
    """자기학습 PDF AI 에이전트"""

    def __init__(self, knowledge_base_path: str = "ai_knowledge"):
        self.knowledge_base_path = Path(knowledge_base_path)
        self.knowledge_base_path.mkdir(exist_ok=True)

        # 학습 데이터 저장소
        self.patterns_file = self.knowledge_base_path / "patterns.pkl"
        self.learning_records_file = self.knowledge_base_path / "learning_records.pkl"
        self.rules_file = self.knowledge_base_path / "rules.json"

        # 메모리 캐시
        self.patterns: Dict[str, ConversionPattern] = {}
        self.learning_records: List[LearningRecord] = []
        self.dynamic_rules: Dict[str, Any] = {}

        # 통계
        self.stats = {
            "total_conversions": 0,
            "successful_conversions": 0,
            "patterns_learned": 0,
            "avg_quality_score": 0.0
        }

        # 초기화
        self._load_knowledge_base()

        logger.info("PDF AI 에이전트 초기화 완료")

    def _load_knowledge_base(self):
        """지식 베이스 로드"""
        try:
            # 패턴 로드
            if self.patterns_file.exists():
                with open(self.patterns_file, 'rb') as f:
                    self.patterns = pickle.load(f)
                logger.info(f"{len(self.patterns)}개 패턴 로드됨")

            # 학습 기록 로드
            if self.learning_records_file.exists():
                with open(self.learning_records_file, 'rb') as f:
                    self.learning_records = pickle.load(f)
                logger.info(f"{len(self.learning_records)}개 학습 기록 로드됨")

            # 동적 룰 로드
            if self.rules_file.exists():
                with open(self.rules_file, 'r', encoding='utf-8') as f:
                    self.dynamic_rules = json.load(f)
                logger.info(f"{len(self.dynamic_rules)}개 동적 룰 로드됨")

        except Exception as e:
            logger.error(f"지식 베이스 로드 실패: {e}")

    def _save_knowledge_base(self):
        """지식 베이스 저장"""
        try:
            # 패턴 저장
            with open(self.patterns_file, 'wb') as f:
                pickle.dump(self.patterns, f)

            # 학습 기록 저장 (최근 1000개만 유지)
            recent_records = self.learning_records[-1000:]
            with open(self.learning_records_file, 'wb') as f:
                pickle.dump(recent_records, f)

            # 동적 룰 저장
            with open(self.rules_file, 'w', encoding='utf-8') as f:
                json.dump(self.dynamic_rules, f, ensure_ascii=False, indent=2)

            logger.info("지식 베이스 저장 완료")

        except Exception as e:
            logger.error(f"지식 베이스 저장 실패: {e}")

    def analyze_pdf(self, pdf_data: bytes, content_type: str) -> Dict[str, Any]:
        """
        PDF 분석 및 최적 변환 전략 추천

        Args:
            pdf_data: PDF 원본 데이터
            content_type: 문서 타입

        Returns:
            분석 결과 및 추천 전략
        """
        pdf_hash = hashlib.sha256(pdf_data).hexdigest()

        # 유사 패턴 찾기
        similar_patterns = self._find_similar_patterns(content_type)

        # 최적 전략 선택
        best_strategy = self._select_best_strategy(similar_patterns)

        analysis = {
            "pdf_hash": pdf_hash,
            "content_type": content_type,
            "similar_patterns_found": len(similar_patterns),
            "recommended_strategy": best_strategy,
            "confidence_score": self._calculate_confidence(similar_patterns)
        }

        logger.info(f"PDF 분석 완료: {len(similar_patterns)}개 유사 패턴 발견")

        return analysis

    def _find_similar_patterns(self, content_type: str) -> List[ConversionPattern]:
        """유사한 변환 패턴 찾기"""
        similar = []

        for pattern in self.patterns.values():
            if pattern.pdf_type == content_type:
                similar.append(pattern)

        # 성공률과 사용횟수로 정렬
        similar.sort(key=lambda p: (p.success_rate, p.usage_count), reverse=True)

        return similar[:10]  # 상위 10개 반환

    def _select_best_strategy(self, patterns: List[ConversionPattern]) -> Dict[str, Any]:
        """최적 전략 선택"""
        if not patterns:
            return {
                "strategy": "default",
                "layout_hints": [],
                "object_priorities": {}
            }

        # 가장 성공률 높은 패턴 사용
        best_pattern = patterns[0]

        return {
            "strategy": "learned",
            "pattern_id": best_pattern.pattern_id,
            "layout_structure": best_pattern.layout_structure,
            "success_rate": best_pattern.success_rate
        }

    def _calculate_confidence(self, patterns: List[ConversionPattern]) -> float:
        """신뢰도 계산"""
        if not patterns:
            return 0.5  # 기본 신뢰도

        # 패턴의 평균 성공률과 사용 횟수로 계산
        avg_success = np.mean([p.success_rate for p in patterns])
        total_usage = sum([p.usage_count for p in patterns])

        # 사용 횟수가 많을수록 신뢰도 증가
        usage_factor = min(total_usage / 100, 1.0)

        confidence = avg_success * 0.7 + usage_factor * 0.3

        return round(confidence, 2)

    def learn_from_conversion(
        self,
        pdf_data: bytes,
        conversion_result: Dict[str, Any],
        user_feedback: Optional[Dict[str, Any]] = None
    ):
        """
        변환 결과로부터 학습

        Args:
            pdf_data: PDF 원본 데이터
            conversion_result: 변환 결과
            user_feedback: 사용자 피드백 (선택)
        """
        pdf_hash = hashlib.sha256(pdf_data).hexdigest()

        # 품질 점수 계산
        quality_score = self._calculate_quality_score(conversion_result, user_feedback)

        # 학습 기록 생성
        record = LearningRecord(
            record_id=f"lr_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{pdf_hash[:8]}",
            pdf_hash=pdf_hash,
            conversion_result=conversion_result,
            user_feedback=user_feedback,
            quality_score=quality_score,
            timestamp=datetime.now().isoformat(),
            improvements=self._identify_improvements(conversion_result, user_feedback)
        )

        self.learning_records.append(record)

        # 패턴 업데이트 또는 생성
        self._update_or_create_pattern(conversion_result, quality_score)

        # 동적 룰 개선
        self._refine_dynamic_rules(conversion_result, quality_score)

        # 통계 업데이트
        self._update_stats(quality_score)

        # 지식 베이스 저장
        self._save_knowledge_base()

        logger.info(f"학습 완료: 품질 점수 {quality_score:.2f}")

    def _calculate_quality_score(
        self,
        conversion_result: Dict[str, Any],
        user_feedback: Optional[Dict[str, Any]]
    ) -> float:
        """품질 점수 계산"""
        score = 0.7  # 기본 점수

        # 변환 성공 여부
        if conversion_result.get("success"):
            score += 0.1

        # 구조화된 데이터 존재
        if conversion_result.get("structured_data"):
            score += 0.1

        # 사용자 피드백 반영
        if user_feedback:
            if user_feedback.get("rating"):
                # 1-5 점 -> 0.0-0.2 범위로 변환
                score += (user_feedback["rating"] - 3) * 0.1

            if user_feedback.get("is_satisfied"):
                score += 0.1

        # 0.0-1.0 범위로 제한
        return max(0.0, min(1.0, score))

    def _identify_improvements(
        self,
        conversion_result: Dict[str, Any],
        user_feedback: Optional[Dict[str, Any]]
    ) -> List[str]:
        """개선 사항 식별"""
        improvements = []

        # 사용자 피드백에서 개선 사항 추출
        if user_feedback and user_feedback.get("comments"):
            improvements.append(user_feedback["comments"])

        # 자동 개선 사항 감지
        structured = conversion_result.get("structured_data", {})

        if not structured.get("candidate_name"):
            improvements.append("후보자 이름 인식 개선 필요")

        if not structured.get("core_pledges"):
            improvements.append("핵심 공약 추출 개선 필요")

        return improvements

    def _update_or_create_pattern(self, conversion_result: Dict[str, Any], quality_score: float):
        """패턴 업데이트 또는 생성"""
        content_type = conversion_result.get("content_type", "general")

        # 동일 타입의 기존 패턴 찾기
        existing_pattern = None
        for pattern in self.patterns.values():
            if pattern.pdf_type == content_type:
                existing_pattern = pattern
                break

        if existing_pattern:
            # 기존 패턴 업데이트
            existing_pattern.usage_count += 1
            existing_pattern.last_used = datetime.now().isoformat()

            # 성공률 업데이트 (이동 평균)
            alpha = 0.3  # 학습률
            existing_pattern.success_rate = (
                alpha * quality_score +
                (1 - alpha) * existing_pattern.success_rate
            )

            logger.info(f"패턴 업데이트: {existing_pattern.pattern_id}, 성공률: {existing_pattern.success_rate:.2f}")

        else:
            # 새 패턴 생성
            pattern = ConversionPattern(
                pattern_id=f"pattern_{content_type}_{len(self.patterns)}",
                pdf_type=content_type,
                object_types=self._extract_object_types(conversion_result),
                layout_structure=conversion_result.get("layout_structure", {}),
                success_rate=quality_score,
                usage_count=1,
                created_at=datetime.now().isoformat(),
                last_used=datetime.now().isoformat(),
                metadata={}
            )

            self.patterns[pattern.pattern_id] = pattern
            self.stats["patterns_learned"] += 1

            logger.info(f"새 패턴 생성: {pattern.pattern_id}")

    def _extract_object_types(self, conversion_result: Dict[str, Any]) -> List[str]:
        """변환 결과에서 객체 타입 추출"""
        object_types = set()

        structured = conversion_result.get("structured_data", {})

        if structured.get("candidate_name"):
            object_types.add("profile")

        if structured.get("core_pledges"):
            object_types.add("pledges")

        if structured.get("career"):
            object_types.add("career")

        if structured.get("contact_info"):
            object_types.add("contact")

        return list(object_types)

    def _refine_dynamic_rules(self, conversion_result: Dict[str, Any], quality_score: float):
        """동적 룰 개선"""
        content_type = conversion_result.get("content_type", "general")

        if content_type not in self.dynamic_rules:
            self.dynamic_rules[content_type] = {
                "extraction_rules": [],
                "layout_rules": [],
                "quality_threshold": 0.7
            }

        # 품질 임계값 자동 조정
        rules = self.dynamic_rules[content_type]
        current_threshold = rules.get("quality_threshold", 0.7)

        # 성공적인 변환인 경우 임계값 상향 조정
        if quality_score > current_threshold:
            rules["quality_threshold"] = min(0.95, current_threshold + 0.02)

        logger.info(f"{content_type} 룰 개선: 품질 임계값 {rules['quality_threshold']:.2f}")

    def _update_stats(self, quality_score: float):
        """통계 업데이트"""
        self.stats["total_conversions"] += 1

        if quality_score >= 0.7:
            self.stats["successful_conversions"] += 1

        # 평균 품질 점수 업데이트
        total = self.stats["total_conversions"]
        current_avg = self.stats["avg_quality_score"]
        self.stats["avg_quality_score"] = (
            (current_avg * (total - 1) + quality_score) / total
        )

    def get_learning_insights(self) -> Dict[str, Any]:
        """학습 인사이트 제공"""
        return {
            "statistics": self.stats,
            "total_patterns": len(self.patterns),
            "total_learning_records": len(self.learning_records),
            "top_patterns": self._get_top_patterns(5),
            "recent_improvements": self._get_recent_improvements(10)
        }

    def _get_top_patterns(self, n: int) -> List[Dict[str, Any]]:
        """상위 패턴 가져오기"""
        patterns = list(self.patterns.values())
        patterns.sort(key=lambda p: (p.success_rate, p.usage_count), reverse=True)

        return [
            {
                "pattern_id": p.pattern_id,
                "pdf_type": p.pdf_type,
                "success_rate": p.success_rate,
                "usage_count": p.usage_count
            }
            for p in patterns[:n]
        ]

    def _get_recent_improvements(self, n: int) -> List[str]:
        """최근 개선 사항 가져오기"""
        recent_records = self.learning_records[-n:]
        improvements = []

        for record in reversed(recent_records):
            improvements.extend(record.improvements)

        return improvements[:n]


# 싱글톤 인스턴스
_ai_agent = None

def get_ai_agent() -> PDFAIAgent:
    """AI 에이전트 싱글톤 인스턴스"""
    global _ai_agent
    if _ai_agent is None:
        _ai_agent = PDFAIAgent()
    return _ai_agent
