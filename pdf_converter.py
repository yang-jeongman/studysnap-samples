"""
PDF 변환 모듈 v6
PDF에서 텍스트 추출, 이미지 기반 PDF는 Claude Vision OCR 활용
- 텍스트 우선 추출
- 이미지 기반 PDF는 Claude Vision으로 OCR
- 모바일 최적화
"""

import os
import re
import base64
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional

try:
    import fitz  # PyMuPDF
except ImportError:
    fitz = None
    print("경고: PyMuPDF가 설치되지 않았습니다. pip install pymupdf 실행 필요")

from PIL import Image
import io

# Vision OCR 임포트
try:
    from vision_ocr import VisionOCR
except ImportError:
    VisionOCR = None

# 로거 설정
logger = logging.getLogger(__name__)


class PDFConverter:
    """PDF 파일에서 텍스트/이미지를 추출하는 클래스"""

    def __init__(self, dpi: int = 150, max_width: int = 800, use_vision_ocr: bool = True, include_images: bool = False):
        self.dpi = dpi
        self.max_width = max_width
        self.use_vision_ocr = use_vision_ocr
        self.include_images = include_images  # OCR 사용 시에도 이미지 포함 여부
        self.vision_ocr = VisionOCR() if (use_vision_ocr and VisionOCR) else None

    def extract_from_pdf(self, pdf_path: str, content_type: str = "general", exclude_pages: list = None) -> Optional[Dict[str, Any]]:
        """PDF에서 텍스트 추출, 없으면 Vision OCR 또는 이미지 렌더링

        Args:
            pdf_path: PDF 파일 경로
            content_type: 콘텐츠 타입 (general, election 등)
            exclude_pages: 제외할 페이지 번호 리스트 (1-based index, 예: [2, 3])
        """
        if fitz is None:
            return self._create_demo_data(pdf_path)

        if exclude_pages is None:
            exclude_pages = []

        try:
            doc = fitz.open(pdf_path)
            pages = []
            total_text_length = 0

            # 1차: 텍스트 추출 시도
            for page_num in range(len(doc)):
                # 제외할 페이지는 건너뛰기
                if (page_num + 1) in exclude_pages:
                    logger.info(f"페이지 {page_num + 1} 제외됨")
                    continue

                page = doc[page_num]
                text = page.get_text("text").strip()
                text = self._clean_text(text)
                total_text_length += len(text)

                pages.append({
                    "page_number": page_num + 1,
                    "image": "",
                    "text": text,
                    "width": page.rect.width,
                    "height": page.rect.height,
                })

            # 텍스트가 거의 없으면 이미지 기반 PDF로 판단
            if total_text_length < 100:
                logger.info(f"텍스트 {total_text_length}자 - 이미지 기반 PDF로 판단")

                # Vision OCR 사용 가능하면 OCR 시도
                if self.vision_ocr and self.vision_ocr.client:
                    logger.info("Claude Vision OCR 사용하여 텍스트 추출 시작")
                    pages = []
                    all_structured_data = []

                    for page_num in range(len(doc)):
                        # 제외할 페이지는 건너뛰기
                        if (page_num + 1) in exclude_pages:
                            logger.info(f"페이지 {page_num + 1} 제외됨 (OCR)")
                            continue

                        page = doc[page_num]
                        page_data = self._process_page_with_vision(
                            page, page_num + 1, content_type
                        )
                        pages.append(page_data)

                        if page_data.get("structured"):
                            all_structured_data.append(page_data["structured"])

                    # 구조화된 데이터 병합
                    merged_structured = self._merge_structured_data(all_structured_data)

                    result = {
                        "filename": Path(pdf_path).name,
                        "page_count": len(doc),
                        "pages": pages,
                        "metadata": {
                            "title": doc.metadata.get("title", "") or Path(pdf_path).stem,
                            "author": doc.metadata.get("author", ""),
                        },
                        "is_image_based": True,
                        "ocr_used": True,
                        "structured_data": merged_structured
                    }
                else:
                    # Vision OCR 없으면 이미지로 렌더링 (기존 방식)
                    logger.warning("Vision OCR 사용 불가 - 이미지 렌더링으로 대체")
                    pages = []
                    for page_num in range(len(doc)):
                        # 제외할 페이지는 건너뛰기
                        if (page_num + 1) in exclude_pages:
                            logger.info(f"페이지 {page_num + 1} 제외됨 (이미지)")
                            continue

                        page = doc[page_num]
                        page_data = self._process_page_as_image(page, page_num + 1)
                        pages.append(page_data)

                    result = {
                        "filename": Path(pdf_path).name,
                        "page_count": len(doc),
                        "pages": pages,
                        "metadata": {
                            "title": doc.metadata.get("title", "") or Path(pdf_path).stem,
                            "author": doc.metadata.get("author", ""),
                        },
                        "is_image_based": True,
                        "ocr_used": False
                    }
            else:
                # 텍스트 기반 PDF
                result = {
                    "filename": Path(pdf_path).name,
                    "page_count": len(doc),
                    "pages": pages,
                    "metadata": {
                        "title": doc.metadata.get("title", "") or Path(pdf_path).stem,
                        "author": doc.metadata.get("author", ""),
                    },
                    "is_image_based": False,
                    "ocr_used": False
                }

            doc.close()
            return result

        except Exception as e:
            logger.error(f"PDF 추출 오류: {str(e)}", exc_info=True)
            return self._create_demo_data(pdf_path)

    def _process_page_with_vision(self, page, page_num: int, content_type: str) -> Dict[str, Any]:
        """페이지를 이미지로 렌더링 후 Vision OCR로 텍스트 추출"""
        try:
            # 줌 계산 (DPI 기반)
            zoom = self.dpi / 72
            mat = fitz.Matrix(zoom, zoom)

            # 페이지 렌더링
            pix = page.get_pixmap(matrix=mat)

            # PIL 이미지로 변환
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)

            # 모바일 최적화 리사이즈
            if img.width > self.max_width:
                ratio = self.max_width / img.width
                new_height = int(img.height * ratio)
                img = img.resize((self.max_width, new_height), Image.LANCZOS)

            # JPEG로 압축
            buffer = io.BytesIO()
            img.save(buffer, format="JPEG", quality=85, optimize=True)
            base64_img = base64.b64encode(buffer.getvalue()).decode()

            # Vision OCR 호출
            logger.info(f"페이지 {page_num} OCR 처리 시작")

            if content_type == "election":
                ocr_result = self.vision_ocr.extract_election_info(base64_img, page_number=page_num)
                text = ocr_result.get("text", "")
                structured = ocr_result.get("structured", {})
            elif content_type == "church":
                ocr_result = self.vision_ocr.extract_church_bulletin_info(base64_img, page_number=page_num)
                text = ocr_result.get("text", "")
                structured = ocr_result.get("structured", {})
            else:
                text = self.vision_ocr.extract_text_from_image(base64_img)
                structured = {}

            logger.info(f"페이지 {page_num}: {len(text)}자 추출 완료")

            # include_images 옵션에 따라 이미지 포함 여부 결정
            image_data = f"data:image/jpeg;base64,{base64_img}" if self.include_images else ""

            return {
                "page_number": page_num,
                "image": image_data,
                "text": text,
                "width": page.rect.width,
                "height": page.rect.height,
                "structured": structured
            }

        except Exception as e:
            logger.error(f"페이지 {page_num} Vision OCR 오류: {str(e)}", exc_info=True)
            return {
                "page_number": page_num,
                "image": "",
                "text": "",
                "width": page.rect.width,
                "height": page.rect.height,
            }

    def _process_page_as_image(self, page, page_num: int) -> Dict[str, Any]:
        """페이지를 이미지로 렌더링 (OCR 없이)"""
        try:
            zoom = self.dpi / 72
            mat = fitz.Matrix(zoom, zoom)
            pix = page.get_pixmap(matrix=mat)
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)

            if img.width > self.max_width:
                ratio = self.max_width / img.width
                new_height = int(img.height * ratio)
                img = img.resize((self.max_width, new_height), Image.LANCZOS)

            buffer = io.BytesIO()
            img.save(buffer, format="JPEG", quality=85, optimize=True)
            base64_img = base64.b64encode(buffer.getvalue()).decode()

            return {
                "page_number": page_num,
                "image": f"data:image/jpeg;base64,{base64_img}",
                "text": "",
                "width": page.rect.width,
                "height": page.rect.height,
            }

        except Exception as e:
            logger.error(f"페이지 {page_num} 이미지 렌더링 오류: {str(e)}", exc_info=True)
            return {
                "page_number": page_num,
                "image": "",
                "text": "",
                "width": page.rect.width,
                "height": page.rect.height,
            }

    def _merge_structured_data(self, data_list: List[Dict]) -> Dict:
        """여러 페이지의 구조화된 데이터 병합"""
        if not data_list:
            return {}

        # 첫 번째 데이터를 기반으로 타입 감지
        first_data = data_list[0] if data_list else {}

        # 교회 주보 데이터인지 확인
        if "worship_services" in first_data or "today_verse" in first_data:
            return self._merge_church_data(data_list)

        # 선거 공보물 데이터 (기본)
        merged = {
            "candidate_name": "",
            "party": "",
            "symbol": "",
            "slogan": "",
            "subtitle": "",
            "manifesto": {"title": "", "content": "", "closing": ""},
            "achievements": [],
            "core_pledges": [],
            "pledges": [],
            "public_pledges": [],
            "career": [],
            "closing_message": "",
            "contact_info": "",
            "other_text": ""
        }

        for data in data_list:
            if not data:
                continue

            # 첫 번째 발견된 값 사용 (단일 값 필드)
            if not merged["candidate_name"] and data.get("candidate_name"):
                merged["candidate_name"] = data["candidate_name"]
            if not merged["party"] and data.get("party"):
                merged["party"] = data["party"]
            if not merged["symbol"] and data.get("symbol"):
                merged["symbol"] = data["symbol"]
            if not merged["slogan"] and data.get("slogan"):
                merged["slogan"] = data["slogan"]
            if not merged["subtitle"] and data.get("subtitle"):
                merged["subtitle"] = data["subtitle"]
            if not merged["closing_message"] and data.get("closing_message"):
                merged["closing_message"] = data["closing_message"]
            if not merged["contact_info"] and data.get("contact_info"):
                merged["contact_info"] = data["contact_info"]

            # 출사표 병합
            manifesto = data.get("manifesto", {})
            if manifesto.get("title") and not merged["manifesto"]["title"]:
                merged["manifesto"]["title"] = manifesto["title"]
            if manifesto.get("content") and not merged["manifesto"]["content"]:
                merged["manifesto"]["content"] = manifesto["content"]
            if manifesto.get("closing") and not merged["manifesto"]["closing"]:
                merged["manifesto"]["closing"] = manifesto["closing"]

            # 리스트는 병합 (중복 가능 - 여러 페이지에서 추출)
            if data.get("achievements"):
                merged["achievements"].extend(data["achievements"])
            if data.get("core_pledges"):
                merged["core_pledges"].extend(data["core_pledges"])
            if data.get("pledges"):
                merged["pledges"].extend(data["pledges"])
            if data.get("public_pledges"):
                merged["public_pledges"].extend(data["public_pledges"])
            if data.get("career"):
                merged["career"].extend(data["career"])

            if data.get("other_text"):
                merged["other_text"] += data["other_text"] + "\n"

        # 중복 제거 (단, 순서 유지)
        def remove_duplicates_keep_order(lst):
            if not lst:
                return []
            seen = set()
            result = []
            for item in lst:
                # Dict는 title로 비교
                if isinstance(item, dict):
                    key = item.get("title", str(item))
                else:
                    key = item
                if key not in seen:
                    seen.add(key)
                    result.append(item)
            return result

        merged["pledges"] = remove_duplicates_keep_order(merged["pledges"])
        merged["career"] = remove_duplicates_keep_order(merged["career"])
        merged["core_pledges"] = remove_duplicates_keep_order(merged["core_pledges"])
        merged["public_pledges"] = remove_duplicates_keep_order(merged["public_pledges"])

        # achievements는 병합 로직이 다름 - 같은 title의 achievement는 sections 병합
        achievements_dict = {}
        for ach in merged["achievements"]:
            title = ach.get("title", "")
            if title:
                if title not in achievements_dict:
                    achievements_dict[title] = ach
                else:
                    # sections 병합
                    existing_sections = achievements_dict[title].get("sections", [])
                    new_sections = ach.get("sections", [])
                    achievements_dict[title]["sections"] = remove_duplicates_keep_order(existing_sections + new_sections)
        merged["achievements"] = list(achievements_dict.values())

        merged["other_text"] = merged["other_text"].strip()

        return merged

    def _merge_church_data(self, data_list: List[Dict]) -> Dict:
        """교회 주보 데이터 병합"""
        merged = {
            "today_verse": {"text": "", "reference": ""},
            "worship_services": [],
            "sermon": {"title": "", "scripture": "", "pastor": "", "content": []},
            "choir": [],
            "news": [],
            "announcements": [],
            "other_text": ""
        }

        for data in data_list:
            if not data:
                continue

            # 오늘의 말씀
            verse = data.get("today_verse", {})
            if verse.get("text") and not merged["today_verse"]["text"]:
                merged["today_verse"]["text"] = verse["text"]
            if verse.get("reference") and not merged["today_verse"]["reference"]:
                merged["today_verse"]["reference"] = verse["reference"]

            # 예배 순서 (각 페이지에서 추출된 것 모두 병합)
            if data.get("worship_services"):
                merged["worship_services"].extend(data["worship_services"])

            # 설교 (첫 번째 발견된 것 사용)
            sermon = data.get("sermon", {})
            if sermon.get("title") and not merged["sermon"]["title"]:
                merged["sermon"]["title"] = sermon["title"]
            if sermon.get("scripture") and not merged["sermon"]["scripture"]:
                merged["sermon"]["scripture"] = sermon["scripture"]
            if sermon.get("pastor") and not merged["sermon"]["pastor"]:
                merged["sermon"]["pastor"] = sermon["pastor"]
            if sermon.get("content"):
                merged["sermon"]["content"].extend(sermon["content"])

            # 찬양대
            if data.get("choir"):
                merged["choir"].extend(data["choir"])

            # 교회 소식
            if data.get("news"):
                merged["news"].extend(data["news"])

            # 광고
            if data.get("announcements"):
                merged["announcements"].extend(data["announcements"])

        # 중복 제거
        def remove_dups(lst):
            seen = set()
            result = []
            for item in lst:
                key = str(item) if isinstance(item, dict) else item
                if key not in seen:
                    seen.add(key)
                    result.append(item)
            return result

        merged["news"] = remove_dups(merged["news"])
        merged["announcements"] = remove_dups(merged["announcements"])

        return merged

    def _clean_text(self, text: str) -> str:
        """텍스트 정리"""
        if not text:
            return ""

        text = re.sub(r'[ \t]+', ' ', text)
        text = re.sub(r'\n{3,}', '\n\n', text)
        text = text.strip()

        return text

    def _create_demo_data(self, pdf_path: str) -> Dict[str, Any]:
        """데모 데이터"""
        filename = Path(pdf_path).stem

        return {
            "filename": Path(pdf_path).name,
            "page_count": 1,
            "pages": [{
                "page_number": 1,
                "image": "",
                "text": f"'{filename}' 문서 - PyMuPDF 설치 필요",
                "width": 595,
                "height": 842,
            }],
            "metadata": {"title": filename, "author": ""},
            "is_image_based": False
        }


