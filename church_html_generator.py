"""
교회 주보 전용 HTML 생성기
기존 여의도순복음교회 템플릿(11-16, 11-23) 기반
참조 템플릿의 완성도를 그대로 재현하는 프로덕션 레벨 생성기
"""

import json
import logging
import re
from typing import Dict, List, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class ChurchBulletinGenerator:
    """교회 주보 HTML 생성기"""

    # 기본 교회 정보 (여의도순복음교회)
    DEFAULT_CHURCH_INFO = {
        "name": "여의도순복음교회",
        "name_en": "YOIDO FULL GOSPEL CHURCH",
        "address": "서울특별시 영등포구 국회대로76길 15",
        "founded": "1958년 5월 18일 창립 (설립자 조용기 목사)",
        "phone_day": "02-6181-9191",
        "phone_night": "02-6181-9000~3",
        "website": "https://www.fgtv.com",
        "sns": {
            "youtube": "https://www.youtube.com/user/YFGCFGTV",
            "kakaotalk": "http://pf.kakao.com/_NrTxkK",
            "instagram": "https://www.instagram.com/yfgcprb/"
        },
        "donation_url": "https://m.fgtv.com/donate/donate_m_ver2.asp"
    }

    # CSS 변수 (일반 주일 / 추수감사 테마)
    THEMES = {
        "default": {
            "primary": "#5B4B9E",
            "primary_dark": "#4A3D82",
            "primary_light": "#E8E4F4",
            "accent": "#C9A857",
            "harvest": "#5B4B9E",  # default uses primary
            "header_gradient": "linear-gradient(135deg, #5B4B9E 0%, #4A3D82 100%)",
            "theme_color": "#5B4B9E",
            "is_harvest": False
        },
        "harvest": {  # 추수감사절
            "primary": "#5B4B9E",
            "primary_dark": "#4A3D82",
            "primary_light": "#E8E4F4",
            "accent": "#C9A857",
            "harvest": "#8B6914",
            "accent_warm": "#D4883E",
            "header_gradient": "linear-gradient(135deg, #8B6914 0%, #C9A857 50%, #D4883E 100%)",
            "theme_color": "#8B6914",
            "is_harvest": True
        },
        "christmas": {  # 성탄절
            "primary": "#C41E3A",
            "primary_dark": "#8B0000",
            "primary_light": "#FFE4E1",
            "accent": "#228B22",
            "harvest": "#C41E3A",
            "header_gradient": "linear-gradient(135deg, #C41E3A 0%, #228B22 100%)",
            "theme_color": "#C41E3A",
            "is_harvest": False
        },
        "easter": {  # 부활절
            "primary": "#9370DB",
            "primary_dark": "#663399",
            "primary_light": "#E6E6FA",
            "accent": "#FFD700",
            "harvest": "#9370DB",
            "header_gradient": "linear-gradient(135deg, #9370DB 0%, #FFD700 100%)",
            "theme_color": "#9370DB",
            "is_harvest": False
        }
    }

    def __init__(self, church_info: Dict = None):
        self.church_info = church_info or self.DEFAULT_CHURCH_INFO

    def generate(self, extracted_data: Dict, title: str = "", theme: str = "default") -> str:
        """
        주보 HTML 생성

        Args:
            extracted_data: OCR로 추출된 주보 데이터
            title: 주보 제목
            theme: 테마 (default, harvest, christmas, easter)

        Returns:
            완성된 HTML 문자열
        """
        # 주보 정보 추출
        info = self._extract_bulletin_info(extracted_data)

        # 테마 선택
        theme_vars = self.THEMES.get(theme, self.THEMES["default"])
        is_harvest = theme_vars.get("is_harvest", False)

        # HTML 생성
        html = self._build_html(info, theme_vars, theme, is_harvest)

        return html

    def _extract_bulletin_info(self, extracted_data: Dict) -> Dict:
        """OCR 데이터에서 주보 정보 추출"""
        info = {
            "church_name": self.church_info.get("name", "교회"),
            "church_name_en": self.church_info.get("name_en", ""),
            "date": "",
            "sunday_type": "주일예배",
            "theme": "2025 표어: 오직 말씀으로",
            "verse": {
                "text": "",
                "reference": ""
            },
            "worship_services": [],
            "sermon": {
                "title": "",
                "title_en": "",
                "scripture": "",
                "preacher": "",
                "sections": []  # 설교 본문 섹션 (제목, 내용)
            },
            "choir": [],
            "news": [],
            "devotional": {
                "title": "",
                "content": ""
            },
            "weekly_schedule": [],  # 수요예배, 금요성령대망회, 토요예배
            "bible_verses": {},
            "hymns": {}
        }

        # 구조화된 데이터가 있으면 우선 사용
        structured = extracted_data.get("structured_data", {})
        if structured and ("worship_services" in structured or "today_verse" in structured):
            # Vision OCR에서 추출한 구조화된 데이터 사용
            today_verse = structured.get("today_verse", {})
            if today_verse.get("text"):
                info["verse"]["text"] = today_verse["text"]
            if today_verse.get("reference"):
                info["verse"]["reference"] = today_verse["reference"]

            # 예배 순서
            services = structured.get("worship_services", [])
            if services:
                info["worship_services"] = self._convert_structured_services(services)

            # 설교
            sermon = structured.get("sermon", {})
            if sermon.get("title"):
                info["sermon"]["title"] = sermon["title"]
            if sermon.get("scripture"):
                info["sermon"]["scripture"] = sermon["scripture"]
            if sermon.get("pastor"):
                info["sermon"]["preacher"] = sermon["pastor"]
            if sermon.get("content"):
                content_parts = sermon["content"]
                if isinstance(content_parts, list):
                    info["sermon"]["sections"] = self._parse_sermon_sections(content_parts)
                else:
                    info["sermon"]["sections"] = [{"title": "", "content": content_parts}]

            # 찬양대
            choir_data = structured.get("choir", [])
            if choir_data:
                info["choir"] = choir_data

            # 교회 소식
            news = structured.get("news", [])
            if news:
                info["news"] = self._convert_news_items(news)

        # 페이지별 텍스트에서 추가 정보 추출
        if "pages" in extracted_data:
            full_text = ""
            for page in extracted_data.get("pages", []):
                page_text = page.get("text", "")
                full_text += page_text + "\n"

            # 날짜 추출
            date_match = re.search(r'(\d{4})[.\s]*(\d{1,2})[.\s]*(\d{1,2})', full_text)
            if date_match:
                year, month, day = date_match.groups()
                info["date"] = f"{year}년 {int(month)}월 {int(day)}일"

            # 담임목사 추출 (구조화된 데이터에 없으면)
            if not info["sermon"]["preacher"]:
                pastor_match = re.search(r'(위임목사|담임목사)[:\s]*([가-힣]+)', full_text)
                if pastor_match:
                    info["sermon"]["preacher"] = pastor_match.group(2) + " 목사"

            # 오늘의 말씀 추출 (구조화된 데이터에 없으면)
            if not info["verse"]["text"]:
                verse_patterns = [
                    r"오늘의\s*말씀[:\s]*['\"]?(.+?)['\"]?\s*\(([^)]+)\)",
                    r'[\'"](.+?)[\'"].*?\(([가-힣]+\s*\d+:\d+[~\-\d]*)\)'
                ]
                for pattern in verse_patterns:
                    verse_match = re.search(pattern, full_text, re.DOTALL)
                    if verse_match:
                        info["verse"]["text"] = verse_match.group(1).strip()
                        info["verse"]["reference"] = verse_match.group(2).strip()
                        break

            # 예배 순서 추출 (구조화된 데이터에 없으면)
            if not info["worship_services"]:
                info["worship_services"] = self._extract_worship_services(full_text)

            # 교회 소식 추출 (구조화된 데이터에 없으면)
            if not info["news"]:
                info["news"] = self._extract_news(full_text)

        return info

    def _parse_sermon_sections(self, content_parts: List[str]) -> List[Dict]:
        """설교 내용을 섹션별로 파싱"""
        sections = []
        current_section = {"title": "", "content": ""}

        for part in content_parts:
            # 섹션 제목 패턴 (1. xxx, 2. xxx, 첫째, 둘째 등)
            section_match = re.match(r'^(\d+\.\s*[^:]+|첫째[,\s]*|둘째[,\s]*|셋째[,\s]*)', part)
            if section_match:
                if current_section["content"]:
                    sections.append(current_section)
                current_section = {"title": section_match.group(1).strip(), "content": part[len(section_match.group(0)):].strip()}
            else:
                if current_section["title"]:
                    current_section["content"] += " " + part
                else:
                    current_section["content"] += part

        if current_section["content"]:
            sections.append(current_section)

        return sections if sections else [{"title": "", "content": "\n".join(content_parts)}]

    def _convert_news_items(self, news: List) -> List[Dict]:
        """교회 소식 항목 변환"""
        result = []
        for item in news:
            if isinstance(item, dict):
                result.append(item)
            else:
                # 문자열인 경우 카테고리 추정
                category = "안내"
                if "예배" in str(item):
                    category = "예배"
                elif "모집" in str(item):
                    category = "모집"
                elif "안내" in str(item):
                    category = "안내"
                result.append({
                    "category": category,
                    "title": str(item)[:50],
                    "content": str(item)
                })
        return result

    def _convert_structured_services(self, services: List[Dict]) -> List[Dict]:
        """구조화된 예배 순서를 HTML용 포맷으로 변환"""
        result = []
        for svc in services:
            name = svc.get("name", "예배")
            # 시간 추정
            time = ""
            if "1부" in name:
                time = "오전 7:00"
            elif "2부" in name or "2·3·4부" in name:
                time = "오전 9:00"
            elif "3부" in name:
                time = "오전 11:00"
            elif "4부" in name:
                time = "오후 1:00"
            elif "5부" in name or "대학청년" in name:
                time = "오후 2:30"
            elif "저녁" in name:
                time = "오후 5:00"

            items = []
            # 예배로 부르심
            items.append({"name": "예배로 부르심", "name_en": "Call to Worship", "detail": ""})

            # 찬송 (찬양 -> 찬송으로 변경)
            hymn = svc.get("hymn", "")
            items.append({"name": "찬송", "name_en": "Hymn", "detail": hymn})

            # 신앙고백
            items.append({"name": "신앙고백", "name_en": "Apostle's Creed", "detail": "사도신경"})

            # 기도
            prayer = svc.get("prayer", "")
            items.append({"name": "기도", "name_en": "Prayer", "detail": prayer})

            # 성경봉독
            scripture = svc.get("scripture", "")
            items.append({"name": "성경봉독", "name_en": "Scripture Reading", "detail": scripture})

            # 찬양대
            items.append({"name": "찬양대", "name_en": "Choir", "detail": ""})

            # 설교
            sermon_title = svc.get("sermon_title", "")
            sermon_pastor = svc.get("sermon_pastor", "")
            items.append({"name": "설교", "name_en": "Sermon", "detail": f"{sermon_title}"})

            # 헌금기도
            items.append({"name": "헌금기도", "name_en": "Offertory Prayer", "detail": ""})

            # 축도
            items.append({"name": "축도", "name_en": "Benediction", "detail": ""})

            # 사회자
            mc = svc.get("司會") or svc.get("사회", "")

            result.append({
                "name": name,
                "time": time,
                "mc": mc,
                "items": items,
                "sermon_title": sermon_title,
                "sermon_pastor": sermon_pastor
            })

        return result

    def _extract_worship_services(self, text: str) -> List[Dict]:
        """예배 순서 추출"""
        services = []

        # 예배 시간 패턴
        service_patterns = [
            (r'1부.*?(?:예배|오전\s*7)', "1부 예배", "오전 7:00"),
            (r'2부.*?(?:예배|오전\s*9)', "2부 예배", "오전 9:00"),
            (r'3부.*?(?:예배|오전\s*11)', "3부 예배", "오전 11:00"),
            (r'4부.*?(?:예배|오후\s*1)', "4부 예배", "오후 1:00"),
            (r'5부.*?(?:대학청년|오후\s*2)', "5부 대학청년", "오후 2:30"),
            (r'주일저녁.*?(?:예배|오후\s*5)', "주일저녁 예배", "오후 5:00"),
        ]

        for pattern, name, time in service_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                service = {
                    "name": name,
                    "time": time,
                    "mc": "",
                    "items": self._get_default_worship_items(),
                    "sermon_title": "",
                    "sermon_pastor": ""
                }
                services.append(service)

        # 기본 예배 없으면 추가
        if not services:
            services.append({
                "name": "주일예배",
                "time": "오전 11:00",
                "mc": "",
                "items": self._get_default_worship_items(),
                "sermon_title": "",
                "sermon_pastor": ""
            })

        return services

    def _get_default_worship_items(self) -> List[Dict]:
        """기본 예배 순서 항목 (참조 템플릿 기반)"""
        return [
            {"name": "예배로 부르심", "name_en": "Call to Worship", "detail": ""},
            {"name": "찬송", "name_en": "Hymn", "detail": ""},
            {"name": "신앙고백", "name_en": "Apostle's Creed", "detail": "사도신경"},
            {"name": "기도", "name_en": "Prayer", "detail": ""},
            {"name": "성경봉독", "name_en": "Scripture Reading", "detail": ""},
            {"name": "찬양대", "name_en": "Choir", "detail": ""},
            {"name": "설교", "name_en": "Sermon", "detail": ""},
            {"name": "헌금기도", "name_en": "Offertory Prayer", "detail": ""},
            {"name": "축도", "name_en": "Benediction", "detail": ""}
        ]

    def _extract_news(self, text: str) -> List[Dict]:
        """교회 소식 추출"""
        news = []

        # 소식 패턴
        news_keywords = ["새벽예배", "수요예배", "금요", "모집", "안내", "감사예배", "송년", "신년"]

        for keyword in news_keywords:
            if keyword in text:
                # 해당 키워드 주변 텍스트 추출
                match = re.search(rf'({keyword}[^\n]+)', text)
                if match:
                    category = "안내"
                    if "예배" in keyword:
                        category = "예배"
                    elif "모집" in keyword:
                        category = "모집"

                    news.append({
                        "category": category,
                        "title": match.group(1)[:50],
                        "content": ""
                    })

        return news[:8]  # 최대 8개

    def _build_html(self, info: Dict, theme: Dict, theme_name: str, is_harvest: bool) -> str:
        """HTML 구조 생성"""

        return f'''<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, minimum-scale=1.0, maximum-scale=5.0, user-scalable=yes">
    <title>{info["church_name"]} 주보 - {info["date"]}</title>
    <meta name="description" content="{info["church_name"]} {info["date"]} 주보">
    <!-- PWA 전체화면 지원 -->
    <meta name="mobile-web-app-capable" content="yes">
    <meta name="apple-mobile-web-app-capable" content="yes">
    <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
    <meta name="apple-mobile-web-app-title" content="{info["church_name"]}">
    <link rel="apple-touch-icon" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><text y='.9em' font-size='90'>⛪</text></svg>">
    <meta name="theme-color" content="{theme["theme_color"]}">
    {self._get_css(theme, is_harvest)}
</head>
<body>
    {self._build_header(info, theme, is_harvest)}
    {self._build_nav_tabs()}
    {self._build_dark_mode_toggle()}

    <main class="container">
        {self._build_verse_section(info, is_harvest)}
        {self._build_worship_section(info, is_harvest)}
        {self._build_sermon_section(info, is_harvest)}
        {self._build_choir_section(info, is_harvest)}
        {self._build_news_section(info)}
        {self._build_devotional_section(info)}
        {self._build_contact_section()}
        {self._build_save_section()}
        {self._build_share_section(is_harvest)}
    </main>

    {self._build_footer(info, is_harvest)}
    {self._build_modals()}
    {self._get_javascript(info)}
</body>
</html>'''

    def _get_css(self, theme: Dict, is_harvest: bool) -> str:
        """CSS 스타일 생성 (참조 템플릿 기반)"""
        harvest_vars = ""
        if is_harvest:
            harvest_vars = """
            --harvest: #8B6914;
            --accent-warm: #D4883E;"""

        harvest_color = theme.get("harvest", theme["primary"])

        return f'''<style>
        :root {{
            --primary: {theme["primary"]};
            --primary-dark: {theme["primary_dark"]};
            --primary-light: {theme["primary_light"]};
            --accent: {theme["accent"]};
            --text-dark: #1a1a2e;
            --text-gray: #6B7280;
            --text-light: #9CA3AF;
            --bg-white: #FFFFFF;
            --bg-gray: #F5F3FA;
            --border: #E5E7EB;
            --success: #10B981;
            --warning: #F59E0B;{harvest_vars}
            --harvest: {harvest_color};
        }}

        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
            -webkit-tap-highlight-color: transparent;
        }}

        html {{
            scroll-behavior: smooth;
        }}

        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Apple SD Gothic Neo', 'Noto Sans KR', 'Malgun Gothic', sans-serif;
            background: var(--bg-gray);
            color: var(--text-dark);
            line-height: 1.6;
            min-height: 100vh;
        }}

        /* 헤더 - 스크롤 시 숨김/표시 */
        .header {{
            background: {theme["header_gradient"]};
            color: white;
            padding: 20px;
            padding-top: env(safe-area-inset-top, 20px);
            position: relative;
            z-index: 1000;
            box-shadow: 0 4px 20px rgba({'139, 105, 20' if is_harvest else '91, 75, 158'}, 0.4);
            transition: transform 0.3s ease, opacity 0.3s ease;
        }}

        .header.hidden {{
            transform: translateY(-100%);
            opacity: 0;
            position: absolute;
            width: 100%;
        }}

        .header-content {{
            max-width: 600px;
            margin: 0 auto;
            text-align: center;
        }}

        .harvest-badge {{
            display: inline-block;
            background: rgba(255,255,255,0.25);
            padding: 6px 16px;
            border-radius: 20px;
            font-size: 0.85em;
            font-weight: 600;
            margin-bottom: 8px;
            backdrop-filter: blur(4px);
        }}

        .church-name {{
            font-size: 1.6em;
            font-weight: 800;
            margin-bottom: 4px;
            text-shadow: 0 2px 4px rgba(0,0,0,0.2);
        }}

        .church-name-en {{
            font-size: 0.7em;
            font-weight: 400;
            opacity: 0.9;
            display: block;
            margin-top: 2px;
        }}

        .jubo-date {{
            font-size: 1.1em;
            opacity: 0.95;
            margin-top: 8px;
        }}

        .theme-badge {{
            display: inline-block;
            background: var(--primary);
            color: white;
            padding: 6px 16px;
            border-radius: 20px;
            font-size: 0.85em;
            font-weight: 600;
            margin-top: 12px;
        }}

        /* 네비게이션 탭 - 항상 상단 고정 */
        .nav-tabs {{
            background: white;
            border-bottom: 1px solid var(--border);
            position: sticky;
            top: 0;
            z-index: 999;
            overflow-x: auto;
            -webkit-overflow-scrolling: touch;
            scrollbar-width: none;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }}

        .nav-tabs::-webkit-scrollbar {{
            display: none;
        }}

        .nav-tabs-inner {{
            display: flex;
            max-width: 600px;
            margin: 0 auto;
            padding: 0 8px;
            justify-content: space-around;
        }}

        .nav-tab {{
            flex: 1;
            padding: 12px 8px;
            font-size: 0.85em;
            font-weight: 600;
            color: var(--text-gray);
            text-decoration: none;
            border-bottom: 3px solid transparent;
            white-space: nowrap;
            transition: all 0.2s;
            text-align: center;
        }}

        .nav-tab.active,
        .nav-tab:hover {{
            color: var(--harvest);
            border-bottom-color: var(--harvest);
        }}

        /* 컨테이너 */
        .container {{
            max-width: 600px;
            margin: 0 auto;
            padding: 16px;
            padding-bottom: 30px;
        }}

        /* 섹션 */
        .section {{
            background: white;
            border-radius: 16px;
            margin-bottom: 16px;
            box-shadow: 0 2px 12px rgba(0,0,0,0.06);
            overflow: hidden;
        }}

        .section-header {{
            background: linear-gradient(135deg, var(--primary-light) 0%, #fff 100%);
            padding: 16px 20px;
            border-bottom: 1px solid var(--border);
            display: flex;
            align-items: center;
            gap: 12px;
        }}

        .section-header.harvest {{
            background: linear-gradient(135deg, #FEF3C7 0%, #fff 100%);
        }}

        .section-icon {{
            font-size: 1.5em;
        }}

        .section-title {{
            font-size: 1.15em;
            font-weight: 700;
            color: var(--primary);
        }}

        .section-title.harvest {{
            color: var(--harvest);
        }}

        .section-body {{
            padding: 20px;
        }}

        /* 오늘의 말씀 - 테마별 스타일 */
        .verse-card {{
            background: {theme["header_gradient"]};
            color: white;
            border-radius: 16px;
            padding: 24px;
            margin-bottom: 16px;
            text-align: center;
            position: relative;
            overflow: hidden;
        }}

        .verse-card::before {{
            content: "{'🌾' if is_harvest else '✝️'}";
            position: absolute;
            font-size: 4em;
            opacity: 0.15;
            top: -10px;
            right: -10px;
        }}

        .verse-card::after {{
            content: "{'🌾' if is_harvest else ''}";
            position: absolute;
            font-size: 3em;
            opacity: 0.15;
            bottom: -5px;
            left: -5px;
        }}

        .verse-label {{
            font-size: 0.85em;
            opacity: 0.9;
            margin-bottom: 12px;
        }}

        .verse-text {{
            font-size: 1.05em;
            line-height: 1.8;
            font-weight: 500;
            margin-bottom: 16px;
            position: relative;
            z-index: 1;
        }}

        .verse-ref {{
            font-size: 0.95em;
            background: rgba(255,255,255,0.2);
            display: inline-block;
            padding: 6px 16px;
            border-radius: 20px;
        }}

        .verse-ref a {{
            color: white;
            text-decoration: none;
            border-bottom: 1px dashed rgba(255,255,255,0.5);
        }}

        .verse-ref a:hover {{
            border-bottom-style: solid;
        }}

        /* 예배 정보 카드 */
        .worship-card {{
            background: white;
            border-radius: 12px;
            border: 1px solid var(--border);
            margin-bottom: 12px;
            overflow: hidden;
        }}

        .worship-header {{
            background: var(--harvest);
            color: white;
            padding: 12px 16px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}

        .worship-title {{
            font-weight: 700;
            font-size: 1em;
        }}

        .worship-time {{
            font-size: 0.9em;
            opacity: 0.9;
        }}

        .worship-body {{
            padding: 16px;
        }}

        .worship-item {{
            display: flex;
            justify-content: space-between;
            padding: 8px 0;
            border-bottom: 1px solid #f0f0f0;
        }}

        .worship-item:last-child {{
            border-bottom: none;
        }}

        .worship-item-label {{
            color: var(--text-gray);
            font-size: 0.9em;
        }}

        .worship-item-value {{
            font-weight: 600;
            color: var(--text-dark);
            font-size: 0.9em;
            text-align: right;
        }}

        .sermon-highlight {{
            background: {'linear-gradient(135deg, #FEF3C7 0%, #FDE68A 100%)' if is_harvest else 'var(--primary-light)'};
            padding: 12px 16px;
            border-radius: 10px;
            margin-top: 12px;
            border-left: 4px solid var(--harvest);
        }}

        .sermon-title {{
            font-size: 1.05em;
            font-weight: 700;
            color: var(--harvest);
            margin-bottom: 4px;
        }}

        .sermon-preacher {{
            font-size: 0.9em;
            color: var(--text-gray);
        }}

        /* 설교 본문 */
        .sermon-content {{
            line-height: 1.9;
            font-size: 1em;
            color: var(--text-dark);
        }}

        .sermon-content h3 {{
            font-size: 1.1em;
            color: var(--harvest);
            margin: 24px 0 12px 0;
            padding-left: 12px;
            border-left: 4px solid var(--harvest);
        }}

        .sermon-content p {{
            margin-bottom: 16px;
            text-align: justify;
            word-break: keep-all;
        }}

        .sermon-author {{
            text-align: right;
            margin-top: 24px;
            font-weight: 600;
            color: var(--harvest);
        }}

        /* 설교 오디오 플레이어 스타일 */
        .sermon-audio-section {{
            background: {'linear-gradient(135deg, #FEF3C7 0%, #fff 100%)' if is_harvest else 'linear-gradient(135deg, var(--primary-light) 0%, #fff 100%)'};
            border-radius: 12px;
            padding: 16px;
            margin-top: 20px;
            border: 1px solid {'#FDE68A' if is_harvest else 'var(--border)'};
        }}

        .audio-header {{
            display: flex;
            align-items: center;
            gap: 10px;
            margin-bottom: 12px;
        }}

        .audio-icon {{
            font-size: 1.4em;
        }}

        .audio-title {{
            font-weight: 700;
            color: var(--harvest);
            font-size: 0.95em;
        }}

        .audio-player {{
            width: 100%;
            height: 44px;
            border-radius: 8px;
        }}

        .audio-controls {{
            display: flex;
            gap: 10px;
            margin-top: 10px;
        }}

        .audio-btn {{
            flex: 1;
            padding: 10px 12px;
            border: 1px solid var(--harvest);
            background: white;
            color: var(--harvest);
            border-radius: 8px;
            font-size: 0.85em;
            font-weight: 600;
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 6px;
            transition: all 0.2s;
        }}

        .audio-btn:hover {{
            background: var(--harvest);
            color: white;
        }}

        .audio-btn.download {{
            background: var(--harvest);
            color: white;
        }}

        .audio-btn.download:hover {{
            background: {'#6B4E13' if is_harvest else 'var(--primary-dark)'};
        }}

        /* 교회 소식 */
        .news-item {{
            padding: 16px 0;
            border-bottom: 1px solid #f0f0f0;
        }}

        .news-item:last-child {{
            border-bottom: none;
        }}

        .news-category {{
            display: inline-block;
            background: var(--primary);
            color: white;
            padding: 4px 10px;
            border-radius: 6px;
            font-size: 0.75em;
            font-weight: 600;
            margin-bottom: 8px;
        }}

        .news-category.worship {{ background: var(--harvest); }}
        .news-category.recruit {{ background: var(--success); }}
        .news-category.info {{ background: var(--warning); }}
        .news-category.special {{ background: #E11D48; }}

        .news-title {{
            font-weight: 700;
            font-size: 1em;
            margin-bottom: 6px;
            color: var(--text-dark);
        }}

        .news-content {{
            font-size: 0.9em;
            color: var(--text-gray);
            line-height: 1.6;
        }}

        /* 찬양대 정보 */
        .choir-grid {{
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 10px;
        }}

        .choir-item {{
            background: {'linear-gradient(135deg, #FEF3C7 0%, #fff 100%)' if is_harvest else 'var(--bg-gray)'};
            padding: 12px;
            border-radius: 10px;
            text-align: center;
            border: {'1px solid #FDE68A' if is_harvest else 'none'};
        }}

        .choir-service {{
            font-size: 0.8em;
            color: var(--harvest);
            font-weight: 600;
            margin-bottom: 4px;
        }}

        .choir-name {{
            font-size: 0.85em;
            font-weight: 700;
            color: var(--text-dark);
        }}

        .choir-song {{
            font-size: 0.75em;
            color: var(--text-gray);
            margin-top: 4px;
        }}

        /* 오늘의 양식 */
        .devotional-title {{
            font-size: 1.2em;
            font-weight: 700;
            color: var(--harvest);
            text-align: center;
            margin-bottom: 20px;
            padding-bottom: 12px;
            border-bottom: 2px solid {'#FDE68A' if is_harvest else 'var(--primary-light)'};
        }}

        .devotional-content {{
            font-size: 0.95em;
            line-height: 1.9;
            color: var(--text-dark);
            text-align: justify;
            word-break: keep-all;
        }}

        .devotional-content p {{
            margin-bottom: 16px;
            text-indent: 1em;
        }}

        /* 연락처 */
        .contact-grid {{
            display: grid;
            gap: 12px;
        }}

        .contact-item {{
            display: flex;
            align-items: center;
            gap: 12px;
            padding: 12px;
            background: var(--bg-gray);
            border-radius: 10px;
        }}

        .contact-icon {{
            font-size: 1.2em;
        }}

        .contact-info {{
            flex: 1;
        }}

        .contact-label {{
            font-size: 0.8em;
            color: var(--text-gray);
        }}

        .contact-value {{
            font-weight: 600;
            color: var(--text-dark);
        }}

        .contact-value a {{
            color: var(--primary);
            text-decoration: none;
        }}

        /* 성경/찬송가 링크 스타일 */
        .bible-link, .hymn-link {{
            color: var(--harvest);
            text-decoration: none;
            border-bottom: 1px dashed var(--harvest);
            transition: all 0.2s;
        }}

        .bible-link:hover, .hymn-link:hover {{
            background: {'#FEF3C7' if is_harvest else 'var(--primary-light)'};
            border-bottom-style: solid;
        }}

        /* 모달 팝업 스타일 */
        .modal-overlay {{
            display: none;
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: rgba(0,0,0,0.7);
            z-index: 2000;
            justify-content: center;
            align-items: center;
            padding: 20px;
        }}

        .modal-overlay.active {{
            display: flex;
        }}

        .modal-content {{
            background: white;
            border-radius: 16px;
            max-width: 500px;
            width: 100%;
            max-height: 80vh;
            overflow-y: auto;
            position: relative;
            animation: modalSlideUp 0.3s ease-out;
        }}

        @keyframes modalSlideUp {{
            from {{
                opacity: 0;
                transform: translateY(30px);
            }}
            to {{
                opacity: 1;
                transform: translateY(0);
            }}
        }}

        .modal-header {{
            background: {'linear-gradient(135deg, var(--harvest) 0%, #C9A857 100%)' if is_harvest else 'linear-gradient(135deg, var(--primary) 0%, var(--primary-dark) 100%)'};
            color: white;
            padding: 16px 20px;
            border-radius: 16px 16px 0 0;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}

        .modal-header.hymn {{
            background: linear-gradient(135deg, #D97706 0%, #B45309 100%);
        }}

        .modal-title {{
            font-size: 1.1em;
            font-weight: 700;
        }}

        .modal-close {{
            background: rgba(255,255,255,0.2);
            border: none;
            color: white;
            width: 32px;
            height: 32px;
            border-radius: 50%;
            font-size: 1.2em;
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
        }}

        .modal-body {{
            padding: 20px;
        }}

        .bible-verse-content {{
            font-size: 1.05em;
            line-height: 1.9;
            color: var(--text-dark);
        }}

        .bible-verse-content .verse-num {{
            color: var(--harvest);
            font-weight: 700;
            font-size: 0.85em;
            vertical-align: super;
            margin-right: 2px;
        }}

        .bible-verse-content p {{
            margin-bottom: 12px;
        }}

        .hymn-content {{
            text-align: center;
        }}

        .hymn-number {{
            font-size: 2em;
            font-weight: 800;
            color: #D97706;
            margin-bottom: 8px;
        }}

        .hymn-title {{
            font-size: 1.2em;
            font-weight: 700;
            color: var(--text-dark);
            margin-bottom: 16px;
        }}

        .hymn-lyrics {{
            font-size: 1em;
            line-height: 1.8;
            color: var(--text-dark);
            text-align: left;
            white-space: pre-line;
        }}

        .hymn-lyrics .verse-label {{
            font-weight: 700;
            color: #D97706;
            margin-top: 16px;
            display: block;
        }}

        /* 주보 저장 버튼 스타일 */
        .save-jubo-section {{
            background: linear-gradient(135deg, #E8F5E9 0%, #fff 100%);
            border: 2px dashed #4CAF50;
            border-radius: 12px;
            padding: 16px;
            margin-bottom: 16px;
            text-align: center;
        }}

        .save-title {{
            font-weight: 700;
            color: #2E7D32;
            margin-bottom: 8px;
        }}

        .save-desc {{
            font-size: 0.85em;
            color: var(--text-gray);
            margin-bottom: 12px;
        }}

        .save-btn {{
            display: inline-flex;
            align-items: center;
            gap: 8px;
            padding: 12px 24px;
            background: #4CAF50;
            color: white;
            border: none;
            border-radius: 10px;
            font-size: 0.95em;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.2s;
        }}

        .save-btn:hover {{
            background: #388E3C;
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(76, 175, 80, 0.3);
        }}

        /* 공유 섹션 */
        .share-section {{
            background: white;
            border-radius: 16px;
            padding: 24px;
            margin-bottom: 16px;
            text-align: center;
            box-shadow: 0 2px 12px rgba(0,0,0,0.06);
        }}

        .share-title {{
            font-size: 1em;
            font-weight: 600;
            margin-bottom: 16px;
            color: var(--text-dark);
        }}

        .share-buttons {{
            display: flex;
            gap: 12px;
            justify-content: center;
        }}

        .share-btn {{
            flex: 1;
            max-width: 140px;
            padding: 14px;
            border-radius: 12px;
            border: 1px solid var(--border);
            background: white;
            font-size: 0.9em;
            font-weight: 600;
            color: var(--text-dark);
            cursor: pointer;
            transition: all 0.2s;
        }}

        .share-btn:active {{
            transform: scale(0.95);
            background: var(--bg-gray);
        }}

        .share-btn.kakao {{
            background: #FEE500;
            border-color: #FEE500;
            color: #3C1E1E;
        }}

        /* 푸터 */
        .footer {{
            background: var(--harvest);
            color: white;
            padding: 30px 20px;
            text-align: center;
        }}

        .footer-logo {{
            font-size: 1.2em;
            font-weight: 700;
            margin-bottom: 8px;
        }}

        .footer-address {{
            font-size: 0.85em;
            opacity: 0.9;
            margin-bottom: 16px;
        }}

        .footer-copyright {{
            font-size: 0.75em;
            opacity: 0.7;
        }}

        /* 다크모드 토글 */
        .dark-mode-toggle {{
            position: fixed;
            top: 80px;
            right: 16px;
            background: white;
            border: 1px solid var(--border);
            border-radius: 50%;
            width: 44px;
            height: 44px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 1.2em;
            cursor: pointer;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            z-index: 998;
            transition: all 0.2s;
        }}

        /* 다크모드 */
        body.dark-mode {{
            --bg-gray: #1a1a2e;
            --bg-white: #252540;
            --text-dark: #ffffff;
            --text-gray: #a0a0b0;
            --border: #3a3a50;
            --primary-light: #3a3a50;
        }}

        body.dark-mode .section,
        body.dark-mode .worship-card,
        body.dark-mode .share-section,
        body.dark-mode .nav-tabs {{
            background: var(--bg-white);
        }}

        body.dark-mode .dark-mode-toggle {{
            background: var(--bg-white);
        }}

        body.dark-mode .choir-item {{
            background: var(--bg-white);
            border-color: #3a3a50;
        }}

        body.dark-mode .sermon-highlight {{
            background: #3a3a50;
        }}

        body.dark-mode .modal-content {{
            background: var(--bg-white);
        }}

        body.dark-mode .sermon-audio-section {{
            background: var(--bg-white);
        }}

        body.dark-mode .save-jubo-section {{
            background: var(--bg-white);
            border-color: #388E3C;
        }}

        /* 애니메이션 */
        @keyframes fadeInUp {{
            from {{
                opacity: 0;
                transform: translateY(20px);
            }}
            to {{
                opacity: 1;
                transform: translateY(0);
            }}
        }}

        .section {{
            animation: fadeInUp 0.5s ease-out;
        }}

        /* 반응형 */
        @media (max-width: 375px) {{
            .church-name {{
                font-size: 1.4em;
            }}

            .nav-tab {{
                padding: 12px 12px;
                font-size: 0.85em;
            }}

            .choir-grid {{
                grid-template-columns: 1fr;
            }}
        }}
    </style>'''

    def _build_header(self, info: Dict, theme: Dict, is_harvest: bool) -> str:
        """헤더 섹션 생성"""
        harvest_badge = ""
        sunday_type = "주일"

        if is_harvest:
            harvest_badge = '<div class="harvest-badge">🌾 2025 추수감사절</div>'
            sunday_type = "추수감사주일"

        return f'''
    <!-- 헤더 -->
    <header class="header">
        <div class="header-content">
            {harvest_badge}
            <h1 class="church-name">
                {info["church_name"]}
                <span class="church-name-en">{info["church_name_en"]}</span>
            </h1>
            <div class="jubo-date">{info["date"]} {sunday_type}</div>
            <div class="theme-badge">{info["theme"]}</div>
        </div>
    </header>'''

    def _build_nav_tabs(self) -> str:
        """네비게이션 탭 생성"""
        return '''
    <!-- 네비게이션 탭 -->
    <nav class="nav-tabs">
        <div class="nav-tabs-inner">
            <a href="#verse" class="nav-tab active">말씀</a>
            <a href="#worship" class="nav-tab">예배</a>
            <a href="#sermon" class="nav-tab">설교</a>
            <a href="#choir" class="nav-tab">찬양</a>
            <a href="#news" class="nav-tab">소식</a>
            <a href="#devotional" class="nav-tab">양식</a>
        </div>
    </nav>'''

    def _build_dark_mode_toggle(self) -> str:
        """다크모드 토글 버튼"""
        return '''
    <!-- 다크모드 토글 -->
    <button class="dark-mode-toggle" onclick="toggleDarkMode()" title="다크모드">
        🌙
    </button>'''

    def _build_verse_section(self, info: Dict, is_harvest: bool) -> str:
        """오늘의 말씀 섹션"""
        verse = info.get("verse", {})
        text = verse.get("text", "")
        ref = verse.get("reference", "")

        if not text:
            text = "야훼는 나의 목자시니 내게 부족함이 없으리로다 그가 나를 푸른 풀밭에 누이시며 쉴 만한 물 가로 인도하시는도다"
            ref = "시편 23:1~2"

        verse_label = "🌾 추수감사주일 말씀" if is_harvest else "오늘의 말씀"

        return f'''
        <!-- 오늘의 말씀 -->
        <section id="verse" class="verse-card">
            <div class="verse-label">{verse_label}</div>
            <p class="verse-text">
                "{text}"
            </p>
            <span class="verse-ref"><a href="javascript:void(0)" onclick="openBibleModal('main-verse')">{ref}</a></span>
        </section>'''

    def _build_worship_section(self, info: Dict, is_harvest: bool) -> str:
        """예배 안내 섹션"""
        services = info.get("worship_services", [])

        if not services:
            services = [{
                "name": "주일예배",
                "time": "오전 11:00",
                "mc": "",
                "items": self._get_default_worship_items(),
                "sermon_title": info.get("sermon", {}).get("title", ""),
                "sermon_pastor": info.get("sermon", {}).get("preacher", "")
            }]

        cards_html = ""
        for service in services[:6]:  # 최대 6개
            # 예배 순서 항목
            items_html = ""
            for item in service.get("items", []):
                name = item.get("name", "")
                detail = item.get("detail", "")

                # 사회자 항목 특별 처리
                if name == "예배로 부르심" and service.get("mc"):
                    items_html += f'''
                        <div class="worship-item">
                            <span class="worship-item-label">사회</span>
                            <span class="worship-item-value">{service.get("mc", "")}</span>
                        </div>'''

                if detail:
                    items_html += f'''
                        <div class="worship-item">
                            <span class="worship-item-label">{name}</span>
                            <span class="worship-item-value">{detail}</span>
                        </div>'''

            # 설교 하이라이트
            sermon_title = service.get("sermon_title", "") or info.get("sermon", {}).get("title", "")
            sermon_pastor = service.get("sermon_pastor", "") or info.get("sermon", {}).get("preacher", "")

            cards_html += f'''
                <div class="worship-card">
                    <div class="worship-header">
                        <span class="worship-title">{service.get("name", "예배")}</span>
                        <span class="worship-time">{service.get("time", "")}</span>
                    </div>
                    <div class="worship-body">
                        {items_html}
                        <div class="sermon-highlight">
                            <div class="sermon-title">{sermon_title}</div>
                            <div class="sermon-preacher">{sermon_pastor}</div>
                        </div>
                    </div>
                </div>'''

        section_class = "harvest" if is_harvest else ""
        section_title = "추수감사주일 예배" if is_harvest else "주일예배 안내"

        return f'''
        <!-- 예배 안내 -->
        <section id="worship" class="section">
            <div class="section-header {section_class}">
                <span class="section-icon">⛪</span>
                <h2 class="section-title {section_class}">{section_title}</h2>
            </div>
            <div class="section-body">
                {cards_html}
            </div>
        </section>'''

    def _build_sermon_section(self, info: Dict, is_harvest: bool) -> str:
        """설교 말씀 섹션"""
        sermon = info.get("sermon", {})
        title = sermon.get("title", "")
        title_en = sermon.get("title_en", "")
        scripture = sermon.get("scripture", "")
        preacher = sermon.get("preacher", "")
        sections = sermon.get("sections", [])

        # 설교 본문 생성
        content_html = ""
        if sections:
            for section in sections:
                section_title = section.get("title", "")
                section_content = section.get("content", "")
                if section_title:
                    content_html += f'<h3>{section_title}</h3>\n'
                content_html += f'<p>{section_content}</p>\n'
        else:
            content_html = "<p>설교 내용은 예배 후 업데이트됩니다.</p>"

        section_class = "harvest" if is_harvest else ""
        audio_title = "추수감사절 설교 음성 듣기" if is_harvest else "설교 음성 듣기"

        return f'''
        <!-- 설교 말씀 -->
        <section id="sermon" class="section">
            <div class="section-header {section_class}">
                <span class="section-icon">📖</span>
                <h2 class="section-title {section_class}">생명의 말씀</h2>
            </div>
            <div class="section-body">
                <div style="text-align: center; margin-bottom: 20px;">
                    <div style="font-size: 1.3em; font-weight: 700; color: var(--harvest);">{title}</div>
                    <div style="font-size: 0.9em; color: var(--text-gray); margin-top: 4px;">{title_en}</div>
                    {f'<div style="font-size: 0.9em; color: var(--text-gray); margin-top: 8px;"><a href="javascript:void(0)" onclick="openBibleModal(\'sermon-verse\')" class="bible-link">{scripture}</a></div>' if scripture else ''}
                </div>
                <div class="sermon-content">
                    {content_html}
                    <div class="sermon-author">{self.church_info.get("name", "")} {preacher}</div>
                </div>

                <!-- 설교 음성 듣기 -->
                <div class="sermon-audio-section">
                    <div class="audio-header">
                        <span class="audio-icon">🎧</span>
                        <span class="audio-title">{audio_title}</span>
                    </div>
                    <audio class="audio-player" controls>
                        <source src="sermon.mp3" type="audio/mpeg">
                        브라우저가 오디오를 지원하지 않습니다.
                    </audio>
                    <div class="audio-controls">
                        <button class="audio-btn" onclick="changePlaybackRate()">
                            <span id="speedLabel">1.0x</span> 속도
                        </button>
                        <button class="audio-btn download" onclick="downloadSermon()">
                            ⬇️ 다운로드
                        </button>
                    </div>
                </div>
            </div>
        </section>'''

    def _build_choir_section(self, info: Dict, is_harvest: bool) -> str:
        """금주의 찬양 섹션"""
        choirs = info.get("choir", [])

        if not choirs:
            choirs = [
                {"service": "주일 1부", "name": "베다니 찬양대", "song": ""},
                {"service": "주일 2부", "name": "베들레헴 찬양대", "song": ""},
                {"service": "주일 3부", "name": "예루살렘 찬양대", "song": ""},
                {"service": "주일 4부", "name": "나사렛 찬양대", "song": ""},
                {"service": "5부 대학청년", "name": "임마누엘 찬양대", "song": ""},
                {"service": "주일 저녁", "name": "에벤에셀 찬양대", "song": ""},
            ]

        items_html = ""
        for choir in choirs[:6]:
            items_html += f'''
                    <div class="choir-item">
                        <div class="choir-service">{choir.get("service", "")}</div>
                        <div class="choir-name">{choir.get("name", "")}</div>
                        <div class="choir-song">{choir.get("song", "")}</div>
                    </div>'''

        section_class = "harvest" if is_harvest else ""
        section_title = "추수감사절 찬양" if is_harvest else "금주의 찬양"

        return f'''
        <!-- 금주의 찬양 -->
        <section id="choir" class="section">
            <div class="section-header {section_class}">
                <span class="section-icon">🎵</span>
                <h2 class="section-title {section_class}">{section_title}</h2>
            </div>
            <div class="section-body">
                <div class="choir-grid">
                    {items_html}
                </div>
            </div>
        </section>'''

    def _build_news_section(self, info: Dict) -> str:
        """교회 소식 섹션"""
        news = info.get("news", [])

        if not news:
            news = [
                {"category": "안내", "title": "교회 소식", "content": "교회 소식이 업데이트됩니다."}
            ]

        items_html = ""
        for item in news[:8]:  # 최대 8개
            cat = item.get("category", "안내")
            cat_class = "info"
            if "예배" in cat:
                cat_class = "worship"
            elif "모집" in cat:
                cat_class = "recruit"
            elif "특별" in cat or "감사" in cat:
                cat_class = "special"

            items_html += f'''
                <div class="news-item">
                    <span class="news-category {cat_class}">{cat}</span>
                    <div class="news-title">{item.get("title", "")}</div>
                    <div class="news-content">{item.get("content", "")}</div>
                </div>'''

        return f'''
        <!-- 교회 소식 -->
        <section id="news" class="section">
            <div class="section-header">
                <span class="section-icon">📢</span>
                <h2 class="section-title">교회 소식</h2>
            </div>
            <div class="section-body">
                {items_html}
            </div>
        </section>'''

    def _build_devotional_section(self, info: Dict) -> str:
        """오늘의 양식 섹션"""
        devotional = info.get("devotional", {})
        title = devotional.get("title", "묵상의 글")
        content = devotional.get("content", "")

        if not content:
            content = "<p>오늘의 양식 내용이 업데이트됩니다.</p>"

        return f'''
        <!-- 오늘의 양식 -->
        <section id="devotional" class="section">
            <div class="section-header">
                <span class="section-icon">🌿</span>
                <h2 class="section-title">오늘의 양식</h2>
            </div>
            <div class="section-body">
                <div class="devotional-title">{title}</div>
                <div class="devotional-content">
                    {content}
                </div>
            </div>
        </section>'''

    def _build_contact_section(self) -> str:
        """교회 연락처 섹션"""
        return f'''
        <!-- 연락처 -->
        <section class="section">
            <div class="section-header">
                <span class="section-icon">📞</span>
                <h2 class="section-title">교회 연락처</h2>
            </div>
            <div class="section-body">
                <div class="contact-grid">
                    <div class="contact-item">
                        <span class="contact-icon">📍</span>
                        <div class="contact-info">
                            <div class="contact-label">주소</div>
                            <div class="contact-value">{self.church_info.get("address", "")}</div>
                        </div>
                    </div>
                    <div class="contact-item">
                        <span class="contact-icon">📞</span>
                        <div class="contact-info">
                            <div class="contact-label">대표전화 (주간)</div>
                            <div class="contact-value"><a href="tel:{self.church_info.get("phone_day", "")}">{self.church_info.get("phone_day", "")}</a></div>
                        </div>
                    </div>
                    <div class="contact-item">
                        <span class="contact-icon">🌙</span>
                        <div class="contact-info">
                            <div class="contact-label">대표전화 (야간)</div>
                            <div class="contact-value"><a href="tel:{self.church_info.get("phone_night", "").split("~")[0]}">{self.church_info.get("phone_night", "")}</a></div>
                        </div>
                    </div>
                    <div class="contact-item">
                        <span class="contact-icon">🌐</span>
                        <div class="contact-info">
                            <div class="contact-label">홈페이지</div>
                            <div class="contact-value"><a href="{self.church_info.get("website", "")}" target="_blank">{self.church_info.get("website", "").replace("https://", "")}</a></div>
                        </div>
                    </div>
                </div>
            </div>
        </section>'''

    def _build_save_section(self) -> str:
        """주보 저장 섹션"""
        return '''
        <!-- 주보 저장 -->
        <div class="save-jubo-section">
            <div class="save-title">📱 스마트폰에 주보 저장하기</div>
            <div class="save-desc">홈 화면에 추가하면 언제든지 주보를 다시 볼 수 있어요</div>
            <button class="save-btn" onclick="saveToHomeScreen()">
                📥 홈 화면에 추가
            </button>
        </div>'''

    def _build_share_section(self, is_harvest: bool) -> str:
        """공유 섹션"""
        share_title = "🌾 추수감사주일 주보를 공유해 보세요" if is_harvest else "주보를 공유해 보세요"
        return f'''
        <!-- 공유 섹션 -->
        <div class="share-section">
            <div class="share-title">{share_title}</div>
            <div class="share-buttons">
                <button class="share-btn kakao" onclick="shareKakao()">카카오톡</button>
                <button class="share-btn" onclick="shareLink()">링크 복사</button>
            </div>
        </div>'''

    def _build_footer(self, info: Dict, is_harvest: bool) -> str:
        """푸터 섹션"""
        logo = "🌾 " + info["church_name"] if is_harvest else info["church_name"]
        return f'''
    <!-- 푸터 -->
    <footer class="footer">
        <div class="footer-logo">{logo}</div>
        <div class="footer-address">
            {self.church_info.get("address", "")}<br>
            {self.church_info.get("founded", "")}
        </div>
        <div class="footer-copyright">
            © 2025 {info["church_name"]}. All rights reserved.
        </div>
    </footer>'''

    def _build_modals(self) -> str:
        """모달 팝업"""
        return '''
    <!-- 성경/찬송가 모달 -->
    <div class="modal-overlay" id="bibleModal">
        <div class="modal-content">
            <div class="modal-header">
                <span class="modal-title" id="bibleModalTitle">📖 성경 말씀</span>
                <button class="modal-close" onclick="closeModal('bibleModal')">✕</button>
            </div>
            <div class="modal-body">
                <div class="bible-verse-content" id="bibleModalContent"></div>
            </div>
        </div>
    </div>

    <div class="modal-overlay" id="hymnModal">
        <div class="modal-content">
            <div class="modal-header hymn">
                <span class="modal-title" id="hymnModalTitle">🎵 찬송가</span>
                <button class="modal-close" onclick="closeModal('hymnModal')">✕</button>
            </div>
            <div class="modal-body">
                <div class="hymn-content" id="hymnModalContent"></div>
            </div>
        </div>
    </div>'''

    def _get_javascript(self, info: Dict) -> str:
        """JavaScript 코드"""
        church_name = info.get("church_name", "교회")
        date = info.get("date", "")
        verse_text = info.get("verse", {}).get("text", "")
        verse_ref = info.get("verse", {}).get("reference", "")

        return f'''
    <script>
        // 성경 구절 데이터
        const bibleVerses = {{
            'main-verse': {{
                title: '{verse_ref}',
                content: '<p>{verse_text}</p>'
            }},
            'sermon-verse': {{
                title: '{info.get("sermon", {}).get("scripture", "")}',
                content: '<p>성경 본문이 표시됩니다.</p>'
            }}
        }};

        // 찬송가 데이터
        const hymns = {{}};

        // 모달 열기
        function openBibleModal(verseKey) {{
            const verse = bibleVerses[verseKey];
            if (verse) {{
                document.getElementById('bibleModalTitle').textContent = '📖 ' + verse.title;
                document.getElementById('bibleModalContent').innerHTML = verse.content;
                document.getElementById('bibleModal').classList.add('active');
                document.body.style.overflow = 'hidden';
            }}
        }}

        function openHymnModal(hymnNum) {{
            const hymn = hymns[hymnNum];
            if (hymn) {{
                document.getElementById('hymnModalTitle').textContent = '🎵 찬송가 ' + hymnNum + '장';
                document.getElementById('hymnModalContent').innerHTML = `
                    <div class="hymn-number">${{hymnNum}}장</div>
                    <div class="hymn-title">${{hymn.title}}</div>
                    <div class="hymn-lyrics">${{hymn.lyrics}}</div>
                `;
                document.getElementById('hymnModal').classList.add('active');
                document.body.style.overflow = 'hidden';
            }}
        }}

        function closeModal(modalId) {{
            document.getElementById(modalId).classList.remove('active');
            document.body.style.overflow = '';
        }}

        // 모달 외부 클릭 시 닫기
        document.querySelectorAll('.modal-overlay').forEach(modal => {{
            modal.addEventListener('click', function(e) {{
                if (e.target === this) {{
                    this.classList.remove('active');
                    document.body.style.overflow = '';
                }}
            }});
        }});

        // 오디오 재생 속도 변경
        let currentSpeed = 1.0;
        const speeds = [1.0, 1.25, 1.5, 1.75, 2.0, 0.75];

        function changePlaybackRate() {{
            const audio = document.querySelector('.audio-player');
            const speedLabel = document.getElementById('speedLabel');
            const currentIndex = speeds.indexOf(currentSpeed);
            const nextIndex = (currentIndex + 1) % speeds.length;
            currentSpeed = speeds[nextIndex];
            audio.playbackRate = currentSpeed;
            speedLabel.textContent = currentSpeed + 'x';
        }}

        // 설교 음성 다운로드
        function downloadSermon() {{
            alert('설교 음성 파일이 다운로드됩니다.\\n\\n실제 운영 시 교회 서버에서 음성 파일을 제공합니다.');
        }}

        // 홈 화면에 추가
        function saveToHomeScreen() {{
            const isIOS = /iPad|iPhone|iPod/.test(navigator.userAgent);
            const isAndroid = /Android/.test(navigator.userAgent);

            if (isIOS) {{
                alert('📱 iPhone/iPad에서 저장하기\\n\\n1. 하단의 공유 버튼(□↑)을 탭하세요\\n2. "홈 화면에 추가"를 선택하세요\\n3. "추가"를 탭하면 완료!');
            }} else if (isAndroid) {{
                alert('📱 Android에서 저장하기\\n\\n1. 브라우저 메뉴(⋮)를 탭하세요\\n2. "홈 화면에 추가" 또는 "앱 설치"를 선택하세요\\n3. 확인을 탭하면 완료!');
            }} else {{
                alert('📱 스마트폰에서 저장하기\\n\\n브라우저 메뉴에서 "홈 화면에 추가"를 선택하시면\\n언제든지 이 주보를 다시 보실 수 있습니다.');
            }}
        }}

        // 다크모드 토글
        function toggleDarkMode() {{
            document.body.classList.toggle('dark-mode');
            const btn = document.querySelector('.dark-mode-toggle');
            btn.textContent = document.body.classList.contains('dark-mode') ? '☀️' : '🌙';
            localStorage.setItem('darkMode', document.body.classList.contains('dark-mode'));
        }}

        // 다크모드 설정 불러오기
        if (localStorage.getItem('darkMode') === 'true') {{
            document.body.classList.add('dark-mode');
            document.querySelector('.dark-mode-toggle').textContent = '☀️';
        }}

        // 네비게이션 활성화
        const navTabs = document.querySelectorAll('.nav-tab');

        function setActiveNav(hash) {{
            navTabs.forEach(tab => {{
                tab.classList.toggle('active', tab.getAttribute('href') === hash);
            }});
        }}

        // 스크롤 시 네비게이션 활성화
        const sections = document.querySelectorAll('section[id]');
        window.addEventListener('scroll', () => {{
            let current = '';
            sections.forEach(section => {{
                const sectionTop = section.offsetTop - 150;
                if (window.scrollY >= sectionTop) {{
                    current = section.getAttribute('id');
                }}
            }});
            if (current) {{
                setActiveNav('#' + current);
            }}
        }});

        // 카카오톡 공유
        function shareKakao() {{
            if (navigator.share) {{
                navigator.share({{
                    title: '{church_name} 주보 - {date}',
                    text: '{church_name} 주보',
                    url: window.location.href
                }});
            }} else {{
                alert('카카오톡 공유는 모바일에서 이용 가능합니다.');
            }}
        }}

        // 링크 복사
        function shareLink() {{
            navigator.clipboard.writeText(window.location.href).then(() => {{
                alert('링크가 복사되었습니다.');
            }});
        }}

        // 부드러운 스크롤
        document.querySelectorAll('a[href^="#"]').forEach(anchor => {{
            anchor.addEventListener('click', function(e) {{
                e.preventDefault();
                const target = document.querySelector(this.getAttribute('href'));
                if (target) {{
                    const headerHeight = 60;
                    const targetPosition = target.offsetTop - headerHeight;
                    window.scrollTo({{
                        top: targetPosition,
                        behavior: 'smooth'
                    }});
                    setActiveNav(this.getAttribute('href'));
                }}
            }});
        }});

        // 스크롤 시 헤더 숨김/표시
        let lastScrollY = 0;
        let ticking = false;
        const header = document.querySelector('.header');
        const scrollThreshold = 150;

        function updateHeader() {{
            const currentScrollY = window.scrollY;
            if (currentScrollY > scrollThreshold) {{
                header.classList.add('hidden');
            }} else {{
                header.classList.remove('hidden');
            }}
            lastScrollY = currentScrollY;
            ticking = false;
        }}

        window.addEventListener('scroll', function() {{
            if (!ticking) {{
                window.requestAnimationFrame(updateHeader);
                ticking = true;
            }}
        }});
    </script>'''


# 싱글톤 인스턴스
_church_generator = None

def get_church_bulletin_generator(church_info: Dict = None) -> ChurchBulletinGenerator:
    """교회 주보 생성기 싱글톤 인스턴스"""
    global _church_generator
    if _church_generator is None or church_info:
        _church_generator = ChurchBulletinGenerator(church_info)
    return _church_generator
