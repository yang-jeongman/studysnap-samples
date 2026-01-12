"""
생명의 말씀 텍스트 품질 검증 시스템 (BulletinAI / 주보지기)
===========================================================

4페이지 설교 전문의 텍스트 품질을 검증하고 자동 교정합니다.

검증 항목:
1. 맞춤법 오류 감지
2. OCR 인식 오류 교정 (유사 문자 혼동)
3. 텍스트 누락/중복 감지
4. 할루시네이션(환각) 텍스트 감지
5. 문장 구조 검증

핵심 원칙:
- PDF 원본 텍스트와 비교하여 정확도 검증
- 오류 패턴 학습으로 자동 교정 정확도 향상
- 오류 0(Zero)을 목표로 지속적 개선
"""

import re
import json
import os
import logging
from typing import Dict, List, Tuple, Optional, Any
from datetime import datetime
from pathlib import Path
from difflib import SequenceMatcher

logger = logging.getLogger(__name__)


class SermonTextValidator:
    """생명의 말씀 텍스트 품질 검증기"""

    VERSION = "1.0.0"

    # OCR 자주 혼동되는 문자 패턴
    OCR_CONFUSION_MAP = {
        # 한글 유사 문자
        "오": ["어", "우"],
        "으": ["은", "응"],
        "름": ["릅", "늠"],
        "리": ["라", "러"],
        "하": ["아", "허"],
        "나": ["너", "니"],
        "다": ["디", "드"],
        "가": ["거", "기"],
        "마": ["머", "미"],
        "바": ["버", "비"],
        "사": ["서", "시"],
        "자": ["저", "지"],
        "차": ["처", "치"],
        "카": ["커", "키"],
        "타": ["터", "티"],
        "파": ["퍼", "피"],
        # 숫자/한글 혼동
        "1": ["l", "I", "ㅣ"],
        "0": ["O", "o", "ㅇ"],
        # 특수문자
        "~": ["-", "∼", "〜"],
        ":": ["：", ";"],
        ".": ["。", "·"],
    }

    # 교회 용어 맞춤법 사전 (확장)
    CHURCH_TERMS = {
        # 올바른 표기: [잘못된 표기들]
        # 성경 인물
        "여호수아": ["여호숴", "여호수와", "여호슈아"],
        "이스라엘": ["이스래엘", "이스라앨", "이스라엘"],
        "예루살렘": ["예루샬렘", "예루사렘", "예루살램"],
        "가나안": ["가난안", "가나앙", "카나안"],
        "히브리": ["히브래", "히브루"],
        "모세": ["모새", "모쎄"],
        "아브라함": ["아브라헴", "아부라함"],
        "다윗": ["다위", "다뷧"],
        "솔로몬": ["솔로문", "솔로먼"],
        "베드로": ["베드러", "베드르"],
        "바울": ["바을", "바욼"],
        "세례요한": ["세래요한", "세례요안"],

        # 성경책
        "사도행전": ["사도행젼"],
        "요한복음": ["요안복음", "요한볶음"],
        "마태복음": ["마대복음", "마태볶음"],
        "누가복음": ["누가볶음", "누거복음"],
        "마가복음": ["마가볶음", "마거복음"],
        "창세기": ["창세긔", "창새기"],
        "출애굽기": ["출애굽긔", "출애굽"],
        "로마서": ["로마셔", "로마"],
        "에베소서": ["에베소셔", "에베서"],
        "갈라디아서": ["갈라디아셔", "갈라디아"],
        "빌립보서": ["빌립보셔", "빌립보"],
        "요한계시록": ["요안계시록", "요한계시룩"],

        # 교회 용어
        "성령": ["성녕", "셩령"],
        "축복": ["축볶"],
        "은혜": ["은해", "은헤"],
        "기도": ["기돈", "기드"],
        "말씀": ["말슴", "말씸"],
        "예배": ["예베"],
        "찬양": ["찬얀"],
        "복음": ["볶음"],
        "구원": ["구완"],
        "십자가": ["십자거"],
        "부활": ["부왈"],
        "예수님": ["예수늼"],
        "하나님": ["하난임"],
        "그리스도": ["그리스또"],
        "교만": ["교먼", "교안"],
        "겸손": ["겸손"],
        "회개": ["회개"],
        "사랑": ["사랑"],
        "믿음": ["믿음"],
        "소망": ["소망"],

        # 여의도순복음교회 관련
        "여의도순복음교회": ["여의도순볶음교회", "여이도순복음교회"],
        "이영훈": ["이영훈"],
        "위임목사": ["위임북사", "위임몪사"],
        "담임목사": ["담임북사", "담임몪사"],
    }

    # 자주 발생하는 OCR 오류 단어 교정
    OCR_WORD_CORRECTIONS = {
        # 조사/어미 오류
        "롤": "를",
        "윌": "을",
        "은혜롤": "은혜를",
        "말씀윌": "말씀을",
        "겋": "것",
        "잆는": "있는",
        "읺는": "있는",
        "핰다": "한다",
        "합니디": "합니다",
        "있습니디": "있습니다",
        "됩니디": "됩니다",
        "입니디": "입니다",
        "습니디": "습니다",
        "겂니다": "것입니다",
        "겄입니다": "것입니다",
        "갔습니다": "갔습니다",
        "햇습니다": "했습니다",
        "해야합니다": "해야 합니다",
        "하겟습니다": "하겠습니다",

        # 띄어쓰기 오류
        "우리는": "우리는",
        "그러므로": "그러므로",
        "그러나": "그러나",
        "그래서": "그래서",
        "하나님은": "하나님은",
        "예수님은": "예수님은",
        "성령님은": "성령님은",

        # 일반적인 OCR 오류
        "오넘": "오늘",
        "우리늘": "우리를",
        "하십니다": "하십니다",
        "주십시오": "주십시오",
        "아멘": "아멘",
    }

    # 자주 나오는 성경 표현 패턴
    BIBLE_EXPRESSION_PATTERNS = [
        r"[가-힣]+복음\s*\d+[:\s]\d+",  # 누가복음 3:4
        r"[가-힣]+서\s*\d+[:\s]\d+",     # 로마서 8:28
        r"시편\s*\d+[:\s]\d+",            # 시편 23:1
        r"잠언\s*\d+[:\s]\d+",            # 잠언 3:5
    ]

    # 할루시네이션 감지 패턴 (PDF에 없는 내용이 추가되는 경우)
    HALLUCINATION_INDICATORS = [
        r"또한.*말씀하셨습니다",  # 추가적인 말씀 날조
        r"그러므로.*결론적으로",  # 과도한 결론 추가
        r"이처럼.*우리는",        # 원본에 없는 적용 추가
        r"정리하자면",            # AI가 추가하는 요약
        r"요약하면",              # AI가 추가하는 요약
        r"다시 말해",             # AI 설명 추가
        r"즉[,\s]",              # AI 설명 추가
        r"결국[,\s]",            # AI 결론 추가
    ]

    # 의심스러운 AI 생성 패턴 (할루시네이션 가능성)
    AI_GENERATION_PATTERNS = [
        r"첫째로.*둘째로.*셋째로",  # 원본에 없는 구조화
        r"\.{3,}",                  # 과도한 말줄임표
        r"\([가-힣]{10,}\)",        # 과도하게 긴 괄호 내용
        r"[!]{2,}",                 # 과도한 느낌표
    ]

    # 텍스트 길이 제한 (페이지당 예상 글자수)
    MAX_POINT_CONTENT_LENGTH = 2000  # 한 소제목당 최대 글자수
    MIN_POINT_CONTENT_LENGTH = 50    # 한 소제목당 최소 글자수

    def __init__(self, learning_data_path: str = None):
        """
        Args:
            learning_data_path: 학습 데이터 저장 경로
        """
        if learning_data_path is None:
            learning_data_path = os.path.join(
                os.path.dirname(__file__), "sermon_corrections.json"
            )
        self.learning_data_path = learning_data_path
        self.corrections_log = self._load_corrections_log()
        self.error_patterns = self._load_error_patterns()

    def _load_corrections_log(self) -> Dict:
        """학습된 교정 기록 로드"""
        if os.path.exists(self.learning_data_path):
            try:
                with open(self.learning_data_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"교정 기록 로드 실패: {e}")
        return {"corrections": [], "patterns": {}, "version": self.VERSION}

    def _load_error_patterns(self) -> Dict:
        """학습된 오류 패턴 로드"""
        return self.corrections_log.get("patterns", {})

    def _save_corrections_log(self):
        """교정 기록 저장"""
        try:
            with open(self.learning_data_path, "w", encoding="utf-8") as f:
                json.dump(self.corrections_log, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"교정 기록 저장 실패: {e}")

    def validate_sermon_text(self, extracted_data: Dict, pdf_original_text: str = None) -> Dict:
        """
        생명의 말씀 텍스트 품질 검증

        Args:
            extracted_data: Vision API에서 추출된 sermon_word 데이터
            pdf_original_text: PDF 원본 텍스트 (비교용)

        Returns:
            {
                "is_valid": bool,
                "score": float (0.0 ~ 1.0),
                "errors": [...],
                "corrections": [...],
                "corrected_data": {...}
            }
        """
        errors = []
        corrections = []
        corrected_data = extracted_data.copy()

        # 1. 기본 필드 검증
        title = extracted_data.get("title", "")
        intro = extracted_data.get("intro", "")
        points = extracted_data.get("points", [])
        author = extracted_data.get("author", "")

        # 2. 제목 검증
        title_errors = self._validate_title(title)
        errors.extend(title_errors)

        # 3. 서론 검증
        intro_result = self._validate_and_correct_text(intro, "intro")
        if intro_result["errors"]:
            errors.extend(intro_result["errors"])
        if intro_result["corrected"] != intro:
            corrections.append({
                "field": "intro",
                "original": intro,
                "corrected": intro_result["corrected"]
            })
            corrected_data["intro"] = intro_result["corrected"]

        # 4. 소제목별 내용 검증
        corrected_points = []
        for i, point in enumerate(points):
            subtitle = point.get("subtitle", "")
            content = point.get("content", "")

            # 소제목 검증
            subtitle_result = self._validate_and_correct_text(subtitle, "subtitle")
            # 내용 검증
            content_result = self._validate_and_correct_text(content, "content")

            if subtitle_result["errors"]:
                errors.extend([f"Point {i+1} subtitle: {e}" for e in subtitle_result["errors"]])
            if content_result["errors"]:
                errors.extend([f"Point {i+1} content: {e}" for e in content_result["errors"]])

            corrected_subtitle = subtitle_result["corrected"]
            corrected_content = content_result["corrected"]

            if corrected_subtitle != subtitle or corrected_content != content:
                corrections.append({
                    "field": f"points[{i}]",
                    "original_subtitle": subtitle,
                    "corrected_subtitle": corrected_subtitle,
                    "original_content": content,
                    "corrected_content": corrected_content
                })

            corrected_points.append({
                "subtitle": corrected_subtitle,
                "content": corrected_content
            })

        corrected_data["points"] = corrected_points

        # 5. 설교자 검증
        author_result = self._validate_author(author)
        if author_result["errors"]:
            errors.extend(author_result["errors"])
        if author_result.get("corrected"):
            corrected_data["author"] = author_result["corrected"]
            corrections.append({
                "field": "author",
                "original": author,
                "corrected": author_result["corrected"]
            })

        # 6. PDF 원본과 비교 (제공된 경우)
        if pdf_original_text:
            similarity_result = self._compare_with_original(corrected_data, pdf_original_text)
            errors.extend(similarity_result.get("errors", []))

        # 7. 할루시네이션 검증
        hallucination_errors = self._detect_hallucination(corrected_data, pdf_original_text)
        errors.extend(hallucination_errors)

        # 점수 계산
        total_fields = 1 + 1 + len(points) * 2 + 1  # title + intro + points*2 + author
        error_count = len(errors)
        score = max(0.0, 1.0 - (error_count / total_fields * 0.5))

        # 교정 기록 저장 (학습용)
        if corrections:
            self._log_corrections(corrections)

        return {
            "is_valid": len(errors) == 0,
            "score": score,
            "errors": errors,
            "corrections": corrections,
            "corrected_data": corrected_data
        }

    def _validate_title(self, title: str) -> List[str]:
        """제목 검증"""
        errors = []
        if not title:
            errors.append("제목이 비어있습니다")
        elif len(title) < 2:
            errors.append("제목이 너무 짧습니다")
        elif len(title) > 100:
            errors.append("제목이 너무 깁니다 (100자 초과)")
        return errors

    def _validate_and_correct_text(self, text: str, field_type: str) -> Dict:
        """텍스트 검증 및 교정"""
        errors = []
        corrected = text

        if not text:
            return {"errors": [], "corrected": ""}

        # 1. OCR 오류 교정
        corrected = self._correct_ocr_errors(corrected)

        # 2. 맞춤법 교정 (교회 용어)
        corrected = self._correct_church_terms(corrected)

        # 3. 공백 정규화
        corrected = self._normalize_whitespace(corrected)

        # 4. 문장 구조 검증
        structure_errors = self._check_sentence_structure(corrected)
        errors.extend(structure_errors)

        # 5. 특수문자 정규화
        corrected = self._normalize_special_chars(corrected)

        # 6. 학습된 패턴 적용
        corrected = self._apply_learned_patterns(corrected)

        return {"errors": errors, "corrected": corrected}

    def _correct_ocr_errors(self, text: str) -> str:
        """OCR 오류 교정"""
        corrected = text

        # 1. OCR 단어 교정 사전 적용 (정확한 단어 매칭)
        for wrong, right in self.OCR_WORD_CORRECTIONS.items():
            if wrong in corrected:
                corrected = corrected.replace(wrong, right)
                logger.debug(f"OCR 단어 교정: {wrong} → {right}")

        # 2. 학습된 OCR 오류 패턴 적용
        for wrong, right in self.error_patterns.get("ocr", {}).items():
            if wrong in corrected:
                corrected = corrected.replace(wrong, right)
                logger.debug(f"학습된 OCR 교정: {wrong} → {right}")

        # 3. 연속된 동일 문자 제거 (OCR 오류로 인한 중복)
        # 예: "하하나님" → "하나님" (중복 제거)
        corrected = re.sub(r'(.)\1{2,}', r'\1\1', corrected)

        return corrected

    def _correct_church_terms(self, text: str) -> str:
        """교회 용어 맞춤법 교정"""
        corrected = text

        for correct_term, wrong_terms in self.CHURCH_TERMS.items():
            for wrong in wrong_terms:
                if wrong != correct_term and wrong in corrected:
                    corrected = corrected.replace(wrong, correct_term)
                    logger.info(f"교회 용어 교정: {wrong} → {correct_term}")

        return corrected

    def _normalize_whitespace(self, text: str) -> str:
        """공백 정규화"""
        # 연속 공백 제거
        text = re.sub(r'\s+', ' ', text)
        # 앞뒤 공백 제거
        text = text.strip()
        return text

    def _check_sentence_structure(self, text: str) -> List[str]:
        """문장 구조 검증"""
        errors = []

        # 불완전한 문장 감지
        if text and not re.search(r'[.!?。]$', text.strip()):
            # 마지막 문장이 마침표로 끝나지 않음
            pass  # 설교 텍스트에서는 허용

        # 괄호 짝 검증
        open_parens = text.count('(') + text.count('（')
        close_parens = text.count(')') + text.count('）')
        if open_parens != close_parens:
            errors.append(f"괄호 짝이 맞지 않습니다 (열림: {open_parens}, 닫힘: {close_parens})")

        # 따옴표 짝 검증
        quotes = text.count('"') + text.count('"') + text.count('"')
        if quotes % 2 != 0:
            errors.append("따옴표 짝이 맞지 않습니다")

        return errors

    def _normalize_special_chars(self, text: str) -> str:
        """특수문자 정규화"""
        # 전각 → 반각
        replacements = {
            '：': ':',
            '；': ';',
            '，': ',',
            '。': '.',
            '？': '?',
            '！': '!',
            '（': '(',
            '）': ')',
            '～': '~',
            '"': '"',
            '"': '"',
            ''': "'",
            ''': "'",
        }
        for old, new in replacements.items():
            text = text.replace(old, new)
        return text

    def _apply_learned_patterns(self, text: str) -> str:
        """학습된 교정 패턴 적용"""
        for pattern, replacement in self.error_patterns.get("learned", {}).items():
            text = text.replace(pattern, replacement)
        return text

    def _validate_author(self, author: str) -> Dict:
        """설교자 검증"""
        errors = []
        corrected = author

        if not author:
            return {"errors": [], "corrected": ""}

        # "OOO 목사" 패턴 검증
        if not re.search(r'[가-힣]{2,4}\s*(목사|위임목사|담임목사|전도사)', author):
            errors.append(f"설교자 형식 오류: {author}")

        # 여의도순복음교회 설교자 이름 교정
        known_pastors = {
            "이영훈 목사": ["이영훈목사", "이영 훈 목사"],
            "이영훈 위임목사": ["이영훈위임목사", "이영 훈 위임목사"],
            "엄태욱 목사": ["엄태욱목사", "엄태 욱 목사"],
            "오수황 목사": ["오수황목사", "오수 황 목사"],
            "서광석 목사": ["서광석목사", "서광 석 목사"],
        }

        for correct, wrongs in known_pastors.items():
            for wrong in wrongs:
                if wrong in author:
                    corrected = author.replace(wrong, correct)
                    break

        return {"errors": errors, "corrected": corrected if corrected != author else None}

    def _compare_with_original(self, extracted_data: Dict, pdf_original: str) -> Dict:
        """PDF 원본과 비교"""
        errors = []

        # 추출된 전체 텍스트 조합
        extracted_text = ""
        extracted_text += extracted_data.get("title", "") + " "
        extracted_text += extracted_data.get("intro", "") + " "
        for point in extracted_data.get("points", []):
            extracted_text += point.get("subtitle", "") + " "
            extracted_text += point.get("content", "") + " "

        # 유사도 계산
        similarity = SequenceMatcher(None, extracted_text.lower(), pdf_original.lower()).ratio()

        if similarity < 0.7:
            errors.append(f"PDF 원본과 유사도가 낮습니다 ({similarity:.1%})")

        return {"errors": errors, "similarity": similarity}

    def _detect_hallucination(self, extracted_data: Dict, pdf_original: str = None) -> List[str]:
        """할루시네이션(환각) 텍스트 감지 - 강화된 버전"""
        errors = []

        full_text = ""
        full_text += extracted_data.get("intro", "") + " "
        points = extracted_data.get("points", [])
        for point in points:
            full_text += point.get("content", "") + " "

        # 1. 할루시네이션 패턴 검사
        for pattern in self.HALLUCINATION_INDICATORS:
            if re.search(pattern, full_text):
                if pdf_original:
                    if not re.search(pattern, pdf_original):
                        errors.append(f"할루시네이션 의심: 패턴 '{pattern}' 감지 (원본에 없음)")
                else:
                    # 원본 없이도 의심 패턴 경고
                    logger.warning(f"할루시네이션 가능성: 패턴 '{pattern}' 감지")

        # 2. AI 생성 패턴 검사
        for pattern in self.AI_GENERATION_PATTERNS:
            if re.search(pattern, full_text):
                errors.append(f"AI 생성 의심: 패턴 '{pattern}' 감지")

        # 3. 콘텐츠 길이 검증 (너무 길거나 너무 짧은 경우)
        for i, point in enumerate(points):
            content = point.get("content", "")
            content_len = len(content)
            if content_len > self.MAX_POINT_CONTENT_LENGTH:
                errors.append(f"Point {i+1}: 내용이 너무 깁니다 ({content_len}자 > {self.MAX_POINT_CONTENT_LENGTH}자)")
            elif content_len < self.MIN_POINT_CONTENT_LENGTH and content:
                errors.append(f"Point {i+1}: 내용이 너무 짧습니다 ({content_len}자 < {self.MIN_POINT_CONTENT_LENGTH}자)")

        # 4. 반복 문장 감지 (복사-붙여넣기 오류)
        sentences = re.split(r'[.!?。]', full_text)
        sentence_counts = {}
        for sentence in sentences:
            sentence = sentence.strip()
            if len(sentence) > 20:  # 짧은 문장은 무시
                sentence_counts[sentence] = sentence_counts.get(sentence, 0) + 1

        for sentence, count in sentence_counts.items():
            if count >= 2:
                errors.append(f"반복 문장 감지: '{sentence[:30]}...' ({count}회 반복)")

        # 5. PDF 원본과 비교 (제공된 경우)
        if pdf_original:
            # 원본에 없는 긴 문장 찾기
            for sentence in sentences:
                sentence = sentence.strip()
                if len(sentence) > 30 and sentence not in pdf_original:
                    # 유사도 체크
                    similarity = SequenceMatcher(None, sentence.lower(), pdf_original.lower()).ratio()
                    if similarity < 0.3:
                        errors.append(f"원본에 없는 문장: '{sentence[:50]}...'")

        return errors

    def _log_corrections(self, corrections: List[Dict]):
        """교정 기록 저장 (학습용)"""
        self.corrections_log["corrections"].append({
            "timestamp": datetime.now().isoformat(),
            "corrections": corrections
        })

        # 패턴 학습
        for correction in corrections:
            if "original" in correction and "corrected" in correction:
                original = correction["original"]
                corrected = correction["corrected"]
                if original and corrected and original != corrected:
                    if "learned" not in self.corrections_log["patterns"]:
                        self.corrections_log["patterns"]["learned"] = {}
                    self.corrections_log["patterns"]["learned"][original] = corrected

        self._save_corrections_log()
        logger.info(f"교정 기록 저장 완료: {len(corrections)}건")

    def learn_from_manual_correction(self, original: str, corrected: str, field_type: str = "content"):
        """
        수동 교정에서 학습

        Args:
            original: 원본 텍스트
            corrected: 수정된 텍스트
            field_type: 필드 유형 (title, intro, content, author)
        """
        if original == corrected:
            return

        # 차이점 분석
        sm = SequenceMatcher(None, original, corrected)
        for tag, i1, i2, j1, j2 in sm.get_opcodes():
            if tag == 'replace':
                wrong = original[i1:i2]
                right = corrected[j1:j2]
                if len(wrong) <= 10 and len(right) <= 10:  # 짧은 교정만 학습
                    if "learned" not in self.corrections_log["patterns"]:
                        self.corrections_log["patterns"]["learned"] = {}
                    self.corrections_log["patterns"]["learned"][wrong] = right
                    logger.info(f"패턴 학습: '{wrong}' → '{right}'")

        self._save_corrections_log()


