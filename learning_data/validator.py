"""
텍스트 검증 시스템
PDF 변환 결과의 텍스트 정확도를 검증하고 오류를 탐지

검증 항목:
1. 오자 (Typo): 잘못된 문자
2. 탈자 (Missing): 누락된 문자
3. 첨자 (Extra): 추가된 문자
4. 분리 오류: 한 단어가 잘못 분리됨
5. 병합 오류: 별개 단어가 잘못 합쳐짐
6. 문맥 오류: 문맥에 맞지 않는 단어
7. OCR 특유 오류: 유사 글자 오인식 (ㄹ↔ㅡ, 1↔l↔I, 0↔O 등)
"""

import re
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field
from difflib import SequenceMatcher, unified_diff
import unicodedata


@dataclass
class ValidationError:
    """검증 오류"""
    error_type: str           # typo, missing, extra, split, merge, context, ocr
    original: str             # 원본 텍스트
    converted: str            # 변환된 텍스트
    position: int             # 오류 위치
    suggestion: str           # 수정 제안
    confidence: float         # 오류 확신도 (0~1)
    context: str = ""         # 주변 문맥


@dataclass
class ValidationReport:
    """검증 보고서"""
    total_chars: int
    total_errors: int
    accuracy: float           # 정확도 (0~1)
    errors: List[ValidationError]

    # 오류 유형별 통계
    typo_count: int = 0
    missing_count: int = 0
    extra_count: int = 0
    split_count: int = 0
    merge_count: int = 0
    context_count: int = 0
    ocr_count: int = 0

    def to_dict(self) -> dict:
        return {
            "total_chars": self.total_chars,
            "total_errors": self.total_errors,
            "accuracy": round(self.accuracy, 4),
            "accuracy_percent": f"{self.accuracy * 100:.2f}%",
            "errors": [
                {
                    "type": e.error_type,
                    "original": e.original,
                    "converted": e.converted,
                    "position": e.position,
                    "suggestion": e.suggestion,
                    "confidence": round(e.confidence, 2),
                    "context": e.context
                }
                for e in self.errors
            ],
            "summary": {
                "typo": self.typo_count,
                "missing": self.missing_count,
                "extra": self.extra_count,
                "split": self.split_count,
                "merge": self.merge_count,
                "context": self.context_count,
                "ocr": self.ocr_count
            }
        }


