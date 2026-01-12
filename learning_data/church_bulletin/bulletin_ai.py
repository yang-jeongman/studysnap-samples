"""
BulletinAI (주보지기) v4.0 - Vision API 통합
=====================================================

핵심 원칙:
1. PDF를 직접 분석 - Vision API 직접 호출
2. 섹션별 맞춤 프롬프트 - 각 섹션에 최적화된 추출
3. 오류 검증 및 재시도 - 환각/오류 감지 시 재추출
4. 원본 텍스트 보존 - 말줄임표(…) 등 그대로 유지

사용법:
    from learning_data.church_bulletin import get_bulletin_ai

    ai = get_bulletin_ai()
    ai.load_pdf(pdf_bytes)

    # 섹션별 직접 추출
    verse = ai.extract_today_verse()
    services = ai.extract_worship_services()
"""

import os
import io
import base64
import logging
import fitz  # PyMuPDF
from typing import Dict, List, Optional, Any
from datetime import datetime

logger = logging.getLogger(__name__)


class BulletinAI:
    """
    BulletinAI (주보지기) v4.0 - Vision API 통합

    PDF를 직접 분석하여 섹션별 데이터를 추출합니다.
    """

    VERSION = "4.0.0"
    NAME = "BulletinAI"
    NAME_KR = "주보지기"

    # 여의도순복음교회 주보 페이지 구조
    PAGE_STRUCTURE = {
        1: ["church_info", "pastor_greeting"],
        2: ["worship_services", "common_order"],
        3: ["today_verse", "wednesday_service", "friday_service", "saturday_service", "choir"],
        4: ["sermon_word"],
        5: ["church_news"],
        6: ["devotional"],
    }

    # 섹션별 프롬프트
    SECTION_PROMPTS = {
        "today_verse": """이 페이지에서 '오늘의 말씀' 또는 '금주의 말씀' 섹션을 찾아 추출하세요.

**절대 규칙:**
1. PDF에 보이는 성경 말씀을 **글자 그대로** 추출
2. **말줄임표(…)가 있으면 그대로 "…" 출력** - 절대 뒷부분 완성 금지!
3. PDF에 없는 단어/문장 **절대 추가 금지**
4. 성경 본문을 완성하거나 확장하지 마세요!

응답 형식 (JSON):
{
    "text": "PDF에 보이는 말씀 텍스트 그대로 (줄임표 포함)",
    "reference": "성경 구절 (예: 여호수아 1:6~9)"
}""",

        "worship_services": """이 페이지의 예배순서 전체를 추출하세요.

**핵심 규칙 (절대 준수):**
1. **섹션 제목을 PDF에서 그대로 추출** - "성찬예배순", "주일예배순", "송구영신예배순" 등 하드코딩 금지!
2. **영문 제목도 PDF에서 그대로 추출** - "Communion Sunday Worship Service" 등
3. **날짜도 PDF에서 그대로 추출** - "2026. 1. 4." 형식 그대로
4. **예배 순서를 위→아래 순서대로 정확히 추출** - 순서 변경 금지
5. **부별로 다른 정보(찬송, 성경봉독, 설교) 정확히 분리**
6. PDF에 없는 정보는 절대 추측/생성 금지
7. 이전 주보 데이터 재활용 금지 - 오직 현재 PDF에서만 추출

**중요 - 찬송가 번호 추출:**
- 찬송가 번호는 반드시 **"XXX장(통YYY장)"** 형식으로 추출
- 예: "310장(통410장)", "10장(통34장)", "436장(통493장)"
- 통일찬송가 번호(통XXX장)가 PDF에 있으면 반드시 괄호 안에 포함

**추출 대상:**
- 섹션 제목 (예: "성 찬 예 배 순" → "성찬예배순")
- 영문 제목 (예: "Communion Sunday Worship Service")
- 날짜
- 예배 순서 항목 (순서대로): 예배로 부르심, 찬송, 신앙고백, 찬송, 기도, 성경봉독, 찬양, 설교, 기도와 결신, 성찬(있으면), 헌금기도, 찬송, 축도
- 부별 성경봉독 구절
- 부별 설교 제목/설교자
- **부별 찬송가 번호 (통일찬송가 번호 포함)**

응답 형식 (JSON):
{
    "section_title": "PDF에서 추출한 제목 (예: 성찬예배순)",
    "section_title_en": "PDF에서 추출한 영문 제목",
    "date": "PDF에서 추출한 날짜",
    "order_items": [
        {"order": 1, "name_ko": "예배로 부르심", "name_en": "Invocation", "content": "요(John) 4:24", "performer": "사회자"},
        {"order": 2, "name_ko": "찬송", "name_en": "Hymn", "content": "8장(통9장) 4절", "performer": "다같이(일어서서)"},
        {"order": 3, "name_ko": "신앙고백", "name_en": "Confession", "content": "사도신경", "performer": "다같이(일어서서)"},
        {"order": 4, "name_ko": "찬송", "name_en": "Hymn", "content": "부별 다름", "performer": "다같이", "varies_by_service": true},
        {"order": 5, "name_ko": "기도", "name_en": "Prayer", "content": "", "performer": "기도자"},
        {"order": 6, "name_ko": "성경봉독", "name_en": "Scripture Reading", "content": "부별 다름", "performer": "사회자", "varies_by_service": true},
        {"order": 7, "name_ko": "찬양", "name_en": "Anthem", "content": "", "performer": "찬양대"},
        {"order": 8, "name_ko": "설교", "name_en": "Sermon", "content": "부별 다름", "performer": "설교자", "varies_by_service": true, "highlight": true},
        {"order": 9, "name_ko": "기도와 결신", "name_en": "Prayer & Altar-Call", "content": "", "performer": "설교자"},
        {"order": 10, "name_ko": "성찬", "name_en": "Communion", "content": "229장(통281장)", "performer": "다같이"},
        {"order": 11, "name_ko": "헌금기도", "name_en": "Offering Prayer", "content": "", "performer": "기도자"},
        {"order": 12, "name_ko": "찬송", "name_en": "Hymn", "content": "주기도문(635장)", "performer": "다같이(일어서서)"},
        {"order": 13, "name_ko": "축도", "name_en": "Benediction", "content": "", "performer": "설교자"}
    ],
    "services": {
        "1부": {
            "time": "07:00",
            "second_hymn": "310장(통410장)",
            "scripture": "갈(Gal.) 3:1~6",
            "sermon_title": "믿음의 복",
            "sermon_title_en": "The Blessing of Faith",
            "sermon_pastor": "엄태욱 목사"
        },
        "2·3·4부": {
            "time": "09:00, 11:00, 14:00",
            "second_hymn": "10장(통34장)",
            "scripture": "수(Josh.) 1:6~9",
            "sermon_title": "강하고 담대하라",
            "sermon_title_en": "Be Strong and Courageous",
            "sermon_pastor": "이영훈 목사"
        },
        "5부 대학청년": {
            "time": "16:00",
            "second_hymn": "",
            "scripture": "요(John) 6:28~29",
            "sermon_title": "하나님의 일",
            "sermon_title_en": "The Works of God",
            "sermon_pastor": "오수황 목사"
        },
        "주일저녁": {
            "time": "19:30",
            "second_hymn": "436장(통493장)",
            "scripture": "창(Gen.) 26:19~22",
            "sermon_title": "은혜의 우물 곁에 머물라",
            "sermon_title_en": "Stay at the Well of Grace",
            "sermon_pastor": "서광석 목사"
        }
    }
}""",

        "sermon_word": """이 페이지의 '생명의 말씀' (설교) 전체 내용을 **텍스트 누락 없이 완전하게** 추출하세요.

**절대 규칙:**
1. 제목 (한글 + 영문), 본문 구절, 설교자 정확히 추출
2. 서론: 소제목 이전의 도입 문단 전체를 **글자 하나 빠짐없이** 추출
3. 본론: 각 소제목(보통 1., 2., 3. 또는 첫째, 둘째 등으로 구분)과 해당 내용 전체를 **글자 하나 빠짐없이** 추출
4. 각 소제목의 내용은 다음 소제목 시작 전까지의 **모든 문장**을 포함
5. PDF에 없는 내용 추가 금지
6. 말줄임표(…)가 있으면 그대로 유지
7. **텍스트를 요약하거나 줄이지 마세요 - 원문 그대로 전체 추출**

**추출 예시:**
- 서론: "오늘 본문은... (전체 서론 문단)"
- 소제목1: "마음의 골짜기를 메우라" → 내용: "루카복음 3:5에서... (해당 소제목의 전체 내용)"
- 소제목2: "교만의 산을 낮추라" → 내용: "이사야 40:4에서... (해당 소제목의 전체 내용)"

응답 형식 (JSON):
{
    "title": "설교 제목 (한글)",
    "english_title": "영문 제목",
    "scripture": "본문 구절 (예: 누가복음 3:4~6)",
    "author": "설교자 (예: 여의도순복음교회 이영훈 위임목사)",
    "intro": "서론 전체 문단 (소제목 이전의 모든 내용)",
    "points": [
        {"subtitle": "1. 첫 번째 소제목", "content": "해당 소제목의 전체 내용 (모든 문장 포함)"},
        {"subtitle": "2. 두 번째 소제목", "content": "해당 소제목의 전체 내용 (모든 문장 포함)"},
        {"subtitle": "3. 세 번째 소제목", "content": "해당 소제목의 전체 내용 (모든 문장 포함)"}
    ]
}""",

        "devotional": """이 페이지의 '오늘의 양식' 전체 내용을 추출하세요.

**절대 규칙:**
1. 제목과 본문 내용 전체 추출
2. 문단 구분 유지
3. PDF에 없는 내용 추가 금지

응답 형식 (JSON):
{
    "title": "제목",
    "content": "전체 본문 내용",
    "paragraphs": ["문단1", "문단2", ...]
}""",

        "church_news": """이 페이지의 '교회 소식' 전체를 카테고리별로 추출하세요.

**카테고리:**
- worship: 예배 관련 소식
- recruit: 모집 관련 소식
- info: 일반 안내

응답 형식 (JSON):
{
    "worship": [{"title": "제목", "detail": "상세내용"}],
    "recruit": [{"title": "제목", "detail": "상세내용"}],
    "info": [{"title": "제목", "detail": "상세내용"}]
}""",

        "choir": """이 페이지의 '금주의 찬양' 표를 추출하세요.

응답 형식 (JSON):
{
    "headers": ["찬양대", "지휘", "반주", "곡명"],
    "rows": [
        ["1부 찬양대", "지휘자명", "반주자명", "곡명"],
        ...
    ]
}"""
    }

    # OCR 오류 교정 패턴
    OCR_CORRECTIONS = {
        "경하고 담대하라": "강하고 담대하라",
        "경하고담대하라": "강하고 담대하라",
        "그 율법을 다 지켜 행하라": "그 율법을…",
        "율법을 다 지켜 행하라": "율법을…",
    }

    def __init__(self, api_key: Optional[str] = None):
        """
        BulletinAI 초기화

        Args:
            api_key: Anthropic API 키 (없으면 환경변수에서 가져옴)
        """
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        self.client = None
        self.pdf_doc = None
        self.page_images = {}  # 페이지별 base64 이미지 캐시
        self.extracted_data = {}  # 추출된 데이터 캐시

        # Anthropic 클라이언트 초기화
        if self.api_key:
            try:
                import anthropic
                self.client = anthropic.Anthropic(api_key=self.api_key)
                logger.info(f"🤖 {self.NAME} ({self.NAME_KR}) v{self.VERSION} 초기화 완료 [Vision API 통합]")
            except ImportError:
                logger.warning("anthropic 패키지가 설치되지 않았습니다. pip install anthropic")
            except Exception as e:
                logger.error(f"Anthropic 클라이언트 초기화 실패: {e}")
        else:
            logger.warning("API 키가 없습니다. 환경변수 ANTHROPIC_API_KEY를 설정하세요.")

    def load_pdf(self, pdf_bytes: bytes) -> bool:
        """
        PDF 로드 및 페이지별 이미지 추출

        Args:
            pdf_bytes: PDF 파일 바이트

        Returns:
            성공 여부
        """
        try:
            self.pdf_doc = fitz.open(stream=pdf_bytes, filetype="pdf")
            self.page_images = {}
            self.extracted_data = {}

            logger.info(f"[BulletinAI] PDF 로드 완료: {len(self.pdf_doc)} 페이지")

            # 각 페이지를 이미지로 변환
            for page_num in range(len(self.pdf_doc)):
                page = self.pdf_doc[page_num]
                # 고해상도 이미지로 변환 (DPI 150)
                mat = fitz.Matrix(150/72, 150/72)
                pix = page.get_pixmap(matrix=mat)
                img_bytes = pix.tobytes("png")
                self.page_images[page_num + 1] = base64.standard_b64encode(img_bytes).decode("utf-8")

            logger.info(f"[BulletinAI] 페이지 이미지 추출 완료: {len(self.page_images)}개")
            return True

        except Exception as e:
            logger.error(f"[BulletinAI] PDF 로드 실패: {e}")
            return False

    def _call_vision_api(self, page_num: int, prompt: str, retry: int = 0) -> Optional[str]:
        """
        Vision API 호출

        Args:
            page_num: 페이지 번호 (1부터 시작)
            prompt: 추출 프롬프트
            retry: 재시도 횟수

        Returns:
            API 응답 텍스트
        """
        if not self.client:
            logger.error("[BulletinAI] Anthropic 클라이언트가 초기화되지 않았습니다.")
            return None

        if page_num not in self.page_images:
            logger.error(f"[BulletinAI] 페이지 {page_num} 이미지가 없습니다.")
            return None

        try:
            image_data = self.page_images[page_num]

            response = self.client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=4096,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": "image/png",
                                    "data": image_data
                                }
                            },
                            {
                                "type": "text",
                                "text": prompt
                            }
                        ]
                    }
                ]
            )

            result = response.content[0].text
            logger.info(f"[BulletinAI] Vision API 호출 성공 (페이지 {page_num})")
            return result

        except Exception as e:
            logger.error(f"[BulletinAI] Vision API 호출 실패: {e}")
            if retry < 2:
                logger.info(f"[BulletinAI] 재시도 {retry + 1}/2...")
                return self._call_vision_api(page_num, prompt, retry + 1)
            return None

    def _parse_json_response(self, response: str) -> Optional[Dict]:
        """JSON 응답 파싱"""
        import json
        import re

        if not response:
            return None

        try:
            # JSON 블록 추출
            json_match = re.search(r'```json\s*(.*?)\s*```', response, re.DOTALL)
            if json_match:
                return json.loads(json_match.group(1))

            # 직접 JSON 파싱 시도
            # { 로 시작하는 부분 찾기
            start = response.find('{')
            end = response.rfind('}') + 1
            if start >= 0 and end > start:
                return json.loads(response[start:end])

            return None
        except json.JSONDecodeError as e:
            logger.error(f"[BulletinAI] JSON 파싱 실패: {e}")
            return None

    def _correct_ocr_errors(self, text: str) -> str:
        """OCR 오류 및 AI 환각 텍스트 교정"""
        if not text:
            return text
        corrected = text
        for wrong, correct in self.OCR_CORRECTIONS.items():
            if wrong in corrected:
                corrected = corrected.replace(wrong, correct)
                logger.info(f"[BulletinAI] OCR 교정: '{wrong}' → '{correct}'")
        return corrected

    def _validate_verse(self, verse_data: Dict) -> bool:
        """오늘의 말씀 데이터 검증"""
        if not verse_data:
            return False

        text = verse_data.get("text", "")
        reference = verse_data.get("reference", "")

        # 필수 필드 확인
        if not text or not reference:
            return False

        # 환각 패턴 감지
        hallucination_patterns = [
            "다 지켜 행하라",  # AI가 완성하려는 패턴
            "가라사대",  # 구식 표현
        ]
        for pattern in hallucination_patterns:
            if pattern in text:
                logger.warning(f"[BulletinAI] 환각 패턴 감지: '{pattern}'")
                return False

        return True

    # ========== 섹션 추출 메서드 ==========

    def extract_today_verse(self, force: bool = False) -> Dict:
        """
        오늘의 말씀 추출 (3페이지)

        Args:
            force: True면 캐시 무시하고 재추출

        Returns:
            {"text": "말씀 본문", "reference": "성경 구절"}
        """
        cache_key = "today_verse"
        if not force and cache_key in self.extracted_data:
            return self.extracted_data[cache_key]

        result = {"text": "", "reference": ""}

        # Vision API 호출
        response = self._call_vision_api(3, self.SECTION_PROMPTS["today_verse"])
        if response:
            parsed = self._parse_json_response(response)
            if parsed:
                result["text"] = self._correct_ocr_errors(parsed.get("text", ""))
                result["reference"] = parsed.get("reference", "")

                # 검증
                if not self._validate_verse(result):
                    logger.warning("[BulletinAI] 오늘의 말씀 검증 실패, 재시도...")
                    # 더 엄격한 프롬프트로 재시도
                    strict_prompt = self.SECTION_PROMPTS["today_verse"] + """

**추가 경고:**
- "다 지켜 행하라" 같은 표현은 환각입니다. 원본에 "…"가 있으면 반드시 "…"로 끝내세요.
- 원본 PDF를 다시 확인하고 글자 그대로 추출하세요."""

                    response2 = self._call_vision_api(3, strict_prompt)
                    if response2:
                        parsed2 = self._parse_json_response(response2)
                        if parsed2:
                            result["text"] = self._correct_ocr_errors(parsed2.get("text", ""))
                            result["reference"] = parsed2.get("reference", "")

        self.extracted_data[cache_key] = result
        logger.info(f"[BulletinAI] 오늘의 말씀 추출 완료: {result.get('reference', '없음')}")
        return result

    def extract_worship_services(self, force: bool = False) -> Dict:
        """
        예배 순서 추출 (2페이지)

        핵심 규칙:
        1. 섹션 제목은 PDF에서 그대로 추출 (하드코딩 금지)
        2. 예배 순서는 위→아래 순서 정확히 유지
        3. 부별로 다른 정보는 services에 분리 저장
        4. 이전 데이터 재활용 금지

        Returns:
            {
                "section_title": "성찬예배순",
                "section_title_en": "Communion Sunday Worship Service",
                "date": "2026. 1. 4.",
                "order_items": [...],
                "services": {...}
            }
        """
        cache_key = "worship_services"
        if not force and cache_key in self.extracted_data:
            return self.extracted_data[cache_key]

        result = {
            "section_title": "",
            "section_title_en": "",
            "date": "",
            "order_items": [],
            "services": {}
        }

        response = self._call_vision_api(2, self.SECTION_PROMPTS["worship_services"])
        if response:
            parsed = self._parse_json_response(response)
            if parsed:
                # PDF에서 추출한 제목 (하드코딩 금지 원칙)
                result["section_title"] = parsed.get("section_title", "")
                result["section_title_en"] = parsed.get("section_title_en", "")
                result["date"] = parsed.get("date", "")
                result["order_items"] = parsed.get("order_items", [])
                result["services"] = parsed.get("services", {})

                # 제목이 비어있으면 경고
                if not result["section_title"]:
                    logger.warning("[BulletinAI] 섹션 제목 추출 실패 - PDF 원본 확인 필요")

        self.extracted_data[cache_key] = result
        logger.info(f"[BulletinAI] 예배 순서 추출 완료: {result.get('section_title', '제목없음')}, {len(result.get('services', {}))}개 예배")
        return result

    def extract_sermon_word(self, force: bool = False) -> Dict:
        """
        생명의 말씀 추출 (4페이지) + 텍스트 품질 검증

        Returns:
            {"title": "", "scripture": "", "author": "", "intro": "", "points": [...]}
        """
        cache_key = "sermon_word"
        if not force and cache_key in self.extracted_data:
            return self.extracted_data[cache_key]

        result = {"title": "", "english_title": "", "scripture": "", "author": "", "intro": "", "points": []}

        response = self._call_vision_api(4, self.SECTION_PROMPTS["sermon_word"])
        if response:
            parsed = self._parse_json_response(response)
            if parsed:
                result.update(parsed)

                # 텍스트 품질 검증 및 자동 교정
                try:
                    from learning_data.church_bulletin.sermon_text_validator import get_sermon_validator
                    validator = get_sermon_validator()
                    validation_result = validator.validate_sermon_text(result)

                    if validation_result["corrections"]:
                        logger.info(f"[BulletinAI] 생명의 말씀 텍스트 교정: {len(validation_result['corrections'])}건")
                        result = validation_result["corrected_data"]

                    if validation_result["errors"]:
                        logger.warning(f"[BulletinAI] 텍스트 품질 경고: {validation_result['errors']}")

                    logger.info(f"[BulletinAI] 텍스트 품질 점수: {validation_result['score']:.1%}")
                except Exception as e:
                    logger.warning(f"[BulletinAI] 텍스트 검증 실패 (무시): {e}")

        self.extracted_data[cache_key] = result
        logger.info(f"[BulletinAI] 생명의 말씀 추출 완료: {result.get('title', '없음')}")
        return result

    def extract_devotional(self, force: bool = False) -> Dict:
        """
        오늘의 양식 추출 (6페이지)

        Returns:
            {"title": "", "content": "", "paragraphs": [...]}
        """
        cache_key = "devotional"
        if not force and cache_key in self.extracted_data:
            return self.extracted_data[cache_key]

        result = {"title": "", "content": "", "paragraphs": []}

        response = self._call_vision_api(6, self.SECTION_PROMPTS["devotional"])
        if response:
            parsed = self._parse_json_response(response)
            if parsed:
                result.update(parsed)

        self.extracted_data[cache_key] = result
        logger.info(f"[BulletinAI] 오늘의 양식 추출 완료: {result.get('title', '없음')}")
        return result

    def extract_church_news(self, force: bool = False) -> Dict:
        """
        교회 소식 추출 (5페이지)

        Returns:
            {"worship": [...], "recruit": [...], "info": [...]}
        """
        cache_key = "church_news"
        if not force and cache_key in self.extracted_data:
            return self.extracted_data[cache_key]

        result = {"worship": [], "recruit": [], "info": []}

        response = self._call_vision_api(5, self.SECTION_PROMPTS["church_news"])
        if response:
            parsed = self._parse_json_response(response)
            if parsed:
                result.update(parsed)

        self.extracted_data[cache_key] = result
        total = len(result["worship"]) + len(result["recruit"]) + len(result["info"])
        logger.info(f"[BulletinAI] 교회 소식 추출 완료: {total}개")
        return result

    def extract_choir(self, force: bool = False) -> Dict:
        """
        금주의 찬양 추출 (3페이지)

        Returns:
            {"headers": [...], "rows": [...]}
        """
        cache_key = "choir"
        if not force and cache_key in self.extracted_data:
            return self.extracted_data[cache_key]

        result = {"headers": [], "rows": []}

        response = self._call_vision_api(3, self.SECTION_PROMPTS["choir"])
        if response:
            parsed = self._parse_json_response(response)
            if parsed:
                result.update(parsed)

        self.extracted_data[cache_key] = result
        logger.info(f"[BulletinAI] 금주의 찬양 추출 완료: {len(result['rows'])}개")
        return result

    def extract_all(self) -> Dict:
        """
        모든 섹션 추출

        Returns:
            전체 추출 데이터
        """
        logger.info("[BulletinAI] 전체 섹션 추출 시작...")

        return {
            "today_verse": self.extract_today_verse(),
            "worship_services": self.extract_worship_services(),
            "sermon_word": self.extract_sermon_word(),
            "devotional": self.extract_devotional(),
            "church_news": self.extract_church_news(),
            "choir": self.extract_choir(),
        }

    # ========== 하위 호환성 메서드 (v3.0 인터페이스) ==========

    def get_today_verse(self, extracted_data: Optional[Dict] = None) -> Dict:
        """v3.0 호환 - 오늘의 말씀"""
        # 이미 PDF가 로드되어 있으면 직접 추출
        if self.pdf_doc:
            return self.extract_today_verse()

        # 기존 데이터가 있으면 그것 사용 (하위 호환)
        if extracted_data:
            result = {"text": "", "reference": ""}
            structured = extracted_data.get("structured_data", {})
            today_verse = structured.get("today_verse", {})
            if today_verse:
                result["text"] = self._correct_ocr_errors(today_verse.get("text", ""))
                result["reference"] = today_verse.get("reference", "")
            return result

        return {"text": "", "reference": ""}

    def get_worship_services(self, extracted_data: Optional[Dict] = None) -> List[Dict]:
        """v3.0 호환 - 예배 순서"""
        if self.pdf_doc:
            data = self.extract_worship_services()
            return data.get("services", [])

        if extracted_data:
            services = extracted_data.get("worship_services", [])
            if services:
                return services
            structured = extracted_data.get("structured_data", {})
            return structured.get("worship_services", [])

        return []

    def get_sermon_word(self, extracted_data: Optional[Dict] = None) -> Dict:
        """v3.0 호환 - 생명의 말씀 (4페이지 설교 전문)"""
        if self.pdf_doc:
            return self.extract_sermon_word()

        if extracted_data:
            structured = extracted_data.get("structured_data", {})
            # sermon_word 우선, 없으면 sermon 사용
            sermon = structured.get("sermon_word", {}) or structured.get("sermon", {})
            return {
                "title": sermon.get("title", ""),
                "english_title": sermon.get("english_title", "") or sermon.get("title_en", ""),
                "scripture": sermon.get("scripture", ""),
                "author": sermon.get("author", sermon.get("pastor", "")),
                "intro": sermon.get("intro", ""),
                "points": sermon.get("points", []),
                "content": sermon.get("content", "")
            }

        return {"title": "", "english_title": "", "scripture": "", "author": "", "intro": "", "points": [], "content": ""}

    def get_devotional(self, extracted_data: Optional[Dict] = None) -> Dict:
        """v3.0 호환 - 오늘의 양식"""
        if self.pdf_doc:
            return self.extract_devotional()

        if extracted_data:
            structured = extracted_data.get("structured_data", {})
            devotional = structured.get("devotional", {})
            result = {
                "title": devotional.get("title", ""),
                "content": devotional.get("content", ""),
                "paragraphs": []
            }
            if isinstance(result["content"], list):
                result["paragraphs"] = result["content"]
                result["content"] = "\n\n".join(result["content"])
            return result

        return {"title": "", "content": "", "paragraphs": []}

    def get_church_news(self, extracted_data: Optional[Dict] = None) -> Dict:
        """v3.0 호환 - 교회 소식"""
        if self.pdf_doc:
            return self.extract_church_news()

        if extracted_data:
            structured = extracted_data.get("structured_data", {})
            news = structured.get("news", {})
            if isinstance(news, dict):
                return {
                    "worship": news.get("worship", []),
                    "recruit": news.get("recruit", []),
                    "info": news.get("info", [])
                }
            elif isinstance(news, list):
                return {"worship": [], "recruit": [], "info": [{"title": item, "detail": ""} for item in news]}

        return {"worship": [], "recruit": [], "info": []}

    def get_sermon_replay(self, extracted_data: Optional[Dict] = None) -> Dict:
        """v3.0 호환 - 지난 설교 다시듣기"""
        return {"url": "", "title": ""}

    def get_fgtv_radio(self) -> Dict:
        """v3.0 호환 - FGTV 라디오"""
        return {"stream_url": "", "schedule": []}

    # ========== UI 생성 (학습 규칙 기반) ==========

    def _load_ui_rules(self) -> Dict:
        """UI 규칙 파일 로드"""
        import json
        rules_path = os.path.join(os.path.dirname(__file__), "ui_rules.json")
        try:
            with open(rules_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"[BulletinAI] UI 규칙 로드 실패: {e}")
            return {}

    def generate_todays_verse_html(self, verse_data: Dict, theme: Dict) -> str:
        """
        오늘의 말씀 HTML 생성 (학습된 규칙 기반)

        규칙:
        1. 큰 따옴표로 텍스트 감싸기
        2. 좌측 정렬
        3. 성경구절 괄호로 감싸기
        4. 텍스트 하얀색
        5. 아코디언 형식

        Args:
            verse_data: {"text": "말씀", "reference": "수 1:6~9"}
            theme: 테마 설정

        Returns:
            HTML 문자열
        """
        rules = self._load_ui_rules()
        section_rules = rules.get("sections", {}).get("todays_verse", {}).get("rules", {})

        text = verse_data.get("text", "")
        ref = verse_data.get("reference", "")

        if not text:
            return '<p style="color:#999; text-align:center;">내용 없음</p>'

        # 규칙 1: 큰 따옴표로 감싸기
        if section_rules.get("text_format", {}).get("wrap_with_quotes", True):
            quote_char = section_rules.get("text_format", {}).get("quote_char", '"')
            if not text.startswith(quote_char) and not text.startswith('"'):
                text = f'{quote_char}{text}{quote_char}'

        # 규칙 3: 성경구절 괄호로 감싸기
        if section_rules.get("reference_format", {}).get("wrap_with_parentheses", True):
            if ref and not ref.startswith('('):
                ref = f'({ref})'

        # 배경 그라데이션
        bg_gradient = theme.get("header_gradient", "linear-gradient(135deg, #5B4B9E 0%, #4A3D82 100%)")

        html = f'''
            <div class="verse-accordion-card" onclick="toggleVerseAccordion(this)" style="
                background: {bg_gradient};
                border-radius: 16px;
                overflow: hidden;
                box-shadow: 0 4px 20px rgba(91, 75, 158, 0.25);
                cursor: pointer;
                user-select: none;
            ">
                <div class="verse-accordion-header" style="
                    display: flex;
                    align-items: center;
                    justify-content: space-between;
                    padding: 16px 20px;
                    color: white;
                ">
                    <span style="font-size: 1.1em; font-weight: 700;">📖 오늘의 말씀</span>
                    <span style="
                        font-size: 0.95em;
                        font-weight: 600;
                        color: white;
                        background: rgba(255,255,255,0.2);
                        padding: 4px 12px;
                        border-radius: 16px;
                    ">{ref}</span>
                    <span class="verse-accordion-toggle" style="
                        font-size: 0.8em;
                        color: white;
                        opacity: 0.9;
                        transition: transform 0.3s ease;
                    ">▼</span>
                </div>
                <div class="verse-accordion-content" style="
                    max-height: 0;
                    overflow: hidden;
                    transition: max-height 0.4s ease-out, padding 0.3s ease;
                    padding: 0 20px;
                    background: rgba(0,0,0,0.1);
                ">
                    <p style="
                        color: white;
                        font-size: 1.05em;
                        line-height: 1.9;
                        text-align: left;
                        word-break: keep-all;
                        margin: 0;
                        padding: 16px 0;
                    ">{text}</p>
                </div>
            </div>
            <style>
                .verse-accordion-card.expanded .verse-accordion-toggle {{
                    transform: rotate(180deg);
                }}
                .verse-accordion-card.expanded .verse-accordion-content {{
                    max-height: 500px !important;
                    padding: 16px 20px 20px !important;
                }}
            </style>'''

        logger.info(f"[BulletinAI] 오늘의 말씀 HTML 생성 완료: {ref}")
        return html

    def generate_worship_order_html(self, worship_data: Dict, theme: Dict) -> str:
        """
        예배순서 HTML 생성 (PDF 원본 형식 그대로 반영)

        핵심 규칙:
        1. 섹션 제목은 PDF 원본에서 추출 (하드코딩 금지)
        2. 예배 순서는 PDF 원본의 위→아래 순서 정확히 유지
        3. 부별로 다른 정보(찬송, 성경봉독, 설교)는 PDF 형식 그대로 표시
        4. 이전 데이터 재활용 금지 - 항상 현재 PDF에서 추출

        PDF 원본 형식:
        ┌─────────────────────────────────────────────────────────────┐
        │  성 찬 예 배 순                              2026. 1. 4.    │
        │  Communion Sunday Worship Service                           │
        ├─────────────────────────────────────────────────────────────┤
        │ 예배로 부르심 ········· 요(John) 4:24 ········· 사회자      │
        │ 찬송 ·· 1부: 310장, 2·3·4부: 10장, 주일저녁: 436장 · 다같이│
        │ 성경봉독 ············································ 사회자│
        │     1부 갈(Gal.) 3:1~6      2·3·4부 수(Josh.) 1:6~9       │
        │ 설교 ················································ 설교자│
        │     1부 믿음의 복 ························· 엄태욱 목사   │
        │     2·3·4부 강하고 담대하라 ··············· 이영훈 목사   │
        └─────────────────────────────────────────────────────────────┘

        Args:
            worship_data: extract_worship_services() 결과
            theme: 테마 설정

        Returns:
            HTML 문자열
        """
        # PDF에서 추출된 제목 사용 (하드코딩 금지)
        section_title = worship_data.get("section_title", "예배순서")
        section_title_en = worship_data.get("section_title_en", "Worship Service")
        date = worship_data.get("date", "")

        # 예배 순서 항목
        order_items = worship_data.get("order_items", [])

        # 부별 정보
        services = worship_data.get("services", {})

        # 배경 그라데이션
        bg_gradient = theme.get("header_gradient", "linear-gradient(135deg, #5B4B9E 0%, #4A3D82 100%)")
        primary_color = theme.get("primary", "#5B4B9E")

        # 예배 순서 항목 HTML 생성 (PDF 원본 형식)
        order_items_html = ""
        for item in order_items:
            item_name = item.get("name_ko", "")
            item_name_en = item.get("name_en", "")
            content = item.get("content", "")
            performer = item.get("performer", "")
            is_sermon = "설교" in item_name
            is_scripture = "성경봉독" in item_name
            varies_by_service = item.get("varies_by_service", False)

            # 부별로 다른 항목인 경우 (찬송, 성경봉독, 설교)
            if varies_by_service and services:
                # 찬송: 메인 행 + 부별 찬송을 2열 그리드로 표시
                if "찬송" in item_name and "주기도문" not in content:
                    # 메인 행 (내용 비워둠)
                    order_items_html += self._build_order_item_row(
                        item_name, item_name_en, "", performer,
                        is_sermon=False, is_scripture=False, primary_color=primary_color
                    )
                    # 부별 찬송 (좌우 전체 폭 사용, 2열 그리드)
                    hymn_details = self._build_hymn_details(services, primary_color)
                    order_items_html += hymn_details

                # 성경봉독: 메인 행 + 부별 구절을 전체 폭으로 표시
                elif is_scripture:
                    # 메인 행 (내용 비워둠)
                    order_items_html += self._build_order_item_row(
                        item_name, item_name_en, "", performer,
                        is_sermon=False, is_scripture=True, primary_color=primary_color
                    )
                    # 부별 구절 (좌우 전체 폭 사용)
                    scripture_details = self._build_scripture_details(services, primary_color)
                    order_items_html += scripture_details

                # 설교: 메인 행 + 부별 설교 정보를 전체 폭으로 표시
                elif is_sermon:
                    # 메인 행 (내용 비워둠)
                    order_items_html += self._build_order_item_row(
                        item_name, item_name_en, "", performer,
                        is_sermon=True, is_scripture=False, primary_color=primary_color
                    )
                    # 부별 설교 정보 (좌우 전체 폭 사용)
                    sermon_details = self._build_sermon_details(services, primary_color)
                    order_items_html += sermon_details

                else:
                    # 기타 varies_by_service 항목
                    order_items_html += self._build_order_item_row(
                        item_name, item_name_en, content, performer,
                        is_sermon=False, is_scripture=False, primary_color=primary_color
                    )

            else:
                # 일반 항목 (공통)
                order_items_html += self._build_order_item_row(
                    item_name, item_name_en, content, performer,
                    is_sermon=is_sermon, is_scripture=False, primary_color=primary_color
                )

                # 설교 항목 뒤에 부별 설교 상세 정보 추가
                if is_sermon and services:
                    sermon_details = self._build_sermon_details(services, primary_color)
                    order_items_html += sermon_details

        html = f'''
            <div class="worship-order-section" style="
                background: white;
                border-radius: 16px;
                overflow: hidden;
                box-shadow: 0 2px 12px rgba(0,0,0,0.08);
                margin-bottom: 20px;
            ">
                <!-- 헤더: PDF에서 추출된 제목 -->
                <div class="worship-order-header" style="
                    background: {bg_gradient};
                    color: white;
                    padding: 20px;
                    text-align: center;
                    position: relative;
                ">
                    <h2 style="margin: 0; font-size: 1.5em; font-weight: 700; letter-spacing: 8px;">{section_title}</h2>
                    <p style="margin: 8px 0 0; font-size: 0.9em; opacity: 0.9;">{section_title_en}</p>
                    <span style="
                        position: absolute;
                        right: 20px;
                        top: 20px;
                        font-size: 0.9em;
                        opacity: 0.9;
                    ">{date}</span>
                </div>

                <!-- 예배 순서 목록 (PDF 원본 형식) -->
                <div class="worship-order-list" style="padding: 8px 0;">
                    {order_items_html}
                </div>
            </div>
        '''

        logger.info(f"[BulletinAI] 예배순서 HTML 생성 완료: {section_title}")
        return html

    def _build_order_item_row(self, name_ko: str, name_en: str, content: str, performer: str,
                               is_sermon: bool = False, is_scripture: bool = False, primary_color: str = "#5B4B9E") -> str:
        """예배 순서 항목 한 행 생성 (PDF 형식: 항목명 ···· 내용 ···· 담당자)"""
        # 설교/성경봉독 항목은 강조
        bg_style = f"background: rgba(91, 75, 158, 0.06);" if is_sermon else ""
        font_weight = "600" if is_sermon else "500"

        # 점선 구분자 스타일
        dotted_line = "border-bottom: 1px dotted rgba(0,0,0,0.15);"

        return f'''
            <div class="worship-order-item" style="
                display: flex;
                align-items: center;
                padding: 14px 20px;
                {bg_style}
                {dotted_line}
            ">
                <div style="flex: 0 0 120px;">
                    <span style="font-weight: {font_weight}; color: #333; font-size: 1em;">{name_ko}</span>
                    <br><span style="font-size: 0.75em; color: #888;">{name_en}</span>
                </div>
                <div style="flex: 1; text-align: center; color: {primary_color}; font-weight: 500; padding: 0 12px;">
                    {content}
                </div>
                <div style="flex: 0 0 80px; text-align: right; color: #666; font-size: 0.9em;">
                    {performer}
                </div>
            </div>
        '''

    def _build_hymn_details(self, services: Dict, primary_color: str) -> str:
        """
        찬송 부별 상세 (2줄 정렬: 찬송번호 / 통일찬송가 번호)

        형식:
        1부: 310장,    2·3·4부: 10장,    주일저녁: 436장
             (통410장)        (통34장)           (통493장)
        """
        import re

        # 전체 services 데이터 로그
        logger.info(f"[찬송 파싱] services 전체 데이터: {services}")

        hymn_data = []
        for svc_name, svc_data in services.items():
            # svc_data 전체 로그
            logger.info(f"[찬송 파싱] {svc_name} 전체: {svc_data}")
            hymn = svc_data.get("second_hymn", "") or svc_data.get("hymn", "")
            if hymn:
                # 디버그 로그
                logger.info(f"[찬송 파싱] {svc_name}: 원본 = '{hymn}'")

                # 데이터 검증: 찬송가 번호가 포함되어 있는지 확인
                # "장" 또는 "통"이 포함되어야 찬송가로 인식
                if not re.search(r'\d+장|통\d+', hymn):
                    # 찬송가 형식이 아니면 건너뜀 (설교 제목 등 잘못된 데이터 필터링)
                    logger.warning(f"찬송 데이터 형식 오류 (건너뜀): {svc_name} = {hymn}")
                    continue

                # 다양한 형식 지원:
                # "310장(통410장)", "310장 (통410장)", "310장(통 410장)", "310 장 (통 410 장)"
                main_hymn = ""
                tong_hymn = ""

                # 1) 통일찬송가 번호 추출 - 다양한 형식 지원
                # "(통410장)", "(통 410장)", "(통410 장)", "통410장", "통 410 장"
                tong_patterns = [
                    r'\(통\s*(\d+)\s*장\)',      # (통410장), (통 410 장)
                    r'통\s*(\d+)\s*장',           # 통410장, 통 410 장
                    r'\((\d+)\s*통\)',            # (410통) - 비표준 형식
                ]
                for pattern in tong_patterns:
                    tong_match = re.search(pattern, hymn)
                    if tong_match:
                        tong_hymn = f"통{tong_match.group(1)}장"
                        break

                # 2) 메인 찬송가 번호 추출 - 괄호 밖의 숫자+장
                # 괄호 앞 부분에서 찾기
                main_part = re.split(r'\(', hymn)[0]  # 괄호 앞 부분
                main_match = re.search(r'(\d+)\s*장', main_part)
                if main_match:
                    main_hymn = f"{main_match.group(1)}장"
                else:
                    # 전체에서 첫 번째 숫자+장 찾기 (통 제외)
                    fallback_match = re.search(r'(?<!통)(\d+)\s*장', hymn)
                    if fallback_match:
                        main_hymn = f"{fallback_match.group(1)}장"

                if not main_hymn:
                    continue  # 찬송번호를 찾을 수 없으면 건너뜀

                logger.info(f"[찬송 파싱] {svc_name}: main={main_hymn}, tong={tong_hymn}")

                hymn_data.append({
                    "service": svc_name,
                    "main": main_hymn,
                    "tong": f"({tong_hymn})" if tong_hymn else ""
                })

        if not hymn_data:
            return ""

        # 테이블 형식으로 정렬 (모바일 최적화)
        cells_html = ""
        for item in hymn_data:
            cells_html += f'''
                <div style="text-align: center; min-width: 80px;">
                    <div style="white-space: nowrap;">
                        <strong style="color: {primary_color};">{item["service"]}:</strong>
                        <span style="color: #333;">{item["main"]}</span>
                    </div>
                    <div style="color: #888; font-size: 0.85em;">{item["tong"]}</div>
                </div>
            '''

        return f'''
            <div class="hymn-details" style="
                padding: 10px 20px 14px;
                background: rgba(91, 75, 158, 0.03);
                border-bottom: 1px dotted rgba(0,0,0,0.15);
            ">
                <div style="
                    display: flex;
                    flex-wrap: wrap;
                    justify-content: flex-start;
                    gap: 16px 24px;
                    font-size: 0.92em;
                ">
                    {cells_html}
                </div>
            </div>
        '''

    def _build_scripture_details(self, services: Dict, primary_color: str) -> str:
        """
        성경봉독 부별 상세 (좌우 전체 폭 사용, 2열 그리드)

        형식:
        1부 갈(Gal.) 3:1~6              2·3·4부 수(Josh.) 1:6~9
        5부 대학청년 요(John) 6:28~29   주일저녁 창(Gen.) 26:19~22
        """
        scripture_items = []
        for svc_name, svc_data in services.items():
            scripture = svc_data.get("scripture", "")
            if scripture:
                scripture_items.append(f'''
                    <div style="padding: 4px 0;">
                        <strong style="color: {primary_color};">{svc_name}</strong>
                        <span style="color: #333; margin-left: 6px;">{scripture}</span>
                    </div>
                ''')

        if not scripture_items:
            return ""

        return f'''
            <div class="scripture-details" style="
                padding: 10px 20px 14px;
                background: rgba(91, 75, 158, 0.03);
                border-bottom: 1px dotted rgba(0,0,0,0.15);
            ">
                <div style="
                    display: grid;
                    grid-template-columns: repeat(2, 1fr);
                    gap: 4px 24px;
                    font-size: 0.92em;
                ">
                    {"".join(scripture_items)}
                </div>
            </div>
        '''

    def _build_sermon_details(self, services: Dict, primary_color: str) -> str:
        """
        설교 부별 상세 (좌우 전체 폭 사용, 모바일 최적화)

        형식:
        1부 믿음의 복 ················· 엄태욱 목사
        2·3·4부 강하고 담대하라 ······· 이영훈 목사
        """
        sermon_rows = ""
        for svc_name, svc_data in services.items():
            sermon_title = svc_data.get("sermon_title", "")
            sermon_title_en = svc_data.get("sermon_title_en", "")
            # sermon_pastor 또는 preacher 둘 다 지원
            preacher = svc_data.get("sermon_pastor", "") or svc_data.get("preacher", "")

            if sermon_title:
                # 영문 제목이 있으면 표시
                en_part = f'<span style="font-size: 0.8em; color: #888; margin-left: 8px;">({sermon_title_en})</span>' if sermon_title_en else ''

                sermon_rows += f'''
                    <div style="
                        display: flex;
                        flex-wrap: wrap;
                        align-items: baseline;
                        padding: 8px 0;
                        border-bottom: 1px dotted rgba(0,0,0,0.08);
                    ">
                        <span style="font-weight: 600; color: {primary_color}; margin-right: 10px; white-space: nowrap;">{svc_name}</span>
                        <span style="font-weight: 600; color: #333; flex: 1; min-width: 100px;">{sermon_title}{en_part}</span>
                        <span style="color: #555; font-weight: 500; white-space: nowrap;">{preacher}</span>
                    </div>
                '''

        if not sermon_rows:
            return ""

        return f'''
            <div class="sermon-details" style="
                padding: 10px 20px 14px;
                background: rgba(91, 75, 158, 0.04);
            ">
                {sermon_rows}
            </div>
        '''

    # ========== 유틸리티 ==========

    def get_status(self) -> Dict:
        """BulletinAI 상태 반환"""
        return {
            "name": self.NAME,
            "name_kr": self.NAME_KR,
            "version": self.VERSION,
            "status": "ready" if self.client else "no_api_key",
            "pdf_loaded": self.pdf_doc is not None,
            "pages": len(self.page_images) if self.page_images else 0,
            "cached_sections": list(self.extracted_data.keys())
        }


# 싱글톤 인스턴스
_bulletin_ai_instance = None


def get_bulletin_ai(api_key: Optional[str] = None) -> BulletinAI:
    """BulletinAI 싱글톤 인스턴스 반환"""
    global _bulletin_ai_instance
    if _bulletin_ai_instance is None:
        _bulletin_ai_instance = BulletinAI(api_key=api_key)
    return _bulletin_ai_instance


def reset_bulletin_ai():
    """BulletinAI 인스턴스 리셋 (테스트용)"""
    global _bulletin_ai_instance
    _bulletin_ai_instance = None
