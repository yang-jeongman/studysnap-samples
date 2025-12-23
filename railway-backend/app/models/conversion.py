"""
Conversion database model
"""
from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, Enum, Float
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base
import enum


class ConversionStatus(str, enum.Enum):
    """Conversion status enumeration"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class ConversionCategory(str, enum.Enum):
    """Conversion category enumeration"""
    ELECTION_DEMOCRATIC = "election_democratic"
    ELECTION_PPP = "election_ppp"
    ELECTION_PROGRESSIVE = "election_progressive"
    CHURCH = "church"
    NEWSLETTER = "newsletter"
    LECTURE = "lecture"


class Conversion(Base):
    """Conversion model for storing PDF conversion records"""

    __tablename__ = "conversions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    # File information
    pdf_filename = Column(String(255), nullable=False)
    pdf_size_mb = Column(Float, nullable=True)
    page_count = Column(Integer, nullable=True)

    # Conversion details
    category = Column(Enum(ConversionCategory), nullable=False)
    template_id = Column(String(100), nullable=True)
    status = Column(Enum(ConversionStatus), default=ConversionStatus.PENDING)

    # Output information
    html_url = Column(Text, nullable=True)
    github_commit_sha = Column(String(40), nullable=True)
    output_folder_path = Column(String(500), nullable=True)

    # Metadata
    candidate_name = Column(String(255), nullable=True)  # For election
    party_name = Column(String(100), nullable=True)  # For election
    district = Column(String(255), nullable=True)  # For election

    # Processing details
    processing_time_seconds = Column(Float, nullable=True)
    error_message = Column(Text, nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    user = relationship("User", back_populates="conversions")

    def __repr__(self):
        return f"<Conversion(id={self.id}, category='{self.category}', status='{self.status}')>"