# 전역 인스턴스
_sermon_validator = None

def get_sermon_validator() -> SermonTextValidator:
    """싱글톤 인스턴스 반환"""
    global _sermon_validator
    if _sermon_validator is None:
        _sermon_validator = SermonTextValidator()
    return _sermon_validator


def validate_and_correct_sermon(extracted_data: Dict, pdf_original_text: str = None) -> Dict:
    """
    생명의 말씀 텍스트 검증 및 교정 (편의 함수)

    Args:
        extracted_data: Vision API에서 추출된 sermon_word 데이터
        pdf_original_text: PDF 원본 텍스트 (선택)

    Returns:
        교정된 데이터와 검증 결과
    """
    validator = get_sermon_validator()
    result = validator.validate_sermon_text(extracted_data, pdf_original_text)

    # 로깅
    if result["corrections"]:
        logger.info(f"[SermonValidator] 텍스트 교정 완료: {len(result['corrections'])}건")
    if result["errors"]:
        logger.warning(f"[SermonValidator] 품질 경고: {result['errors']}")

    logger.info(f"[SermonValidator] 품질 점수: {result['score']:.1%} (유효: {result['is_valid']})")

    return result


def learn_correction(original: str, corrected: str, field_type: str = "content"):
    """
    수동 교정에서 학습 (편의 함수)

    Args:
        original: 원본 텍스트
        corrected: 수정된 텍스트
        field_type: 필드 유형
    """
    validator = get_sermon_validator()
    validator.learn_from_manual_correction(original, corrected, field_type)


def get_validation_stats() -> Dict:
    """검증 통계 반환"""
    validator = get_sermon_validator()
    corrections_log = validator.corrections_log

    total_corrections = len(corrections_log.get("corrections", []))
    learned_patterns = len(corrections_log.get("patterns", {}).get("learned", {}))

    return {
        "total_corrections": total_corrections,
        "learned_patterns": learned_patterns,
        "version": validator.VERSION,
        "church_terms_count": len(validator.CHURCH_TERMS),
        "ocr_corrections_count": len(validator.OCR_WORD_CORRECTIONS)
    }
