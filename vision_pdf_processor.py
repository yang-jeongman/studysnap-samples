"""
Claude Vision 기반 PDF 처리 엔진
과거 프로젝트의 vision_content_detector + advanced_pdf_analyzer 통합 및 개선
"""

import logging
import anthropic
import base64
import json
from typing import Dict, List, Any, Optional, Tuple
from PIL import Image
import io
from pathlib import Path

logger = logging.getLogger(__name__)


class VisionPDFProcessor:
    """Claude Vision을 사용한 고급 PDF 처리"""

    def __init__(self, api_key: str):
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = "claude-sonnet-4-20250514"  # 최신 모델 사용

    def encode_image_to_base64(
        self,
        image_path: str,
        max_size_mb: float = 4.5
    ) -> Tuple[str, int, int, str]:
        """
        이미지를 base64로 인코딩 (5MB 제한)

        Args:
            image_path: 이미지 파일 경로
            max_size_mb: 최대 크기 (MB)

        Returns:
            (base64_string, width, height, media_type)
        """
        img = Image.open(image_path)

        # RGB 변환 (JPEG는 RGBA 미지원)
        if img.mode in ('RGBA', 'LA', 'P'):
            background = Image.new('RGB', img.size, (255, 255, 255))
            if img.mode == 'P':
                img = img.convert('RGBA')
            background.paste(img, mask=img.split()[-1] if img.mode in ('RGBA', 'LA') else None)
            img = background
        elif img.mode != 'RGB':
            img = img.convert('RGB')

        original_width, original_height = img.size

        # JPEG 변환 및 크기 확인
        buffer = io.BytesIO()
        img.save(buffer, format='JPEG', quality=95, optimize=True)
        buffer.seek(0)
        size_mb = len(buffer.getvalue()) / (1024 * 1024)

        logger.info(f"원본 이미지: {original_width}x{original_height}px, {size_mb:.2f}MB")

        # 최대 크기 초과 시 리사이즈
        if size_mb > max_size_mb:
            scale = (max_size_mb / size_mb) ** 0.5
            new_width = int(original_width * scale)
            new_height = int(original_height * scale)

            logger.info(f"리사이즈: {new_width}x{new_height}px")

            img_resized = img.resize((new_width, new_height), Image.Resampling.LANCZOS)

            buffer = io.BytesIO()
            img_resized.save(buffer, format='JPEG', quality=95, optimize=True)
            buffer.seek(0)

            new_size_mb = len(buffer.getvalue()) / (1024 * 1024)
            logger.info(f"리사이즈 완료: {new_width}x{new_height}px, {new_size_mb:.2f}MB")

            return base64.standard_b64encode(buffer.getvalue()).decode('utf-8'), new_width, new_height, 'image/jpeg'
        else:
            logger.info("리사이즈 불필요")
            buffer.seek(0)
            return base64.standard_b64encode(buffer.getvalue()).decode('utf-8'), original_width, original_height, 'image/jpeg'

    def detect_content_blocks(
        self,
        image_path: str,
        content_type: str = "general"
    ) -> Dict[str, Any]:
        """
        Claude Vision으로 콘텐츠 블록 자동 감지

        Args:
            image_path: 이미지 경로
            content_type: 문서 타입 (election, newsletter, resume, etc.)

        Returns:
            감지된 콘텐츠 블록 정보
        """
        logger.info(f"Vision 콘텐츠 블록 감지 시작: {image_path}")

        # 이미지 인코딩
        image_data, width, height, media_type = self.encode_image_to_base64(image_path)

        # 콘텐츠 타입별 프롬프트
        if content_type == "election":
            prompt = self._get_election_analysis_prompt(width, height)
        elif content_type == "newsletter":
            prompt = self._get_newsletter_analysis_prompt(width, height)
        else:
            prompt = self._get_general_analysis_prompt(width, height)

        # Claude Vision API 호출
        logger.info("Claude Vision 분석 중...")

        message = self.client.messages.create(
            model=self.model,
            max_tokens=4096,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": media_type,
                                "data": image_data,
                            },
                        },
                        {
                            "type": "text",
                            "text": prompt
                        }
                    ],
                }
            ],
        )

        # 응답 파싱
        response_text = message.content[0].text

        logger.debug(f"Vision 응답:\n{response_text}")

        # JSON 추출
        json_text = self._extract_json(response_text)

        try:
            result = json.loads(json_text)
            logger.info(f"블록 감지 완료: {result.get('total_blocks', 0)}개")
            return result
        except json.JSONDecodeError as e:
            logger.error(f"JSON 파싱 실패: {e}")
            logger.error(f"원본 응답:\n{response_text}")
            return {"error": "JSON parsing failed", "raw_response": response_text}

    def _get_election_analysis_prompt(self, width: int, height: int) -> str:
        """선거 공보물 분석 프롬프트"""
        return f"""이 선거 공보물 이미지를 분석하여 JSON 형식으로 반환하세요 (크기: {width}x{height}px).

**분석 항목:**

1. **후보자 프로필 영역**
   - 이름, 정당, 기호, 사진 위치
   - 배경색, 레이아웃

2. **핵심 공약 영역**
   - 각 공약의 제목, 설명, 아이콘/이미지
   - 배치 (세로/가로), 강조 스타일

3. **경력/실적 영역**
   - 항목 리스트, 시간순 배치 여부

4. **연락처/SNS 영역**
   - QR코드, 전화번호, 주소 등

**JSON 형식:**
```json
{{
  "content_type": "election",
  "page_size": {{"width": {width}, "height": {height}}},
  "profile_section": {{
    "position": {{"x": 0, "y": 0, "width": 0, "height": 0}},
    "candidate_name": "이름",
    "party": "정당",
    "number": "기호",
    "confidence": 0.95
  }},
  "pledge_sections": [
    {{
      "id": 1,
      "title": "공약 제목",
      "description": "공약 설명",
      "position": {{"x": 0, "y": 0, "width": 0, "height": 0}},
      "icon_position": {{"x": 0, "y": 0, "width": 0, "height": 0}},
      "confidence": 0.9
    }}
  ],
  "career_section": {{
    "position": {{"x": 0, "y": 0, "width": 0, "height": 0}},
    "items": ["경력1", "경력2"],
    "confidence": 0.85
  }},
  "contact_section": {{
    "position": {{"x": 0, "y": 0, "width": 0, "height": 0}},
    "phone": "전화번호",
    "address": "주소",
    "confidence": 0.8
  }},
  "layout_description": "전체 레이아웃 설명",
  "total_blocks": 10
}}
```

**중요:** 정확한 픽셀 좌표를 제공하고 JSON만 출력하세요."""

    def _get_newsletter_analysis_prompt(self, width: int, height: int) -> str:
        """뉴스레터 분석 프롬프트"""
        return f"""이 뉴스레터 페이지를 분석하여 JSON 형식으로 반환하세요 (크기: {width}x{height}px).

**분석 항목:**

1. **콘텐츠 블록 식별**
   - 독립적인 기사/섹션 단위
   - 제목, 본문, 이미지 포함 여부

2. **레이아웃 구조**
   - 좌/우 분할, 상/하 분할 여부
   - 컬럼 개수, 배치 방식

3. **시각적 계층**
   - 메인 콘텐츠 vs 부가 콘텐츠
   - 강조 영역 (배경색, 테두리 등)

**JSON 형식:**
```json
{{
  "content_type": "newsletter",
  "page_size": {{"width": {width}, "height": {height}}},
  "layout_type": "single_column|two_column|mixed",
  "content_blocks": [
    {{
      "id": 1,
      "title": "블록 제목",
      "description": "내용 요약",
      "type": "article|calendar|event|ad",
      "position": {{"x": 0, "y": 0, "width": 0, "height": 0}},
      "has_image": true,
      "image_position": {{"x": 0, "y": 0, "width": 0, "height": 0}},
      "emphasis_level": "high|medium|low",
      "confidence": 0.9
    }}
  ]],
  "total_blocks": 5
}}
```

**중요:** 정확한 픽셀 좌표를 제공하고 JSON만 출력하세요."""

    def _get_general_analysis_prompt(self, width: int, height: int) -> str:
        """일반 문서 분석 프롬프트"""
        return f"""이 문서 이미지를 분석하여 JSON 형식으로 반환하세요 (크기: {width}x{height}px).

독립적인 콘텐츠 블록을 식별하고 각 블록의 위치와 내용을 파악하세요.

**JSON 형식:**
```json
{{
  "page_size": {{"width": {width}, "height": {height}}},
  "total_blocks": 0,
  "content_blocks": [
    {{
      "id": 1,
      "title": "블록 제목",
      "description": "블록 내용 요약",
      "position": {{"x": 0, "y": 0, "width": 0, "height": 0}},
      "confidence": 0.9
    }}
  ]
}}
```

**중요:** 정확한 픽셀 좌표를 제공하고 JSON만 출력하세요."""

    def _extract_json(self, text: str) -> str:
        """응답에서 JSON 추출"""
        if "```json" in text:
            json_start = text.find("```json") + 7
            json_end = text.find("```", json_start)
            return text[json_start:json_end].strip()
        elif "```" in text:
            json_start = text.find("```") + 3
            json_end = text.find("```", json_start)
            return text[json_start:json_end].strip()
        else:
            return text.strip()

    def analyze_document_structure(
        self,
        image_path: str,
        content_type: str = "general"
    ) -> Dict[str, Any]:
        """
        문서 구조 심화 분석

        Args:
            image_path: 이미지 경로
            content_type: 문서 타입

        Returns:
            구조화된 문서 분석 결과
        """
        logger.info(f"문서 구조 분석 시작: {image_path}")

        # 이미지 인코딩
        image_data, width, height, media_type = self.encode_image_to_base64(image_path)

        # 구조 분석 프롬프트
        prompt = f"""이 문서의 **전체 구조와 레이아웃**을 분석하세요.

**분석 항목:**
1. 문서 유형 (공보물, 뉴스레터, 이력서, 계약서 등)
2. 전체 레이아웃 (단일 컬럼, 2단, 3단 등)
3. 시각적 계층 (헤더, 본문, 푸터)
4. 배경색/테마색 사용
5. 이미지와 텍스트의 비율
6. 강조 요소 (박스, 배경색, 큰 글씨 등)

**JSON 형식:**
```json
{{
  "document_type": "문서 타입",
  "layout_structure": {{
    "columns": 1,
    "header_area": {{"x": 0, "y": 0, "width": 0, "height": 0}},
    "main_area": {{"x": 0, "y": 0, "width": 0, "height": 0}},
    "footer_area": {{"x": 0, "y": 0, "width": 0, "height": 0}}
  }},
  "visual_hierarchy": [
    {{"level": 1, "type": "header", "description": "설명"}},
    {{"level": 2, "type": "main_content", "description": "설명"}}
  ],
  "color_theme": {{
    "primary": "#color",
    "secondary": "#color",
    "background": "#color"
  }},
  "content_ratio": {{
    "text_percentage": 60,
    "image_percentage": 40
  }},
  "emphasis_elements": ["요소1", "요소2"],
  "recommendations": ["추천사항1", "추천사항2"]
}}
```

**중요:** JSON만 출력하세요."""

        # API 호출
        message = self.client.messages.create(
            model=self.model,
            max_tokens=2048,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": media_type,
                                "data": image_data,
                            },
                        },
                        {
                            "type": "text",
                            "text": prompt
                        }
                    ],
                }
            ],
        )

        response_text = message.content[0].text
        json_text = self._extract_json(response_text)

        try:
            result = json.loads(json_text)
            logger.info("문서 구조 분석 완료")
            return result
        except json.JSONDecodeError as e:
            logger.error(f"JSON 파싱 실패: {e}")
            return {"error": "JSON parsing failed", "raw_response": response_text}


# 싱글톤 인스턴스
_vision_processor = None

def get_vision_processor(api_key: str) -> VisionPDFProcessor:
    """Vision 프로세서 싱글톤 인스턴스"""
    global _vision_processor
    if _vision_processor is None:
        _vision_processor = VisionPDFProcessor(api_key)
    return _vision_processor
