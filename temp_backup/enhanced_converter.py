"""
향상된 선거공보물 변환 엔진 v2.0
- 후보 유형별 템플릿 (광역단체장/기초단체장/국회의원)
- 지역별 지도 자동 생성
- OCR 후처리 및 오타 수정
- 공약 수 자동 감지
"""

import re
import json
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class CandidateType(Enum):
    """후보자 유형"""
    METROPOLITAN_MAYOR = "광역단체장"  # 시장, 도지사
    BASIC_MAYOR = "기초단체장"  # 구청장, 군수
    NATIONAL_ASSEMBLY = "국회의원"
    PROVINCIAL_COUNCIL = "광역의원"  # 시도의원
    LOCAL_COUNCIL = "기초의원"  # 구시군의원
    PRESIDENT = "대통령"
    UNKNOWN = "미확인"


@dataclass
class RegionInfo:
    """지역 정보"""
    name: str  # 지역명 (서울시, 동작구 등)
    type: str  # metro, district, dong
    parent: str = ""  # 상위 지역
    sub_regions: List[str] = field(default_factory=list)  # 하위 지역 (시군구, 동)


# ============================================================
# 지역 데이터베이스
# ============================================================

KOREA_REGIONS = {
    # 광역시/도
    "서울특별시": {
        "type": "metro",
        "districts": ["종로구", "중구", "용산구", "성동구", "광진구", "동대문구", "중랑구",
                     "성북구", "강북구", "도봉구", "노원구", "은평구", "서대문구", "마포구",
                     "양천구", "강서구", "구로구", "금천구", "영등포구", "동작구", "관악구",
                     "서초구", "강남구", "송파구", "강동구"]
    },
    "부산광역시": {
        "type": "metro",
        "districts": ["중구", "서구", "동구", "영도구", "부산진구", "동래구", "남구", "북구",
                     "해운대구", "사하구", "금정구", "강서구", "연제구", "수영구", "사상구", "기장군"]
    },
    "대구광역시": {
        "type": "metro",
        "districts": ["중구", "동구", "서구", "남구", "북구", "수성구", "달서구", "달성군"]
    },
    "인천광역시": {
        "type": "metro",
        "districts": ["중구", "동구", "미추홀구", "연수구", "남동구", "부평구", "계양구", "서구", "강화군", "옹진군"]
    },
    "광주광역시": {
        "type": "metro",
        "districts": ["동구", "서구", "남구", "북구", "광산구"]
    },
    "대전광역시": {
        "type": "metro",
        "districts": ["동구", "중구", "서구", "유성구", "대덕구"]
    },
    "울산광역시": {
        "type": "metro",
        "districts": ["중구", "남구", "동구", "북구", "울주군"]
    },
    "세종특별자치시": {
        "type": "metro",
        "districts": []
    },
    "경기도": {
        "type": "province",
        "districts": ["수원시", "성남시", "의정부시", "안양시", "부천시", "광명시", "평택시", "동두천시",
                     "안산시", "고양시", "과천시", "구리시", "남양주시", "오산시", "시흥시", "군포시",
                     "의왕시", "하남시", "용인시", "파주시", "이천시", "안성시", "김포시", "화성시",
                     "광주시", "양주시", "포천시", "여주시", "연천군", "가평군", "양평군"]
    },
    "강원도": {
        "type": "province",
        "districts": ["춘천시", "원주시", "강릉시", "동해시", "태백시", "속초시", "삼척시",
                     "홍천군", "횡성군", "영월군", "평창군", "정선군", "철원군", "화천군",
                     "양구군", "인제군", "고성군", "양양군"]
    },
    "충청북도": {
        "type": "province",
        "districts": ["청주시", "충주시", "제천시", "보은군", "옥천군", "영동군", "증평군",
                     "진천군", "괴산군", "음성군", "단양군"]
    },
    "충청남도": {
        "type": "province",
        "districts": ["천안시", "공주시", "보령시", "아산시", "서산시", "논산시", "계룡시",
                     "당진시", "금산군", "부여군", "서천군", "청양군", "홍성군", "예산군", "태안군"]
    },
    "전라북도": {
        "type": "province",
        "districts": ["전주시", "군산시", "익산시", "정읍시", "남원시", "김제시",
                     "완주군", "진안군", "무주군", "장수군", "임실군", "순창군", "고창군", "부안군"]
    },
    "전라남도": {
        "type": "province",
        "districts": ["목포시", "여수시", "순천시", "나주시", "광양시",
                     "담양군", "곡성군", "구례군", "고흥군", "보성군", "화순군", "장흥군",
                     "강진군", "해남군", "영암군", "무안군", "함평군", "영광군", "장성군",
                     "완도군", "진도군", "신안군"]
    },
    "경상북도": {
        "type": "province",
        "districts": ["포항시", "경주시", "김천시", "안동시", "구미시", "영주시", "영천시",
                     "상주시", "문경시", "경산시", "군위군", "의성군", "청송군", "영양군",
                     "영덕군", "청도군", "고령군", "성주군", "칠곡군", "예천군", "봉화군", "울진군", "울릉군"]
    },
    "경상남도": {
        "type": "province",
        "districts": ["창원시", "진주시", "통영시", "사천시", "김해시", "밀양시", "거제시",
                     "양산시", "의령군", "함안군", "창녕군", "고성군", "남해군", "하동군",
                     "산청군", "함양군", "거창군", "합천군"]
    },
    "제주특별자치도": {
        "type": "province",
        "districts": ["제주시", "서귀포시"]
    }
}

