"""
HTML 생성 모듈 v6
홍태용 선거공보물 스타일 모바일 최적화 페이지 생성
- Promise Cards: 확장 가능한 공약 카드
- Timeline: 실적 타임라인
- Bottom Navigation
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
import re
import json

# 교회 주보 전용 생성기 (선거 홍보물과 완전 분리)
from church_html_generator import get_church_bulletin_generator


class HTMLGenerator:
    """모바일 최적화 HTML 생성 - 홍태용 스타일"""

    def __init__(self):
        self.party_colors = {
            "국민의힘": {"primary": "#E11D48", "light": "#E11D4820", "dark": "#E11D48dd"},
            "더불어민주당": {"primary": "#004EA2", "light": "#004EA220", "dark": "#004EA2dd"},
            "민주당": {"primary": "#004EA2", "light": "#004EA220", "dark": "#004EA2dd"},
            "정의당": {"primary": "#FFCC00", "light": "#FFCC0020", "dark": "#FFCC00dd"},
            "국민의당": {"primary": "#EA5504", "light": "#EA550420", "dark": "#EA5504dd"},
            "무소속": {"primary": "#6B7280", "light": "#6B728020", "dark": "#6B7280dd"},
        }
        self.default_color = {"primary": "#E11D48", "light": "#E11D4820", "dark": "#E11D48dd"}

    def _clean_text(self, text: str) -> str:
        """텍스트에서 인코딩 손상 문자 및 불필요한 제어 문자 제거"""
        if not text:
            return ""

        # 일반적인 인코딩 손상 문자 제거 (¸, ˜, º 등)
        # Unicode 범위: 0x00B0-0x00BF (상위 ASCII 범위의 일부 제어/특수 문자)
        cleaned = re.sub(r'[\u00b8\u02dc\u00ba\u00b0\u00b7]', '', text)

        # 기타 제어 문자 제거 (탭, 개행 제외)
        cleaned = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]', '', cleaned)

        # 여러 공백을 하나로
        cleaned = re.sub(r'\s+', ' ', cleaned)

        return cleaned.strip()

    def generate_html(
        self,
        extracted_data: Dict[str, Any],
        title: str,
        content_type: str = "general",
        job_id: str = ""
    ) -> str:
        """콘텐츠 유형에 따라 적절한 HTML 생성"""
        if content_type == "election":
            return self._generate_election_html(extracted_data, title, job_id)
        elif content_type == "church":
            return self._generate_church_html(extracted_data, title, job_id)
        else:
            return self._generate_general_html(extracted_data, title, job_id)

    def _generate_election_html(
        self,
        extracted_data: Dict[str, Any],
        title: str,
        job_id: str
    ) -> str:
        """선거 홍보물 HTML 생성 - 홍태용 스타일"""
        pages = extracted_data.get("pages", [])
        structured_data = extracted_data.get("structured_data", {})

        # 모든 페이지 텍스트 결합
        all_text = "\n".join([p.get("text", "") for p in pages])

        # 텍스트에서 정보 추출
        info = self._extract_election_info(all_text, title, structured_data)

        # 정당에 따른 색상
        party = info.get("party", "")
        colors = self.party_colors.get(party, self.default_color)

        # 공약 추출 - core_pledges 우선 사용
        pledges = info.get("core_pledges", []) or info.get("pledges", [])

        # 실적 추출
        careers = info.get("careers", [])

        return f'''<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <meta name="description" content="{info.get('name', '후보')} - {info.get('position', '선거공보')}">
    <title>{info.get('name', title)} - {info.get('position', '선거공보')}</title>

    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}

        :root {{
            --party-color: {colors['primary']};
            --party-color-light: {colors['light']};
            --party-color-dark: {colors['dark']};
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
            color: white;
            padding: 5px 12px;
            border-radius: 20px;
            font-size: 0.85em;
            font-weight: 600;
        }}

        /* Hero Section */
        .hero-section {{
            margin-top: 60px;
            background: linear-gradient(135deg, var(--party-color) 0%, var(--party-color-dark) 100%);
            color: white;
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

        .highlight-card .description {{
            font-size: 0.85em;
            color: #666;
            margin-top: 3px;
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

        .promise-summary {{
            font-size: 0.9em;
            color: #666;
            margin-top: 5px;
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

        /* Profile Timeline */
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

        /* Page Content Section */
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

        /* Scrollbar */
        ::-webkit-scrollbar {{
            width: 6px;
        }}

        ::-webkit-scrollbar-thumb {{
            background: var(--party-color);
            border-radius: 3px;
        }}
    </style>
</head>
<body>

    <!-- Fixed Top Navigation -->
    <nav class="nav-bar">
        <span class="candidate-name">{info.get('name', '후보')}</span>
        <span class="party-badge">{info.get('party', '정당')}</span>
    </nav>

    <!-- Hero Section -->
    <section class="hero-section" id="home">
        <div class="hero-content">
            <div class="hero-number">기호 {info.get('symbol', '?')}</div>
            <h1 class="hero-name">{info.get('name', '후보')}</h1>
            <p class="hero-slogan">{info.get('slogan', '')}</p>
            <p class="hero-position">{info.get('position', '')}</p>
        </div>
    </section>

    <!-- Quick Highlights -->
    <div class="quick-highlights">
        {self._generate_highlights_html(info)}
    </div>

    <!-- Pledges Section -->
    <section class="section" id="pledges">
        <h2 class="section-title"><span class="icon">📋</span> 핵심 공약</h2>
        <div class="promise-list">
            {self._generate_promise_cards_html(pledges)}
        </div>
    </section>

    <!-- Contact Section -->
    {self._generate_contact_section_html(structured_data)}

    <!-- Full Text Section -->
    <section class="section" id="fulltext">
        <h2 class="section-title"><span class="icon">📄</span> 전문보기</h2>
        {self._generate_page_contents_html(pages)}
    </section>

    <!-- Career Section (마지막에 위치) -->
    <section class="section" id="career">
        <h2 class="section-title"><span class="icon">📜</span> 주요 실적</h2>
        <div class="timeline">
            {self._generate_timeline_html(careers)}
        </div>
    </section>

    <!-- Footer -->
    <footer class="footer">
        <p>본 페이지는 PDF 선거공보물에서 자동 생성되었습니다.</p>
        <p style="margin-top: 10px;"><a href="https://studysnap.kr" target="_blank">StudySnap</a> | PDF를 모바일 콘텐츠로</p>
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
            실적
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
    </script>

</body>
</html>'''

    def _extract_election_info(self, text: str, title: str, structured_data: Dict = None) -> Dict:
        """텍스트에서 선거 정보 추출 - 확장된 구조"""
        info = {
            "name": "",
            "party": "",
            "symbol": "",
            "slogan": "",
            "subtitle": "",  # 부제
            "position": "",
            "manifesto": {},  # 출사표
            "achievements": [],  # 성과
            "core_pledges": [],  # 6개 핵심공약
            "pledges": [],  # 기존 호환성
            "public_pledges": [],  # 국민밀착공약
            "careers": [],
            "closing_message": "",
            "contact_info": "",
            "highlights": []
        }

        # structured_data가 있으면 우선 사용
        if structured_data:
            info["name"] = structured_data.get("candidate_name", "")
            info["party"] = structured_data.get("party", "")
            info["symbol"] = structured_data.get("symbol", "")
            info["slogan"] = structured_data.get("slogan", "")
            info["subtitle"] = structured_data.get("subtitle", "")
            info["manifesto"] = structured_data.get("manifesto", {})
            info["achievements"] = structured_data.get("achievements", [])
            info["core_pledges"] = structured_data.get("core_pledges", [])
            info["pledges"] = structured_data.get("pledges", [])
            info["public_pledges"] = structured_data.get("public_pledges", [])
            info["careers"] = structured_data.get("career", [])
            info["closing_message"] = structured_data.get("closing_message", "")
            info["contact_info"] = structured_data.get("contact_info", "")

        # 텍스트에서 추가 정보 추출
        lines = text.split('\n')

        # 이름 추출
        if not info["name"]:
            name_patterns = [
                r'기호\s*\d+[번호]?\s*([가-힣]{2,4})',
                r'([가-힣]{2,4})\s*후보',
                r'후보\s*([가-힣]{2,4})',
            ]
            for pattern in name_patterns:
                match = re.search(pattern, text)
                if match:
                    info["name"] = match.group(1)
                    break
            if not info["name"] and title:
                info["name"] = title.replace('.pdf', '').strip()

        # 정당 추출
        if not info["party"]:
            parties = ["국민의힘", "더불어민주당", "민주당", "정의당", "국민의당", "무소속"]
            for party in parties:
                if party in text:
                    info["party"] = party
                    break

        # 기호 추출
        if not info["symbol"]:
            symbol_match = re.search(r'기호\s*(\d+)', text)
            if symbol_match:
                info["symbol"] = symbol_match.group(1)

        # 슬로건 추출 - structured_data에 있는 경우에만 사용
        # 선거 공약집은 본문에서 임의로 슬로건을 추출하지 않음
        # (강의 자료와 달리 원본 구조 유지가 중요)
        if not info["slogan"]:
            # 명시적인 슬로건 패턴만 허용 (첫 100자 내에서만)
            first_text = text[:200]  # 첫 페이지 시작 부분만
            explicit_slogan_patterns = [
                r'진심이\s*이깁니다',  # 명시적인 캐치프레이즈
            ]
            for pattern in explicit_slogan_patterns:
                match = re.search(pattern, first_text)
                if match:
                    info["slogan"] = match.group(0).strip()
                    break

        # 직위/선거구 추출
        position_patterns = [
            r'국회의원',
            r'시장',
            r'구청장',
            r'도지사',
            r'시의원',
            r'구의원',
        ]
        for pattern in position_patterns:
            if pattern in text:
                info["position"] = pattern + " 후보"
                break

        # 공약 추출 (텍스트 기반)
        if not info["pledges"]:
            pledge_patterns = [
                r'[①②③④⑤⑥⑦⑧⑨⑩]\s*(.+)',
                r'[1-9]\.\s*(.+)',
                r'•\s*(.+)',
                r'[○●]\s*(.+)',
            ]
            for pattern in pledge_patterns:
                matches = re.findall(pattern, text)
                for match in matches[:10]:  # 최대 10개
                    pledge = match.strip()
                    if 10 < len(pledge) < 100 and pledge not in info["pledges"]:
                        info["pledges"].append(pledge)

        # 실적 추출 (텍스트 기반)
        if not info["careers"]:
            career_patterns = [
                r'(\d{4})[~\-년]\s*(.+)',
                r'(전|현)\s*(.+장|.+위원|.+대표)',
            ]
            for pattern in career_patterns:
                matches = re.findall(pattern, text)
                for match in matches[:15]:
                    if isinstance(match, tuple):
                        career = f"{match[0]} {match[1]}".strip()
                    else:
                        career = match.strip()
                    if career not in info["careers"] and len(career) > 5:
                        info["careers"].append(career)

        # 하이라이트 생성
        info["highlights"] = [
            {"icon": "🎯", "label": "핵심 공약", "value": f"{len(info['pledges'])}개"},
            {"icon": "📋", "label": "주요 실적", "value": f"{len(info['careers'])}건"},
        ]

        # 모든 텍스트 필드 정리 (인코딩 손상 문자 제거)
        info["name"] = self._clean_text(info["name"])
        info["party"] = self._clean_text(info["party"])
        info["symbol"] = self._clean_text(info["symbol"])
        info["slogan"] = self._clean_text(info["slogan"])
        info["subtitle"] = self._clean_text(info["subtitle"])
        info["position"] = self._clean_text(info["position"])
        info["closing_message"] = self._clean_text(info["closing_message"])
        info["contact_info"] = self._clean_text(info["contact_info"])

        # 리스트 내 텍스트 정리
        info["pledges"] = [self._clean_text(p) for p in info["pledges"]]
        info["careers"] = [self._clean_text(c) for c in info["careers"]]
        if isinstance(info["core_pledges"], list):
            info["core_pledges"] = [
                {
                    "title": self._clean_text(p.get("title", "")),
                    "subtitle": self._clean_text(p.get("subtitle", "")),
                    "details": [self._clean_text(d) for d in p.get("details", [])]
                }
                for p in info["core_pledges"]
            ]

        return info

    def _generate_highlights_html(self, info: Dict) -> str:
        """하이라이트 카드 HTML 생성"""
        highlights = info.get("highlights", [])
        if not highlights:
            return ""

        html = ""
        for h in highlights:
            html += f'''
        <div class="highlight-card">
            <span class="icon">{h.get('icon', '📌')}</span>
            <div class="content">
                <span class="number">{h.get('value', '')}</span>
                <div>
                    <div class="label">{h.get('label', '')}</div>
                </div>
            </div>
        </div>'''

        return html

    def _generate_promise_cards_html(self, pledges: List) -> str:
        """공약 카드 HTML 생성 - 문자열 또는 딕셔너리 지원"""
        if not pledges:
            return '<p style="color:#666; text-align:center; padding:20px;">공약 정보를 추출할 수 없습니다.</p>'

        html = ""
        for i, pledge in enumerate(pledges[:20], 1):
            # pledge가 dict인 경우 (core_pledges)
            if isinstance(pledge, dict):
                title = pledge.get("title", "")
                details_list = pledge.get("details", [])
                if details_list:
                    details = "\n".join([f"• {d}" for d in details_list])
                else:
                    details = title
            # pledge가 문자열인 경우 (기존 pledges)
            else:
                # 공약을 제목과 상세 내용으로 분리
                parts = pledge.split(':', 1) if ':' in pledge else pledge.split('.', 1)

                if len(parts) > 1 and len(parts[0]) < 80:
                    title = parts[0].strip()
                    details = parts[1].strip()
                elif len(pledge) > 80:
                    # 긴 공약은 첫 60자를 제목으로
                    title = pledge[:60].strip() + '...'
                    details = pledge
                else:
                    title = pledge
                    details = pledge

            # HTML 이스케이프
            title_escaped = title.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
            details_escaped = details.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
            # 줄바꿈을 <br>로 변환
            details_escaped = details_escaped.replace('\n', '<br>')

            html += f'''
            <div class="promise-card">
                <div class="promise-header">
                    <span class="promise-number">{i}</span>
                    <div class="promise-header-text">
                        <div class="promise-title">{title_escaped}</div>
                    </div>
                </div>
                <div class="promise-details">
                    <p style="color:#333; line-height:1.7; margin:0;">{details_escaped}</p>
                </div>
                <div class="expand-btn">상세 보기</div>
            </div>'''

        return html

    def _generate_timeline_html(self, careers: List[str]) -> str:
        """실적 타임라인 HTML 생성 - 개선된 포맷팅"""
        if not careers:
            return '<p style="color:#666; text-align:center; padding:20px;">실적 정보를 추출할 수 없습니다.</p>'

        html = ""
        for career in careers[:15]:
            # 연도 추출
            year_match = re.search(r'(\d{4})', career)
            year = year_match.group(1) if year_match else ""

            # 실적을 제목과 상세 내용으로 분리
            title = ""
            details = career

            # 패턴 1: "연도~연도 내용" 형식
            year_range_match = re.match(r'(\d{4}[~\-년]\s*(?:\d{4}|현재)?)\s*(.+)', career)
            if year_range_match:
                title = year_range_match.group(1).strip()
                details = year_range_match.group(2).strip()
            # 패턴 2: "직위/직책 + 기관명" 형식 (예: "전 ○○장", "현 △△위원")
            elif re.match(r'(전|현|제\d+대)\s*(.+)', career):
                parts = career.split(None, 2)  # 첫 두 단어를 제목으로
                if len(parts) >= 2:
                    title = f"{parts[0]} {parts[1]}"
                    details = ' '.join(parts[2:]) if len(parts) > 2 else parts[1]
            # 패턴 3: 직책이 명확한 경우 (장, 위원, 대표 등)
            elif any(keyword in career for keyword in ['장', '위원', '대표', '국장', '본부장', '실장']):
                # 첫 번째 문장이나 절을 제목으로
                split_career = re.split(r'[,\n]', career, 1)
                if len(split_career) > 1:
                    title = split_career[0].strip()
                    details = split_career[1].strip()
                else:
                    title = career[:30] + "..." if len(career) > 30 else career
                    details = career

            # HTML 이스케이프
            title_escaped = title.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
            details_escaped = details.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')

            # 줄바꿈을 <br>로 변환
            details_escaped = details_escaped.replace('\n', '<br>')

            # 제목이 있으면 강조, 없으면 전체를 content로
            if title and title != details:
                html += f'''
            <div class="timeline-item">
                <div class="timeline-year">{year}</div>
                <div class="timeline-content">
                    <div style="font-weight:600; font-size:1.05em; color:#222; margin-bottom:5px;">{title_escaped}</div>
                    <div style="color:#555; font-size:0.95em; line-height:1.6;">{details_escaped}</div>
                </div>
            </div>'''
            else:
                html += f'''
            <div class="timeline-item">
                <div class="timeline-year">{year}</div>
                <div class="timeline-content">{details_escaped}</div>
            </div>'''

        return html

    def _make_links_clickable(self, text):
        """URL을 클릭 가능한 링크로 변환 - 개선된 버전"""
        import re
        # SNS 패턴들 (순서 중요 - 더 구체적인 패턴을 먼저 매칭)
        patterns = [
            # 전체 URL (http/https 포함)
            (r'(https?://[^\s<>]+)', r'<a href="" target="_blank" style="color:var(--party-color); text-decoration:underline;"></a>'),

            # Facebook
            (r'(?<!href=")(?<!>)facebook\.com/([a-zA-Z0-9._-]+)',
             r'<a href="https://facebook.com/" target="_blank" style="color:#1877f2; font-weight:500;">🔗 facebook.com/</a>'),

            # Instagram @username or instagram.com/username
            (r'(?<!href=")(?<!>)instagram\.com/([a-zA-Z0-9._-]+)',
             r'<a href="https://instagram.com/" target="_blank" style="color:#e4405f; font-weight:500;">📷 instagram.com/</a>'),
            (r'@([a-zA-Z0-9._-]+)(?=\s|$|<br>)',
             r'<a href="https://instagram.com/" target="_blank" style="color:#e4405f; font-weight:500;">📷 @</a>'),

            # Naver Blog
            (r'(?<!href=")(?<!>)blog\.naver\.com/([a-zA-Z0-9_-]+)',
             r'<a href="https://blog.naver.com/" target="_blank" style="color:#03c75a; font-weight:500;">📝 blog.naver.com/</a>'),

            # YouTube
            (r'(?<!href=")(?<!>)youtube\.com/([^\s<>🟢]+)',
             r'<a href="https://youtube.com/" target="_blank" style="color:#ff0000; font-weight:500;">▶️ youtube.com/</a>'),
            (r'(?<!href=")(?<!>)youtu\.be/([a-zA-Z0-9_-]+)',
             r'<a href="https://youtu.be/" target="_blank" style="color:#ff0000; font-weight:500;">▶️ youtu.be/</a>'),

            # Twitter/X
            (r'(?<!href=")(?<!>)(?:twitter|x)\.com/([a-zA-Z0-9_]+)',
             r'<a href="https://x.com/" target="_blank" style="color:#1da1f2; font-weight:500;">🐦 @</a>'),

            # 전화번호 (클릭시 전화) - TEL, 전화 키워드 포함
            (r'TEL\s*(\d{2,3}-\d{3,4}-\d{4})',
             r'TEL <a href="tel:" style="color:var(--party-color); font-weight:500; text-decoration:underline;"></a>'),
            (r'전화\s*[:：]\s*(\d{2,3}-\d{3,4}-\d{4})',
             r'전화 : <a href="tel:" style="color:var(--party-color); font-weight:500; text-decoration:underline;"></a>'),
            # 일반 전화번호 (위 패턴에 매칭되지 않은 경우)
            (r'(?<!">)(\d{2,3}-\d{3,4}-\d{4})',
             r'<a href="tel:" style="color:var(--party-color); font-weight:500;">📞 </a>'),
        ]

        for pattern, replacement in patterns:
            text = re.sub(pattern, replacement, text)

        return text


    def _generate_contact_section_html(self, structured_data: Dict) -> str:
        """연락처 섹션 HTML 생성 - 개선된 SNS 링크"""
        if not structured_data:
            return ""

        contact_info = structured_data.get("contact_info", "")
        if not contact_info:
            return ""

        # SNS 링크를 클릭 가능하게 변환
        import re

        def make_links_clickable(text):
            """URL을 클릭 가능한 링크로 변환 - 개선된 버전"""
            # SNS 패턴들 (순서 중요 - 더 구체적인 패턴을 먼저 매칭)
            patterns = [
                # 전체 URL (http/https 포함)
                (r'(https?://[^\s<>]+)', r'<a href="\1" target="_blank" style="color:var(--party-color); text-decoration:underline;">\1</a>'),

                # Facebook
                (r'(?<!href=")(?<!>)facebook\.com/([a-zA-Z0-9._-]+)',
                 r'<a href="https://facebook.com/\1" target="_blank" style="color:#1877f2; font-weight:500;">🔗 facebook.com/\1</a>'),

                # Instagram @username or instagram.com/username
                (r'(?<!href=")(?<!>)instagram\.com/([a-zA-Z0-9._-]+)',
                 r'<a href="https://instagram.com/\1" target="_blank" style="color:#e4405f; font-weight:500;">📷 instagram.com/\1</a>'),
                (r'@([a-zA-Z0-9._-]+)(?=\s|$|<br>)',
                 r'<a href="https://instagram.com/\1" target="_blank" style="color:#e4405f; font-weight:500;">📷 @\1</a>'),

                # Naver Blog
                (r'(?<!href=")(?<!>)blog\.naver\.com/([a-zA-Z0-9_-]+)',
                 r'<a href="https://blog.naver.com/\1" target="_blank" style="color:#03c75a; font-weight:500;">📝 blog.naver.com/\1</a>'),

                # YouTube
                (r'(?<!href=")(?<!>)youtube\.com/([^\s<>🟢]+)',
                 r'<a href="https://youtube.com/\1" target="_blank" style="color:#ff0000; font-weight:500;">▶️ youtube.com/\1</a>'),
                (r'(?<!href=")(?<!>)youtu\.be/([a-zA-Z0-9_-]+)',
                 r'<a href="https://youtu.be/\1" target="_blank" style="color:#ff0000; font-weight:500;">▶️ youtu.be/\1</a>'),

                # Twitter/X
                (r'(?<!href=")(?<!>)(?:twitter|x)\.com/([a-zA-Z0-9_]+)',
                 r'<a href="https://x.com/\1" target="_blank" style="color:#1da1f2; font-weight:500;">🐦 @\1</a>'),

                # 전화번호 (클릭시 전화) - TEL, 전화 키워드 포함
                (r'TEL\s*(\d{2,3}-\d{3,4}-\d{4})',
                 r'TEL <a href="tel:\1" style="color:var(--party-color); font-weight:500; text-decoration:underline;">\1</a>'),
                (r'전화\s*[:：]\s*(\d{2,3}-\d{3,4}-\d{4})',
                 r'전화 : <a href="tel:\1" style="color:var(--party-color); font-weight:500; text-decoration:underline;">\1</a>'),
                # 일반 전화번호 (위 패턴에 매칭되지 않은 경우)
                (r'(?<!">)(\d{2,3}-\d{3,4}-\d{4})',
                 r'<a href="tel:\1" style="color:var(--party-color); font-weight:500;">📞 \1</a>'),
            ]

            for pattern, replacement in patterns:
                text = re.sub(pattern, replacement, text)

            return text

        # HTML 이스케이프 먼저 수행
        contact_escaped = contact_info.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')

        # 줄바꿈을 <br>로 변환 (링크 변환 전에)
        contact_escaped = contact_escaped.replace('\n', '<br>')

        # SNS 링크를 클릭 가능하게 변환
        contact_html = self._make_links_clickable(contact_escaped)

        return f'''
    <section class="section" id="contact">
        <h2 class="section-title"><span class="icon">📞</span> 선거사무소 연락처</h2>
        <div style="background:#f8f9fa; padding:25px; border-radius:10px; line-height:2.0;">
            {contact_html}
        </div>
        <div style="margin-top:15px; padding:15px; background:#fff3cd; border-radius:8px; border-left:4px solid #ffc107;">
            <p style="margin:0; font-size:0.9em; color:#856404;">
                💡 링크를 클릭하면 해당 SNS 페이지로 바로 이동합니다
            </p>
        </div>
    </section>'''

    def _generate_page_contents_html(self, pages: List[Dict]) -> str:
        """페이지별 내용 HTML 생성"""
        if not pages:
            return ""

        html = ""
        for page in pages:
            page_num = page.get("page_number", 1)
            text = page.get("text", "").strip()

            if text:
                # 텍스트 포맷팅
                formatted_text = self._format_page_text(text)

                html += f'''
        <div class="page-content">
            <h4>📄 페이지 {page_num}</h4>
            {formatted_text}
        </div>'''

        return html

    def _format_page_text(self, text: str) -> str:
        """페이지 텍스트 포맷팅"""
        if not text:
            return ""

        # HTML 이스케이프
        text = text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')

        # 줄바꿈 처리
        lines = text.split('\n')
        formatted = []

        for line in lines:
            line = line.strip()
            if not line:
                continue
            formatted.append(f"<p>{line}</p>")

        return '\n            '.join(formatted)

    def _generate_general_html(
        self,
        extracted_data: Dict[str, Any],
        title: str,
        job_id: str
    ) -> str:
        """일반 문서 HTML 생성"""
        pages = extracted_data.get("pages", [])

        return f'''<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
            background: #f5f5f5;
        }}
        .page {{
            background: white;
            padding: 30px;
            margin-bottom: 20px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}
        .page-header {{
            color: #6366F1;
            border-bottom: 2px solid #6366F1;
            padding-bottom: 10px;
            margin-bottom: 20px;
        }}
        p {{
            margin-bottom: 15px;
        }}
    </style>
</head>
<body>
    <h1>{title}</h1>
    {self._generate_general_pages_html(pages)}
</body>
</html>'''

    def _generate_general_pages_html(self, pages: List[Dict]) -> str:
        """일반 문서 페이지 HTML"""
        html = ""
        for page in pages:
            page_num = page.get("page_number", 1)
            text = page.get("text", "").strip()
            if text:
                formatted = self._format_page_text(text)
                html += f'''
    <div class="page">
        <h3 class="page-header">페이지 {page_num}</h3>
        {formatted}
    </div>'''
        return html

    def _generate_manifesto_section_html(self, manifesto: Dict) -> str:
        """출사표 섹션 HTML 생성"""
        if not manifesto or not manifesto.get("title"):
            return ""

        title = manifesto.get("title", "")
        content = manifesto.get("content", "")
        closing = manifesto.get("closing", "")

        content_escaped = content.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
        closing_escaped = closing.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')

        return f'''
    <section class="section" id="manifesto">
        <h2 class="section-title"><span class="icon">📢</span> {title}</h2>
        <div class="promise-card" style="cursor: pointer;">
            <div class="promise-header">
                <span class="promise-number">📜</span>
                <div class="promise-header-text">
                    <div class="promise-title">출사표 전문</div>
                    <div class="promise-summary">클릭하여 펼쳐보기</div>
                </div>
            </div>
            <div class="promise-details">
                <p style="color:#333; line-height:1.8; margin:0; white-space:pre-wrap;">{content_escaped}</p>
                {f'<p style="color:#E11D48; font-weight:600; margin-top:20px;">{closing_escaped}</p>' if closing else ''}
            </div>
            <div class="expand-btn">상세 보기</div>
        </div>
    </section>'''

    def _generate_achievements_section_html(self, achievements: List[Dict]) -> str:
        """성과 섹션 HTML 생성"""
        if not achievements:
            return ""

        html = ""
        for achievement in achievements:
            title = achievement.get("title", "")
            sections = achievement.get("sections", [])

            if not title:
                continue

            html += f'''
    <section class="section" id="achievements">
        <h2 class="section-title"><span class="icon">⭐</span> {title}</h2>
        <div class="promise-list">'''

            for i, section in enumerate(sections, 1):
                section_title = section.get("title", "")
                items = section.get("items", [])

                items_html = ""
                for item in items:
                    item_escaped = item.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                    items_html += f'<li>{item_escaped}</li>'

                html += f'''
            <div class="promise-card">
                <div class="promise-header">
                    <span class="promise-number">{i}</span>
                    <div class="promise-header-text">
                        <div class="promise-title">{section_title}</div>
                    </div>
                </div>
                <div class="promise-details">
                    <ul style="list-style:none; margin:0; padding:0;">
                        {items_html}
                    </ul>
                </div>
                <div class="expand-btn">상세 보기</div>
            </div>'''

            html += '''
        </div>
    </section>'''

        return html

    def _generate_core_pledges_html(self, core_pledges: List[Dict]) -> str:
        """6개 핵심공약 HTML 생성"""
        if not core_pledges:
            return '<p style="color:#666; text-align:center; padding:20px;">공약 정보를 추출할 수 없습니다.</p>'

        html = ""
        for i, pledge in enumerate(core_pledges, 1):
            title = pledge.get("title", "")
            details = pledge.get("details", [])

            title_escaped = title.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')

            details_html = ""
            for detail in details:
                detail_escaped = detail.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                details_html += f'<li>{detail_escaped}</li>'

            html += f'''
            <div class="promise-card">
                <div class="promise-header">
                    <span class="promise-number">{i}</span>
                    <div class="promise-header-text">
                        <div class="promise-title">{title_escaped}</div>
                    </div>
                </div>
                <div class="promise-details">
                    <ul style="list-style:none; margin:0; padding:0;">
                        {details_html}
                    </ul>
                </div>
                <div class="expand-btn">상세 보기</div>
            </div>'''

        return html

    def _generate_public_pledges_section_html(self, public_pledges: List[str]) -> str:
        """주민밀착공약 섹션 HTML 생성 - 지역별 지도 포함"""
        if not public_pledges:
            return ""

        # 지역별 공약 데이터 구조화 (예시 - 실제로는 OCR에서 추출)
        regional_pledges = {
            "상도동": ["상도동 지하철역 주변 보행환경 개선", "상도문화광장 리모델링"],
            "흑석동": ["중앙대 앞 도로 정비", "흑석시장 현대화 사업 추진"],
            "사당5동": ["사당5동 주민센터 확충", "어린이공원 안전시설 보강"]
        }

        html = '''
    <section class="section" id="public-pledges">
        <h2 class="section-title"><span class="icon">💝</span> 주민밀착공약</h2>

        <!-- 지역별 공약 지도 -->
        <div style="margin:20px 0;">
            <h3 style="color:#666; font-size:0.95em; margin:10px 0 15px 0;">📍 우리 동네 공약 (지도를 클릭하세요)</h3>
            <div style="background:#fff; padding:20px; border-radius:10px; box-shadow:0 2px 8px rgba(0,0,0,0.1);">
                <svg viewBox="0 0 400 300" style="width:100%; height:auto; max-width:400px; margin:0 auto; display:block;">
                    <!-- 배경 -->
                    <rect width="400" height="300" fill="#f0f4f8"/>

                    <!-- 상도동 -->
                    <path id="region-sangdo" d="M 50,50 L 150,50 L 150,150 L 50,150 Z"
                          fill="#e3f2fd" stroke="#1976d2" stroke-width="2"
                          style="cursor:pointer; transition:all 0.3s;"
                          onmouseover="this.setAttribute('fill','#bbdefb')"
                          onmouseout="this.setAttribute('fill','#e3f2fd')"
                          onclick="toggleRegion('sangdo')"/>
                    <text x="100" y="95" text-anchor="middle" font-size="16" font-weight="bold" fill="#1976d2" style="pointer-events:none;">
                        상도동
                    </text>
                    <text x="100" y="115" text-anchor="middle" font-size="12" fill="#666" style="pointer-events:none;">
                        클릭
                    </text>

                    <!-- 흑석동 -->
                    <path id="region-heukseok" d="M 160,50 L 260,50 L 260,150 L 160,150 Z"
                          fill="#fff3e0" stroke="#f57c00" stroke-width="2"
                          style="cursor:pointer; transition:all 0.3s;"
                          onmouseover="this.setAttribute('fill','#ffe0b2')"
                          onmouseout="this.setAttribute('fill','#fff3e0')"
                          onclick="toggleRegion('heukseok')"/>
                    <text x="210" y="95" text-anchor="middle" font-size="16" font-weight="bold" fill="#f57c00" style="pointer-events:none;">
                        흑석동
                    </text>
                    <text x="210" y="115" text-anchor="middle" font-size="12" fill="#666" style="pointer-events:none;">
                        클릭
                    </text>

                    <!-- 사당5동 -->
                    <path id="region-sadang" d="M 270,50 L 370,50 L 370,150 L 270,150 Z"
                          fill="#e8f5e9" stroke="#388e3c" stroke-width="2"
                          style="cursor:pointer; transition:all 0.3s;"
                          onmouseover="this.setAttribute('fill','#c8e6c9')"
                          onmouseout="this.setAttribute('fill','#e8f5e9')"
                          onclick="toggleRegion('sadang')"/>
                    <text x="320" y="90" text-anchor="middle" font-size="16" font-weight="bold" fill="#388e3c" style="pointer-events:none;">
                        사당5동
                    </text>
                    <text x="320" y="115" text-anchor="middle" font-size="12" fill="#666" style="pointer-events:none;">
                        클릭
                    </text>

                    <!-- 범례 -->
                    <text x="200" y="180" text-anchor="middle" font-size="14" fill="#666">
                        💡 지역을 클릭하면 해당 지역 공약을 확인할 수 있습니다
                    </text>
                </svg>
            </div>
        </div>

        <!-- 지역별 공약 상세 (토글) -->'''

        for region_id, region_name in [("sangdo", "상도동"), ("heukseok", "흑석동"), ("sadang", "사당5동")]:
            pledges = regional_pledges.get(region_name, [])
            html += f'''
        <div id="pledges-{region_id}" class="regional-pledges" style="display:none; margin:15px 0; padding:20px; background:#f8f9fa; border-radius:10px; border-left:4px solid var(--party-color);">
            <h4 style="margin:0 0 15px 0; color:var(--party-color);">📍 {region_name} 공약</h4>
            <ul style="list-style:none; margin:0; padding:0;">'''

            for pledge in pledges:
                pledge_escaped = pledge.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                html += f'''
                <li style="padding:8px 0; padding-left:20px; position:relative;">
                    <span style="position:absolute; left:0; color:var(--party-color);">✓</span>
                    {pledge_escaped}
                </li>'''

            html += '''
            </ul>
        </div>'''

        html += '''

        <!-- 지역공통 공약 -->
        <div style="margin-top:20px;">
            <h3 style="color:#666; font-size:0.95em; margin:10px 0 15px 0;">[지역공통]</h3>
            <div style="background:#f8f9fa; padding:20px; border-radius:10px;">
                <ul style="list-style:none; margin:0; padding:0;">'''

        for pledge in public_pledges:
            pledge_escaped = pledge.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
            html += f'''
                    <li style="padding:12px 0; padding-left:25px; position:relative; border-bottom:1px solid #e0e0e0;">
                        <span style="position:absolute; left:0; color:var(--party-color); font-weight:bold;">✓</span>
                        {pledge_escaped}
                    </li>'''

        html += '''
                </ul>
            </div>
        </div>
    </section>

    <script>
        // 지역별 공약 토글 기능
        function toggleRegion(regionId) {
            const pledgeDiv = document.getElementById('pledges-' + regionId);
            const allRegions = document.querySelectorAll('.regional-pledges');

            // 다른 지역 닫기
            allRegions.forEach(region => {
                if (region.id !== 'pledges-' + regionId) {
                    region.style.display = 'none';
                }
            });

            // 현재 지역 토글
            if (pledgeDiv.style.display === 'none') {
                pledgeDiv.style.display = 'block';
                // 부드럽게 스크롤
                pledgeDiv.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
            } else {
                pledgeDiv.style.display = 'none';
            }
        }
    </script>'''

        return html

    def _generate_closing_message_html(self, message: str) -> str:
        """마무리 문구 HTML 생성"""
        if not message:
            return ""

        message_escaped = message.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
        return f'''
        <div style="margin-top:30px; padding:20px; background:var(--party-color-light); border-radius:10px; text-align:center;">
            <p style="font-size:1.1em; font-weight:600; color:var(--party-color); margin:0;">{message_escaped}</p>
        </div>'''

    def _generate_contact_section_html_v2(self, contact_info: str) -> str:
        """연락처 섹션 HTML 생성 (V2)"""
        if not contact_info:
            return ""

        contact_escaped = contact_info.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
        contact_html = contact_escaped.replace('\n', '<br>')

        return f'''
    <section class="section" id="contact">
        <h2 class="section-title"><span class="icon">📞</span> 선거사무소</h2>
        <div style="background:#f8f9fa; padding:20px; border-radius:10px; line-height:1.8; text-align:center;">
            {contact_html}
        </div>
    </section>'''

    def _generate_church_html(
        self,
        extracted_data: Dict[str, Any],
        title: str,
        job_id: str
    ) -> str:
        """
        교회 주보 HTML 생성 - 전용 생성기 모듈로 위임
        선거 홍보물과 완전히 분리된 독립 템플릿 사용
        """
        # 교회 주보 전용 생성기 사용
        generator = get_church_bulletin_generator()
        return generator.generate(extracted_data, title)

    def _generate_church_html_legacy(
        self,
        extracted_data: Dict[str, Any],
        title: str,
        job_id: str
    ) -> str:
        """[DEPRECATED] 레거시 교회 주보 HTML 생성 - 새 모듈로 이전됨"""
        pages = extracted_data.get("pages", [])
        structured_data = extracted_data.get("structured_data", {})

        # 모든 페이지 텍스트 결합
        all_text = "\n".join([p.get("text", "") for p in pages])

        # 교회 주보 정보 추출
        info = self._extract_church_info(all_text, title, structured_data)

        # 여의도순복음교회 기본 SNS 정보 (PDF에서 추출 못할 경우 기본값)
        default_sns = {
            "youtube": "https://www.youtube.com/user/YFGCFGTV",
            "kakaotalk": "http://pf.kakao.com/_NrTxkK",
            "instagram": "https://www.instagram.com/yfgcprb/"
        }
        # info["sns"]가 빈 딕셔너리이면 기본값 사용
        sns = info.get("sns") or default_sns
        # 개별 키가 없으면 기본값에서 가져오기
        sns = {
            "youtube": sns.get("youtube") or default_sns["youtube"],
            "kakaotalk": sns.get("kakaotalk") or default_sns["kakaotalk"],
            "instagram": sns.get("instagram") or default_sns["instagram"]
        }

        # 헌금 링크
        donation_url = info.get("donation_url", "https://m.fgtv.com/donate/donate_m_ver2.asp")

        return f'''<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <meta name="description" content="{info.get('church_name', '교회')} 주보 - {info.get('date', '')}">
    <title>{info.get('church_name', title)} - {info.get('date', '주보')}</title>

    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}

        :root {{
            --primary-color: #6366F1;
            --primary-light: #6366F120;
            --primary-dark: #4F46E5;
            --accent-color: #D97706;
            --text-dark: #1F2937;
            --text-light: #6B7280;
            --bg-light: #F9FAFB;
        }}

        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Apple SD Gothic Neo', 'Noto Sans KR', sans-serif;
            line-height: 1.6;
            color: var(--text-dark);
            background: var(--bg-light);
            overflow-x: hidden;
            padding-bottom: 80px;
        }}

        body.dark-mode {{
            --primary-color: #818CF8;
            --primary-light: #818CF830;
            --primary-dark: #6366F1;
            --text-dark: #F9FAFB;
            --text-light: #D1D5DB;
            --bg-light: #111827;
            background: #0F172A;
            color: var(--text-dark);
        }}

        /* Header */
        .header {{
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            background: white;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            z-index: 1000;
            padding: 12px 16px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            transition: transform 0.3s ease, background 0.3s;
        }}

        body.dark-mode .header {{
            background: #1F2937;
        }}

        .header.hidden {{
            transform: translateY(-100%);
        }}

        .header-title {{
            font-size: 1.1em;
            font-weight: 700;
            color: var(--primary-color);
        }}

        .header-actions {{
            display: flex;
            gap: 8px;
        }}

        .header-btn {{
            background: none;
            border: none;
            font-size: 1.3em;
            cursor: pointer;
            padding: 5px;
            border-radius: 8px;
            transition: background 0.2s;
        }}

        .header-btn:hover {{
            background: var(--primary-light);
        }}

        /* Hero Section */
        .hero {{
            margin-top: 56px;
            background: linear-gradient(135deg, var(--primary-color) 0%, var(--primary-dark) 100%);
            color: white;
            padding: 30px 20px;
            text-align: center;
        }}

        .hero-church {{
            font-size: 1.5em;
            font-weight: 800;
            margin-bottom: 8px;
        }}

        .hero-date {{
            font-size: 1em;
            opacity: 0.9;
            margin-bottom: 5px;
        }}

        .hero-service {{
            font-size: 0.9em;
            opacity: 0.8;
        }}

        /* SNS Links Bar */
        .sns-bar {{
            display: flex;
            justify-content: center;
            gap: 20px;
            padding: 15px;
            background: white;
            border-bottom: 1px solid #e5e7eb;
        }}

        body.dark-mode .sns-bar {{
            background: #1F2937;
            border-color: #374151;
        }}

        .sns-link {{
            display: flex;
            flex-direction: column;
            align-items: center;
            text-decoration: none;
            color: var(--text-light);
            font-size: 0.75em;
            transition: transform 0.2s;
        }}

        .sns-link:hover {{
            transform: scale(1.1);
        }}

        .sns-icon {{
            font-size: 1.8em;
            margin-bottom: 4px;
        }}

        .sns-link.youtube .sns-icon {{ color: #FF0000; }}
        .sns-link.kakao .sns-icon {{ color: #FEE500; }}
        .sns-link.instagram .sns-icon {{ color: #E4405F; }}
        .sns-link.donation .sns-icon {{ color: #10B981; }}

        /* Section */
        .section {{
            background: white;
            margin: 12px;
            padding: 20px;
            border-radius: 16px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.05);
        }}

        body.dark-mode .section {{
            background: #1F2937;
        }}

        .section-title {{
            font-size: 1.2em;
            font-weight: 700;
            color: var(--primary-color);
            margin-bottom: 15px;
            padding-bottom: 10px;
            border-bottom: 2px solid var(--primary-color);
            display: flex;
            align-items: center;
            gap: 8px;
        }}

        /* Sermon Info */
        .sermon-card {{
            background: linear-gradient(135deg, var(--primary-light) 0%, #fff 100%);
            border-radius: 12px;
            padding: 20px;
            margin-bottom: 15px;
        }}

        body.dark-mode .sermon-card {{
            background: linear-gradient(135deg, var(--primary-light) 0%, #374151 100%);
        }}

        .sermon-title {{
            font-size: 1.3em;
            font-weight: 700;
            color: var(--text-dark);
            margin-bottom: 10px;
        }}

        .sermon-pastor {{
            font-size: 0.95em;
            color: var(--text-light);
            margin-bottom: 8px;
        }}

        .sermon-scripture {{
            display: inline-block;
            background: var(--primary-color);
            color: white;
            padding: 6px 14px;
            border-radius: 20px;
            font-size: 0.9em;
            cursor: pointer;
            transition: transform 0.2s, box-shadow 0.2s;
        }}

        .sermon-scripture:hover {{
            transform: scale(1.05);
            box-shadow: 0 4px 12px rgba(99, 102, 241, 0.4);
        }}

        /* Hymn Link */
        .hymn-link {{
            display: inline-block;
            background: var(--accent-color);
            color: white;
            padding: 6px 14px;
            border-radius: 20px;
            font-size: 0.9em;
            cursor: pointer;
            margin: 5px 5px 5px 0;
            transition: transform 0.2s, box-shadow 0.2s;
        }}

        .hymn-link:hover {{
            transform: scale(1.05);
            box-shadow: 0 4px 12px rgba(217, 119, 6, 0.4);
        }}

        /* Worship Order */
        .worship-order {{
            list-style: none;
        }}

        .worship-item {{
            display: flex;
            align-items: center;
            padding: 12px 0;
            border-bottom: 1px solid #e5e7eb;
        }}

        body.dark-mode .worship-item {{
            border-color: #374151;
        }}

        .worship-item:last-child {{
            border-bottom: none;
        }}

        .worship-number {{
            width: 28px;
            height: 28px;
            background: var(--primary-color);
            color: white;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 0.8em;
            font-weight: 600;
            margin-right: 12px;
            flex-shrink: 0;
        }}

        .worship-content {{
            flex: 1;
        }}

        .worship-name {{
            font-weight: 600;
            color: var(--text-dark);
        }}

        .worship-detail {{
            font-size: 0.85em;
            color: var(--text-light);
            margin-top: 2px;
        }}

        /* Church News */
        .news-item {{
            padding: 15px;
            background: var(--bg-light);
            border-radius: 10px;
            margin-bottom: 10px;
            border-left: 4px solid var(--primary-color);
        }}

        body.dark-mode .news-item {{
            background: #374151;
        }}

        .news-title {{
            font-weight: 600;
            color: var(--text-dark);
            margin-bottom: 5px;
        }}

        .news-content {{
            font-size: 0.9em;
            color: var(--text-light);
            line-height: 1.6;
        }}

        /* Donation Button */
        .donation-section {{
            text-align: center;
            padding: 25px;
            background: linear-gradient(135deg, #10B981 0%, #059669 100%);
            border-radius: 16px;
            margin: 20px 12px;
        }}

        .donation-title {{
            color: white;
            font-size: 1.1em;
            font-weight: 600;
            margin-bottom: 12px;
        }}

        .donation-btn {{
            display: inline-block;
            background: white;
            color: #059669;
            padding: 12px 30px;
            border-radius: 25px;
            font-size: 1em;
            font-weight: 700;
            text-decoration: none;
            transition: transform 0.2s, box-shadow 0.2s;
        }}

        .donation-btn:hover {{
            transform: scale(1.05);
            box-shadow: 0 6px 20px rgba(0,0,0,0.2);
        }}

        /* Modal */
        .modal-overlay {{
            display: none;
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: rgba(0,0,0,0.6);
            z-index: 2000;
            align-items: center;
            justify-content: center;
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
            animation: modalSlide 0.3s ease;
        }}

        body.dark-mode .modal-content {{
            background: #1F2937;
        }}

        @keyframes modalSlide {{
            from {{ transform: translateY(50px); opacity: 0; }}
            to {{ transform: translateY(0); opacity: 1; }}
        }}

        .modal-header {{
            padding: 16px 20px;
            background: linear-gradient(135deg, var(--primary-color) 0%, var(--primary-dark) 100%);
            color: white;
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-radius: 16px 16px 0 0;
        }}

        .modal-header.hymn {{
            background: linear-gradient(135deg, var(--accent-color) 0%, #B45309 100%);
        }}

        .modal-title {{
            font-size: 1.1em;
            font-weight: 700;
        }}

        .modal-close {{
            background: none;
            border: none;
            color: white;
            font-size: 1.5em;
            cursor: pointer;
            padding: 5px;
            line-height: 1;
        }}

        .modal-body {{
            padding: 20px;
            line-height: 1.8;
        }}

        .verse-num {{
            color: var(--primary-color);
            font-weight: 700;
            margin-right: 5px;
        }}

        .verse-label {{
            display: block;
            color: var(--accent-color);
            font-weight: 600;
            margin-top: 15px;
            margin-bottom: 5px;
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
            padding: 8px 0;
            z-index: 1000;
        }}

        body.dark-mode .bottom-nav {{
            background: #1F2937;
        }}

        .bottom-nav a {{
            display: flex;
            flex-direction: column;
            align-items: center;
            text-decoration: none;
            color: var(--text-light);
            font-size: 0.7em;
            padding: 5px 12px;
            transition: color 0.2s;
        }}

        .bottom-nav a.active {{
            color: var(--primary-color);
        }}

        .bottom-nav .nav-icon {{
            font-size: 1.6em;
            margin-bottom: 2px;
        }}

        /* Footer */
        .footer {{
            text-align: center;
            padding: 25px 20px;
            color: var(--text-light);
            font-size: 0.85em;
        }}

        .footer a {{
            color: var(--primary-color);
            text-decoration: none;
        }}

        /* Page Content */
        .page-content {{
            background: var(--bg-light);
            padding: 15px;
            border-radius: 10px;
            margin-bottom: 12px;
            border-left: 4px solid var(--primary-color);
        }}

        body.dark-mode .page-content {{
            background: #374151;
        }}

        .page-content h4 {{
            color: var(--primary-color);
            margin-bottom: 10px;
            font-size: 1em;
        }}

        .page-content p {{
            margin-bottom: 8px;
            line-height: 1.7;
            color: var(--text-dark);
        }}
    </style>
</head>
<body>
    <!-- Header -->
    <header class="header" id="header">
        <span class="header-title">{info.get('church_name', '교회')} 주보</span>
        <div class="header-actions">
            <button class="header-btn" onclick="toggleDarkMode()" title="다크모드">🌙</button>
            <button class="header-btn" onclick="shareLink()" title="공유">📤</button>
        </div>
    </header>

    <!-- Hero -->
    <section class="hero">
        <h1 class="hero-church">{info.get('church_name', '교회')}</h1>
        <p class="hero-date">{info.get('date', '')}</p>
        <p class="hero-service">{info.get('service_type', '주일예배')}</p>
    </section>

    <!-- SNS Links -->
    <div class="sns-bar">
        <a href="{sns.get('youtube', '#')}" target="_blank" class="sns-link youtube">
            <span class="sns-icon">▶️</span>
            <span>유튜브</span>
        </a>
        <a href="{sns.get('kakaotalk', '#')}" target="_blank" class="sns-link kakao">
            <span class="sns-icon">💬</span>
            <span>카카오톡</span>
        </a>
        <a href="{sns.get('instagram', '#')}" target="_blank" class="sns-link instagram">
            <span class="sns-icon">📷</span>
            <span>인스타그램</span>
        </a>
        <a href="{donation_url}" target="_blank" class="sns-link donation">
            <span class="sns-icon">💝</span>
            <span>헌금</span>
        </a>
    </div>

    <!-- Sermon Section -->
    <section class="section" id="sermon">
        <h2 class="section-title">📖 오늘의 말씀</h2>
        <div class="sermon-card">
            <h3 class="sermon-title">{info.get('sermon_title', '말씀 제목')}</h3>
            <p class="sermon-pastor">설교: {info.get('pastor', '담임목사')}</p>
            {self._generate_scripture_links(info.get('scripture', ''))}
        </div>
        {self._generate_hymn_links(info.get('hymns', []))}
    </section>

    <!-- Worship Order -->
    <section class="section" id="order">
        <h2 class="section-title">⛪ 예배 순서</h2>
        <ul class="worship-order">
            {self._generate_worship_order_html(info.get('worship_order', []))}
        </ul>
    </section>

    <!-- Church News -->
    <section class="section" id="news">
        <h2 class="section-title">📢 교회 소식</h2>
        {self._generate_church_news_html(info.get('news', []))}
    </section>

    <!-- Donation Section -->
    <div class="donation-section">
        <p class="donation-title">💝 온라인 헌금</p>
        <a href="{donation_url}" target="_blank" class="donation-btn">헌금하기</a>
    </div>

    <!-- Full Text -->
    <section class="section" id="fulltext">
        <h2 class="section-title">📄 전문보기</h2>
        {self._generate_church_page_contents_html(pages)}
    </section>

    <!-- Footer -->
    <footer class="footer">
        <p>{info.get('church_name', '교회')}</p>
        <p style="margin-top: 5px;">{info.get('address', '')}</p>
        <p style="margin-top: 10px;">
            <a href="https://studysnap.kr" target="_blank">StudySnap</a> | PDF를 모바일 콘텐츠로
        </p>
    </footer>

    <!-- Bottom Navigation -->
    <nav class="bottom-nav">
        <a href="#sermon" class="active">
            <span class="nav-icon">📖</span>
            말씀
        </a>
        <a href="#order">
            <span class="nav-icon">⛪</span>
            순서
        </a>
        <a href="#news">
            <span class="nav-icon">📢</span>
            소식
        </a>
        <a href="#fulltext">
            <span class="nav-icon">📄</span>
            전문
        </a>
    </nav>

    <!-- Bible Modal -->
    <div class="modal-overlay" id="bibleModal">
        <div class="modal-content">
            <div class="modal-header">
                <h2 class="modal-title" id="bibleModalTitle">성경구절</h2>
                <button class="modal-close" onclick="closeModal('bibleModal')">×</button>
            </div>
            <div class="modal-body" id="bibleModalContent"></div>
        </div>
    </div>

    <!-- Hymn Modal -->
    <div class="modal-overlay" id="hymnModal">
        <div class="modal-content">
            <div class="modal-header hymn">
                <h2 class="modal-title" id="hymnModalTitle">찬송가</h2>
                <button class="modal-close" onclick="closeModal('hymnModal')">×</button>
            </div>
            <div class="modal-body" id="hymnModalContent"></div>
        </div>
    </div>

    <script>
        // 성경구절 데이터 (실제 구현 시 API 또는 데이터베이스에서 가져옴)
        const bibleVerses = {{
            'default': {{
                title: '성경구절',
                content: '<p>{info.get("scripture", "성경구절을 로드할 수 없습니다.")}</p>'
            }}
        }};

        // 찬송가 데이터
        const hymns = {{}};

        // 성경구절 팝업 열기
        function openBibleModal(verseKey) {{
            const verse = bibleVerses[verseKey] || bibleVerses['default'];
            document.getElementById('bibleModalTitle').textContent = verse.title;
            document.getElementById('bibleModalContent').innerHTML = verse.content;
            document.getElementById('bibleModal').classList.add('active');
            document.body.style.overflow = 'hidden';
        }}

        // 찬송가 팝업 열기
        function openHymnModal(hymnNum) {{
            const hymn = hymns[hymnNum];
            if (hymn) {{
                document.getElementById('hymnModalTitle').textContent = '찬송가 ' + hymnNum + '장 - ' + hymn.title;
                document.getElementById('hymnModalContent').innerHTML = hymn.lyrics;
            }} else {{
                document.getElementById('hymnModalTitle').textContent = '찬송가 ' + hymnNum + '장';
                document.getElementById('hymnModalContent').innerHTML = '<p>가사 정보를 로드할 수 없습니다.</p>';
            }}
            document.getElementById('hymnModal').classList.add('active');
            document.body.style.overflow = 'hidden';
        }}

        // 모달 닫기
        function closeModal(modalId) {{
            document.getElementById(modalId).classList.remove('active');
            document.body.style.overflow = '';
        }}

        // 모달 외부 클릭 시 닫기
        document.querySelectorAll('.modal-overlay').forEach(modal => {{
            modal.addEventListener('click', (e) => {{
                if (e.target === modal) {{
                    modal.classList.remove('active');
                    document.body.style.overflow = '';
                }}
            }});
        }});

        // 다크모드 토글
        function toggleDarkMode() {{
            document.body.classList.toggle('dark-mode');
            localStorage.setItem('darkMode', document.body.classList.contains('dark-mode'));
        }}

        // 다크모드 초기화
        if (localStorage.getItem('darkMode') === 'true') {{
            document.body.classList.add('dark-mode');
        }}

        // 링크 공유
        function shareLink() {{
            if (navigator.share) {{
                navigator.share({{
                    title: '{info.get("church_name", "교회")} 주보 - {info.get("date", "")}',
                    text: '{info.get("sermon_title", "오늘의 말씀")}',
                    url: window.location.href
                }});
            }} else {{
                navigator.clipboard.writeText(window.location.href);
                alert('링크가 복사되었습니다!');
            }}
        }}

        // 헤더 스크롤 숨김
        let lastScroll = 0;
        window.addEventListener('scroll', () => {{
            const currentScroll = window.scrollY;
            const header = document.getElementById('header');

            if (currentScroll > lastScroll && currentScroll > 150) {{
                header.classList.add('hidden');
            }} else {{
                header.classList.remove('hidden');
            }}
            lastScroll = currentScroll;
        }});

        // 네비게이션 스크롤 스파이
        const sections = ['sermon', 'order', 'news', 'fulltext'];
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

        // 부드러운 스크롤
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
    </script>
</body>
</html>'''

    def _extract_church_info(self, text: str, title: str, structured_data: Dict = None) -> Dict:
        """교회 주보 정보 추출"""
        info = {
            "church_name": "",
            "date": "",
            "service_type": "",
            "sermon_title": "",
            "pastor": "",
            "scripture": "",
            "hymns": [],
            "worship_order": [],
            "news": [],
            "address": "",
            "sns": {},
            "donation_url": "https://m.fgtv.com/donate/donate_m_ver2.asp"
        }

        # structured_data 우선 사용
        if structured_data:
            info["church_name"] = structured_data.get("church_name", "")
            info["date"] = structured_data.get("date", "")
            info["service_type"] = structured_data.get("service_type", "")
            info["sermon_title"] = structured_data.get("sermon_title", "")
            info["pastor"] = structured_data.get("pastor", "")
            info["scripture"] = structured_data.get("scripture", "")
            info["hymns"] = structured_data.get("hymns", [])
            info["worship_order"] = structured_data.get("worship_order", [])
            info["news"] = structured_data.get("news", [])
            info["address"] = structured_data.get("address", "")
            info["sns"] = structured_data.get("sns", {})

        # 텍스트에서 추가 정보 추출
        # 교회 이름
        if not info["church_name"]:
            church_patterns = [
                r'(여의도순복음교회)',
                r'([가-힣]+교회)',
            ]
            for pattern in church_patterns:
                match = re.search(pattern, text)
                if match:
                    info["church_name"] = match.group(1)
                    break
            if not info["church_name"] and title:
                info["church_name"] = title.split('_')[0] if '_' in title else title.replace('.pdf', '')

        # 날짜 추출
        if not info["date"]:
            date_patterns = [
                r'(\d{4})\s*[.년]\s*(\d{1,2})\s*[.월]\s*(\d{1,2})',
                r'(\d{4})[-/](\d{1,2})[-/](\d{1,2})',
            ]
            for pattern in date_patterns:
                match = re.search(pattern, text)
                if match:
                    info["date"] = f"{match.group(1)}년 {match.group(2)}월 {match.group(3)}일"
                    break

        # 예배 유형
        if not info["service_type"]:
            service_types = ["주일1부예배", "주일2부예배", "주일3부예배", "주일예배", "수요예배", "금요철야예배"]
            for st in service_types:
                if st in text:
                    info["service_type"] = st
                    break
            if not info["service_type"]:
                info["service_type"] = "주일예배"

        # 설교 제목
        if not info["sermon_title"]:
            sermon_patterns = [
                r'설교[제목\s:：]*[：:\s]*([^\n]{5,50})',
                r'말씀[제목\s:：]*[：:\s]*([^\n]{5,50})',
            ]
            for pattern in sermon_patterns:
                match = re.search(pattern, text)
                if match:
                    info["sermon_title"] = match.group(1).strip()
                    break

        # 목사님
        if not info["pastor"]:
            pastor_patterns = [
                r'설교[자\s:：]*[：:\s]*([가-힣]+\s*목사)',
                r'([가-힣]+\s*담임목사)',
                r'([가-힣]{2,4})\s*목사',
            ]
            for pattern in pastor_patterns:
                match = re.search(pattern, text)
                if match:
                    info["pastor"] = match.group(1).strip()
                    break

        # 성경구절
        if not info["scripture"]:
            scripture_patterns = [
                r'본문[：:\s]*([가-힣]+\s*\d+[：:]\d+[-~]\d+)',
                r'([가-힣]+\s*\d+장\s*\d+절)',
                r'(창세기|출애굽기|레위기|민수기|신명기|여호수아|사사기|룻기|사무엘|열왕기|역대|에스라|느헤미야|에스더|욥기|시편|잠언|전도서|아가|이사야|예레미야|예레미야애가|에스겔|다니엘|호세아|요엘|아모스|오바댜|요나|미가|나훔|하박국|스바냐|학개|스가랴|말라기|마태복음|마가복음|누가복음|요한복음|사도행전|로마서|고린도전서|고린도후서|갈라디아서|에베소서|빌립보서|골로새서|데살로니가전서|데살로니가후서|디모데전서|디모데후서|디도서|빌레몬서|히브리서|야고보서|베드로전서|베드로후서|요한1서|요한2서|요한3서|유다서|요한계시록)\s*\d+[：:]\d+',
            ]
            for pattern in scripture_patterns:
                match = re.search(pattern, text)
                if match:
                    info["scripture"] = match.group(0).strip()
                    break

        # 찬송가 번호 추출
        if not info["hymns"]:
            hymn_matches = re.findall(r'찬송[가\s]*(\d+)장?', text)
            info["hymns"] = list(set(hymn_matches))[:5]

        # 모든 텍스트 필드 정리
        for key in ["church_name", "date", "service_type", "sermon_title", "pastor", "scripture", "address"]:
            info[key] = self._clean_text(info[key])

        return info

    def _generate_scripture_links(self, scripture: str) -> str:
        """성경구절 링크 생성"""
        if not scripture:
            return ""

        scripture_escaped = scripture.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
        return f'''<span class="sermon-scripture" onclick="openBibleModal('default')">📖 {scripture_escaped}</span>'''

    def _generate_hymn_links(self, hymns: List[str]) -> str:
        """찬송가 링크 생성"""
        if not hymns:
            return ""

        html = '<div style="margin-top: 15px;">'
        for hymn_num in hymns:
            html += f'<span class="hymn-link" onclick="openHymnModal(\'{hymn_num}\')">🎵 찬송가 {hymn_num}장</span>'
        html += '</div>'
        return html

    def _generate_worship_order_html(self, worship_order: List) -> str:
        """예배 순서 HTML 생성"""
        if not worship_order:
            # 기본 예배 순서
            worship_order = [
                {"name": "예배의 부름", "detail": ""},
                {"name": "찬양", "detail": ""},
                {"name": "기도", "detail": ""},
                {"name": "성경봉독", "detail": ""},
                {"name": "설교", "detail": ""},
                {"name": "봉헌", "detail": ""},
                {"name": "축도", "detail": ""},
            ]

        html = ""
        for i, item in enumerate(worship_order, 1):
            if isinstance(item, dict):
                name = item.get("name", "")
                detail = item.get("detail", "")
            else:
                name = str(item)
                detail = ""

            name_escaped = name.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
            detail_escaped = detail.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;') if detail else ""

            html += f'''
            <li class="worship-item">
                <span class="worship-number">{i}</span>
                <div class="worship-content">
                    <div class="worship-name">{name_escaped}</div>
                    {'<div class="worship-detail">' + detail_escaped + '</div>' if detail_escaped else ''}
                </div>
            </li>'''

        return html

    def _generate_church_news_html(self, news: List) -> str:
        """교회 소식 HTML 생성"""
        if not news:
            return '<p style="color: var(--text-light); text-align: center; padding: 20px;">교회 소식을 추출할 수 없습니다.</p>'

        html = ""
        for item in news:
            if isinstance(item, dict):
                title = item.get("title", "")
                content = item.get("content", "")
            else:
                title = ""
                content = str(item)

            title_escaped = title.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;') if title else ""
            content_escaped = content.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
            content_escaped = content_escaped.replace('\n', '<br>')

            html += f'''
            <div class="news-item">
                {'<div class="news-title">' + title_escaped + '</div>' if title_escaped else ''}
                <div class="news-content">{content_escaped}</div>
            </div>'''

        return html

    def _generate_church_page_contents_html(self, pages: List[Dict]) -> str:
        """교회 주보 페이지별 내용 HTML 생성"""
        if not pages:
            return ""

        html = ""
        for page in pages:
            page_num = page.get("page_number", 1)
            text = page.get("text", "").strip()

            if text:
                formatted_text = self._format_page_text(text)
                html += f'''
        <div class="page-content">
            <h4>📄 페이지 {page_num}</h4>
            {formatted_text}
        </div>'''

        return html
