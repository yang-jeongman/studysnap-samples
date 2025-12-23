"""
Email Service for sending notifications
"""
import aiosmtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)


class EmailService:
    """Service for sending emails via SMTP"""

    async def send_conversion_complete_email(
        self,
        to_email: str,
        html_url: str,
        category: str
    ):
        """
        Send email notification when PDF conversion is complete

        Args:
            to_email: Recipient email address
            html_url: URL of the converted HTML
            category: Conversion category
        """
        subject = "StudySnap - PDF 변환 완료!"

        # Create HTML email body
        html_body = f"""
<!DOCTYPE html>
<html>
<head>
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
        .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                   color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }}
        .content {{ background: #f9f9f9; padding: 30px; }}
        .button {{ display: inline-block; padding: 15px 30px; background: #667eea;
                  color: white; text-decoration: none; border-radius: 5px; margin: 20px 0; }}
        .footer {{ text-align: center; padding: 20px; color: #999; font-size: 0.9em; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📚 StudySnap</h1>
            <p>PDF 변환이 완료되었습니다!</p>
        </div>
        <div class="content">
            <h2>안녕하세요,</h2>
            <p>요청하신 <strong>{category}</strong> PDF 파일의 HTML 변환이 성공적으로 완료되었습니다.</p>

            <p>아래 버튼을 클릭하여 변환된 웹페이지를 확인하실 수 있습니다:</p>

            <div style="text-align: center;">
                <a href="{html_url}" class="button">변환된 페이지 보기</a>
            </div>

            <p><strong>링크:</strong> <a href="{html_url}">{html_url}</a></p>

            <hr style="margin: 30px 0; border: none; border-top: 1px solid #ddd;">

            <h3>주요 특징:</h3>
            <ul>
                <li>✅ 모바일 최적화 반응형 디자인</li>
                <li>✅ 빠른 로딩 속도</li>
                <li>✅ 쉬운 공유</li>
                <li>✅ 검색 엔진 최적화</li>
            </ul>

            <p>궁금한 점이 있으시면 언제든지 답장해 주세요.</p>

            <p>감사합니다,<br><strong>StudySnap 팀</strong></p>
        </div>
        <div class="footer">
            <p>© 2025 StudySnap. All rights reserved.</p>
            <p><a href="https://studysnap-pdf.netlify.app">studysnap-pdf.netlify.app</a></p>
        </div>
    </div>
</body>
</html>
        """

        # Create plain text version
        text_body = f"""
StudySnap - PDF 변환 완료!

안녕하세요,

요청하신 {category} PDF 파일의 HTML 변환이 성공적으로 완료되었습니다.

변환된 페이지: {html_url}

주요 특징:
- 모바일 최적화 반응형 디자인
- 빠른 로딩 속도
- 쉬운 공유
- 검색 엔진 최적화

감사합니다,
StudySnap 팀

© 2025 StudySnap
https://studysnap-pdf.netlify.app
        """

        await self._send_email(
            to_email=to_email,
            subject=subject,
            html_body=html_body,
            text_body=text_body
        )

    async def _send_email(
        self,
        to_email: str,
        subject: str,
        html_body: str,
        text_body: str
    ):
        """
        Send email via SMTP

        Args:
            to_email: Recipient email
            subject: Email subject
            html_body: HTML email body
            text_body: Plain text email body
        """
        try:
            # Create message
            message = MIMEMultipart('alternative')
            message['From'] = settings.SMTP_FROM
            message['To'] = to_email
            message['Subject'] = subject

            # Attach text and HTML parts
            part1 = MIMEText(text_body, 'plain')
            part2 = MIMEText(html_body, 'html')

            message.attach(part1)
            message.attach(part2)

            # Send email
            await aiosmtplib.send(
                message,
                hostname=settings.SMTP_HOST,
                port=settings.SMTP_PORT,
                username=settings.SMTP_USER,
                password=settings.SMTP_PASSWORD,
                start_tls=True
            )

            logger.info(f"Email sent successfully to {to_email}")

        except Exception as e:
            logger.error(f"Failed to send email to {to_email}: {str(e)}")
            # Don't raise exception - email failure shouldn't break conversion
