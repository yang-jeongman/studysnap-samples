"""
NewsletterAI - 지자체 소식지 변환 스크립트
광명소식 649호 PDF -> 모바일 최적화 HTML

🤖 Powered by NewsletterAI
"""

import fitz  # PyMuPDF
import base64
import os
import sys
import json
from datetime import datetime
from pathlib import Path

# 프로젝트 경로 추가
sys.path.insert(0, str(Path(__file__).parent))

from vision_ocr import VisionOCR
from newsletter_html_generator import NewsletterHTMLGenerator

# 품질 검사 모듈 (있으면 사용)
try:
    from learning_data.newsletter.ocr_validator import OCRValidator, NewsletterQualityChecker
    QUALITY_CHECK_AVAILABLE = True
except ImportError:
    QUALITY_CHECK_AVAILABLE = False


def extract_page_images(pdf_path: str, output_dir: Path, dpi: int = 150) -> dict:
    """
    PDF에서 페이지별 이미지를 추출하여 저장

    Args:
        pdf_path: PDF 파일 경로
        output_dir: 이미지 저장 디렉토리
        dpi: 이미지 해상도 (기본 150, 원문보기용)

    Returns:
        {page_num: image_path} 딕셔너리
    """
    images_dir = output_dir / "pages"
    images_dir.mkdir(parents=True, exist_ok=True)

    page_images = {}
    doc = fitz.open(pdf_path)

    for page_num in range(len(doc)):
        page = doc[page_num]

        # 페이지를 이미지로 변환
        mat = fitz.Matrix(dpi/72, dpi/72)
        pix = page.get_pixmap(matrix=mat)

        # 이미지 저장
        image_path = images_dir / f"page_{page_num + 1}.jpg"
        pix.save(str(image_path), "jpeg")

        # 상대 경로 저장 (HTML에서 사용)
        page_images[page_num + 1] = f"pages/page_{page_num + 1}.jpg"

        print(f"  [{page_num + 1}p] 이미지 저장: {image_path.name}")

    doc.close()
    return page_images


def convert_newsletter_pdf(pdf_path: str, output_path: str = None, city_name: str = "광명시", extract_images: bool = True):
    """
    지자체 소식지 PDF를 HTML로 변환

    Args:
        pdf_path: PDF 파일 경로
        output_path: HTML 출력 경로 (None이면 자동 생성)
        city_name: 지자체 이름
        extract_images: 페이지 이미지 추출 여부 (원문보기 기능용)
    """
    print(f"\n{'='*60}")
    print(f"[NewsletterAI] 지자체 소식지 PDF 변환")
    print(f"{'='*60}")
    print(f"입력: {pdf_path}")
    print(f"지자체: {city_name}")

    # Vision OCR 초기화
    vision_ocr = VisionOCR()
    if not vision_ocr.client:
        print("오류: ANTHROPIC_API_KEY가 설정되지 않았습니다!")
        return None

    # PDF 열기
    doc = fitz.open(pdf_path)
    page_count = len(doc)
    print(f"PDF 페이지 수: {page_count}")

    # 모든 페이지 분석
    all_pages_data = []

    for page_num in range(page_count):
        print(f"\n[{page_num + 1}/{page_count}] 페이지 분석 중...")

        page = doc[page_num]

        # 페이지를 이미지로 변환 (DPI 250 - OCR 정확도와 API 제한 균형)
        mat = fitz.Matrix(250/72, 250/72)
        pix = page.get_pixmap(matrix=mat)
        img_data = pix.tobytes("jpeg")

        # Base64 인코딩
        image_base64 = base64.b64encode(img_data).decode('utf-8')

        # Claude Vision으로 분석
        result = vision_ocr.extract_newsletter_info(
            image_base64=image_base64,
            media_type="image/jpeg",
            page_number=page_num + 1,
            total_pages=page_count
        )

        structured = result.get("structured", {})
        print(f"  - 카테고리: {structured.get('category', 'N/A')}")
        print(f"  - 기사 수: {len(structured.get('articles', []))}")
        print(f"  - 현장취재: {len(structured.get('field_reports', []))}")
        print(f"  - 인터뷰: {len(structured.get('interviews', []))}")

        all_pages_data.append({
            "page_num": page_num + 1,
            "text": result.get("text", ""),
            "structured": structured
        })

    doc.close()

    # 품질 검사 및 자동 교정
    if QUALITY_CHECK_AVAILABLE:
        print(f"\n{'='*60}")
        print("[품질검사] OCR 결과 검증 중...")

        quality_checker = NewsletterQualityChecker()
        quality_report = quality_checker.check_newsletter_quality(all_pages_data)

        print(f"  - 전체 품질 점수: {quality_report['overall_score']}/100")
        print(f"  - 권장사항: {quality_report['recommendation']}")

        if quality_report['pages_needing_reprocess']:
            print(f"  - 재처리 필요 페이지: {quality_report['pages_needing_reprocess']}")

        # 자동 교정 적용
        validator = OCRValidator()
        for page_data in all_pages_data:
            structured = page_data.get("structured", {})

            # 기사 텍스트 교정
            for article in structured.get("articles", []):
                if article.get("summary"):
                    corrected, _ = validator.auto_correct(article["summary"])
                    article["summary"] = corrected
                if article.get("content"):
                    corrected, _ = validator.auto_correct(article["content"])
                    article["content"] = corrected

            # 현장취재 텍스트 교정
            for report in structured.get("field_reports", []):
                if report.get("content"):
                    corrected, _ = validator.auto_correct(report["content"])
                    report["content"] = corrected

            # 인터뷰 텍스트 교정
            for interview in structured.get("interviews", []):
                if interview.get("quote"):
                    corrected, _ = validator.auto_correct(interview["quote"])
                    interview["quote"] = corrected

        print("  - 자동 교정 완료")

    # 데이터 통합
    print(f"\n{'='*60}")
    print("데이터 통합 및 HTML 생성 중...")

    merged_data = _merge_newsletter_data(all_pages_data, city_name)

    # HTML 생성
    generator = NewsletterHTMLGenerator(city_name)
    html_content = generator.generate(merged_data)

    # 출력 경로 설정
    if not output_path:
        output_dir = Path("outputs/Newsletter") / city_name
        output_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M")
        output_path = output_dir / f"newsletter_{timestamp}.html"
    else:
        output_dir = Path(output_path).parent
        output_dir.mkdir(parents=True, exist_ok=True)

    # 페이지 이미지 추출 (원문보기 기능용)
    page_images = {}
    if extract_images:
        print(f"\n[이미지 추출] 페이지 이미지 추출 중...")
        page_images = extract_page_images(pdf_path, output_dir)

        # HTML에 이미지 경로 주입
        page_images_js = json.dumps(page_images)
        html_content = html_content.replace(
            "const PAGE_IMAGES = {}; // 페이지 이미지 경로 (convert_newsletter.py에서 설정)",
            f"const PAGE_IMAGES = {page_images_js}; // 원문 이미지 경로"
        )

    # HTML 저장
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html_content)

    print(f"\n[완료] 변환 완료!")
    print(f"HTML: {output_path}")
    if page_images:
        print(f"이미지: {len(page_images)}개 페이지")
    print(f"{'='*60}\n")

    return str(output_path)


