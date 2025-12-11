"""
학습 시스템 - 변환 결과를 분석하고 개선하는 자동 학습 모듈
"""

import os
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional
from collections import defaultdict, Counter

logger = logging.getLogger(__name__)


class LearningSystem:
    """자동 학습 및 개선 시스템"""

    def __init__(self, data_dir: str = "learning_data"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)

        # 학습 데이터 파일들
        self.conversions_file = self.data_dir / "conversions.jsonl"
        self.feedback_file = self.data_dir / "feedback.jsonl"
        self.stats_file = self.data_dir / "stats.json"
        self.patterns_file = self.data_dir / "learned_patterns.json"

        # 학습된 패턴 로드
        self.learned_patterns = self._load_patterns()

        logger.info(f"학습 시스템 초기화 완료: {self.data_dir}")

    def log_conversion(self, job_id: str, conversion_data: Dict[str, Any]) -> None:
        """변환 작업 기록"""
        try:
            content_type = conversion_data.get("content_type", "")
            structured_data = conversion_data.get("structured_data", {})

            # 컨텐츠 타입에 따라 다른 메타데이터 추출
            if content_type == "church":
                extracted_data = {
                    "worship_services_count": len(structured_data.get("worship_services", [])),
                    "has_sermon": bool(structured_data.get("sermon", {}).get("title", "")),
                    "choir_count": len(structured_data.get("choir", [])),
                    "news_count": len(structured_data.get("news", [])),
                    "has_verse": bool(structured_data.get("today_verse", {}).get("text", "")),
                }
            else:
                # 선거 공보물 등 기본 구조
                extracted_data = {
                    "candidate_name": structured_data.get("candidate_name", ""),
                    "party": structured_data.get("party", ""),
                    "pledges_count": len(structured_data.get("core_pledges", [])),
                    "career_count": len(structured_data.get("career", [])),
                    "has_contact": bool(structured_data.get("contact_info", "")),
                }

            log_entry = {
                "timestamp": datetime.now().isoformat(),
                "job_id": job_id,
                "filename": conversion_data.get("filename", ""),
                "content_type": content_type,
                "page_count": conversion_data.get("page_count", 0),
                "is_image_based": conversion_data.get("is_image_based", False),
                "ocr_used": conversion_data.get("ocr_used", False),
                "processing_time": conversion_data.get("processing_time", 0),
                "extracted_data": extracted_data
            }

            # JSONL 형식으로 추가 (각 줄이 하나의 JSON 객체)
            with open(self.conversions_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")

            logger.info(f"[학습] 변환 기록 저장: {job_id}")

        except Exception as e:
            logger.error(f"변환 기록 저장 실패: {str(e)}", exc_info=True)

    def log_feedback(self, job_id: str, feedback_data: Dict[str, Any]) -> None:
        """사용자 피드백 기록"""
        try:
            feedback_entry = {
                "timestamp": datetime.now().isoformat(),
                "job_id": job_id,
                "rating": feedback_data.get("rating", 0),  # 1-5 별점
                "accuracy": feedback_data.get("accuracy", 0),  # OCR 정확도 1-5
                "completeness": feedback_data.get("completeness", 0),  # 완성도 1-5
                "issues": feedback_data.get("issues", []),  # 발견된 문제들
                "comment": feedback_data.get("comment", ""),
                "corrections": feedback_data.get("corrections", {})  # 사용자 수정사항
            }

            with open(self.feedback_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(feedback_entry, ensure_ascii=False) + "\n")

            logger.info(f"[학습] 피드백 저장: {job_id} (평점: {feedback_data.get('rating', 0)})")

            # 피드백 기반으로 패턴 학습
            self._learn_from_feedback(feedback_entry)

        except Exception as e:
            logger.error(f"피드백 저장 실패: {str(e)}", exc_info=True)

    def get_statistics(self) -> Dict[str, Any]:
        """전체 통계 분석"""
        try:
            stats = {
                "total_conversions": 0,
                "content_types": Counter(),
                "average_page_count": 0,
                "ocr_usage_rate": 0,
                "feedback_count": 0,
                "average_rating": 0,
                "common_issues": Counter(),
                "success_rate": 0,
                "top_parties": Counter(),
                "processing_times": []
            }

            # 변환 기록 분석
            if self.conversions_file.exists():
                conversions = []
                with open(self.conversions_file, "r", encoding="utf-8") as f:
                    for line in f:
                        if line.strip():
                            conversions.append(json.loads(line))

                stats["total_conversions"] = len(conversions)

                if conversions:
                    # 콘텐츠 타입 통계
                    for conv in conversions:
                        stats["content_types"][conv.get("content_type", "unknown")] += 1
                        if conv.get("processing_time"):
                            stats["processing_times"].append(conv["processing_time"])

                        # 정당 통계
                        party = conv.get("extracted_data", {}).get("party", "")
                        if party:
                            stats["top_parties"][party] += 1

                    # 평균 계산
                    page_counts = [c.get("page_count", 0) for c in conversions]
                    stats["average_page_count"] = sum(page_counts) / len(page_counts)

                    ocr_used = sum(1 for c in conversions if c.get("ocr_used", False))
                    stats["ocr_usage_rate"] = (ocr_used / len(conversions)) * 100

                    if stats["processing_times"]:
                        stats["average_processing_time"] = sum(stats["processing_times"]) / len(stats["processing_times"])

            # 피드백 분석
            if self.feedback_file.exists():
                feedbacks = []
                with open(self.feedback_file, "r", encoding="utf-8") as f:
                    for line in f:
                        if line.strip():
                            feedbacks.append(json.loads(line))

                stats["feedback_count"] = len(feedbacks)

                if feedbacks:
                    ratings = [f.get("rating", 0) for f in feedbacks if f.get("rating", 0) > 0]
                    if ratings:
                        stats["average_rating"] = sum(ratings) / len(ratings)

                    # 일반적인 문제 수집
                    for fb in feedbacks:
                        for issue in fb.get("issues", []):
                            stats["common_issues"][issue] += 1

                    # 성공률 (평점 4+ 비율)
                    success = sum(1 for r in ratings if r >= 4)
                    stats["success_rate"] = (success / len(ratings) * 100) if ratings else 0

            # 통계 파일 저장
            with open(self.stats_file, "w", encoding="utf-8") as f:
                # Counter 객체를 dict로 변환
                stats_serializable = {
                    **stats,
                    "content_types": dict(stats["content_types"]),
                    "common_issues": dict(stats["common_issues"]),
                    "top_parties": dict(stats["top_parties"]),
                    "last_updated": datetime.now().isoformat()
                }
                json.dump(stats_serializable, f, ensure_ascii=False, indent=2)

            return stats

        except Exception as e:
            logger.error(f"통계 분석 실패: {str(e)}", exc_info=True)
            return {}

    def _learn_from_feedback(self, feedback: Dict[str, Any]) -> None:
        """피드백으로부터 패턴 학습"""
        try:
            # 정확도가 낮은 경우 개선 패턴 추출
            if feedback.get("accuracy", 5) < 3:
                issues = feedback.get("issues", [])
                corrections = feedback.get("corrections", {})

                # 공통 오류 패턴 저장
                for issue in issues:
                    if issue not in self.learned_patterns.get("common_errors", []):
                        self.learned_patterns.setdefault("common_errors", []).append(issue)

                # 수정사항 패턴화
                if corrections:
                    for field, correction in corrections.items():
                        pattern_key = f"field_{field}"
                        if pattern_key not in self.learned_patterns.get("corrections", {}):
                            self.learned_patterns.setdefault("corrections", {})[pattern_key] = []
                        self.learned_patterns["corrections"][pattern_key].append(correction)

            # 패턴 저장
            self._save_patterns()

        except Exception as e:
            logger.error(f"패턴 학습 실패: {str(e)}", exc_info=True)

    def _load_patterns(self) -> Dict[str, Any]:
        """학습된 패턴 로드"""
        try:
            if self.patterns_file.exists():
                with open(self.patterns_file, "r", encoding="utf-8") as f:
                    return json.load(f)
        except Exception as e:
            logger.error(f"패턴 로드 실패: {str(e)}")

        return {
            "common_errors": [],
            "corrections": {},
            "optimization_hints": {},
            "version": "1.0"
        }

    def _save_patterns(self) -> None:
        """학습된 패턴 저장"""
        try:
            with open(self.patterns_file, "w", encoding="utf-8") as f:
                json.dump(self.learned_patterns, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"패턴 저장 실패: {str(e)}")

    def get_improvement_suggestions(self) -> List[str]:
        """개선 제안 생성"""
        suggestions = []

        try:
            stats = self.get_statistics()

            # OCR 정확도 개선 제안
            if stats.get("average_rating", 0) < 4:
                suggestions.append("OCR 프롬프트 개선 필요 - 평균 평점이 낮습니다")

            # 자주 발생하는 문제 분석
            common_issues = stats.get("common_issues", {})
            if common_issues:
                top_issue = max(common_issues.items(), key=lambda x: x[1])
                suggestions.append(f"자주 발생하는 문제: '{top_issue[0]}' ({top_issue[1]}회)")

            # 처리 시간 최적화
            avg_time = stats.get("average_processing_time", 0)
            if avg_time > 300:  # 5분 이상
                suggestions.append(f"처리 시간 최적화 필요 - 평균 {avg_time:.1f}초")

            # 데이터 부족 경고
            if stats.get("total_conversions", 0) < 10:
                suggestions.append("더 많은 변환 데이터 수집이 필요합니다")

            if stats.get("feedback_count", 0) < stats.get("total_conversions", 0) * 0.1:
                suggestions.append("사용자 피드백 수집률이 낮습니다")

        except Exception as e:
            logger.error(f"개선 제안 생성 실패: {str(e)}")

        return suggestions

    def export_training_data(self, output_file: str) -> bool:
        """학습 데이터 내보내기 (추후 모델 파인튜닝용)"""
        try:
            training_data = {
                "conversions": [],
                "feedbacks": [],
                "patterns": self.learned_patterns,
                "exported_at": datetime.now().isoformat()
            }

            # 변환 데이터 로드
            if self.conversions_file.exists():
                with open(self.conversions_file, "r", encoding="utf-8") as f:
                    for line in f:
                        if line.strip():
                            training_data["conversions"].append(json.loads(line))

            # 피드백 데이터 로드
            if self.feedback_file.exists():
                with open(self.feedback_file, "r", encoding="utf-8") as f:
                    for line in f:
                        if line.strip():
                            training_data["feedbacks"].append(json.loads(line))

            # 내보내기
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(training_data, f, ensure_ascii=False, indent=2)

            logger.info(f"학습 데이터 내보내기 완료: {output_file}")
            return True

        except Exception as e:
            logger.error(f"학습 데이터 내보내기 실패: {str(e)}", exc_info=True)
            return False


# 싱글톤 인스턴스
_learning_system = None

def get_learning_system() -> LearningSystem:
    """학습 시스템 싱글톤 인스턴스 가져오기"""
    global _learning_system
    if _learning_system is None:
        _learning_system = LearningSystem()
    return _learning_system
