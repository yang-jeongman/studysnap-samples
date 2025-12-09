"""
PDF에서 모바일 최적화 HTML 자동 생성
이전에 수동으로 편집한 파일과 비교 가능
"""

import fitz  # PyMuPDF
import json
import os
from datetime import datetime
from learning_data.classifier import ObjectClassifier, LayoutAnalyzer
from learning_data.schema import ObjectType, PDFObject, BoundingBox, TextStyle, FontStyle, TextAlignment


def extract_objects_from_pdf(pdf_path: str) -> list:
    """PDF에서 객체 추출"""
    doc = fitz.open(pdf_path)
    objects = []
    obj_id = 0

    for page_num, page in enumerate(doc):
        blocks = page.get_text("dict")["blocks"]

        for block in blocks:
            if "lines" not in block:
                continue

            for line in block["lines"]:
                for span in line["spans"]:
                    text = span["text"].strip()
                    if not text:
                        continue

                    # 스타일 정보 추출
                    font_size = span["size"]
                    font_name = span["font"]
                    color_int = span["color"]
                    color_hex = f"#{color_int:06x}"

                    # 폰트 스타일 판단
                    font_style = FontStyle.REGULAR
                    if "Bold" in font_name or "bold" in font_name:
                        font_style = FontStyle.BOLD
                    elif "Italic" in font_name or "italic" in font_name:
                        font_style = FontStyle.ITALIC

                    bbox = span["bbox"]

                    style = TextStyle(
                        font_name=font_name,
                        font_size=font_size,
                        font_style=font_style,
                        color=color_hex,
                        alignment=TextAlignment.LEFT
                    )

                    pdf_obj = PDFObject(
                        id=f"obj_{obj_id}",
                        object_type=ObjectType.PARAGRAPH,  # 초기값, 분류기가 결정
                        content=text,
                        bbox=BoundingBox(
                            x=bbox[0],
                            y=bbox[1],
                            width=bbox[2] - bbox[0],
                            height=bbox[3] - bbox[1],
                            page=page_num + 1
                        ),
                        style=style,
                        source_page=page_num + 1
                    )
                    objects.append(pdf_obj)
                    obj_id += 1

    doc.close()
    return objects


