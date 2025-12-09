"""
완전 자동화 선거공보물 변환 엔진 v2.0
- 정당 자동 감지 및 테마 적용
- 레이아웃 자동 분석
- 구조화된 데이터 추출
- 모바일 최적화 HTML 생성
- 후보 유형별 템플릿 (광역/기초/국회의원)
- 지역별 지도 자동 생성
- OCR 후처리 및 오타 수정
"""

import os
import re
import json
import base64
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field, asdict
from enum import Enum

try:
    import fitz  # PyMuPDF
except ImportError:
    fitz = None

from PIL import Image
import io

# 향상된 변환기 모듈 임포트
try:
    from enhanced_converter import (
        EnhancedConverter, CandidateType, get_enhanced_converter,
        OCR_CORRECTIONS, KOREA_REGIONS
    )
    ENHANCED_AVAILABLE = True
except ImportError:
    ENHANCED_AVAILABLE = False

# 로거 설정
logger = logging.getLogger(__name__)

# 능동형 AI 학습 엔진 임포트
try:
    from learning_data.active_learning import get_learning_engine
    ACTIVE_LEARNING_AVAILABLE = True
    logger.info("능동형 AI 학습 엔진 연동됨")
except ImportError:
    ACTIVE_LEARNING_AVAILABLE = False
    logger.warning("능동형 학습 엔진을 찾을 수 없습니다. 학습 기능 비활성화.")


class PartyType(Enum):
    """정당 유형"""
    PPP = "국민의힘"  # People Power Party
    DPK = "더불어민주당"  # Democratic Party of Korea
    JP = "정의당"  # Justice Party
    PP = "국민의당"  # People's Party
    RP = "개혁신당"  # Reform Party
    NRP = "새로운미래"  # New Reform Party
    INDEPENDENT = "무소속"  # Independent
    UNKNOWN = "미확인"


@dataclass
class PartyTheme:
    """정당별 테마 설정"""
    name: str
    primary_color: str
    light_color: str
    dark_color: str
    gradient_start: str
    gradient_end: str
    accent_color: str
    text_on_primary: str = "#FFFFFF"

    @classmethod
    def from_party(cls, party: PartyType) -> 'PartyTheme':
        """정당에 맞는 테마 반환"""
        themes = {
            PartyType.PPP: cls(
                name="국민의힘",
                primary_color="#E11D48",
                light_color="#FEE2E2",
                dark_color="#BE123C",
                gradient_start="#E11D48",
                gradient_end="#BE123C",
                accent_color="#F43F5E"
            ),
            PartyType.DPK: cls(
                name="더불어민주당",
                primary_color="#004EA2",
                light_color="#DBEAFE",
                dark_color="#1E3A8A",
                gradient_start="#004EA2",
                gradient_end="#1E3A8A",
                accent_color="#3B82F6"
            ),
            PartyType.JP: cls(
                name="정의당",
                primary_color="#FFCC00",
                light_color="#FEF3C7",
                dark_color="#D97706",
                gradient_start="#FFCC00",
                gradient_end="#F59E0B",
                accent_color="#F59E0B",
                text_on_primary="#000000"
            ),
            PartyType.PP: cls(
                name="국민의당",
                primary_color="#EA5504",
                light_color="#FFEDD5",
                dark_color="#C2410C",
                gradient_start="#EA5504",
                gradient_end="#C2410C",
                accent_color="#F97316"
            ),
            PartyType.RP: cls(
                name="개혁신당",
                primary_color="#FF6B35",
                light_color="#FED7AA",
                dark_color="#EA580C",
                gradient_start="#FF6B35",
                gradient_end="#EA580C",
                accent_color="#FB923C"
            ),
            PartyType.NRP: cls(
                name="새로운미래",
                primary_color="#10B981",
                light_color="#D1FAE5",
                dark_color="#059669",
                gradient_start="#10B981",
                gradient_end="#059669",
                accent_color="#34D399"
            ),
            PartyType.INDEPENDENT: cls(
                name="무소속",
                primary_color="#6B7280",
                light_color="#F3F4F6",
                dark_color="#374151",
                gradient_start="#6B7280",
                gradient_end="#374151",
                accent_color="#9CA3AF"
            ),
            PartyType.UNKNOWN: cls(
                name="미확인",
                primary_color="#6366F1",
                light_color="#E0E7FF",
                dark_color="#4338CA",
                gradient_start="#6366F1",
                gradient_end="#4338CA",
                accent_color="#818CF8"
            ),
        }
        return themes.get(party, themes[PartyType.UNKNOWN])


@dataclass
class CandidateInfo:
    """후보자 정보"""
    name: str = ""
    party: str = ""
    party_type: PartyType = PartyType.UNKNOWN
    symbol: str = ""  # 기호
    slogan: str = ""
    subtitle: str = ""
    position: str = ""  # 국회의원, 시장 등
    district: str = ""  # 선거구


@dataclass
class Pledge:
    """공약 정보"""
    title: str
    subtitle: str = ""
    details: List[str] = field(default_factory=list)
    category: str = ""  # 교육, 경제, 복지 등
    priority: int = 0


@dataclass
class Achievement:
    """실적 정보"""
    title: str
    sections: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class Career:
    """경력 정보"""
    period: str = ""
    title: str = ""
    description: str = ""


@dataclass
class Vision:
    """비전 정보"""
    title: str = ""  # 비전 제목 (예: "다시 대구의 번영과 영광을!")
    items: List[str] = field(default_factory=list)  # 비전 항목들


@dataclass
class ContactInfo:
    """연락처 정보"""
    office_address: str = ""
    phone: str = ""
    email: str = ""
    website: str = ""
    facebook: str = ""
    instagram: str = ""
    youtube: str = ""
    blog: str = ""
    twitter: str = ""
    raw_text: str = ""


@dataclass
class ElectionBrochure:
    """선거공보물 전체 데이터"""
    candidate: CandidateInfo = field(default_factory=CandidateInfo)
    manifesto: Dict[str, str] = field(default_factory=dict)  # 출사표
    achievements: List[Achievement] = field(default_factory=list)
    core_pledges: List[Pledge] = field(default_factory=list)  # 핵심공약
    public_pledges: List[str] = field(default_factory=list)  # 주민밀착공약
    careers: List[Career] = field(default_factory=list)
    contact: ContactInfo = field(default_factory=ContactInfo)
    closing_message: str = ""
    theme: PartyTheme = None
    raw_pages: List[Dict] = field(default_factory=list)
    # v2.0 추가 필드
    candidate_type: str = ""  # 광역단체장, 기초단체장, 국회의원 등
    region_metro: str = ""  # 광역시/도
    region_district: str = ""  # 기초단체 (구/군/시)
    sub_regions: List[str] = field(default_factory=list)  # 하위 지역 (시군구 또는 동)
    region_pledges: Dict[str, str] = field(default_factory=dict)  # 지역별 공약
    pledge_count: int = 0  # 공약 개수
    vision: Vision = field(default_factory=Vision)  # 비전 섹션

    def to_dict(self) -> Dict:
        """딕셔너리로 변환"""
        return {
            "candidate": asdict(self.candidate),
            "manifesto": self.manifesto,
            "achievements": [asdict(a) for a in self.achievements],
            "core_pledges": [asdict(p) for p in self.core_pledges],
            "public_pledges": self.public_pledges,
            "careers": [asdict(c) for c in self.careers],
            "contact": asdict(self.contact),
            "closing_message": self.closing_message,
            "theme": asdict(self.theme) if self.theme else None,
            # v2.0 추가
            "candidate_type": self.candidate_type,
            "region_metro": self.region_metro,
            "region_district": self.region_district,
            "sub_regions": self.sub_regions,
            "region_pledges": self.region_pledges,
            "pledge_count": self.pledge_count,
            "vision": asdict(self.vision),
        }


