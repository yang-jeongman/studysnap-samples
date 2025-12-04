"""
StudySnap Backend - 데이터베이스 모델
SQLAlchemy ORM 기반 PostgreSQL 연동
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from uuid import UUID, uuid4
import enum

from sqlalchemy import (
    create_engine, Column, String, Text, Integer, BigInteger,
    Boolean, DateTime, ForeignKey, Numeric, Index, Enum as SQLEnum,
    UniqueConstraint, CheckConstraint
)
from sqlalchemy.dialects.postgresql import UUID as PGUUID, JSONB, INET
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
from sqlalchemy.sql import func

Base = declarative_base()


# ============================================
# Enum 정의
# ============================================
class UserRole(enum.Enum):
    ADMIN = "admin"
    USER = "user"
    GUEST = "guest"


class DocumentStatus(enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class AccessLevel(enum.Enum):
    READ = "read"
    WRITE = "write"
    ADMIN = "admin"


# ============================================
# 1. 서비스 모델
# ============================================
class Service(Base):
    __tablename__ = "services"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    code = Column(String(50), unique=True, nullable=False)
    name = Column(String(100), nullable=False)
    description = Column(Text)
    is_active = Column(Boolean, default=True)
    config = Column(JSONB, default={})
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # 관계
    document_types = relationship("DocumentType", back_populates="service")
    documents = relationship("Document", back_populates="service")

    def __repr__(self):
        return f"<Service(code='{self.code}', name='{self.name}')>"


# ============================================
# 2. 사용자 모델
# ============================================
class User(Base):
    __tablename__ = "users"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    email = Column(String(255), unique=True, nullable=False)
    password_hash = Column(String(255))
    name = Column(String(100))
    role = Column(String(20), default="user")
    is_active = Column(Boolean, default=True)
    last_login_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # 관계
    documents = relationship("Document", back_populates="user")
    api_keys = relationship("ApiKey", back_populates="user")
    service_access = relationship("UserServiceAccess", back_populates="user")

    def __repr__(self):
        return f"<User(email='{self.email}', role='{self.role}')>"


class UserServiceAccess(Base):
    __tablename__ = "user_service_access"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"))
    service_id = Column(PGUUID(as_uuid=True), ForeignKey("services.id", ondelete="CASCADE"))
    access_level = Column(String(20), default="read")
    granted_at = Column(DateTime(timezone=True), server_default=func.now())
    expires_at = Column(DateTime(timezone=True))

    __table_args__ = (
        UniqueConstraint('user_id', 'service_id', name='uq_user_service'),
    )

    # 관계
    user = relationship("User", back_populates="service_access")
    service = relationship("Service")


# ============================================
# 3. 문서 타입 모델
# ============================================
class DocumentType(Base):
    __tablename__ = "document_types"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    service_id = Column(PGUUID(as_uuid=True), ForeignKey("services.id", ondelete="CASCADE"))
    code = Column(String(50), nullable=False)
    name = Column(String(100), nullable=False)
    description = Column(Text)
    template_config = Column(JSONB, default={})
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        UniqueConstraint('service_id', 'code', name='uq_service_doctype'),
    )

    # 관계
    service = relationship("Service", back_populates="document_types")
    documents = relationship("Document", back_populates="document_type")

    def __repr__(self):
        return f"<DocumentType(code='{self.code}', name='{self.name}')>"


# ============================================
# 4. 문서 모델
# ============================================
class Document(Base):
    __tablename__ = "documents"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"))
    service_id = Column(PGUUID(as_uuid=True), ForeignKey("services.id", ondelete="CASCADE"))
    document_type_id = Column(PGUUID(as_uuid=True), ForeignKey("document_types.id", ondelete="SET NULL"))

    # 파일 정보
    original_filename = Column(String(500), nullable=False)
    original_file_path = Column(String(1000))
    original_file_hash = Column(String(64))
    file_size_bytes = Column(BigInteger)
    page_count = Column(Integer)

    # 변환 결과
    output_filename = Column(String(500))
    output_file_path = Column(String(1000))
    output_format = Column(String(20), default="html")

    # 상태 관리
    status = Column(String(20), default="pending")
    error_message = Column(Text)

    # 품질 및 메타데이터
    quality_score = Column(Numeric(3, 2))
    processing_time_ms = Column(Integer)
    extra_data = Column(JSONB, default={})

    # 타임스탬프
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    processed_at = Column(DateTime(timezone=True))
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # 관계
    user = relationship("User", back_populates="documents")
    service = relationship("Service", back_populates="documents")
    document_type = relationship("DocumentType", back_populates="documents")
    blocks = relationship("DocumentBlock", back_populates="document", cascade="all, delete-orphan")

    # 인덱스
    __table_args__ = (
        Index('idx_documents_user', 'user_id'),
        Index('idx_documents_service', 'service_id'),
        Index('idx_documents_status', 'status'),
        Index('idx_documents_created', 'created_at'),
        Index('idx_documents_hash', 'original_file_hash'),
    )

    def __repr__(self):
        return f"<Document(filename='{self.original_filename}', status='{self.status}')>"


# ============================================
# 5. 문서 블록 모델
# ============================================
class DocumentBlock(Base):
    __tablename__ = "document_blocks"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    document_id = Column(PGUUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"))

    # 블록 정보
    block_type = Column(String(50), nullable=False)
    block_order = Column(Integer, nullable=False)
    page_number = Column(Integer)

    # 위치 정보
    position_x = Column(Integer)
    position_y = Column(Integer)
    width = Column(Integer)
    height = Column(Integer)

    # 콘텐츠
    content = Column(Text)
    html_content = Column(Text)

    # 스타일 및 메타데이터
    styles = Column(JSONB, default={})
    extra_data = Column(JSONB, default={})

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # 관계
    document = relationship("Document", back_populates="blocks")

    __table_args__ = (
        Index('idx_blocks_document', 'document_id'),
        Index('idx_blocks_type', 'block_type'),
    )

    def __repr__(self):
        return f"<DocumentBlock(type='{self.block_type}', order={self.block_order})>"


# ============================================
# 6. AI 학습 기록 모델
# ============================================
class AILearningRecord(Base):
    __tablename__ = "ai_learning_records"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    document_id = Column(PGUUID(as_uuid=True), ForeignKey("documents.id", ondelete="SET NULL"))
    service_id = Column(PGUUID(as_uuid=True), ForeignKey("services.id", ondelete="CASCADE"))
    document_type_id = Column(PGUUID(as_uuid=True), ForeignKey("document_types.id", ondelete="SET NULL"))

    # 학습 데이터
    input_features = Column(JSONB, nullable=False)
    output_result = Column(JSONB, nullable=False)

    # 품질 평가
    quality_score = Column(Numeric(3, 2))
    user_rating = Column(Integer)
    user_feedback = Column(Text)
    is_successful = Column(Boolean, default=True)

    # 패턴 정보
    pattern_id = Column(String(100))
    pattern_matched = Column(Boolean, default=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        CheckConstraint('user_rating >= 1 AND user_rating <= 5', name='chk_user_rating'),
        Index('idx_learning_service', 'service_id'),
        Index('idx_learning_type', 'document_type_id'),
        Index('idx_learning_quality', 'quality_score'),
    )


# ============================================
# 7. AI 패턴 모델
# ============================================
class AIPattern(Base):
    __tablename__ = "ai_patterns"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    service_id = Column(PGUUID(as_uuid=True), ForeignKey("services.id", ondelete="CASCADE"))
    document_type_id = Column(PGUUID(as_uuid=True), ForeignKey("document_types.id", ondelete="SET NULL"))

    pattern_name = Column(String(200), nullable=False)
    pattern_data = Column(JSONB, nullable=False)

    # 성능 지표
    usage_count = Column(Integer, default=0)
    success_rate = Column(Numeric(3, 2), default=0.00)
    avg_quality_score = Column(Numeric(3, 2))

    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index('idx_patterns_service', 'service_id'),
        Index('idx_patterns_success', 'success_rate'),
    )


# ============================================
# 8. API 키 모델
# ============================================
class ApiKey(Base):
    __tablename__ = "api_keys"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"))

    key_hash = Column(String(64), nullable=False)
    key_prefix = Column(String(10), nullable=False)
    name = Column(String(100))

    # 권한
    permissions = Column(JSONB, default=[])
    allowed_services = Column(JSONB, default=[])

    # 사용 제한
    rate_limit_per_minute = Column(Integer, default=60)
    rate_limit_per_day = Column(Integer, default=1000)

    # 상태
    is_active = Column(Boolean, default=True)
    last_used_at = Column(DateTime(timezone=True))
    expires_at = Column(DateTime(timezone=True))

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # 관계
    user = relationship("User", back_populates="api_keys")

    __table_args__ = (
        Index('idx_api_keys_user', 'user_id'),
        Index('idx_api_keys_prefix', 'key_prefix'),
    )


# ============================================
# 9. 감사 로그 모델
# ============================================
class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"))
    api_key_id = Column(PGUUID(as_uuid=True), ForeignKey("api_keys.id", ondelete="SET NULL"))

    action = Column(String(100), nullable=False)
    resource_type = Column(String(50))
    resource_id = Column(PGUUID(as_uuid=True))

    # 요청 정보
    ip_address = Column(INET)
    user_agent = Column(Text)
    request_data = Column(JSONB)

    # 결과
    is_success = Column(Boolean, default=True)
    error_message = Column(Text)
    response_time_ms = Column(Integer)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index('idx_audit_created', 'created_at'),
        Index('idx_audit_user', 'user_id'),
        Index('idx_audit_action', 'action'),
    )


# ============================================
# 10. 시스템 설정 모델
# ============================================
class SystemSetting(Base):
    __tablename__ = "system_settings"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    key = Column(String(100), unique=True, nullable=False)
    value = Column(JSONB, nullable=False)
    description = Column(Text)
    is_public = Column(Boolean, default=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


# ============================================
# 데이터베이스 연결 관리
# ============================================
class Database:
    """데이터베이스 연결 및 세션 관리"""

    def __init__(self, connection_string: str = None):
        if connection_string is None:
            # 기본 연결 문자열 (로컬 개발용)
            connection_string = "postgresql://studysnap:studysnap@localhost:5432/studysnap"

        self.engine = create_engine(connection_string, echo=False)
        self.SessionLocal = sessionmaker(bind=self.engine)

    def create_tables(self):
        """모든 테이블 생성"""
        Base.metadata.create_all(self.engine)

    def drop_tables(self):
        """모든 테이블 삭제 (주의!)"""
        Base.metadata.drop_all(self.engine)

    def get_session(self):
        """세션 반환"""
        return self.SessionLocal()

    def init_default_data(self):
        """기본 데이터 초기화"""
        session = self.get_session()
        try:
            # 서비스가 없으면 기본 서비스 추가
            if session.query(Service).count() == 0:
                default_services = [
                    Service(code="studysnap", name="StudySnap", description="PDF 학습 자료를 모바일 최적화 HTML로 변환"),
                    Service(code="lectures", name="Lectures", description="강의 콘텐츠 변환 서비스"),
                    Service(code="church", name="Church", description="교회 주보/설교 변환 서비스"),
                    Service(code="language", name="외국어 학습기", description="언어 학습 콘텐츠 변환"),
                    Service(code="catalog", name="기업용 카탈로그", description="제품 카탈로그 변환 서비스"),
                ]
                session.add_all(default_services)
                session.commit()
                print("기본 서비스 5개 등록 완료")

            # 관리자 계정이 없으면 생성
            if session.query(User).filter_by(role="admin").count() == 0:
                admin = User(
                    email="admin@studysnap.local",
                    name="관리자",
                    role="admin"
                )
                session.add(admin)
                session.commit()
                print("관리자 계정 생성 완료")

        except Exception as e:
            session.rollback()
            print(f"초기 데이터 생성 실패: {e}")
        finally:
            session.close()


# 싱글톤 인스턴스
_db_instance: Optional[Database] = None


def get_database(connection_string: str = None) -> Database:
    """데이터베이스 싱글톤 인스턴스 반환"""
    global _db_instance
    if _db_instance is None:
        _db_instance = Database(connection_string)
    return _db_instance