# 동작구 동 목록 (예시)
DONGJAK_DONGS = ["노량진1동", "노량진2동", "상도1동", "상도2동", "상도3동", "상도4동",
                 "흑석동", "사당1동", "사당2동", "사당3동", "사당4동", "사당5동",
                 "대방동", "신대방1동", "신대방2동"]


# ============================================================
# OCR 오타 수정 사전
# ============================================================

OCR_CORRECTIONS = {
    # 일반적인 OCR 오류
    "대톨형": "대통령",
    "대통렁": "대통령",
    "국회의웜": "국회의원",
    "국회의연": "국회의원",
    "시쟝": "시장",
    "도지샤": "도지사",
    "노지샤": "도지사",
    "구청쟝": "구청장",
    "굼수": "군수",
    "박냥훈": "박남훈",
    "흉준표": "홍준표",
    "세흩시함": "세종시장",
    "정의당입": "정의당",
    "북도지사": "도지사",
    "인대통령": "대통령",
    "로서": "후보",

    # 정당명 오류
    "국민의햄": "국민의힘",
    "더불어민주딩": "더불어민주당",
    "민주딩": "민주당",
    "정의딩": "정의당",
    "녹색딩": "녹색당",
    "진보딩": "진보당",

    # 지역명 오류
    "동작굼": "동작구",
    "강남굼": "강남구",
    "서초굼": "서초구",
}