class TextValidator:
    """텍스트 검증기"""

    def __init__(self):
        # OCR 오인식 패턴 (자주 혼동되는 글자들)
        self.ocr_confusion_map = {
            # 한글 유사 글자
            'ㄹ': ['ㅡ', 'ㅜ'],
            'ㅎ': ['ㅗ', 'ㅏ'],
            'ㄱ': ['ㅋ', '7'],
            'ㅁ': ['ㅂ', 'ㅍ'],
            'ㅇ': ['ㅎ', 'O', '0'],
            # 숫자/영문 혼동
            '0': ['O', 'o', 'ㅇ'],
            '1': ['l', 'I', 'ㅣ', '|'],
            '2': ['Z', 'z'],
            '5': ['S', 's'],
            '6': ['b', 'G'],
            '8': ['B', '&'],
            '9': ['g', 'q'],
            # 영문 혼동
            'l': ['1', 'I', '|'],
            'O': ['0', 'o', 'ㅇ'],
            'S': ['5', '$'],
            'B': ['8', '3'],
            'G': ['6', 'C'],
            # 특수문자
            '-': ['ㅡ', '一', '—', '–'],
            '.': ['·', '。', ','],
        }

        # 자주 오인식되는 단어 패턴
        self.common_ocr_errors = {
            '2266': '☎',      # 전화번호 오인식
            '한전': ['한전', '현전', '한젼'],
            '철도': ['철도', '첫도', '철또'],
            '신설': ['신설', '싞설', '신썰'],
            '확보': ['확보', '확뵤', '왁보'],
        }

        # 문맥 검사용 단어 사전
        self.context_patterns = [
            # (잘못된 패턴, 올바른 패턴, 설명)
            (r'(\d{4})년\s*(\d{4})', r'\1년-\2년', '연도 범위'),
            (r'(\d+)\s*억\s*(\d+)\s*원', r'\1억 \2만원', '금액 단위'),
            (r'제(\d+)쪽', r'제\1조', '법률 용어'),
        ]

        # 선거홍보물 특화 용어
        self.election_terms = [
            '국민의힘', '더불어민주당', '정의당', '무소속',
            '공약', '실적', '비전', '약속', '변화', '희망',
            '교육', '복지', '안전', '환경', '경제', '일자리',
            '기호', '후보', '당선', '투표', '선거'
        ]

    def validate(self, original: str, converted: str) -> ValidationReport:
        """
        원본과 변환 텍스트 비교 검증

        Args:
            original: 원본 PDF 텍스트
            converted: 변환된 HTML 텍스트

        Returns:
            ValidationReport
        """
        errors: List[ValidationError] = []

        # 전처리
        orig_clean = self._preprocess(original)
        conv_clean = self._preprocess(converted)

        # 1. 문자 레벨 비교
        char_errors = self._compare_characters(orig_clean, conv_clean)
        errors.extend(char_errors)

        # 2. 단어 레벨 비교
        word_errors = self._compare_words(orig_clean, conv_clean)
        errors.extend(word_errors)

        # 3. OCR 특유 오류 검사
        ocr_errors = self._check_ocr_errors(orig_clean, conv_clean)
        errors.extend(ocr_errors)

        # 4. 문맥 오류 검사
        context_errors = self._check_context_errors(conv_clean)
        errors.extend(context_errors)

        # 중복 제거
        errors = self._deduplicate_errors(errors)

        # 통계 계산
        total_chars = len(orig_clean)
        total_errors = len(errors)
        accuracy = 1.0 - (total_errors / max(total_chars, 1))

        # 유형별 카운트
        report = ValidationReport(
            total_chars=total_chars,
            total_errors=total_errors,
            accuracy=max(0, accuracy),
            errors=errors
        )

        for error in errors:
            if error.error_type == 'typo':
                report.typo_count += 1
            elif error.error_type == 'missing':
                report.missing_count += 1
            elif error.error_type == 'extra':
                report.extra_count += 1
            elif error.error_type == 'split':
                report.split_count += 1
            elif error.error_type == 'merge':
                report.merge_count += 1
            elif error.error_type == 'context':
                report.context_count += 1
            elif error.error_type == 'ocr':
                report.ocr_count += 1

        return report

    def _preprocess(self, text: str) -> str:
        """텍스트 전처리"""
        if not text:
            return ""

        # HTML 태그 제거
        text = re.sub(r'<[^>]+>', '', text)

        # 연속 공백 정리
        text = re.sub(r'\s+', ' ', text)

        # 특수 유니코드 정규화
        text = unicodedata.normalize('NFC', text)

        return text.strip()

    def _compare_characters(self, original: str, converted: str) -> List[ValidationError]:
        """문자 레벨 비교"""
        errors = []
        matcher = SequenceMatcher(None, original, converted)

        for tag, i1, i2, j1, j2 in matcher.get_opcodes():
            if tag == 'replace':
                # 오자
                orig_part = original[i1:i2]
                conv_part = converted[j1:j2]
                context = self._get_context(original, i1, i2)

                errors.append(ValidationError(
                    error_type='typo',
                    original=orig_part,
                    converted=conv_part,
                    position=i1,
                    suggestion=orig_part,
                    confidence=0.9,
                    context=context
                ))

            elif tag == 'delete':
                # 탈자 (원본에 있고 변환에 없음)
                missing = original[i1:i2]
                context = self._get_context(original, i1, i2)

                errors.append(ValidationError(
                    error_type='missing',
                    original=missing,
                    converted='',
                    position=i1,
                    suggestion=f'"{missing}" 추가 필요',
                    confidence=0.95,
                    context=context
                ))

            elif tag == 'insert':
                # 첨자 (원본에 없고 변환에 있음)
                extra = converted[j1:j2]
                context = self._get_context(converted, j1, j2)

                errors.append(ValidationError(
                    error_type='extra',
                    original='',
                    converted=extra,
                    position=j1,
                    suggestion=f'"{extra}" 삭제 필요',
                    confidence=0.85,
                    context=context
                ))

        return errors

    def _compare_words(self, original: str, converted: str) -> List[ValidationError]:
        """단어 레벨 비교"""
        errors = []

        orig_words = original.split()
        conv_words = converted.split()

        matcher = SequenceMatcher(None, orig_words, conv_words)

        for tag, i1, i2, j1, j2 in matcher.get_opcodes():
            if tag == 'replace':
                orig_part = ' '.join(orig_words[i1:i2])
                conv_part = ' '.join(conv_words[j1:j2])

                # 분리 오류 감지: 원본 1단어 → 변환 여러 단어
                if i2 - i1 == 1 and j2 - j1 > 1:
                    errors.append(ValidationError(
                        error_type='split',
                        original=orig_part,
                        converted=conv_part,
                        position=i1,
                        suggestion=f'"{orig_part}"로 병합',
                        confidence=0.85,
                        context=f'원본: {orig_part}'
                    ))

                # 병합 오류 감지: 원본 여러 단어 → 변환 1단어
                elif i2 - i1 > 1 and j2 - j1 == 1:
                    errors.append(ValidationError(
                        error_type='merge',
                        original=orig_part,
                        converted=conv_part,
                        position=i1,
                        suggestion=f'"{orig_part}"로 분리',
                        confidence=0.85,
                        context=f'원본: {orig_part}'
                    ))

        return errors

    def _check_ocr_errors(self, original: str, converted: str) -> List[ValidationError]:
        """OCR 특유 오류 검사"""
        errors = []

        # 알려진 OCR 오류 패턴 검사
        for wrong, correct_list in self.common_ocr_errors.items():
            if wrong in converted and wrong not in original:
                # 오인식된 패턴 발견
                if isinstance(correct_list, str):
                    suggestion = correct_list
                else:
                    suggestion = correct_list[0]

                pos = converted.find(wrong)
                errors.append(ValidationError(
                    error_type='ocr',
                    original='',
                    converted=wrong,
                    position=pos,
                    suggestion=f'"{suggestion}"로 수정',
                    confidence=0.9,
                    context=self._get_context(converted, pos, pos + len(wrong))
                ))

        # 유사 문자 오인식 검사
        for i, (orig_char, conv_char) in enumerate(zip(original, converted)):
            if orig_char != conv_char:
                # 알려진 혼동 쌍인지 확인
                if orig_char in self.ocr_confusion_map:
                    if conv_char in self.ocr_confusion_map[orig_char]:
                        errors.append(ValidationError(
                            error_type='ocr',
                            original=orig_char,
                            converted=conv_char,
                            position=i,
                            suggestion=f'"{orig_char}"로 수정 (OCR 오인식)',
                            confidence=0.95,
                            context=self._get_context(converted, i, i + 1)
                        ))

        return errors

    def _check_context_errors(self, text: str) -> List[ValidationError]:
        """문맥 오류 검사"""
        errors = []

        # 연도 오류 검사 (예: 2266 같은 비정상 연도)
        year_pattern = r'\b(1\d{3}|2\d{3})\b'
        for match in re.finditer(year_pattern, text):
            year = int(match.group())
            if year < 1900 or year > 2100:
                errors.append(ValidationError(
                    error_type='context',
                    original='',
                    converted=str(year),
                    position=match.start(),
                    suggestion='연도가 비정상적입니다. 확인 필요',
                    confidence=0.8,
                    context=self._get_context(text, match.start(), match.end())
                ))

        # 전화번호 형식 검사
        phone_pattern = r'(\d{2,4})[-\s]?(\d{3,4})[-\s]?(\d{4})'
        for match in re.finditer(phone_pattern, text):
            full_number = match.group()
            # 지역번호 검증
            area_code = match.group(1)
            if area_code not in ['02', '031', '032', '033', '041', '042', '043',
                                  '044', '051', '052', '053', '054', '055',
                                  '061', '062', '063', '064', '010', '011',
                                  '016', '017', '018', '019', '070', '080']:
                if len(area_code) <= 4:  # 짧은 번호는 오류일 가능성
                    errors.append(ValidationError(
                        error_type='context',
                        original='',
                        converted=full_number,
                        position=match.start(),
                        suggestion='전화번호 형식 확인 필요',
                        confidence=0.7,
                        context=self._get_context(text, match.start(), match.end())
                    ))

        # 선거 용어 오타 검사
        for term in self.election_terms:
            # 유사하지만 다른 단어 찾기
            similar = self._find_similar_words(text, term)
            for sim_word, sim_pos in similar:
                if sim_word != term:
                    errors.append(ValidationError(
                        error_type='context',
                        original=term,
                        converted=sim_word,
                        position=sim_pos,
                        suggestion=f'"{term}"의 오타일 수 있음',
                        confidence=0.6,
                        context=self._get_context(text, sim_pos, sim_pos + len(sim_word))
                    ))

        return errors

    def _find_similar_words(self, text: str, target: str,
                            threshold: float = 0.7) -> List[Tuple[str, int]]:
        """유사한 단어 찾기"""
        results = []
        words = re.findall(r'[\w가-힣]+', text)

        for i, word in enumerate(words):
            if len(word) < 2:
                continue

            similarity = SequenceMatcher(None, word, target).ratio()
            if threshold < similarity < 1.0:  # 유사하지만 다른 경우
                pos = text.find(word)
                results.append((word, pos))

        return results

    def _get_context(self, text: str, start: int, end: int,
                     context_size: int = 20) -> str:
        """주변 문맥 추출"""
        ctx_start = max(0, start - context_size)
        ctx_end = min(len(text), end + context_size)

        prefix = "..." if ctx_start > 0 else ""
        suffix = "..." if ctx_end < len(text) else ""

        return f"{prefix}{text[ctx_start:ctx_end]}{suffix}"

    def _deduplicate_errors(self, errors: List[ValidationError]) -> List[ValidationError]:
        """중복 오류 제거"""
        seen = set()
        unique = []

        for error in errors:
            key = (error.error_type, error.position, error.original, error.converted)
            if key not in seen:
                seen.add(key)
                unique.append(error)

        return unique

    def get_diff_html(self, original: str, converted: str) -> str:
        """원본과 변환 텍스트의 차이를 HTML로 표시"""
        orig_clean = self._preprocess(original)
        conv_clean = self._preprocess(converted)

        html_parts = []
        matcher = SequenceMatcher(None, orig_clean, conv_clean)

        for tag, i1, i2, j1, j2 in matcher.get_opcodes():
            if tag == 'equal':
                html_parts.append(f'<span class="match">{conv_clean[j1:j2]}</span>')
            elif tag == 'replace':
                html_parts.append(f'<span class="error replace" title="원본: {orig_clean[i1:i2]}">{conv_clean[j1:j2]}</span>')
            elif tag == 'insert':
                html_parts.append(f'<span class="error extra">{conv_clean[j1:j2]}</span>')
            elif tag == 'delete':
                html_parts.append(f'<span class="error missing">[{orig_clean[i1:i2]}]</span>')

        return ''.join(html_parts)