def generate_mobile_html(layout: dict) -> str:
    """모바일 레이아웃 데이터를 HTML로 변환"""

    # CSS 스타일 - 국민의힘 색상 (빨간/분홍 계열, 파란색 배제)
    css = """
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Pretendard', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            background: linear-gradient(180deg, #FFE4E6 0%, #FECDD3 100%);
            min-height: 100vh;
            padding: 15px;
            line-height: 1.6;
        }
        .container {
            max-width: 480px;
            margin: 0 auto;
            background: #FFF5F5;
            border-radius: 20px;
            padding: 15px;
        }

        /* 히어로 섹션 */
        .hero {
            text-align: center;
            padding: 30px 20px;
            background: white;
            border-radius: 15px;
            margin-bottom: 20px;
            box-shadow: 0 4px 15px rgba(0,0,0,0.08);
        }
        .hero .party {
            display: inline-block;
            background: #E11D48;
            color: white;
            padding: 8px 24px;
            border-radius: 30px;
            font-size: 14px;
            font-weight: 600;
            margin-bottom: 15px;
        }
        .hero .candidate {
            font-size: 42px;
            font-weight: 800;
            color: #1a1a1a;
            margin: 10px 0;
        }
        .hero .slogan {
            font-size: 16px;
            color: #E11D48;
            font-weight: 600;
            margin-top: 10px;
        }

        /* 요약 카드 (핵심공약 6개, 주요실적 7건) */
        .summary-cards {
            display: flex;
            gap: 10px;
            margin-bottom: 20px;
        }
        .summary-card {
            flex: 1;
            background: white;
            border-radius: 12px;
            padding: 15px;
            text-align: center;
            border: 2px solid #FECDD3;
        }
        .summary-card .number {
            font-size: 28px;
            font-weight: 800;
            color: #E11D48;
        }
        .summary-card .label {
            font-size: 13px;
            color: #666;
            margin-top: 5px;
        }

        /* 섹션 제목 */
        .section-title {
            color: #1a1a1a;
            font-size: 18px;
            font-weight: 700;
            margin: 25px 0 15px;
            padding: 10px 15px;
            background: #FEE2E2;
            border-radius: 10px;
            border-left: 4px solid #E11D48;
        }

        /* 핵심공약/실적 카드 (확장형) */
        .expandable-list {
            background: white;
            border-radius: 15px;
            overflow: hidden;
            box-shadow: 0 2px 10px rgba(0,0,0,0.05);
        }
        .expandable-item {
            border-bottom: 1px solid #FEE2E2;
        }
        .expandable-item:last-child {
            border-bottom: none;
        }
        .expandable-header {
            display: flex;
            align-items: center;
            padding: 15px;
            cursor: pointer;
            transition: background 0.2s;
        }
        .expandable-header:hover {
            background: #FFF5F5;
        }
        .expandable-number {
            width: 32px;
            height: 32px;
            background: #E11D48;
            color: white;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-weight: 700;
            font-size: 14px;
            margin-right: 12px;
            flex-shrink: 0;
        }
        .expandable-content {
            flex: 1;
        }
        .expandable-title {
            font-size: 15px;
            font-weight: 600;
            color: #1a1a1a;
        }
        .expandable-subtitle {
            font-size: 12px;
            color: #888;
            margin-top: 2px;
        }
        .expandable-toggle {
            color: #E11D48;
            font-size: 13px;
            padding: 5px 10px;
            transition: transform 0.3s;
        }
        .expandable-toggle.open {
            transform: rotate(180deg);
        }

        /* 상세 내용 영역 */
        .expandable-details {
            max-height: 0;
            overflow: hidden;
            transition: max-height 0.3s ease-out;
            background: #FEFEFE;
        }
        .expandable-details.open {
            max-height: 1000px;
        }
        .details-inner {
            padding: 15px 15px 15px 60px;
            border-top: 1px dashed #FEE2E2;
        }
        .details-text {
            font-size: 14px;
            color: #444;
            line-height: 1.8;
            margin-bottom: 15px;
        }
        .details-text ul {
            margin: 10px 0;
            padding-left: 20px;
        }
        .details-text li {
            margin: 5px 0;
        }

        /* 버튼 그룹 */
        .btn-group {
            display: flex;
            gap: 10px;
            margin-top: 10px;
        }
        .btn {
            flex: 1;
            padding: 10px 15px;
            border-radius: 8px;
            font-size: 13px;
            font-weight: 600;
            text-align: center;
            cursor: pointer;
            transition: all 0.2s;
            text-decoration: none;
        }
        .btn-primary {
            background: #E11D48;
            color: white;
        }
        .btn-primary:hover {
            background: #BE123C;
        }
        .btn-secondary {
            background: #FEE2E2;
            color: #E11D48;
        }
        .btn-secondary:hover {
            background: #FECDD3;
        }

        /* 주요실적 그룹 제목 */
        .achievement-group {
            margin-bottom: 15px;
        }
        .achievement-group-title {
            font-size: 14px;
            font-weight: 700;
            color: #E11D48;
            margin-bottom: 10px;
            padding: 10px 15px;
            background: #FFF5F5;
            border-radius: 10px 10px 0 0;
        }

        /* 동별공약 지도 섹션 */
        .district-map-section {
            background: white;
            border-radius: 15px;
            padding: 15px;
            margin-bottom: 15px;
        }
        .district-map {
            position: relative;
            width: 100%;
            height: 300px;
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
            fill: #FEE2E2;
            stroke: #E11D48;
            stroke-width: 1.5;
            cursor: pointer;
            transition: all 0.3s;
        }
        .district-area:hover {
            fill: #FECDD3;
        }
        .district-area.active {
            fill: #E11D48;
        }
        .district-label {
            font-size: 10px;
            font-weight: 600;
            fill: #333;
            pointer-events: none;
            text-anchor: middle;
        }
        .district-area.active + .district-label {
            fill: white;
        }

        /* 선택된 동 정보 */
        .district-info {
            display: none;
            padding: 15px;
            background: #FFF5F5;
            border-radius: 12px;
            margin-top: 10px;
        }
        .district-info.active {
            display: block;
        }
        .district-info-title {
            font-size: 16px;
            font-weight: 700;
            color: #E11D48;
            margin-bottom: 10px;
        }
        .district-info-content {
            font-size: 14px;
            color: #444;
            line-height: 1.7;
        }

        /* 연락처 */
        .contact-section {
            background: white;
            border-radius: 15px;
            padding: 20px;
            margin-top: 20px;
        }
        .contact-section .title {
            font-size: 16px;
            font-weight: 700;
            color: #333;
            margin-bottom: 15px;
        }
        .contact-item {
            padding: 10px 0;
            border-bottom: 1px solid #eee;
            font-size: 14px;
            color: #555;
        }
        .contact-item:last-child {
            border-bottom: none;
        }

        /* 푸터 */
        .footer {
            text-align: center;
            padding: 30px 20px;
            color: rgba(255,255,255,0.7);
            font-size: 12px;
        }

        /* 모달 (원문보기) */
        .modal-overlay {
            display: none;
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0,0,0,0.8);
            z-index: 1000;
            justify-content: center;
            align-items: center;
        }
        .modal-overlay.active {
            display: flex;
        }
        .modal-content {
            background: white;
            border-radius: 15px;
            max-width: 90%;
            max-height: 90%;
            overflow: auto;
            position: relative;
        }
        .modal-close {
            position: absolute;
            top: 10px;
            right: 10px;
            width: 30px;
            height: 30px;
            background: #E11D48;
            color: white;
            border: none;
            border-radius: 50%;
            cursor: pointer;
            font-size: 18px;
            z-index: 10;
        }
        .modal-image {
            width: 100%;
            height: auto;
        }
    </style>
    """

    # 핵심공약 6개 (고정 - PDF 6~7페이지 기준) - 상세 내용 포함
    core_pledges = [
        {
            "number": 1,
            "title": "교육특구 동작",
            "subtitle": "동작을 8학군 수준으로",
            "details": """
                <ul>
                    <li>초·중·고 학력 향상 특별 프로그램 도입</li>
                    <li>방과후 학교 무료 확대</li>
                    <li>영재교육원 유치 및 확대</li>
                    <li>진로·진학 컨설팅 무료 제공</li>
                    <li>학교 시설 현대화 (에어컨, 공기청정기 등)</li>
                </ul>
            """,
            "image": "/outputs/pledge1.png",
            "has_map": False
        },
        {
            "number": 2,
            "title": "사통팔달 동작",
            "subtitle": "서울 내부순환 급행전용 철도망",
            "details": """
                <ul>
                    <li>GTX-D 동작역 유치 추진</li>
                    <li>신림선·서부선 연장 추진</li>
                    <li>노량진역 환승센터 구축</li>
                    <li>마을버스 노선 확대</li>
                    <li>교통약자 이동편의 증진</li>
                </ul>
            """,
            "image": "/outputs/pledge2-2.png",
            "map_image": "/outputs/pledge2-1.png",
            "has_map": True
        },
        {
            "number": 3,
            "title": "상전벽해 동작",
            "subtitle": "노량진 뉴타운, 스카이라인 확보",
            "details": """
                <ul>
                    <li>노량진 수산시장 현대화</li>
                    <li>노량진 재정비 촉진지구 활성화</li>
                    <li>사당역 일대 도시재생</li>
                    <li>노후 아파트 리모델링 지원</li>
                    <li>한강변 스카이라인 조성</li>
                </ul>
            """,
            "image": "/outputs/pledge3.png",
            "has_map": False
        },
        {
            "number": 4,
            "title": "15분도시 동작",
            "subtitle": "도서관, 체육관, 공원 15분 내",
            "details": """
                <ul>
                    <li>동별 작은도서관 확충</li>
                    <li>생활체육시설 확대</li>
                    <li>동네공원 리모델링</li>
                    <li>주민커뮤니티센터 신설</li>
                    <li>걷고 싶은 거리 조성</li>
                </ul>
            """,
            "image": "/outputs/pledge4.png",
            "has_map": False
        },
        {
            "number": 5,
            "title": "든든복지 동작",
            "subtitle": "어르신, 장애인, 아이 돌봄",
            "details": """
                <ul>
                    <li>어르신 일자리 확대</li>
                    <li>장애인 활동지원 강화</li>
                    <li>국공립어린이집 확충</li>
                    <li>돌봄교실 확대</li>
                    <li>경로당 시설 현대화</li>
                </ul>
            """,
            "image": "/outputs/pledge5.png",
            "has_map": False
        },
        {
            "number": 6,
            "title": "안심안전 동작",
            "subtitle": "범죄예방, CCTV, 안전통학로",
            "details": """
                <ul>
                    <li>CCTV 사각지대 해소</li>
                    <li>안전통학로 확대</li>
                    <li>여성안심귀갓길 조성</li>
                    <li>재난안전 대응체계 강화</li>
                    <li>소방·응급 인프라 확충</li>
                </ul>
            """,
            "image": "/outputs/pledge6.png",
            "has_map": False
        },
    ]

    # 주요실적 - PDF 4~5페이지 기준 (핵심공약 내용 참조 금지)
    # 나경원이 바꾼 동작: 동작 주민들과 함께한 10년의 시간
    achievements_structured = {
        "나경원이 바꾼 동작": [
            {
                "title": "교육동작",
                "subtitle": "아이 키우기 좋은 동네, 교육동작 기반 만들기",
                "details": """
                    <ul>
                        <li>30년 만의 숙원 해결! 흑석동 공립고교 신설 확정</li>
                        <li>사당3동 맘스하트카페 3호점 개관</li>
                        <li>흑석동 구립까망돌어린이집 등 보육시설 신설</li>
                        <li>2014~2020 교육 환경개선 및 동작발전 예산 총 774억원</li>
                        <li>2022~2024 학교 시설환경개선비 247억원 확정</li>
                    </ul>
                """,
                "page": 4
            },
            {
                "title": "교통동작",
                "subtitle": "삶의 질이 오르는, 즐거운 동작 - 서울 주요 도심을 잇는 심장",
                "details": """
                    <ul>
                        <li><strong>서리풀터널 개통</strong> - 이수에서 강남까지 8분!</li>
                        <li>30년간 1,890억원의 편익 발생 추정 (서울시, 서초구, 국방부간 공조 추진)</li>
                        <li>사당로 3차구간 확장사업 착공</li>
                        <li>사당역 방향 마을버스 전용차로 이용</li>
                        <li>40년 끊겨있던 일류동작의 지름길 개통</li>
                    </ul>
                """,
                "page": 4
            },
            {
                "title": "문화동작",
                "subtitle": "더 좋아진 도서관, 체육관, 놀이터",
                "details": """
                    <ul>
                        <li>흑석복합도서관 건립</li>
                        <li>흑석체육센터 증축 및 개보수 완료</li>
                        <li>사당문화회관 리모델링</li>
                        <li>현충근린공원 정비</li>
                        <li>까치어린이공원 안전놀이터 조성</li>
                    </ul>
                """,
                "page": 4
            },
            {
                "title": "동별 성과",
                "subtitle": "각 동별 맞춤 성과",
                "details": """
                    <ul>
                        <li><strong>사당1,2동</strong>: 한전 남부지사 부지개발 확정, 남성사계시장 현대화, 까치어린이공원 안전놀이터 조성완료</li>
                        <li><strong>사당3,4,5동</strong>: 사당종합체육관 개관, 삼일공원 내 유관순 열사상 건립, 가족친화형 공원 5개소 조성</li>
                        <li><strong>상도1동</strong>: 동작구 가족센터 건립, 힐스테이트 아파트브랜드 변경, 청년창업지원센터 건립</li>
                        <li><strong>흑석동</strong>: 효사정 문화공원 조성, 국립현충원 둘레길 통문 개방, 6.25 한강방어선전투 전사자 명비 제작</li>
                    </ul>
                """,
                "page": 5
            },
        ],
        "나경원이 바꾼 대한민국": [
            {
                "title": "진심",
                "subtitle": "흔들림 없이 지켜온 원칙과 가치",
                "details": """
                    <ul>
                        <li>보수정당 최초 여성 원내대표</li>
                        <li>헌정 최초 여성 외교통일위원장</li>
                        <li>공수처·선거법, 종전선언 일방 강행에 맞서 지켜온 원칙</li>
                        <li>중국 및 주요 4개국 FTA, 북한인권법 통과로 지켜낸 자유의 가치</li>
                    </ul>
                """,
                "page": 5
            },
            {
                "title": "동행",
                "subtitle": "변함없는 약자와의 동행",
                "details": """
                    <ul>
                        <li>국회 장애인특위 최초 구성</li>
                        <li>장애인 지원 교육·교통·주거 5대 법안 대표발의 및 예산확보</li>
                        <li>2013 평창 동계 스페셜올림픽 세계대회 조직위원장, IPC 집행위원</li>
                        <li>「부가가치세법」 개정으로 서민·소상공인 비과세 한도 상향</li>
                        <li>「조세특례제한법」 개정으로 새마을금고 예금이자 비과세 혜택 부여</li>
                    </ul>
                """,
                "page": 5
            },
            {
                "title": "변화",
                "subtitle": "시대 흐름을 읽고 미래를 준비하다",
                "details": """
                    <ul>
                        <li>국회 저출산고령화대책특위 위원장</li>
                        <li>대통령직속 저출산고령사회 부위원장</li>
                        <li>외교부 기후환경대사</li>
                        <li>싱크탱크 인구와기후그리고내일(PACT) 이사장</li>
                        <li>세계경제포럼(WEF, 다보스포럼) 대통령 특사</li>
                    </ul>
                """,
                "page": 5
            },
        ]
    }

    # 주요실적 헤더 텍스트
    achievements_header = """동작 주민들과 함께한 10년의 시간<br>
주민들이 들려주신 1,000여개의 이야기로<br>
동작의 오늘을 보고 내일을 그려갑니다."""

    # 동별공약 데이터 (동작구 15개 동)
    district_pledges_data = {
        "노량진1동": {"pledges": "학원가 청년 주거 지원, 노량진 수산시장 현대화", "page": 8},
        "노량진2동": {"pledges": "노량진역 환승센터, 재개발 촉진", "page": 8},
        "상도1동": {"pledges": "숭실대 연계 창업지원, 골목상권 활성화", "page": 8},
        "상도2동": {"pledges": "경로당 현대화, 주민커뮤니티센터 신설", "page": 8},
        "상도3동": {"pledges": "어린이공원 리모델링, 안전통학로 조성", "page": 9},
        "상도4동": {"pledges": "마을버스 노선 확대, CCTV 확충", "page": 9},
        "흑석동": {"pledges": "중앙대 연계 교육혁신, 한강변 조성", "page": 9},
        "사당1동": {"pledges": "사당역 환승센터, 남태령 터널 확장", "page": 9},
        "사당2동": {"pledges": "까치산 공원 정비, 경로복지관 확충", "page": 10},
        "사당3동": {"pledges": "방배천 생태공원 연결, 도서관 신설", "page": 10},
        "사당4동": {"pledges": "이수역 상권 활성화, 청년 창업지원", "page": 10},
        "사당5동": {"pledges": "어르신 일자리 확대, 돌봄서비스 강화", "page": 10},
        "대방동": {"pledges": "여의도 접근성 개선, 1인가구 지원", "page": 11},
        "신대방1동": {"pledges": "보라매공원 연계, 체육시설 확충", "page": 11},
        "신대방2동": {"pledges": "국공립어린이집 확충, 방과후교실 확대", "page": 11},
    }

    # HTML 생성
    html_parts = [f"""<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>나경원 후보 - 모바일 선거공보</title>
    {css}
</head>
<body>
<div class="container">
"""]

    # 히어로 섹션
    hero = layout.get("hero_section")
    candidate = hero.get("candidate", "나경원") if hero else "나경원"
    slogan = hero.get("slogan", "나만 믿어요 새로운 동작!") if hero else "나만 믿어요 새로운 동작!"

    html_parts.append(f"""
    <div class="hero">
        <div class="party">국민의힘</div>
        <div class="candidate">{candidate}</div>
        <div class="slogan">{slogan}</div>
    </div>
""")

    # 요약 카드 (핵심공약 6개, 주요실적 7건)
    html_parts.append("""
    <div class="summary-cards">
        <div class="summary-card">
            <div class="number">6개</div>
            <div class="label">핵심 공약</div>
        </div>
        <div class="summary-card">
            <div class="number">7건</div>
            <div class="label">주요 실적</div>
        </div>
    </div>
""")

    # 핵심공약 6개 (확장형 형식)
    html_parts.append('    <div class="section-title">핵심 공약</div>\n')
    html_parts.append('    <div class="expandable-list">\n')

    for pledge in core_pledges:
        # 버튼 생성 - 지도보기가 있는 경우 2개 버튼
        if pledge.get("has_map"):
            buttons_html = f"""
                    <div class="btn-group">
                        <button class="btn btn-secondary" onclick="showImage('{pledge.get('map_image', '')}')">🗺️ 지도보기</button>
                        <button class="btn btn-secondary" onclick="showImage('{pledge.get('image', '')}')">📄 원문보기</button>
                    </div>
"""
        else:
            buttons_html = f"""
                    <div class="btn-group">
                        <button class="btn btn-secondary" onclick="showImage('{pledge.get('image', '')}')">📄 원문보기</button>
                    </div>
"""
        html_parts.append(f"""
        <div class="expandable-item">
            <div class="expandable-header" onclick="toggleExpand(this)">
                <div class="expandable-number">{pledge["number"]}</div>
                <div class="expandable-content">
                    <div class="expandable-title">{pledge["title"]}</div>
                    <div class="expandable-subtitle">{pledge["subtitle"]}</div>
                </div>
                <div class="expandable-toggle">▼</div>
            </div>
            <div class="expandable-details">
                <div class="details-inner">
                    <div class="details-text">
                        {pledge["details"]}
                    </div>
                    {buttons_html}
                </div>
            </div>
        </div>
""")
    html_parts.append('    </div>\n')

    # 주요실적 7건 (핵심공약과 동일한 확장형 형식)
    html_parts.append('    <div class="section-title">주요 실적</div>\n')

    # 주요실적 헤더 텍스트 (그룹별로 다름)
    achievements_headers = {
        "나경원이 바꾼 동작": """동작 주민들과 함께한 10년의 시간<br>
주민들이 들려주신 1,000여개의 이야기로<br>
동작의 오늘을 보고 내일을 그려갑니다.""",
        "나경원이 바꾼 대한민국": """지속가능한 대한민국, 더 좋은 내일을 위해<br>
통합의 정치를 바로 세우고, 국민의 삶을 치유하겠습니다."""
    }

    item_number = 1
    for group_title, items in achievements_structured.items():
        header_text = achievements_headers.get(group_title, "")
        html_parts.append(f"""
    <div class="achievement-group">
        <div class="achievement-group-title">{group_title}</div>
        <div style="padding: 10px 15px; font-size: 13px; color: #666; line-height: 1.6; background: #FFF5F5; border-radius: 0 0 10px 10px; margin-bottom: 10px;">
            {header_text}
        </div>
        <div class="expandable-list">
""")
        for item in items:
            html_parts.append(f"""
            <div class="expandable-item">
                <div class="expandable-header" onclick="toggleExpand(this)">
                    <div class="expandable-number" style="background: #BE123C;">{item_number}</div>
                    <div class="expandable-content">
                        <div class="expandable-title">{item["title"]}</div>
                        <div class="expandable-subtitle">{item["subtitle"]}</div>
                    </div>
                    <div class="expandable-toggle">▼</div>
                </div>
                <div class="expandable-details">
                    <div class="details-inner">
                        <div class="details-text">
                            {item["details"]}
                        </div>
                    </div>
                </div>
            </div>
""")
            item_number += 1
        html_parts.append('        </div>\n    </div>\n')

    # 동별 공약 (지도 포함)
    html_parts.append('    <div class="section-title">동별 공약</div>\n')
    html_parts.append("""
    <div class="district-map-section">
        <div class="district-map">
            <svg viewBox="0 0 400 300" preserveAspectRatio="xMidYMid meet">
                <!-- 동작구 지도 (간략화된 형태) -->
                <!-- 상단: 노량진, 흑석 -->
                <path class="district-area" data-district="노량진1동" d="M50,30 L100,25 L110,60 L60,65 Z" onclick="selectDistrict('노량진1동')"/>
                <text class="district-label" x="75" y="50">노량진1</text>

                <path class="district-area" data-district="노량진2동" d="M100,25 L160,20 L165,55 L110,60 Z" onclick="selectDistrict('노량진2동')"/>
                <text class="district-label" x="130" y="45">노량진2</text>

                <path class="district-area" data-district="흑석동" d="M160,20 L250,15 L260,70 L165,55 Z" onclick="selectDistrict('흑석동')"/>
                <text class="district-label" x="205" y="45">흑석동</text>

                <!-- 중상단: 상도 -->
                <path class="district-area" data-district="상도1동" d="M60,65 L110,60 L115,100 L65,105 Z" onclick="selectDistrict('상도1동')"/>
                <text class="district-label" x="85" y="85">상도1</text>

                <path class="district-area" data-district="상도2동" d="M110,60 L165,55 L170,95 L115,100 Z" onclick="selectDistrict('상도2동')"/>
                <text class="district-label" x="138" y="80">상도2</text>

                <path class="district-area" data-district="상도3동" d="M65,105 L115,100 L120,140 L70,145 Z" onclick="selectDistrict('상도3동')"/>
                <text class="district-label" x="90" y="125">상도3</text>

                <path class="district-area" data-district="상도4동" d="M115,100 L170,95 L175,135 L120,140 Z" onclick="selectDistrict('상도4동')"/>
                <text class="district-label" x="143" y="120">상도4</text>

                <!-- 중앙: 사당 -->
                <path class="district-area" data-district="사당1동" d="M70,145 L120,140 L125,185 L75,190 Z" onclick="selectDistrict('사당1동')"/>
                <text class="district-label" x="95" y="165">사당1</text>

                <path class="district-area" data-district="사당2동" d="M120,140 L175,135 L180,180 L125,185 Z" onclick="selectDistrict('사당2동')"/>
                <text class="district-label" x="148" y="160">사당2</text>

                <path class="district-area" data-district="사당3동" d="M175,135 L235,130 L240,175 L180,180 Z" onclick="selectDistrict('사당3동')"/>
                <text class="district-label" x="205" y="155">사당3</text>

                <path class="district-area" data-district="사당4동" d="M75,190 L125,185 L130,230 L80,235 Z" onclick="selectDistrict('사당4동')"/>
                <text class="district-label" x="100" y="210">사당4</text>

                <path class="district-area" data-district="사당5동" d="M125,185 L180,180 L185,225 L130,230 Z" onclick="selectDistrict('사당5동')"/>
                <text class="district-label" x="153" y="205">사당5</text>

                <!-- 우측: 대방, 신대방 -->
                <path class="district-area" data-district="대방동" d="M260,70 L340,60 L350,130 L270,140 Z" onclick="selectDistrict('대방동')"/>
                <text class="district-label" x="300" y="100">대방동</text>

                <path class="district-area" data-district="신대방1동" d="M270,140 L350,130 L360,200 L280,210 Z" onclick="selectDistrict('신대방1동')"/>
                <text class="district-label" x="310" y="170">신대방1</text>

                <path class="district-area" data-district="신대방2동" d="M280,210 L360,200 L370,270 L290,280 Z" onclick="selectDistrict('신대방2동')"/>
                <text class="district-label" x="320" y="240">신대방2</text>
            </svg>
        </div>
        <p style="text-align: center; font-size: 13px; color: #888; margin-bottom: 15px;">
            지도를 클릭하여 동별 공약을 확인하세요
        </p>
""")

    # 각 동별 정보 패널
    for dong, data in district_pledges_data.items():
        html_parts.append(f"""
        <div class="district-info" id="info-{dong}">
            <div class="district-info-title">📍 {dong}</div>
            <div class="district-info-content">{data["pledges"]}</div>
            <div class="btn-group" style="margin-top: 15px;">
                <button class="btn btn-secondary" onclick="showOriginal({data['page']})">📄 원문보기</button>
            </div>
        </div>
""")
    html_parts.append('    </div>\n')

    # 연락처
    contacts = layout.get("contact_section", [])
    if contacts:
        html_parts.append("""
    <div class="contact-section">
        <div class="title">📞 연락처</div>
""")
        for c in contacts:
            content = c.get("content", "")
            html_parts.append(f'        <div class="contact-item">{content}</div>\n')
        html_parts.append('    </div>\n')

    # 푸터 - 인쇄정보 포함
    html_parts.append(f"""
    <div class="footer" style="color: #666; margin-top: 30px; padding: 20px; background: white; border-radius: 15px; text-align: center;">
        <div style="font-size: 11px; line-height: 1.8; color: #888;">
            인쇄 : (주)인비젼플러스ㅣ서울시 중구 퇴계로36가길 10, B104호<br>
            전화 : 02-2266-2350
        </div>
        <div style="margin-top: 15px; padding-top: 15px; border-top: 1px solid #eee; font-size: 10px; color: #aaa;">
            자동 생성: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}<br>
            StudySnap PDF 변환 시스템
        </div>
    </div>
</div>

<!-- 원문보기 모달 - 반응형 이미지 최적화 -->
<div class="modal-overlay" id="originalModal" onclick="closeModal()">
    <div class="modal-content" onclick="event.stopPropagation()" style="width: 95%; max-width: 600px;">
        <button class="modal-close" onclick="closeModal()">×</button>
        <img class="modal-image" id="modalImage" src="" alt="원문 페이지" style="width: 100%; height: auto; display: block; border-radius: 10px;">
    </div>
</div>

<script>
// 상세보기 토글
function toggleExpand(header) {{
    const item = header.parentElement;
    const details = item.querySelector('.expandable-details');
    const toggle = header.querySelector('.expandable-toggle');

    details.classList.toggle('open');
    toggle.classList.toggle('open');
}}

// 동 선택
function selectDistrict(districtName) {{
    // 모든 영역 초기화
    document.querySelectorAll('.district-area').forEach(area => {{
        area.classList.remove('active');
    }});
    document.querySelectorAll('.district-info').forEach(info => {{
        info.classList.remove('active');
    }});

    // 선택된 영역 활성화
    const selectedArea = document.querySelector(`[data-district="${{districtName}}"]`);
    if (selectedArea) {{
        selectedArea.classList.add('active');
    }}

    // 해당 정보 패널 표시
    const infoPanel = document.getElementById(`info-${{districtName}}`);
    if (infoPanel) {{
        infoPanel.classList.add('active');
    }}
}}

// 이미지 보기 모달 (핵심공약용 - 이미지 경로 직접 지정)
function showImage(imagePath) {{
    const modal = document.getElementById('originalModal');
    const modalImage = document.getElementById('modalImage');

    modalImage.src = imagePath;
    modalImage.alt = '원문 이미지';
    modalImage.style.display = 'block';

    // 이미지 로드 실패 시 대체 메시지
    modalImage.onerror = function() {{
        this.style.display = 'none';
        this.parentElement.innerHTML = `
            <button class="modal-close" onclick="closeModal()">×</button>
            <div style="padding: 40px; text-align: center;">
                <p style="font-size: 16px; color: #333; margin-bottom: 10px;">📄 원문 이미지</p>
                <p style="font-size: 14px; color: #666;">이미지를 불러올 수 없습니다.</p>
                <p style="font-size: 12px; color: #999; margin-top: 10px;">경로: ${{imagePath}}</p>
            </div>
        `;
    }};

    modal.classList.add('active');
}}

// 원문보기 모달 (페이지 번호 기반)
function showOriginal(pageNumber) {{
    showImage(`/outputs/나경원_page_${{pageNumber}}.png`);
}}

function closeModal() {{
    const modal = document.getElementById('originalModal');
    const modalImage = document.getElementById('modalImage');
    modal.classList.remove('active');
    // 모달 내용 복구
    modalImage.style.display = 'block';
}}

// ESC 키로 모달 닫기
document.addEventListener('keydown', function(e) {{
    if (e.key === 'Escape') {{
        closeModal();
    }}
}});
</script>
</body>
</html>
""")

    return "".join(html_parts)


