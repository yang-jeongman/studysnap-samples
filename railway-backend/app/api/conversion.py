"""
PDF Conversion API endpoints
"""
from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models import Conversion, ConversionStatus, ConversionCategory, User
from app.services.pdf_converter import PDFConverterService
from pydantic import BaseModel, EmailStr
from typing import Optional
import logging

router = APIRouter()
logger = logging.getLogger(__name__)


class ConversionRequest(BaseModel):
    """Request model for PDF conversion"""
    email: EmailStr
    category: ConversionCategory
    candidate_name: Optional[str] = None
    party_name: Optional[str] = None
    district: Optional[str] = None


class ConversionResponse(BaseModel):
    """Response model for PDF conversion"""
    conversion_id: int
    status: ConversionStatus
    message: str
    html_url: Optional[str] = None


class ConversionStatusResponse(BaseModel):
    """Response model for conversion status check"""
    conversion_id: int
    status: ConversionStatus
    html_url: Optional[str] = None
    error_message: Optional[str] = None
    progress_percent: Optional[int] = None


@router.post("/convert", response_model=ConversionResponse)
async def convert_pdf(
    background_tasks: BackgroundTasks,
    pdf: UploadFile = File(..., description="PDF file to convert"),
    email: EmailStr = Form(..., description="User email address"),
    category: str = Form(..., description="Conversion category"),
    candidate_name: Optional[str] = Form(None, description="Candidate name (for election)"),
    party_name: Optional[str] = Form(None, description="Party name (for election)"),
    district: Optional[str] = Form(None, description="District (for election)"),
    db: Session = Depends(get_db)
):
    """
    Convert PDF to HTML

    - **pdf**: PDF file to upload (max 50MB)
    - **email**: User email for notifications
    - **category**: Conversion category (election_democratic, church, etc.)
    - **candidate_name**: Optional candidate name for election materials
    - **party_name**: Optional party name for election materials
    - **district**: Optional district for election materials
    """

    # Validate file
    if not pdf.filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="File must be a PDF")

    # Get file size
    pdf_content = await pdf.read()
    file_size_mb = len(pdf_content) / (1024 * 1024)

    if file_size_mb > 50:
        raise HTTPException(status_code=400, detail="PDF file too large (max 50MB)")

    # Get or create user
    user = db.query(User).filter(User.email == email).first()
    if not user:
        user = User(email=email, is_active=True)
        db.add(user)
        db.commit()
        db.refresh(user)
        logger.info(f"Created new user: {email}")

    # Validate and convert category
    try:
        category_enum = ConversionCategory(category)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid category. Must be one of: {[c.value for c in ConversionCategory]}"
        )

    # Create conversion record
    conversion = Conversion(
        user_id=user.id,
        pdf_filename=pdf.filename,
        pdf_size_mb=round(file_size_mb, 2),
        category=category_enum,
        status=ConversionStatus.PENDING,
        candidate_name=candidate_name,
        party_name=party_name,
        district=district
    )

    db.add(conversion)
    db.commit()
    db.refresh(conversion)

    logger.info(f"Created conversion {conversion.id} for user {email}")

    # Add background task for PDF conversion
    background_tasks.add_task(
        process_pdf_conversion,
        conversion_id=conversion.id,
        pdf_content=pdf_content,
        filename=pdf.filename
    )

    return ConversionResponse(
        conversion_id=conversion.id,
        status=ConversionStatus.PENDING,
        message="PDF conversion started. You will receive an email when complete.",
        html_url=None
    )


@router.get("/convert/{conversion_id}/status", response_model=ConversionStatusResponse)
async def get_conversion_status(
    conversion_id: int,
    db: Session = Depends(get_db)
):
    """
    Get conversion status

    - **conversion_id**: ID of the conversion to check
    """

    conversion = db.query(Conversion).filter(Conversion.id == conversion_id).first()

    if not conversion:
        raise HTTPException(status_code=404, detail="Conversion not found")

    # Calculate progress percentage
    progress = 0
    if conversion.status == ConversionStatus.PENDING:
        progress = 0
    elif conversion.status == ConversionStatus.PROCESSING:
        progress = 50
    elif conversion.status == ConversionStatus.COMPLETED:
        progress = 100
    elif conversion.status == ConversionStatus.FAILED:
        progress = 0

    return ConversionStatusResponse(
        conversion_id=conversion.id,
        status=conversion.status,
        html_url=conversion.html_url,
        error_message=conversion.error_message,
        progress_percent=progress
    )


async def process_pdf_conversion(conversion_id: int, pdf_content: bytes, filename: str):
    """
    Background task to process PDF conversion

    This runs asynchronously and updates the conversion status in the database
    """
    from app.core.database import SessionLocal

    db = SessionLocal()

    try:
        # Get conversion record
        conversion = db.query(Conversion).filter(Conversion.id == conversion_id).first()
        if not conversion:
            logger.error(f"Conversion {conversion_id} not found")
            return

        # Update status to processing
        conversion.status = ConversionStatus.PROCESSING
        db.commit()

        logger.info(f"Starting PDF conversion {conversion_id}")

        # Initialize converter service
        converter = PDFConverterService()

        # Perform conversion
        result = await converter.convert_pdf(
            pdf_content=pdf_content,
            filename=filename,
            category=conversion.category,
            candidate_name=conversion.candidate_name,
            party_name=conversion.party_name,
            district=conversion.district
        )

        # Update conversion record with results
        conversion.status = ConversionStatus.COMPLETED
        conversion.html_url = result['html_url']
        conversion.github_commit_sha = result.get('commit_sha')
        conversion.output_folder_path = result.get('output_path')
        conversion.page_count = result.get('page_count')
        conversion.template_id = result.get('template_id')
        conversion.processing_time_seconds = result.get('processing_time')

        db.commit()

        logger.info(f"Conversion {conversion_id} completed successfully")

        # Send email notification
        from app.services.email_service import EmailService
        email_service = EmailService()
        user = db.query(User).filter(User.id == conversion.user_id).first()

        await email_service.send_conversion_complete_email(
            to_email=user.email,
            html_url=conversion.html_url,
            category=conversion.category.value
        )

    except Exception as e:
        logger.error(f"Conversion {conversion_id} failed: {str(e)}", exc_info=True)

        # Update status to failed
        conversion.status = ConversionStatus.FAILED
        conversion.error_message = str(e)
        db.commit()

    finally:
        db.close()
