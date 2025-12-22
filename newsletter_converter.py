# -*- coding: utf-8 -*-
"""
정당/단체 소식지 PDF → 모바일 HTML 변환기
API 없이 PyMuPDF만으로 텍스트/이미지 추출
"""

import fitz
import os
import re
import base64
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple

class NewsletterConverter:
    """소식지 PDF를 모바일 최적화 HTML로 변환"""

    # 정당별 테마 색상
    PARTY_THEMES = {
        "진보당": {
            "primary": "#E53935",  # 빨강
            "primary_dark": "#B71C1C",
            "primary_light": "#FFEBEE",
            "accent": "#FF5722",
            "text": "#212121"
        },
        "더불어민주당": {
            "primary": "#1565C0",
            "primary_dark": "#0D47A1",
            "primary_light": "#E3F2FD",
            "accent": "#2196F3",
            "text": "#212121"
        },
        "국민의힘": {
            "primary": "#D32F2F",
            "primary_dark": "#B71C1C",
            "primary_light": "#FFEBEE",
            "accent": "#F44336",
            "text": "#212121"
        },
        "default": {
            "primary": "#6200EA",
            "primary_dark": "#4A148C",
            "primary_light": "#F3E5F5",
            "accent": "#7C4DFF",
            "text": "#212121"
        }
    }

    def __init__(self, pdf_path: str):
        self.pdf_path = pdf_path
        self.doc = fitz.open(pdf_path)
        self.pages_data = []
        self.toc = []  # 목차
        self.metadata = {}
        self.images = []

    def extract_all(self) -> Dict:
        """PDF에서 모든 데이터 추출"""
        # 메타데이터 추출
        self._extract_metadata()

        # 페이지별 텍스트 및 이미지 추출
        for page_num in range(self.doc.page_count):
            page = self.doc[page_num]
            page_data = {
                "page_num": page_num + 1,
                "text": page.get_text(),
                "images": self._extract_page_images(page, page_num)
            }
            self.pages_data.append(page_data)

        # 첫 페이지에서 목차 추출
        self._extract_toc()

        # 기사별 파싱
        articles = self._parse_articles()

        return {
            "metadata": self.metadata,
            "toc": self.toc,
            "articles": articles,
            "pages": self.pages_data
        }

    def _extract_metadata(self):
        """PDF 메타데이터 및 첫 페이지에서 정보 추출"""
        first_page_text = self.doc[0].get_text()

        # 발행 정보 추출
        self.metadata = {
            "title": "",
            "issue": "",
            "date": "",
            "publisher": "",
            "editor": "",
            "party": "",
            "total_pages": self.doc.page_count
        }

        # 제목 추출 (예: 기관지 '너머')
        title_match = re.search(r"기관지\s*['''\"]?([가-힣]+)['''\"]?", first_page_text)
        if title_match:
            self.metadata["title"] = title_match.group(1)

        # 호수 추출 (예: 통권 55호)
        issue_match = re.search(r"통권\s*(\d+)\s*호", first_page_text)
        if issue_match:
            self.metadata["issue"] = issue_match.group(1) + "호"

        # 날짜 추출 (예: 2025년 12월호)
        date_match = re.search(r"(\d{4})년\s*(\d{1,2})월", first_page_text)
        if date_match:
            self.metadata["date"] = f"{date_match.group(1)}년 {date_match.group(2)}월"

        # 발행인/편집장 추출
        publisher_match = re.search(r"발행인\s*[:\s]*([가-힣]+)", first_page_text)
        if publisher_match:
            self.metadata["publisher"] = publisher_match.group(1)

        editor_match = re.search(r"편집장\s*[:\s]*([가-힣]+)", first_page_text)
        if editor_match:
            self.metadata["editor"] = editor_match.group(1)

        # 정당명 추출
        if "진보당" in first_page_text:
            self.metadata["party"] = "진보당"
        elif "민주당" in first_page_text or "더불어" in first_page_text:
            self.metadata["party"] = "더불어민주당"
        elif "국민의힘" in first_page_text:
            self.metadata["party"] = "국민의힘"

    def _extract_page_images(self, page, page_num: int) -> List[Dict]:
        """페이지에서 이미지 추출 (base64)"""
        images = []
        image_list = page.get_images()

        for img_idx, img in enumerate(image_list):
            try:
                xref = img[0]
                base_image = self.doc.extract_image(xref)
                image_bytes = base_image["image"]
                image_ext = base_image["ext"]

                # Base64 인코딩
                b64_image = base64.b64encode(image_bytes).decode('utf-8')

                images.append({
                    "index": img_idx,
                    "page": page_num + 1,
                    "ext": image_ext,
                    "data": f"data:image/{image_ext};base64,{b64_image}"
                })
            except Exception as e:
                pass  # 이미지 추출 실패 시 무시

        return images

    def _extract_toc(self):
        """첫 페이지에서 목차 추출"""
        if not self.pages_data:
            return

        first_page_text = self.pages_data[0]["text"]

        # 목차 패턴: 페이지번호•섹션명 (예: 7•원내 소식)
        toc_pattern = r"(\d+)\s*[•·]\s*([가-힣\s]+)"
        matches = re.findall(toc_pattern, first_page_text)

        for match in matches:
            page_num = int(match[0])
            section_title = match[1].strip()
            if section_title and len(section_title) > 1:
                self.toc.append({
                    "page": page_num,
                    "title": section_title
                })

        # 기사 제목 패턴도 추출 (줄바꿈 후 제목)
        article_patterns = [
            r"(\d+)[•·]([가-힣\s]+)\n([^\n]+)",
        ]

    def _parse_articles(self) -> List[Dict]:
        """페이지별 기사 파싱"""
        articles = []

        for i, page_data in enumerate(self.pages_data):
            text = page_data["text"]
            page_num = page_data["page_num"]

            # 첫 페이지는 표지/목차
            if page_num == 1:
                continue

            # 기사 구조 파싱
            article = {
                "page": page_num,
                "category": "",
                "title": "",
                "subtitle": "",
                "content": text,
                "images": page_data["images"]
            }

            # 카테고리 추출 (인터뷰, 기획, 정책 등)
            category_match = re.search(r"^(인터뷰|기획|정책|지방선거|평등너머|진보당\s*소식|원내\s*소식)", text, re.MULTILINE)
            if category_match:
                article["category"] = category_match.group(1)

            # 제목 추출 (큰 글씨 - 보통 줄 시작)
            lines = text.split('\n')
            for j, line in enumerate(lines[:10]):
                line = line.strip()
                if len(line) > 5 and len(line) < 50 and not re.match(r"^\d+$", line):
                    # 숫자만 있는 줄 제외
                    if article["category"] and article["category"] in line:
                        continue
                    article["title"] = line
                    break

            articles.append(article)

        return articles

    def generate_html(self, output_path: str = None, party: str = None) -> str:
        """모바일 최적화 HTML 생성"""
        data = self.extract_all()

        # 테마 선택 (파라미터 우선, 없으면 메타데이터에서)
        party_name = party or data["metadata"].get("party", "default")
        data["metadata"]["party"] = party_name
        theme = self.PARTY_THEMES.get(party_name, self.PARTY_THEMES["default"])

        # HTML 생성
        html = self._build_html(data, theme)

        # 저장
        if output_path:
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(html)

        return html

    def _parse_articles_by_category(self, pages: List[Dict]) -> List[Dict]:
        """페이지들을 카테고리/기사 단위로 파싱"""
        articles = []
        current_article = None

        # 카테고리 키워드
        category_keywords = [
            "인터뷰", "기획", "정책", "지방선거", "평등너머", "진보당 소식",
            "원내 소식", "가로 세로 퀴즈", "국가보안법"
        ]

        for page_data in pages:
            page_num = page_data["page_num"]
            text = page_data["text"]
            images = page_data["images"]

            # 첫 페이지는 표지로 별도 처리
            if page_num == 1:
                articles.append({
                    "id": "cover",
                    "category": "표지",
                    "title": "표지 · 목차",
                    "page": 1,
                    "content": text,
                    "images": images,
                    "is_cover": True
                })
                continue

            # 카테고리/제목 추출
            lines = [l.strip() for l in text.split('\n') if l.strip()]
            category = ""
            title = ""
            subtitle = ""

            # 첫 몇 줄에서 카테고리와 제목 찾기
            for i, line in enumerate(lines[:15]):
                # 카테고리 매칭
                for kw in category_keywords:
                    if kw in line and len(line) < 30:
                        category = kw
                        break

                # 제목 추출 (카테고리 다음 줄 또는 긴 텍스트)
                if not title and len(line) > 5 and len(line) < 60:
                    # 페이지 번호나 카테고리가 아닌 경우
                    if not re.match(r'^\d+$', line) and line not in category_keywords:
                        if category and i > 0:
                            title = line
                        elif not category and len(line) > 10:
                            title = line

            # 제목이 없으면 기본값
            if not title:
                title = f"{page_num}페이지"

            # 본문 추출 (제목 이후)
            content_lines = []
            title_found = False
            for line in lines:
                if title in line:
                    title_found = True
                    continue
                if title_found:
                    content_lines.append(line)

            content = '\n'.join(content_lines) if content_lines else text

            articles.append({
                "id": f"article-{page_num}",
                "category": category or "소식",
                "title": title,
                "page": page_num,
                "content": content,
                "images": images,
                "is_cover": False
            })

        return articles

    def _build_html(self, data: Dict, theme: Dict) -> str:
        """HTML 템플릿 빌드 - 아코디언 방식"""
        metadata = data["metadata"]
        toc = data["toc"]
        pages = data["pages"]

        # 기사 파싱
        articles = self._parse_articles_by_category(pages)

        # 카테고리별 그룹핑
        categories = {}
        for article in articles:
            cat = article["category"]
            if cat not in categories:
                categories[cat] = []
            categories[cat].append(article)

        # 목차 HTML (아코디언 링크)
        toc_html = ""
        for item in toc:
            toc_html += f'''
            <a href="javascript:void(0)" class="toc-item" onclick="openArticle('article-{item['page']}')">
                <span class="toc-title">{item['title']}</span>
                <span class="toc-page">{item['page']}p</span>
            </a>'''

        # 아코디언 아이템 HTML 생성
        accordion_html = ""
        for article in articles:
            # 본문을 단락으로 분리 (빈 줄 또는 줄바꿈 기준)
            # 먼저 연속 줄바꿈을 단락 구분자로, 단일 줄바꿈은 문장 구분으로
            raw_text = article["content"]

            # 빈 줄(2개 이상 줄바꿈)로 큰 단락 분리
            big_paragraphs = re.split(r'\n\s*\n', raw_text)
            content_html = ""

            for big_para in big_paragraphs:
                big_para = big_para.strip()
                if not big_para:
                    continue

                # 각 큰 단락 내에서 줄바꿈으로 문장 분리
                lines = [l.strip() for l in big_para.split('\n') if l.strip()]

                for line in lines:
                    if len(line) < 3:
                        continue
                    # 소제목 감지 (짧고 특정 패턴)
                    if len(line) < 60 and (line.startswith('▶') or line.startswith('■') or line.startswith('●') or line.startswith('◆') or re.match(r'^\d+[\.\)]', line) or re.match(r'^[가-힣]{2,6}\s*:', line)):
                        content_html += f'<h4 class="content-subhead">{line}</h4>'
                    # 인용문 감지 (따옴표로 시작)
                    elif line.startswith('"') or line.startswith('"') or line.startswith('「'):
                        content_html += f'<blockquote class="content-quote">{line}</blockquote>'
                    else:
                        content_html += f'<p>{line}</p>'

            # 이미지 HTML
            images_html = ""
            for img in article["images"][:3]:
                images_html += f'<img src="{img["data"]}" class="article-image" loading="lazy">'

            # 카테고리 배지 색상
            cat_colors = {
                "인터뷰": "#E53935", "기획": "#1E88E5", "정책": "#43A047",
                "지방선거": "#FB8C00", "평등너머": "#8E24AA", "진보당 소식": "#D81B60",
                "원내 소식": "#00ACC1", "표지": "#546E7A", "소식": "#78909C"
            }
            cat_color = cat_colors.get(article["category"], theme["primary"])

            accordion_html += f'''
            <div class="accordion-item" id="{article['id']}">
                <div class="accordion-header" onclick="toggleAccordion('{article['id']}')">
                    <div class="accordion-header-content">
                        <span class="category-badge" style="background:{cat_color}">{article['category']}</span>
                        <span class="accordion-title">{article['title']}</span>
                    </div>
                    <div class="accordion-meta">
                        <span class="page-badge">{article['page']}p</span>
                        <span class="accordion-icon">▼</span>
                    </div>
                </div>
                <div class="accordion-body">
                    {images_html}
                    <div class="accordion-content">
                        {content_html}
                    </div>
                </div>
            </div>'''

        html = f'''<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>{metadata.get("title", "소식지")} {metadata.get("issue", "")}</title>
    <style>
        :root {{
            --primary: {theme["primary"]};
            --primary-dark: {theme["primary_dark"]};
            --primary-light: {theme["primary_light"]};
            --accent: {theme["accent"]};
            --text: {theme["text"]};
            --bg: #F5F5F5;
            --card-bg: #FFFFFF;
            --shadow: 0 2px 12px rgba(0,0,0,0.08);
        }}

        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}

        body {{
            font-family: 'Pretendard', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            background: var(--bg);
            color: var(--text);
            line-height: 1.8;
            font-size: 16px;
            -webkit-font-smoothing: antialiased;
        }}

        /* 헤더 */
        .header {{
            background: linear-gradient(135deg, var(--primary), var(--primary-dark));
            color: white;
            padding: 20px 16px;
            position: sticky;
            top: 0;
            z-index: 100;
            box-shadow: 0 4px 20px rgba(0,0,0,0.15);
        }}

        .header-content {{
            max-width: 600px;
            margin: 0 auto;
            text-align: center;
        }}

        .newsletter-title {{
            font-size: 32px;
            font-weight: 800;
            margin-bottom: 4px;
            letter-spacing: -1px;
        }}

        .newsletter-issue {{
            font-size: 14px;
            opacity: 0.9;
        }}

        .newsletter-meta {{
            margin-top: 8px;
            font-size: 11px;
            opacity: 0.7;
        }}

        /* 컨테이너 */
        .container {{
            max-width: 600px;
            margin: 0 auto;
            padding: 12px;
        }}

        /* 목차 (접이식) */
        .toc-section {{
            background: var(--card-bg);
            margin-bottom: 12px;
            border-radius: 16px;
            overflow: hidden;
            box-shadow: var(--shadow);
        }}

        .toc-header {{
            padding: 16px 20px;
            font-size: 16px;
            font-weight: 700;
            color: var(--primary);
            display: flex;
            align-items: center;
            justify-content: space-between;
            cursor: pointer;
            background: var(--primary-light);
        }}

        .toc-header:active {{
            opacity: 0.8;
        }}

        .toc-body {{
            max-height: 0;
            overflow: hidden;
            transition: max-height 0.3s ease;
        }}

        .toc-body.open {{
            max-height: 500px;
        }}

        .toc-item {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 14px 20px;
            border-bottom: 1px solid #f0f0f0;
            text-decoration: none;
            color: var(--text);
            transition: all 0.2s;
        }}

        .toc-item:last-child {{
            border-bottom: none;
        }}

        .toc-item:active {{
            background: var(--primary-light);
        }}

        .toc-title {{
            font-weight: 500;
            font-size: 14px;
        }}

        .toc-page {{
            color: var(--primary);
            font-weight: 700;
            font-size: 13px;
            background: var(--primary-light);
            padding: 2px 8px;
            border-radius: 10px;
        }}

        /* 아코디언 */
        .accordion-item {{
            background: var(--card-bg);
            margin-bottom: 8px;
            border-radius: 16px;
            overflow: hidden;
            box-shadow: var(--shadow);
        }}

        .accordion-header {{
            padding: 16px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            cursor: pointer;
            transition: all 0.2s;
            gap: 12px;
        }}

        .accordion-header:active {{
            background: #f8f8f8;
        }}

        .accordion-header-content {{
            display: flex;
            align-items: center;
            gap: 10px;
            flex: 1;
            min-width: 0;
        }}

        .category-badge {{
            padding: 4px 10px;
            border-radius: 12px;
            font-size: 11px;
            font-weight: 700;
            color: white;
            white-space: nowrap;
            flex-shrink: 0;
        }}

        .accordion-title {{
            font-size: 15px;
            font-weight: 600;
            color: var(--text);
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
        }}

        .accordion-meta {{
            display: flex;
            align-items: center;
            gap: 8px;
            flex-shrink: 0;
        }}

        .page-badge {{
            font-size: 11px;
            color: #999;
            background: #f0f0f0;
            padding: 2px 6px;
            border-radius: 8px;
        }}

        .accordion-icon {{
            font-size: 12px;
            color: #999;
            transition: transform 0.3s ease;
        }}

        .accordion-item.open .accordion-icon {{
            transform: rotate(180deg);
        }}

        .accordion-body {{
            max-height: 0;
            overflow: hidden;
            transition: max-height 0.4s ease;
        }}

        .accordion-item.open .accordion-body {{
            max-height: 5000px;
        }}

        .accordion-content {{
            padding: 0 20px 20px 20px;
            border-top: 1px solid #f0f0f0;
        }}

        .accordion-content p {{
            margin: 14px 0;
            text-align: justify;
            word-break: keep-all;
            font-size: 15px;
            color: #444;
            line-height: 1.9;
            text-indent: 0.5em;
            padding: 4px 0;
        }}

        .accordion-content p + p {{
            margin-top: 12px;
        }}

        .content-subhead {{
            margin-top: 24px;
            margin-bottom: 12px;
            font-size: 16px;
            font-weight: 700;
            color: var(--primary-dark);
            padding: 10px 12px;
            background: var(--primary-light);
            border-left: 4px solid var(--primary);
            border-radius: 0 8px 8px 0;
        }}

        .content-quote {{
            margin: 16px 0;
            padding: 16px 20px;
            background: linear-gradient(135deg, #f8f9fa 0%, #fff 100%);
            border-left: 4px solid var(--accent);
            border-radius: 0 12px 12px 0;
            font-style: italic;
            font-size: 15px;
            line-height: 1.8;
            color: #555;
        }}

        .accordion-content > *:first-child {{
            margin-top: 16px;
        }}

        .article-image {{
            width: 100%;
            border-radius: 12px;
            margin-top: 16px;
        }}

        /* 네비게이션 */
        .bottom-nav {{
            position: fixed;
            bottom: 0;
            left: 0;
            right: 0;
            background: var(--card-bg);
            border-top: 1px solid #eee;
            padding: 10px 16px;
            padding-bottom: calc(10px + env(safe-area-inset-bottom));
            display: flex;
            justify-content: space-around;
            z-index: 100;
            box-shadow: 0 -2px 10px rgba(0,0,0,0.05);
        }}

        .nav-btn {{
            background: none;
            border: none;
            font-size: 22px;
            color: var(--primary);
            cursor: pointer;
            padding: 8px 20px;
            border-radius: 12px;
            transition: all 0.2s;
        }}

        .nav-btn:active {{
            background: var(--primary-light);
            transform: scale(0.95);
        }}

        /* 다크모드 */
        .dark-mode {{
            --bg: #121212;
            --card-bg: #1E1E1E;
            --text: #E0E0E0;
        }}

        .dark-mode .accordion-content p {{
            color: #bbb;
        }}

        .dark-mode .accordion-header:active {{
            background: #2a2a2a;
        }}

        .dark-mode .toc-item {{
            border-color: #333;
        }}

        .dark-mode .page-badge {{
            background: #333;
            color: #aaa;
        }}

        .dark-mode .content-subhead {{
            background: rgba(229, 57, 53, 0.15);
            color: #ff8a80;
        }}

        .dark-mode .content-quote {{
            background: rgba(255, 255, 255, 0.05);
            color: #ccc;
            border-left-color: var(--accent);
        }}

        /* 푸터 여백 */
        .footer-spacer {{
            height: 80px;
        }}

        /* 스크롤 부드럽게 */
        html {{
            scroll-behavior: smooth;
        }}

        /* 현재 열린 아이템 강조 */
        .accordion-item.open .accordion-header {{
            background: var(--primary-light);
        }}

        .accordion-item.open .accordion-title {{
            color: var(--primary-dark);
        }}
    </style>
</head>
<body>
    <!-- 헤더 -->
    <header class="header">
        <div class="header-content">
            <div class="newsletter-title">{metadata.get("title", "소식지")}</div>
            <div class="newsletter-issue">통권 {metadata.get("issue", "")} · {metadata.get("date", "")}</div>
            <div class="newsletter-meta">
                발행: {metadata.get("publisher", "")} | 편집: {metadata.get("editor", "")}
            </div>
        </div>
    </header>

    <div class="container">
        <!-- 목차 (접이식) -->
        <nav class="toc-section">
            <div class="toc-header" onclick="toggleToc()">
                <span>📑 목차</span>
                <span class="toc-toggle">▼</span>
            </div>
            <div class="toc-body" id="tocBody">
                {toc_html}
            </div>
        </nav>

        <!-- 아코디언 기사 목록 -->
        {accordion_html}
    </div>

    <!-- 푸터 여백 -->
    <div class="footer-spacer"></div>

    <!-- 하단 네비게이션 -->
    <nav class="bottom-nav">
        <button class="nav-btn" onclick="window.scrollTo({{top:0, behavior:'smooth'}})" title="맨 위로">⬆️</button>
        <button class="nav-btn" onclick="collapseAll()" title="모두 접기">📑</button>
        <button class="nav-btn" onclick="toggleDarkMode()" title="다크모드">🌙</button>
        <button class="nav-btn" onclick="shareNewsletter()" title="공유">📤</button>
    </nav>

    <script>
        // 현재 열린 아코디언 ID
        let currentOpenId = null;

        // 아코디언 토글 (하나만 열림)
        function toggleAccordion(id) {{
            const item = document.getElementById(id);
            const isOpen = item.classList.contains('open');

            // 모든 아코디언 닫기
            document.querySelectorAll('.accordion-item.open').forEach(el => {{
                el.classList.remove('open');
            }});

            // 클릭한 아이템이 닫혀있었으면 열기
            if (!isOpen) {{
                item.classList.add('open');
                currentOpenId = id;

                // 스크롤하여 화면에 보이게
                setTimeout(() => {{
                    item.scrollIntoView({{ behavior: 'smooth', block: 'start' }});
                }}, 100);
            }} else {{
                currentOpenId = null;
            }}
        }}

        // 특정 기사 열기 (목차에서 클릭)
        function openArticle(id) {{
            // 목차 닫기
            document.getElementById('tocBody').classList.remove('open');

            // 아코디언 열기
            toggleAccordion(id);
        }}

        // 모든 아코디언 닫기
        function collapseAll() {{
            document.querySelectorAll('.accordion-item.open').forEach(el => {{
                el.classList.remove('open');
            }});
            currentOpenId = null;
        }}

        // 목차 토글
        function toggleToc() {{
            document.getElementById('tocBody').classList.toggle('open');
        }}

        // 다크모드 토글
        function toggleDarkMode() {{
            document.body.classList.toggle('dark-mode');
            localStorage.setItem('darkMode', document.body.classList.contains('dark-mode'));
        }}

        // 다크모드 복원
        if (localStorage.getItem('darkMode') === 'true') {{
            document.body.classList.add('dark-mode');
        }}

        // 공유
        function shareNewsletter() {{
            if (navigator.share) {{
                navigator.share({{
                    title: '{metadata.get("title", "소식지")} {metadata.get("issue", "")}',
                    text: '{metadata.get("party", "")} {metadata.get("date", "")} 소식지',
                    url: window.location.href
                }});
            }} else {{
                // 클립보드 복사
                navigator.clipboard.writeText(window.location.href).then(() => {{
                    alert('링크가 복사되었습니다!');
                }});
            }}
        }}
    </script>
</body>
</html>'''

        return html

    def close(self):
        """리소스 정리"""
        self.doc.close()


def convert_newsletter(pdf_path: str, output_path: str = None) -> str:
    """소식지 PDF를 HTML로 변환하는 간편 함수"""
    converter = NewsletterConverter(pdf_path)
    try:
        if not output_path:
            pdf_name = Path(pdf_path).stem
            output_path = str(Path(pdf_path).parent / f"{pdf_name}_mobile.html")

        html = converter.generate_html(output_path)
        print(f"변환 완료: {output_path}")
        return output_path
    finally:
        converter.close()


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        pdf_path = sys.argv[1]
        output = convert_newsletter(pdf_path)
        print(f"결과: {output}")
    else:
        print("사용법: python newsletter_converter.py <PDF파일경로>")