def main():
    pdf_path = "C:/Users/jmyang/Downloads/나경원-텍스트.pdf"
    output_dir = "c:/StudySnap-Backend/outputs"  # outputs 폴더 (서버 마운트 경로)

    # 출력 디렉토리 생성
    os.makedirs(output_dir, exist_ok=True)

    print("=" * 60)
    print("PDF → 모바일 HTML 자동 변환")
    print("=" * 60)

    # 1. PDF에서 객체 추출
    print("\n[1/4] PDF에서 객체 추출 중...")
    objects = extract_objects_from_pdf(pdf_path)
    print(f"    추출된 객체: {len(objects)}개")

    # 2. 객체 분류
    print("\n[2/4] 객체 분류 중...")
    classifier = ObjectClassifier()
    classified_objects = []

    for obj in objects:
        # classify 메서드는 (text, style, bbox, page_height) 를 받음
        obj_type, confidence = classifier.classify(
            text=obj.content,
            style=obj.style,
            bbox=obj.bbox,
            page_height=842  # A4 기준
        )
        obj.object_type = obj_type
        obj.confidence = confidence
        classified_objects.append(obj)

    # 분류 통계
    type_counts = {}
    for obj in classified_objects:
        t = obj.object_type.value
        type_counts[t] = type_counts.get(t, 0) + 1

    print("    분류 결과:")
    for t, count in sorted(type_counts.items(), key=lambda x: -x[1])[:10]:
        print(f"      - {t}: {count}개")

    # 3. 모바일 레이아웃 생성
    print("\n[3/4] 모바일 레이아웃 생성 중...")
    analyzer = LayoutAnalyzer()
    layout = analyzer.generate_mobile_layout(classified_objects)

    hero = layout.get("hero_section", {}) or {}
    print(f"    후보자: {hero.get('candidate', 'N/A')}")
    print(f"    정당: {hero.get('party', 'N/A')}")
    print(f"    슬로건: {hero.get('slogan', 'N/A')}")
    print(f"    핵심 공약: {len(layout.get('quick_highlights', []))}개")
    print(f"    전체 공약: {len(layout.get('pledge_cards', []))}개")
    print(f"    실적: {len(layout.get('achievements', []))}개")
    print(f"    동별 공약: {list(layout.get('district_pledges', {}).keys())}")
    print(f"    연락처: {len(layout.get('contact_section', []) or [])}개")

    # 4. HTML 생성 및 저장
    print("\n[4/4] HTML 생성 및 저장 중...")
    html_content = generate_mobile_html(layout)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = os.path.join(output_dir, f"나경원_자동생성_{timestamp}.html")

    with open(output_file, "w", encoding="utf-8") as f:
        f.write(html_content)

    print(f"    저장 완료: {output_file}")

    # 레이아웃 데이터도 JSON으로 저장
    layout_json_file = os.path.join(output_dir, f"나경원_레이아웃_{timestamp}.json")
    with open(layout_json_file, "w", encoding="utf-8") as f:
        json.dump(layout, f, ensure_ascii=False, indent=2)
    print(f"    레이아웃 데이터: {layout_json_file}")

    print("\n" + "=" * 60)
    print("변환 완료!")
    print("=" * 60)
    print(f"\n이전 수동 편집 파일: C:/Users/jmyang/Documents/8e2f0aeb_20251202_091627 (1).html")
    print(f"새로 생성된 파일: {output_file}")
    print("\n두 파일을 브라우저에서 열어 비교해 보세요!")

    return output_file, layout


if __name__ == "__main__":
    main()
