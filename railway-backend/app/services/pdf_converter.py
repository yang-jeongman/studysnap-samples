"""
PDF to HTML Conversion Service
"""
import anthropic
import fitz  # PyMuPDF
from pathlib import Path
import time
import logging
from typing import Dict, Any, Optional
from app.core.config import settings
from app.models import ConversionCategory

logger = logging.getLogger(__name__)


class PDFConverterService:
    """Service for converting PDF files to HTML using Claude API"""

    def __init__(self):
        self.client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)

    async def convert_pdf(
        self,
        pdf_content: bytes,
        filename: str,
        category: ConversionCategory,
        candidate_name: Optional[str] = None,
        party_name: Optional[str] = None,
        district: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Convert PDF to HTML

        Args:
            pdf_content: PDF file content as bytes
            filename: Original filename
            category: Conversion category
            candidate_name: Optional candidate name
            party_name: Optional party name
            district: Optional district

        Returns:
            Dictionary with conversion results
        """
        start_time = time.time()

        logger.info(f"Starting PDF conversion: {filename}, category: {category}")

        # Step 1: Extract PDF pages as images
        pdf_images = await self._extract_pdf_images(pdf_content)
        page_count = len(pdf_images)

        logger.info(f"Extracted {page_count} pages from PDF")

        # Step 2: Extract text from PDF using Claude Vision
        pdf_text = await self._extract_text_with_claude(pdf_images, category)

        logger.info("Text extraction completed")

        # Step 3: Select appropriate template
        template_id = self._select_template(category)

        logger.info(f"Selected template: {template_id}")

        # Step 4: Generate HTML using Claude
        html_content = await self._generate_html(
            pdf_text=pdf_text,
            template_id=template_id,
            category=category,
            candidate_name=candidate_name,
            party_name=party_name,
            district=district
        )

        logger.info("HTML generation completed")

        # Step 5: Commit to GitHub
        commit_result = await self._commit_to_github(
            html_content=html_content,
            images=pdf_images,
            category=category,
            candidate_name=candidate_name or "unnamed"
        )

        processing_time = time.time() - start_time

        logger.info(f"PDF conversion completed in {processing_time:.2f} seconds")

        return {
            'html_url': commit_result['html_url'],
            'commit_sha': commit_result['commit_sha'],
            'output_path': commit_result['output_path'],
            'page_count': page_count,
            'template_id': template_id,
            'processing_time': round(processing_time, 2)
        }

    async def _extract_pdf_images(self, pdf_content: bytes) -> list:
        """
        Extract pages from PDF as images

        Args:
            pdf_content: PDF file content

        Returns:
            List of image data (base64 encoded)
        """
        import base64
        from io import BytesIO

        images = []

        # Open PDF
        pdf_document = fitz.open(stream=pdf_content, filetype="pdf")

        for page_num in range(len(pdf_document)):
            page = pdf_document[page_num]

            # Render page as image (150 DPI)
            pix = page.get_pixmap(matrix=fitz.Matrix(150/72, 150/72))

            # Convert to PNG
            img_data = pix.tobytes("png")

            # Encode to base64
            img_base64 = base64.b64encode(img_data).decode('utf-8')

            images.append({
                'page_num': page_num + 1,
                'image_data': img_base64,
                'format': 'png'
            })

        pdf_document.close()

        return images

    async def _extract_text_with_claude(
        self,
        pdf_images: list,
        category: ConversionCategory
    ) -> str:
        """
        Extract text from PDF images using Claude Vision API

        Args:
            pdf_images: List of PDF page images
            category: Conversion category

        Returns:
            Extracted text content
        """
        # Build category-specific prompt
        category_prompts = {
            ConversionCategory.ELECTION_DEMOCRATIC: "더불어민주당 선거공보물",
            ConversionCategory.ELECTION_PPP: "국민의힘 선거공보물",
            ConversionCategory.ELECTION_PROGRESSIVE: "진보당 선거공보물",
            ConversionCategory.CHURCH: "교회 주보",
            ConversionCategory.NEWSLETTER: "뉴스레터",
            ConversionCategory.LECTURE: "강의자료"
        }

        category_name = category_prompts.get(category, "문서")

        # Prepare content for Claude
        content = [
            {
                "type": "text",
                "text": f"""다음은 {category_name} PDF의 페이지 이미지들입니다.

각 페이지의 내용을 정확하게 추출해주세요:

1. 모든 텍스트를 정확하게 추출
2. 구조와 계층을 유지
3. 제목, 소제목, 본문 구분
4. 이미지 설명 포함
5. 표와 목록 구조 유지

페이지별로 구분하여 마크다운 형식으로 작성해주세요."""
            }
        ]

        # Add images to content
        for img in pdf_images[:5]:  # Limit to first 5 pages for API limits
            content.append({
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": "image/png",
                    "data": img['image_data']
                }
            })

        # Call Claude API
        message = self.client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=4096,
            messages=[{
                "role": "user",
                "content": content
            }]
        )

        extracted_text = message.content[0].text

        return extracted_text

    def _select_template(self, category: ConversionCategory) -> str:
        """
        Select appropriate template based on category

        Args:
            category: Conversion category

        Returns:
            Template ID
        """
        template_mapping = {
            ConversionCategory.ELECTION_DEMOCRATIC: "minjoo_standard_v1",
            ConversionCategory.ELECTION_PPP: "ppp_standard_v1",
            ConversionCategory.ELECTION_PROGRESSIVE: "progressive_standard_v1",
            ConversionCategory.CHURCH: "church_general_v1",
            ConversionCategory.NEWSLETTER: "newsletter_party_v1",
            ConversionCategory.LECTURE: "lecture_standard_v1"
        }

        return template_mapping.get(category, "default_v1")

    async def _generate_html(
        self,
        pdf_text: str,
        template_id: str,
        category: ConversionCategory,
        candidate_name: Optional[str],
        party_name: Optional[str],
        district: Optional[str]
    ) -> str:
        """
        Generate HTML using Claude based on extracted text and template

        Args:
            pdf_text: Extracted text from PDF
            template_id: Selected template ID
            category: Conversion category
            candidate_name: Candidate name
            party_name: Party name
            district: District

        Returns:
            Generated HTML content
        """
        # Build prompt based on category
        if category in [ConversionCategory.ELECTION_DEMOCRATIC, ConversionCategory.ELECTION_PPP, ConversionCategory.ELECTION_PROGRESSIVE]:
            prompt = f"""다음 선거공보물 내용을 모바일 최적화된 HTML로 변환해주세요.

템플릿: {template_id}
후보자: {candidate_name or '미지정'}
정당: {party_name or '미지정'}
지역구: {district or '미지정'}

PDF 내용:
{pdf_text}

요구사항:
1. 모바일 최적화 반응형 디자인
2. 정당 색상 적용 (민주당: #004EA2, 국민의힘: #E61E2B, 진보당: #10B981)
3. 아코디언 스타일 공약 카드
4. 타임라인 형식 경력 섹션
5. 이미지 갤러리
6. 하단 네비게이션
7. 완전한 HTML 문서 (<!DOCTYPE html>부터)

HTML 코드만 출력하세요:"""

        else:
            prompt = f"""다음 문서 내용을 모바일 최적화된 HTML로 변환해주세요.

카테고리: {category.value}
템플릿: {template_id}

문서 내용:
{pdf_text}

요구사항:
1. 모바일 최적화 반응형 디자인
2. 깔끔하고 읽기 쉬운 레이아웃
3. 적절한 색상 스킴
4. 완전한 HTML 문서 (<!DOCTYPE html>부터)

HTML 코드만 출력하세요:"""

        # Call Claude API
        message = self.client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=8192,
            messages=[{
                "role": "user",
                "content": prompt
            }]
        )

        html_content = message.content[0].text

        # Clean HTML (remove markdown code blocks if present)
        if html_content.startswith("```html"):
            html_content = html_content[7:]
        if html_content.endswith("```"):
            html_content = html_content[:-3]

        return html_content.strip()

    async def _commit_to_github(
        self,
        html_content: str,
        images: list,
        category: ConversionCategory,
        candidate_name: str
    ) -> Dict[str, str]:
        """
        Commit HTML and images to GitHub repository

        Args:
            html_content: Generated HTML content
            images: List of PDF page images
            category: Conversion category
            candidate_name: Candidate/document name

        Returns:
            Dictionary with commit details
        """
        from github import Github
        import base64

        # Initialize GitHub client
        g = Github(settings.GITHUB_TOKEN)
        repo = g.get_repo(f"{settings.GITHUB_REPO_OWNER}/{settings.GITHUB_REPO_NAME}")

        # Determine output path based on category
        category_paths = {
            ConversionCategory.ELECTION_DEMOCRATIC: "outputs/Election/Minjoo",
            ConversionCategory.ELECTION_PPP: "outputs/Election/PPP",
            ConversionCategory.ELECTION_PROGRESSIVE: "outputs/Election/Progressive",
            ConversionCategory.CHURCH: "outputs/Church",
            ConversionCategory.NEWSLETTER: "outputs/Newsletter",
            ConversionCategory.LECTURE: "outputs/Lecture"
        }

        base_path = category_paths.get(category, "outputs/Other")
        output_path = f"{base_path}/{candidate_name}"

        # Commit HTML file
        html_file_path = f"{output_path}/{candidate_name}.html"

        try:
            # Try to get existing file
            existing_file = repo.get_contents(html_file_path)
            commit = repo.update_file(
                html_file_path,
                f"Update: {candidate_name} HTML",
                html_content,
                existing_file.sha,
                branch="main"
            )
        except:
            # File doesn't exist, create new
            commit = repo.create_file(
                html_file_path,
                f"Add: {candidate_name} HTML",
                html_content,
                branch="main"
            )

        # Commit images
        for img in images:
            img_file_path = f"{output_path}/images/page{img['page_num']}.png"

            try:
                existing_img = repo.get_contents(img_file_path)
                repo.update_file(
                    img_file_path,
                    f"Update: {candidate_name} page {img['page_num']} image",
                    base64.b64decode(img['image_data']),
                    existing_img.sha,
                    branch="main"
                )
            except:
                repo.create_file(
                    img_file_path,
                    f"Add: {candidate_name} page {img['page_num']} image",
                    base64.b64decode(img['image_data']),
                    branch="main"
                )

        # Generate Netlify URL
        netlify_url = f"https://studysnap-pdf.netlify.app/{output_path}/{candidate_name}.html"

        return {
            'html_url': netlify_url,
            'commit_sha': commit['commit'].sha,
            'output_path': output_path
        }
