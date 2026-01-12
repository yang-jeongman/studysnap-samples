"""
NewsletterAI - 지자체 소식지 전용 HTML 생성기
광명소식, 서초소식 등 지자체 뉴스레터를 모바일 최적화 HTML로 변환

🤖 Powered by NewsletterAI
"""

import json
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class NewsletterHTMLGenerator:
    """
    NewsletterAI - 지자체 소식지 HTML 생성기

    BulletinAI의 자매 서비스로, 지자체 소식지를 모바일 최적화 HTML로 변환합니다.
    """

    # 카테고리 그룹핑 (유사 카테고리를 합침) - 범용
    CATEGORY_GROUPS = {
        "스마트도시": ["스마트 도시", "스마트도시", "스마트 도시 서비스", "스마트 도시 광명", "AI", "디지털", "첨단", "기술"],
        "복지": ["복지", "녹색복지", "돌봄", "장애인", "어르신", "아동", "건강", "의료", "보건", "살기 좋은"],
        "교육": ["교육", "평생교육", "시민교육", "학교", "청소년", "도서관", "학습"],
        "문화": ["문화", "행사", "축제", "공연", "예술", "관광", "체육", "스포츠"],
        "생활정보": ["생활정보", "생활", "정보", "안내", "알림", "공지", "모집", "소식"],
        "특집": ["특집", "커버", "표지", "인트로", "대표"],
        "공동체": ["공동체", "마을", "주민", "시민참여", "자원봉사", "배려", "이웃"],
        "환경": ["환경", "녹색", "친환경", "탄소중립", "에코", "재활용"],
        "경제": ["경제", "일자리", "창업", "기업", "상권", "시장"],
        "도시개발": ["도시", "개발", "건설", "교통", "주거", "인프라"],
        "시정": ["시정", "정책", "행정", "의회", "예산"],
    }

    # 지자체별 테마 색상
    CITY_THEMES = {
        "광명시": {
            "primary": "#3498db",
            "primary_dark": "#2980b9",
            "accent": "#e74c3c",
            "bg_light": "#e8f4fc",
            "gradient": "linear-gradient(135deg, #3498db 0%, #2980b9 100%)"
        },
        "서초구": {
            "primary": "#27ae60",
            "primary_dark": "#219a52",
            "accent": "#f39c12",
            "bg_light": "#e8f8f0",
            "gradient": "linear-gradient(135deg, #27ae60 0%, #219a52 100%)"
        },
        "성남시": {
            "primary": "#9b59b6",
            "primary_dark": "#8e44ad",
            "accent": "#3498db",
            "bg_light": "#f5eef8",
            "gradient": "linear-gradient(135deg, #9b59b6 0%, #8e44ad 100%)"
        },
        "수원시": {
            "primary": "#2c3e50",
            "primary_dark": "#1a252f",
            "accent": "#e74c3c",
            "bg_light": "#ecf0f1",
            "gradient": "linear-gradient(135deg, #2c3e50 0%, #3498db 100%)"
        },
        "용인시": {
            "primary": "#16a085",
            "primary_dark": "#1abc9c",
            "accent": "#f39c12",
            "bg_light": "#e8f6f3",
            "gradient": "linear-gradient(135deg, #16a085 0%, #1abc9c 100%)"
        },
        "안양시": {
            "primary": "#e67e22",
            "primary_dark": "#d35400",
            "accent": "#2980b9",
            "bg_light": "#fef5e7",
            "gradient": "linear-gradient(135deg, #e67e22 0%, #d35400 100%)"
        },
        "부천시": {
            "primary": "#8e44ad",
            "primary_dark": "#9b59b6",
            "accent": "#1abc9c",
            "bg_light": "#f5eef8",
            "gradient": "linear-gradient(135deg, #8e44ad 0%, #9b59b6 100%)"
        },
        "안산시": {
            "primary": "#2980b9",
            "primary_dark": "#3498db",
            "accent": "#e74c3c",
            "bg_light": "#ebf5fb",
            "gradient": "linear-gradient(135deg, #2980b9 0%, #3498db 100%)"
        },
        "고양시": {
            "primary": "#27ae60",
            "primary_dark": "#2ecc71",
            "accent": "#e74c3c",
            "bg_light": "#eafaf1",
            "gradient": "linear-gradient(135deg, #27ae60 0%, #2ecc71 100%)"
        },
        "default": {
            "primary": "#667eea",
            "primary_dark": "#5a67d8",
            "accent": "#ed8936",
            "bg_light": "#eef2ff",
            "gradient": "linear-gradient(135deg, #667eea 0%, #764ba2 100%)"
        }
    }

    def __init__(self, city_name: str = "default"):
        self.city_name = city_name
        self.theme = self.CITY_THEMES.get(city_name, self.CITY_THEMES["default"])

    def _normalize_category(self, raw_category: str) -> str:
        """카테고리 이름을 표준화된 그룹으로 매핑"""
        if not raw_category:
            return "기타"

        raw_lower = raw_category.lower()

        for group_name, keywords in self.CATEGORY_GROUPS.items():
            for keyword in keywords:
                if keyword.lower() in raw_lower or raw_lower in keyword.lower():
                    return group_name

        # 특수 케이스 처리
        if "똑똑" in raw_category or "안전" in raw_category:
            return "스마트도시"
        if "살기 좋은" in raw_category or "도시 정책" in raw_category:
            return "복지"
        if "캐릭터" in raw_category or "만화" in raw_category:
            return "캐릭터"

        return "기타"

    def generate(self, data: Dict[str, Any]) -> str:
        """
        소식지 HTML 생성

        Args:
            data: {
                "title": "광명소식",
                "issue": "제649호",
                "date": "2025년 10월 29일",
                "publisher": "광명시장 박승원",
                "pages": [
                    {
                        "page_num": 1,
                        "category": "특집",
                        "main_title": "새롭게 편리하게 똑똑한 광명생활",
                        "subtitle": "시민의 삶을 안전하고 편리하게 만드는 똑똑한 도시 광명",
                        "content": "...",
                        "articles": [...]
                    },
                    ...
                ]
            }
        """
        title = data.get("title", "지자체 소식지")
        issue = data.get("issue", "")
        date = data.get("date", "")
        publisher = data.get("publisher", "")
        pages = data.get("pages", [])

        html = f'''<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=3.0">
    <title>{title} {issue}</title>
    <meta name="description" content="{title} {issue} - {date}">

    <!-- Open Graph -->
    <meta property="og:type" content="article">
    <meta property="og:title" content="{title} {issue}">
    <meta property="og:description" content="{date} 발행">
    <meta property="og:image" content="{data.get('thumbnail_url', '')}">

    <!-- PWA -->
    <meta name="mobile-web-app-capable" content="yes">
    <meta name="apple-mobile-web-app-capable" content="yes">
    <meta name="theme-color" content="{self.theme['primary']}">

    {self._get_css()}
</head>
<body>
    {self._build_header(title, issue, date, publisher)}
    {self._build_nav_tabs(pages)}

    <main class="container">
        {self._build_pages_content(pages)}
    </main>

    {self._build_footer(data)}

    <!-- 원문보기 모달 -->
    <div id="originalModal" class="original-modal">
        <button class="close-btn" onclick="closeOriginalModal()">✕</button>
        <img id="originalImage" src="" alt="원문 이미지">
        <p id="pageInfo" class="page-info"></p>
    </div>

    {self._get_javascript()}
</body>
</html>'''

        return html

    def _get_css(self) -> str:
        """CSS 스타일"""
        return f'''<style>
        @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;500;600;700;800&display=swap');

        :root {{
            --primary: {self.theme['primary']};
            --primary-dark: {self.theme['primary_dark']};
            --accent: {self.theme['accent']};
            --bg-light: {self.theme['bg_light']};
            --text-dark: #1a1a2e;
            --text-gray: #6b7280;
            --bg-white: #ffffff;
            --bg-gray: #f5f5f5;
            --border: #e5e7eb;
            --shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
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
            font-family: 'Noto Sans KR', -apple-system, BlinkMacSystemFont, sans-serif;
            background: var(--bg-gray);
            color: var(--text-dark);
            line-height: 1.7;
            min-height: 100vh;
        }}

        .container {{
            max-width: 500px;
            margin: 0 auto;
            background: var(--bg-white);
            min-height: 100vh;
        }}

        /* 헤더 */
        .header {{
            background: {self.theme['gradient']};
            color: white;
            padding: 25px 20px;
            text-align: center;
            position: sticky;
            top: 0;
            z-index: 100;
            box-shadow: var(--shadow);
        }}

        .header-badge {{
            display: inline-block;
            background: rgba(255,255,255,0.2);
            padding: 5px 15px;
            border-radius: 20px;
            font-size: 0.85em;
            margin-bottom: 10px;
            backdrop-filter: blur(4px);
        }}

        .header h1 {{
            font-size: 1.8em;
            font-weight: 800;
            margin-bottom: 5px;
            text-shadow: 0 2px 4px rgba(0,0,0,0.2);
        }}

        .header .meta {{
            font-size: 0.9em;
            opacity: 0.9;
        }}

        /* 네비게이션 탭 */
        .nav-tabs {{
            display: flex;
            overflow-x: auto;
            gap: 8px;
            padding: 12px 15px;
            background: var(--bg-white);
            border-bottom: 1px solid var(--border);
            position: sticky;
            top: 95px;
            z-index: 99;
            -webkit-overflow-scrolling: touch;
        }}

        .nav-tabs::-webkit-scrollbar {{
            display: none;
        }}

        .nav-tab {{
            flex-shrink: 0;
            padding: 10px 18px;
            border: none;
            background: #f0f0f0;
            border-radius: 25px;
            font-size: 0.9em;
            font-weight: 500;
            cursor: pointer;
            transition: all 0.3s ease;
            white-space: nowrap;
        }}

        .nav-tab.active {{
            background: var(--primary);
            color: white;
            box-shadow: 0 4px 15px rgba(0,0,0,0.2);
        }}

        .nav-tab:hover:not(.active) {{
            background: #e0e0e0;
        }}

        /* 페이지 콘텐츠 */
        .page-section {{
            display: none;
            animation: fadeIn 0.3s ease;
        }}

        .page-section.active {{
            display: block;
        }}

        @keyframes fadeIn {{
            from {{ opacity: 0; transform: translateY(10px); }}
            to {{ opacity: 1; transform: translateY(0); }}
        }}

        /* 특집 섹션 */
        .feature-section {{
            padding: 0;
        }}

        .feature-hero {{
            position: relative;
            padding: 30px 20px;
            background: var(--bg-light);
            border-bottom: 4px solid var(--primary);
        }}

        .feature-category {{
            display: inline-block;
            background: var(--primary);
            color: white;
            padding: 5px 15px;
            border-radius: 20px;
            font-size: 0.85em;
            font-weight: 600;
            margin-bottom: 15px;
        }}

        .feature-hero h2 {{
            font-size: 1.6em;
            font-weight: 800;
            color: var(--text-dark);
            line-height: 1.4;
            margin-bottom: 10px;
        }}

        .feature-hero .subtitle {{
            font-size: 1em;
            color: var(--text-gray);
            line-height: 1.6;
        }}

        /* 기사 카드 */
        .article-card {{
            background: var(--bg-white);
            border-radius: 16px;
            margin: 15px;
            padding: 20px;
            box-shadow: var(--shadow);
            border: 1px solid var(--border);
            transition: transform 0.2s, box-shadow 0.2s;
        }}

        .article-card:hover {{
            transform: translateY(-2px);
            box-shadow: 0 8px 25px rgba(0,0,0,0.1);
        }}

        .article-card .category-tag {{
            display: inline-block;
            background: var(--bg-light);
            color: var(--primary);
            padding: 4px 12px;
            border-radius: 15px;
            font-size: 0.8em;
            font-weight: 600;
            margin-bottom: 10px;
        }}

        .article-card h3 {{
            font-size: 1.15em;
            font-weight: 700;
            color: var(--text-dark);
            margin-bottom: 10px;
            line-height: 1.4;
        }}

        .article-card .summary {{
            font-size: 0.95em;
            color: var(--text-gray);
            line-height: 1.7;
            margin-bottom: 15px;
        }}

        .article-card .contact-info {{
            background: #f8f9fa;
            padding: 12px;
            border-radius: 10px;
            font-size: 0.9em;
        }}

        .article-card .contact-info .phone {{
            color: var(--primary);
            font-weight: 600;
        }}

        /* 현장 취재 박스 */
        .field-report {{
            background: linear-gradient(135deg, #fff9e6 0%, #fff3cd 100%);
            border-left: 4px solid #f39c12;
            border-radius: 0 12px 12px 0;
            padding: 20px;
            margin: 15px;
        }}

        .field-report-badge {{
            display: inline-block;
            background: #f39c12;
            color: white;
            padding: 4px 12px;
            border-radius: 15px;
            font-size: 0.8em;
            font-weight: 600;
            margin-bottom: 10px;
        }}

        .field-report h4 {{
            font-size: 1.1em;
            font-weight: 700;
            color: #333;
            margin-bottom: 10px;
        }}

        .field-report p {{
            font-size: 0.95em;
            color: #555;
            line-height: 1.7;
        }}

        .field-report .reporter {{
            margin-top: 12px;
            font-size: 0.85em;
            color: #888;
            text-align: right;
        }}

        /* 인터뷰 박스 */
        .interview-box {{
            background: linear-gradient(135deg, #e8f5e9 0%, #c8e6c9 100%);
            border-left: 4px solid #27ae60;
            border-radius: 0 12px 12px 0;
            padding: 20px;
            margin: 15px;
        }}

        .interview-badge {{
            display: inline-block;
            background: #27ae60;
            color: white;
            padding: 4px 12px;
            border-radius: 15px;
            font-size: 0.8em;
            font-weight: 600;
            margin-bottom: 10px;
        }}

        .interview-box .person {{
            font-weight: 700;
            color: #333;
            margin-bottom: 10px;
        }}

        .interview-box .quote {{
            font-size: 0.95em;
            color: #555;
            line-height: 1.7;
            font-style: italic;
        }}

        /* 생활정보 섹션 */
        .info-card {{
            background: var(--bg-white);
            border-radius: 12px;
            margin: 15px;
            padding: 18px;
            border: 1px solid var(--border);
        }}

        .info-card .icon-title {{
            display: flex;
            align-items: center;
            gap: 10px;
            margin-bottom: 12px;
        }}

        .info-card .icon {{
            width: 40px;
            height: 40px;
            background: var(--bg-light);
            border-radius: 10px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 1.3em;
        }}

        .info-card h4 {{
            font-size: 1.05em;
            font-weight: 700;
            color: var(--text-dark);
        }}

        .info-card .details {{
            font-size: 0.9em;
            color: var(--text-gray);
            line-height: 1.6;
        }}

        .info-card .details p {{
            margin: 8px 0;
        }}

        .info-card .highlight {{
            color: var(--primary);
            font-weight: 600;
        }}

        /* 표 스타일 */
        .data-table {{
            width: 100%;
            border-collapse: collapse;
            margin: 15px 0;
            font-size: 0.9em;
        }}

        .data-table th {{
            background: var(--primary);
            color: white;
            padding: 12px 8px;
            text-align: center;
            font-weight: 600;
        }}

        .data-table td {{
            padding: 10px 8px;
            border-bottom: 1px solid var(--border);
            text-align: center;
        }}

        .data-table tr:nth-child(even) {{
            background: #f9f9f9;
        }}

        /* 푸터 */
        .footer {{
            background: #2c3e50;
            color: white;
            padding: 30px 20px;
            text-align: center;
        }}

        .footer .city-name {{
            font-size: 1.3em;
            font-weight: 700;
            margin-bottom: 10px;
        }}

        .footer .contact {{
            font-size: 0.9em;
            opacity: 0.8;
            line-height: 1.8;
        }}

        .footer .copyright {{
            margin-top: 20px;
            font-size: 0.8em;
            opacity: 0.6;
        }}

        .footer .powered-by {{
            margin-top: 15px;
            padding-top: 15px;
            border-top: 1px solid rgba(255,255,255,0.2);
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 10px;
        }}

        .footer .ai-badge {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 5px 12px;
            border-radius: 15px;
            font-size: 0.85em;
            font-weight: 600;
        }}

        .footer .powered-text {{
            font-size: 0.8em;
            opacity: 0.7;
        }}

        /* 공유 버튼 */
        .share-section {{
            padding: 20px;
            text-align: center;
            border-top: 1px solid var(--border);
        }}

        .share-btn {{
            display: inline-flex;
            align-items: center;
            gap: 8px;
            padding: 12px 25px;
            background: var(--primary);
            color: white;
            border: none;
            border-radius: 25px;
            font-size: 0.95em;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s;
        }}

        .share-btn:hover {{
            background: var(--primary-dark);
            transform: scale(1.02);
        }}

        /* 만화 섹션 */
        .comic-section {{
            padding: 15px;
            background: #fffbf0;
        }}

        .comic-section h3 {{
            font-size: 1.2em;
            color: var(--text-dark);
            margin-bottom: 15px;
            text-align: center;
        }}

        /* 아코디언 카드 스타일 */
        .accordion-card {{
            cursor: pointer;
            transition: all 0.3s ease;
        }}

        .accordion-card .article-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 10px;
        }}

        .accordion-card .accordion-icon {{
            font-size: 0.9em;
            color: var(--text-gray);
            transition: transform 0.3s ease;
        }}

        .accordion-card.expanded .accordion-icon {{
            transform: rotate(180deg);
        }}

        .accordion-card .preview {{
            display: block;
        }}

        .accordion-card.expanded .preview {{
            display: none;
        }}

        .accordion-card .accordion-content {{
            display: none;
            animation: slideDown 0.3s ease;
        }}

        .accordion-card.expanded .accordion-content {{
            display: block;
        }}

        @keyframes slideDown {{
            from {{ opacity: 0; max-height: 0; }}
            to {{ opacity: 1; max-height: 1000px; }}
        }}

        .accordion-card .article-subtitle {{
            font-size: 0.95em;
            color: var(--primary);
            font-weight: 500;
            margin-bottom: 8px;
        }}

        .accordion-card .full {{
            white-space: pre-line;
            line-height: 1.8;
        }}

        /* 원문보기 버튼 */
        .view-original-btn {{
            background: transparent;
            border: 1px solid var(--primary);
            color: var(--primary);
            padding: 6px 14px;
            border-radius: 20px;
            font-size: 0.8em;
            font-weight: 500;
            cursor: pointer;
            transition: all 0.3s ease;
        }}

        .view-original-btn:hover {{
            background: var(--primary);
            color: white;
        }}

        .hero-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 15px;
            flex-wrap: wrap;
            gap: 10px;
        }}

        /* 페이지 구분선 */
        .page-divider {{
            height: 8px;
            background: linear-gradient(90deg, var(--primary) 0%, var(--accent) 100%);
            margin: 0;
            opacity: 0.3;
        }}

        /* 원문 이미지 모달 */
        .original-modal {{
            display: none;
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0,0,0,0.9);
            z-index: 10000;
            overflow: auto;
            animation: fadeInModal 0.3s ease;
        }}

        .original-modal.active {{
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: flex-start;
            padding: 20px;
        }}

        @keyframes fadeInModal {{
            from {{ opacity: 0; }}
            to {{ opacity: 1; }}
        }}

        .original-modal .close-btn {{
            position: fixed;
            top: 15px;
            right: 15px;
            background: rgba(255,255,255,0.9);
            border: none;
            width: 45px;
            height: 45px;
            border-radius: 50%;
            font-size: 1.5em;
            cursor: pointer;
            z-index: 10001;
            box-shadow: 0 2px 10px rgba(0,0,0,0.3);
        }}

        .original-modal img {{
            max-width: 100%;
            max-height: 90vh;
            object-fit: contain;
            border-radius: 8px;
            margin-top: 50px;
        }}

        .original-modal .page-info {{
            color: white;
            font-size: 1.1em;
            margin-top: 15px;
            text-align: center;
        }}

        /* 반응형 */
        @media (max-width: 400px) {{
            .header h1 {{
                font-size: 1.5em;
            }}

            .feature-hero h2 {{
                font-size: 1.4em;
            }}

            .article-card {{
                margin: 10px;
                padding: 15px;
            }}

            .nav-tab {{
                padding: 8px 14px;
                font-size: 0.85em;
            }}
        }}
        </style>'''

    def _build_header(self, title: str, issue: str, date: str, publisher: str) -> str:
        """헤더 생성"""
        return f'''
        <header class="header">
            <div class="header-badge">{issue}</div>
            <h1>{title}</h1>
            <p class="meta">{date} | 발행인 {publisher}</p>
        </header>'''

    def _build_nav_tabs(self, pages: List[Dict]) -> str:
        """네비게이션 탭 생성 (표준화된 카테고리로 그룹핑)"""
        tabs = []

        # 표준화된 카테고리 순서
        category_order = ["특집", "스마트도시", "복지", "교육", "공동체", "생활정보", "문화", "캐릭터", "기타"]

        # 실제 사용되는 카테고리만 추출
        used_categories = []
        for page in pages:
            raw_cat = page.get("category", "기타")
            normalized = self._normalize_category(raw_cat)
            if normalized not in used_categories:
                used_categories.append(normalized)

        # 정렬된 카테고리 목록
        sorted_categories = [cat for cat in category_order if cat in used_categories]

        for i, cat in enumerate(sorted_categories):
            active = "active" if i == 0 else ""
            # 카테고리 아이콘 추가
            icon = self._get_category_icon(cat)
            tabs.append(f'<button class="nav-tab {active}" data-tab="tab-{i}">{icon} {cat}</button>')

        return f'''
        <nav class="nav-tabs">
            {''.join(tabs)}
        </nav>'''

    def _get_category_icon(self, category: str) -> str:
        """카테고리별 아이콘"""
        icons = {
            "특집": "⭐",
            "스마트도시": "🏙️",
            "복지": "💚",
            "교육": "📚",
            "공동체": "🤝",
            "생활정보": "📋",
            "문화": "🎭",
            "캐릭터": "🎨",
            "기타": "📌"
        }
        return icons.get(category, "📌")

    def _build_pages_content(self, pages: List[Dict]) -> str:
        """페이지 콘텐츠 생성 (표준화된 카테고리로 그룹핑)"""
        content = []

        # 표준화된 카테고리 순서
        category_order = ["특집", "스마트도시", "복지", "교육", "공동체", "생활정보", "문화", "캐릭터", "기타"]

        # 카테고리별로 그룹화 (표준화된 이름 사용)
        categories = {}
        for page in pages:
            raw_cat = page.get("category", "기타")
            normalized = self._normalize_category(raw_cat)
            if normalized not in categories:
                categories[normalized] = []
            # 원본 카테고리도 보존
            page["original_category"] = raw_cat
            categories[normalized].append(page)

        # 정렬된 순서로 섹션 생성
        sorted_categories = [cat for cat in category_order if cat in categories]

        for i, cat in enumerate(sorted_categories):
            active = "active" if i == 0 else ""
            cat_pages = categories[cat]
            section_content = []

            for page in cat_pages:
                section_content.append(self._build_page_content(page))

            content.append(f'''
            <section class="page-section {active}" id="tab-{i}">
                {''.join(section_content)}
            </section>''')

        return ''.join(content)

    def _build_page_content(self, page: Dict) -> str:
        """개별 페이지 콘텐츠 생성 (아코디언 형식)"""
        page_num = page.get("page_num", 0)
        main_title = page.get("main_title", "")
        page_title = page.get("page_title", "")  # 페이지 제목
        page_desc = page.get("page_desc", "")    # 페이지 설명
        subtitle = page.get("subtitle", "")
        category = page.get("category", "")
        articles = page.get("articles", [])
        field_reports = page.get("field_reports", [])
        interviews = page.get("interviews", [])
        info_items = page.get("info_items", [])

        html_parts = []

        # 페이지 구분선 (첫 페이지 제외)
        if page_num > 1:
            html_parts.append('<div class="page-divider"></div>')

        # 페이지 제목 사용 (page_title 우선, 없으면 main_title)
        display_title = page_title or main_title
        display_desc = page_desc or subtitle

        # 특집 히어로 (메인 타이틀이 있는 경우)
        if display_title:
            # 원문보기 버튼
            view_original_btn = f'''
                <button class="view-original-btn" onclick="showOriginalPage({page_num})">
                    📄 {page_num}p 원문보기
                </button>''' if page_num > 0 else ''

            html_parts.append(f'''
            <div class="feature-hero">
                <div class="hero-header">
                    <span class="feature-category">{category}</span>
                    {view_original_btn}
                </div>
                <h2>{display_title}</h2>
                <p class="subtitle">{display_desc}</p>
            </div>''')

        # 기사 카드들
        for article in articles:
            html_parts.append(self._build_article_card(article))

        # 현장 취재
        for report in field_reports:
            html_parts.append(self._build_field_report(report))

        # 인터뷰
        for interview in interviews:
            html_parts.append(self._build_interview(interview))

        # 생활정보
        for info in info_items:
            html_parts.append(self._build_info_card(info))

        return ''.join(html_parts)

    def _build_article_card(self, article: Dict) -> str:
        """기사 카드 생성 (아코디언 형식)"""
        title = article.get("title", "")
        subtitle = article.get("subtitle", "")
        category = article.get("category", "")
        summary = article.get("summary", "")
        contact = article.get("contact", "")

        # 제목에서 "기사1:", "기사2:" 등 형식적 텍스트 제거
        if title.startswith("기사") and ":" in title[:6]:
            title = title.split(":", 1)[1].strip() if ":" in title else title

        # 연락처 HTML
        contact_html = ""
        if contact:
            contact_html = f'''
            <div class="contact-info">
                <span class="phone">📞 {contact}</span>
            </div>'''

        # 소제목 HTML
        subtitle_html = f'<p class="article-subtitle">{subtitle}</p>' if subtitle else ''

        # 긴 내용은 아코디언으로
        if len(summary) > 150:
            preview = summary[:100] + "..."
            return f'''
        <article class="article-card accordion-card" onclick="toggleAccordion(this)">
            <div class="article-header">
                <span class="category-tag">{category}</span>
                <span class="accordion-icon">▼</span>
            </div>
            <h3>{title}</h3>
            {subtitle_html}
            <p class="summary preview">{preview}</p>
            <div class="accordion-content">
                <p class="summary full">{summary}</p>
                {contact_html}
            </div>
        </article>'''
        else:
            return f'''
        <article class="article-card">
            <span class="category-tag">{category}</span>
            <h3>{title}</h3>
            {subtitle_html}
            <p class="summary">{summary}</p>
            {contact_html}
        </article>'''

    def _build_field_report(self, report: Dict) -> str:
        """현장 취재 박스 생성"""
        title = report.get("title", "")
        content = report.get("content", "")
        reporter = report.get("reporter", "")

        return f'''
        <div class="field-report">
            <span class="field-report-badge">현장취재</span>
            <h4>{title}</h4>
            <p>{content}</p>
            <p class="reporter">글 {reporter}</p>
        </div>'''

    def _build_interview(self, interview: Dict) -> str:
        """인터뷰 박스 생성"""
        person = interview.get("person", "")
        title = interview.get("title", "")
        quote = interview.get("quote", "")

        return f'''
        <div class="interview-box">
            <span class="interview-badge">인터뷰</span>
            <p class="person">{person} {title}</p>
            <p class="quote">"{quote}"</p>
        </div>'''

    def _build_info_card(self, info: Dict) -> str:
        """생활정보 카드 생성"""
        icon = info.get("icon", "📌")
        title = info.get("title", "")
        details = info.get("details", [])

        details_html = ""
        for detail in details:
            details_html += f"<p>{detail}</p>"

        return f'''
        <div class="info-card">
            <div class="icon-title">
                <span class="icon">{icon}</span>
                <h4>{title}</h4>
            </div>
            <div class="details">
                {details_html}
            </div>
        </div>'''

    def _build_footer(self, data: Dict) -> str:
        """푸터 생성"""
        city = data.get("city", self.city_name)
        contact = data.get("contact", {})
        phone = contact.get("phone", "")
        email = contact.get("email", "")
        website = contact.get("website", "")

        return f'''
        <section class="share-section">
            <button class="share-btn" onclick="shareNewsletter()">
                �� 이 소식지 공유하기
            </button>
        </section>

        <footer class="footer">
            <p class="city-name">{city}</p>
            <div class="contact">
                {f"<p>📞 {phone}</p>" if phone else ""}
                {f"<p>📧 {email}</p>" if email else ""}
                {f"<p>🌐 {website}</p>" if website else ""}
            </div>
            <p class="copyright">© {datetime.now().year} {city}. All rights reserved.</p>
            <div class="powered-by">
                <span class="ai-badge">🤖 NewsletterAI</span>
                <span class="powered-text">Powered by StudySnap</span>
            </div>
        </footer>'''

    def _get_javascript(self) -> str:
        """JavaScript 생성"""
        return '''
        <script>
        // 탭 전환
        document.querySelectorAll('.nav-tab').forEach(tab => {
            tab.addEventListener('click', function() {
                // 탭 활성화
                document.querySelectorAll('.nav-tab').forEach(t => t.classList.remove('active'));
                this.classList.add('active');

                // 콘텐츠 전환
                const tabId = this.dataset.tab;
                document.querySelectorAll('.page-section').forEach(section => {
                    section.classList.remove('active');
                });
                document.getElementById(tabId).classList.add('active');
            });
        });

        // 아코디언 토글
        function toggleAccordion(element) {
            element.classList.toggle('expanded');
        }

        // 원문보기 모달
        const PAGE_IMAGES = {}; // 페이지 이미지 경로 (convert_newsletter.py에서 설정)

        function showOriginalPage(pageNum) {
            const modal = document.getElementById('originalModal');
            const img = document.getElementById('originalImage');
            const pageInfo = document.getElementById('pageInfo');

            // 키가 문자열 또는 숫자일 수 있으므로 둘 다 체크
            const imagePath = PAGE_IMAGES[pageNum] || PAGE_IMAGES[String(pageNum)];
            if (imagePath) {
                img.src = imagePath;
                pageInfo.textContent = `${pageNum}페이지 원문`;
                modal.classList.add('active');
                document.body.style.overflow = 'hidden';
            } else {
                alert(`${pageNum}페이지 원문 이미지가 준비되지 않았습니다.`);
            }
        }

        function closeOriginalModal() {
            const modal = document.getElementById('originalModal');
            modal.classList.remove('active');
            document.body.style.overflow = '';
        }

        // 모달 배경 클릭 시 닫기
        document.addEventListener('DOMContentLoaded', function() {
            const modal = document.getElementById('originalModal');
            if (modal) {
                modal.addEventListener('click', function(e) {
                    if (e.target === modal) {
                        closeOriginalModal();
                    }
                });
            }
        });

        // ESC 키로 모달 닫기
        document.addEventListener('keydown', function(e) {
            if (e.key === 'Escape') {
                closeOriginalModal();
            }
        });

        // 공유 기능
        function shareNewsletter() {
            if (navigator.share) {
                navigator.share({
                    title: document.title,
                    text: document.querySelector('.header h1').textContent,
                    url: window.location.href
                }).catch(err => console.log('공유 취소됨'));
            } else {
                // 클립보드 복사
                navigator.clipboard.writeText(window.location.href).then(() => {
                    alert('링크가 클립보드에 복사되었습니다!');
                });
            }
        }
        </script>'''


# 테스트
if __name__ == "__main__":
    generator = NewsletterHTMLGenerator("광명시")

    test_data = {
        "title": "광명소식",
        "issue": "제649호",
        "date": "2025년 10월 29일",
        "publisher": "광명시장 박승원",
        "city": "광명시",
        "contact": {
            "phone": "02-2680-2062",
            "email": "gmgongbo@korea.kr",
            "website": "www.gm.go.kr"
        },
        "pages": [
            {
                "page_num": 1,
                "category": "특집",
                "main_title": "새롭게 편리하게 똑똑한 광명생활",
                "subtitle": "시민의 삶을 안전하고 편리하게 만드는 똑똑한 도시 광명",
                "articles": [
                    {
                        "title": "전기차 기반 커뮤니티 카셰어링",
                        "category": "스마트 도시",
                        "summary": "광명시는 시청 지하주차장을 운영 거점으로, 2022년부터 전기 관용차량을 활용한 카셰어링을 도입했습니다.",
                        "contact": "AI스마트도시과 02-2680-5576"
                    }
                ]
            }
        ]
    }

    html = generator.generate(test_data)
    print("HTML 생성 완료!")
    print(f"길이: {len(html)} 글자")