class PartyDetector:
    """정당 자동 감지"""

    PARTY_KEYWORDS = {
        PartyType.PPP: ["국민의힘", "국민의 힘", "국힘", "People Power"],
        PartyType.DPK: ["더불어민주당", "민주당", "더민주", "Democratic Party"],
        PartyType.JP: ["정의당", "Justice Party"],
        PartyType.PP: ["국민의당", "People's Party"],
        PartyType.RP: ["개혁신당", "Reform Party"],
        PartyType.NRP: ["새로운미래", "New Reform"],
        PartyType.INDEPENDENT: ["무소속", "Independent"],
    }

    # 색상 기반 감지 (RGB 범위)
    PARTY_COLORS = {
        PartyType.PPP: [(180, 0, 0), (255, 60, 100)],  # 빨강
        PartyType.DPK: [(0, 50, 120), (50, 120, 200)],  # 파랑
        PartyType.JP: [(200, 180, 0), (255, 220, 50)],  # 노랑
        PartyType.PP: [(200, 70, 0), (255, 130, 50)],  # 주황
    }

    @classmethod
    def detect_from_text(cls, text: str) -> Tuple[PartyType, float]:
        """텍스트에서 정당 감지"""
        text_lower = text.lower()

        for party, keywords in cls.PARTY_KEYWORDS.items():
            for keyword in keywords:
                if keyword.lower() in text_lower:
                    return party, 1.0

        return PartyType.UNKNOWN, 0.0

    @classmethod
    def detect_from_image(cls, image: Image.Image) -> Tuple[PartyType, float]:
        """이미지 색상에서 정당 감지"""
        # 이미지 상단 영역 분석 (보통 헤더에 정당 색상)
        width, height = image.size
        header_region = image.crop((0, 0, width, int(height * 0.2)))

        # 주요 색상 추출
        colors = header_region.getcolors(maxcolors=10000)
        if not colors:
            return PartyType.UNKNOWN, 0.0

        # 가장 많이 사용된 색상들
        sorted_colors = sorted(colors, key=lambda x: x[0], reverse=True)[:20]

        for count, color in sorted_colors:
            if len(color) >= 3:
                r, g, b = color[:3]
                for party, (min_color, max_color) in cls.PARTY_COLORS.items():
                    if (min_color[0] <= r <= max_color[0] and
                        min_color[1] <= g <= max_color[1] and
                        min_color[2] <= b <= max_color[2]):
                        confidence = count / sum(c[0] for c in sorted_colors)
                        if confidence > 0.1:  # 최소 10% 이상
                            return party, min(confidence * 2, 1.0)

        return PartyType.UNKNOWN, 0.0