# 테스트
if __name__ == "__main__":
    converter = PDFConverter()
    test_pdf = r"C:\Users\jmyang\Downloads\나경원.pdf"

    print(f"Vision OCR 활성화: {converter.vision_ocr is not None}")
    if converter.vision_ocr:
        print(f"API 클라이언트 초기화: {converter.vision_ocr.client is not None}")

    if os.path.exists(test_pdf):
        result = converter.extract_from_pdf(test_pdf, content_type="election")
        print(f"\n페이지 수: {result['page_count']}")
        print(f"이미지 기반: {result.get('is_image_based', False)}")
        print(f"OCR 사용: {result.get('ocr_used', False)}")

        if result.get("structured_data"):
            sd = result["structured_data"]
            print(f"\n=== 구조화된 데이터 ===")
            print(f"후보자: {sd.get('candidate_name', '')}")
            print(f"정당: {sd.get('party', '')}")
            print(f"기호: {sd.get('symbol', '')}")
            print(f"슬로건: {sd.get('slogan', '')}")
            print(f"공약 수: {len(sd.get('pledges', []))}")
            print(f"경력 수: {len(sd.get('career', []))}")

        print(f"\n=== 페이지별 텍스트 ===")
        for page in result['pages'][:3]:
            text_len = len(page['text'])
            print(f"페이지 {page['page_number']}: {text_len}자")
            if page['text']:
                print(f"  미리보기: {page['text'][:200]}...")
