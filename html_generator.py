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