class AutoElectionConverter:
    """완전 자동화 선거공보물 변환기 v2.0"""

    def __init__(self, vision_ocr=None, dpi: int = 150, max_width: int = 800):
        self.dpi = dpi
        self.max_width = max_width
        self.vision_ocr = vision_ocr

        # Vision OCR 자동 초기화
        if self.vision_ocr is None:
            try:
                from vision_ocr import VisionOCR
                self.vision_ocr = VisionOCR()
            except Exception as e:
                logger.warning(f"Vision OCR 초기화 실패: {e}")
                self.vision_ocr = None

        # 향상된 변환기 (v2.0)
        self.enhanced = None
        if ENHANCED_AVAILABLE:
            try:
                self.enhanced = get_enhanced_converter()
                logger.info("향상된 변환기 (v2.0) 활성화됨")
            except Exception as e:
                logger.warning(f"향상된 변환기 초기화 실패: {e}")

    def _extract_info_from_filename(self, pdf_path: str) -> Optional[Dict[str, str]]:
        """
        PDF 파일명에서 정당과 후보자 정보 추출
        지원 형식:
        - "정당-후보자.pdf" (예: 국민-홍준표.pdf)
        - "정당_후보자.pdf"
        - "후보자_정당.pdf"
        - "선거구_정당_후보자.pdf" (예: 2022-광역 단체장_국민-홍준표.pdf)
        """
        import os
        filename = os.path.basename(pdf_path)
        name_part = os.path.splitext(filename)[0]  # 확장자 제거

        # 정당명 매핑
        party_mapping = {
            "국민": "국민의힘",
            "국민의힘": "국민의힘",
            "민주": "더불어민주당",
            "더불어민주당": "더불어민주당",
            "정의": "정의당",
            "정의당": "정의당",
            "국민의당": "국민의당",
            "개혁신당": "개혁신당",
            "새로운미래": "새로운미래",
            "무소속": "무소속",
        }

        result = {"party": None, "name": None}

        # 패턴 1: "정당-후보자" 또는 "정당_후보자"
        for sep in ["-", "_"]:
            parts = name_part.split(sep)
            for i, part in enumerate(parts):
                # 정당 확인
                for key, value in party_mapping.items():
                    if key in part:
                        result["party"] = value
                        # 다음 파트가 후보자명일 가능성
                        if i + 1 < len(parts):
                            candidate_part = parts[i + 1]
                            # 한글 이름만 추출 (2~4글자)
                            name_match = re.search(r'([가-힣]{2,4})', candidate_part)
                            if name_match:
                                result["name"] = name_match.group(1)
                        break

        # 패턴 2: 한글 이름만 있는 경우 (2~4글자)
        if not result["name"]:
            # 파일명 전체에서 한글 이름 추출
            name_matches = re.findall(r'([가-힣]{2,4})', name_part)
            for match in name_matches:
                # 정당명이 아닌 것만 후보자명으로
                if match not in party_mapping and match not in ["광역", "단체장", "기초", "국회의원"]:
                    result["name"] = match
                    break

        return result if result["party"] or result["name"] else None

    def convert(self, pdf_path: str, original_filename: str = None) -> ElectionBrochure:
        """PDF를 완전 자동으로 변환

        Args:
            pdf_path: PDF 파일 경로
            original_filename: 원본 파일명 (업로드 시 파일명 정보 보존용)
        """
        logger.info(f"자동 변환 시작: {pdf_path}")

        if fitz is None:
            raise ImportError("PyMuPDF가 설치되지 않았습니다")

        brochure = ElectionBrochure()

        # 파일명에서 후보 정보 추출 (폴백용)
        # 원본 파일명이 제공되면 우선 사용
        filename_for_extraction = original_filename if original_filename else pdf_path
        filename_info = self._extract_info_from_filename(filename_for_extraction)
        if filename_info:
            logger.info(f"파일명에서 추출: 정당={filename_info.get('party')}, 후보={filename_info.get('name')}")

        try:
            doc = fitz.open(pdf_path)
            all_text = ""
            first_page_image = None

            # 1단계: 모든 페이지 처리
            for page_num in range(len(doc)):
                page = doc[page_num]
                page_data = self._process_page(page, page_num + 1)
                brochure.raw_pages.append(page_data)
                all_text += page_data.get("text", "") + "\n"

                # 첫 페이지 이미지 저장 (정당 색상 분석용)
                if page_num == 0:
                    first_page_image = self._render_page_to_image(page)

            doc.close()

            # v2.0: OCR 후처리 (오타 수정)
            if self.enhanced:
                all_text = self.enhanced.correct_ocr_errors(all_text)
                logger.info("OCR 후처리 완료 (오타 수정)")

            # 2단계: 정당 감지
            party_from_text, text_conf = PartyDetector.detect_from_text(all_text)
            party_from_image, image_conf = PartyType.UNKNOWN, 0.0

            if first_page_image:
                party_from_image, image_conf = PartyDetector.detect_from_image(first_page_image)

            # 텍스트 기반 감지 우선
            if text_conf > 0:
                detected_party = party_from_text
            elif image_conf > 0.3:
                detected_party = party_from_image
            else:
                detected_party = PartyType.UNKNOWN

            brochure.candidate.party_type = detected_party
            brochure.candidate.party = detected_party.value
            brochure.theme = PartyTheme.from_party(detected_party)

            logger.info(f"정당 감지: {detected_party.value} (텍스트: {text_conf:.2f}, 이미지: {image_conf:.2f})")

            # 3단계: 구조화된 데이터 추출
            self._extract_structured_data(brochure)

            # 파일명 정보를 우선 적용 (OCR 오류 방지)
            if filename_info:
                # 파일명에서 추출한 이름이 있으면 OCR 결과보다 우선 적용
                # (OCR이 '삼'을 '삽'으로 잘못 인식하는 등의 오류 방지)
                if filename_info.get("name"):
                    if brochure.candidate.name and brochure.candidate.name != filename_info["name"]:
                        logger.info(f"후보자명 파일명 우선 적용: {filename_info['name']} (OCR: {brochure.candidate.name})")
                    brochure.candidate.name = filename_info["name"]

                # 정당이 미확인인 경우 파일명에서 추출
                # 조건 완화: 정당이 UNKNOWN이거나 신뢰도가 낮은 경우
                if filename_info.get("party"):
                    party_name = filename_info["party"]
                    # 파일명에서 명확한 정당이 있으면 우선 적용
                    if detected_party == PartyType.UNKNOWN or brochure.candidate.party == "미확인":
                        for pt in PartyType:
                            if pt.value == party_name:
                                brochure.candidate.party_type = pt
                                brochure.candidate.party = party_name
                                brochure.theme = PartyTheme.from_party(pt)
                                logger.info(f"정당 폴백 적용: {party_name}")
                                break
                    # 또한 파일명 정당이 더 명확할 경우 덮어쓰기
                    elif text_conf < 0.5:
                        for pt in PartyType:
                            if pt.value == party_name:
                                brochure.candidate.party_type = pt
                                brochure.candidate.party = party_name
                                brochure.theme = PartyTheme.from_party(pt)
                                logger.info(f"정당 파일명 우선 적용: {party_name}")
                                break

            # v2.0: 후보 유형 및 지역 감지
            if self.enhanced:
                # 후보 유형 감지
                candidate_type = self.enhanced.detect_candidate_type(
                    all_text, brochure.candidate.position
                )
                brochure.candidate_type = candidate_type.value

                # 지역 감지
                metro, district = self.enhanced.detect_region(all_text)
                brochure.region_metro = metro or ""
                brochure.region_district = district or ""

                # 하위 지역 목록 가져오기
                brochure.sub_regions = self.enhanced.get_sub_regions(
                    candidate_type, metro or "", district
                )

                # 공약 개수 감지
                brochure.pledge_count = self.enhanced.extract_pledge_count(all_text)

                logger.info(f"v2.0 감지: 유형={candidate_type.value}, 지역={metro}/{district}, 하위지역={len(brochure.sub_regions)}개, 공약수={brochure.pledge_count}")

            # 능동형 AI 학습: 변환 메타데이터 기록
            if ACTIVE_LEARNING_AVAILABLE:
                try:
                    learning_engine = get_learning_engine()
                    conversion_data = {
                        "candidate_name": brochure.candidate.name,
                        "party": brochure.candidate.party,
                        "candidate_type": brochure.candidate_type,
                        "region": f"{brochure.region_metro}/{brochure.region_district}",
                        "pledge_count": brochure.pledge_count,
                        "page_count": len(brochure.raw_pages),
                        "filename": original_filename or pdf_path
                    }
                    learning_engine.record_conversion(conversion_data)
                    logger.info("🧠 변환 데이터가 학습 엔진에 기록됨")
                except Exception as e:
                    logger.warning(f"학습 데이터 기록 실패: {e}")

            return brochure

        except Exception as e:
            logger.error(f"변환 오류: {e}", exc_info=True)
            raise

    def _process_page(self, page, page_num: int) -> Dict[str, Any]:
        """페이지 처리 - OCR 포함"""
        try:
            # 먼저 텍스트 추출 시도
            text = page.get_text("text").strip()

            # 텍스트가 적으면 OCR 사용
            if len(text) < 50 and self.vision_ocr:
                logger.info(f"페이지 {page_num}: OCR 처리 시작")

                # 페이지를 이미지로 렌더링
                zoom = self.dpi / 72
                mat = fitz.Matrix(zoom, zoom)
                pix = page.get_pixmap(matrix=mat)

                img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)

                # 리사이즈
                if img.width > self.max_width:
                    ratio = self.max_width / img.width
                    new_height = int(img.height * ratio)
                    img = img.resize((self.max_width, new_height), Image.LANCZOS)

                # Base64 인코딩
                buffer = io.BytesIO()
                img.save(buffer, format="JPEG", quality=85)
                base64_img = base64.b64encode(buffer.getvalue()).decode()

                # Vision OCR 호출
                if hasattr(self.vision_ocr, 'extract_election_info'):
                    ocr_result = self.vision_ocr.extract_election_info(
                        base64_img,
                        page_number=page_num
                    )
                    text = ocr_result.get("text", "")
                    structured = ocr_result.get("structured", {})
                else:
                    text = self.vision_ocr.extract_text_from_image(base64_img)
                    structured = {}

                return {
                    "page_number": page_num,
                    "text": text,
                    "structured": structured,
                    "ocr_used": True,
                    "width": page.rect.width,
                    "height": page.rect.height
                }

            return {
                "page_number": page_num,
                "text": self._clean_text(text),
                "structured": {},
                "ocr_used": False,
                "width": page.rect.width,
                "height": page.rect.height
            }

        except Exception as e:
            logger.error(f"페이지 {page_num} 처리 오류: {e}")
            return {
                "page_number": page_num,
                "text": "",
                "structured": {},
                "ocr_used": False,
                "error": str(e)
            }

    def _render_page_to_image(self, page) -> Optional[Image.Image]:
        """페이지를 PIL 이미지로 렌더링"""
        try:
            zoom = self.dpi / 72
            mat = fitz.Matrix(zoom, zoom)
            pix = page.get_pixmap(matrix=mat)
            return Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        except Exception as e:
            logger.error(f"이미지 렌더링 오류: {e}")
            return None

    def _clean_text(self, text: str) -> str:
        """텍스트 정리"""
        if not text:
            return ""
        text = re.sub(r'[\u00b8\u02dc\u00ba\u00b0\u00b7]', '', text)
        text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]', '', text)
        text = re.sub(r'[ \t]+', ' ', text)
        text = re.sub(r'\n{3,}', '\n\n', text)
        return text.strip()

    def _extract_structured_data(self, brochure: ElectionBrochure):
        """구조화된 데이터 추출"""
        all_text = ""
        all_structured = {}

        for page in brochure.raw_pages:
            all_text += page.get("text", "") + "\n"

            # structured 데이터 병합
            structured = page.get("structured", {})
            if structured:
                for key, value in structured.items():
                    if value and not all_structured.get(key):
                        all_structured[key] = value
                    elif isinstance(value, list) and value:
                        if key not in all_structured:
                            all_structured[key] = []
                        all_structured[key].extend(value)

        # 후보자 정보 추출
        self._extract_candidate_info(brochure, all_text, all_structured)

        # 출사표 추출
        if all_structured.get("manifesto"):
            brochure.manifesto = all_structured["manifesto"]

        # 핵심공약 추출
        self._extract_pledges(brochure, all_text, all_structured)

        # 실적 추출
        if all_structured.get("achievements"):
            for ach in all_structured["achievements"]:
                brochure.achievements.append(Achievement(
                    title=ach.get("title", ""),
                    sections=ach.get("sections", [])
                ))

        # 경력 추출
        self._extract_careers(brochure, all_text, all_structured)

        # 비전 추출
        self._extract_vision(brochure, all_text, all_structured)

        # 연락처 추출
        self._extract_contact_info(brochure, all_text, all_structured)

        # 마무리 문구
        if all_structured.get("closing_message"):
            brochure.closing_message = all_structured["closing_message"]

    def _extract_candidate_info(self, brochure: ElectionBrochure, text: str, structured: Dict):
        """후보자 정보 추출"""
        candidate = brochure.candidate

        # structured 데이터 우선
        if structured.get("candidate_name"):
            candidate.name = structured["candidate_name"]
        if structured.get("symbol"):
            candidate.symbol = structured["symbol"]
        if structured.get("slogan"):
            candidate.slogan = structured["slogan"]
        if structured.get("subtitle"):
            candidate.subtitle = structured["subtitle"]

        # 텍스트에서 추가 추출
        if not candidate.name:
            name_patterns = [
                r'기호\s*(\d+)[번호]?\s*([가-힣]{2,4})',
                r'([가-힣]{2,4})\s*후보',
                r'후보\s*([가-힣]{2,4})',
            ]
            for pattern in name_patterns:
                match = re.search(pattern, text)
                if match:
                    if len(match.groups()) == 2:
                        candidate.symbol = match.group(1)
                        candidate.name = match.group(2)
                    else:
                        candidate.name = match.group(1)
                    break

        if not candidate.symbol:
            # 다양한 기호 패턴 시도
            symbol_patterns = [
                r'기호\s*(\d+)\s*번?',           # 기호 2, 기호 2번
                r'기호\s*제?\s*(\d+)\s*호?',      # 기호 제2호
                r'(\d+)\s*번\s*후보',             # 2번 후보
                r'[①②③④⑤⑥⑦⑧⑨⑩]',            # 원문자
                r'제\s*(\d+)\s*호',               # 제2호
                r'No\.\s*(\d+)',                  # No.2
                r'#\s*(\d+)',                     # #2
            ]

            for pattern in symbol_patterns:
                symbol_match = re.search(pattern, text)
                if symbol_match:
                    if '①②③④⑤⑥⑦⑧⑨⑩'.find(symbol_match.group(0)) >= 0:
                        # 원문자를 숫자로 변환
                        circled_nums = '①②③④⑤⑥⑦⑧⑨⑩'
                        idx = circled_nums.find(symbol_match.group(0))
                        if idx >= 0:
                            candidate.symbol = str(idx + 1)
                    else:
                        candidate.symbol = symbol_match.group(1)
                    break

        # 직위 추출
        positions = ["국회의원", "시장", "도지사", "구청장", "군수", "시의원", "구의원", "도의원"]
        for pos in positions:
            if pos in text:
                candidate.position = pos + " 후보"
                break

        # 선거구 추출
        district_match = re.search(r'([가-힣]+(?:시|도|구|군|읍|면|동))\s*(?:갑|을|병|정)?(?:선거구)?', text)
        if district_match:
            candidate.district = district_match.group(0)

    def _extract_pledges(self, brochure: ElectionBrochure, text: str, structured: Dict):
        """공약 추출"""
        # structured 데이터 우선
        if structured.get("core_pledges"):
            for pledge_data in structured["core_pledges"]:
                brochure.core_pledges.append(Pledge(
                    title=pledge_data.get("title", ""),
                    subtitle=pledge_data.get("subtitle", ""),
                    details=pledge_data.get("details", [])
                ))

        if structured.get("public_pledges"):
            brochure.public_pledges = structured["public_pledges"]

        # 텍스트에서 추가 공약 추출
        if not brochure.core_pledges or len(brochure.core_pledges) < 5:
            # 공약 제목 키워드 패턴 (실제 공보물에서 자주 사용되는 표현)
            pledge_keyword_patterns = [
                # 숫자 기호 패턴 (원문자)
                r'[①②③④⑤⑥⑦⑧⑨⑩]\s*(.{5,100})',
                r'[❶❷❸❹❺❻❼❽❾❿]\s*(.{5,100})',
                # 번호 패턴 (1. 2. 3. 등)
                r'(?:^|\n)\s*[1-9]\s*[\.]\s*(.{5,100})',
                r'(?:^|\n)\s*[1-9]\s*번째?\s*[공약]?\s*[:\-]?\s*(.{5,100})',
                # 공약/정책 표현 패턴 (확장)
                r'([가-힣]+(?:통합|신공항|공항|산단|벤처|밸리|건설|첨단화|재구조화|후적지|두바이|개발).{0,50})',
                r'([가-힣]+(?:글로벌|문화|콘텐츠|도시|르네상스|하이웨이|광역도시).{0,30})',
                r'([가-힣]+(?:조성|구축|추진|실현|확대|지원|강화|혁신|개발).{0,50})',
                r'([가-힣]+\s*(?:도시|사업|정책|프로젝트|시대).{0,50})',
                # 글머리 기호 패턴
                r'•\s*(.{5,100})',
                r'[○●◆◇]\s*(.{5,100})',
                r'▶\s*(.{5,100})',
                # 하이픈/대시 패턴
                r'[-]\s*(.{5,100})',
            ]

            extracted_pledges = []
            for pattern in pledge_keyword_patterns:
                matches = re.findall(pattern, text, re.MULTILINE)
                for match in matches:
                    pledge = match.strip()
                    # 중복 제거 및 유효성 검사 (최소 5자 이상)
                    if 4 < len(pledge) < 150:
                        # 이미 추출된 공약과 유사한지 확인
                        is_duplicate = False
                        for existing in extracted_pledges:
                            if pledge in existing or existing in pledge:
                                is_duplicate = True
                                break
                        if not is_duplicate:
                            extracted_pledges.append(pledge)

            # 기존 공약에 추가
            existing_titles = {p.title for p in brochure.core_pledges}
            for pledge in extracted_pledges[:10]:  # 최대 10개
                if pledge not in existing_titles:
                    brochure.core_pledges.append(Pledge(title=pledge))

    def _extract_careers(self, brochure: ElectionBrochure, text: str, structured: Dict):
        """경력 추출"""
        if structured.get("career"):
            for career_text in structured["career"]:
                # 연도 추출 시도
                year_match = re.search(r'(\d{4})[~\-년]\s*(\d{4}|현재)?', career_text)
                if year_match:
                    period = year_match.group(0)
                    description = career_text.replace(period, "").strip()
                else:
                    period = ""
                    description = career_text

                brochure.careers.append(Career(
                    period=period,
                    description=description
                ))

        # 텍스트에서 추가 경력 추출
        if not brochure.careers:
            career_patterns = [
                r'(\d{4})[~\-년]\s*(?:\d{4}|현재)?\s*(.+)',
                r'(전|현)\s*(.+장|.+위원|.+대표)',
            ]
            for pattern in career_patterns:
                matches = re.findall(pattern, text)
                for match in matches[:20]:
                    if isinstance(match, tuple):
                        brochure.careers.append(Career(
                            period=match[0] if match[0].isdigit() else "",
                            description=" ".join(match)
                        ))

    def _extract_vision(self, brochure: ElectionBrochure, text: str, structured: Dict):
        """비전 추출 - 후보자의 핵심 비전/슬로건 추출"""
        vision = brochure.vision

        # structured 데이터에서 비전 추출
        if structured.get("vision_title"):
            vision.title = structured["vision_title"]
        if structured.get("vision_items"):
            vision.items = structured["vision_items"]

        # 텍스트에서 비전 추출
        if not vision.title:
            # 비전 제목 패턴 (슬로건, 대의명분)
            vision_title_patterns = [
                r'"([^"]{10,50})"',  # 큰따옴표로 감싼 슬로건
                r'「([^」]{10,50})」',  # 꺾쇠로 감싼 슬로건
                r'『([^』]{10,50})』',
                r'다시\s+([가-힣]+의?\s*[가-힣]+[을를]?[!]?)',  # "다시 대구의 번영과 영광을!"
                r'([가-힣]+\s*(?:발전|번영|미래|도약|희망|변화|혁신)[을를]?\s*(?:위해|위한|향해)?[!]?)',
            ]

            for pattern in vision_title_patterns:
                match = re.search(pattern, text)
                if match:
                    vision.title = match.group(1).strip()
                    break

        # 비전 항목 추출 (번호 + 하겠습니다/만들겠습니다 등의 약속 형태)
        if not vision.items:
            vision_item_patterns = [
                # 번호 + 비전 내용 + 하겠습니다
                r'[1-3]\s*[\.]\s*([^\.]{15,100}(?:하겠습니다|만들겠습니다|이루겠습니다|실현하겠습니다|추진하겠습니다|창조하겠습니다))',
                r'[①②③]\s*([^①②③]{15,100}(?:하겠습니다|만들겠습니다|이루겠습니다|실현하겠습니다|추진하겠습니다|창조하겠습니다))',
                # 비전 키워드가 있는 패턴
                r'([가-힣]+(?:리빌딩|대전환|글로벌)[으로]?\s*[^\.]{10,80}[\.!]?)',
            ]

            extracted_visions = []
            for pattern in vision_item_patterns:
                matches = re.findall(pattern, text, re.MULTILINE)
                for match in matches:
                    item = match.strip()
                    if 10 < len(item) < 150:
                        # 중복 확인
                        is_duplicate = False
                        for existing in extracted_visions:
                            if item in existing or existing in item:
                                is_duplicate = True
                                break
                        if not is_duplicate:
                            extracted_visions.append(item)

            vision.items = extracted_visions[:5]  # 최대 5개

        logger.info(f"비전 추출: 제목='{vision.title}', 항목수={len(vision.items)}")

    def _extract_contact_info(self, brochure: ElectionBrochure, text: str, structured: Dict):
        """연락처 정보 추출"""
        contact = brochure.contact

        if structured.get("contact_info"):
            contact.raw_text = structured["contact_info"]

        # 전화번호 추출
        phone_match = re.search(r'(\d{2,3}-\d{3,4}-\d{4})', text)
        if phone_match:
            contact.phone = phone_match.group(1)

        # SNS 추출
        facebook_match = re.search(r'facebook\.com/([a-zA-Z0-9._-]+)', text, re.I)
        if facebook_match:
            contact.facebook = f"https://facebook.com/{facebook_match.group(1)}"

        instagram_match = re.search(r'instagram\.com/([a-zA-Z0-9._-]+)', text, re.I)
        if instagram_match:
            contact.instagram = f"https://instagram.com/{instagram_match.group(1)}"

        youtube_match = re.search(r'youtube\.com/([^\s<>]+)', text, re.I)
        if youtube_match:
            contact.youtube = f"https://youtube.com/{youtube_match.group(1)}"

        blog_match = re.search(r'blog\.naver\.com/([a-zA-Z0-9_-]+)', text, re.I)
        if blog_match:
            contact.blog = f"https://blog.naver.com/{blog_match.group(1)}"

        # 선거사무소 주소 추출
        address_patterns = [
            r'(?:선거사무소|사무소|캠프)\s*[:\-]?\s*([가-힣]+(?:시|도)[가-힣\s\d\-]+(?:층|호)?)',
            r'([가-힣]+(?:광역시|특별시|시|도)\s+[가-힣]+(?:구|군|시)\s+[가-힣\d\s\-]+(?:번지|길|로)?[가-힣\d\s\-]*)',
            r'주소\s*[:\-]?\s*([가-힣\d\s\-,]+(?:층|호)?)',
        ]
        for pattern in address_patterns:
            addr_match = re.search(pattern, text)
            if addr_match and not contact.office_address:
                contact.office_address = addr_match.group(1).strip()
                break

    def generate_html(self, brochure: ElectionBrochure, output_folder: str = None) -> str:
        """모바일 최적화 HTML 생성

        Args:
            brochure: 변환된 선거 공보 데이터
            output_folder: 이미지가 저장된 폴더 경로 (이미지 자동 포함용)
        """
        theme = brochure.theme or PartyTheme.from_party(PartyType.UNKNOWN)
        candidate = brochure.candidate

        # 폴더에서 이미지 파일 목록 가져오기
        folder_images = self._get_folder_images(output_folder) if output_folder else []

        # 이미지 관련 HTML 생성
        image_styles = self._generate_image_styles() if folder_images else ""
        image_script = self._generate_image_script() if folder_images else ""

        # 이미지를 섹션별로 분배 (문맥에 맞게 배치)
        hero_image = ""
        inline_images = []
        gallery_images = []

        if folder_images:
            logger.info(f"📸 폴더에서 {len(folder_images)}개 이미지 발견")
            # 첫 번째 이미지: 히어로 섹션에 배치 (얼굴/대표 이미지)
            hero_image = self._generate_inline_image_html(folder_images[0], "full")

            # 나머지 이미지들: 공약 섹션 사이에 배치
            if len(folder_images) > 1:
                inline_images = folder_images[1:]

            # 모든 이미지를 갤러리에도 추가
            gallery_images = folder_images

        # 이미지 갤러리 HTML (모든 이미지 모아서 보기)
        image_gallery_html = self._generate_image_gallery_html(gallery_images) if gallery_images else ""

        # 공약 HTML 생성
        pledges_html = self._generate_pledges_html(brochure.core_pledges)

        # 경력 HTML 생성
        careers_html = self._generate_careers_html(brochure.careers)

        # 연락처 HTML 생성
        contact_html = self._generate_contact_html(brochure.contact)

        # 비전 HTML 생성
        vision_html = self._generate_vision_html(brochure.vision)

        # 하이라이트 HTML
        highlights_html = self._generate_highlights_html(brochure)

        # 전문보기 HTML
        fulltext_html = self._generate_fulltext_html(brochure.raw_pages)

        # v2.0: 지역 지도 섹션 HTML
        # 조건: 지역별 공약(region_pledges)이 있거나 기초단체장/국회의원인 경우에만 표시
        region_map_html = ""
        region_map_styles = ""
        region_map_script = ""
        if self.enhanced and brochure.sub_regions:
            try:
                from enhanced_converter import CandidateType
                candidate_type = CandidateType(brochure.candidate_type) if brochure.candidate_type else CandidateType.UNKNOWN

                # 광역단체장은 지역별 공약이 있는 경우에만 지도 표시
                # 기초단체장/국회의원은 항상 지도 표시
                show_map = False
                if candidate_type in [CandidateType.BASIC_MAYOR, CandidateType.NATIONAL_ASSEMBLY]:
                    show_map = True
                elif brochure.region_pledges:  # 지역별 공약이 있으면 표시
                    show_map = True

                if show_map:
                    region_map_html = self.enhanced.generate_map_section_html(
                        candidate_type, brochure.sub_regions, brochure.region_pledges
                    )
                    region_map_styles = self.enhanced.generate_map_styles()
                    region_map_script = self.enhanced.generate_map_script()
                    logger.info(f"지역 지도 섹션 생성: {len(brochure.sub_regions)}개 지역")
                else:
                    logger.info(f"지역 지도 섹션 생략: 광역단체장이고 지역별 공약 없음")
            except Exception as e:
                logger.warning(f"지역 지도 생성 실패: {e}")

        # HTML 생성
        html_output = f'''<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <meta name="description" content="{candidate.name} - {candidate.position or '선거공보'}">
    <title>{candidate.name} - {candidate.position or '선거공보'}</title>

    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}

        :root {{
            --party-color: {theme.primary_color};
            --party-color-light: {theme.light_color};
            --party-color-dark: {theme.dark_color};
            --party-gradient: linear-gradient(135deg, {theme.gradient_start} 0%, {theme.gradient_end} 100%);
            --party-accent: {theme.accent_color};
            --text-on-primary: {theme.text_on_primary};
        }}

        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Apple SD Gothic Neo', 'Noto Sans KR', sans-serif;
            line-height: 1.6;
            color: #333;
            background: #f5f5f5;
            overflow-x: hidden;
            padding-bottom: 80px;
        }}

        /* Fixed Navigation */
        .nav-bar {{
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            background: white;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            z-index: 1000;
            padding: 15px 20px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}

        .nav-bar .candidate-name {{
            font-size: 1.1em;
            font-weight: bold;
            color: var(--party-color);
        }}

        .nav-bar .party-badge {{
            background: var(--party-color);
            color: var(--text-on-primary);
            padding: 5px 12px;
            border-radius: 20px;
            font-size: 0.85em;
            font-weight: 600;
        }}

        /* Hero Section */
        .hero-section {{
            margin-top: 60px;
            background: var(--party-gradient);
            color: var(--text-on-primary);
            padding: 40px 20px;
            text-align: center;
            position: relative;
            overflow: hidden;
        }}

        .hero-content {{
            position: relative;
            z-index: 1;
        }}

        .hero-number {{
            display: inline-block;
            background: rgba(255,255,255,0.2);
            padding: 8px 24px;
            border-radius: 24px;
            font-size: 1.5em;
            font-weight: 900;
            margin-bottom: 15px;
            backdrop-filter: blur(10px);
        }}

        .hero-slogan {{
            font-size: 1.8em;
            font-weight: 900;
            margin-bottom: 10px;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
        }}

        .hero-name {{
            font-size: 2.5em;
            font-weight: 900;
            margin: 15px 0;
        }}

        .hero-position {{
            font-size: 1em;
            opacity: 0.9;
        }}

        /* Vision Section (Accordion Style) */
        .vision-section {{
            background: white;
            margin: 0;
            padding: 25px 20px;
            border-bottom: 1px solid #e0e0e0;
        }}

        .vision-title {{
            font-size: 1.3em;
            font-weight: bold;
            color: var(--party-color);
            text-align: center;
            margin-bottom: 20px;
            padding: 15px;
            background: var(--party-color-light);
            border-radius: 10px;
        }}

        .vision-list {{
            display: flex;
            flex-direction: column;
            gap: 10px;
        }}

        .vision-item {{
            background: #f8f9fa;
            border: 2px solid #e0e0e0;
            border-radius: 12px;
            overflow: hidden;
            transition: all 0.3s;
        }}

        .vision-item.expanded {{
            border-color: var(--party-color);
            box-shadow: 0 4px 15px rgba(0,0,0,0.1);
        }}

        .vision-header {{
            padding: 15px 20px;
            display: flex;
            align-items: center;
            gap: 15px;
            cursor: pointer;
            background: white;
        }}

        .vision-number {{
            font-size: 1.5em;
            font-weight: bold;
            color: var(--party-color);
            min-width: 40px;
            height: 40px;
            display: flex;
            align-items: center;
            justify-content: center;
            background: var(--party-color-light);
            border-radius: 50%;
        }}

        .vision-text {{
            flex: 1;
            font-size: 1em;
            font-weight: 600;
            color: #333;
        }}

        .vision-expand {{
            color: var(--party-color);
            font-size: 1.2em;
            transition: transform 0.3s;
        }}

        .vision-item.expanded .vision-expand {{
            transform: rotate(180deg);
        }}

        .vision-content {{
            padding: 0 20px 15px;
            display: none;
            font-size: 0.95em;
            color: #666;
            line-height: 1.8;
        }}

        .vision-item.expanded .vision-content {{
            display: block;
        }}

        /* Quick Highlights */
        .quick-highlights {{
            display: flex;
            flex-direction: column;
            gap: 12px;
            padding: 25px 20px;
            background: white;
        }}

        .highlight-card {{
            display: flex;
            align-items: center;
            padding: 15px 20px;
            border-radius: 15px;
            background: var(--party-color-light);
            border: 2px solid var(--party-color);
            gap: 15px;
        }}

        .highlight-card .icon {{
            font-size: 2em;
            min-width: 50px;
            text-align: center;
        }}

        .highlight-card .content {{
            flex: 1;
        }}

        .highlight-card .number {{
            font-size: 1.5em;
            font-weight: bold;
            color: var(--party-color);
        }}

        .highlight-card .label {{
            font-size: 1em;
            font-weight: 600;
            color: #333;
        }}

        /* Section Container */
        .section {{
            background: white;
            margin: 15px 0;
            padding: 25px 20px;
        }}

        .section-title {{
            font-size: 1.4em;
            font-weight: bold;
            color: var(--party-color);
            margin-bottom: 20px;
            padding-bottom: 10px;
            border-bottom: 3px solid var(--party-color);
            display: flex;
            align-items: center;
            gap: 10px;
        }}

        .section-title .icon {{
            font-size: 1.2em;
        }}

        /* Promise Cards */
        .promise-list {{
            display: grid;
            gap: 15px;
        }}

        .promise-card {{
            background: white;
            border: 2px solid #e0e0e0;
            border-radius: 15px;
            overflow: hidden;
            transition: all 0.3s;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }}

        .promise-card.expanded {{
            border-color: var(--party-color);
            box-shadow: 0 5px 20px rgba(0,0,0,0.15);
        }}

        .promise-header {{
            padding: 20px;
            background: var(--party-color-light);
            cursor: pointer;
            display: flex;
            align-items: center;
            gap: 15px;
        }}

        .promise-number {{
            font-size: 1.8em;
            font-weight: 900;
            color: var(--party-color);
            min-width: 50px;
            text-align: center;
        }}

        .promise-header-text {{
            flex: 1;
        }}

        .promise-title {{
            font-size: 1.1em;
            font-weight: bold;
            color: #333;
        }}

        .promise-details {{
            padding: 20px;
            display: none;
            background: #f8f9fa;
        }}

        .promise-card.expanded .promise-details {{
            display: block;
        }}

        .promise-details ul {{
            list-style: none;
            margin: 0;
            padding: 0;
        }}

        .promise-details li {{
            padding: 12px 0;
            padding-left: 25px;
            position: relative;
            border-bottom: 1px solid #e0e0e0;
        }}

        .promise-details li:before {{
            content: '✓';
            position: absolute;
            left: 0;
            color: var(--party-color);
            font-weight: bold;
        }}

        .promise-details li:last-child {{
            border-bottom: none;
        }}

        .expand-btn {{
            text-align: center;
            color: var(--party-color);
            font-weight: 600;
            padding: 10px;
            font-size: 0.9em;
        }}

        .expand-btn::after {{
            content: ' ▼';
        }}

        .promise-card.expanded .expand-btn::after {{
            content: ' ▲';
        }}

        /* Timeline */
        .timeline {{
            position: relative;
            padding-left: 30px;
        }}

        .timeline::before {{
            content: '';
            position: absolute;
            left: 10px;
            top: 0;
            bottom: 0;
            width: 3px;
            background: var(--party-color);
        }}

        .timeline-item {{
            position: relative;
            margin-bottom: 25px;
            padding-left: 20px;
        }}

        .timeline-item::before {{
            content: '';
            position: absolute;
            left: -24px;
            top: 5px;
            width: 15px;
            height: 15px;
            background: var(--party-color);
            border-radius: 50%;
            border: 3px solid white;
            box-shadow: 0 0 0 2px var(--party-color);
        }}

        .timeline-year {{
            font-size: 0.85em;
            color: var(--party-color);
            font-weight: 600;
            margin-bottom: 5px;
        }}

        .timeline-content {{
            font-size: 1em;
            color: #333;
            line-height: 1.5;
        }}

        /* Page Content */
        .page-content {{
            background: #f8f9fa;
            padding: 20px;
            border-radius: 10px;
            margin-bottom: 15px;
            border-left: 4px solid var(--party-color);
        }}

        .page-content h4 {{
            color: var(--party-color);
            margin-bottom: 10px;
            font-size: 1.1em;
        }}

        .page-content p {{
            margin-bottom: 10px;
            line-height: 1.7;
        }}

        /* Contact Section */
        .contact-links {{
            display: flex;
            flex-wrap: wrap;
            gap: 10px;
            margin-top: 15px;
        }}

        .contact-link {{
            display: inline-flex;
            align-items: center;
            gap: 8px;
            padding: 10px 15px;
            border-radius: 25px;
            text-decoration: none;
            font-weight: 500;
            transition: all 0.3s;
        }}

        .contact-link.phone {{
            background: var(--party-color);
            color: var(--text-on-primary);
        }}

        .contact-link.facebook {{
            background: #1877F2;
            color: white;
        }}

        .contact-link.instagram {{
            background: linear-gradient(45deg, #f09433, #e6683c, #dc2743, #cc2366, #bc1888);
            color: white;
        }}

        .contact-link.youtube {{
            background: #FF0000;
            color: white;
        }}

        .contact-link.blog {{
            background: #03C75A;
            color: white;
        }}

        /* Bottom Navigation */
        .bottom-nav {{
            position: fixed;
            bottom: 0;
            left: 0;
            right: 0;
            background: white;
            box-shadow: 0 -2px 10px rgba(0,0,0,0.1);
            display: flex;
            justify-content: space-around;
            padding: 10px 0;
            z-index: 1000;
        }}

        .bottom-nav a {{
            display: flex;
            flex-direction: column;
            align-items: center;
            text-decoration: none;
            color: #666;
            font-size: 0.75em;
            padding: 5px 15px;
            transition: all 0.3s;
        }}

        .bottom-nav a.active {{
            color: var(--party-color);
        }}

        .bottom-nav .nav-icon {{
            font-size: 1.5em;
            margin-bottom: 3px;
        }}

        /* Footer */
        .footer {{
            text-align: center;
            padding: 30px 20px;
            background: white;
            margin-top: 15px;
            color: #666;
            font-size: 0.85em;
        }}

        .footer a {{
            color: var(--party-color);
            text-decoration: none;
        }}

        /* Auto Badge */
        .auto-badge {{
            position: fixed;
            top: 70px;
            right: 10px;
            background: linear-gradient(135deg, #10B981, #059669);
            color: white;
            padding: 5px 10px;
            border-radius: 15px;
            font-size: 0.7em;
            font-weight: 600;
            z-index: 999;
            box-shadow: 0 2px 8px rgba(16, 185, 129, 0.4);
        }}

        /* v2.0: Region Map Styles */
        {region_map_styles}

        /* 이미지 갤러리 스타일 */
        {image_styles}
    </style>
</head>
<body>
    <!-- Auto Generation Badge -->
    <div class="auto-badge">AUTO</div>

    <!-- Fixed Top Navigation -->
    <nav class="nav-bar">
        <span class="candidate-name">{candidate.name or '후보'}</span>
        <span class="party-badge">{candidate.party or '정당'}</span>
    </nav>

    <!-- Hero Section -->
    <section class="hero-section" id="home">
        <div class="hero-content">
            <div class="hero-number">기호 {candidate.symbol or '?'}</div>
            <h1 class="hero-name">{candidate.name or '후보'}</h1>
            <p class="hero-slogan">{candidate.slogan or ''}</p>
            <p class="hero-position">{candidate.position or ''} {candidate.district or ''}</p>
        </div>
    </section>

    <!-- 대표 이미지 (폴더 첫 번째 이미지) -->
    {hero_image}

    <!-- Vision Section -->
    {vision_html}

    <!-- Quick Highlights -->
    <div class="quick-highlights">
        {highlights_html}
    </div>

    <!-- Pledges Section -->
    <section class="section" id="pledges">
        <h2 class="section-title"><span class="icon">📋</span> 핵심 공약</h2>
        <div class="promise-list">
            {pledges_html}
        </div>
    </section>

    <!-- v2.0: Region Map Section -->
    {region_map_html}

    <!-- Career Section -->
    <section class="section" id="career">
        <h2 class="section-title"><span class="icon">📜</span> 주요 경력</h2>
        <div class="timeline">
            {careers_html}
        </div>
    </section>

    <!-- Full Text Section -->
    <section class="section" id="fulltext">
        <h2 class="section-title"><span class="icon">📄</span> 전문보기</h2>
        {fulltext_html}
    </section>

    <!-- Image Gallery Section (모든 이미지 모아보기) -->
    {image_gallery_html}

    <!-- Contact Section (맨 마지막) -->
    {contact_html}

    <!-- Footer -->
    <footer class="footer">
        <p>본 페이지는 PDF 선거공보물에서 자동 생성되었습니다.</p>
        <p style="margin-top: 10px;"><a href="https://studysnap.kr" target="_blank">StudySnap</a> | 완전 자동화 변환</p>
    </footer>

    <!-- Bottom Navigation -->
    <nav class="bottom-nav">
        <a href="#home" class="active">
            <span class="nav-icon">🏠</span>
            홈
        </a>
        <a href="#pledges">
            <span class="nav-icon">📋</span>
            공약
        </a>
        <a href="#career">
            <span class="nav-icon">📜</span>
            경력
        </a>
        <a href="#fulltext">
            <span class="nav-icon">📄</span>
            전문
        </a>
    </nav>

    <script>
        // Promise card toggle
        document.querySelectorAll('.promise-card').forEach(card => {{
            card.addEventListener('click', () => {{
                card.classList.toggle('expanded');
            }});
        }});

        // Vision item toggle
        document.querySelectorAll('.vision-item').forEach(item => {{
            item.querySelector('.vision-header').addEventListener('click', () => {{
                item.classList.toggle('expanded');
            }});
        }});

        // Bottom navigation scroll spy
        const sections = ['home', 'pledges', 'career', 'fulltext'];
        const navLinks = document.querySelectorAll('.bottom-nav a');

        window.addEventListener('scroll', () => {{
            let current = '';
            sections.forEach(id => {{
                const section = document.getElementById(id);
                if (section && window.scrollY >= section.offsetTop - 100) {{
                    current = id;
                }}
            }});

            navLinks.forEach(link => {{
                link.classList.remove('active');
                if (link.getAttribute('href') === '#' + current) {{
                    link.classList.add('active');
                }}
            }});
        }});

        // Smooth scroll
        navLinks.forEach(link => {{
            link.addEventListener('click', (e) => {{
                e.preventDefault();
                const targetId = link.getAttribute('href').substring(1);
                const target = document.getElementById(targetId);
                if (target) {{
                    window.scrollTo({{
                        top: target.offsetTop - 60,
                        behavior: 'smooth'
                    }});
                }}
            }});
        }});

        // v2.0: Region Map Script
        {region_map_script}

        // 이미지 갤러리 스크립트
        {image_script}
    </script>
</body>
</html>'''

        # 능동형 AI 학습 엔진: 학습된 규칙 적용
        if ACTIVE_LEARNING_AVAILABLE:
            try:
                learning_engine = get_learning_engine()
                # 선거공보 카테고리로 학습된 규칙 적용
                html_output, applied_rules = learning_engine.apply_rules_to_html(
                    html_output, category="선거공보"
                )
                if applied_rules:
                    logger.info(f"🧠 학습된 규칙 {len(applied_rules)}개 적용됨: {', '.join(applied_rules)}")
                else:
                    logger.debug("적용할 학습된 규칙 없음")
            except Exception as e:
                logger.warning(f"학습 규칙 적용 실패: {e}")

        return html_output

    def _generate_vision_html(self, vision: Vision) -> str:
        """비전 섹션 HTML 생성 (아코디언 방식)"""
        if not vision.title and not vision.items:
            return ""

        html = '<section class="vision-section" id="vision">'

        # 비전 제목
        if vision.title:
            html += f'<div class="vision-title">{self._escape_html(vision.title)}</div>'

        # 비전 항목들 (아코디언)
        if vision.items:
            html += '<div class="vision-list">'
            for i, item in enumerate(vision.items, 1):
                html += f'''
                <div class="vision-item">
                    <div class="vision-header">
                        <span class="vision-number">{i}</span>
                        <span class="vision-text">{self._escape_html(item)}</span>
                        <span class="vision-expand">▼</span>
                    </div>
                    <div class="vision-content">
                        <p>{self._escape_html(item)}</p>
                    </div>
                </div>'''
            html += '</div>'

        html += '</section>'
        return html

    def _generate_highlights_html(self, brochure: ElectionBrochure) -> str:
        """하이라이트 HTML 생성"""
        pledge_count = len(brochure.core_pledges)
        career_count = len(brochure.careers)

        return f'''
        <div class="highlight-card">
            <span class="icon">🎯</span>
            <div class="content">
                <span class="number">{pledge_count}개</span>
                <div class="label">핵심 공약</div>
            </div>
        </div>
        <div class="highlight-card">
            <span class="icon">📋</span>
            <div class="content">
                <span class="number">{career_count}건</span>
                <div class="label">주요 경력</div>
            </div>
        </div>'''

    def _generate_pledges_html(self, pledges: List[Pledge]) -> str:
        """공약 카드 HTML 생성"""
        if not pledges:
            return '<p style="color:#666; text-align:center; padding:20px;">공약 정보를 추출할 수 없습니다.</p>'

        html = ""
        for i, pledge in enumerate(pledges[:20], 1):
            title = self._escape_html(pledge.title)

            details_html = ""
            if pledge.details:
                details_html = "<ul>"
                for detail in pledge.details:
                    details_html += f"<li>{self._escape_html(detail)}</li>"
                details_html += "</ul>"
            else:
                details_html = f"<p>{title}</p>"

            html += f'''
            <div class="promise-card">
                <div class="promise-header">
                    <span class="promise-number">{i}</span>
                    <div class="promise-header-text">
                        <div class="promise-title">{title}</div>
                    </div>
                </div>
                <div class="promise-details">
                    {details_html}
                </div>
                <div class="expand-btn">상세 보기</div>
            </div>'''

        return html

    def _generate_careers_html(self, careers: List[Career]) -> str:
        """경력 타임라인 HTML 생성"""
        if not careers:
            return '<p style="color:#666; text-align:center; padding:20px;">경력 정보를 추출할 수 없습니다.</p>'

        html = ""
        for career in careers[:15]:
            period = self._escape_html(career.period)
            description = self._escape_html(career.description)

            html += f'''
            <div class="timeline-item">
                <div class="timeline-year">{period}</div>
                <div class="timeline-content">{description}</div>
            </div>'''

        return html

    def _generate_contact_html(self, contact: ContactInfo) -> str:
        """연락처 섹션 HTML 생성"""
        # 아무 정보도 없으면 빈 문자열 반환
        has_any_info = (contact.phone or contact.raw_text or contact.facebook or
                        contact.instagram or contact.youtube or contact.blog or
                        contact.office_address)
        if not has_any_info:
            return ""

        links_html = ""

        # 선거사무소 정보 (SNS가 없을 때 우선 표시)
        if contact.office_address:
            links_html += f'<div class="contact-link office" style="background:#f0f9ff; border-color:#0ea5e9;">📍 {self._escape_html(contact.office_address)}</div>'

        if contact.phone:
            links_html += f'<a href="tel:{contact.phone}" class="contact-link phone">📞 {contact.phone}</a>'

        if contact.facebook:
            links_html += f'<a href="{contact.facebook}" target="_blank" class="contact-link facebook">📘 Facebook</a>'

        if contact.instagram:
            links_html += f'<a href="{contact.instagram}" target="_blank" class="contact-link instagram">📷 Instagram</a>'

        if contact.youtube:
            links_html += f'<a href="{contact.youtube}" target="_blank" class="contact-link youtube">▶️ YouTube</a>'

        if contact.blog:
            links_html += f'<a href="{contact.blog}" target="_blank" class="contact-link blog">📝 Blog</a>'

        raw_text_html = ""
        if contact.raw_text:
            raw_text_html = f'<div style="margin-top:15px; padding:15px; background:#f8f9fa; border-radius:10px; line-height:1.8;">{self._escape_html(contact.raw_text).replace(chr(10), "<br>")}</div>'

        return f'''
    <section class="section" id="contact">
        <h2 class="section-title"><span class="icon">📞</span> 연락처 / 선거사무소</h2>
        <div class="contact-links">
            {links_html}
        </div>
        {raw_text_html}
    </section>'''

    def _generate_fulltext_html(self, pages: List[Dict]) -> str:
        """전문보기 HTML 생성"""
        if not pages:
            return ""

        html = ""
        for page in pages:
            page_num = page.get("page_number", 1)
            text = page.get("text", "").strip()

            if text:
                formatted_text = self._escape_html(text).replace("\n", "<br>")
                html += f'''
        <div class="page-content">
            <h4>📄 페이지 {page_num}</h4>
            <p>{formatted_text}</p>
        </div>'''

        return html

    def _escape_html(self, text: str) -> str:
        """HTML 이스케이프"""
        if not text:
            return ""
        return text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')

    def _get_folder_images(self, folder_path: str) -> List[Dict[str, str]]:
        """폴더에서 이미지 파일 목록 가져오기 (HTML 파일 제외)"""
        if not folder_path:
            return []

        folder = Path(folder_path)
        if not folder.exists():
            return []

        images = []
        image_extensions = {'.png', '.jpg', '.jpeg', '.gif', '.webp'}

        for file in folder.iterdir():
            if file.is_file() and file.suffix.lower() in image_extensions:
                images.append({
                    'filename': file.name,
                    'path': f'./{file.name}',  # 상대 경로
                    'name': file.stem  # 파일명 (확장자 제외)
                })

        # 파일명으로 정렬 (1-xxx, 2-xxx 순서)
        images.sort(key=lambda x: x['filename'])
        return images

    def _generate_image_gallery_html(self, images: List[Dict[str, str]]) -> str:
        """이미지 갤러리 섹션 HTML 생성"""
        if not images:
            return ""

        gallery_html = '''
    <!-- 이미지 갤러리 -->
    <section class="section" id="gallery">
        <h2 class="section-title"><span class="icon">📸</span> 주요 이미지</h2>
        <div class="image-gallery">
'''
        for img in images:
            gallery_html += f'''
            <div class="gallery-item" onclick="showFullImage('{img['path']}')">
                <img src="{img['path']}" alt="{img['name']}" loading="lazy">
            </div>
'''
        gallery_html += '''
        </div>
    </section>
'''
        return gallery_html

    def _generate_inline_image_html(self, image: Dict[str, str], position: str = "center") -> str:
        """문맥에 맞는 인라인 이미지 HTML 생성"""
        align_style = {
            "center": "margin: 20px auto; display: block;",
            "left": "float: left; margin: 0 20px 15px 0;",
            "right": "float: right; margin: 0 0 15px 20px;",
            "full": "width: 100%; margin: 20px 0;"
        }.get(position, "margin: 20px auto; display: block;")

        return f'''
        <div class="inline-image" style="{align_style}">
            <img src="{image['path']}" alt="{image['name']}"
                 style="max-width: 100%; height: auto; border-radius: 12px; box-shadow: 0 4px 15px rgba(0,0,0,0.1);"
                 onclick="showFullImage('{image['path']}')">
        </div>
'''

    def _generate_image_styles(self) -> str:
        """이미지 관련 CSS 스타일"""
        return '''
        /* Image Gallery Styles */
        .image-gallery {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: 15px;
            padding: 15px 0;
        }

        .gallery-item {
            border-radius: 12px;
            overflow: hidden;
            box-shadow: 0 4px 15px rgba(0,0,0,0.1);
            cursor: pointer;
            transition: transform 0.3s, box-shadow 0.3s;
        }

        .gallery-item:hover {
            transform: scale(1.02);
            box-shadow: 0 6px 20px rgba(0,0,0,0.15);
        }

        .gallery-item img {
            width: 100%;
            height: auto;
            display: block;
        }

        /* Inline Image */
        .inline-image {
            cursor: pointer;
        }

        .inline-image:hover img {
            opacity: 0.95;
        }

        /* Full Image Modal */
        .image-modal {
            display: none;
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0,0,0,0.9);
            z-index: 9999;
            justify-content: center;
            align-items: center;
        }

        .image-modal.show {
            display: flex;
        }

        .image-modal img {
            max-width: 95%;
            max-height: 95%;
            object-fit: contain;
        }

        .image-modal-close {
            position: absolute;
            top: 20px;
            right: 20px;
            color: white;
            font-size: 40px;
            cursor: pointer;
            z-index: 10000;
        }
'''

    def _generate_image_script(self) -> str:
        """이미지 관련 JavaScript"""
        return '''
        // Full Image Modal
        function showFullImage(src) {
            let modal = document.getElementById('imageModal');
            if (!modal) {
                modal = document.createElement('div');
                modal.id = 'imageModal';
                modal.className = 'image-modal';
                modal.innerHTML = `
                    <span class="image-modal-close" onclick="closeImageModal()">&times;</span>
                    <img id="modalImage" src="" alt="Full Image">
                `;
                modal.onclick = function(e) {
                    if (e.target === modal) closeImageModal();
                };
                document.body.appendChild(modal);
            }
            document.getElementById('modalImage').src = src;
            modal.classList.add('show');
            document.body.style.overflow = 'hidden';
        }

        function closeImageModal() {
            const modal = document.getElementById('imageModal');
            if (modal) {
                modal.classList.remove('show');
                document.body.style.overflow = '';
            }
        }

        // Escape key to close modal
        document.addEventListener('keydown', function(e) {
            if (e.key === 'Escape') closeImageModal();
        });
'''


# 테스트
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    converter = AutoElectionConverter()

    test_pdf = r"C:\Users\jmyang\Downloads\나경원.pdf"
    if os.path.exists(test_pdf):
        print("완전 자동화 변환 테스트...")
        brochure = converter.convert(test_pdf)

        print(f"\n=== 변환 결과 ===")
        print(f"후보자: {brochure.candidate.name}")
        print(f"정당: {brochure.candidate.party}")
        print(f"기호: {brochure.candidate.symbol}")
        print(f"공약 수: {len(brochure.core_pledges)}")
        print(f"경력 수: {len(brochure.careers)}")

        # HTML 생성
        html = converter.generate_html(brochure)
        print(f"\nHTML 길이: {len(html)} 문자")
    else:
        print(f"테스트 PDF 없음: {test_pdf}")
