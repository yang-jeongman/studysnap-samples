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
        },
        "advent": {  # 대림절
            "primary": "#4A0D67",
            "primary_dark": "#3A0A52",
            "primary_light": "#F0E6F4",
            "accent": "#C9A857",
            "harvest": "#4A0D67",
            "header_gradient": "linear-gradient(135deg, #4A0D67 0%, #6B1B8E 100%)",
            "theme_color": "#4A0D67",
            "is_harvest": False
        },
        "lent": {  # 사순절
            "primary": "#4A0D67",
            "primary_dark": "#3A0A52",
            "primary_light": "#F0E6F4",
            "accent": "#8B4513",
            "harvest": "#4A0D67",
            "header_gradient": "linear-gradient(135deg, #4A0D67 0%, #6B1B8E 100%)",
            "theme_color": "#4A0D67",
            "is_harvest": False
        },
        "pentecost": {  # 성령강림절
            "primary": "#DC143C",
            "primary_dark": "#B22222",
            "primary_light": "#FFE4E1",
            "accent": "#FF6347",
            "harvest": "#DC143C",
            "header_gradient": "linear-gradient(135deg, #DC143C 0%, #FF6347 100%)",
            "theme_color": "#DC143C",
            "is_harvest": False
        }
    }

    # 교회별 프리셋 - 각 교회의 고유 스타일
    CHURCH_PRESETS = {
        "명성교회": {
            "primary": "#1E3A5F",
            "primary_dark": "#152A45",
            "primary_light": "#E8EEF4",
            "accent": "#C9A857",
            "accent_light": "#F5EED8",
            "font_style": "serif",
            "letter_spacing": "8px",
            "name_en": "MYUNGSUNG CHURCH",
            "style": "elegant",
            "address": "서울특별시 강동구 올림픽로 780",
            "website": "http://www.myungsung.com",
            "phone": "02-440-9000",
            "fax": "02-440-9099",
            # 명성교회 고도화 - SNS 및 모바일 헌금
            "sns": {
                "youtube": "https://www.youtube.com/@MyungsungCh",
                "instagram": "",
                "facebook": "",
                "kakaotalk": ""
            },
            "mobile_offering": {
                "enabled": True,
                "url": "",
                "bank_accounts": [
                    {"bank": "국민은행", "account": "099-21-0211-791", "holder": "명성교회"},
                    {"bank": "신한은행", "account": "100-022-853853", "holder": "명성교회"},
                ]
            },
            # 예배별 상세 설정
            "worship_config": {
                "show_per_service_details": True,
                "show_prayer_person": True,
                "show_hymn_per_service": True,
                "stand_indicator": "*",
                "dawn_prayer_times": ["05:00", "06:00", "07:00"],
            },
            # 목회자 정보
            "staff_info": {
                "senior_pastor": "김삼환",
                "senior_pastor_title": "원로목사",
                "lead_pastor": "김하나",
                "lead_pastor_title": "담임목사"
            },
            # 명성교회는 '오늘의 말씀' 카드 섹션 비활성화
            "show_sermon_card": False
        },
        "여의도순복음교회": {
            "primary": "#5B4B9E",
            "primary_dark": "#4A3D82",
            "primary_light": "#E8E4F4",
            "accent": "#C9A857",
            "accent_light": "#F5EED8",
            "font_style": "sans-serif",
            "letter_spacing": "2px",
            "name_en": "YOIDO FULL GOSPEL CHURCH",
            "style": "modern",
            "address": "서울특별시 영등포구 국회대로76길 15",
            "website": "https://www.fgtv.com",
            "founded": "1958년 5월 18일 창립 (설립자 조용기 목사)",
            "phone_day": "02-6181-9191",
            "phone_night": "02-6181-9000~3",
            "sns": {
                "youtube": "https://www.youtube.com/@fgtv",
                "instagram": "https://www.instagram.com/yfgc_official",
                "facebook": "https://www.facebook.com/fgtv",
                "kakaotalk": "http://pf.kakao.com/_NrTxkK"
            },
            "mobile_offering": {
                "enabled": True,
                "bank_accounts": [
                    {"bank": "국민은행", "account": "039-21-0001-389", "holder": "여의도순복음교회"},
                    {"bank": "우리은행", "account": "1005-201-123456", "holder": "여의도순복음교회"}
                ],
                "url": "https://m.fgtv.com/donate/donate_m_ver2.asp"
            },
            "staff_info": {
                "senior_pastor": "조용기",
                "senior_pastor_title": "원로목사",
                "lead_pastor": "이영훈",
                "lead_pastor_title": "담임목사"
            }
        },
        "혈동교회": {
            "primary": "#8B4513",
            "primary_dark": "#5D3A1A",
            "primary_light": "#FDF8F0",
            "accent": "#C5A572",
            "accent_light": "#FAF5EB",
            "font_style": "serif",
            "letter_spacing": "4px",
            "name_en": "HYULDONG CHURCH",
            "style": "traditional",
            "address": "",
            "website": ""
        }
    }

    def __init__(self, church_info: Dict = None):
        self.church_info = church_info or self.DEFAULT_CHURCH_INFO
        # 교회별 프리셋 적용
        church_name = self.church_info.get("name", "")
        if church_name in self.CHURCH_PRESETS:
            self.preset = self.CHURCH_PRESETS[church_name]
        else:
            self.preset = self.CHURCH_PRESETS.get("여의도순복음교회")

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
            "church_name_en": self.church_info.get("name_en", "") or self.preset.get("name_en", ""),
            "date": "",
            "volume": "",
            "issue": "",
            "sunday_type": "주일예배",
            "theme": "2025 표어: 오직 말씀으로",
            "slogan": "",  # 교회 표어 (2025 표어: 오직 말씀으로)
            "theme_badge": "",  # 절기 배지 (대림절, 성탄절 등)
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
            "last_week_sermon": {  # 지난주 말씀
                "title": "",
                "scripture": "",
                "preacher": "",
                "summary": ""
            },
            "choir": [],
            "news": [],
            "member_news": {  # 교우소식
                "birth": [],
                "passing": [],
                "wedding": [],
                "new_members": []
            },
            "dawn_prayer": {  # 새벽기도회 (명성교회 등 해당 교회만 사용)
                "times": "",  # PDF에서 추출된 데이터만 사용
                "schedule": []
            },
            "weekly_services": [],  # 주중예배 (수요, 찬양 등)
            "staff": {  # 목회자 정보
                "senior_pastor": "",
                "lead_pastor": "",
                "associate_pastors": [],
                "education_pastors": []
            },
            "contact": {  # 연락처
                "address": self.preset.get("address", ""),
                "phone": "",
                "fax": "",
                "website": self.preset.get("website", "")
            },
            "devotional": {
                "title": "",
                "content": ""
            },
            "weekly_schedule": [],  # 수요예배, 금요성령대망회, 토요예배
            "bible_verses": {},
            "hymns": {},
            "translations": {},  # AI 번역 데이터
            "multilingual": False  # 다국어 모드
        }

        # 다국어 번역 데이터 복사
        if extracted_data.get("translations"):
            info["translations"] = extracted_data["translations"]
            info["multilingual"] = True

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

            # 설교 (새로운 points 구조 지원)
            sermon = structured.get("sermon", {})
            if sermon.get("title"):
                info["sermon"]["title"] = sermon["title"]
            if sermon.get("english_title"):
                info["sermon"]["title_en"] = sermon["english_title"]
            if sermon.get("scripture"):
                info["sermon"]["scripture"] = sermon["scripture"]
            if sermon.get("pastor") or sermon.get("author"):
                info["sermon"]["preacher"] = sermon.get("author") or sermon.get("pastor")
            if sermon.get("intro"):
                info["sermon"]["sections"].append({
                    "title": "",
                    "content": sermon["intro"]
                })
            # 새로운 points 구조 처리
            if sermon.get("points"):
                for point in sermon["points"]:
                    section = {
                        "title": point.get("title", ""),
                        "title_en": point.get("english", ""),
                        "content": point.get("content", "")
                    }
                    info["sermon"]["sections"].append(section)
            # 이전 content 구조도 지원
            elif sermon.get("content"):
                content_parts = sermon["content"]
                if isinstance(content_parts, list):
                    info["sermon"]["sections"] = self._parse_sermon_sections(content_parts)
                else:
                    info["sermon"]["sections"] = [{"title": "", "content": content_parts}]

            # 찬양대
            choir_data = structured.get("choir", [])
            if choir_data:
                info["choir"] = choir_data

            # 교회 소식 (새로운 중첩 구조 지원)
            news = structured.get("news", {})
            if news:
                if isinstance(news, dict):
                    # 새로운 중첩 구조: {"worship": [], "recruit": [], "info": []}
                    all_news = []
                    category_icons = {"worship": "⛪", "recruit": "📝", "info": "📢"}
                    category_names = {"worship": "예배", "recruit": "모집", "info": "안내"}
                    for category, items in news.items():
                        category_name = category_names.get(category, category)
                        category_icon = category_icons.get(category, "📌")
                        for item in items:
                            # 제목과 내용을 분리 (첫 번째 줄은 제목, 나머지는 내용)
                            if ":" in item:
                                parts = item.split(":", 1)
                                title = parts[0].strip()
                                content = parts[1].strip() if len(parts) > 1 else ""
                            else:
                                title = item
                                content = ""
                            all_news.append({
                                "title": f"[{category_name}] {title}",
                                "content": content
                            })
                    info["news"] = all_news
                else:
                    # 이전 리스트 구조
                    info["news"] = self._convert_news_items(news)

            # 오늘의 양식 (devotional)
            devotional = structured.get("devotional", {})
            if devotional:
                info["devotional"]["title"] = devotional.get("title", "")
                info["devotional"]["content"] = devotional.get("content", "")

            # 교회 정보
            church_info = structured.get("church_info", {})
            if church_info:
                if church_info.get("slogan"):
                    info["theme"] = church_info["slogan"]
                    info["slogan"] = church_info["slogan"]  # 헤더 표어 뱃지용
                if church_info.get("goals"):
                    info["goals"] = church_info["goals"]
                if church_info.get("volume"):
                    info["volume"] = church_info["volume"]
                if church_info.get("date"):
                    info["date"] = church_info["date"]
                if church_info.get("english_name"):
                    info["church_name_en"] = church_info["english_name"]

            # 목회자 정보
            pastors = structured.get("pastors", {})
            if pastors:
                if pastors.get("senior"):
                    info["staff"]["senior_pastor"] = pastors["senior"]
                if pastors.get("associate"):
                    info["staff"]["associate_pastors"] = pastors["associate"]

        # extracted_data에서 직접 추가 정보 가져오기
        if extracted_data.get("date"):
            info["date"] = extracted_data["date"]
        if extracted_data.get("volume"):
            info["volume"] = extracted_data["volume"]
        if extracted_data.get("issue"):
            info["issue"] = extracted_data["issue"]
        if extracted_data.get("theme"):
            info["theme_name"] = extracted_data["theme"]

        # 지난주 말씀 데이터 추출
        if extracted_data.get("last_week_sermon"):
            lws = extracted_data["last_week_sermon"]
            info["last_week_sermon"]["title"] = lws.get("title", "")
            info["last_week_sermon"]["scripture"] = lws.get("scripture", "")
            info["last_week_sermon"]["preacher"] = lws.get("preacher", "")
            info["last_week_sermon"]["summary"] = lws.get("summary", "")

        # worship_services 직접 복사 (app.py에서 파싱된 데이터)
        if extracted_data.get("worship_services") and not info["worship_services"]:
            info["worship_services"] = extracted_data["worship_services"]

        # dawn_prayer 직접 복사
        if extracted_data.get("dawn_prayer"):
            dp = extracted_data["dawn_prayer"]
            if dp.get("times"):
                info["dawn_prayer"]["times"] = dp["times"]
            if dp.get("schedule"):
                info["dawn_prayer"]["schedule"] = dp["schedule"]

        # 주중예배 (수요예배, 찬양예배 등) 직접 복사
        if extracted_data.get("weekly_services"):
            info["weekly_services"] = extracted_data["weekly_services"]

        # 날짜 형식 변환 (YYYY-MM-DD -> YYYY년 MM월 DD일)
        if info["date"] and "-" in info["date"]:
            parts = info["date"].split("-")
            if len(parts) == 3:
                info["date"] = f"{parts[0]}년 {int(parts[1])}월 {int(parts[2])}일"

        # 페이지별 텍스트에서 추가 정보 추출
        if "pages" in extracted_data:
            full_text = ""
            for page in extracted_data.get("pages", []):
                page_text = page.get("text", "")
                full_text += page_text + "\n"

            # 명성교회 주보 1면 3섹션 구조 처리
            # 날짜 추출 (형식: 2025년 12월 7일 또는 2025.12.7)
            if not info["date"]:
                date_patterns = [
                    r'(\d{4})년\s*(\d{1,2})월\s*(\d{1,2})일',
                    r'(\d{4})[.\s-]+(\d{1,2})[.\s-]+(\d{1,2})'
                ]
                for pattern in date_patterns:
                    date_match = re.search(pattern, full_text)
                    if date_match:
                        year, month, day = date_match.groups()
                        info["date"] = f"{year}년 {int(month)}월 {int(day)}일"
                        break

            # 권/호 추출 (형식: 46권 49호)
            if not info["volume"]:
                volume_match = re.search(r'(\d+)\s*권\s*(\d+)\s*호', full_text)
                if volume_match:
                    info["volume"] = volume_match.group(1)
                    info["issue"] = volume_match.group(2)

            # 담임목사 추출
            if not info["sermon"]["preacher"]:
                pastor_patterns = [
                    r'([가-힣]{2,4})\s*(담임목사|원로목사)',
                    r'(담임목사|원로목사)[:\s]*([가-힣]{2,4})',
                    r'설교[:\s]*([가-힣]{2,4})\s*목사'
                ]
                for pattern in pastor_patterns:
                    pastor_match = re.search(pattern, full_text)
                    if pastor_match:
                        groups = pastor_match.groups()
                        for g in groups:
                            if g and 2 <= len(g) <= 4 and g not in ['담임목사', '원로목사']:
                                info["sermon"]["preacher"] = g + " 목사"
                                break
                        if info["sermon"]["preacher"]:
                            break

            # 원로목사/담임목사 정보 추출 (섬기는 이들 섹션용)
            # 주의: "담임목사", "부목사" 등 다른 직책명이 잘못 추출되지 않도록 명확한 패턴 사용
            # 패턴: "원로목사 이름" 형태에서 이름만 추출 (2-3자 이름, 직책명 제외)
            senior_match = re.search(r'원로목사[:\s·]+([가-힣]{2,3})(?:\s|목사|$)', full_text)
            if senior_match:
                name = senior_match.group(1)
                # 다른 직책명이 아닌 경우에만 저장
                if name not in ['담임', '부목', '협동', '교육', '전도']:
                    info["staff"]["senior_pastor"] = name

            lead_match = re.search(r'담임목사[:\s·]+([가-힣]{2,3})(?:\s|목사|$)', full_text)
            if lead_match:
                name = lead_match.group(1)
                if name not in ['원로', '부목', '협동', '교육', '전도']:
                    info["staff"]["lead_pastor"] = name

            # 오늘의 말씀 추출
            if not info["verse"]["text"]:
                verse_patterns = [
                    r'[""]([^""]{10,100})[""].*?[(\[]?([가-힣]+\s*\d+[:\s]*\d+[~\-\d]*)[)\]]?',
                    r"오늘의\s*말씀[:\s]*['\"]?(.+?)['\"]?\s*\(([^)]+)\)"
                ]
                for pattern in verse_patterns:
                    verse_match = re.search(pattern, full_text, re.DOTALL)
                    if verse_match:
                        info["verse"]["text"] = verse_match.group(1).strip()
                        info["verse"]["reference"] = verse_match.group(2).strip()
                        break

            # 예배 순서 추출
            if not info["worship_services"]:
                info["worship_services"] = self._extract_worship_services(full_text)

            # 교회 소식 추출
            if not info["news"]:
                info["news"] = self._extract_news(full_text)

            # 연락처 정보 추출
            if not info["contact"]["phone"]:
                phone_match = re.search(r'(?:TEL|전화)[:\s]*([0-9\-]+)', full_text)
                if phone_match:
                    info["contact"]["phone"] = phone_match.group(1)
            if not info["contact"]["fax"]:
                fax_match = re.search(r'FAX[:\s]*([0-9\-]+)', full_text)
                if fax_match:
                    info["contact"]["fax"] = fax_match.group(1)
            if not info["contact"]["address"]:
                addr_match = re.search(r'(서울[가-힣\s]+(?:동|구|로)[^\n]{5,50})', full_text)
                if addr_match:
                    info["contact"]["address"] = addr_match.group(1).strip()

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

    # ========== 성경 참조 다국어 번역 헬퍼 ==========
    BIBLE_BOOK_TRANSLATIONS = {
        # 구약
        "창세기": {"en": "Genesis", "zh": "创世记", "ja": "創世記", "id": "Kejadian", "es": "Génesis", "ru": "Бытие", "fr": "Genèse"},
        "출애굽기": {"en": "Exodus", "zh": "出埃及记", "ja": "出エジプト記", "id": "Keluaran", "es": "Éxodo", "ru": "Исход", "fr": "Exode"},
        "레위기": {"en": "Leviticus", "zh": "利未记", "ja": "レビ記", "id": "Imamat", "es": "Levítico", "ru": "Левит", "fr": "Lévitique"},
        "민수기": {"en": "Numbers", "zh": "民数记", "ja": "民数記", "id": "Bilangan", "es": "Números", "ru": "Числа", "fr": "Nombres"},
        "신명기": {"en": "Deuteronomy", "zh": "申命记", "ja": "申命記", "id": "Ulangan", "es": "Deuteronomio", "ru": "Второзаконие", "fr": "Deutéronome"},
        "시편": {"en": "Psalms", "zh": "诗篇", "ja": "詩篇", "id": "Mazmur", "es": "Salmos", "ru": "Псалтирь", "fr": "Psaumes"},
        "잠언": {"en": "Proverbs", "zh": "箴言", "ja": "箴言", "id": "Amsal", "es": "Proverbios", "ru": "Притчи", "fr": "Proverbes"},
        "이사야": {"en": "Isaiah", "zh": "以赛亚书", "ja": "イザヤ書", "id": "Yesaya", "es": "Isaías", "ru": "Исаия", "fr": "Ésaïe"},
        # 신약
        "마태복음": {"en": "Matthew", "zh": "马太福音", "ja": "マタイによる福音書", "id": "Matius", "es": "Mateo", "ru": "Матфея", "fr": "Matthieu"},
        "마가복음": {"en": "Mark", "zh": "马可福音", "ja": "マルコによる福音書", "id": "Markus", "es": "Marcos", "ru": "Марка", "fr": "Marc"},
        "누가복음": {"en": "Luke", "zh": "路加福音", "ja": "ルカによる福音書", "id": "Lukas", "es": "Lucas", "ru": "Луки", "fr": "Luc"},
        "요한복음": {"en": "John", "zh": "约翰福音", "ja": "ヨハネによる福音書", "id": "Yohanes", "es": "Juan", "ru": "Иоанна", "fr": "Jean"},
        "사도행전": {"en": "Acts", "zh": "使徒行传", "ja": "使徒行伝", "id": "Kisah Para Rasul", "es": "Hechos", "ru": "Деяния", "fr": "Actes"},
        "로마서": {"en": "Romans", "zh": "罗马书", "ja": "ローマ人への手紙", "id": "Roma", "es": "Romanos", "ru": "Римлянам", "fr": "Romains"},
        "고린도전서": {"en": "1 Corinthians", "zh": "哥林多前书", "ja": "コリント人への第一の手紙", "id": "1 Korintus", "es": "1 Corintios", "ru": "1 Коринфянам", "fr": "1 Corinthiens"},
        "고린도후서": {"en": "2 Corinthians", "zh": "哥林多后书", "ja": "コリント人への第二の手紙", "id": "2 Korintus", "es": "2 Corintios", "ru": "2 Коринфянам", "fr": "2 Corinthiens"},
        "갈라디아서": {"en": "Galatians", "zh": "加拉太书", "ja": "ガラテヤ人への手紙", "id": "Galatia", "es": "Gálatas", "ru": "Галатам", "fr": "Galates"},
        "에베소서": {"en": "Ephesians", "zh": "以弗所书", "ja": "エペソ人への手紙", "id": "Efesus", "es": "Efesios", "ru": "Ефесянам", "fr": "Éphésiens"},
        "빌립보서": {"en": "Philippians", "zh": "腓立比书", "ja": "ピリピ人への手紙", "id": "Filipi", "es": "Filipenses", "ru": "Филиппийцам", "fr": "Philippiens"},
        "골로새서": {"en": "Colossians", "zh": "歌罗西书", "ja": "コロサイ人への手紙", "id": "Kolose", "es": "Colosenses", "ru": "Колоссянам", "fr": "Colossiens"},
        "데살로니가전서": {"en": "1 Thessalonians", "zh": "帖撒罗尼迦前书", "ja": "テサロニケ人への第一の手紙", "id": "1 Tesalonika", "es": "1 Tesalonicenses", "ru": "1 Фессалоникийцам", "fr": "1 Thessaloniciens"},
        "데살로니가후서": {"en": "2 Thessalonians", "zh": "帖撒罗尼迦后书", "ja": "テサロニケ人への第二の手紙", "id": "2 Tesalonika", "es": "2 Tesalonicenses", "ru": "2 Фессалоникийцам", "fr": "2 Thessaloniciens"},
        "디모데전서": {"en": "1 Timothy", "zh": "提摩太前书", "ja": "テモテへの第一の手紙", "id": "1 Timotius", "es": "1 Timoteo", "ru": "1 Тимофею", "fr": "1 Timothée"},
        "디모데후서": {"en": "2 Timothy", "zh": "提摩太后书", "ja": "テモテへの第二の手紙", "id": "2 Timotius", "es": "2 Timoteo", "ru": "2 Тимофею", "fr": "2 Timothée"},
        "히브리서": {"en": "Hebrews", "zh": "希伯来书", "ja": "ヘブル人への手紙", "id": "Ibrani", "es": "Hebreos", "ru": "Евреям", "fr": "Hébreux"},
        "야고보서": {"en": "James", "zh": "雅各书", "ja": "ヤコブの手紙", "id": "Yakobus", "es": "Santiago", "ru": "Иакова", "fr": "Jacques"},
        "베드로전서": {"en": "1 Peter", "zh": "彼得前书", "ja": "ペテロの第一の手紙", "id": "1 Petrus", "es": "1 Pedro", "ru": "1 Петра", "fr": "1 Pierre"},
        "베드로후서": {"en": "2 Peter", "zh": "彼得后书", "ja": "ペテロの第二の手紙", "id": "2 Petrus", "es": "2 Pedro", "ru": "2 Петра", "fr": "2 Pierre"},
        "요한일서": {"en": "1 John", "zh": "约翰一书", "ja": "ヨハネの第一の手紙", "id": "1 Yohanes", "es": "1 Juan", "ru": "1 Иоанна", "fr": "1 Jean"},
        "요한이서": {"en": "2 John", "zh": "约翰二书", "ja": "ヨハネの第二の手紙", "id": "2 Yohanes", "es": "2 Juan", "ru": "2 Иоанна", "fr": "2 Jean"},
        "요한삼서": {"en": "3 John", "zh": "约翰三书", "ja": "ヨハネの第三の手紙", "id": "3 Yohanes", "es": "3 Juan", "ru": "3 Иоанна", "fr": "3 Jean"},
        "유다서": {"en": "Jude", "zh": "犹大书", "ja": "ユダの手紙", "id": "Yudas", "es": "Judas", "ru": "Иуды", "fr": "Jude"},
        "요한계시록": {"en": "Revelation", "zh": "启示录", "ja": "ヨハネの黙示録", "id": "Wahyu", "es": "Apocalipsis", "ru": "Откровение", "fr": "Apocalypse"}
    }

    def _translate_bible_ref(self, ref: str, lang: str) -> str:
        """성경 참조를 다른 언어로 번역"""
        if not ref:
            return ""
        for ko_book, translations in self.BIBLE_BOOK_TRANSLATIONS.items():
            if ko_book in ref:
                if lang in translations:
                    return ref.replace(ko_book, translations[lang])
        return ref

    def _get_english_bible_ref(self, ref: str) -> str:
        return self._translate_bible_ref(ref, 'en')

    def _get_chinese_bible_ref(self, ref: str) -> str:
        return self._translate_bible_ref(ref, 'zh')

    def _get_japanese_bible_ref(self, ref: str) -> str:
        return self._translate_bible_ref(ref, 'ja')

    def _get_indonesian_bible_ref(self, ref: str) -> str:
        return self._translate_bible_ref(ref, 'id')

    def _get_spanish_bible_ref(self, ref: str) -> str:
        return self._translate_bible_ref(ref, 'es')

    def _get_russian_bible_ref(self, ref: str) -> str:
        return self._translate_bible_ref(ref, 'ru')

    def _get_french_bible_ref(self, ref: str) -> str:
        return self._translate_bible_ref(ref, 'fr')

    def _translate_verse_to_english(self, verse_text: str) -> str:
        """성경 구절을 영어로 번역 (기본 구현 - 빈 문자열 반환, AI 번역은 별도 처리)"""
        # 실제 번역은 Vision OCR에서 AI를 통해 수행됨
        # 여기서는 기본값으로 빈 문자열 반환
        return ""

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
        """구조화된 예배 순서를 HTML용 포맷으로 변환

        v2.0 개선: 입력 데이터의 leader, time, items를 보존
        parse_bulletin_text()에서 추출한 데이터를 그대로 사용
        """
        result = []
        for svc in services:
            name = svc.get("name", "예배")

            # 시간: 입력 데이터 우선 사용, 없으면 추정
            time = svc.get("time", "")
            if not time:
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
                elif "저녁" in name or "찬양" in name:
                    time = "오후 7:00"

            # 담당 목사: 입력 데이터에서 가져오기 (leader 필드)
            leader = svc.get("leader", "")

            # 예배 순서 items: 입력 데이터 우선 사용
            items = svc.get("items", [])

            # items가 없으면 기본 순서 생성
            if not items:
                # 새 필드 추출 (presider, offering_prayer 등)
                hymn = svc.get("hymn", "")
                scripture = svc.get("scripture", "")
                sermon_title = svc.get("sermon_title", "")
                prayer = svc.get("prayer", "")  # 대표기도
                offering_prayer = svc.get("offering_prayer", "")  # 헌금기도
                presider = svc.get("presider", "")  # 사회

                items = [
                    {"name": "예배로 부르심", "name_en": "Call to Worship", "detail": ""},
                    {"name": "찬송", "name_en": "Hymn", "detail": hymn},
                    {"name": "신앙고백", "name_en": "Apostle's Creed", "detail": "사도신경"},
                    {"name": "대표기도", "name_en": "Prayer", "detail": prayer},
                    {"name": "성경봉독", "name_en": "Scripture Reading", "detail": scripture},
                    {"name": "찬양대", "name_en": "Choir", "detail": ""},
                    {"name": "설교", "name_en": "Sermon", "detail": sermon_title},
                    {"name": "헌금기도", "name_en": "Offertory Prayer", "detail": offering_prayer},
                    {"name": "축도", "name_en": "Benediction", "detail": ""}
                ]

            # 사회자 (여러 필드에서 추출)
            mc = svc.get("presider") or svc.get("司會") or svc.get("사회", "")

            # 설교 정보
            sermon_title = svc.get("sermon_title", "")
            sermon_pastor = svc.get("sermon_pastor", "") or leader

            # 대표기도자, 헌금기도자
            prayer_person = svc.get("prayer", "")
            offering_prayer_person = svc.get("offering_prayer", "")

            result.append({
                "name": name,
                "time": time,
                "leader": leader,  # 목사님 이름 보존
                "presider": mc or svc.get("presider", ""),  # 사회자 필드 보존
                "scripture": svc.get("scripture", ""),  # 성경봉독 필드 보존
                "mc": mc,
                "items": items,
                "sermon_title": sermon_title,
                "sermon_pastor": sermon_pastor,
                "prayer": prayer_person,  # 대표기도
                "representative_prayer": prayer_person,  # 대표기도 (alias)
                "offering_prayer": offering_prayer_person,  # 헌금기도
                "hymn": svc.get("hymn", "")  # 찬송가 필드 보존
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
        """HTML 구조 생성 - 전문가 템플릿 기반"""

        # 명성교회: '지난주 말씀'을 '새벽기도회' 뒤에 배치
        show_sermon_card = self.preset.get("show_sermon_card", True)

        # 지난주 말씀 섹션 (위치에 따라 다르게 배치)
        last_week_sermon_early = self._build_last_week_sermon(info) if show_sermon_card else ""
        last_week_sermon_late = self._build_last_week_sermon(info) if not show_sermon_card else ""

        return f'''<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, minimum-scale=1.0, maximum-scale=5.0, user-scalable=yes">
    <title>{info["church_name"]} 주보 - {info["date"]}</title>
    <meta name="description" content="{info["church_name"]} {info["date"]} 주보 - {info.get('sermon', {}).get('title', '')}">
    <!-- PWA 전체화면 지원 -->
    <meta name="mobile-web-app-capable" content="yes">
    <meta name="apple-mobile-web-app-capable" content="yes">
    <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
    <meta name="apple-mobile-web-app-title" content="{info["church_name"]}">
    <link rel="apple-touch-icon" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><text y='.9em' font-size='90'>⛪</text></svg>">
    <meta name="theme-color" content="{theme["theme_color"]}">
    {self._get_css(theme, is_harvest, theme_name)}
</head>
<body>
    {self._build_header(info, theme, is_harvest, theme_name)}
    {self._build_nav_tabs()}
    {self._build_dark_mode_toggle()}

    <main class="container">
        {self._build_verse_section(info, is_harvest, theme_name)}
        {self._build_worship_section(info, is_harvest, theme_name)}
        {self._build_sermon_word_section(info, theme_name)}
        {self._build_sermon_card(info, theme_name)}
        {last_week_sermon_early}
        {self._build_choir_section(info, is_harvest)}
        {self._build_news_section(info, theme_name)}
        {self._build_prayer_table_section(info, theme_name)}
        {self._build_member_news_section(info)}
        {self._build_dawn_prayer_section(info)}
        {last_week_sermon_late}
        {self._build_weekly_service_section(info)}
        {self._build_devotional_section(info)}
        {self._build_contact_section(info)}
        {self._build_staff_section(info, theme_name)}
        {self._build_sns_offering_section()}
        {self._build_share_section(is_harvest, theme_name)}
    </main>

    {self._build_footer(info, is_harvest)}
    {self._build_modals()}
    {self._get_javascript(info)}
</body>
</html>'''

    def _get_css(self, theme: Dict, is_harvest: bool, theme_name: str = "default") -> str:
        """CSS 스타일 생성 (참조 템플릿 기반, 교회별 프리셋 적용)"""
        harvest_vars = ""
        if is_harvest:
            harvest_vars = """
            --harvest: #8B6914;
            --accent-warm: #D4883E;"""

        harvest_color = theme.get("harvest", theme["primary"])

        # 교회별 프리셋 적용
        preset = self.preset
        font_style = preset.get("font_style", "sans-serif")
        letter_spacing = preset.get("letter_spacing", "2px")

        # 프리셋의 기본 색상과 테마 색상 병합 (테마가 default면 프리셋 색상 사용)
        primary_color = preset.get("primary", theme["primary"])
        primary_dark = preset.get("primary_dark", theme["primary_dark"])
        primary_light = preset.get("primary_light", theme["primary_light"])
        accent_color = preset.get("accent", theme["accent"])

        # 특정 테마(대림절, 부활절 등)가 적용된 경우 테마 색상 우선
        if theme.get("theme_color") and theme.get("theme_color") != "#5B4B9E":
            # 절기 테마는 primary만 오버라이드
            primary_color = theme["primary"]
            primary_dark = theme["primary_dark"]
            primary_light = theme["primary_light"]

        # 헤더 그라데이션 생성
        header_gradient = f"linear-gradient(135deg, {primary_color} 0%, {primary_dark} 100%)"

        # 폰트 패밀리
        if font_style == "serif":
            font_family = "'Noto Serif KR', 'Apple SD Gothic Neo', serif"
            font_import = "@import url('https://fonts.googleapis.com/css2?family=Noto+Serif+KR:wght@400;500;600;700&display=swap');"
        else:
            font_family = "-apple-system, BlinkMacSystemFont, 'Apple SD Gothic Neo', 'Noto Sans KR', 'Malgun Gothic', sans-serif"
            font_import = "@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;500;600;700&display=swap');"

        return f'''<style>
        {font_import}

        :root {{
            --primary: {primary_color};
            --primary-dark: {primary_dark};
            --primary-light: {primary_light};
            --accent: {accent_color};
            --text-dark: #1a1a2e;
            --text-gray: #6B7280;
            --text-light: #9CA3AF;
            --bg-white: #FFFFFF;
            --bg-gray: #F5F3FA;
            --border: #E5E7EB;
            --success: #10B981;
            --warning: #F59E0B;{harvest_vars}
            --harvest: {harvest_color};
            --letter-spacing: {letter_spacing};
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
            font-family: {font_family};
            background: var(--bg-gray);
            color: var(--text-dark);
            line-height: 1.6;
            min-height: 100vh;
        }}

        /* 헤더 - 스크롤 시 숨김/표시 */
        .header {{
            background: {header_gradient};
            color: white;
            padding: 20px;
            padding-top: env(safe-area-inset-top, 20px);
            position: relative;
            z-index: 1000;
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
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
            letter-spacing: var(--letter-spacing);
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

        /* 표어 뱃지 */
        .slogan-badge {{
            display: inline-flex;
            align-items: center;
            gap: 8px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 8px 20px;
            border-radius: 25px;
            font-size: 0.9em;
            margin: 12px 0;
            box-shadow: 0 4px 15px rgba(102, 126, 234, 0.4);
        }}

        .slogan-year {{
            background: rgba(255,255,255,0.2);
            padding: 3px 10px;
            border-radius: 12px;
            font-size: 0.85em;
            font-weight: 600;
        }}

        .slogan-text {{
            font-weight: 700;
            letter-spacing: 0.5px;
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

        /* 오늘의 말씀 - 컴팩트 카드 스타일 */
        .verse-card {{
            background: {theme["header_gradient"]};
            color: white;
            border-radius: 16px;
            padding: 14px 20px;
            margin-bottom: 16px;
            text-align: center;
            position: relative;
            overflow: hidden;
            box-shadow: 0 4px 16px rgba(91, 75, 158, 0.2);
        }}

        .verse-card::before {{
            content: "{'🌾' if is_harvest else '✝️'}";
            position: absolute;
            font-size: 3em;
            opacity: 0.1;
            top: -8px;
            right: -8px;
            filter: blur(1px);
        }}

        .verse-label {{
            font-size: 0.85em;
            font-weight: 600;
            letter-spacing: 0.3px;
            opacity: 0.95;
            text-shadow: 0 1px 2px rgba(0,0,0,0.15);
        }}

        .verse-ref {{
            font-size: 0.85em;
            font-weight: 600;
            background: rgba(255,255,255,0.2);
            display: inline-block;
            padding: 5px 14px;
            border-radius: 20px;
            border: 1px solid rgba(255,255,255,0.2);
            transition: all 0.2s ease;
        }}

        .verse-ref:hover {{
            background: rgba(255,255,255,0.3);
        }}

        .verse-ref a {{
            color: white;
            text-decoration: none;
        }}

        /* 말씀 아코디언 스타일 - 한 줄 레이아웃 */
        .verse-accordion {{
            cursor: pointer;
            user-select: none;
        }}

        .verse-header {{
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 16px;
            flex-wrap: wrap;
        }}

        .verse-toggle {{
            font-size: 0.7em;
            opacity: 0.8;
            transition: transform 0.3s ease;
            margin-left: 4px;
        }}

        .verse-accordion.expanded .verse-toggle {{
            transform: rotate(180deg);
        }}

        .verse-content {{
            max-height: 0;
            overflow: hidden;
            transition: max-height 0.4s ease-out, opacity 0.3s ease;
            opacity: 0;
        }}

        .verse-accordion.expanded .verse-content {{
            max-height: 500px;
            opacity: 1;
            transition: max-height 0.5s ease-in, opacity 0.3s ease;
        }}

        .verse-text {{
            font-size: 1.1em;
            line-height: 2;
            font-weight: 500;
            position: relative;
            z-index: 1;
            color: white;
            word-break: keep-all;
            text-align: justify;
            margin: 16px auto 20px;
            max-width: 95%;
            padding: 16px 20px;
            background: rgba(255,255,255,0.12);
            border-radius: 14px;
            border: 1px solid rgba(255,255,255,0.15);
            backdrop-filter: blur(4px);
            text-shadow: 0 1px 2px rgba(0,0,0,0.1);
        }}

        .verse-hint {{
            font-size: 0.75em;
            opacity: 0.7;
            margin-top: 8px;
        }}

        .verse-accordion.expanded .verse-hint {{
            display: none;
        }}

        /* 공통 예배순서 */
        .common-worship-order {{
            background: linear-gradient(135deg, var(--primary-light) 0%, #fff 100%);
            border-radius: 14px;
            padding: 20px;
            margin-bottom: 20px;
            border: 1px solid var(--border);
            box-shadow: 0 2px 8px rgba(91, 75, 158, 0.08);
        }}

        .common-order-title {{
            display: flex;
            flex-wrap: wrap;
            align-items: center;
            gap: 8px;
            font-weight: 700;
            font-size: 1.05em;
            color: var(--primary);
            margin-bottom: 16px;
            padding-bottom: 12px;
            border-bottom: 2px solid var(--primary);
        }}

        .order-icon {{
            font-size: 1.2em;
        }}

        /* 📖 오늘의 말씀 섹션 */
        .sermon-word-section {{
            background: linear-gradient(135deg, #f8f6ff 0%, #fff 100%);
            border-radius: 16px;
            overflow: hidden;
            margin-bottom: 20px;
            border: 1px solid var(--border);
            box-shadow: 0 2px 12px rgba(91, 75, 158, 0.1);
        }}

        .sermon-word-header {{
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 16px 20px;
            background: var(--primary);
            color: white;
            cursor: pointer;
            transition: background 0.2s ease;
        }}

        .sermon-word-header:hover {{
            background: #4a3d8f;
        }}

        .sermon-word-titles {{
            display: flex;
            flex-direction: column;
            gap: 2px;
        }}

        .sermon-word-titles .section-title {{
            margin: 0;
            font-size: 1.1em;
            font-weight: 700;
            color: white;
        }}

        .sermon-word-subtitle {{
            font-size: 0.75em;
            opacity: 0.85;
            font-style: italic;
            color: rgba(255,255,255,0.9);
        }}

        .sermon-word-toggle {{
            font-size: 0.8em;
            transition: transform 0.3s ease;
            color: white;
        }}

        .sermon-word-section.expanded .sermon-word-toggle {{
            transform: rotate(180deg);
        }}

        .sermon-word-preview {{
            padding: 16px 20px;
            text-align: center;
            background: white;
        }}

        .sermon-title-ko {{
            font-size: 1.2em;
            font-weight: 700;
            color: var(--primary);
            margin-bottom: 4px;
        }}

        .sermon-title-en {{
            font-size: 0.85em;
            color: #666;
            margin-bottom: 8px;
        }}

        .sermon-scripture-ref {{
            font-size: 0.9em;
            font-weight: 600;
            color: var(--primary);
            background: var(--primary-light);
            padding: 6px 14px;
            border-radius: 16px;
            display: inline-block;
        }}

        .sermon-word-content {{
            max-height: 0;
            overflow: hidden;
            transition: max-height 0.5s ease-out;
        }}

        .sermon-word-section.expanded .sermon-word-content {{
            max-height: 2000px;
            transition: max-height 0.6s ease-in;
        }}

        .sermon-full-text {{
            padding: 20px;
            line-height: 1.8;
            color: var(--text);
            font-size: 0.95em;
            background: white;
        }}

        .sermon-intro {{
            margin: 0 0 24px 0;
            padding: 16px;
            background: var(--primary-light);
            border-radius: 12px;
            line-height: 1.8;
            color: #333;
            text-align: justify;
            word-break: keep-all;
            font-weight: 500;
        }}

        .sermon-section {{
            margin-bottom: 28px;
        }}

        .sermon-subtitle {{
            font-size: 1.1em;
            font-weight: 700;
            color: var(--primary);
            margin: 0 0 12px 0;
            padding-bottom: 8px;
            border-bottom: 2px solid var(--primary-light);
        }}

        .sermon-paragraph {{
            margin: 0;
            text-align: justify;
            word-break: keep-all;
            line-height: 1.9;
            color: #333;
        }}

        .sermon-pastor {{
            margin-top: 28px;
            padding-top: 16px;
            border-top: 1px solid var(--border);
            text-align: right;
            font-weight: 600;
            color: var(--primary);
            font-size: 0.95em;
        }}

        /* 예배별 탭 버튼 */
        .service-tabs {{
            display: flex;
            gap: 6px;
            margin-left: auto;
            flex-wrap: wrap;
        }}

        .service-tab {{
            padding: 6px 12px;
            font-size: 0.75em;
            font-weight: 600;
            color: var(--primary);
            background: white;
            border: 1px solid var(--primary);
            border-radius: 16px;
            cursor: pointer;
            transition: all 0.2s ease;
            white-space: nowrap;
        }}

        .service-tab:hover {{
            background: var(--primary-light);
        }}

        .service-tab.active {{
            background: var(--primary);
            color: white;
            box-shadow: 0 2px 8px rgba(91, 75, 158, 0.3);
        }}

        .common-order-items {{
            display: flex;
            flex-direction: column;
            gap: 10px;
        }}

        .order-item {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 10px 14px;
            background: white;
            border-radius: 10px;
            border: 1px solid rgba(91, 75, 158, 0.1);
            transition: all 0.2s ease;
        }}

        .order-item:hover {{
            border-color: var(--primary);
            box-shadow: 0 2px 8px rgba(91, 75, 158, 0.12);
        }}

        .order-item.highlight-item {{
            background: linear-gradient(135deg, var(--primary) 0%, var(--primary-dark) 100%);
            color: white;
            border: none;
        }}

        .order-item.highlight-item .order-label,
        .order-item.highlight-item .order-value {{
            color: white;
        }}

        .order-item.sermon-order {{
            background: linear-gradient(135deg, var(--primary-light) 0%, #fff 100%);
            border: 1px solid rgba(91, 75, 158, 0.2);
        }}

        .order-item.sermon-order .order-label {{
            color: var(--primary);
            font-weight: 700;
        }}

        .order-label {{
            font-weight: 600;
            color: var(--text-dark);
            font-size: 0.95em;
        }}

        .order-value {{
            font-size: 0.9em;
            color: var(--text-gray);
            text-align: right;
        }}

        .order-value .bible-link,
        .order-value .hymn-link {{
            color: var(--primary);
            font-weight: 600;
            text-decoration: none;
            border-bottom: 1px dashed var(--primary);
        }}

        .order-value .bible-link:hover,
        .order-value .hymn-link:hover {{
            border-bottom-style: solid;
        }}

        /* 예배 정보 카드 */
        .worship-card {{
            background: white;
            border-radius: 12px;
            border: 1px solid var(--border);
            margin-bottom: 12px;
            overflow: hidden;
            box-shadow: 0 2px 8px rgba(0,0,0,0.04);
        }}

        .worship-header {{
            background: var(--primary);
            color: white;
            padding: 14px 18px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}

        .worship-title {{
            font-weight: 700;
            font-size: 1.05em;
        }}

        .worship-time {{
            font-size: 0.9em;
            opacity: 0.9;
            background: rgba(255,255,255,0.15);
            padding: 4px 10px;
            border-radius: 12px;
        }}

        .worship-body {{
            padding: 16px;
        }}

        .worship-item {{
            display: flex;
            justify-content: space-between;
            padding: 10px 0;
            border-bottom: 1px solid #f0f0f0;
        }}

        .worship-item:last-child {{
            border-bottom: none;
        }}

        .worship-item-label {{
            color: var(--text-gray);
            font-size: 0.9em;
            font-weight: 500;
        }}

        .worship-item-value {{
            font-weight: 600;
            color: var(--text-dark);
            font-size: 0.9em;
            text-align: right;
        }}

        .worship-item-value .bible-link,
        .worship-item-value .hymn-link {{
            color: var(--primary);
            text-decoration: none;
            border-bottom: 1px dashed var(--primary);
        }}

        .worship-item-value .bible-link:hover,
        .worship-item-value .hymn-link:hover {{
            border-bottom-style: solid;
        }}

        /* 설교 항목 강조 */
        .worship-item.sermon-item {{
            background: linear-gradient(135deg, var(--primary-light) 0%, #fff 100%);
            margin: 8px -16px;
            padding: 12px 16px;
            border-radius: 10px;
            border: 1px solid rgba(91, 75, 158, 0.15);
        }}

        .worship-item.sermon-item .worship-item-label {{
            color: var(--primary);
            font-weight: 600;
        }}

        .worship-item.sermon-item .worship-item-value {{
            color: var(--primary);
            font-weight: 700;
        }}

        /* 사회자 항목 */
        .worship-item.mc-item {{
            background: rgba(201, 168, 87, 0.1);
            margin: 0 -16px 8px;
            padding: 10px 16px;
            border-radius: 8px 8px 0 0;
            border-bottom: 2px solid var(--accent);
        }}

        .worship-item.mc-item .worship-item-label {{
            color: var(--accent);
            font-weight: 600;
        }}

        .sermon-highlight {{
            background: var(--primary-light);
            padding: 14px 18px;
            border-radius: 10px;
            margin-top: 12px;
        }}

        .sermon-title {{
            font-size: 1.05em;
            font-weight: 700;
            color: var(--primary);
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

        /* 설교 제목 박스 */
        .sermon-title-box {{
            text-align: center;
            padding: 20px;
            margin-bottom: 20px;
            background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
            border-radius: 16px;
        }}

        .sermon-main-title {{
            font-size: 1.4em;
            font-weight: 700;
            color: var(--text-dark);
            margin-bottom: 8px;
        }}

        .sermon-title-en {{
            font-size: 0.95em;
            color: var(--text-gray);
            margin-bottom: 12px;
        }}

        .sermon-scripture {{
            font-size: 0.95em;
        }}

        .sermon-scripture .bible-link {{
            color: var(--primary);
            text-decoration: none;
            font-weight: 600;
        }}

        .sermon-scripture .bible-link:hover {{
            text-decoration: underline;
        }}

        /* 설교 아코디언 */
        .sermon-accordion {{
            border: 1px solid var(--border);
            border-radius: 16px;
            overflow: hidden;
            background: white;
            margin-bottom: 20px;
        }}

        .sermon-accordion[open] {{
            box-shadow: 0 4px 20px rgba(0,0,0,0.1);
        }}

        .sermon-accordion-header {{
            display: flex;
            align-items: center;
            gap: 12px;
            padding: 16px 20px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            cursor: pointer;
            font-weight: 600;
        }}

        .sermon-accordion-header:hover {{
            filter: brightness(1.05);
        }}

        .accordion-icon {{
            font-size: 1.3em;
        }}

        .accordion-title {{
            flex: 1;
            font-size: 1em;
        }}

        .sermon-accordion[open] .accordion-arrow {{
            transform: rotate(180deg);
        }}

        .sermon-accordion-body {{
            padding: 24px;
            background: white;
        }}

        .sermon-content-full {{
            line-height: 2;
            font-size: 1em;
            color: var(--text-dark);
        }}

        .sermon-section-title {{
            font-size: 1.1em;
            color: var(--primary);
            margin: 28px 0 16px 0;
            padding: 12px 16px;
            background: var(--primary-light);
            border-radius: 8px;
            border-left: 4px solid var(--primary);
        }}

        .sermon-section-title-en {{
            font-size: 0.85em;
            color: var(--text-gray);
            font-weight: 400;
        }}

        .sermon-paragraph {{
            margin-bottom: 16px;
            text-align: justify;
            word-break: keep-all;
            text-indent: 1em;
        }}

        .sermon-placeholder {{
            color: var(--text-gray);
            font-style: italic;
            text-align: center;
            padding: 40px;
        }}

        .sermon-author-box {{
            display: flex;
            justify-content: flex-end;
            align-items: center;
            gap: 12px;
            margin-top: 24px;
            padding-top: 16px;
            border-top: 1px solid var(--border);
        }}

        .author-label {{
            font-size: 0.85em;
            color: var(--text-gray);
        }}

        .author-name {{
            font-size: 1.1em;
            font-weight: 700;
            color: var(--primary);
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

        /* 예배 시간 그리드 - 전문가 템플릿 스타일 */
        .service-grid {{
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 10px;
            margin-bottom: 20px;
        }}

        .service-item {{
            text-align: center;
            padding: 14px 10px;
            background: var(--bg-gray);
            border-radius: 12px;
            transition: all 0.2s;
        }}

        .service-item.highlight {{
            background: var(--primary-light);
            border: 2px solid var(--primary);
        }}

        .service-part {{
            font-size: 0.85em;
            font-weight: 700;
            color: var(--primary);
            margin-bottom: 4px;
        }}

        .service-time {{
            font-size: 1.1em;
            font-weight: 700;
            color: var(--text-dark);
            margin-bottom: 2px;
        }}

        .service-pastor {{
            font-size: 0.75em;
            color: var(--text-gray);
        }}

        /* 담당자 상세 테이블 */
        .service-roles-container {{
            margin: 16px 0;
            border-radius: 12px;
            overflow: hidden;
            box-shadow: 0 2px 8px rgba(0,0,0,0.08);
        }}

        .roles-table-scroll {{
            overflow-x: auto;
            -webkit-overflow-scrolling: touch;
        }}

        .service-roles-table {{
            width: 100%;
            min-width: 600px;
            border-collapse: collapse;
            font-size: 0.85em;
        }}

        .service-roles-table th,
        .service-roles-table td {{
            padding: 10px 8px;
            text-align: center;
            border-bottom: 1px solid var(--border);
        }}

        .service-roles-table th {{
            background: var(--primary);
            color: white;
            font-weight: 600;
            font-size: 0.85em;
            white-space: nowrap;
        }}

        .service-roles-table td {{
            background: white;
            color: var(--text-dark);
            white-space: nowrap;
        }}

        .service-roles-table tr:nth-child(even) td {{
            background: var(--bg-gray);
        }}

        .service-roles-table .part-cell {{
            font-weight: 700;
            color: var(--primary);
            background: var(--primary-light) !important;
        }}

        .service-roles-table .sermon-cell {{
            color: var(--accent);
            font-weight: 600;
        }}

        /* 예배별 담당자 상세 카드 */
        .service-detail-cards {{
            display: flex;
            flex-direction: column;
            gap: 16px;
            margin: 20px 0;
        }}

        .service-detail-card {{
            background: white;
            border-radius: 16px;
            box-shadow: 0 4px 15px rgba(0,0,0,0.08);
            overflow: hidden;
            border: 1px solid var(--border);
        }}

        .service-card-header {{
            background: linear-gradient(135deg, var(--primary) 0%, #5a6fd6 100%);
            color: white;
            padding: 12px 16px;
            font-weight: 700;
        }}

        .service-card-part {{
            font-size: 1.1em;
        }}

        .service-card-body {{
            padding: 16px;
        }}

        .service-roles {{
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 10px;
        }}

        .role-item {{
            display: flex;
            flex-direction: column;
            gap: 4px;
            padding: 10px 12px;
            background: var(--bg-gray);
            border-radius: 10px;
        }}

        .role-label {{
            font-size: 0.75em;
            color: var(--text-gray);
            font-weight: 600;
        }}

        .role-value {{
            font-size: 0.9em;
            font-weight: 600;
            color: var(--text-dark);
        }}

        .role-value.hymn-badge {{
            color: var(--accent);
        }}

        .sermon-info-card {{
            margin-top: 16px;
            padding: 16px;
            background: linear-gradient(135deg, #667eea15 0%, #764ba215 100%);
            border-radius: 12px;
            border-left: 4px solid var(--primary);
        }}

        .sermon-label {{
            font-size: 0.75em;
            color: var(--primary);
            font-weight: 700;
            margin-bottom: 6px;
        }}

        .sermon-info-title {{
            font-size: 1.05em;
            font-weight: 700;
            color: var(--text-dark);
            margin-bottom: 4px;
        }}

        .sermon-info-preacher {{
            font-size: 0.9em;
            color: var(--text-gray);
        }}

        @media (max-width: 400px) {{
            .service-roles {{
                grid-template-columns: 1fr;
            }}
        }}

        /* 예배 순서 - 전문가 템플릿 스타일 */
        .worship-order {{
            margin-top: 20px;
            border-top: 1px solid var(--border);
            padding-top: 16px;
        }}

        .worship-order-title {{
            font-weight: 700;
            color: var(--primary);
            margin-bottom: 12px;
            font-size: 0.9em;
        }}

        .worship-order-item {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 10px 0;
            border-bottom: 1px solid var(--border);
        }}

        .worship-order-item:last-child {{
            border-bottom: none;
        }}

        .worship-order-item.highlight {{
            background: var(--primary-light);
            margin: 0 -18px;
            padding: 10px 18px;
            border-radius: 8px;
        }}

        .worship-name {{
            font-weight: 600;
            color: var(--text-dark);
            font-size: 0.9em;
        }}

        .worship-detail {{
            font-size: 0.85em;
            color: var(--text-gray);
        }}

        .worship-hymn {{
            color: var(--primary);
            font-weight: 600;
        }}

        /* 설교 카드 - 전문가 템플릿 스타일 */
        .sermon-card-box {{
            background: linear-gradient(135deg, var(--accent-light, #FEF3C7) 0%, white 100%);
            border: 1px solid var(--accent);
            border-radius: 12px;
            padding: 18px;
            margin-bottom: 16px;
        }}

        .sermon-card-label {{
            font-size: 0.75em;
            color: var(--accent);
            font-weight: 600;
            margin-bottom: 8px;
        }}

        .sermon-card-title {{
            font-family: 'Noto Serif KR', serif;
            font-size: 1.3em;
            font-weight: 700;
            color: var(--primary);
            margin-bottom: 8px;
        }}

        .sermon-card-scripture {{
            font-size: 0.9em;
            color: var(--text-gray);
            margin-bottom: 8px;
        }}

        .sermon-card-preacher {{
            font-size: 0.95em;
            font-weight: 600;
            color: var(--text-dark);
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

        .choir-part {{
            font-size: 0.8em;
            color: var(--harvest);
            font-weight: 600;
            margin-bottom: 4px;
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

        /* 찬양 테이블 (데스크톱) */
        /* 금주의 찬양 - 원본 PDF 표 형식 유지 + 좌우 슬라이드 */
        .choir-table-container {{
            display: block;
            border-radius: 12px;
            overflow: hidden;
            box-shadow: 0 2px 8px rgba(0,0,0,0.08);
            position: relative;
        }}

        .choir-table-scroll {{
            overflow-x: auto;
            -webkit-overflow-scrolling: touch;
            scrollbar-width: thin;
            scrollbar-color: var(--primary) var(--bg-gray);
        }}

        .choir-table-scroll::-webkit-scrollbar {{
            height: 6px;
        }}

        .choir-table-scroll::-webkit-scrollbar-track {{
            background: var(--bg-gray);
            border-radius: 3px;
        }}

        .choir-table-scroll::-webkit-scrollbar-thumb {{
            background: var(--primary);
            border-radius: 3px;
        }}

        .choir-table {{
            width: 100%;
            min-width: 100%;
            border-collapse: collapse;
            font-size: 0.85em;
            table-layout: auto;
        }}

        .choir-table th {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 12px 10px;
            font-weight: 600;
            text-align: center;
            white-space: nowrap;
            position: sticky;
            top: 0;
            z-index: 1;
        }}

        .choir-table td {{
            padding: 12px 10px;
            text-align: center;
            border-bottom: 1px solid var(--border);
            background: white;
            white-space: nowrap;
        }}

        .choir-table tr:nth-child(even) td {{
            background: var(--bg-gray);
        }}

        .choir-service-cell {{
            font-weight: 700;
            color: var(--primary);
            min-width: 80px;
        }}

        .choir-name-cell {{
            font-weight: 600;
            color: var(--text-dark);
            min-width: 100px;
        }}

        .choir-song-cell {{
            color: var(--accent);
            font-weight: 500;
            min-width: 120px;
            white-space: normal;
            word-break: keep-all;
        }}

        .choir-conductor-cell,
        .choir-accompanist-cell {{
            min-width: 70px;
            color: var(--text-gray);
        }}

        /* 슬라이드 힌트 표시 */
        .choir-scroll-hint {{
            display: none;
            text-align: center;
            padding: 8px;
            font-size: 0.75em;
            color: var(--text-gray);
            background: linear-gradient(to right, transparent, var(--bg-gray), transparent);
        }}

        .choir-scroll-hint::before {{
            content: '← ';
        }}

        .choir-scroll-hint::after {{
            content: ' →';
        }}

        /* 모바일에서 슬라이드 힌트 표시 */
        @media (max-width: 600px) {{
            .choir-table {{
                min-width: 550px;
            }}

            .choir-table th,
            .choir-table td {{
                padding: 10px 8px;
                font-size: 0.8em;
            }}

            .choir-scroll-hint {{
                display: block;
            }}
        }}

        /* 다음 주간 대표기도 표 */
        .prayer-table-wrapper {{
            margin-top: 12px;
        }}

        .prayer-table-wrapper .scroll-hint {{
            text-align: center;
            font-size: 0.75em;
            color: var(--text-gray);
            padding: 6px 0;
            display: none;
        }}

        .prayer-table-scroll {{
            overflow-x: auto;
            -webkit-overflow-scrolling: touch;
            border-radius: 12px;
            border: 1px solid var(--border);
        }}

        .prayer-table-scroll::-webkit-scrollbar {{
            height: 6px;
        }}

        .prayer-table-scroll::-webkit-scrollbar-track {{
            background: var(--bg-light);
            border-radius: 3px;
        }}

        .prayer-table-scroll::-webkit-scrollbar-thumb {{
            background: var(--primary);
            border-radius: 3px;
        }}

        .prayer-table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 0.9em;
            min-width: 400px;
        }}

        .prayer-table th {{
            background: var(--primary);
            color: white;
            padding: 12px 10px;
            text-align: center;
            font-weight: 700;
            font-size: 0.85em;
            white-space: nowrap;
            border-right: 1px solid rgba(255,255,255,0.2);
        }}

        .prayer-table th:last-child {{
            border-right: none;
        }}

        .prayer-table td {{
            padding: 12px 10px;
            text-align: center;
            border-bottom: 1px solid var(--border);
            vertical-align: middle;
        }}

        .prayer-table td.prayer-category {{
            background: var(--bg-light);
            font-weight: 700;
            color: var(--primary);
        }}

        .prayer-table tr:last-child td {{
            border-bottom: none;
        }}

        .prayer-table tr:nth-child(even) td {{
            background: rgba(var(--primary-rgb), 0.03);
        }}

        .prayer-table tr:nth-child(even) td.prayer-category {{
            background: var(--bg-light);
        }}

        /* 대표기도 리스트 형식 (이전 호환) */
        .prayer-list {{
            display: flex;
            flex-direction: column;
            gap: 10px;
        }}

        .prayer-item {{
            display: flex;
            gap: 12px;
            padding: 12px;
            background: var(--bg-light);
            border-radius: 8px;
        }}

        .prayer-date {{
            font-weight: 700;
            color: var(--primary);
            white-space: nowrap;
        }}

        .prayer-name {{
            flex: 1;
            color: var(--text-dark);
        }}

        @media (max-width: 600px) {{
            .prayer-table-wrapper .scroll-hint {{
                display: block;
            }}

            .prayer-table {{
                min-width: 450px;
            }}

            .prayer-table th,
            .prayer-table td {{
                padding: 10px 8px;
                font-size: 0.8em;
            }}
        }}

        /* 교회 소식 - 전문가 템플릿 스타일 */
        .news-item-expert {{
            display: flex;
            flex-wrap: wrap;
            gap: 10px;
            padding: 14px 0;
            border-bottom: 1px solid var(--border);
        }}

        .news-item-expert:last-child {{
            border-bottom: none;
        }}

        .news-number {{
            width: 24px;
            height: 24px;
            background: var(--primary);
            color: white;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 0.8em;
            font-weight: 700;
            flex-shrink: 0;
        }}

        .news-title-expert {{
            flex: 1;
            font-weight: 700;
            color: var(--text-dark);
        }}

        .news-content-expert {{
            width: 100%;
            padding-left: 34px;
            font-size: 0.9em;
            color: var(--text-gray);
            line-height: 1.7;
        }}

        .news-highlight {{
            background: var(--primary-light);
            border-radius: 8px;
            padding: 12px;
            margin-top: 10px;
        }}

        /* 교회 소식 아코디언 */
        .news-accordion {{
            display: flex;
            flex-direction: column;
            gap: 12px;
        }}

        .news-category-accordion {{
            border: 1px solid var(--border);
            border-radius: 12px;
            overflow: hidden;
            background: white;
        }}

        .news-category-accordion[open] {{
            box-shadow: 0 4px 12px rgba(0,0,0,0.1);
        }}

        .news-category-header {{
            display: flex;
            align-items: center;
            gap: 10px;
            padding: 14px 16px;
            background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
            cursor: pointer;
            font-weight: 600;
        }}

        .news-category-header:hover {{
            background: linear-gradient(135deg, #e9ecef 0%, #dee2e6 100%);
        }}

        .news-category-icon {{
            font-size: 1.2em;
        }}

        .news-category-name {{
            flex: 1;
            font-size: 0.95em;
            color: var(--text-dark);
        }}

        .news-category-count {{
            background: var(--primary);
            color: white;
            padding: 2px 8px;
            border-radius: 10px;
            font-size: 0.75em;
        }}

        .accordion-arrow {{
            font-size: 0.7em;
            color: var(--text-gray);
            transition: transform 0.3s ease;
        }}

        .news-category-accordion[open] .accordion-arrow {{
            transform: rotate(180deg);
        }}

        .news-category-body {{
            padding: 12px 16px;
            background: white;
        }}

        .news-item-accordion {{
            display: flex;
            gap: 10px;
            padding: 10px 0;
            border-bottom: 1px solid var(--border);
        }}

        .news-item-accordion:last-child {{
            border-bottom: none;
        }}

        .news-num {{
            width: 22px;
            height: 22px;
            background: var(--primary-light);
            color: var(--primary);
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 0.75em;
            font-weight: 700;
            flex-shrink: 0;
        }}

        .news-item-content {{
            flex: 1;
        }}

        .news-item-title {{
            font-weight: 600;
            color: var(--text-dark);
            font-size: 0.9em;
            margin-bottom: 4px;
        }}

        .news-item-detail {{
            font-size: 0.85em;
            color: var(--text-gray);
            line-height: 1.6;
        }}

        /* 소식 항목별 아코디언 */
        .news-item-detail-accordion {{
            border: none;
            margin-bottom: 8px;
        }}

        .news-item-summary {{
            display: flex;
            align-items: center;
            gap: 10px;
            padding: 10px 12px;
            background: var(--bg-light);
            border-radius: 8px;
            cursor: pointer;
            list-style: none;
        }}

        .news-item-summary::-webkit-details-marker {{
            display: none;
        }}

        .news-num {{
            width: 22px;
            height: 22px;
            background: var(--primary);
            color: white;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 0.75em;
            font-weight: 700;
            flex-shrink: 0;
        }}

        .news-item-title {{
            flex: 1;
            font-weight: 600;
            color: var(--text-dark);
            font-size: 0.9em;
        }}

        .news-item-arrow {{
            font-size: 0.7em;
            color: var(--text-gray);
            transition: transform 0.2s;
        }}

        .news-item-detail-accordion[open] .news-item-arrow {{
            transform: rotate(180deg);
        }}

        .news-item-detail-content {{
            padding: 12px 16px 12px 44px;
            font-size: 0.85em;
            color: var(--text-gray);
            line-height: 1.8;
            background: rgba(var(--primary-rgb), 0.03);
            border-radius: 0 0 8px 8px;
            margin-top: -4px;
        }}

        .news-item-simple {{
            display: flex;
            align-items: center;
            gap: 10px;
            padding: 10px 12px;
            background: var(--bg-light);
            border-radius: 8px;
            margin-bottom: 8px;
        }}

        /* 교우 소식 섹션 */
        .member-news-section {{
            margin-bottom: 16px;
        }}

        .member-news-title {{
            font-weight: 700;
            color: var(--primary);
            margin-bottom: 8px;
            font-size: 0.95em;
        }}

        .member-news-list {{
            font-size: 0.85em;
            color: var(--text-gray);
            line-height: 1.7;
        }}

        .wedding-grid {{
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 10px;
        }}

        .wedding-card {{
            background: var(--bg-gray);
            border-radius: 10px;
            padding: 12px;
        }}

        .wedding-couple {{
            font-weight: 600;
            color: var(--text-dark);
            font-size: 0.85em;
            margin-bottom: 4px;
        }}

        .wedding-info {{
            font-size: 0.8em;
            color: var(--text-gray);
            line-height: 1.6;
        }}

        /* 새벽기도회 테이블 */
        .dawn-schedule {{
            overflow-x: auto;
        }}

        .dawn-table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 0.8em;
            min-width: 400px;
        }}

        .dawn-table th {{
            background: var(--primary);
            color: white;
            padding: 10px 8px;
            font-weight: 600;
            text-align: center;
        }}

        .dawn-table td {{
            padding: 8px;
            border-bottom: 1px solid var(--border);
            text-align: center;
        }}

        .dawn-table tr:nth-child(even) {{
            background: var(--bg-gray);
        }}

        /* 지난주 말씀 */
        .last-week-sermon {{
            background: var(--bg-gray);
            border-radius: 12px;
            padding: 18px;
        }}

        .last-week-title {{
            font-family: 'Noto Serif KR', serif;
            font-size: 1.1em;
            font-weight: 700;
            color: var(--primary);
            margin-bottom: 8px;
        }}

        .last-week-ref {{
            font-size: 0.85em;
            color: var(--accent);
            margin-bottom: 12px;
        }}

        .last-week-content {{
            font-size: 0.9em;
            color: var(--text-dark);
            line-height: 1.9;
            text-align: justify;
        }}

        /* ========================================
           명성교회 고도화 - 아코디언 컴포넌트
           ======================================== */
        .accordion {{
            border: 1px solid var(--border);
            border-radius: 12px;
            overflow: hidden;
            margin-bottom: 12px;
        }}

        .accordion-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 14px 16px;
            background: var(--bg-gray);
            cursor: pointer;
            transition: background 0.2s;
            user-select: none;
        }}

        .accordion-header:hover {{
            background: var(--primary-light);
        }}

        .accordion-title {{
            font-weight: 600;
            color: var(--text-dark);
            display: flex;
            align-items: center;
            gap: 8px;
        }}

        .accordion-title .icon {{
            font-size: 1.1em;
        }}

        .accordion-ref {{
            font-size: 0.85em;
            color: var(--accent);
            font-weight: 500;
        }}

        .accordion-arrow {{
            font-size: 0.8em;
            color: var(--text-gray);
            transition: transform 0.3s;
        }}

        .accordion.open .accordion-arrow {{
            transform: rotate(180deg);
        }}

        .accordion-content {{
            max-height: 0;
            overflow: hidden;
            transition: max-height 0.3s ease-out;
            background: white;
        }}

        .accordion.open .accordion-content {{
            max-height: 2000px;
        }}

        .accordion-body {{
            padding: 16px;
            font-size: 0.9em;
            line-height: 1.8;
            color: var(--text-dark);
        }}

        /* 지난주 말씀 아코디언 */
        .last-week-accordion {{
            background: linear-gradient(135deg, var(--bg-gray) 0%, white 100%);
            border: 1px solid var(--border);
            border-radius: 12px;
            margin-bottom: 16px;
        }}

        .last-week-accordion .accordion-header {{
            background: transparent;
            border-bottom: 1px solid var(--border);
        }}

        .last-week-accordion.open .accordion-header {{
            border-bottom: 1px solid var(--border);
        }}

        .last-week-accordion .accordion-body {{
            max-height: 400px;
            overflow-y: auto;
        }}

        /* 예배 회차별 탭 */
        .service-tabs {{
            display: flex;
            gap: 4px;
            margin-bottom: 16px;
            overflow-x: auto;
            padding-bottom: 4px;
        }}

        .service-tab {{
            flex-shrink: 0;
            padding: 8px 14px;
            background: var(--bg-gray);
            border: none;
            border-radius: 20px;
            font-size: 0.85em;
            font-weight: 600;
            color: var(--text-gray);
            cursor: pointer;
            transition: all 0.2s;
        }}

        .service-tab.active {{
            background: var(--primary);
            color: white;
        }}

        .service-tab .tab-name {{
            display: block;
            font-weight: 700;
        }}

        .service-tab .tab-time {{
            display: block;
            font-size: 0.75em;
            font-weight: 400;
            opacity: 0.8;
            margin-top: 2px;
        }}

        .service-tab-content {{
            display: none;
        }}

        .service-tab-content.active {{
            display: block;
        }}

        /* 회차별 상세 정보 */
        .service-details-container {{
            background: var(--bg-gray);
            border-radius: 12px;
            padding: 16px;
        }}

        .service-detail {{
            animation: fadeIn 0.3s ease;
        }}

        @keyframes fadeIn {{
            from {{ opacity: 0; transform: translateY(-8px); }}
            to {{ opacity: 1; transform: translateY(0); }}
        }}

        .service-detail-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 12px;
            padding-bottom: 12px;
            border-bottom: 2px solid var(--primary);
        }}

        .detail-part {{
            font-size: 1.2em;
            font-weight: 700;
            color: var(--primary);
        }}

        .detail-time {{
            font-size: 0.9em;
            color: var(--text-gray);
        }}

        .service-leader-info {{
            display: flex;
            gap: 20px;
            margin-bottom: 16px;
            padding: 12px;
            background: white;
            border-radius: 8px;
        }}

        .leader-item {{
            display: flex;
            align-items: center;
            gap: 8px;
        }}

        .leader-label {{
            font-size: 0.8em;
            color: var(--text-secondary);
            padding: 2px 8px;
            background: var(--primary-light);
            border-radius: 4px;
        }}

        .leader-value {{
            font-weight: 600;
            color: var(--text-dark);
        }}

        .service-hymns {{
            display: flex;
            flex-wrap: wrap;
            gap: 8px;
            margin-bottom: 16px;
        }}

        .hymn-badge {{
            display: inline-flex;
            align-items: center;
            gap: 4px;
            padding: 6px 12px;
            background: var(--accent-light);
            color: var(--accent);
            border-radius: 20px;
            font-size: 0.8em;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.2s;
        }}

        .hymn-badge:hover {{
            background: var(--accent);
            color: white;
            transform: translateY(-2px);
        }}

        /* 예배 순서 클릭 가능 항목 */
        .worship-order-item.clickable {{
            cursor: pointer;
            transition: all 0.2s;
        }}

        .worship-order-item.clickable:hover {{
            background: var(--primary-light);
            border-radius: 6px;
            padding-left: 8px;
            margin-left: -8px;
        }}

        .worship-order-item.clickable::after {{
            content: '→';
            margin-left: 8px;
            opacity: 0.5;
            font-size: 0.85em;
        }}

        .worship-order-item.standing {{
            background: linear-gradient(90deg, var(--primary-light) 0%, transparent 50%);
            border-left: 3px solid var(--primary);
            padding-left: 8px;
            margin-left: -8px;
        }}

        /* 예배 순서 상세 - 기립 표시 */
        .worship-order-item .stand-mark {{
            color: var(--accent);
            font-weight: 700;
            margin-right: 4px;
        }}

        .worship-order-item.stand {{
            position: relative;
        }}

        .worship-order-item.stand::before {{
            content: '*';
            color: var(--accent);
            font-weight: 700;
            margin-right: 4px;
        }}

        /* 찬송가/교독문/사도신경 아코디언 */
        .liturgy-accordion {{
            border: 1px solid var(--border);
            border-radius: 10px;
            margin: 8px 0;
            overflow: hidden;
        }}

        .liturgy-accordion .accordion-header {{
            padding: 10px 14px;
            background: var(--primary-light);
        }}

        .liturgy-accordion .accordion-body {{
            background: white;
            font-size: 0.85em;
            padding: 14px;
        }}

        .liturgy-accordion .verse-line {{
            padding: 4px 0;
            border-bottom: 1px dotted var(--border);
        }}

        .liturgy-accordion .verse-line:last-child {{
            border-bottom: none;
        }}

        .liturgy-accordion .responsive {{
            display: flex;
            gap: 8px;
        }}

        .liturgy-accordion .responsive .leader {{
            color: var(--primary);
            font-weight: 600;
            flex-shrink: 0;
        }}

        .liturgy-accordion .responsive .people {{
            color: var(--text-dark);
        }}

        /* 교우소식 카테고리 아코디언 */
        .member-news-accordion {{
            margin-bottom: 8px;
        }}

        .member-news-accordion .accordion-header {{
            padding: 12px 14px;
            background: white;
            border: 1px solid var(--border);
            border-radius: 10px;
        }}

        .member-news-accordion.open .accordion-header {{
            border-radius: 10px 10px 0 0;
            border-bottom: none;
        }}

        .member-news-accordion .accordion-content {{
            border: 1px solid var(--border);
            border-top: none;
            border-radius: 0 0 10px 10px;
        }}

        .member-news-badge {{
            background: var(--primary);
            color: white;
            font-size: 0.75em;
            padding: 2px 8px;
            border-radius: 10px;
            margin-left: 8px;
        }}

        .category-count {{
            font-size: 0.75em;
            color: var(--primary);
            background: var(--primary-light);
            padding: 2px 8px;
            border-radius: 12px;
            margin-left: 8px;
        }}

        .category-arrow {{
            font-size: 1.2em;
            color: var(--text-secondary);
            font-weight: 300;
        }}

        /* 교우소식 상세 항목 스타일 */
        .birth-list, .passing-list {{
            display: flex;
            flex-direction: column;
            gap: 8px;
        }}

        .birth-item, .passing-item {{
            display: flex;
            align-items: center;
            gap: 12px;
            padding: 8px 12px;
            background: var(--bg-gray);
            border-radius: 8px;
        }}

        .birth-parent, .passing-name {{
            font-weight: 600;
            color: var(--text-dark);
        }}

        .birth-baby {{
            color: var(--primary);
        }}

        .birth-date, .passing-date {{
            font-size: 0.85em;
            color: var(--text-secondary);
            margin-left: auto;
        }}

        .passing-relation {{
            font-size: 0.85em;
            color: var(--text-secondary);
        }}

        .wedding-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(140px, 1fr));
            gap: 12px;
        }}

        .wedding-card {{
            background: var(--bg-gray);
            padding: 12px;
            border-radius: 10px;
            text-align: center;
        }}

        .wedding-couple {{
            font-weight: 600;
            color: var(--primary);
            margin-bottom: 4px;
        }}

        .wedding-info {{
            font-size: 0.8em;
            color: var(--text-secondary);
        }}

        /* SNS 및 모바일 헌금 섹션 */
        .sns-offering-section {{
            background: linear-gradient(135deg, var(--primary-light) 0%, white 100%);
            border-radius: 16px;
            padding: 20px;
            margin-bottom: 16px;
        }}

        .sns-buttons {{
            display: flex;
            gap: 10px;
            margin-bottom: 16px;
            flex-wrap: wrap;
            justify-content: center;
        }}

        .sns-btn {{
            display: flex;
            align-items: center;
            gap: 6px;
            padding: 10px 16px;
            background: white;
            border: 1px solid var(--border);
            border-radius: 25px;
            font-size: 0.85em;
            font-weight: 600;
            color: var(--text-dark);
            text-decoration: none;
            transition: all 0.2s;
        }}

        .sns-btn:hover {{
            background: var(--primary);
            color: white;
            border-color: var(--primary);
        }}

        .sns-btn.youtube {{
            border-color: #FF0000;
            color: #FF0000;
        }}

        .sns-btn.youtube:hover {{
            background: #FF0000;
            color: white;
        }}

        .sns-btn.instagram {{
            border-color: #E4405F;
            color: #E4405F;
        }}

        .sns-btn.instagram:hover {{
            background: linear-gradient(45deg, #f09433, #e6683c, #dc2743, #cc2366, #bc1888);
            color: white;
        }}

        .sns-btn.facebook {{
            border-color: #1877F2;
            color: #1877F2;
        }}

        .sns-btn.facebook:hover {{
            background: #1877F2;
            color: white;
        }}

        .sns-btn.kakao {{
            border-color: #FEE500;
            color: #3C1E1E;
            background: #FEE500;
        }}

        .sns-btn.kakao:hover {{
            background: #F7D600;
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(254, 229, 0, 0.4);
        }}

        .sns-btn.homepage {{
            background: linear-gradient(135deg, var(--primary) 0%, var(--primary-dark) 100%);
            color: white;
        }}

        .sns-btn.homepage:hover {{
            filter: brightness(1.1);
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(91, 75, 158, 0.4);
        }}

        /* SNS 그리드 - 전문가 결과물 스타일 (fg-2025-12-14 기준) */
        .sns-grid {{
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 12px;
        }}

        .sns-item {{
            display: flex;
            flex-direction: column;
            align-items: center;
            padding: 16px 8px;
            background: var(--bg-gray);
            border-radius: 12px;
            text-decoration: none;
            transition: all 0.2s;
        }}

        .sns-item:hover {{
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(0,0,0,0.1);
        }}

        .sns-icon {{
            font-size: 2em;
            margin-bottom: 8px;
        }}

        .sns-name {{
            font-size: 0.8em;
            font-weight: 600;
            color: var(--text-dark);
        }}

        .sns-item.youtube {{ background: linear-gradient(135deg, #FFE5E5 0%, #FFF 100%); }}
        .sns-item.youtube:hover {{ background: #FFE5E5; }}
        .sns-item.instagram {{ background: linear-gradient(135deg, #FCE4EC 0%, #FFF 100%); }}
        .sns-item.instagram:hover {{ background: #FCE4EC; }}
        .sns-item.facebook {{ background: linear-gradient(135deg, #E3F2FD 0%, #FFF 100%); }}
        .sns-item.facebook:hover {{ background: #E3F2FD; }}
        .sns-item.website {{ background: linear-gradient(135deg, #E8F5E9 0%, #FFF 100%); }}
        .sns-item.website:hover {{ background: #E8F5E9; }}

        /* 헌금 그리드 - 전문가 결과물 스타일 (fg-2025-12-14 기준) */
        .offering-grid {{
            display: grid;
            gap: 12px;
        }}

        .offering-item {{
            display: flex;
            align-items: center;
            padding: 16px;
            background: linear-gradient(135deg, var(--primary-light) 0%, #fff 100%);
            border-radius: 12px;
            border: 1px solid var(--border);
            cursor: pointer;
            transition: all 0.2s;
        }}

        .offering-item:hover {{
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(91, 75, 158, 0.15);
        }}

        .offering-item .offering-icon {{
            font-size: 2em;
            margin-right: 16px;
        }}

        .offering-info {{
            flex: 1;
        }}

        .offering-name {{
            font-weight: 700;
            color: var(--primary);
            margin-bottom: 4px;
        }}

        .offering-desc {{
            font-size: 0.85em;
            color: var(--text-gray);
        }}

        .offering-arrow {{
            font-size: 1.2em;
            color: var(--primary);
        }}

        .offering-section {{
            text-align: center;
        }}

        /* 헌금 버튼 그룹 (전문가 수준) */
        .offering-buttons {{
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 12px;
            margin-top: 16px;
        }}

        .offering-method-btn {{
            display: flex;
            flex-direction: column;
            align-items: center;
            gap: 8px;
            padding: 20px 16px;
            background: var(--bg-gray);
            border: 2px solid var(--border);
            border-radius: 16px;
            cursor: pointer;
            transition: all 0.2s;
        }}

        .offering-method-btn:hover {{
            background: var(--primary-light);
            border-color: var(--primary);
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(0,0,0,0.1);
        }}

        .offering-method-btn .offering-icon {{
            font-size: 2em;
        }}

        .offering-method-btn .offering-label {{
            font-size: 0.9em;
            font-weight: 600;
            color: var(--text-dark);
        }}

        .offering-method-btn.kakao {{
            border-color: #FEE500;
        }}

        .offering-method-btn.kakao:hover {{
            background: #FFF9D9;
            border-color: #FEE500;
        }}

        .offering-method-btn.app {{
            border-color: var(--primary);
        }}

        .offering-method-btn.app:hover {{
            background: var(--primary-light);
            border-color: var(--primary);
        }}

        .offering-title {{
            font-size: 0.9em;
            font-weight: 600;
            color: var(--primary);
            margin-bottom: 12px;
        }}

        .offering-btn {{
            display: inline-flex;
            align-items: center;
            gap: 8px;
            padding: 12px 24px;
            background: var(--primary);
            color: white;
            border: none;
            border-radius: 25px;
            font-size: 0.9em;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.2s;
            text-decoration: none;
        }}

        .offering-btn:hover {{
            background: var(--primary-dark);
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(0,0,0,0.2);
        }}

        .bank-accounts {{
            margin-top: 12px;
            font-size: 0.85em;
        }}

        .bank-account {{
            padding: 4px 0;
        }}

        .bank-account-item {{
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 12px 16px;
            margin-bottom: 8px;
            background: var(--bg-gray);
            border-radius: 10px;
            gap: 12px;
        }}

        .bank-name {{
            font-weight: 600;
            color: var(--primary);
            min-width: 70px;
        }}

        .account-number {{
            flex: 1;
            font-family: 'Courier New', monospace;
            color: var(--text-dark);
            cursor: pointer;
            padding: 4px 8px;
            background: white;
            border-radius: 4px;
            border: 1px dashed var(--border);
            transition: all 0.2s;
        }}

        .account-number:hover {{
            background: var(--primary-light);
            border-color: var(--primary);
        }}

        .account-holder {{
            font-size: 0.85em;
            color: var(--text-gray);
        }}

        /* 계좌번호 등록 예정 스타일 */
        .bank-account-item.pending {{
            background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
            border: 1px dashed var(--border);
        }}

        .pending-text {{
            color: var(--text-gray);
            font-style: italic;
            cursor: default;
            background: transparent;
            border: none;
        }}

        .pending-text:hover {{
            background: transparent;
            border: none;
        }}

        .section-subtitle {{
            font-size: 0.9em;
            font-weight: 600;
            color: var(--primary);
            margin-bottom: 12px;
        }}

        /* 연락처 그리드 */
        .contact-grid {{
            display: grid;
            gap: 10px;
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
            font-size: 0.75em;
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

        /* 주보 정보 */
        .jubo-info {{
            display: flex;
            justify-content: center;
            gap: 16px;
            font-size: 0.9em;
            opacity: 0.9;
            margin-top: 12px;
        }}

        .jubo-number {{
            opacity: 0.8;
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

        /* 오늘의 양식 아코디언 */
        .devotional-accordion {{
            border: 1px solid var(--border);
            border-radius: 12px;
            overflow: hidden;
            background: linear-gradient(135deg, #f8f9fa 0%, #fff 100%);
        }}

        .devotional-accordion[open] {{
            box-shadow: 0 4px 15px rgba(0,0,0,0.1);
        }}

        .devotional-header {{
            display: flex;
            align-items: center;
            gap: 12px;
            padding: 16px 20px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            cursor: pointer;
            font-weight: 600;
        }}

        .devotional-header:hover {{
            filter: brightness(1.05);
        }}

        .devotional-icon {{
            font-size: 1.3em;
        }}

        .devotional-header .devotional-title {{
            flex: 1;
            font-size: 1em;
            font-weight: 700;
            color: white;
            text-align: left;
            margin: 0;
            padding: 0;
            border: none;
        }}

        .devotional-arrow {{
            font-size: 0.8em;
            opacity: 0.8;
            transition: transform 0.3s ease;
        }}

        .devotional-accordion[open] .devotional-arrow {{
            transform: rotate(180deg);
        }}

        .devotional-body {{
            padding: 20px;
            background: white;
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

        /* 우측 상단 컨트롤 */
        .top-controls {{
            position: fixed;
            top: 80px;
            right: 16px;
            display: flex;
            flex-direction: column;
            gap: 8px;
            z-index: 998;
        }}

        /* 언어 선택 */
        .language-selector {{
            background: white;
            border: 1px solid var(--border);
            border-radius: 8px;
            padding: 8px 12px;
            font-size: 0.85em;
            cursor: pointer;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            transition: all 0.2s;
            outline: none;
        }}

        .language-selector:hover {{
            border-color: var(--primary);
        }}

        /* 다크모드 토글 */
        .dark-mode-toggle {{
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

        body.dark-mode .dark-mode-toggle,
        body.dark-mode .language-selector {{
            background: var(--bg-white);
            color: var(--text-dark);
            border-color: var(--border);
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

    def _build_header(self, info: Dict, theme: Dict, is_harvest: bool, theme_name: str = "default") -> str:
        """헤더 섹션 생성 - 전문가 템플릿 기반"""
        # 절기별 배지 설정
        THEME_BADGES = {
            "advent": ("🕯️", "대림절"),
            "christmas": ("🎄", "성탄절"),
            "lent": ("✝️", "사순절"),
            "easter": ("🌸", "부활절"),
            "pentecost": ("🔥", "성령강림절"),
            "harvest": ("🌾", "추수감사절")
        }

        theme_badge_html = ""
        sunday_type = ""
        if theme_name in THEME_BADGES:
            icon, name = THEME_BADGES[theme_name]
            theme_badge_html = f'<div class="theme-badge">{icon} {name}</div>'
            sunday_type = name

        # 권/호 정보
        volume_issue = ""
        if info.get("volume") and info.get("issue"):
            volume_issue = f'{info["volume"]}권 {info["issue"]}호'

        # 날짜와 권호 표시
        jubo_info_html = f'''
            <div class="jubo-info">
                <span class="jubo-date">{info["date"]}</span>
                {f'<span class="jubo-number">{volume_issue}</span>' if volume_issue else ''}
            </div>'''

        # 2025 표어 뱃지 추가
        slogan = info.get("slogan", "")
        slogan_badge_html = ""
        if slogan:
            slogan_badge_html = f'''
            <div class="slogan-badge">
                <span class="slogan-year">2025 표어</span>
                <span class="slogan-text">{slogan}</span>
            </div>'''

        return f'''
    <!-- 헤더 -->
    <header class="header">
        <div class="header-content">
            {theme_badge_html}
            {slogan_badge_html}
            <h1 class="church-name">
                {info["church_name"]}
                <span class="church-name-en">{info["church_name_en"]}</span>
            </h1>
            {jubo_info_html}
        </div>
    </header>'''

    def _build_nav_tabs(self) -> str:
        """네비게이션 탭 생성 - 전문가 템플릿 스타일"""
        # 명성교회는 '오늘의 말씀' 없음 -> '지난주 말씀'으로 변경하고 새벽 뒤에 배치
        if not self.preset.get("show_sermon_card", True):
            return '''
    <!-- 네비게이션 탭 -->
    <nav class="nav-tabs">
        <div class="nav-tabs-inner">
            <a href="#worship" class="nav-tab active" data-i18n="nav_worship">예배</a>
            <a href="#news" class="nav-tab" data-i18n="nav_news">소식</a>
            <a href="#members" class="nav-tab" data-i18n="nav_members">교우</a>
            <a href="#dawn" class="nav-tab" data-i18n="nav_dawn">새벽</a>
            <a href="#last-sermon" class="nav-tab" data-i18n="nav_last_sermon">지난주 말씀</a>
            <a href="#contact" class="nav-tab" data-i18n="nav_contact">안내</a>
        </div>
    </nav>'''
        return '''
    <!-- 네비게이션 탭 -->
    <nav class="nav-tabs">
        <div class="nav-tabs-inner">
            <a href="#todays-word" class="nav-tab active" data-i18n="nav_verse">말씀</a>
            <a href="#worship" class="nav-tab" data-i18n="nav_worship">예배</a>
            <a href="#choir" class="nav-tab" data-i18n="nav_choir">찬양</a>
            <a href="#news" class="nav-tab" data-i18n="nav_news">소식</a>
            <a href="#devotional" class="nav-tab" data-i18n="nav_devotional">양식</a>
            <a href="#sns" class="nav-tab" data-i18n="nav_sns">SNS</a>
            <a href="#offering" class="nav-tab" data-i18n="nav_offering">헌금</a>
        </div>
    </nav>'''

    def _build_dark_mode_toggle(self) -> str:
        """다크모드 토글 및 언어 선택 버튼"""
        return '''
    <!-- 우측 상단 컨트롤 -->
    <div class="top-controls">
        <!-- 언어 선택 -->
        <select class="language-selector" onchange="changeLanguage(this.value)" title="언어 선택">
            <option value="ko" selected>한국어</option>
            <option value="en">English</option>
            <option value="zh">中文</option>
            <option value="ja">日本語</option>
            <option value="id">Bahasa Indonesia</option>
            <option value="es">Español</option>
            <option value="ru">Русский</option>
            <option value="fr">Français</option>
        </select>
        <!-- 다크모드 토글 -->
        <button class="dark-mode-toggle" onclick="toggleDarkMode()" title="다크모드">
            🌙
        </button>
    </div>'''

    def _build_verse_section(self, info: Dict, is_harvest: bool, theme_name: str = "default") -> str:
        """오늘의 말씀 섹션 - 전문가 템플릿 스타일 (fg-2025-12-14 기준)"""
        # 프리셋에서 '오늘의 말씀' 표시 여부 확인 (명성교회는 비활성화)
        if not self.preset.get("show_sermon_card", True):
            return ""

        verse = info.get("verse", {})
        text = verse.get("text", "")
        ref = verse.get("reference", "")

        # 말씀 텍스트 없으면 설교 정보에서 가져오기 시도
        if not text:
            sermon = info.get("sermon", {})
            scripture = sermon.get("scripture", "")
            if scripture:
                ref = scripture
                text = "오늘 예배를 통해 말씀의 은혜가 함께 하시길 기원합니다."
            else:
                # 기본값 제공 (여의도순복음교회 기준)
                ref = "누가복음 3:4~6"
                text = "선지자 이사야의 책에 쓴 바 광야에서 외치는 자의 소리가 있어 이르되 너희는 주의 길을 준비하라 그의 오실 길을 곧게 하라 모든 골짜기가 메워지고 모든 산과 작은 산이 낮아지고 굽은 것이 곧아지고 험한 길이 평탄하여질 것이요 모든 육체가 하나님의 구원하심을 보리라 하였느니라"

        # 성경 구절 키 생성 (예: "눅 3:4~6" -> "luke-3-4")
        verse_key = self._generate_verse_key(ref)

        # 테마별 아이콘과 레이블
        THEME_LABELS = {
            "advent": ("🕯️", "대림절 말씀"),
            "christmas": ("🎄", "성탄절 말씀"),
            "lent": ("✝️", "사순절 말씀"),
            "easter": ("🌸", "부활절 말씀"),
            "pentecost": ("🔥", "성령강림절 말씀"),
            "harvest": ("🌾", "추수감사 말씀")
        }

        icon, label = THEME_LABELS.get(theme_name, ("📖", "오늘의 말씀"))

        # 말씀 텍스트에 따옴표 추가 (없으면)
        if text and not text.startswith('"') and not text.startswith('"'):
            text = f'"{text}"'

        return f'''
        <!-- 오늘의 말씀 - 컴팩트 아코디언 -->
        <section id="verse" class="verse-card verse-accordion" onclick="toggleVerseAccordion(this)">
            <div class="verse-header">
                <span class="verse-label" data-i18n="section_verse">{label}</span>
                <span class="verse-ref">
                    <a href="javascript:void(0)" onclick="event.stopPropagation(); openBibleModal('{verse_key}')" data-i18n="verse_ref">{ref}</a>
                    <span class="verse-toggle">▼</span>
                </span>
            </div>
            <div class="verse-hint" data-i18n="tap_to_expand">👆 터치하여 말씀 보기</div>
            <div class="verse-content">
                <p class="verse-text" data-i18n="verse_text">{text}</p>
            </div>
        </section>'''

    def _generate_verse_key(self, reference: str) -> str:
        """성경 구절 참조를 JavaScript 키로 변환 (예: '눅 3:4~6' -> 'luke-3-4')"""
        if not reference:
            return "main-verse"

        # 성경책 이름 매핑
        BOOK_MAP = {
            "창": "gen", "출": "exod", "레": "lev", "민": "num", "신": "deut",
            "수": "josh", "삿": "judg", "룻": "ruth", "삼상": "1sam", "삼하": "2sam",
            "왕상": "1kgs", "왕하": "2kgs", "대상": "1chr", "대하": "2chr",
            "스": "ezra", "느": "neh", "에": "esth", "욥": "job", "시": "ps",
            "잠": "prov", "전": "eccl", "아": "song", "사": "isa", "렘": "jer",
            "애": "lam", "겔": "ezek", "단": "dan", "호": "hos", "욜": "joel",
            "암": "amos", "옵": "obad", "욘": "jonah", "미": "mic", "나": "nah",
            "합": "hab", "습": "zeph", "학": "hag", "슥": "zech", "말": "mal",
            "마": "matt", "막": "mark", "눅": "luke", "요": "john", "행": "acts",
            "롬": "rom", "고전": "1cor", "고후": "2cor", "갈": "gal", "엡": "eph",
            "빌": "phil", "골": "col", "살전": "1thes", "살후": "2thes",
            "딤전": "1tim", "딤후": "2tim", "딛": "tit", "몬": "phlm", "히": "heb",
            "약": "jas", "벧전": "1pet", "벧후": "2pet", "요일": "1john", "요이": "2john",
            "요삼": "3john", "유": "jude", "계": "rev",
            # 전체 이름도 지원
            "창세기": "gen", "출애굽기": "exod", "레위기": "lev", "민수기": "num",
            "신명기": "deut", "여호수아": "josh", "사사기": "judg", "룻기": "ruth",
            "마태복음": "matt", "마가복음": "mark", "누가복음": "luke", "요한복음": "john",
            "사도행전": "acts", "로마서": "rom", "고린도전서": "1cor", "고린도후서": "2cor",
            "갈라디아서": "gal", "에베소서": "eph", "빌립보서": "phil", "골로새서": "col",
            "데살로니가전서": "1thes", "데살로니가후서": "2thes", "디모데전서": "1tim",
            "디모데후서": "2tim", "디도서": "tit", "빌레몬서": "phlm", "히브리서": "heb",
            "야고보서": "jas", "베드로전서": "1pet", "베드로후서": "2pet",
            "요한1서": "1john", "요한2서": "2john", "요한3서": "3john",
            "유다서": "jude", "요한계시록": "rev"
        }

        import re
        # 성경 구절 파싱 (예: "눅 3:4~6", "누가복음 3:4-6")
        match = re.match(r'([가-힣]+)\s*(\d+)\s*[:장]\s*(\d+)', reference)
        if match:
            book_kr = match.group(1)
            chapter = match.group(2)
            verse = match.group(3)
            book_en = BOOK_MAP.get(book_kr, "main")
            return f"{book_en}-{chapter}-{verse}"

        return "main-verse"

    def _build_sermon_word_section(self, info: Dict, theme_name: str = "default") -> str:
        """📖 오늘의 말씀 섹션 - 아코디언 형식 (원본 주보 콘텐츠 전체)"""
        sermon = info.get("sermon", {})
        # 빈 문자열도 기본값으로 대체 (or 연산자 사용)
        title_ko = sermon.get("title", "") or "예수님 오심을 기다리며(Ⅱ)"
        title_en = sermon.get("title_en", "") or "Waiting for Jesus' Coming(Ⅱ)"
        scripture = sermon.get("scripture", "") or "눅(Luke) 3:4~6"
        pastor = sermon.get("pastor", "") or "여의도순복음교회 이영훈 위임목사"

        return f'''
        <!-- 📖 오늘의 말씀 -->
        <section id="todays-word" class="section sermon-word-section">
            <div class="section-header sermon-word-header" onclick="toggleSermonWord(this.parentElement)">
                <div class="sermon-word-titles">
                    <h2 class="section-title">📖 오늘의 말씀</h2>
                    <span class="sermon-word-subtitle">Today's Word</span>
                </div>
                <span class="sermon-word-toggle">▼</span>
            </div>
            <div class="sermon-word-preview">
                <div class="sermon-title-ko">{title_ko}</div>
                <div class="sermon-title-en">({title_en})</div>
                <div class="sermon-scripture-ref">{scripture}</div>
            </div>
            <div class="sermon-word-content">
                <div class="sermon-full-text">
                    <p class="sermon-intro">예수님께서 이 땅에 오신 성탄절이 두 주 앞으로 다가왔습니다. 우리는 온 인류를 구원하시기 위해 오신 주님을 감사로 맞이해야 합니다. 굽어진 길을 곧게 하고 높아진 마음을 낮추며 빈 골짜기를 은혜로 채워 예수님의 성탄을 준비해야 합니다.</p>

                    <div class="sermon-section">
                        <h3 class="sermon-subtitle">1. 굽은 것이 곧아지고 (The Crooked Become Straight)</h3>
                        <p class="sermon-paragraph">주님의 길을 준비하기 위해서는 먼저 우리 마음의 굽어진 부분이 곧아져야 합니다. 울퉁불퉁한 땅이 평탄해져야 길이 열리듯 우리 안의 거짓되고 교활한 마음, 위선과 뒤틀린 생각이 바로 펴져야 주님을 맞이할 수 있습니다. 마음이 비뚤어지면 모든 것을 부정적으로 바라보게 되고 비방과 거짓으로 사람들에게 상처를 주기 쉽습니다. 이런 모습을 경계하며 성경은 분함과 악의, 위선과 거짓을 버리라고 권면합니다(골 3:8~9, 벧전 2:1). 그러므로 우리는 우리 마음을 살펴 굽어진 부분을 주님 앞에 겸손히 회개해야 합니다. 정직과 진실로 마음을 곧게 세울 때 주님께서 우리 안에 찾아오십니다. 왜곡된 마음을 바로잡고 어려운 이웃을 사랑으로 돌보는 삶을 통해 주님의 길을 준비하는 성도가 되기를 소망합니다.</p>
                    </div>

                    <div class="sermon-section">
                        <h3 class="sermon-subtitle">2. 험한 길이 평탄하여질 것이요 (The Rough Way Will Be Made Smooth)</h3>
                        <p class="sermon-paragraph">성경이 말하는 험한 길은 사람들이 지나기 어려운 울퉁불퉁한 땅, 열매 맺기 힘든 황폐한 땅을 말합니다. 이는 우리의 거친 마음과 황량한 심령을 의미합니다. 이렇게 마음이 거칠어지면 고집스럽고 날카로운 태도로 사람들과 부딪히기 쉽습니다. 또한 우리 안에 자리한 죄의 습관은 우리 마음을 황폐하게 합니다. 그러나 예수님을 만나면 이러한 죄의 굴레가 끊어지고 심령이 온유하게 변화되어 이웃과 화평을 이루며 선한 열매를 맺는 삶으로 나아가게 됩니다. 주님의 은혜가 임하면 하나님께서 우리보다 앞서가시며 거친 길을 평탄하게 만들어 주십니다(사 45:2).</p>
                    </div>

                    <div class="sermon-section">
                        <h3 class="sermon-subtitle">3. 모든 육체가 하나님의 구원을 보리라 (All Flesh Will See the Salvation of God)</h3>
                        <p class="sermon-paragraph">무관심과 상처로 깊어진 골짜기는 십자가의 사랑으로 메우고 교만의 산은 겸손으로 낮추며 굽어진 마음은 정직과 진실로 곧게 펴야 합니다. 또한 죄의 습관과 거친 성격으로 인해 불화가 계속되던 험한 길을 화평의 길로 바꾸어야 합니다(눅 3:5). 이처럼 우리의 마음이 바로 세워지고 치유될 때 하나님의 구원이 우리 가운데 역사합니다. 구원의 역사가 우리 안에 나타날 때 예수님의 십자가 은혜가 주님을 사랑하는 모든 그리스도인의 삶 속에 임하게 됩니다. 그렇게 영혼이 잘 되고 범사가 잘 되고 강건케 되는 복을 누리며 깨어지고 낮아져 회개함으로 예수님으로 마음과 삶을 가득 채우는 복된 성탄절을 맞이하는 우리가 되기를 축원합니다.</p>
                    </div>

                    <div class="sermon-pastor">
                        {pastor}
                    </div>
                </div>
            </div>
        </section>'''

    def _build_worship_section(self, info: Dict, is_harvest: bool, theme_name: str = "default") -> str:
        """예배 안내 섹션 - 공통순서 + 개별 예배 카드 형식"""
        services = info.get("worship_services", [])

        # 명성교회 고도화: 회차별 탭 및 상세 정보 표시
        worship_config = self.preset.get("worship_config", {})
        show_per_service = worship_config.get("show_per_service_details", False)

        section_class = "advent" if theme_name == "advent" else ("harvest" if is_harvest else "")

        if show_per_service and len(services) > 1:
            # 명성교회 스타일: 회차별 탭 표시
            return self._build_worship_section_with_tabs(info, services, section_class, "주일낮예배", worship_config)

        # 공통순서 HTML 생성
        common_order_html = self._build_common_worship_order(info, services)

        # 전문가 결과물 스타일: worship-card로 각 예배 표시
        worship_cards_html = ""
        for service in services:
            worship_cards_html += self._build_single_worship_card(service)

        return f'''
        <!-- 예배 안내 -->
        <section id="worship" class="section">
            <div class="section-header">
                <span class="section-icon">⛪</span>
                <h2 class="section-title" data-i18n="section_worship">주일예배 안내</h2>
            </div>
            <div class="section-body">
                {common_order_html}
                {worship_cards_html}
            </div>
        </section>'''

    def _build_common_worship_order(self, info: Dict, services: List) -> str:
        """공통 예배순서 섹션 생성 - 여의도순복음교회 형식"""
        # 공통 찬송가 (기본값)
        common_hymn_first = "8장(통9장)"
        common_hymn_last = "635장"

        # 개별 예배 카드가 있는 경우: 공통순서 + 개별 카드 참조
        if services:
            return f'''
                <!-- 공통 예배순서 -->
                <div class="common-worship-order">
                    <div class="common-order-title">
                        <span class="order-icon">📋</span>
                        <span data-i18n="common_order_title">공통 예배순서</span>
                    </div>
                    <div class="common-order-items">
                        <div class="order-item">
                            <span class="order-label">예배로 부르심</span>
                            <span class="order-value"><a href="javascript:void(0)" onclick="openBibleModal('john-4-24')" class="bible-link">요 4:24</a> (사회자)</span>
                        </div>
                        <div class="order-item">
                            <span class="order-label">찬송</span>
                            <span class="order-value"><a href="javascript:void(0)" onclick="openHymnModal('8')" class="hymn-link">{common_hymn_first}</a> 4절 (다같이, 일어서서)</span>
                        </div>
                        <div class="order-item">
                            <span class="order-label">신앙고백</span>
                            <span class="order-value">사도신경 (다같이, 일어서서)</span>
                        </div>
                        <div class="order-item highlight-item">
                            <span class="order-label">⬇ 개별 예배순서</span>
                            <span class="order-value">아래 각 예배 카드 참조</span>
                        </div>
                        <div class="order-item">
                            <span class="order-label">찬송</span>
                            <span class="order-value"><a href="javascript:void(0)" onclick="openHymnModal('635')" class="hymn-link">{common_hymn_last}</a> 주기도문 (다같이, 일어서서)</span>
                        </div>
                        <div class="order-item">
                            <span class="order-label">축도</span>
                            <span class="order-value">설교자</span>
                        </div>
                    </div>
                </div>'''

        # 개별 예배 카드가 없는 경우: 탭 버튼 + 동적 템플릿
        return f'''
                <!-- 주일예배 순서 (탭 전환) -->
                <div class="common-worship-order">
                    <div class="common-order-title">
                        <span class="order-icon">📋</span>
                        <span data-i18n="common_order_title">주일예배 순서</span>
                        <div class="service-tabs">
                            <button class="service-tab active" onclick="switchService('1bu')" data-service="1bu">1부</button>
                            <button class="service-tab" onclick="switchService('234bu')" data-service="234bu">2·3·4부</button>
                            <button class="service-tab" onclick="switchService('youth')" data-service="youth">5부 대학청년</button>
                            <button class="service-tab" onclick="switchService('evening')" data-service="evening">주일저녁</button>
                        </div>
                    </div>
                    <div class="common-order-items">
                        <div class="order-item">
                            <span class="order-label">예배로 부르심</span>
                            <span class="order-value"><a href="javascript:void(0)" onclick="openBibleModal('john-4-24')" class="bible-link">요 4:24</a> (사회자)</span>
                        </div>
                        <div class="order-item">
                            <span class="order-label">찬송</span>
                            <span class="order-value"><a href="javascript:void(0)" onclick="openHymnModal('8')" class="hymn-link">{common_hymn_first}</a> 4절 (다같이, 일어서서)</span>
                        </div>
                        <div class="order-item">
                            <span class="order-label">신앙고백</span>
                            <span class="order-value">사도신경 (다같이, 일어서서)</span>
                        </div>
                        <div class="order-item" id="hymn-row">
                            <span class="order-label">찬송</span>
                            <span class="order-value" id="hymn-value"><a href="javascript:void(0)" onclick="openHymnModal('301')" class="hymn-link">301장</a>(통460장) (다같이)</span>
                        </div>
                        <div class="order-item" id="prayer-row">
                            <span class="order-label">기도</span>
                            <span class="order-value" id="prayer-value">대표기도자</span>
                        </div>
                        <div class="order-item" id="scripture-row">
                            <span class="order-label">성경봉독</span>
                            <span class="order-value" id="scripture-value"><a href="javascript:void(0)" onclick="openBibleModal('phil-1-3')" class="bible-link">빌 1:3~8</a> (사회자)</span>
                        </div>
                        <div class="order-item" id="choir-row">
                            <span class="order-label">찬양</span>
                            <span class="order-value" id="choir-value">찬양대</span>
                        </div>
                        <div class="order-item sermon-order" id="sermon-row">
                            <span class="order-label">설교</span>
                            <span class="order-value" id="sermon-value">담임목사</span>
                        </div>
                        <div class="order-item">
                            <span class="order-label">기도와 결신</span>
                            <span class="order-value">설교자</span>
                        </div>
                        <div class="order-item" id="offering-row">
                            <span class="order-label">헌금기도</span>
                            <span class="order-value" id="offering-value">헌금기도자</span>
                        </div>
                        <div class="order-item">
                            <span class="order-label">찬송</span>
                            <span class="order-value"><a href="javascript:void(0)" onclick="openHymnModal('635')" class="hymn-link">{common_hymn_last}</a> 주기도문 (다같이, 일어서서)</span>
                        </div>
                        <div class="order-item">
                            <span class="order-label">축도</span>
                            <span class="order-value">설교자</span>
                        </div>
                    </div>
                </div>'''

    def _build_single_worship_card(self, service: Dict) -> str:
        """단일 예배 카드 생성 - 전문가 결과물 스타일 (fg-2025-12-14 기준)"""
        name = service.get("name", "예배")
        time = service.get("time", "")

        # 예배 이름 포맷 (예: "1부 예배", "2부 예배")
        part_name = name.replace(" 예배", "").replace("예배", "").strip()
        if part_name and not part_name.endswith("부"):
            if part_name[0].isdigit():
                part_name = f"{part_name}부 예배"
            else:
                part_name = f"{part_name} 예배"
        else:
            part_name = f"{part_name} 예배" if part_name else name

        # 시간 포맷 (오전/오후 → AM/PM)
        time_display = time
        if "오전" in time:
            time_display = time.replace("오전 ", "") + " AM"
        elif "오후" in time:
            time_display = time.replace("오후 ", "") + " PM"

        # 담당자 정보 추출 (vision_ocr.py 필드명과 호환)
        presider = service.get("presider", "")  # 사회자
        scripture = service.get("scripture", "")  # 성경봉독
        scripture_reader = service.get("scripture_reader", "")  # 성경봉독자
        rep_prayer = service.get("representative_prayer", "") or service.get("prayer", "")  # 대표기도
        offering_prayer = service.get("offering_prayer", "")  # 헌금기도
        hymns = service.get("hymn", "") or service.get("hymns", "")  # 찬송가
        sermon_title = service.get("sermon_title", "")  # 설교 제목
        preacher = service.get("leader", "") or service.get("preacher", "") or service.get("sermon_pastor", "")  # 설교자
        choir = service.get("choir", "") or service.get("praise_team", "")  # 찬양대/찬양팀

        # 예배 항목 HTML 생성 (순서대로: 기도 → 성경봉독 → 찬양 → 설교 → 기도와 결신 → 헌금기도)
        items_html = ""

        # 1. 기도 (대표기도)
        if rep_prayer:
            items_html += f'''
                        <div class="worship-item">
                            <span class="worship-item-label" data-i18n="label_prayer">기도 (대표기도)</span>
                            <span class="worship-item-value">{rep_prayer}</span>
                        </div>'''

        # 2. 성경봉독 (클릭 가능한 링크로)
        if scripture:
            verse_key = self._generate_verse_key(scripture)
            reader_info = f" ({scripture_reader})" if scripture_reader else " (사회자)"
            items_html += f'''
                        <div class="worship-item">
                            <span class="worship-item-label" data-i18n="label_scripture">성경봉독</span>
                            <span class="worship-item-value"><a href="javascript:void(0)" onclick="openBibleModal('{verse_key}')" class="bible-link">{scripture}</a>{reader_info}</span>
                        </div>'''

        # 3. 찬양 (찬양대/찬양팀)
        if choir:
            items_html += f'''
                        <div class="worship-item">
                            <span class="worship-item-label" data-i18n="label_choir">찬양</span>
                            <span class="worship-item-value">{choir}</span>
                        </div>'''

        # 4. 설교
        if sermon_title or preacher:
            sermon_display = sermon_title if sermon_title else ""
            preacher_display = f" ({preacher})" if preacher else ""
            items_html += f'''
                        <div class="worship-item sermon-item">
                            <span class="worship-item-label" data-i18n="label_sermon">설교</span>
                            <span class="worship-item-value">{sermon_display}{preacher_display}</span>
                        </div>'''

        # 5. 기도와 결신 (설교자)
        if preacher:
            items_html += f'''
                        <div class="worship-item">
                            <span class="worship-item-label" data-i18n="label_decision">기도와 결신</span>
                            <span class="worship-item-value">{preacher}</span>
                        </div>'''

        # 6. 헌금기도
        if offering_prayer:
            items_html += f'''
                        <div class="worship-item">
                            <span class="worship-item-label" data-i18n="label_offering_prayer">헌금기도</span>
                            <span class="worship-item-value">{offering_prayer}</span>
                        </div>'''

        # 7. 찬송가 (부별 다른 찬송)
        if hymns:
            hymn_links = self._format_hymn_links(hymns)
            items_html += f'''
                        <div class="worship-item">
                            <span class="worship-item-label" data-i18n="label_hymn">찬송</span>
                            <span class="worship-item-value">{hymn_links}</span>
                        </div>'''

        # 사회자 정보 (헤더 옆에 표시하지 않고 별도 항목으로)
        mc_html = ""
        if presider:
            mc_html = f'''
                        <div class="worship-item mc-item">
                            <span class="worship-item-label" data-i18n="label_mc">사회</span>
                            <span class="worship-item-value">{presider}</span>
                        </div>'''

        return f'''
                <!-- {part_name} -->
                <div class="worship-card">
                    <div class="worship-header">
                        <span class="worship-title">{part_name}</span>
                        <span class="worship-time">{time_display}</span>
                    </div>
                    <div class="worship-body">{mc_html}{items_html}
                    </div>
                </div>'''

    def _format_hymn_links(self, hymns) -> str:
        """찬송가 번호를 클릭 가능한 링크로 변환"""
        import re

        if isinstance(hymns, list):
            # 리스트인 경우 각 항목 처리
            links = []
            for h in hymns:
                if isinstance(h, dict):
                    num = h.get("number", "")
                else:
                    num = str(h)
                if num:
                    links.append(f'<a href="javascript:void(0)" onclick="openHymnModal(\'{num}\')" class="hymn-link">{num}</a>')
            return ", ".join(links)
        elif isinstance(hymns, str):
            # 문자열인 경우: "8, 301" 또는 "8장, 301장" 등
            # 숫자만 추출
            numbers = re.findall(r'\d+', hymns)
            if numbers:
                links = [f'<a href="javascript:void(0)" onclick="openHymnModal(\'{num}\')" class="hymn-link">{num}</a>' for num in numbers]
                return ", ".join(links)
            return hymns
        return str(hymns)

    def _build_service_roles_table(self, services: List) -> str:
        """예배별 담당자 상세 테이블 (사회, 성경봉독, 대표기도, 헌금기도, 찬송, 설교)"""
        if not services:
            return ""

        # 담당자 정보가 있는지 확인
        has_roles = any(
            service.get("presider") or service.get("scripture_reader") or
            service.get("offering_prayer") or service.get("representative_prayer") or
            service.get("hymn") or service.get("sermon_title")
            for service in services
        )

        if not has_roles:
            return ""

        # 테이블 헤더
        table_html = '''
        <div class="service-roles-container">
            <div class="roles-table-scroll">
                <table class="service-roles-table">
                    <thead>
                        <tr>
                            <th>구분</th>
                            <th>사회</th>
                            <th>성경봉독</th>
                            <th>대표기도</th>
                            <th>헌금기도</th>
                            <th>찬송</th>
                            <th>설교</th>
                        </tr>
                    </thead>
                    <tbody>'''

        for service in services[:6]:
            name = service.get("name", "예배")
            part_name = name.replace(" 예배", "").replace("예배", "").strip()

            presider = service.get("presider", "-")
            scripture_reader = service.get("scripture_reader", "-")
            rep_prayer = service.get("representative_prayer", "-")
            offering_prayer = service.get("offering_prayer", "-")
            hymn = service.get("hymn", "-")
            sermon = service.get("sermon_title", "") or service.get("leader", "-")

            table_html += f'''
                        <tr>
                            <td class="part-cell">{part_name}</td>
                            <td>{presider}</td>
                            <td>{scripture_reader}</td>
                            <td>{rep_prayer}</td>
                            <td>{offering_prayer}</td>
                            <td>{hymn}</td>
                            <td class="sermon-cell">{sermon}</td>
                        </tr>'''

        table_html += '''
                    </tbody>
                </table>
            </div>
        </div>'''

        return table_html

    def _build_service_detail_cards(self, services: List) -> str:
        """예배별 담당자 상세 카드 (사회, 성경봉독, 대표기도, 헌금기도, 찬송, 설교)"""
        if not services:
            return ""

        cards_html = '<div class="service-detail-cards">'

        for service in services:
            name = service.get("name", "예배")
            part_name = name.replace(" 예배", "").replace("예배", "").strip()

            presider = service.get("presider", "")
            scripture = service.get("scripture_reader", "") or service.get("scripture", "")
            rep_prayer = service.get("representative_prayer", "")
            offering_prayer = service.get("offering_prayer", "")
            hymn = service.get("hymn", "")
            sermon_title = service.get("sermon_title", "")
            preacher = service.get("leader", "") or service.get("preacher", "")

            # 담당자 정보가 하나라도 있으면 카드 생성
            has_info = any([presider, scripture, rep_prayer, offering_prayer, hymn, sermon_title])
            if not has_info:
                continue

            # 역할 정보 HTML 생성
            roles_html = ""
            if presider:
                roles_html += f'''
                <div class="role-item">
                    <span class="role-label">사회</span>
                    <span class="role-value">{presider}</span>
                </div>'''
            if scripture:
                roles_html += f'''
                <div class="role-item">
                    <span class="role-label">성경봉독</span>
                    <span class="role-value">{scripture}</span>
                </div>'''
            if rep_prayer:
                roles_html += f'''
                <div class="role-item">
                    <span class="role-label">대표기도</span>
                    <span class="role-value">{rep_prayer}</span>
                </div>'''
            if offering_prayer:
                roles_html += f'''
                <div class="role-item">
                    <span class="role-label">헌금기도</span>
                    <span class="role-value">{offering_prayer}</span>
                </div>'''
            if hymn:
                roles_html += f'''
                <div class="role-item">
                    <span class="role-label">찬송</span>
                    <span class="role-value hymn-badge">{hymn}</span>
                </div>'''

            # 설교 카드 (특별 스타일)
            sermon_card_html = ""
            if sermon_title or preacher:
                sermon_card_html = f'''
                <div class="sermon-info-card">
                    <div class="sermon-label">설교</div>
                    <div class="sermon-info-title">{sermon_title}</div>
                    <div class="sermon-info-preacher">{preacher}</div>
                </div>'''

            cards_html += f'''
            <div class="service-detail-card">
                <div class="service-card-header">
                    <span class="service-card-part">{part_name}</span>
                </div>
                <div class="service-card-body">
                    <div class="service-roles">
                        {roles_html}
                    </div>
                    {sermon_card_html}
                </div>
            </div>'''

        cards_html += '</div>'

        # 카드가 하나도 없으면 빈 문자열 반환
        if '<div class="service-detail-card">' not in cards_html:
            return ""

        return cards_html

    def _build_worship_section_with_tabs(self, info: Dict, services: List, section_class: str, section_title: str, worship_config: Dict) -> str:
        """회차별 탭이 있는 예배 섹션"""
        stand_indicator = worship_config.get("stand_indicator", "*")

        # 회차 탭 생성
        tabs_html = '<div class="service-tabs">'
        for idx, service in enumerate(services[:6]):
            name = service.get("name", "예배")
            time = service.get("time", "")
            # 부 번호와 시간 추출
            part_name = name.replace(" 예배", "").replace("예배", "").strip()
            time_short = time.replace("오전 ", "").replace("오후 ", "")

            active_class = "active" if idx == 0 else ""
            tabs_html += f'''
                <button class="service-tab {active_class}" onclick="switchServiceTab({idx + 1})">
                    <span class="tab-name">{part_name}</span>
                    <span class="tab-time">{time_short}</span>
                </button>'''
        tabs_html += '</div>'

        # 각 회차별 상세 정보 생성
        details_html = ''
        for idx, service in enumerate(services[:6]):
            name = service.get("name", "예배")
            time = service.get("time", "")
            leader = service.get("leader", "")
            prayer_person = service.get("prayer_person", "")
            hymns = service.get("hymns", [])
            items = service.get("items", [])

            display_style = "block" if idx == 0 else "none"
            part_name = name.replace(" 예배", "").replace("예배", "").strip()

            # 인도자 정보
            leader_html = f'''
                <div class="service-leader-info">
                    <div class="leader-item">
                        <span class="leader-label">인도</span>
                        <span class="leader-value">{leader}</span>
                    </div>
                    {f'<div class="leader-item"><span class="leader-label">기도</span><span class="leader-value">{prayer_person}</span></div>' if prayer_person else ''}
                </div>'''

            # 회차별 찬송가 (다를 경우)
            hymn_html = ''
            if hymns:
                hymn_html = '<div class="service-hymns">'
                for hymn in hymns[:3]:
                    hymn_num = hymn.get("number", "")
                    hymn_name = hymn.get("name", "")
                    hymn_html += f'''
                        <span class="hymn-badge" onclick="openHymnModal('{hymn_num}')">
                            🎵 {hymn_num}장 {hymn_name if hymn_name else ''}
                        </span>'''
                hymn_html += '</div>'

            # 예배 순서
            order_html = self._build_worship_order_html(items, worship_config)

            details_html += f'''
            <div class="service-detail" id="service-{idx + 1}" style="display: {display_style};">
                <div class="service-detail-header">
                    <span class="detail-part">{part_name}</span>
                    <span class="detail-time">{time}</span>
                </div>
                {leader_html}
                {hymn_html}
                {order_html}
            </div>'''

        return f'''
        <!-- 예배 안내 - 회차별 탭 형식 -->
        <section id="worship" class="section">
            <div class="section-header {section_class}">
                <span class="section-icon">⛪</span>
                <h2 class="section-title {section_class}">{section_title}</h2>
            </div>
            <div class="section-body">
                {tabs_html}
                <div class="service-details-container">
                    {details_html}
                </div>
            </div>
        </section>'''

    def _build_worship_order_html(self, items: List, worship_config: Dict = None) -> str:
        """예배 순서 HTML 생성 - 인터랙티브 요소 포함"""
        if not items:
            return ""

        stand_indicator = (worship_config or {}).get("stand_indicator", "*")

        worship_order_html = '<div class="worship-order">'
        for item in items:
            name = item.get("name", "")
            detail = item.get("detail", "")
            name_en = item.get("name_en", "")
            is_standing = item.get("standing", False) or name.startswith("*") or name.endswith("*")

            # 하이라이트 항목 (설교, 성찬식, 축도)
            highlight_class = "highlight" if name.replace("*", "").strip() in ["설교", "성찬식", "축도", "말씀"] else ""

            # 서는 순서 표시
            stand_class = "standing" if is_standing else ""
            clean_name = name.replace("*", "").strip()

            # 인터랙티브 요소 결정
            onclick = ""
            detail_html = detail
            interactive_class = ""

            # 찬송가 - 클릭 시 가사 팝업
            if "장" in detail and ("찬송" in clean_name or "송영" in clean_name or "찬양" in clean_name):
                # 찬송가 번호 추출
                hymn_num = ''.join(filter(str.isdigit, detail.split("장")[0]))
                if hymn_num:
                    onclick = f'onclick="openHymnModal(\'{hymn_num}\')"'
                    interactive_class = "clickable"
                    detail_html = f'<span class="worship-hymn">{detail}</span>'

            # 교독문 - 클릭 시 전문 표시
            elif "교독문" in clean_name or "교독" in clean_name:
                reading_num = ''.join(filter(str.isdigit, detail)) if detail else ""
                if reading_num:
                    onclick = f'onclick="openResponsiveReading(\'{reading_num}\')"'
                    interactive_class = "clickable"

            # 사도신경 - 클릭 시 전문 표시
            elif "사도신경" in clean_name:
                onclick = 'onclick="openCreed()"'
                interactive_class = "clickable"

            # 주기도문 - 클릭 시 전문 표시
            elif "주기도" in clean_name or "주기도문" in clean_name:
                onclick = 'onclick="openLordsPrayer()"'
                interactive_class = "clickable"

            # 성경봉독 - 클릭 시 성경구절 표시
            elif "성경" in clean_name or "봉독" in clean_name:
                if detail:
                    onclick = f'onclick="openBibleModal(\'sermon-verse\')"'
                    interactive_class = "clickable"

            worship_order_html += f'''
            <div class="worship-order-item {highlight_class} {stand_class} {interactive_class}" {onclick}>
                <span class="worship-name">
                    {f'<span class="stand-mark">{stand_indicator}</span>' if is_standing else ''}
                    {clean_name}
                </span>
                <span class="worship-detail">{detail_html}</span>
            </div>'''

        # 범례 추가
        worship_order_html += f'''
        <div class="worship-legend" style="margin-top: 12px; padding-top: 12px; border-top: 1px dashed var(--border); font-size: 0.75em; color: var(--text-secondary);">
            <span>{stand_indicator} 표시: 서서 드리는 순서</span>
            <span style="margin-left: 16px;">📖 클릭하면 상세 내용을 볼 수 있습니다</span>
        </div>'''

        worship_order_html += '</div>'
        return worship_order_html

    def _build_sermon_section(self, info: Dict, is_harvest: bool) -> str:
        """설교 말씀 섹션 - 아코디언 형식으로 전체 본문 표시"""
        sermon = info.get("sermon", {})
        title = sermon.get("title", "")
        title_en = sermon.get("title_en", "")
        scripture = sermon.get("scripture", "")
        preacher = sermon.get("preacher", "")
        sections = sermon.get("sections", [])

        # 설교 본문 생성 (아코디언 내부)
        content_html = ""
        if sections:
            for section in sections:
                section_title = section.get("title", "")
                section_title_en = section.get("title_en", "")
                section_content = section.get("content", "")
                if section_title:
                    title_html = f'<h4 class="sermon-section-title">{section_title}'
                    if section_title_en:
                        title_html += f' <span class="sermon-section-title-en">({section_title_en})</span>'
                    title_html += '</h4>'
                    content_html += title_html
                if section_content:
                    # 긴 내용을 문단으로 분리
                    paragraphs = section_content.split('\n') if '\n' in section_content else [section_content]
                    for p in paragraphs:
                        if p.strip():
                            content_html += f'<p class="sermon-paragraph">{p.strip()}</p>\n'
        else:
            content_html = "<p class='sermon-placeholder'>설교 내용은 예배 후 업데이트됩니다.</p>"

        section_class = "harvest" if is_harvest else ""
        audio_title = "추수감사절 설교 음성 듣기" if is_harvest else "설교 음성 듣기"

        return f'''
        <!-- 오늘의 말씀 -->
        <section id="sermon-detail" class="section">
            <div class="section-header {section_class}">
                <span class="section-icon">📖</span>
                <h2 class="section-title {section_class}">오늘의 말씀</h2>
            </div>
            <div class="section-body">
                <!-- 설교 제목 헤더 -->
                <div class="sermon-title-box">
                    <div class="sermon-main-title">{title}</div>
                    {f'<div class="sermon-title-en">{title_en}</div>' if title_en else ''}
                    {f'<div class="sermon-scripture"><a href="javascript:void(0)" onclick="openBibleModal(\'sermon-verse\')" class="bible-link">📖 {scripture}</a></div>' if scripture else ''}
                </div>

                <!-- 설교 본문 아코디언 -->
                <details class="sermon-accordion" open>
                    <summary class="sermon-accordion-header">
                        <span class="accordion-icon">📜</span>
                        <span class="accordion-title">본문 전체 보기</span>
                        <span class="accordion-arrow">▼</span>
                    </summary>
                    <div class="sermon-accordion-body">
                        <div class="sermon-content-full">
                            {content_html}
                        </div>
                        <div class="sermon-author-box">
                            <span class="author-label">설교</span>
                            <span class="author-name">{preacher}</span>
                        </div>
                    </div>
                </details>

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
        """금주의 찬양 섹션 - 원본 PDF 표 형식 유지 + 좌우 슬라이드"""
        choirs = info.get("choir", [])

        # 원본 PDF 테이블 데이터 (raw_choir_table)가 있으면 우선 사용
        raw_choir_table = info.get("raw_choir_table", None)

        # 데이터가 없으면 섹션 표시 안함 (가상 데이터 사용 안함)
        has_raw_table = raw_choir_table and isinstance(raw_choir_table, dict) and raw_choir_table.get("rows")
        if not choirs and not has_raw_table:
            return ""  # 찬양 데이터 없으면 섹션 표시 안함

        section_class = "harvest" if is_harvest else ""
        section_title = "추수감사절 찬양" if is_harvest else "금주의 찬양"

        # 원본 테이블 데이터가 있는 경우 (헤더 + 데이터 행) - 우선 사용
        if has_raw_table:
            headers = raw_choir_table.get("headers", [])
            rows = raw_choir_table.get("rows", [])

            # 헤더 생성
            header_html = ""
            for header in headers:
                header_html += f'<th>{header}</th>'

            # 데이터 행 생성
            table_rows = ""
            for row in rows:
                table_rows += "<tr>"
                for i, cell in enumerate(row):
                    # 첫 번째 열은 예배, 두 번째는 찬양대명 등 스타일 적용
                    if i == 0:
                        table_rows += f'<td class="choir-service-cell">{cell}</td>'
                    elif i == 1:
                        table_rows += f'<td class="choir-name-cell">{cell}</td>'
                    elif "곡" in headers[i] if i < len(headers) else False:
                        table_rows += f'<td class="choir-song-cell">{cell}</td>'
                    else:
                        table_rows += f'<td>{cell}</td>'
                table_rows += "</tr>"

            return f'''
        <!-- 금주의 찬양 -->
        <section id="choir" class="section">
            <div class="section-header {section_class}">
                <span class="section-icon">🎵</span>
                <h2 class="section-title {section_class}" data-i18n="section_choir">{section_title}</h2>
            </div>
            <div class="section-body">
                <div class="choir-scroll-hint">좌우로 스와이프하여 전체 내용 보기</div>
                <div class="choir-table-container">
                    <div class="choir-table-scroll">
                        <table class="choir-table">
                            <thead>
                                <tr>{header_html}</tr>
                            </thead>
                            <tbody>
                                {table_rows}
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>
        </section>'''

        # 기존 구조화된 데이터 사용
        table_rows = ""
        for choir in choirs:
            service = choir.get("service", "")
            name = choir.get("name", "")
            song = choir.get("song", "")
            conductor = choir.get("conductor", "")
            accompanist = choir.get("accompanist", "")

            table_rows += f'''
                        <tr>
                            <td class="choir-service-cell">{service}</td>
                            <td class="choir-name-cell">{name}</td>
                            <td class="choir-song-cell">{song}</td>
                            <td class="choir-conductor-cell">{conductor if conductor else "-"}</td>
                            <td class="choir-accompanist-cell">{accompanist if accompanist else "-"}</td>
                        </tr>'''

        return f'''
        <!-- 금주의 찬양 -->
        <section id="choir" class="section">
            <div class="section-header {section_class}">
                <span class="section-icon">🎵</span>
                <h2 class="section-title {section_class}" data-i18n="section_choir">{section_title}</h2>
            </div>
            <div class="section-body">
                <div class="choir-scroll-hint">좌우로 스와이프하여 전체 내용 보기</div>
                <div class="choir-table-container">
                    <div class="choir-table-scroll">
                        <table class="choir-table">
                            <thead>
                                <tr>
                                    <th>예배</th>
                                    <th>찬양대</th>
                                    <th>찬양곡</th>
                                    <th>지휘</th>
                                    <th>반주</th>
                                </tr>
                            </thead>
                            <tbody>
                                {table_rows}
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>
        </section>'''

    def _build_news_section(self, info: Dict, theme_name: str = "default") -> str:
        """교회 소식 섹션 - 카테고리별 아코디언 스타일 (제목 클릭 시 상세내용 펼침)"""
        news = info.get("news", {})

        # 딕셔너리 형식 (worship, recruit, info)
        if isinstance(news, dict):
            worship_items = news.get("worship", [])
            recruit_items = news.get("recruit", [])
            info_items = news.get("info", [])

            if not worship_items and not recruit_items and not info_items:
                return ""  # 소식이 없으면 섹션 표시 안함

            categories = [
                {"name": "예배", "icon": "⛪", "items": worship_items},
                {"name": "모집", "icon": "📝", "items": recruit_items},
                {"name": "안내", "icon": "📢", "items": info_items}
            ]
        else:
            # 리스트 형식 (이전 호환)
            if not news:
                return ""
            categories = [{"name": "안내", "icon": "📢", "items": news}]

        # 아코디언 HTML 생성
        accordion_html = '<div class="news-accordion">'
        accordion_idx = 0

        for cat in categories:
            if not cat["items"]:
                continue

            accordion_idx += 1
            items_html = ""

            for idx, item in enumerate(cat["items"], 1):
                # 새 형식: {"title": "...", "detail": "..."} 또는 이전 형식: 문자열
                if isinstance(item, dict):
                    title = item.get("title", "")
                    detail = item.get("detail", "") or item.get("content", "")
                else:
                    title = str(item)
                    detail = ""

                # 상세내용이 있으면 아코디언으로, 없으면 일반 항목으로
                if detail:
                    # 줄바꿈을 <br>로 변환
                    detail_html = detail.replace("\n", "<br>")
                    items_html += f'''
                    <details class="news-item-detail-accordion">
                        <summary class="news-item-summary">
                            <span class="news-num">{idx}</span>
                            <span class="news-item-title">{title}</span>
                            <span class="news-item-arrow">▼</span>
                        </summary>
                        <div class="news-item-detail-content">
                            {detail_html}
                        </div>
                    </details>'''
                else:
                    items_html += f'''
                    <div class="news-item-simple">
                        <span class="news-num">{idx}</span>
                        <span class="news-item-title">{title}</span>
                    </div>'''

            # 첫 번째 카테고리는 기본 열림
            is_open = "open" if accordion_idx == 1 else ""
            accordion_html += f'''
                <details class="news-category-accordion" {is_open}>
                    <summary class="news-category-header">
                        <span class="news-category-icon">{cat["icon"]}</span>
                        <span class="news-category-name">{cat["name"]}</span>
                        <span class="news-category-count">{len(cat["items"])}</span>
                        <span class="accordion-arrow">▼</span>
                    </summary>
                    <div class="news-category-body">
                        {items_html}
                    </div>
                </details>'''

        accordion_html += '</div>'

        section_class = "advent" if theme_name == "advent" else ""

        return f'''
        <!-- 교회 소식 -->
        <section id="news" class="section">
            <div class="section-header {section_class}">
                <span class="section-icon">📢</span>
                <h2 class="section-title {section_class}" data-i18n="section_news">교회 소식</h2>
            </div>
            <div class="section-body">
                {accordion_html}
            </div>
        </section>'''

    def _build_prayer_table_section(self, info: Dict, theme_name: str = "default") -> str:
        """다음 주간 대표기도 표 섹션 - 원본 PDF 테이블 형식 그대로 표시"""
        raw_prayer_table = info.get("raw_prayer_table", {})
        next_prayers = info.get("next_week_prayers", [])

        # 원본 테이블 데이터가 있는지 확인
        has_raw_table = raw_prayer_table and isinstance(raw_prayer_table, dict) and raw_prayer_table.get("rows")

        if not has_raw_table and not next_prayers:
            return ""  # 대표기도 데이터가 없으면 섹션 표시 안함

        section_class = "advent" if theme_name == "advent" else ""

        # 원본 테이블 형식 사용
        if has_raw_table:
            headers = raw_prayer_table.get("headers", [])
            rows = raw_prayer_table.get("rows", [])

            # 헤더 셀 생성
            header_html = ""
            if headers:
                header_html = "<tr>"
                for h in headers:
                    header_html += f'<th>{h}</th>'
                header_html += "</tr>"

            # 데이터 행 생성
            rows_html = ""
            for row in rows:
                rows_html += "<tr>"
                for idx, cell in enumerate(row):
                    # 첫 번째 셀(구분)은 강조
                    if idx == 0:
                        rows_html += f'<td class="prayer-category">{cell}</td>'
                    else:
                        rows_html += f'<td>{cell}</td>'
                rows_html += "</tr>"

            table_html = f'''
            <div class="prayer-table-wrapper">
                <div class="scroll-hint">← 좌우 스크롤 →</div>
                <div class="prayer-table-scroll">
                    <table class="prayer-table">
                        <thead>{header_html}</thead>
                        <tbody>{rows_html}</tbody>
                    </table>
                </div>
            </div>'''
        else:
            # 리스트 형식 (이전 호환)
            items_html = ""
            for item in next_prayers:
                if isinstance(item, dict):
                    date = item.get("date", "")
                    name = item.get("name", "")
                    items_html += f'<div class="prayer-item"><span class="prayer-date">{date}</span><span class="prayer-name">{name}</span></div>'
                else:
                    items_html += f'<div class="prayer-item">{item}</div>'

            table_html = f'<div class="prayer-list">{items_html}</div>'

        return f'''
        <!-- 다음 주간 대표기도 -->
        <section id="next-prayers" class="section">
            <div class="section-header {section_class}">
                <span class="section-icon">🙏</span>
                <h2 class="section-title {section_class}" data-i18n="section_next_prayers">다음 주간 대표기도</h2>
            </div>
            <div class="section-body">
                {table_html}
            </div>
        </section>'''

    def _build_sermon_card(self, info: Dict, theme_name: str = "default") -> str:
        """설교 카드 섹션 - 전문가 템플릿 스타일"""
        # 프리셋에서 '오늘의 말씀' 카드 표시 여부 확인 (기본값: True)
        if not self.preset.get("show_sermon_card", True):
            return ""  # 명성교회 등 해당 섹션이 없는 교회

        sermon = info.get("sermon", {})
        title = sermon.get("title", "")
        scripture = sermon.get("scripture", "")
        preacher = sermon.get("preacher", "")

        # 설교 제목이 없어도 성경 구절이나 설교자가 있으면 표시
        if not title and not scripture:
            return ""  # 모든 정보 없으면 표시 안함

        # 제목이 없으면 기본 텍스트 사용
        if not title:
            title = "주일 예배"

        return f'''
        <!-- 오늘 설교 -->
        <div class="sermon-card-box">
            <div class="sermon-card-label">오늘의 말씀</div>
            <div class="sermon-card-title">{title}</div>
            {f'<div class="sermon-card-scripture">📖 {scripture}</div>' if scripture else ''}
            {f'<div class="sermon-card-preacher">{preacher}</div>' if preacher else ''}
        </div>'''

    def _build_last_week_sermon(self, info: Dict) -> str:
        """지난주 말씀 섹션 - 아코디언 + 모달 형식 (명성교회 고도화)"""
        last_week = info.get("last_week_sermon", {})
        title = last_week.get("title", "")
        scripture = last_week.get("scripture", "")
        preacher = last_week.get("preacher", "")
        summary = last_week.get("summary", "")

        # 명성교회는 '지난주 말씀' 섹션 항상 표시
        show_sermon_card = self.preset.get("show_sermon_card", True)

        # 데이터가 없는 경우 처리
        if not title and not summary:
            # 명성교회가 아니면 섹션 생성 안함
            if show_sermon_card:
                return ""

            # 명성교회는 현재 설교 정보로 대체하거나 기본 텍스트 사용
            current_sermon = info.get("sermon", {})
            if current_sermon.get("title"):
                # 현재 주일 말씀 정보 사용 (지난주로 표시는 안 함)
                title = "지난 주일 말씀"
                scripture = current_sermon.get("scripture", "")
                preacher = current_sermon.get("preacher", "") or info.get("staff", {}).get("lead_pastor", "")
                if preacher and "목사" not in preacher:
                    preacher = preacher + " 목사"
                summary = "지난 주일 말씀의 은혜를 되새기며 한 주간을 시작합니다."
            else:
                # 기본 플레이스홀더
                title = "지난 주일 말씀"
                preacher = self.preset.get("staff_info", {}).get("lead_pastor", "")
                if preacher:
                    preacher = preacher + " 목사"
                summary = "지난 주일 말씀의 은혜를 되새기며 한 주간을 시작합니다."

        # 요약 텍스트 (미리보기용 - 처음 200자)
        preview_text = summary[:200] + "..." if len(summary) > 200 else summary

        # JavaScript용 문자열 이스케이프
        escaped_title = title.replace("'", "\\'").replace("\n", "\\n")
        escaped_scripture = scripture.replace("'", "\\'").replace("\n", "\\n")
        escaped_preacher = preacher.replace("'", "\\'").replace("\n", "\\n")
        escaped_summary = summary.replace("'", "\\'").replace("\n", "\\n")

        return f'''
        <!-- 지난주 말씀 - 아코디언 형식 -->
        <section id="last-sermon">
        <div class="last-week-accordion accordion" id="lastWeekAccordion">
            <div class="accordion-header" onclick="toggleAccordion('lastWeekAccordion')">
                <div class="accordion-title">
                    <span class="icon">📖</span>
                    <span>지난주 말씀</span>
                </div>
                <div style="display: flex; align-items: center; gap: 12px;">
                    {f'<span class="accordion-ref">{scripture}</span>' if scripture else ''}
                    <span class="accordion-arrow">▼</span>
                </div>
            </div>
            <div class="accordion-content">
                <div class="accordion-body">
                    {f'<div class="last-week-title" style="font-family: Noto Serif KR, serif; font-size: 1.2em; font-weight: 700; color: var(--primary); margin-bottom: 12px;">{title}</div>' if title else ''}
                    {f'<div class="last-week-ref" style="font-size: 0.85em; color: var(--accent); margin-bottom: 16px;">{scripture}{" | " + preacher if preacher else ""}</div>' if scripture or preacher else ''}
                    <div class="last-week-preview" style="font-size: 0.9em; color: var(--text-dark); line-height: 1.9; text-align: justify;">
                        {preview_text if preview_text else "말씀 내용이 준비 중입니다."}
                    </div>
                    {f'<button class="offering-btn" style="margin-top: 16px; font-size: 0.85em; padding: 10px 20px;" onclick="openLastWeekModal()">📖 전체 말씀 보기</button>' if len(summary) > 200 else ''}
                </div>
            </div>
        </div>
        <script>
            // 지난주 말씀 데이터 설정
            setLastWeekSermonData('{escaped_title}', '{escaped_scripture}', '{escaped_preacher}', '{escaped_summary}');
        </script>
        </section>'''

    def _build_member_news_section(self, info: Dict) -> str:
        """교우 소식 섹션 (출산, 소천, 결혼, 새가족, 축하) - 명성교회 고도화: 카테고리별 아코디언"""
        member_news = info.get("member_news", {})
        church_name = info.get("church_name", "")

        # 카테고리별 데이터
        categories = [
            {"key": "birth", "icon": "👶", "title": "출산", "data": member_news.get("birth", [])},
            {"key": "passing", "icon": "🕊️", "title": "소천", "data": member_news.get("passing", [])},
            {"key": "wedding", "icon": "💒", "title": "결혼", "data": member_news.get("wedding", [])},
            {"key": "celebration", "icon": "🎉", "title": "축하", "data": member_news.get("celebration", [])},
            {"key": "new_members", "icon": "🤝", "title": "새가족 등록", "data": member_news.get("new_members", [])},
            {"key": "baptism", "icon": "💧", "title": "세례", "data": member_news.get("baptism", [])},
        ]

        # 데이터가 있는 카테고리만 필터링
        active_categories = [cat for cat in categories if cat["data"]]

        if not active_categories:
            return ""  # 교우 소식 없으면 표시 안함

        # 명성교회: 아코디언 방식
        preset = self.CHURCH_PRESETS.get(church_name, {})
        use_accordion = preset.get("worship_config", {}).get("show_per_service_details", False)

        sections_html = ""
        for idx, cat in enumerate(active_categories):
            data = cat["data"]
            cat_id = f"memberNews-{cat['key']}"
            count = len(data) if isinstance(data, list) else 1

            if use_accordion:
                # 아코디언 방식 (명성교회)
                content_html = self._format_member_news_content(cat["key"], data)
                default_open = "open" if idx == 0 else ""  # 첫 번째 카테고리만 열기

                sections_html += f'''
                <div class="member-news-accordion accordion {default_open}" id="{cat_id}">
                    <div class="accordion-header" onclick="toggleMemberNewsCategory('{cat_id}')">
                        <div class="accordion-title">
                            <span class="icon">{cat["icon"]}</span>
                            <span>{cat["title"]}</span>
                            <span class="category-count">{count}명</span>
                        </div>
                        <span class="category-arrow">{"−" if idx == 0 else "+"}</span>
                    </div>
                    <div class="accordion-content">
                        <div class="accordion-body">
                            {content_html}
                        </div>
                    </div>
                </div>'''
            else:
                # 기본 방식
                content_html = self._format_member_news_content(cat["key"], data)
                sections_html += f'''
                <div class="member-news-section">
                    <div class="member-news-title">{cat["icon"]} {cat["title"]}</div>
                    {content_html}
                </div>'''

        return f'''
        <!-- 교우 소식 -->
        <section id="members" class="section">
            <div class="section-header">
                <span class="section-icon">👨‍👩‍👧‍👦</span>
                <h2 class="section-title">교우 소식</h2>
            </div>
            <div class="section-body">
                {sections_html}
            </div>
        </section>'''

    def _format_member_news_content(self, key: str, data: List) -> str:
        """교우 소식 내용 포맷팅"""
        if not data:
            return ""

        if key == "wedding":
            # 결혼 - 카드 형태
            if isinstance(data, list) and len(data) > 0:
                html = '<div class="wedding-grid">'
                for w in data[:6]:
                    if isinstance(w, dict):
                        html += f'''
                            <div class="wedding-card">
                                <div class="wedding-couple">💍 {w.get("couple", "")}</div>
                                <div class="wedding-info">{w.get("info", "")}</div>
                            </div>'''
                    else:
                        html += f'<div class="wedding-card">{w}</div>'
                html += '</div>'
                return html
            return f'<div class="member-news-list">{data}</div>'

        elif key == "passing":
            # 소천 - 정중한 형태
            if isinstance(data, list):
                items_html = ""
                for item in data:
                    if isinstance(item, dict):
                        name = item.get("name", "")
                        relation = item.get("relation", "")
                        date = item.get("date", "")
                        items_html += f'''
                            <div class="passing-item">
                                <span class="passing-name">{name}</span>
                                {f'<span class="passing-relation">({relation})</span>' if relation else ''}
                                {f'<span class="passing-date">{date}</span>' if date else ''}
                            </div>'''
                    else:
                        items_html += f'<div class="passing-item">{item}</div>'
                return f'<div class="passing-list">{items_html}</div>'
            return f'<div class="member-news-list">{data}</div>'

        elif key == "birth":
            # 출산 - 축하 형태
            if isinstance(data, list):
                items_html = ""
                for item in data:
                    if isinstance(item, dict):
                        parent = item.get("parent", "")
                        baby = item.get("baby", "")
                        date = item.get("date", "")
                        items_html += f'''
                            <div class="birth-item">
                                <span class="birth-parent">{parent}</span>
                                {f'<span class="birth-baby">👶 {baby}</span>' if baby else ''}
                                {f'<span class="birth-date">{date}</span>' if date else ''}
                            </div>'''
                    else:
                        items_html += f'<div class="birth-item">{item}</div>'
                return f'<div class="birth-list">{items_html}</div>'
            return f'<div class="member-news-list">{data}</div>'

        else:
            # 기타 - 리스트 형태
            if isinstance(data, list):
                return f'<div class="member-news-list">{", ".join(str(d) for d in data)}</div>'
            return f'<div class="member-news-list">{data}</div>'

    def _build_dawn_prayer_section(self, info: Dict) -> str:
        """새벽기도회 섹션 - 명성교회 고도화"""
        dawn_prayer = info.get("dawn_prayer", {})
        times = dawn_prayer.get("times", "")
        schedule = dawn_prayer.get("schedule", [])

        if not times and not schedule:
            return ""  # 새벽기도회 정보 없으면 표시 안함

        schedule_html = ""
        if schedule:
            # 새로운 형식 (day, date, speaker, scripture) 지원
            first_item = schedule[0] if schedule else {}
            if "day" in first_item or "speaker" in first_item:
                schedule_html = '''
                <div class="dawn-schedule">
                    <table class="dawn-table">
                        <thead><tr><th>요일</th><th>날짜</th><th>말씀</th><th>본문</th></tr></thead>
                        <tbody>'''
                for row in schedule:
                    day = row.get("day", "")
                    date = row.get("date", "")
                    speaker = row.get("speaker", "")
                    scripture = row.get("scripture", "")
                    schedule_html += f'''
                        <tr>
                            <td>{day}</td>
                            <td>{date}</td>
                            <td>{speaker}</td>
                            <td class="clickable" onclick="openBibleModal('{scripture}')" style="cursor:pointer;">{scripture}</td>
                        </tr>'''
                schedule_html += '</tbody></table></div>'
            else:
                # 레거시 형식 (columns, cells)
                schedule_html = '''
                <div class="dawn-schedule">
                    <table class="dawn-table">
                        <thead><tr><th>날짜</th>'''
                if schedule and len(schedule) > 0:
                    for col in first_item.get("columns", []):
                        schedule_html += f'<th>{col}</th>'
                schedule_html += '</tr></thead><tbody>'
                for row in schedule:
                    schedule_html += '<tr>'
                    for cell in row.get("cells", []):
                        schedule_html += f'<td>{cell}</td>'
                    schedule_html += '</tr>'
                schedule_html += '</tbody></table></div>'

        return f'''
        <!-- 새벽기도회 -->
        <section id="dawn" class="section">
            <div class="section-header">
                <span class="section-icon">🌅</span>
                <h2 class="section-title">새벽기도회</h2>
            </div>
            <div class="section-body">
                {f'<div style="margin-bottom: 12px; font-size: 0.85em; color: var(--text-gray);">{times}</div>' if times else ''}
                {schedule_html}
            </div>
        </section>'''

    def _build_weekly_service_section(self, info: Dict) -> str:
        """주중 예배 안내 섹션"""
        weekly_services = info.get("weekly_services", [])

        if not weekly_services:
            return ""  # 주중 예배 정보 없으면 표시 안함

        services_html = '<div style="display: grid; gap: 12px;">'
        for service in weekly_services[:4]:
            name = service.get("name", "")
            time = service.get("time", "")
            leader = service.get("leader", "")
            sermon_title = service.get("sermon_title", "")
            scripture = service.get("scripture", "")

            services_html += f'''
                <div style="background: var(--bg-gray); border-radius: 10px; padding: 14px;">
                    <div style="font-weight: 700; color: var(--primary); margin-bottom: 6px;">{name}</div>
                    <div style="font-size: 0.85em; color: var(--text-gray);">
                        {time}{f' | 인도: {leader}' if leader else ''}<br>
                        {f'설교: "{sermon_title}"<br>' if sermon_title else ''}
                        {f'본문: {scripture}' if scripture else ''}
                    </div>
                </div>'''
        services_html += '</div>'

        return f'''
        <!-- 주중 예배 안내 -->
        <section class="section">
            <div class="section-header">
                <span class="section-icon">🙏</span>
                <h2 class="section-title">주중 예배 안내</h2>
            </div>
            <div class="section-body">
                {services_html}
            </div>
        </section>'''

    def _build_staff_section(self, info: Dict, theme_name: str = "default") -> str:
        """목회자 안내 섹션 - 프리셋 데이터 우선 사용"""
        # self.preset 사용 (이미 __init__에서 설정됨)
        preset_staff = self.preset.get("staff_info", {})
        staff = info.get("staff", {})

        # 프리셋 데이터 우선 사용 (프리셋에 값이 있으면 무조건 사용)
        senior_pastor = preset_staff.get("senior_pastor") or staff.get("senior_pastor", "")
        lead_pastor = preset_staff.get("lead_pastor") or staff.get("lead_pastor", "")
        senior_title = preset_staff.get("senior_pastor_title", "원로목사")
        lead_title = preset_staff.get("lead_pastor_title", "담임목사")
        associate_pastors = staff.get("associate_pastors", [])
        education_pastors = staff.get("education_pastors", [])

        if not senior_pastor and not lead_pastor:
            return ""  # 목회자 정보 없으면 표시 안함

        theme_class = "advent" if theme_name == "advent" else "primary"

        return f'''
        <!-- 목회자 안내 -->
        <section class="section">
            <div class="section-header">
                <span class="section-icon">🙏</span>
                <h2 class="section-title">목회자 안내</h2>
            </div>
            <div class="section-body" style="font-size: 0.85em; line-height: 1.8;">
                <div style="margin-bottom: 12px;">
                    {f'<strong style="color: var(--{theme_class});">{senior_title}</strong> {senior_pastor}' if senior_pastor else ''}
                    {' · ' if senior_pastor and lead_pastor else ''}
                    {f'<strong style="color: var(--{theme_class});">{lead_title}</strong> {lead_pastor}' if lead_pastor else ''}
                </div>
                {f'<div style="color: var(--text-gray);"><strong>협동목사</strong> {" ".join(associate_pastors)}</div>' if associate_pastors else ''}
                {f'<div style="color: var(--text-gray);"><strong>교육목사</strong> {" ".join(education_pastors)}</div>' if education_pastors else ''}
            </div>
        </section>'''

    def _build_devotional_section(self, info: Dict) -> str:
        """오늘의 양식 섹션 - 아코디언 스타일"""
        devotional = info.get("devotional", {})
        title = devotional.get("title", "")
        content = devotional.get("content", "")

        if not content and not title:
            return ""  # 양식 정보 없으면 표시 안함

        # 내용을 문단으로 분리
        content_paragraphs = ""
        if content:
            paragraphs = content.split('\n\n') if '\n\n' in content else content.split('\n')
            for p in paragraphs:
                if p.strip():
                    content_paragraphs += f'<p>{p.strip()}</p>'
        else:
            content_paragraphs = "<p>오늘의 양식 내용이 업데이트됩니다.</p>"

        return f'''
        <!-- 오늘의 양식 -->
        <section id="devotional" class="section">
            <div class="section-header">
                <span class="section-icon">🌿</span>
                <h2 class="section-title">오늘의 양식</h2>
            </div>
            <div class="section-body">
                <details class="devotional-accordion" open>
                    <summary class="devotional-header">
                        <span class="devotional-icon">📖</span>
                        <span class="devotional-title">{title if title else "묵상의 글"}</span>
                        <span class="devotional-arrow">▼</span>
                    </summary>
                    <div class="devotional-body">
                        <div class="devotional-content">
                            {content_paragraphs}
                        </div>
                    </div>
                </details>
            </div>
        </section>'''

    def _build_contact_section(self, info: Dict) -> str:
        """교회 연락처 섹션 - 전문가 템플릿 스타일"""
        contact = info.get("contact", {})
        address = contact.get("address", "") or self.church_info.get("address", "")
        phone = contact.get("phone", "") or self.church_info.get("phone_day", "")
        fax = contact.get("fax", "")
        website = contact.get("website", "") or self.church_info.get("website", "")

        if not address and not phone:
            return ""  # 연락처 정보 없으면 표시 안함

        contact_items = []

        if address:
            contact_items.append(f'''
                    <div class="contact-item">
                        <span class="contact-icon">📍</span>
                        <div class="contact-info">
                            <div class="contact-label">주소</div>
                            <div class="contact-value">{address}</div>
                        </div>
                    </div>''')

        if phone:
            contact_items.append(f'''
                    <div class="contact-item">
                        <span class="contact-icon">📞</span>
                        <div class="contact-info">
                            <div class="contact-label">대표전화</div>
                            <div class="contact-value"><a href="tel:{phone}">{phone}</a></div>
                        </div>
                    </div>''')

        if fax:
            contact_items.append(f'''
                    <div class="contact-item">
                        <span class="contact-icon">📠</span>
                        <div class="contact-info">
                            <div class="contact-label">FAX</div>
                            <div class="contact-value">{fax}</div>
                        </div>
                    </div>''')

        if website:
            website_display = website.replace("https://", "").replace("http://", "")
            contact_items.append(f'''
                    <div class="contact-item">
                        <span class="contact-icon">🌐</span>
                        <div class="contact-info">
                            <div class="contact-label">홈페이지</div>
                            <div class="contact-value"><a href="{website}" target="_blank">{website_display}</a></div>
                        </div>
                    </div>''')

        return f'''
        <!-- 연락처 -->
        <section id="contact" class="section">
            <div class="section-header">
                <span class="section-icon">📞</span>
                <h2 class="section-title">교회 안내</h2>
            </div>
            <div class="section-body">
                <div class="contact-grid">
                    {"".join(contact_items)}
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

    def _build_share_section(self, is_harvest: bool, theme_name: str = "default") -> str:
        """공유 섹션 - 전문가 템플릿 스타일"""
        THEME_ICONS = {
            "advent": "🕯️ 대림절",
            "christmas": "🎄 성탄절",
            "lent": "✝️ 사순절",
            "easter": "🌸 부활절",
            "pentecost": "🔥 성령강림절",
            "harvest": "🌾 추수감사절"
        }

        theme_text = THEME_ICONS.get(theme_name, "")
        if theme_text:
            share_title = f"{theme_text} 주보를 공유해 보세요"
        else:
            share_title = "주보를 공유해 보세요"

        return f'''
        <!-- 공유 섹션 -->
        <div class="share-section">
            <div class="share-title">{share_title}</div>
            <div class="share-buttons">
                <button class="share-btn kakao" onclick="shareKakao()">카카오톡</button>
                <button class="share-btn" onclick="shareLink()">링크 복사</button>
            </div>
        </div>'''

    def _build_sns_offering_section(self) -> str:
        """SNS 링크 및 모바일 헌금 안내 섹션 - 전문가 수준 (fg-2025-12-14 기준)"""
        sns = self.preset.get("sns", {})
        church_name = self.church_info.get("name", "교회")
        website = self.preset.get("website", "") or "https://www.fgtv.com"

        # SNS 섹션 - 전문가 결과물과 동일한 구조 (.sns-grid + .sns-item)
        sns_html = f'''
        <!-- SNS 링크 -->
        <section id="sns" class="section">
            <div class="section-header">
                <span class="section-icon">📱</span>
                <h2 class="section-title" data-i18n="section_sns">SNS 채널</h2>
            </div>
            <div class="section-body">
                <div class="sns-grid">
                    <a href="{sns.get('youtube', 'https://www.youtube.com/@fgtv')}" target="_blank" class="sns-item youtube">
                        <span class="sns-icon">▶️</span>
                        <span class="sns-name">YouTube</span>
                    </a>
                    <a href="{sns.get('instagram', 'https://www.instagram.com/yfgc_official')}" target="_blank" class="sns-item instagram">
                        <span class="sns-icon">📷</span>
                        <span class="sns-name">Instagram</span>
                    </a>
                    <a href="{sns.get('facebook', 'https://www.facebook.com/fgtv')}" target="_blank" class="sns-item facebook">
                        <span class="sns-icon">👍</span>
                        <span class="sns-name">Facebook</span>
                    </a>
                    <a href="{website}" target="_blank" class="sns-item website">
                        <span class="sns-icon">🌐</span>
                        <span class="sns-name">홈페이지</span>
                    </a>
                </div>
            </div>
        </section>

        <!-- 모바일 헌금 -->
        <section id="offering" class="section">
            <div class="section-header">
                <span class="section-icon">💝</span>
                <h2 class="section-title" data-i18n="section_offering">모바일 헌금</h2>
            </div>
            <div class="section-body">
                <div class="offering-grid">
                    <div class="offering-item" onclick="openOfferingModal('bank')">
                        <span class="offering-icon">🏦</span>
                        <div class="offering-info">
                            <div class="offering-name">계좌이체 헌금</div>
                            <div class="offering-desc">은행 계좌로 헌금하기</div>
                        </div>
                        <span class="offering-arrow">→</span>
                    </div>
                    <div class="offering-item" onclick="openOfferingModal('kakaopay')">
                        <span class="offering-icon">💛</span>
                        <div class="offering-info">
                            <div class="offering-name">카카오페이 헌금</div>
                            <div class="offering-desc">간편하게 헌금하기</div>
                        </div>
                        <span class="offering-arrow">→</span>
                    </div>
                    <div class="offering-item" onclick="openOfferingModal('app')">
                        <span class="offering-icon">📲</span>
                        <div class="offering-info">
                            <div class="offering-name">교회 앱 헌금</div>
                            <div class="offering-desc">{church_name} 앱으로 헌금</div>
                        </div>
                        <span class="offering-arrow">→</span>
                    </div>
                </div>
            </div>
        </section>'''

        return sns_html

    def _build_footer(self, info: Dict, is_harvest: bool) -> str:
        """푸터 섹션"""
        logo = "🌾 " + info["church_name"] if is_harvest else info["church_name"]
        # 프리셋에서 주소, 창립일 가져오기 (없으면 church_info에서)
        address = self.preset.get("address", "") or self.church_info.get("address", "")
        founded = self.preset.get("founded", "") or self.church_info.get("founded", "")
        return f'''
    <!-- 푸터 -->
    <footer class="footer">
        <div class="footer-logo">{logo}</div>
        <div class="footer-address">
            {address}<br>
            {founded}
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
    </div>

    <!-- 지난주 말씀 전체 보기 모달 -->
    <div class="modal-overlay" id="lastWeekModal">
        <div class="modal-content" style="max-height: 85vh;">
            <div class="modal-header">
                <span class="modal-title" id="lastWeekModalTitle">📖 지난주 말씀</span>
                <button class="modal-close" onclick="closeModal('lastWeekModal')">✕</button>
            </div>
            <div class="modal-body" style="max-height: calc(85vh - 60px); overflow-y: auto;">
                <div class="last-week-modal-content" id="lastWeekModalContent">
                    <div class="sermon-title" style="font-family: 'Noto Serif KR', serif; font-size: 1.3em; font-weight: 700; color: var(--primary); margin-bottom: 8px;"></div>
                    <div class="sermon-ref" style="font-size: 0.9em; color: var(--accent); margin-bottom: 20px; padding-bottom: 16px; border-bottom: 1px solid var(--border);"></div>
                    <div class="sermon-text" style="font-size: 1em; color: var(--text-dark); line-height: 2; text-align: justify; white-space: pre-line;"></div>
                </div>
            </div>
        </div>
    </div>

    <!-- 교독문 모달 -->
    <div class="modal-overlay" id="responsiveReadingModal">
        <div class="modal-content" style="max-height: 80vh;">
            <div class="modal-header">
                <span class="modal-title" id="responsiveReadingTitle">📜 교독문</span>
                <button class="modal-close" onclick="closeModal('responsiveReadingModal')">✕</button>
            </div>
            <div class="modal-body" style="max-height: calc(80vh - 60px); overflow-y: auto;">
                <div id="responsiveReadingContent" style="line-height: 2;"></div>
            </div>
        </div>
    </div>

    <!-- 사도신경 모달 -->
    <div class="modal-overlay" id="creedModal">
        <div class="modal-content">
            <div class="modal-header">
                <span class="modal-title">✝️ 사도신경</span>
                <button class="modal-close" onclick="closeModal('creedModal')">✕</button>
            </div>
            <div class="modal-body" style="max-height: calc(80vh - 60px); overflow-y: auto;">
                <div style="font-size: 1.05em; line-height: 2.2; text-align: justify;">
                    <p style="margin-bottom: 16px;">전능하사 천지를 만드신 하나님 아버지를 내가 믿사오며,</p>
                    <p style="margin-bottom: 16px;">그 외아들 우리 주 예수 그리스도를 믿사오니, 이는 성령으로 잉태하사 동정녀 마리아에게 나시고,</p>
                    <p style="margin-bottom: 16px;">본디오 빌라도에게 고난을 받으사 십자가에 못 박혀 죽으시고, 장사한 지 사흘 만에 죽은 자 가운데서 다시 살아나시며,</p>
                    <p style="margin-bottom: 16px;">하늘에 오르사 전능하신 하나님 우편에 앉아 계시다가, 저리로서 산 자와 죽은 자를 심판하러 오시리라.</p>
                    <p style="margin-bottom: 16px;">성령을 믿사오며, 거룩한 공회와 성도가 서로 교통하는 것과,</p>
                    <p style="margin-bottom: 16px;">죄를 사하여 주시는 것과, 몸이 다시 사는 것과, 영원히 사는 것을 믿사옵나이다.</p>
                    <p style="font-weight: 700; color: var(--primary); text-align: center; margin-top: 20px;">아멘.</p>
                </div>
            </div>
        </div>
    </div>

    <!-- 주기도문 모달 -->
    <div class="modal-overlay" id="lordsPrayerModal">
        <div class="modal-content">
            <div class="modal-header">
                <span class="modal-title">🙏 주기도문</span>
                <button class="modal-close" onclick="closeModal('lordsPrayerModal')">✕</button>
            </div>
            <div class="modal-body" style="max-height: calc(80vh - 60px); overflow-y: auto;">
                <div style="font-size: 1.05em; line-height: 2.2; text-align: justify;">
                    <p style="margin-bottom: 16px;">하늘에 계신 우리 아버지여,</p>
                    <p style="margin-bottom: 16px;">이름이 거룩히 여김을 받으시오며, 나라이 임하옵시며, 뜻이 하늘에서 이룬 것같이 땅에서도 이루어지이다.</p>
                    <p style="margin-bottom: 16px;">오늘날 우리에게 일용할 양식을 주옵시고, 우리가 우리에게 죄 지은 자를 사하여 준 것같이 우리 죄를 사하여 주옵시고,</p>
                    <p style="margin-bottom: 16px;">우리를 시험에 들게 하지 마옵시고, 다만 악에서 구하옵소서.</p>
                    <p style="margin-bottom: 16px;">대개 나라와 권세와 영광이 아버지께 영원히 있사옵나이다.</p>
                    <p style="font-weight: 700; color: var(--primary); text-align: center; margin-top: 20px;">아멘.</p>
                </div>
            </div>
        </div>
    </div>

    <!-- 헌금 모달 (전문가 수준) -->
    <div class="modal-overlay" id="offeringModal">
        <div class="modal-content">
            <div class="modal-header offering">
                <span class="modal-title" id="offeringModalTitle">💝 헌금 안내</span>
                <button class="modal-close" onclick="closeOfferingModal(event)">✕</button>
            </div>
            <div class="modal-body" id="offeringModalBody">
            </div>
        </div>
    </div>'''

    def _get_javascript(self, info: Dict) -> str:
        """JavaScript 코드 - 전문가 수준 8개국어 지원"""
        church_name = info.get("church_name", "교회")
        date = info.get("date", "")
        verse_text = info.get("verse", {}).get("text", "")
        verse_ref = info.get("verse", {}).get("reference", "")
        sermon = info.get("sermon", {})
        devotional = info.get("devotional", {})

        # AI 번역 데이터 가져오기
        ai_translations = info.get("translations", {})

        # 동적 번역 데이터 생성 (각 언어별) - 전문가 수준 확장
        def get_dynamic_trans(lang):
            trans = ai_translations.get(lang, {})
            entries = []
            if trans.get("verse_text"):
                entries.append(f'verse_text: `{trans["verse_text"].replace("`", "\\`")}`')
            if trans.get("sermon_title"):
                entries.append(f'sermon_title: `{trans["sermon_title"].replace("`", "\\`")}`')
            if trans.get("sermon_intro"):
                entries.append(f'sermon_intro: `{trans["sermon_intro"].replace("`", "\\`")}`')
            if trans.get("devotional_title"):
                entries.append(f'devotional_title: `{trans["devotional_title"].replace("`", "\\`")}`')
            if trans.get("devotional_content"):
                # 긴 콘텐츠는 줄바꿈 처리
                content = trans["devotional_content"].replace("`", "\\`").replace("\n", "\\n")
                entries.append(f'devotional_content: `{content}`')
            # 설교 포인트
            for i in range(1, 6):
                if trans.get(f"sermon_point{i}_title"):
                    entries.append(f'sermon_point{i}_title: `{trans[f"sermon_point{i}_title"].replace("`", "\\`")}`')
                if trans.get(f"sermon_point{i}_content"):
                    entries.append(f'sermon_point{i}_content: `{trans[f"sermon_point{i}_content"].replace("`", "\\`")}`')
            return ", ".join(entries)

        ko_dynamic = get_dynamic_trans("ko")
        en_dynamic = get_dynamic_trans("en")
        zh_dynamic = get_dynamic_trans("zh")
        ja_dynamic = get_dynamic_trans("ja")
        id_dynamic = get_dynamic_trans("id")
        es_dynamic = get_dynamic_trans("es")
        ru_dynamic = get_dynamic_trans("ru")
        fr_dynamic = get_dynamic_trans("fr")

        # 한국어 기본값 (AI 번역 없는 경우)
        ko_verse_text = verse_text.replace('"', '\\"').replace("'", "\\'") if verse_text else ""

        return f'''
    <script>
        // ========== 다국어 번역 시스템 ==========
        const translations = {{
            ko: {{
                nav_sermon: "말씀",
                nav_worship: "예배",
                nav_news: "소식",
                nav_members: "교우",
                nav_dawn: "새벽",
                nav_last_sermon: "지난주 말씀",
                nav_contact: "안내",
                section_verse: "오늘의 말씀",
                section_worship: "예배 안내",
                section_news: "교회 소식",
                section_members: "교우 소식",
                section_dawn: "새벽기도",
                section_contact: "교회 안내",
                btn_share: "공유하기",
                btn_copy: "복사",
                btn_offering: "헌금",
                verse_text: `{ko_verse_text}`{', ' + ko_dynamic if ko_dynamic else ''}
            }},
            en: {{
                nav_sermon: "Sermon",
                nav_worship: "Worship",
                nav_news: "News",
                nav_members: "Members",
                nav_dawn: "Dawn",
                nav_last_sermon: "Last Week",
                nav_contact: "Contact",
                section_verse: "Today's Word",
                section_worship: "Worship Service",
                section_news: "Church News",
                section_members: "Member News",
                section_dawn: "Dawn Prayer",
                section_contact: "Church Info",
                btn_share: "Share",
                btn_copy: "Copy",
                btn_offering: "Offering"{', ' + en_dynamic if en_dynamic else ''}
            }},
            zh: {{
                nav_sermon: "讲道",
                nav_worship: "礼拜",
                nav_news: "消息",
                nav_members: "教友",
                nav_dawn: "晨祷",
                nav_last_sermon: "上周讲道",
                nav_contact: "联系",
                section_verse: "今日经文",
                section_worship: "礼拜指南",
                section_news: "教会新闻",
                section_members: "教友消息",
                section_dawn: "晨祷会",
                section_contact: "教会信息",
                btn_share: "分享",
                btn_copy: "复制",
                btn_offering: "奉献"{', ' + zh_dynamic if zh_dynamic else ''}
            }},
            ja: {{
                nav_sermon: "説教",
                nav_worship: "礼拝",
                nav_news: "お知らせ",
                nav_members: "教友",
                nav_dawn: "早朝",
                nav_last_sermon: "先週の説教",
                nav_contact: "案内",
                section_verse: "今日のみことば",
                section_worship: "礼拝案内",
                section_news: "教会ニュース",
                section_members: "教友便り",
                section_dawn: "早朝祈祷",
                section_contact: "教会案内",
                btn_share: "共有",
                btn_copy: "コピー",
                btn_offering: "献金"{', ' + ja_dynamic if ja_dynamic else ''}
            }},
            id: {{
                nav_sermon: "Khotbah",
                nav_worship: "Ibadah",
                nav_news: "Berita",
                nav_members: "Jemaat",
                nav_dawn: "Fajar",
                nav_last_sermon: "Minggu Lalu",
                nav_contact: "Kontak",
                section_verse: "Firman Hari Ini",
                section_worship: "Jadwal Ibadah",
                section_news: "Berita Gereja",
                section_members: "Berita Jemaat",
                section_dawn: "Doa Fajar",
                section_contact: "Info Gereja",
                btn_share: "Bagikan",
                btn_copy: "Salin",
                btn_offering: "Persembahan"{', ' + id_dynamic if id_dynamic else ''}
            }},
            es: {{
                nav_sermon: "Sermón",
                nav_worship: "Culto",
                nav_news: "Noticias",
                nav_members: "Miembros",
                nav_dawn: "Amanecer",
                nav_last_sermon: "Semana Pasada",
                nav_contact: "Contacto",
                section_verse: "Palabra de Hoy",
                section_worship: "Horario de Culto",
                section_news: "Noticias de la Iglesia",
                section_members: "Noticias de Miembros",
                section_dawn: "Oración Matutina",
                section_contact: "Info de la Iglesia",
                btn_share: "Compartir",
                btn_copy: "Copiar",
                btn_offering: "Ofrenda"{', ' + es_dynamic if es_dynamic else ''}
            }},
            ru: {{
                nav_sermon: "Проповедь",
                nav_worship: "Богослужение",
                nav_news: "Новости",
                nav_members: "Члены",
                nav_dawn: "Утро",
                nav_last_sermon: "Прошлая неделя",
                nav_contact: "Контакты",
                section_verse: "Слово на сегодня",
                section_worship: "Расписание служений",
                section_news: "Новости церкви",
                section_members: "Новости членов",
                section_dawn: "Утренняя молитва",
                section_contact: "Информация о церкви",
                btn_share: "Поделиться",
                btn_copy: "Копировать",
                btn_offering: "Пожертвование"{', ' + ru_dynamic if ru_dynamic else ''}
            }},
            fr: {{
                nav_sermon: "Sermon",
                nav_worship: "Culte",
                nav_news: "Actualités",
                nav_members: "Membres",
                nav_dawn: "Aube",
                nav_last_sermon: "Semaine Dernière",
                nav_contact: "Contact",
                section_verse: "Parole du Jour",
                section_worship: "Horaires des Cultes",
                section_news: "Nouvelles de l'Église",
                section_members: "Nouvelles des Membres",
                section_dawn: "Prière Matinale",
                section_contact: "Infos de l'Église",
                btn_share: "Partager",
                btn_copy: "Copier",
                btn_offering: "Offrande"{', ' + fr_dynamic if fr_dynamic else ''}
            }}
        }};

        let currentLanguage = 'ko';

        function changeLanguage(lang) {{
            currentLanguage = lang;
            document.querySelectorAll('[data-i18n]').forEach(el => {{
                const key = el.getAttribute('data-i18n');
                // 선택한 언어 -> 영어 -> 한국어 순으로 폴백
                const text = (translations[lang] && translations[lang][key])
                    || (translations['en'] && translations['en'][key])
                    || (translations['ko'] && translations['ko'][key])
                    || el.textContent;
                el.textContent = text;
            }});
            localStorage.setItem('church_bulletin_lang', lang);
        }}

        // 페이지 로드 시 저장된 언어 복원
        document.addEventListener('DOMContentLoaded', function() {{
            const savedLang = localStorage.getItem('church_bulletin_lang');
            if (savedLang && translations[savedLang]) {{
                document.querySelector('.language-selector').value = savedLang;
                changeLanguage(savedLang);
            }}
        }});

        // ========== 성경 구절 데이터 (다국어 - 전문가 수준) ==========
        const bibleVerses = {{
            'main-verse': {{
                ko: {{ title: '{verse_ref}', content: `{verse_text.replace('"', '\\"').replace("'", "\\'")}` }},
                en: {{ title: '{self._get_english_bible_ref(verse_ref)}', content: `{self._translate_verse_to_english(verse_text)}` }},
                zh: {{ title: '{self._get_chinese_bible_ref(verse_ref)}', content: '' }},
                ja: {{ title: '{self._get_japanese_bible_ref(verse_ref)}', content: '' }},
                id: {{ title: '{self._get_indonesian_bible_ref(verse_ref)}', content: '' }},
                es: {{ title: '{self._get_spanish_bible_ref(verse_ref)}', content: '' }},
                ru: {{ title: '{self._get_russian_bible_ref(verse_ref)}', content: '' }},
                fr: {{ title: '{self._get_french_bible_ref(verse_ref)}', content: '' }}
            }},
            // 누가복음 3:4-6 (대림절/강림절 핵심 말씀)
            'luke-3-4': {{
                ko: {{ title: '누가복음 3:4~6', content: '선지자 이사야의 책에 쓴 바 광야에서 외치는 자의 소리가 있어 이르되 너희는 주의 길을 준비하라 그의 오실 길을 곧게 하라 모든 골짜기가 메워지고 모든 산과 작은 산이 낮아지고 굽은 것이 곧아지고 험한 길이 평탄하여질 것이요 모든 육체가 하나님의 구원하심을 보리라 하였느니라' }},
                en: {{ title: 'Luke 3:4-6', content: 'As it is written in the book of the words of Isaiah the prophet: "A voice of one calling in the wilderness, Prepare the way for the Lord, make straight paths for him. Every valley shall be filled in, every mountain and hill made low. The crooked roads shall become straight, the rough ways smooth. And all people will see God\\'s salvation."' }},
                zh: {{ title: '路加福音 3:4-6', content: '正如先知以赛亚书上所记的话，说：在旷野有人声喊着说：预备主的道，修直他的路！一切山洼都要填满；大小山冈都要削平！弯弯曲曲的地方要改为正直；高高低低的道路要改为平坦！凡有血气的，都要见神的救恩！' }},
                ja: {{ title: 'ルカ 3:4-6', content: '預言者イザヤの書に書いてあるとおりである。「荒野で叫ぶ者の声がする。『主の道を用意し、その道筋をまっすぐにせよ。すべての谷は埋められ、すべての山と丘は低くされる。曲がった道はまっすぐになり、でこぼこ道は平らになる。こうして、すべての肉なる者が神の救いを見る。』」' }},
                id: {{ title: 'Lukas 3:4-6', content: 'seperti ada tertulis dalam kitab nubuat-nubuat Yesaya: Ada suara yang berseru-seru di padang gurun: Persiapkanlah jalan untuk Tuhan, luruskanlah jalan bagi-Nya. Setiap lembah akan ditimbun dan setiap gunung dan bukit akan menjadi rata, yang berliku-liku akan diluruskan, yang berlekak-lekuk akan diratakan, dan semua orang akan melihat keselamatan yang dari Allah.' }},
                es: {{ title: 'Lucas 3:4-6', content: 'como está escrito en el libro de las palabras del profeta Isaías: Voz del que clama en el desierto: Preparad el camino del Señor, enderezad sus sendas. Todo valle será rellenado, y todo monte y collado será bajado; los caminos torcidos serán enderezados, y los caminos ásperos allanados; y verá toda carne la salvación de Dios.' }},
                ru: {{ title: 'Луки 3:4-6', content: 'как написано в книге слов пророка Исаии: глас вопиющего в пустыне: приготовьте путь Господу, прямыми сделайте стези Ему; всякий дол да наполнится, и всякая гора и холм да понизятся, кривизны выпрямятся и неровные пути сделаются гладкими; и узрит всякая плоть спасение Божие.' }},
                fr: {{ title: 'Luc 3:4-6', content: 'selon ce qui est écrit dans le livre des paroles du prophète Ésaïe: C\\'est la voix de celui qui crie dans le désert: Préparez le chemin du Seigneur, Aplanissez ses sentiers. Toute vallée sera comblée, Toute montagne et toute colline seront abaissées; Ce qui est tortueux sera redressé, Et les chemins raboteux seront aplanis. Et toute chair verra le salut de Dieu.' }}
            }},
            // 빌립보서 1:3-8 (감사)
            'phil-1-3': {{
                ko: {{ title: '빌립보서 1:3~8', content: '내가 너희를 생각할 때마다 나의 하나님께 감사하며 간구할 때마다 너희 모든 사람을 위하여 기쁨으로 항상 간구함은 첫날부터 이제까지 복음을 위한 너희의 교제로 말미암음이라 너희 안에서 착한 일을 시작하신 이가 그리스도 예수의 날까지 이루실 줄을 우리는 확신하노라' }},
                en: {{ title: 'Philippians 1:3-8', content: 'I thank my God every time I remember you. In all my prayers for all of you, I always pray with joy because of your partnership in the gospel from the first day until now, being confident of this, that he who began a good work in you will carry it on to completion until the day of Christ Jesus.' }},
                zh: {{ title: '腓立比书 1:3-8', content: '我每逢想念你们，就感谢我的神；每逢为你们众人祈求的时候，常是欢欢喜喜地祈求。因为从头一天直到如今，你们是同心合意地兴旺福音。我深信那在你们心里动了善工的，必成全这工，直到耶稣基督的日子。' }},
                ja: {{ title: 'ピリピ 1:3-8', content: '私は、あなたがたのことを思うごとに私の神に感謝しています。あなたがたすべてのために祈るごとに、いつも喜びをもって祈り、最初の日から今日まで、福音を広めることにあなたがたが参加してきたことを感謝しています。' }},
                id: {{ title: 'Filipi 1:3-8', content: 'Aku mengucap syukur kepada Allahku setiap kali aku mengingat kamu. Dan setiap kali aku berdoa untuk kamu semua, aku selalu berdoa dengan sukacita.' }},
                es: {{ title: 'Filipenses 1:3-8', content: 'Doy gracias a mi Dios siempre que me acuerdo de vosotros, siempre en todas mis oraciones rogando con gozo por todos vosotros.' }},
                ru: {{ title: 'Филиппийцам 1:3-8', content: 'Благодарю Бога моего при всяком воспоминании о вас, всегда во всякой молитве моей за всех вас принося с радостью молитву мою.' }},
                fr: {{ title: 'Philippiens 1:3-8', content: 'Je rends grâces à mon Dieu de tout le souvenir que je garde de vous.' }}
            }},
            // 요한복음 1:14 (성탄절/말씀이 육신이 되어)
            'john-1-14': {{
                ko: {{ title: '요한복음 1:14', content: '말씀이 육신이 되어 우리 가운데 거하시매 우리가 그의 영광을 보니 아버지의 독생자의 영광이요 은혜와 진리가 충만하더라' }},
                en: {{ title: 'John 1:14', content: 'The Word became flesh and made his dwelling among us. We have seen his glory, the glory of the one and only Son, who came from the Father, full of grace and truth.' }},
                zh: {{ title: '约翰福音 1:14', content: '道成了肉身，住在我们中间，充充满满地有恩典有真理。我们也见过他的荣光，正是父独生子的荣光。' }},
                ja: {{ title: 'ヨハネ 1:14', content: 'ことばは人となって、私たちの間に住まわれた。私たちはこの方の栄光を見た。父のひとり子としての栄光である。この方は恵みとまことに満ちておられた。' }},
                id: {{ title: 'Yohanes 1:14', content: 'Firman itu telah menjadi manusia, dan diam di antara kita, dan kita telah melihat kemuliaan-Nya.' }},
                es: {{ title: 'Juan 1:14', content: 'Y aquel Verbo fue hecho carne, y habitó entre nosotros, y vimos su gloria, gloria como del unigénito del Padre.' }},
                ru: {{ title: 'Иоанна 1:14', content: 'И Слово стало плотию, и обитало с нами, полное благодати и истины.' }},
                fr: {{ title: 'Jean 1:14', content: 'Et la parole a été faite chair, et elle a habité parmi nous, pleine de grâce et de vérité.' }}
            }},
            // 에베소서 2:4-8 (은혜)
            'eph-2-4': {{
                ko: {{ title: '에베소서 2:4~8', content: '긍휼이 풍성하신 하나님이 우리를 사랑하신 그 큰 사랑을 인하여 허물로 죽은 우리를 그리스도와 함께 살리셨고 너희는 은혜로 구원을 받은 것이라' }},
                en: {{ title: 'Ephesians 2:4-8', content: 'But because of his great love for us, God, who is rich in mercy, made us alive with Christ even when we were dead in transgressions—it is by grace you have been saved.' }},
                zh: {{ title: '以弗所书 2:4-8', content: '然而，神既有丰富的怜悯，因他爱我们的大爱，当我们死在过犯中的时候，便叫我们与基督一同活过来。你们得救是本乎恩。' }},
                ja: {{ title: 'エペソ 2:4-8', content: 'しかし、あわれみ豊かな神は、私たちを愛してくださったその大きな愛のゆえに、背きの中に死んでいた私たちを、キリストとともに生かしてくださいました。' }},
                id: {{ title: 'Efesus 2:4-8', content: 'Tetapi Allah yang kaya dengan rahmat, oleh karena kasih-Nya yang besar, telah menghidupkan kita bersama-sama dengan Kristus.' }},
                es: {{ title: 'Efesios 2:4-8', content: 'Pero Dios, que es rico en misericordia, por su gran amor con que nos amó, nos dio vida juntamente con Cristo.' }},
                ru: {{ title: 'Ефесянам 2:4-8', content: 'Бог, богатый милостью, по Своей великой любви, которою возлюбил нас, оживотворил со Христом.' }},
                fr: {{ title: 'Éphésiens 2:4-8', content: 'Mais Dieu, qui est riche en miséricorde, nous a rendus à la vie avec Christ.' }}
            }},
            // 로마서 15:13 (소망)
            'rom-15-13': {{
                ko: {{ title: '로마서 15:13', content: '소망의 하나님이 모든 기쁨과 평강을 믿음 안에서 너희에게 충만하게 하사 성령의 능력으로 소망이 넘치게 하시기를 원하노라' }},
                en: {{ title: 'Romans 15:13', content: 'May the God of hope fill you with all joy and peace as you trust in him, so that you may overflow with hope by the power of the Holy Spirit.' }},
                zh: {{ title: '罗马书 15:13', content: '但愿使人有盼望的神，因信将诸般的喜乐、平安充满你们的心，使你们借着圣灵的能力大有盼望。' }},
                ja: {{ title: 'ローマ 15:13', content: '希望の神が、信仰によるすべての喜びと平安であなたがたを満たし、聖霊の力によって希望にあふれさせてくださいますように。' }},
                id: {{ title: 'Roma 15:13', content: 'Semoga Allah, sumber pengharapan, memenuhi kamu dengan segala sukacita dan damai sejahtera.' }},
                es: {{ title: 'Romanos 15:13', content: 'Y el Dios de esperanza os llene de todo gozo y paz en el creer.' }},
                ru: {{ title: 'Римлянам 15:13', content: 'Бог же надежды да исполнит вас всякой радости и мира в вере.' }},
                fr: {{ title: 'Romains 15:13', content: 'Que le Dieu de l\\'espérance vous remplisse de toute joie et de toute paix dans la foi.' }}
            }}
        }};

        // ========== 찬송가 데이터 (다국어 - 전문가 수준) ==========
        const hymnData = {{
            '8': {{
                ko: {{ title: '기뻐하며 경배하세', subtitle: 'Joyful, Joyful, We Adore Thee', composer: '베토벤 작곡', hymnLabel: '찬송가', verseLabel: '장', lyrics: [{{verse: 1, text: '기뻐하며 경배하세 영광의 주 하나님\\n주의 얼굴 빛 같으니 모든 근심 물러가네\\n죄와 슬픔 다 사라지고 의심 구름 걷히나니\\n영원하신 기쁨 되어 주의 빛 안에 살리라'}}, {{verse: 2, text: '주는 만물 다스리며 만유의 주 되시니\\n들의 꽃과 산과 강도 다 주를 찬양하도다\\n주의 손이 펼쳐 있어 온 세상에 복 주시고\\n사랑으로 덮으셨네 우리 찬양 받으소서'}}] }},
                en: {{ title: 'Joyful, Joyful, We Adore Thee', subtitle: 'Hymn to Joy', composer: 'Beethoven', hymnLabel: 'Hymn', verseLabel: '', lyrics: [{{verse: 1, text: 'Joyful, joyful, we adore Thee\\nGod of glory, Lord of love\\nHearts unfold like flowers before Thee\\nOpening to the sun above'}}, {{verse: 2, text: 'All Thy works with joy surround Thee\\nEarth and heaven reflect Thy rays\\nStars and angels sing around Thee\\nCenter of unbroken praise'}}] }},
                zh: {{ title: '欢乐颂', subtitle: '欢欣崇拜', composer: '贝多芬 作曲', hymnLabel: '赞美诗', verseLabel: '章', lyrics: [{{verse: 1, text: '欢欣敬拜荣耀主\\n天父上帝慈爱深\\n心如花朵向主开放\\n迎向阳光灿烂新'}}] }},
                ja: {{ title: '喜びの歌', subtitle: '喜び喜び主を崇めん', composer: 'ベートーヴェン作曲', hymnLabel: '讃美歌', verseLabel: '番', lyrics: [{{verse: 1, text: '喜び喜び主を崇めん\\n栄光の神 愛の主\\n心は花のように開く\\n太陽に向かって'}}] }},
                id: {{ title: 'Sukacita, Sukacita', subtitle: 'Bersuka Menyembah', composer: 'Beethoven', hymnLabel: 'Kidung', verseLabel: '', lyrics: [{{verse: 1, text: 'Sukacita sukacita\\nKita sembah Tuhan mulia'}}] }},
                es: {{ title: 'Jubilosos, Te Adoramos', subtitle: 'Himno a la Alegría', composer: 'Beethoven', hymnLabel: 'Himno', verseLabel: '', lyrics: [{{verse: 1, text: 'Jubilosos te adoramos\\nDios de gloria, Dios de amor'}}] }},
                ru: {{ title: 'Радостно, Радостно', subtitle: 'Ода к Радости', composer: 'Бетховен', hymnLabel: 'Гимн', verseLabel: '', lyrics: [{{verse: 1, text: 'Радостно, радостно поклоняемся\\nБогу славы, Богу любви'}}] }},
                fr: {{ title: 'Joyeux, Joyeux, Nous T\\'adorons', subtitle: 'Hymne à la Joie', composer: 'Beethoven', hymnLabel: 'Cantique', verseLabel: '', lyrics: [{{verse: 1, text: 'Joyeux, joyeux, nous t\\'adorons\\nDieu de gloire, Seigneur d\\'amour'}}] }},
                musical: {{ key: 'G', tempo: 'Allegro maestoso', timeSignature: '4/4' }}
            }},
            '94': {{
                ko: {{ title: '저 높고 푸른 하늘과', subtitle: 'This Is My Father\\'s World', composer: 'Franklin L. Sheppard', hymnLabel: '찬송가', verseLabel: '장', lyrics: [{{verse: 1, text: '저 높고 푸른 하늘과 그 아래 푸른 들\\n산과 나무와 꽃과 새 모두가 주 지으신 것\\n주님의 솜씨 온 세상에 깃들어 있나니\\n바람 소리 들리는 곳 주 음성이 들리네'}}] }},
                en: {{ title: 'This Is My Father\\'s World', subtitle: '', composer: 'Franklin L. Sheppard', hymnLabel: 'Hymn', verseLabel: '', lyrics: [{{verse: 1, text: 'This is my Father\\'s world\\nAnd to my listening ears\\nAll nature sings and round me rings\\nThe music of the spheres'}}] }},
                zh: {{ title: '这是天父世界', subtitle: '', composer: 'Franklin L. Sheppard', hymnLabel: '赞美诗', verseLabel: '章', lyrics: [{{verse: 1, text: '这是天父世界\\n我要侧耳细听'}}] }},
                ja: {{ title: 'この世は父の世界', subtitle: '', composer: 'Franklin L. Sheppard', hymnLabel: '讃美歌', verseLabel: '番', lyrics: [{{verse: 1, text: 'この世は父の世界\\n耳を澄ませば'}}] }},
                id: {{ title: 'Dunia Milik Bapa', hymnLabel: 'Kidung', verseLabel: '', lyrics: [{{verse: 1, text: 'Dunia ini milik Bapa'}}] }},
                es: {{ title: 'El Mundo Es De Mi Padre', hymnLabel: 'Himno', verseLabel: '', lyrics: [{{verse: 1, text: 'El mundo es de mi Padre'}}] }},
                ru: {{ title: 'Это Мир Моего Отца', hymnLabel: 'Гимн', verseLabel: '', lyrics: [{{verse: 1, text: 'Это мир моего Отца'}}] }},
                fr: {{ title: 'C\\'est Le Monde De Mon Père', hymnLabel: 'Cantique', verseLabel: '', lyrics: [{{verse: 1, text: 'C\\'est le monde de mon Père'}}] }},
                musical: {{ key: 'D', tempo: 'Andante', timeSignature: '6/8' }}
            }},
            '105': {{
                ko: {{ title: '온 천하 만물 우러러', subtitle: 'All Creatures of Our God and King', composer: 'Geistliche Kirchengesäng', hymnLabel: '찬송가', verseLabel: '장', lyrics: [{{verse: 1, text: '온 천하 만물 우러러 다 주를 찬양하여라\\n할렐루야 할렐루야\\n해와 달 아름답게 비치고 밝은 별들도 찬양해\\n찬양해 찬양해 할렐루야 할렐루야 할렐루야'}}] }},
                en: {{ title: 'All Creatures of Our God and King', subtitle: '', composer: 'Geistliche Kirchengesäng', hymnLabel: 'Hymn', verseLabel: '', lyrics: [{{verse: 1, text: 'All creatures of our God and King\\nLift up your voice and with us sing\\nAlleluia Alleluia'}}] }},
                zh: {{ title: '万物称颂主', hymnLabel: '赞美诗', verseLabel: '章', lyrics: [{{verse: 1, text: '万物同颂赞主\\n高举声音齐唱'}}] }},
                ja: {{ title: '神の造りしすべてのもの', hymnLabel: '讃美歌', verseLabel: '番', lyrics: [{{verse: 1, text: '神の造りしすべてのものよ'}}] }},
                id: {{ title: 'Segala Makhluk Tuhan', hymnLabel: 'Kidung', verseLabel: '', lyrics: [{{verse: 1, text: 'Segala makhluk Allah'}}] }},
                es: {{ title: 'Criaturas Del Señor', hymnLabel: 'Himno', verseLabel: '', lyrics: [{{verse: 1, text: 'Criaturas del Señor'}}] }},
                ru: {{ title: 'Все Создания Бога', hymnLabel: 'Гимн', verseLabel: '', lyrics: [{{verse: 1, text: 'Все создания Бога нашего'}}] }},
                fr: {{ title: 'Créatures Du Seigneur', hymnLabel: 'Cantique', verseLabel: '', lyrics: [{{verse: 1, text: 'Créatures de notre Dieu'}}] }},
                musical: {{ key: 'F', tempo: 'Maestoso', timeSignature: '3/4' }}
            }},
            '301': {{
                ko: {{ title: '지금까지 지내온 것', subtitle: 'Wonderful Grace of Jesus', composer: 'Haldor Lillenas', hymnLabel: '찬송가', verseLabel: '장', lyrics: [{{verse: 1, text: '지금까지 지내온 것 주의 크신 은혜라\\n한이 없는 주의 사랑 어찌 다 측량하랴\\n주님 크신 은혜가 나를 구원하셨네\\n나 같은 죄인도 구원하신 주 은혜 놀라와'}}] }},
                en: {{ title: 'Wonderful Grace of Jesus', subtitle: '', composer: 'Haldor Lillenas', hymnLabel: 'Hymn', verseLabel: '', lyrics: [{{verse: 1, text: 'Wonderful grace of Jesus\\nGreater than all my sin'}}] }},
                zh: {{ title: '主恩典何等奇妙', hymnLabel: '赞美诗', verseLabel: '章', lyrics: [{{verse: 1, text: '主恩典何等奇妙'}}] }},
                ja: {{ title: '主の恵み素晴らしき', hymnLabel: '讃美歌', verseLabel: '番', lyrics: [{{verse: 1, text: '主の恵み素晴らしき'}}] }},
                id: {{ title: 'Anugerah Yesus Ajaib', hymnLabel: 'Kidung', verseLabel: '', lyrics: [{{verse: 1, text: 'Anugerah Yesus ajaib'}}] }},
                es: {{ title: 'Maravillosa Gracia', hymnLabel: 'Himno', verseLabel: '', lyrics: [{{verse: 1, text: 'Maravillosa gracia de Jesús'}}] }},
                ru: {{ title: 'Чудесная Благодать', hymnLabel: 'Гимн', verseLabel: '', lyrics: [{{verse: 1, text: 'Чудесная благодать Иисуса'}}] }},
                fr: {{ title: 'Merveilleuse Grâce', hymnLabel: 'Cantique', verseLabel: '', lyrics: [{{verse: 1, text: 'Merveilleuse grâce de Jésus'}}] }},
                musical: {{ key: 'Ab', tempo: 'Moderato', timeSignature: '4/4' }}
            }},
            '187': {{
                ko: {{ title: '주 예수 이름 높이어', subtitle: 'All Hail the Power of Jesus\\' Name', composer: 'Oliver Holden', hymnLabel: '찬송가', verseLabel: '장', lyrics: [{{verse: 1, text: '주 예수 이름 높이어 다 찬양하여라\\n천사들아 엎드려서 면류관 드리어라'}}] }},
                en: {{ title: 'All Hail the Power of Jesus\\' Name', hymnLabel: 'Hymn', verseLabel: '', lyrics: [{{verse: 1, text: 'All hail the power of Jesus\\' name\\nLet angels prostrate fall'}}] }},
                zh: {{ title: '万口欢唱', hymnLabel: '赞美诗', verseLabel: '章', lyrics: [{{verse: 1, text: '万口欢唱救主耶稣'}}] }},
                ja: {{ title: '主イエスの御名をたたえよ', hymnLabel: '讃美歌', verseLabel: '番', lyrics: [{{verse: 1, text: '主イエスの御名をたたえよ'}}] }},
                musical: {{ key: 'G', tempo: 'Maestoso', timeSignature: '4/4' }}
            }},
            '435': {{
                ko: {{ title: '나의 갈 길 다 가도록', subtitle: 'All the Way My Savior Leads Me', composer: 'Robert Lowry', hymnLabel: '찬송가', verseLabel: '장', lyrics: [{{verse: 1, text: '나의 갈 길 다 가도록 예수 인도하시니\\n내가 어찌 주를 앙모하지 않을 수 있으랴'}}] }},
                en: {{ title: 'All the Way My Savior Leads Me', hymnLabel: 'Hymn', verseLabel: '', lyrics: [{{verse: 1, text: 'All the way my Savior leads me\\nWhat have I to ask beside'}}] }},
                zh: {{ title: '一路引导', hymnLabel: '赞美诗', verseLabel: '章', lyrics: [{{verse: 1, text: '一路有救主同行'}}] }},
                ja: {{ title: '主イエスがすべての道を', hymnLabel: '讃美歌', verseLabel: '番', lyrics: [{{verse: 1, text: '主イエスがすべての道を'}}] }},
                musical: {{ key: 'G', tempo: 'Andante', timeSignature: '4/4' }}
            }}
        }};
        const hymns = hymnData; // 하위 호환성

        // 성경 API 설정 (선택적 외부 API 연동)
        const BIBLE_API_ENABLED = false;  // 외부 API 사용 시 true로 변경
        const BIBLE_API_URL = '/api/bible/';  // 백엔드 API 엔드포인트

        // 성경 구절 파싱 (예: "요한복음 3:16", "창세기 1:1-3")
        function parseBibleReference(ref) {{
            if (!ref) return null;
            const match = ref.match(/([가-힣]+)\s*(\d+)[장]?\s*[:절]\s*(\d+)(?:\s*[-~]\s*(\d+))?/);
            if (match) {{
                return {{
                    book: match[1],
                    chapter: parseInt(match[2]),
                    verseStart: parseInt(match[3]),
                    verseEnd: match[4] ? parseInt(match[4]) : parseInt(match[3])
                }};
            }}
            return null;
        }}

        // 성경 모달 열기 (다국어 지원)
        function openBibleModal(verseKey) {{
            const verseData = bibleVerses[verseKey];
            const modal = document.getElementById('bibleModal');
            const titleEl = document.getElementById('bibleModalTitle');
            const contentEl = document.getElementById('bibleModalContent');

            if (verseData) {{
                // 현재 언어 -> 영어 -> 한국어 폴백
                const verse = verseData[currentLanguage] || verseData['en'] || verseData['ko'];
                titleEl.textContent = '📖 ' + verse.title;

                if (BIBLE_API_ENABLED && verse.title) {{
                    // API에서 성경 구절 불러오기
                    contentEl.innerHTML = '<p style="text-align: center; color: var(--text-secondary);">📖 성경 구절을 불러오는 중...</p>';
                    modal.classList.add('active');
                    document.body.style.overflow = 'hidden';

                    fetchBibleVerse(verse.title).then(text => {{
                        contentEl.innerHTML = `<div class="bible-verse-text" style="line-height: 2;">${{text}}</div>`;
                    }}).catch(err => {{
                        contentEl.innerHTML = verse.content || '<p>성경 구절을 불러올 수 없습니다.</p>';
                    }});
                }} else {{
                    // 로컬 데이터 사용
                    contentEl.innerHTML = '<div class="bible-verse-text" style="line-height: 2;">' + verse.content + '</div>';
                    modal.classList.add('active');
                    document.body.style.overflow = 'hidden';
                }}
            }}
        }}

        // 성경 구절 API 호출
        async function fetchBibleVerse(reference) {{
            try {{
                const parsed = parseBibleReference(reference);
                if (!parsed) {{
                    throw new Error('Invalid reference');
                }}
                const response = await fetch(`${{BIBLE_API_URL}}${{encodeURIComponent(reference)}}`);
                if (!response.ok) throw new Error('API error');
                const data = await response.json();
                return data.text || data.content || reference;
            }} catch (error) {{
                console.log('Bible API not available, using local data');
                return '성경 본문이 표시됩니다.<br><small style="color: var(--text-secondary);">(외부 API 연동 시 실제 구절이 표시됩니다)</small>';
            }}
        }}

        // 성경 구절 직접 열기 (참조 문자열로)
        function openBibleVerseByRef(reference) {{
            const modal = document.getElementById('bibleModal');
            const titleEl = document.getElementById('bibleModalTitle');
            const contentEl = document.getElementById('bibleModalContent');

            titleEl.textContent = '📖 ' + reference;
            contentEl.innerHTML = '<p style="text-align: center; color: var(--text-secondary);">📖 성경 구절을 불러오는 중...</p>';
            modal.classList.add('active');
            document.body.style.overflow = 'hidden';

            if (BIBLE_API_ENABLED) {{
                fetchBibleVerse(reference).then(text => {{
                    contentEl.innerHTML = `<div class="bible-verse-text" style="line-height: 2;">${{text}}</div>`;
                }});
            }} else {{
                contentEl.innerHTML = '<div class="bible-verse-text" style="line-height: 2;">성경 본문이 표시됩니다.<br><small style="color: var(--text-secondary);">(외부 API 연동 시 실제 구절이 표시됩니다)</small></div>';
            }}
        }}

        function openHymnModal(hymnNum) {{
            const hymnDataItem = hymnData[hymnNum];
            const modal = document.getElementById('hymnModal');
            const titleEl = document.getElementById('hymnModalTitle');
            const contentEl = document.getElementById('hymnModalContent');

            if (hymnDataItem) {{
                // 현재 언어 -> 영어 -> 한국어 폴백
                const hymn = hymnDataItem[currentLanguage] || hymnDataItem['en'] || hymnDataItem['ko'];
                const musical = hymnDataItem.musical || {{}};
                const hymnLabel = hymn.hymnLabel || '찬송가';
                const verseLabel = hymn.verseLabel || '';

                titleEl.textContent = '🎵 ' + hymnLabel + ' ' + hymnNum + verseLabel;
                let lyricsHtml = hymn.lyrics ? hymn.lyrics.map(v =>
                    '<div class="hymn-verse"><span class="verse-number">' + v.verse + '</span>' + v.text.replace(/\\n/g, '<br>') + '</div>'
                ).join('') : '<p style="text-align: center; color: var(--text-gray);">가사가 준비 중입니다.</p>';

                contentEl.innerHTML = `
                    <div class="hymn-sheet">
                        <div class="hymn-info">
                            <div class="hymn-number">${{hymnNum}}${{verseLabel}}</div>
                            <div class="hymn-title">${{hymn.title}}</div>
                            <div style="font-size: 0.85em; color: var(--text-gray); margin-top: 8px;">${{musical.key || ''}} | ${{musical.tempo || ''}}</div>
                        </div>
                        <div class="hymn-lyrics">${{lyricsHtml}}</div>
                    </div>
                `;
                modal.classList.add('active');
                document.body.style.overflow = 'hidden';
            }} else {{
                // 찬송가 데이터가 없는 경우
                const hymnLabels = {{ ko: '찬송가', en: 'Hymn', zh: '赞美诗', ja: '讃美歌', id: 'Kidung', es: 'Himno', ru: 'Гимн', fr: 'Cantique' }};
                const notReadyMsg = {{
                    ko: '이 찬송가의 가사는 준비 중입니다.',
                    en: 'Lyrics for this hymn are being prepared.',
                    zh: '此赞美诗的歌词正在准备中。',
                    ja: 'この讃美歌の歌詞は準備中です。',
                    id: 'Lirik untuk kidung ini sedang dipersiapkan.',
                    es: 'La letra de este himno está en preparación.',
                    ru: 'Текст этого гимна готовится.',
                    fr: 'Les paroles de ce cantique sont en préparation.'
                }};
                const label = hymnLabels[currentLanguage] || hymnLabels['ko'];
                const msg = notReadyMsg[currentLanguage] || notReadyMsg['ko'];

                titleEl.textContent = '🎵 ' + label + ' ' + hymnNum;
                contentEl.innerHTML = '<div style="text-align: center; padding: 40px; color: var(--text-gray);"><p>' + msg + '</p></div>';
                modal.classList.add('active');
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

        // ============================================
        // 아코디언 토글 함수 (명성교회 고도화)
        // ============================================
        function toggleAccordion(accordionId) {{
            const accordion = document.getElementById(accordionId);
            if (accordion) {{
                accordion.classList.toggle('open');
                const arrow = accordion.querySelector('.accordion-arrow');
                if (arrow) {{
                    arrow.textContent = accordion.classList.contains('open') ? '▲' : '▼';
                }}
            }}
        }}

        // 오늘의 말씀 아코디언 토글
        function toggleSermonWord(element) {{
            element.classList.toggle('expanded');
        }}

        // 지난주 말씀 모달 열기
        let lastWeekSermonData = null;
        function setLastWeekSermonData(title, scripture, preacher, content) {{
            lastWeekSermonData = {{ title, scripture, preacher, content }};
        }}

        function openLastWeekModal() {{
            if (lastWeekSermonData) {{
                const modal = document.getElementById('lastWeekModal');
                const content = document.getElementById('lastWeekModalContent');
                content.querySelector('.sermon-title').textContent = lastWeekSermonData.title || '지난주 말씀';
                content.querySelector('.sermon-ref').textContent =
                    (lastWeekSermonData.scripture || '') +
                    (lastWeekSermonData.preacher ? ' | ' + lastWeekSermonData.preacher : '');
                content.querySelector('.sermon-text').textContent = lastWeekSermonData.content || '';
                modal.classList.add('active');
                document.body.style.overflow = 'hidden';
            }}
        }}

        // 교독문 모달 열기
        function openResponsiveReading(readingNum) {{
            const title = document.getElementById('responsiveReadingTitle');
            const content = document.getElementById('responsiveReadingContent');
            title.textContent = '📜 교독문 ' + readingNum + '번';
            content.innerHTML = '<p style="text-align: center; color: var(--text-secondary);">교독문 내용을 불러오는 중...</p>';
            document.getElementById('responsiveReadingModal').classList.add('active');
            document.body.style.overflow = 'hidden';
            // TODO: 실제 교독문 데이터 연동
        }}

        // 사도신경 모달 열기
        function openCreed() {{
            document.getElementById('creedModal').classList.add('active');
            document.body.style.overflow = 'hidden';
        }}

        // 주기도문 모달 열기
        function openLordsPrayer() {{
            document.getElementById('lordsPrayerModal').classList.add('active');
            document.body.style.overflow = 'hidden';
        }}

        // 오늘의 말씀 아코디언 토글
        function toggleVerseAccordion(element) {{
            element.classList.toggle('expanded');
        }}

        // 예배 회차별 탭 전환 (명성교회)
        function switchServiceTab(serviceNum) {{
            // 모든 탭 비활성화
            document.querySelectorAll('.service-tab').forEach(tab => {{
                tab.classList.remove('active');
            }});
            // 클릭한 탭 활성화
            event.target.classList.add('active');

            // 회차별 내용 전환
            document.querySelectorAll('.service-detail').forEach(detail => {{
                detail.style.display = 'none';
            }});
            const activeDetail = document.getElementById('service-' + serviceNum);
            if (activeDetail) {{
                activeDetail.style.display = 'block';
            }}
        }}

        // 교우소식 카테고리 아코디언 (명성교회)
        function toggleMemberNewsCategory(categoryId) {{
            const category = document.getElementById(categoryId);
            if (category) {{
                category.classList.toggle('open');
                const arrow = category.querySelector('.category-arrow');
                if (arrow) {{
                    arrow.textContent = category.classList.contains('open') ? '−' : '+';
                }}
            }}
        }}

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

        // ========== 예배별 탭 전환 ==========
        const serviceData = {{
            '1bu': {{
                hymn: '<a href="javascript:void(0)" onclick="openHymnModal(\\'301\\')" class="hymn-link">301장</a>(통460장) (다같이)',
                prayer: '대표기도자',
                scripture: '<a href="javascript:void(0)" onclick="openBibleModal(\\'phil-1-3\\')" class="bible-link">빌 1:3~8</a> (사회자)',
                choir: '베다니 찬양대',
                sermon: '담임목사',
                offering: '헌금기도자',
                time: '오전 7:00'
            }},
            '234bu': {{
                hymn: '<a href="javascript:void(0)" onclick="openHymnModal(\\'105\\')" class="hymn-link">105장</a> (다같이)',
                prayer: '대표기도자',
                scripture: '<a href="javascript:void(0)" onclick="openBibleModal(\\'luke-3-4\\')" class="bible-link">눅 3:4~6</a> (사회자)',
                choir: '베들레헴 찬양대',
                sermon: '담임목사',
                offering: '헌금기도자',
                time: '오전 9:00 / 11:00 / 오후 1:00'
            }},
            'youth': {{
                hymn: '<a href="javascript:void(0)" onclick="openHymnModal(\\'105\\')" class="hymn-link">105장</a> (다같이)',
                prayer: '대표기도자',
                scripture: '<a href="javascript:void(0)" onclick="openBibleModal(\\'john-1-14\\')" class="bible-link">요 1:14</a> (사회자)',
                choir: '청년 찬양팀',
                sermon: '청년 담당 목사',
                offering: '헌금기도자',
                time: '오후 2:00'
            }},
            'evening': {{
                hymn: '<a href="javascript:void(0)" onclick="openHymnModal(\\'94\\')" class="hymn-link">94장</a> (다같이)',
                prayer: '대표기도자',
                scripture: '<a href="javascript:void(0)" onclick="openBibleModal(\\'eph-2-4\\')" class="bible-link">엡 2:4~8</a> (사회자)',
                choir: '찬양대',
                sermon: '담임목사',
                offering: '헌금기도자',
                time: '오후 5:00'
            }}
        }};

        function switchService(serviceKey) {{
            // 탭 버튼 활성화 상태 변경
            document.querySelectorAll('.service-tab').forEach(tab => {{
                tab.classList.remove('active');
                if (tab.dataset.service === serviceKey) {{
                    tab.classList.add('active');
                }}
            }});

            // 콘텐츠 업데이트
            const data = serviceData[serviceKey];
            if (data) {{
                const hymnEl = document.getElementById('hymn-value');
                const prayerEl = document.getElementById('prayer-value');
                const scriptureEl = document.getElementById('scripture-value');
                const choirEl = document.getElementById('choir-value');
                const sermonEl = document.getElementById('sermon-value');
                const offeringEl = document.getElementById('offering-value');

                if (hymnEl) hymnEl.innerHTML = data.hymn;
                if (prayerEl) prayerEl.textContent = data.prayer;
                if (scriptureEl) scriptureEl.innerHTML = data.scripture;
                if (choirEl) choirEl.textContent = data.choir;
                if (sermonEl) sermonEl.textContent = data.sermon;
                if (offeringEl) offeringEl.textContent = data.offering;
            }}
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

        // 계좌번호 복사
        function copyAccount(accountNum) {{
            navigator.clipboard.writeText(accountNum).then(() => {{
                alert('계좌번호가 복사되었습니다: ' + accountNum);
            }}).catch(() => {{
                // 폴백: 구형 브라우저용
                const textarea = document.createElement('textarea');
                textarea.value = accountNum;
                document.body.appendChild(textarea);
                textarea.select();
                document.execCommand('copy');
                document.body.removeChild(textarea);
                alert('계좌번호가 복사되었습니다: ' + accountNum);
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

        // ========== 헌금 모달 시스템 (전문가 수준) ==========
        const offeringData = {{
            bank: {{
                title: '계좌이체 헌금',
                content: `<div style="padding: 20px;">
                    <div style="background: var(--primary-light); padding: 20px; border-radius: 12px; margin-bottom: 20px;">
                        <h3 style="color: var(--primary); margin-bottom: 16px;">헌금 계좌 안내</h3>
                        <div style="background: white; padding: 16px; border-radius: 8px; margin-bottom: 8px; cursor: pointer;" onclick="copyAccount('060-9191-9191')">
                            <div style="font-weight: 600; color: var(--primary);">우리은행</div>
                            <div style="font-size: 1.1em; font-weight: 700; margin: 6px 0;">060-9191-9191 📋</div>
                        </div>
                        <div style="background: white; padding: 16px; border-radius: 8px; margin-bottom: 8px; cursor: pointer;" onclick="copyAccount('816-25-0003-095')">
                            <div style="font-weight: 600; color: var(--primary);">국민은행</div>
                            <div style="font-size: 1.1em; font-weight: 700; margin: 6px 0;">816-25-0003-095 📋</div>
                        </div>
                        <div style="background: white; padding: 16px; border-radius: 8px; margin-bottom: 8px; cursor: pointer;" onclick="copyAccount('256-890015-74104')">
                            <div style="font-weight: 600; color: var(--primary);">하나은행</div>
                            <div style="font-size: 1.1em; font-weight: 700; margin: 6px 0;">256-890015-74104 📋</div>
                        </div>
                        <div style="background: white; padding: 16px; border-radius: 8px; cursor: pointer;" onclick="copyAccount('367-01-035287')">
                            <div style="font-weight: 600; color: var(--primary);">농협</div>
                            <div style="font-size: 1.1em; font-weight: 700; margin: 6px 0;">367-01-035287 📋</div>
                        </div>
                        <div style="color: var(--text-gray); font-size: 0.85em; margin-top: 12px; text-align: center;">예금주: {church_name}</div>
                    </div>
                    <div style="font-size: 0.9em; color: var(--text-gray); line-height: 1.6;">
                        <p>※ 입금자명에 교적번호 또는 이름을 기재해 주세요.</p>
                    </div>
                </div>`
            }},
            kakaopay: {{
                title: '카카오페이 헌금',
                content: `<div style="padding: 20px; text-align: center;">
                    <div style="background: #FEE500; color: #3C1E1E; padding: 40px; border-radius: 16px; margin-bottom: 20px;">
                        <div style="font-size: 3em; margin-bottom: 16px;">💛</div>
                        <div style="font-size: 1.2em; font-weight: 700;">카카오페이로 헌금하기</div>
                    </div>
                    <div style="background: var(--bg-gray); padding: 20px; border-radius: 12px;">
                        <p style="font-weight: 600; margin-bottom: 12px;">카카오페이 송금 방법</p>
                        <ol style="text-align: left; line-height: 2; padding-left: 20px; color: var(--text-gray);">
                            <li>카카오톡 앱을 엽니다</li>
                            <li>하단 메뉴에서 더보기 선택</li>
                            <li>카카오페이 > 송금 선택</li>
                            <li>계좌번호로 송금 선택</li>
                        </ol>
                    </div>
                </div>`
            }},
            app: {{
                title: '교회 앱 헌금',
                content: `<div style="padding: 20px; text-align: center;">
                    <div style="background: linear-gradient(135deg, var(--primary) 0%, var(--primary-dark) 100%); color: white; padding: 40px; border-radius: 16px; margin-bottom: 20px;">
                        <div style="font-size: 3em; margin-bottom: 16px;">⛪</div>
                        <div style="font-size: 1.2em; font-weight: 700;">{church_name} 앱</div>
                    </div>
                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin-bottom: 20px;">
                        <a href="#" style="display: block; background: #000; color: white; padding: 16px; border-radius: 10px; text-decoration: none;">
                            <div style="font-size: 1.5em; margin-bottom: 4px;">🍎</div>
                            <div style="font-size: 0.85em;">App Store</div>
                        </a>
                        <a href="#" style="display: block; background: #3DDC84; color: white; padding: 16px; border-radius: 10px; text-decoration: none;">
                            <div style="font-size: 1.5em; margin-bottom: 4px;">🤖</div>
                            <div style="font-size: 0.85em;">Google Play</div>
                        </a>
                    </div>
                </div>`
            }}
        }};

        function openOfferingModal(type) {{
            const data = offeringData[type];
            const modal = document.getElementById('offeringModal');
            document.getElementById('offeringModalTitle').textContent = data.title;
            document.getElementById('offeringModalBody').innerHTML = data.content;
            modal.classList.add('active');
            document.body.style.overflow = 'hidden';
        }}

        function closeOfferingModal(event) {{
            if (event && event.target !== event.currentTarget && !event.target.classList.contains('modal-close')) return;
            document.getElementById('offeringModal').classList.remove('active');
            document.body.style.overflow = '';
        }}

        // ESC 키로 모든 모달 닫기
        document.addEventListener('keydown', function(e) {{
            if (e.key === 'Escape') {{
                closeModal('bibleModal');
                closeModal('hymnModal');
                closeModal('lastWeekModal');
                closeOfferingModal();
            }}
        }});
    </script>'''


# ============================================================
# 다중 템플릿 시스템 (Traditional / Modern 스타일)
# ============================================================

class TraditionalChurchGenerator(ChurchBulletinGenerator):
    """전통적인 교회 스타일 생성기 (따뜻한 브라운/골드 테마)

    혈동교회, 장로교회 등 전통적인 분위기의 교회에 적합
    """

    # 전통적인 교회 테마
    THEMES = {
        "default": {
            "primary": "#8B4513",
            "primary_dark": "#5D3A1A",
            "primary_light": "#F5E6D3",
            "accent": "#C5A572",
            "harvest": "#8B4513",
            "header_gradient": "linear-gradient(135deg, #8B4513 0%, #D2691E 100%)",
            "theme_color": "#8B4513",
            "is_harvest": False
        },
        "advent": {  # 대림절
            "primary": "#4A0D67",
            "primary_dark": "#2D0840",
            "primary_light": "#E8D5F0",
            "accent": "#9333EA",
            "harvest": "#4A0D67",
            "header_gradient": "linear-gradient(135deg, #4A0D67 0%, #7C3AED 100%)",
            "theme_color": "#4A0D67",
            "is_harvest": False
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
        "lent": {  # 사순절
            "primary": "#4B0082",
            "primary_dark": "#2E0854",
            "primary_light": "#E6E0F0",
            "accent": "#8B668B",
            "harvest": "#4B0082",
            "header_gradient": "linear-gradient(135deg, #4B0082 0%, #6B238E 100%)",
            "theme_color": "#4B0082",
            "is_harvest": False
        },
        "easter": {  # 부활절
            "primary": "#FFD700",
            "primary_dark": "#DAA520",
            "primary_light": "#FFFACD",
            "accent": "#FFFFFF",
            "harvest": "#FFD700",
            "header_gradient": "linear-gradient(135deg, #FFD700 0%, #FFA500 100%)",
            "theme_color": "#FFD700",
            "is_harvest": False
        },
        "pentecost": {  # 성령강림절
            "primary": "#DC143C",
            "primary_dark": "#8B0000",
            "primary_light": "#FFE4E1",
            "accent": "#FF6347",
            "harvest": "#DC143C",
            "header_gradient": "linear-gradient(135deg, #DC143C 0%, #FF4500 100%)",
            "theme_color": "#DC143C",
            "is_harvest": False
        }
    }

    def _get_css(self, theme: Dict, is_harvest: bool, theme_name: str = "default") -> str:
        """전통적인 스타일 CSS 생성"""
        base_css = super()._get_css(theme, is_harvest, theme_name)

        # 전통적인 스타일 추가 CSS
        traditional_css = """
        /* 전통적인 스타일 오버라이드 */
        body {
            font-family: 'Noto Serif KR', 'Apple SD Gothic Neo', serif;
        }

        .church-name {
            font-family: 'Noto Serif KR', serif;
            letter-spacing: 4px;
        }

        .section-title {
            font-family: 'Noto Serif KR', serif;
        }

        .verse-text {
            font-family: 'Noto Serif KR', serif;
        }

        .sermon-content {
            font-family: 'Noto Serif KR', serif;
        }

        /* 세리프 폰트 로드 */
        @import url('https://fonts.googleapis.com/css2?family=Noto+Serif+KR:wght@400;600;700&display=swap');
        """

        return base_css.replace('</style>', traditional_css + '</style>')


# ============================================================
# 주보 아카이브 인덱스 생성기
# ============================================================

class ChurchArchiveGenerator:
    """교회 주보 아카이브 인덱스 페이지 생성기"""

    def __init__(self, church_info: Dict = None):
        self.church_info = church_info or ChurchBulletinGenerator.DEFAULT_CHURCH_INFO

    def generate_index(self, bulletins: List[Dict], output_path: str = None) -> str:
        """
        주보 목록 인덱스 페이지 생성

        Args:
            bulletins: 주보 목록 [{"date": "2025-12-07", "title": "...", "file": "...", "theme": "..."}]
            output_path: 출력 경로 (선택)

        Returns:
            HTML 문자열
        """
        church_name = self.church_info.get("name", "교회")

        # 주보 카드 HTML 생성
        cards_html = ""
        for bulletin in bulletins:
            date = bulletin.get("date", "")
            title = bulletin.get("title", "주일예배")
            file_path = bulletin.get("file", "#")
            theme = bulletin.get("theme", "default")
            sermon_title = bulletin.get("sermon_title", "")

            # 테마별 배지 색상
            theme_colors = {
                "default": "#5B4B9E",
                "harvest": "#8B6914",
                "christmas": "#C41E3A",
                "easter": "#9370DB",
                "advent": "#4A0D67",
                "lent": "#4B0082",
                "pentecost": "#DC143C"
            }
            badge_color = theme_colors.get(theme, "#5B4B9E")

            cards_html += f'''
            <a href="{file_path}" class="bulletin-card">
                <div class="card-date">{date}</div>
                <div class="card-title">{title}</div>
                {f'<div class="card-sermon">{sermon_title}</div>' if sermon_title else ''}
                <div class="card-badge" style="background: {badge_color}">
                    {"🌾 추수감사절" if theme == "harvest" else
                     "🎄 성탄절" if theme == "christmas" else
                     "✝️ 부활절" if theme == "easter" else
                     "🕯️ 대림절" if theme == "advent" else
                     "⛪ 주일예배"}
                </div>
            </a>'''

        html = f'''<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{church_name} 주보 아카이브</title>
    <meta name="description" content="{church_name} 주보 모음">
    <meta name="theme-color" content="#5B4B9E">
    <link rel="apple-touch-icon" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><text y='.9em' font-size='90'>⛪</text></svg>">
    <style>
        :root {{
            --primary: #5B4B9E;
            --primary-dark: #4A3D82;
            --primary-light: #E8E4F4;
            --accent: #C9A857;
            --text-dark: #1a1a2e;
            --text-gray: #6B7280;
            --bg-gray: #F5F3FA;
            --white: #FFFFFF;
        }}

        * {{ margin: 0; padding: 0; box-sizing: border-box; }}

        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Apple SD Gothic Neo', 'Noto Sans KR', sans-serif;
            background: var(--bg-gray);
            color: var(--text-dark);
            min-height: 100vh;
        }}

        .header {{
            background: linear-gradient(135deg, var(--primary) 0%, var(--primary-dark) 100%);
            color: white;
            padding: 24px 20px;
            text-align: center;
            position: sticky;
            top: 0;
            z-index: 100;
        }}

        .church-name {{
            font-size: 1.5em;
            font-weight: 800;
            margin-bottom: 4px;
        }}

        .archive-title {{
            font-size: 1em;
            opacity: 0.9;
        }}

        .container {{
            max-width: 600px;
            margin: 0 auto;
            padding: 20px;
        }}

        .year-section {{
            margin-bottom: 24px;
        }}

        .year-header {{
            font-size: 1.2em;
            font-weight: 700;
            color: var(--primary);
            padding: 12px 0;
            border-bottom: 2px solid var(--primary-light);
            margin-bottom: 12px;
        }}

        .bulletins-grid {{
            display: grid;
            gap: 12px;
        }}

        .bulletin-card {{
            display: block;
            background: var(--white);
            border-radius: 12px;
            padding: 16px;
            text-decoration: none;
            color: var(--text-dark);
            box-shadow: 0 2px 8px rgba(0,0,0,0.06);
            transition: all 0.2s;
        }}

        .bulletin-card:hover {{
            transform: translateY(-2px);
            box-shadow: 0 4px 16px rgba(0,0,0,0.1);
        }}

        .card-date {{
            font-size: 0.85em;
            color: var(--text-gray);
            margin-bottom: 4px;
        }}

        .card-title {{
            font-size: 1.1em;
            font-weight: 700;
            margin-bottom: 8px;
        }}

        .card-sermon {{
            font-size: 0.9em;
            color: var(--text-gray);
            margin-bottom: 8px;
        }}

        .card-badge {{
            display: inline-block;
            color: white;
            padding: 4px 10px;
            border-radius: 12px;
            font-size: 0.75em;
            font-weight: 600;
        }}

        .empty-state {{
            text-align: center;
            padding: 60px 20px;
            color: var(--text-gray);
        }}

        .empty-icon {{
            font-size: 3em;
            margin-bottom: 16px;
        }}

        .footer {{
            text-align: center;
            padding: 30px;
            color: var(--text-gray);
            font-size: 0.85em;
        }}
    </style>
</head>
<body>
    <header class="header">
        <h1 class="church-name">{church_name}</h1>
        <p class="archive-title">📚 주보 아카이브</p>
    </header>

    <main class="container">
        <section class="year-section">
            <h2 class="year-header">2025년</h2>
            <div class="bulletins-grid">
                {cards_html if cards_html else '''
                <div class="empty-state">
                    <div class="empty-icon">📭</div>
                    <p>아직 등록된 주보가 없습니다.</p>
                </div>
                '''}
            </div>
        </section>
    </main>

    <footer class="footer">
        © 2025 {church_name}. 손안의 주보 서비스
    </footer>
</body>
</html>'''

        if output_path:
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(html)

        return html


# ============================================================
# 교회 설정 관리 시스템
# ============================================================

class ChurchConfigManager:
    """교회별 설정 관리자"""

    # 사전 정의된 교회 프리셋
    CHURCH_PRESETS = {
        "여의도순복음교회": {
            "name": "여의도순복음교회",
            "name_en": "YOIDO FULL GOSPEL CHURCH",
            "address": "서울특별시 영등포구 국회대로76길 15",
            "founded": "1958년 5월 18일 창립",
            "phone_day": "02-6181-9191",
            "phone_night": "02-6181-9000~3",
            "website": "https://www.fgtv.com",
            "sns": {
                "youtube": "https://www.youtube.com/user/YFGCFGTV",
                "kakaotalk": "http://pf.kakao.com/_NrTxkK",
                "instagram": "https://www.instagram.com/yfgcprb/"
            },
            "donation_url": "https://m.fgtv.com/donate/donate_m_ver2.asp",
            "template_style": "modern",
            "theme": "default"
        },
        "혈동교회": {
            "name": "혈동교회",
            "name_en": "",
            "address": "",
            "founded": "",
            "phone_day": "",
            "phone_night": "",
            "website": "",
            "sns": {},
            "donation_url": "",
            "template_style": "traditional",
            "theme": "default"
        }
    }

    @classmethod
    def get_preset(cls, church_name: str) -> Dict:
        """교회 프리셋 가져오기"""
        return cls.CHURCH_PRESETS.get(church_name, cls._get_default_preset(church_name))

    @classmethod
    def _get_default_preset(cls, church_name: str) -> Dict:
        """기본 프리셋 생성"""
        return {
            "name": church_name,
            "name_en": "",
            "address": "",
            "founded": "",
            "phone_day": "",
            "phone_night": "",
            "website": "",
            "sns": {},
            "donation_url": "",
            "template_style": "modern",
            "theme": "default"
        }

    @classmethod
    def create_generator(cls, church_name: str = None, church_info: Dict = None) -> ChurchBulletinGenerator:
        """교회 정보에 맞는 생성기 생성"""
        if church_info:
            config = church_info
        elif church_name:
            config = cls.get_preset(church_name)
        else:
            config = cls.CHURCH_PRESETS["여의도순복음교회"]

        template_style = config.get("template_style", "modern")

        if template_style == "traditional":
            return TraditionalChurchGenerator(config)
        else:
            return ChurchBulletinGenerator(config)


# ============================================================
# 싱글톤 및 팩토리 함수
# ============================================================

_church_generator = None
_archive_generator = None

def get_church_bulletin_generator(church_info: Dict = None, church_name: str = None) -> ChurchBulletinGenerator:
    """교회 주보 생성기 인스턴스 반환

    Args:
        church_info: 교회 정보 딕셔너리
        church_name: 교회 이름 (프리셋 사용)

    Returns:
        ChurchBulletinGenerator 또는 TraditionalChurchGenerator 인스턴스
    """
    global _church_generator

    if church_info or church_name:
        return ChurchConfigManager.create_generator(church_name, church_info)

    if _church_generator is None:
        _church_generator = ChurchBulletinGenerator()

    return _church_generator


def get_archive_generator(church_info: Dict = None) -> ChurchArchiveGenerator:
    """주보 아카이브 생성기 인스턴스 반환"""
    global _archive_generator
    if _archive_generator is None or church_info:
        _archive_generator = ChurchArchiveGenerator(church_info)
    return _archive_generator


def create_bulletin_from_preset(church_name: str, extracted_data: Dict,
                                 title: str = "", theme: str = "default") -> str:
    """프리셋을 사용하여 주보 생성

    Args:
        church_name: 교회 이름 (예: "여의도순복음교회", "혈동교회")
        extracted_data: OCR 추출 데이터
        title: 주보 제목
        theme: 테마

    Returns:
        HTML 문자열
    """
    generator = ChurchConfigManager.create_generator(church_name)
    return generator.generate(extracted_data, title, theme)