class BatchValidator:
    """대량 검증 처리"""

    def __init__(self):
        self.validator = TextValidator()
        self.results: List[ValidationReport] = []

    def validate_document(self, original_pages: List[str],
                          converted_pages: List[str]) -> Dict:
        """문서 전체 검증"""
        if len(original_pages) != len(converted_pages):
            return {
                "error": "페이지 수 불일치",
                "original_pages": len(original_pages),
                "converted_pages": len(converted_pages)
            }

        page_results = []
        total_errors = 0
        total_chars = 0

        for i, (orig, conv) in enumerate(zip(original_pages, converted_pages)):
            report = self.validator.validate(orig, conv)
            self.results.append(report)

            page_results.append({
                "page": i + 1,
                "accuracy": report.accuracy,
                "errors": len(report.errors),
                "details": report.to_dict()
            })

            total_errors += report.total_errors
            total_chars += report.total_chars

        overall_accuracy = 1.0 - (total_errors / max(total_chars, 1))

        return {
            "total_pages": len(original_pages),
            "total_chars": total_chars,
            "total_errors": total_errors,
            "overall_accuracy": round(overall_accuracy, 4),
            "overall_accuracy_percent": f"{overall_accuracy * 100:.2f}%",
            "pages": page_results,
            "error_summary": self._summarize_errors()
        }

    def _summarize_errors(self) -> Dict:
        """전체 오류 요약"""
        summary = {
            "typo": 0,
            "missing": 0,
            "extra": 0,
            "split": 0,
            "merge": 0,
            "context": 0,
            "ocr": 0
        }

        for report in self.results:
            summary["typo"] += report.typo_count
            summary["missing"] += report.missing_count
            summary["extra"] += report.extra_count
            summary["split"] += report.split_count
            summary["merge"] += report.merge_count
            summary["context"] += report.context_count
            summary["ocr"] += report.ocr_count

        return summary

    def get_critical_errors(self, min_confidence: float = 0.8) -> List[Dict]:
        """높은 확신도의 중요 오류만 추출"""
        critical = []

        for i, report in enumerate(self.results):
            for error in report.errors:
                if error.confidence >= min_confidence:
                    critical.append({
                        "page": i + 1,
                        "type": error.error_type,
                        "original": error.original,
                        "converted": error.converted,
                        "suggestion": error.suggestion,
                        "confidence": error.confidence,
                        "context": error.context
                    })

        # 확신도 높은 순 정렬
        critical.sort(key=lambda x: x["confidence"], reverse=True)
        return critical
