"""
능동형 AI 학습 시스템 v1.0
- 사용자 피드백 수집 및 저장
- HTML 변경 비교 및 패턴 추출
- 규칙 자동 개선 및 진화
- 학습 효과 측정

학습 루프:
1. 변환 수행 → 결과 저장
2. 사용자 피드백 수집 (좋음/나쁨/수정)
3. 수정된 HTML과 원본 비교 → 차이점 추출
4. 패턴 분석 → 새 규칙 생성/기존 규칙 개선
5. 다음 변환에 적용 → 반복
"""

import os
import json
import re
import difflib
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field, asdict
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


@dataclass
class Feedback:
    """사용자 피드백"""
    job_id: str
    timestamp: str
    rating: int  # 1-5점
    feedback_type: str  # 'rating', 'correction', 'suggestion'
    category: str  # 'party', 'name', 'pledge', 'layout', 'color', 'image'
    original_value: str = ""
    corrected_value: str = ""
    comment: str = ""


@dataclass
class HTMLDiff:
    """HTML 변경 비교 결과"""
    job_id: str
    timestamp: str
    original_html: str
    modified_html: str
    changes: List[Dict[str, Any]] = field(default_factory=list)
    extracted_patterns: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class LearnedRule:
    """학습된 규칙"""
    rule_id: str
    created_at: str
    updated_at: str
    category: str  # 'party_detection', 'name_extraction', 'pledge_pattern', etc.
    pattern: str
    action: str  # 'replace', 'add', 'remove', 'style'
    confidence: float
    success_count: int = 0
    fail_count: int = 0
    source_feedbacks: List[str] = field(default_factory=list)  # feedback IDs