class EnhancedConverter:
    """향상된 선거공보물 변환기"""

    def __init__(self):
        self.ocr_corrections = OCR_CORRECTIONS.copy()

    def detect_candidate_type(self, text: str, position: str = "") -> CandidateType:
        """후보자 유형 감지"""
        text_lower = text.lower()
        position_lower = position.lower() if position else ""

        # 직위 기반 감지
        if any(x in position_lower for x in ["대통령"]):
            return CandidateType.PRESIDENT
        elif any(x in position_lower for x in ["도지사", "시장"]) and any(x in text for x in KOREA_REGIONS.keys()):
            return CandidateType.METROPOLITAN_MAYOR
        elif any(x in position_lower for x in ["구청장", "군수", "시장"]):
            return CandidateType.BASIC_MAYOR
        elif any(x in position_lower for x in ["국회의원"]):
            return CandidateType.NATIONAL_ASSEMBLY
        elif any(x in position_lower for x in ["시의원", "도의원", "광역의원"]):
            return CandidateType.PROVINCIAL_COUNCIL
        elif any(x in position_lower for x in ["구의원", "군의원", "시의원", "기초의원"]):
            return CandidateType.LOCAL_COUNCIL

        # 텍스트 기반 감지
        if "도지사" in text or any(f"{r} 시장" in text for r in ["서울", "부산", "대구", "인천", "광주", "대전", "울산"]):
            return CandidateType.METROPOLITAN_MAYOR
        elif "구청장" in text or "군수" in text:
            return CandidateType.BASIC_MAYOR
        elif "국회의원" in text:
            return CandidateType.NATIONAL_ASSEMBLY

        return CandidateType.UNKNOWN

    def detect_region(self, text: str) -> Tuple[Optional[str], Optional[str]]:
        """지역 감지 (광역, 기초) - 정확한 패턴 매칭"""
        metro = None
        district = None

        # 광역시/도 감지 - 직함과 함께 사용된 패턴 우선
        # "대구광역시장", "대구시장", "서울시장" 등의 패턴 먼저 검색
        position_patterns = [
            (r'(서울특별시|서울시|서울)\s*시장', "서울특별시"),
            (r'(부산광역시|부산시|부산)\s*시장', "부산광역시"),
            (r'(대구광역시|대구시|대구)\s*시장', "대구광역시"),
            (r'(인천광역시|인천시|인천)\s*시장', "인천광역시"),
            (r'(광주광역시|광주시|광주)\s*시장', "광주광역시"),
            (r'(대전광역시|대전시|대전)\s*시장', "대전광역시"),
            (r'(울산광역시|울산시|울산)\s*시장', "울산광역시"),
            (r'(세종특별자치시|세종시|세종)\s*시장', "세종특별자치시"),
            (r'(경기도|경기)\s*도지사|경기\s*지사', "경기도"),
            (r'(강원도|강원)\s*도지사|강원\s*지사', "강원도"),
            (r'(충청북도|충북)\s*도지사|충북\s*지사', "충청북도"),
            (r'(충청남도|충남)\s*도지사|충남\s*지사', "충청남도"),
            (r'(전라북도|전북)\s*도지사|전북\s*지사', "전라북도"),
            (r'(전라남도|전남)\s*도지사|전남\s*지사', "전라남도"),
            (r'(경상북도|경북)\s*도지사|경북\s*지사', "경상북도"),
            (r'(경상남도|경남)\s*도지사|경남\s*지사', "경상남도"),
            (r'(제주특별자치도|제주도|제주)\s*도지사|제주\s*지사', "제주특별자치도"),
        ]

        for pattern, region in position_patterns:
            if re.search(pattern, text):
                metro = region
                break

        # 직함 패턴 매칭 실패 시 일반 지역명 검색
        if not metro:
            # 전체 광역시/도명을 길이 역순으로 정렬 (긴 것 먼저 매칭)
            sorted_regions = sorted(KOREA_REGIONS.keys(), key=len, reverse=True)
            for region_name in sorted_regions:
                if region_name in text:
                    metro = region_name
                    break
                # 축약형 검색
                short_name = region_name.replace("특별시", "").replace("광역시", "시").replace("특별자치시", "시").replace("특별자치도", "도")
                if short_name in text and short_name not in ["도", "시"]:
                    metro = region_name
                    break

        # 기초단체 감지 (구청장, 군수 등)
        if metro and metro in KOREA_REGIONS:
            districts = KOREA_REGIONS[metro].get("districts", [])
            # 길이 역순 정렬 (긴 것 먼저)
            sorted_districts = sorted(districts, key=len, reverse=True)
            for dist in sorted_districts:
                # "동작구청장", "동작구 구청장" 등 패턴 검색
                if dist in text:
                    district = dist
                    break

        return metro, district

    def correct_ocr_errors(self, text: str) -> str:
        """OCR 오류 수정"""
        corrected = text
        for wrong, correct in self.ocr_corrections.items():
            corrected = corrected.replace(wrong, correct)
        return corrected

    def extract_pledge_count(self, text: str) -> int:
        """공약 개수 추출"""
        # "5대 공약", "6대 핵심공약" 등 패턴
        patterns = [
            r'(\d+)\s*대\s*공약',
            r'(\d+)\s*대\s*핵심',
            r'핵심\s*공약\s*(\d+)',
            r'(\d+)\s*가지\s*공약',
        ]

        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                return int(match.group(1))

        return 0  # 감지 실패

    def get_sub_regions(self, candidate_type: CandidateType, metro: str, district: str = None) -> List[str]:
        """후보 유형에 따른 하위 지역 목록 반환"""
        if candidate_type == CandidateType.METROPOLITAN_MAYOR:
            # 광역단체장: 시군구 목록
            if metro in KOREA_REGIONS:
                return KOREA_REGIONS[metro].get("districts", [])
        elif candidate_type == CandidateType.BASIC_MAYOR:
            # 기초단체장: 동 목록 (예시: 동작구)
            if district == "동작구":
                return DONGJAK_DONGS
            # 다른 구의 동 목록도 추가 가능
        elif candidate_type == CandidateType.NATIONAL_ASSEMBLY:
            # 국회의원: 선거구 내 동 목록
            if district:
                return self._get_constituency_dongs(district)

        return []

    def _get_constituency_dongs(self, district: str) -> List[str]:
        """선거구 내 동 목록 (나경원 사례처럼 일부 동만)"""
        # 실제로는 선거구별 데이터가 필요
        # 예시: 동작구을 = 상도1동, 흑석동, 사당1~5동
        constituency_map = {
            "동작구을": ["상도1동", "흑석동", "사당1동", "사당2동", "사당3동", "사당4동", "사당5동"],
            "동작구갑": ["노량진1동", "노량진2동", "상도2동", "상도3동", "상도4동", "대방동", "신대방1동", "신대방2동"],
        }
        return constituency_map.get(district, [])

    def generate_region_map_svg(self, regions: List[str], region_type: str = "district") -> str:
        """지역 지도 SVG 생성"""
        if not regions:
            return ""

        num_regions = len(regions)

        # 그리드 계산
        if num_regions <= 4:
            cols, rows = 2, 2
        elif num_regions <= 6:
            cols, rows = 3, 2
        elif num_regions <= 9:
            cols, rows = 3, 3
        elif num_regions <= 12:
            cols, rows = 4, 3
        elif num_regions <= 16:
            cols, rows = 4, 4
        else:
            cols, rows = 5, (num_regions + 4) // 5

        cell_width = 340 // cols
        cell_height = 260 // rows
        padding = 5

        paths = []
        labels = []

        for i, region in enumerate(regions):
            row = i // cols
            col = i % cols

            x = 10 + col * cell_width + padding
            y = 10 + row * cell_height + padding
            w = cell_width - padding * 2
            h = cell_height - padding * 2

            # 사각형 path
            path = f'<path class="district-area" data-district="{region}" d="M{x},{y} L{x+w},{y} L{x+w},{y+h} L{x},{y+h} Z" onclick="selectDistrict(\'{region}\')"/>'
            paths.append(path)

            # 라벨
            label_x = x + w // 2
            label_y = y + h // 2 + 5
            # 긴 이름 축약
            display_name = region.replace("동", "").replace("구", "").replace("시", "").replace("군", "")
            if len(display_name) > 4:
                display_name = display_name[:4]
            label = f'<text class="district-label" x="{label_x}" y="{label_y}">{display_name}</text>'
            labels.append(label)

        svg = f'''<svg viewBox="0 0 360 280" preserveAspectRatio="xMidYMid meet">
            <!-- 자동 생성된 {region_type} 지도 ({num_regions}개 지역) -->
            {"".join(paths)}
            {"".join(labels)}
        </svg>'''

        return svg

    def generate_region_pledges_html(self, regions: List[str], pledges_by_region: Dict[str, str] = None) -> str:
        """지역별 공약 정보 HTML 생성"""
        if not regions:
            return ""

        pledges_by_region = pledges_by_region or {}

        info_divs = []
        for region in regions:
            pledge_text = pledges_by_region.get(region, "지역 맞춤 공약을 준비 중입니다.")
            info_div = f'''
        <div class="district-info" id="info-{region}">
            <div class="district-info-title">📍 {region}</div>
            <div class="district-info-content">{pledge_text}</div>
            <div class="btn-group" style="margin-top: 15px;">
                <button class="btn btn-secondary" onclick="showImage('/outputs/district_{region}.png')">📄 원문보기</button>
            </div>
        </div>'''
            info_divs.append(info_div)

        return "\n".join(info_divs)

    def generate_map_section_html(self, candidate_type: CandidateType, regions: List[str],
                                   pledges_by_region: Dict[str, str] = None) -> str:
        """지도 섹션 전체 HTML 생성"""
        if not regions:
            return ""

        # 섹션 제목 결정
        if candidate_type == CandidateType.METROPOLITAN_MAYOR:
            section_title = "시군구별 공약"
            map_description = "지도를 클릭하여 시군구별 공약을 확인하세요"
        elif candidate_type == CandidateType.BASIC_MAYOR:
            section_title = "동별 공약"
            map_description = "지도를 클릭하여 동별 공약을 확인하세요"
        elif candidate_type == CandidateType.NATIONAL_ASSEMBLY:
            section_title = "지역구 공약"
            map_description = "지도를 클릭하여 지역별 공약을 확인하세요"
        else:
            section_title = "지역별 공약"
            map_description = "지도를 클릭하여 지역별 공약을 확인하세요"

        svg_map = self.generate_region_map_svg(regions)
        region_infos = self.generate_region_pledges_html(regions, pledges_by_region)

        return f'''
    <div class="section-title">{section_title}</div>
    <div class="district-map-section">
        <div class="district-map">
            {svg_map}
        </div>
        <p style="text-align: center; font-size: 13px; color: #888; margin-bottom: 15px;">
            {map_description}
        </p>
        {region_infos}
    </div>'''

    def generate_map_styles(self) -> str:
        """지도 관련 CSS 스타일"""
        return '''
        /* 지역별 공약 지도 섹션 */
        .district-map-section {
            background: white;
            border-radius: 15px;
            padding: 15px;
            margin-bottom: 15px;
        }
        .district-map {
            position: relative;
            width: 100%;
            height: 350px;
            background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
            border-radius: 12px;
            margin-bottom: 15px;
            overflow: hidden;
        }
        .district-map svg {
            width: 100%;
            height: 100%;
        }
        .district-area {
            fill: var(--party-color-light, #FEE2E2);
            stroke: var(--party-color, #E11D48);
            stroke-width: 1.5;
            cursor: pointer;
            transition: all 0.3s;
        }
        .district-area:hover {
            fill: var(--party-accent, #FECDD3);
        }
        .district-area.active {
            fill: var(--party-color, #E11D48);
        }
        .district-label {
            font-size: 14px;
            font-weight: 700;
            fill: #333;
            pointer-events: none;
            text-anchor: middle;
        }
        .district-area.active + .district-label {
            fill: white;
        }
        .district-info {
            display: none;
            padding: 15px;
            background: var(--party-color-light, #FFF5F5);
            border-radius: 12px;
            border: 2px solid var(--party-color, #E11D48);
            margin-top: 10px;
        }
        .district-info.active {
            display: block;
        }
        .district-info-title {
            font-size: 18px;
            font-weight: 700;
            color: var(--party-color, #E11D48);
            margin-bottom: 10px;
        }
        .district-info-content {
            font-size: 14px;
            line-height: 1.6;
            color: #333;
        }'''

    def generate_map_script(self) -> str:
        """지도 관련 JavaScript"""
        return '''
// 지역 선택
function selectDistrict(districtName) {
    // 모든 영역 초기화
    document.querySelectorAll('.district-area').forEach(area => {
        area.classList.remove('active');
    });
    document.querySelectorAll('.district-info').forEach(info => {
        info.classList.remove('active');
    });

    // 선택된 영역 활성화
    const selectedArea = document.querySelector(`[data-district="${districtName}"]`);
    if (selectedArea) {
        selectedArea.classList.add('active');
    }

    // 해당 정보 표시
    const infoDiv = document.getElementById(`info-${districtName}`);
    if (infoDiv) {
        infoDiv.classList.add('active');
        infoDiv.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }
}

// 이미지 팝업 표시
function showImage(imageUrl) {
    const modal = document.createElement('div');
    modal.style.cssText = `
        position: fixed; top: 0; left: 0; right: 0; bottom: 0;
        background: rgba(0,0,0,0.9); z-index: 10000;
        display: flex; align-items: center; justify-content: center;
        padding: 20px;
    `;
    modal.innerHTML = `
        <div style="position: relative; max-width: 100%; max-height: 100%;">
            <img src="${imageUrl}" style="max-width: 100%; max-height: 90vh; border-radius: 10px;">
            <button onclick="this.parentElement.parentElement.remove()"
                    style="position: absolute; top: -15px; right: -15px;
                           width: 40px; height: 40px; border-radius: 50%;
                           background: white; border: none; font-size: 24px;
                           cursor: pointer; box-shadow: 0 2px 10px rgba(0,0,0,0.3);">×</button>
        </div>
    `;
    modal.onclick = (e) => { if (e.target === modal) modal.remove(); };
    document.body.appendChild(modal);
}'''


def get_enhanced_converter() -> EnhancedConverter:
    """싱글톤 인스턴스 반환"""
    if not hasattr(get_enhanced_converter, '_instance'):
        get_enhanced_converter._instance = EnhancedConverter()
    return get_enhanced_converter._instance