def _merge_newsletter_data(pages_data: list, city_name: str) -> dict:
    """페이지 데이터 통합"""
    merged = {
        "title": "광명소식",
        "issue": "",
        "date": "",
        "publisher": "",
        "city": city_name,
        "contact": {
            "phone": "02-2680-2062",
            "email": "gmgongbo@korea.kr",
            "website": "www.gm.go.kr"
        },
        "pages": []
    }

    # 첫 페이지에서 기본 정보 추출
    if pages_data:
        first_page = pages_data[0].get("structured", {})
        merged["issue"] = first_page.get("issue", "제649호")
        merged["date"] = first_page.get("date", "2025년 10월 29일")
        merged["publisher"] = first_page.get("publisher", "광명시장 박승원")

    # 카테고리별로 페이지 그룹화
    category_pages = {}

    for page in pages_data:
        structured = page.get("structured", {})
        page_num = structured.get("page_num", page.get("page_num", 0))

        # 카테고리 결정
        category = structured.get("category", "")
        if not category:
            if page_num == 1:
                category = "특집"
            elif page_num in [2, 3, 4]:
                category = "스마트 도시"
            elif page_num in [5]:
                category = "복지"
            elif page_num in [6, 7]:
                category = "공동체"
            elif page_num in [8, 9]:
                category = "돌봄"
            elif page_num in [10, 11]:
                category = "생활정보"
            elif page_num == 12:
                category = "캐릭터"
            else:
                category = "기타"

        if category not in category_pages:
            category_pages[category] = []

        page_data = {
            "page_num": page_num,
            "category": category,
            "main_title": structured.get("main_title", ""),
            "page_title": structured.get("page_title", ""),  # 페이지 제목
            "page_desc": structured.get("page_desc", ""),    # 페이지 설명
            "subtitle": structured.get("subtitle", ""),
            "articles": structured.get("articles", []),
            "field_reports": structured.get("field_reports", []),
            "interviews": structured.get("interviews", []),
            "info_items": structured.get("info_items", []),
            "characters": structured.get("characters", [])   # 캐릭터 정보
        }

        # 기사에 카테고리 추가
        for article in page_data["articles"]:
            if not article.get("category"):
                article["category"] = category

        category_pages[category].append(page_data)

    # 페이지 목록 생성
    for category, pages in category_pages.items():
        for page in pages:
            merged["pages"].append(page)

    return merged


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="NewsletterAI - 지자체 소식지 PDF 변환")
    parser.add_argument("--pdf", type=str, help="PDF 파일 경로")
    parser.add_argument("--city", type=str, default="광명시", help="지자체 이름 (기본값: 광명시)")
    parser.add_argument("--output", type=str, help="출력 HTML 경로")
    parser.add_argument("--no-images", action="store_true", help="페이지 이미지 추출 안함")

    args = parser.parse_args()

    # PDF 경로 결정
    if args.pdf:
        pdf_path = args.pdf
    else:
        # 기본값: 광명소식 649호
        pdf_path = r"C:\Users\jmyang\Dropbox\배정우-더소통\더소통\지자체 소식지 pdf-원본\광명\광명소식 649호_최종최적.pdf"

    if os.path.exists(pdf_path):
        output = convert_newsletter_pdf(
            pdf_path=pdf_path,
            output_path=args.output,
            city_name=args.city,
            extract_images=not args.no_images
        )
        if output:
            print(f"브라우저에서 열기: file:///{output.replace(chr(92), '/')}")
    else:
        print(f"PDF 파일을 찾을 수 없습니다: {pdf_path}")
        print("\n사용법:")
        print("  python convert_newsletter.py --pdf <PDF경로> --city <지자체명>")
        print("\n예시:")
        print("  python convert_newsletter.py --pdf ./소식지.pdf --city 서초구")
        print("  python convert_newsletter.py --pdf ./성남소식.pdf --city 성남시")