class ActiveLearningEngine:
    """능동형 AI 학습 엔진"""

    def __init__(self, data_dir: str = None):
        if data_dir is None:
            data_dir = os.path.dirname(os.path.abspath(__file__))

        self.data_dir = Path(data_dir)
        self.feedback_file = self.data_dir / "feedbacks.jsonl"
        self.diffs_file = self.data_dir / "html_diffs.jsonl"
        self.rules_file = self.data_dir / "learned_rules.json"
        self.stats_file = self.data_dir / "learning_stats.json"

        # 메모리 캐시
        self.learned_rules: Dict[str, LearnedRule] = {}
        self.recent_feedbacks: List[Feedback] = []
        self.stats = self._load_stats()

        # 규칙 로드
        self._load_rules()

        logger.info("능동형 AI 학습 엔진 초기화 완료")

    def _load_stats(self) -> Dict:
        """학습 통계 로드"""
        default_stats = {
            "total_feedbacks": 0,
            "positive_feedbacks": 0,
            "negative_feedbacks": 0,
            "corrections_count": 0,
            "rules_generated": 0,
            "rules_improved": 0,
            "average_rating": 0.0,
            "category_stats": {},
            "improvement_history": [],
            "last_updated": datetime.now().isoformat()
        }

        if self.stats_file.exists():
            try:
                with open(self.stats_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                pass

        return default_stats

    def _save_stats(self):
        """통계 저장"""
        self.stats["last_updated"] = datetime.now().isoformat()
        with open(self.stats_file, 'w', encoding='utf-8') as f:
            json.dump(self.stats, f, ensure_ascii=False, indent=2)

    def _load_rules(self):
        """학습된 규칙 로드"""
        if self.rules_file.exists():
            try:
                with open(self.rules_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for rule_data in data.get("rules", []):
                        rule = LearnedRule(**rule_data)
                        self.learned_rules[rule.rule_id] = rule
                logger.info(f"학습된 규칙 {len(self.learned_rules)}개 로드됨")
            except Exception as e:
                logger.warning(f"규칙 로드 실패: {e}")

    def _save_rules(self):
        """규칙 저장"""
        data = {
            "updated_at": datetime.now().isoformat(),
            "rules_count": len(self.learned_rules),
            "rules": [asdict(rule) for rule in self.learned_rules.values()]
        }
        with open(self.rules_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    # =========================================================================
    # 0. 변환 기록
    # =========================================================================

    def record_conversion(self, conversion_data: Dict[str, Any]) -> None:
        """
        변환 메타데이터 기록

        Args:
            conversion_data: 변환 정보 (후보명, 정당, 지역, 공약수 등)
        """
        conversion_record = {
            "timestamp": datetime.now().isoformat(),
            **conversion_data
        }

        # conversions.jsonl에 추가 (기존 파일과 호환)
        conversions_file = self.data_dir / "conversions.jsonl"
        try:
            with open(conversions_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(conversion_record, ensure_ascii=False) + "\n")

            # 통계 업데이트
            if "conversion_count" not in self.stats:
                self.stats["conversion_count"] = 0
            self.stats["conversion_count"] += 1

            # 정당별 통계
            party = conversion_data.get("party", "미확인")
            if "party_stats" not in self.stats:
                self.stats["party_stats"] = {}
            self.stats["party_stats"][party] = self.stats["party_stats"].get(party, 0) + 1

            # 후보 유형별 통계
            ctype = conversion_data.get("candidate_type", "unknown")
            if "candidate_type_stats" not in self.stats:
                self.stats["candidate_type_stats"] = {}
            self.stats["candidate_type_stats"][ctype] = self.stats["candidate_type_stats"].get(ctype, 0) + 1

            self._save_stats()
            logger.info(f"변환 기록 저장: {conversion_data.get('candidate_name', 'unknown')}")

        except Exception as e:
            logger.error(f"변환 기록 저장 실패: {e}")

    # =========================================================================
    # 1. 피드백 수집
    # =========================================================================

    def add_feedback(self, job_id: str, rating: int, feedback_type: str,
                     category: str, original_value: str = "",
                     corrected_value: str = "", comment: str = "") -> Feedback:
        """
        사용자 피드백 추가

        Args:
            job_id: 변환 작업 ID
            rating: 1-5점 평가
            feedback_type: 'rating', 'correction', 'suggestion'
            category: 'party', 'name', 'pledge', 'layout', 'color', 'image'
            original_value: 원래 값 (수정 시)
            corrected_value: 수정된 값
            comment: 추가 코멘트
        """
        feedback = Feedback(
            job_id=job_id,
            timestamp=datetime.now().isoformat(),
            rating=rating,
            feedback_type=feedback_type,
            category=category,
            original_value=original_value,
            corrected_value=corrected_value,
            comment=comment
        )

        # 파일에 저장
        with open(self.feedback_file, 'a', encoding='utf-8') as f:
            f.write(json.dumps(asdict(feedback), ensure_ascii=False) + '\n')

        # 통계 업데이트
        self.stats["total_feedbacks"] += 1
        if rating >= 4:
            self.stats["positive_feedbacks"] += 1
        elif rating <= 2:
            self.stats["negative_feedbacks"] += 1

        if feedback_type == "correction":
            self.stats["corrections_count"] += 1
            # 수정 피드백은 즉시 학습
            self._learn_from_correction(feedback)

        # 카테고리별 통계
        if category not in self.stats["category_stats"]:
            self.stats["category_stats"][category] = {"count": 0, "avg_rating": 0}

        cat_stats = self.stats["category_stats"][category]
        cat_stats["count"] += 1
        cat_stats["avg_rating"] = (
            (cat_stats["avg_rating"] * (cat_stats["count"] - 1) + rating)
            / cat_stats["count"]
        )

        self._save_stats()

        logger.info(f"피드백 저장: job={job_id}, rating={rating}, category={category}")
        return feedback

    # =========================================================================
    # 2. HTML 변경 비교 및 저장
    # =========================================================================

    def save_html_diff(self, job_id: str, original_html: str,
                       modified_html: str) -> HTMLDiff:
        """
        원본 HTML과 수정된 HTML 비교 저장
        """
        changes = self._extract_changes(original_html, modified_html)
        patterns = self._extract_patterns_from_changes(changes)

        diff = HTMLDiff(
            job_id=job_id,
            timestamp=datetime.now().isoformat(),
            original_html=original_html[:1000],  # 요약 저장
            modified_html=modified_html[:1000],
            changes=changes,
            extracted_patterns=patterns
        )

        # 파일에 저장
        with open(self.diffs_file, 'a', encoding='utf-8') as f:
            f.write(json.dumps(asdict(diff), ensure_ascii=False) + '\n')

        # 패턴에서 규칙 학습
        for pattern in patterns:
            self._create_or_update_rule(pattern, job_id)

        logger.info(f"HTML 변경 저장: {len(changes)}개 변경, {len(patterns)}개 패턴 추출")
        return diff

    def _extract_changes(self, original: str, modified: str) -> List[Dict]:
        """HTML 변경점 추출 - 개선된 버전"""
        changes = []

        # 라인별 비교
        orig_lines = original.split('\n')
        mod_lines = modified.split('\n')

        differ = difflib.unified_diff(orig_lines, mod_lines, lineterm='')

        current_change = None
        for line in differ:
            if line.startswith('---') or line.startswith('+++'):
                continue
            elif line.startswith('-'):
                if current_change and current_change['type'] == 'remove':
                    current_change['content'] += '\n' + line[1:]
                else:
                    if current_change:
                        changes.append(current_change)
                    current_change = {'type': 'remove', 'content': line[1:]}
            elif line.startswith('+'):
                if current_change and current_change['type'] == 'add':
                    current_change['content'] += '\n' + line[1:]
                else:
                    if current_change:
                        changes.append(current_change)
                    current_change = {'type': 'add', 'content': line[1:]}
            else:
                if current_change:
                    changes.append(current_change)
                    current_change = None

        if current_change:
            changes.append(current_change)

        # 변경 유형 분석
        for change in changes:
            change['category'] = self._categorize_change(change['content'])
            change['element_type'] = self._detect_element_type(change['content'])
            change['css_changes'] = self._extract_css_changes(change['content'])

        return changes[:50]  # 최대 50개

    def _detect_element_type(self, content: str) -> str:
        """변경된 HTML 요소 유형 감지"""
        content_lower = content.lower()

        if re.search(r'<(section|div)[^>]*class="[^"]*hero', content_lower):
            return 'hero_section'
        elif re.search(r'<(section|div)[^>]*class="[^"]*pledge', content_lower):
            return 'pledge_section'
        elif re.search(r'<(section|div)[^>]*class="[^"]*career', content_lower):
            return 'career_section'
        elif re.search(r'<(section|div)[^>]*class="[^"]*contact', content_lower):
            return 'contact_section'
        elif '<h1' in content_lower or '<h2' in content_lower:
            return 'heading'
        elif '<p' in content_lower:
            return 'paragraph'
        elif '<ul' in content_lower or '<ol' in content_lower or '<li' in content_lower:
            return 'list'
        elif '<img' in content_lower:
            return 'image'
        elif 'style=' in content_lower or '<style' in content_lower:
            return 'style'
        else:
            return 'other'

    def _extract_css_changes(self, content: str) -> List[Dict]:
        """CSS 변경 사항 추출"""
        css_changes = []

        # inline style 추출
        style_matches = re.findall(r'style=["\']([^"\']+)["\']', content)
        for style in style_matches:
            # 개별 속성 파싱
            props = style.split(';')
            for prop in props:
                if ':' in prop:
                    key, value = prop.split(':', 1)
                    css_changes.append({
                        'property': key.strip(),
                        'value': value.strip(),
                        'type': 'inline'
                    })

        # CSS 규칙 블록 추출
        css_blocks = re.findall(r'([.#]?[\w-]+)\s*\{([^}]+)\}', content)
        for selector, rules in css_blocks:
            props = rules.split(';')
            for prop in props:
                if ':' in prop:
                    key, value = prop.split(':', 1)
                    css_changes.append({
                        'selector': selector.strip(),
                        'property': key.strip(),
                        'value': value.strip(),
                        'type': 'rule'
                    })

        return css_changes

    def _categorize_change(self, content: str) -> str:
        """변경 내용 카테고리 분류"""
        content_lower = content.lower()

        if '<img' in content_lower or 'src=' in content_lower:
            return 'image'
        elif 'color' in content_lower or 'background' in content_lower:
            return 'color'
        elif '국민의힘' in content or '민주당' in content or '정당' in content:
            return 'party'
        elif '공약' in content or 'pledge' in content_lower:
            return 'pledge'
        elif 'style=' in content_lower or 'class=' in content_lower:
            return 'layout'
        elif re.search(r'^[가-힣]{2,4}$', content.strip()):
            return 'name'
        else:
            return 'other'

    def _extract_patterns_from_changes(self, changes: List[Dict]) -> List[Dict]:
        """변경점에서 패턴 추출"""
        patterns = []

        for i, change in enumerate(changes):
            # 연속된 remove-add 쌍 찾기 (교체 패턴)
            if change['type'] == 'remove' and i + 1 < len(changes):
                next_change = changes[i + 1]
                if next_change['type'] == 'add':
                    pattern = {
                        'type': 'replace',
                        'category': change['category'],
                        'from_pattern': self._generalize_pattern(change['content']),
                        'to_pattern': next_change['content'],
                        'confidence': 0.7
                    }
                    patterns.append(pattern)

            # 이미지 추가 패턴
            elif change['type'] == 'add' and change['category'] == 'image':
                img_match = re.search(r'<img[^>]+src=["\']([^"\']+)["\']', change['content'])
                if img_match:
                    patterns.append({
                        'type': 'add_image',
                        'category': 'image',
                        'location': self._detect_location(change['content']),
                        'pattern': img_match.group(0),
                        'confidence': 0.6
                    })

            # 스타일 변경 패턴
            elif change['category'] in ['color', 'layout']:
                style_match = re.search(r'style=["\']([^"\']+)["\']', change['content'])
                if style_match:
                    patterns.append({
                        'type': 'style_change',
                        'category': change['category'],
                        'style': style_match.group(1),
                        'confidence': 0.65
                    })

        return patterns

    def _generalize_pattern(self, content: str) -> str:
        """구체적인 값을 일반화된 패턴으로 변환"""
        # 숫자 일반화
        pattern = re.sub(r'\d+', r'\\d+', content)
        # 한글 이름 일반화
        pattern = re.sub(r'[가-힣]{2,4}(?=\s*(후보|의원|시장|구청장))', r'[가-힣]{2,4}', pattern)
        return pattern

    def _detect_location(self, content: str) -> str:
        """HTML 위치 감지"""
        if 'hero' in content.lower() or 'header' in content.lower():
            return 'hero'
        elif 'pledge' in content.lower() or '공약' in content:
            return 'pledge'
        elif 'footer' in content.lower():
            return 'footer'
        else:
            return 'body'

    # =========================================================================
    # 3. 패턴 학습 및 규칙 개선
    # =========================================================================

    def _learn_from_correction(self, feedback: Feedback):
        """수정 피드백에서 학습"""
        if not feedback.original_value or not feedback.corrected_value:
            return

        rule_id = f"rule_{feedback.category}_{len(self.learned_rules) + 1}"

        # 기존 유사 규칙 찾기
        existing_rule = self._find_similar_rule(
            feedback.category,
            feedback.original_value
        )

        if existing_rule:
            # 기존 규칙 강화
            existing_rule.success_count += 1
            existing_rule.confidence = min(0.99, existing_rule.confidence + 0.05)
            existing_rule.updated_at = datetime.now().isoformat()
            existing_rule.source_feedbacks.append(feedback.job_id)
            self.stats["rules_improved"] += 1
            logger.info(f"규칙 강화: {existing_rule.rule_id}, confidence={existing_rule.confidence}")
        else:
            # 새 규칙 생성
            new_rule = LearnedRule(
                rule_id=rule_id,
                created_at=datetime.now().isoformat(),
                updated_at=datetime.now().isoformat(),
                category=feedback.category,
                pattern=self._generalize_pattern(feedback.original_value),
                action=f"replace_with:{feedback.corrected_value}",
                confidence=0.7,
                success_count=1,
                source_feedbacks=[feedback.job_id]
            )
            self.learned_rules[rule_id] = new_rule
            self.stats["rules_generated"] += 1
            logger.info(f"새 규칙 생성: {rule_id}")

        self._save_rules()
        self._save_stats()

    def _create_or_update_rule(self, pattern: Dict, job_id: str):
        """패턴에서 규칙 생성/업데이트"""
        category = pattern.get('category', 'other')
        pattern_key = f"{category}_{pattern.get('type')}_{hash(str(pattern)) % 10000}"

        if pattern_key in self.learned_rules:
            rule = self.learned_rules[pattern_key]
            rule.success_count += 1
            rule.confidence = min(0.99, rule.confidence + 0.02)
            rule.updated_at = datetime.now().isoformat()
        else:
            rule = LearnedRule(
                rule_id=pattern_key,
                created_at=datetime.now().isoformat(),
                updated_at=datetime.now().isoformat(),
                category=category,
                pattern=str(pattern.get('from_pattern', pattern.get('pattern', ''))),
                action=pattern.get('type', 'unknown'),
                confidence=pattern.get('confidence', 0.5),
                source_feedbacks=[job_id]
            )
            self.learned_rules[pattern_key] = rule

        self._save_rules()

    def _find_similar_rule(self, category: str, pattern: str) -> Optional[LearnedRule]:
        """유사한 규칙 찾기"""
        for rule in self.learned_rules.values():
            if rule.category == category:
                # 패턴 유사도 체크
                if rule.pattern in pattern or pattern in rule.pattern:
                    return rule
        return None

    # =========================================================================
    # 4. 규칙 적용 (변환 시 사용)
    # =========================================================================

    def get_applicable_rules(self, category: str = None,
                            min_confidence: float = 0.6) -> List[LearnedRule]:
        """적용 가능한 규칙 목록 반환"""
        rules = []
        for rule in self.learned_rules.values():
            if rule.confidence >= min_confidence:
                if category is None or rule.category == category:
                    rules.append(rule)

        # 신뢰도 순 정렬
        rules.sort(key=lambda r: r.confidence, reverse=True)
        return rules

    def apply_rules_to_html(self, html: str, category: str = None) -> Tuple[str, List[str]]:
        """
        학습된 규칙을 HTML에 적용

        Returns:
            (수정된 HTML, 적용된 규칙 ID 목록)
        """
        applied = []
        modified_html = html

        rules = self.get_applicable_rules(category)

        for rule in rules:
            if rule.action.startswith('replace_with:'):
                replacement = rule.action.split(':', 1)[1]
                try:
                    new_html = re.sub(rule.pattern, replacement, modified_html)
                    if new_html != modified_html:
                        modified_html = new_html
                        applied.append(rule.rule_id)
                        logger.info(f"규칙 적용: {rule.rule_id}")
                except re.error:
                    pass

        return modified_html, applied

    # =========================================================================
    # 5. 학습 효과 측정
    # =========================================================================

    def get_learning_stats(self) -> Dict:
        """학습 통계 반환"""
        return {
            **self.stats,
            "active_rules": len(self.learned_rules),
            "high_confidence_rules": len([r for r in self.learned_rules.values()
                                          if r.confidence >= 0.8]),
            "rules_by_category": self._count_rules_by_category()
        }

    def _count_rules_by_category(self) -> Dict[str, int]:
        """카테고리별 규칙 수"""
        counts = {}
        for rule in self.learned_rules.values():
            counts[rule.category] = counts.get(rule.category, 0) + 1
        return counts

    def get_improvement_report(self) -> str:
        """개선 리포트 생성"""
        stats = self.get_learning_stats()

        report = f"""
=== 능동형 AI 학습 리포트 ===
생성일: {datetime.now().strftime('%Y-%m-%d %H:%M')}

📊 피드백 현황
- 총 피드백: {stats['total_feedbacks']}건
- 긍정 피드백: {stats['positive_feedbacks']}건
- 부정 피드백: {stats['negative_feedbacks']}건
- 수정 피드백: {stats['corrections_count']}건

🧠 학습 현황
- 활성 규칙: {stats['active_rules']}개
- 고신뢰 규칙 (≥80%): {stats['high_confidence_rules']}개
- 새로 생성된 규칙: {stats['rules_generated']}개
- 강화된 규칙: {stats['rules_improved']}개

📈 카테고리별 현황
"""
        for cat, count in stats['rules_by_category'].items():
            report += f"- {cat}: {count}개 규칙\n"

        return report


# 싱글톤 인스턴스
_engine_instance = None

def get_learning_engine() -> ActiveLearningEngine:
    """학습 엔진 싱글톤 반환"""
    global _engine_instance
    if _engine_instance is None:
        _engine_instance = ActiveLearningEngine()
    return _engine_instance
