-- ============================================
-- StudySnap Backend - PostgreSQL 데이터베이스 스키마
-- 다중 서비스 지원 (StudySnap, Lectures, Church, 외국어, 카탈로그)
-- 작성일: 2025-12-04
-- ============================================

-- UUID 확장 활성화
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================
-- 1. 서비스 정의 테이블
-- ============================================
CREATE TABLE services (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    code VARCHAR(50) UNIQUE NOT NULL,      -- 'studysnap', 'lectures', 'church', 'language', 'catalog'
    name VARCHAR(100) NOT NULL,             -- '스터디스냅', '강의 변환', '교회 주보'
    description TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    config JSONB DEFAULT '{}',              -- 서비스별 설정
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 기본 서비스 등록
INSERT INTO services (code, name, description) VALUES
    ('studysnap', 'StudySnap', 'PDF 학습 자료를 모바일 최적화 HTML로 변환'),
    ('lectures', 'Lectures', '강의 콘텐츠 변환 서비스'),
    ('church', 'Church', '교회 주보/설교 변환 서비스'),
    ('language', '외국어 학습기', '언어 학습 콘텐츠 변환'),
    ('catalog', '기업용 카탈로그', '제품 카탈로그 변환 서비스');

-- ============================================
-- 2. 사용자 테이블
-- ============================================
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255),             -- NULL이면 소셜 로그인 전용
    name VARCHAR(100),
    role VARCHAR(20) DEFAULT 'user',        -- 'admin', 'user', 'guest'
    is_active BOOLEAN DEFAULT TRUE,
    last_login_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 사용자-서비스 접근 권한 (다대다)
CREATE TABLE user_service_access (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    service_id UUID REFERENCES services(id) ON DELETE CASCADE,
    access_level VARCHAR(20) DEFAULT 'read', -- 'read', 'write', 'admin'
    granted_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    expires_at TIMESTAMP WITH TIME ZONE,     -- NULL이면 무제한
    UNIQUE(user_id, service_id)
);

-- ============================================
-- 3. 문서 타입 테이블
-- ============================================
CREATE TABLE document_types (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    service_id UUID REFERENCES services(id) ON DELETE CASCADE,
    code VARCHAR(50) NOT NULL,              -- 'election', 'newsletter', 'sermon', 'textbook'
    name VARCHAR(100) NOT NULL,
    description TEXT,
    template_config JSONB DEFAULT '{}',     -- 레이아웃, 색상 팔레트 등
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(service_id, code)
);

-- 기본 문서 타입 등록
INSERT INTO document_types (service_id, code, name, description, template_config)
SELECT s.id, dt.code, dt.name, dt.description, dt.config::jsonb
FROM services s
CROSS JOIN (VALUES
    ('studysnap', 'election', '선거 공보물', '후보자 선거 홍보물', '{"colors": {"primary": "#E11D48", "secondary": "#1E40AF"}}'),
    ('studysnap', 'newsletter', '뉴스레터', '일반 뉴스레터', '{"colors": {"primary": "#10B981", "secondary": "#6366F1"}}'),
    ('studysnap', 'textbook', '교재', '학습 교재', '{"colors": {"primary": "#3B82F6", "secondary": "#8B5CF6"}}'),
    ('church', 'sermon', '설교', '주일 설교 자료', '{"colors": {"primary": "#7C3AED", "secondary": "#EC4899"}}'),
    ('church', 'bulletin', '주보', '교회 주보', '{"colors": {"primary": "#059669", "secondary": "#0891B2"}}'),
    ('lectures', 'slide', '강의 슬라이드', 'PPT/PDF 강의 자료', '{"colors": {"primary": "#F59E0B", "secondary": "#EF4444"}}'),
    ('language', 'vocabulary', '어휘', '단어장', '{"colors": {"primary": "#06B6D4", "secondary": "#8B5CF6"}}'),
    ('catalog', 'product', '제품', '제품 카탈로그', '{"colors": {"primary": "#DC2626", "secondary": "#EA580C"}}')
) AS dt(service_code, code, name, description, config)
WHERE s.code = dt.service_code;

-- ============================================
-- 4. 문서 (변환 작업) 테이블
-- ============================================
CREATE TABLE documents (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    service_id UUID REFERENCES services(id) ON DELETE CASCADE,
    document_type_id UUID REFERENCES document_types(id) ON DELETE SET NULL,

    -- 파일 정보
    original_filename VARCHAR(500) NOT NULL,
    original_file_path VARCHAR(1000),       -- 원본 PDF 경로
    original_file_hash VARCHAR(64),         -- SHA-256 해시 (중복 검사용)
    file_size_bytes BIGINT,
    page_count INTEGER,

    -- 변환 결과
    output_filename VARCHAR(500),
    output_file_path VARCHAR(1000),         -- 생성된 HTML 경로
    output_format VARCHAR(20) DEFAULT 'html', -- 'html', 'json', 'markdown'

    -- 상태 관리
    status VARCHAR(20) DEFAULT 'pending',   -- 'pending', 'processing', 'completed', 'failed'
    error_message TEXT,

    -- 품질 및 메타데이터
    quality_score DECIMAL(3,2),             -- 0.00 ~ 1.00
    processing_time_ms INTEGER,
    metadata JSONB DEFAULT '{}',            -- 추출된 메타데이터

    -- 타임스탬프
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    processed_at TIMESTAMP WITH TIME ZONE,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 인덱스
CREATE INDEX idx_documents_user ON documents(user_id);
CREATE INDEX idx_documents_service ON documents(service_id);
CREATE INDEX idx_documents_status ON documents(status);
CREATE INDEX idx_documents_created ON documents(created_at DESC);
CREATE INDEX idx_documents_hash ON documents(original_file_hash);

-- ============================================
-- 5. 문서 콘텐츠 블록 테이블
-- ============================================
CREATE TABLE document_blocks (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    document_id UUID REFERENCES documents(id) ON DELETE CASCADE,

    -- 블록 정보
    block_type VARCHAR(50) NOT NULL,        -- 'header', 'title', 'paragraph', 'image', 'list', 'table'
    block_order INTEGER NOT NULL,
    page_number INTEGER,

    -- 위치 정보 (픽셀)
    position_x INTEGER,
    position_y INTEGER,
    width INTEGER,
    height INTEGER,

    -- 콘텐츠
    content TEXT,
    html_content TEXT,

    -- 스타일 및 메타데이터
    styles JSONB DEFAULT '{}',              -- 폰트, 색상, 정렬 등
    metadata JSONB DEFAULT '{}',

    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_blocks_document ON document_blocks(document_id);
CREATE INDEX idx_blocks_type ON document_blocks(block_type);

-- ============================================
-- 6. AI 학습 데이터 테이블
-- ============================================
CREATE TABLE ai_learning_records (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    document_id UUID REFERENCES documents(id) ON DELETE SET NULL,
    service_id UUID REFERENCES services(id) ON DELETE CASCADE,
    document_type_id UUID REFERENCES document_types(id) ON DELETE SET NULL,

    -- 학습 데이터
    input_features JSONB NOT NULL,          -- 입력 특성
    output_result JSONB NOT NULL,           -- 출력 결과

    -- 품질 평가
    quality_score DECIMAL(3,2),
    user_rating INTEGER CHECK (user_rating BETWEEN 1 AND 5),
    user_feedback TEXT,
    is_successful BOOLEAN DEFAULT TRUE,

    -- 패턴 정보
    pattern_id VARCHAR(100),
    pattern_matched BOOLEAN DEFAULT FALSE,

    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_learning_service ON ai_learning_records(service_id);
CREATE INDEX idx_learning_type ON ai_learning_records(document_type_id);
CREATE INDEX idx_learning_quality ON ai_learning_records(quality_score DESC);

-- ============================================
-- 7. AI 패턴 테이블
-- ============================================
CREATE TABLE ai_patterns (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    service_id UUID REFERENCES services(id) ON DELETE CASCADE,
    document_type_id UUID REFERENCES document_types(id) ON DELETE SET NULL,

    pattern_name VARCHAR(200) NOT NULL,
    pattern_data JSONB NOT NULL,            -- 패턴 정의

    -- 성능 지표
    usage_count INTEGER DEFAULT 0,
    success_rate DECIMAL(3,2) DEFAULT 0.00,
    avg_quality_score DECIMAL(3,2),

    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_patterns_service ON ai_patterns(service_id);
CREATE INDEX idx_patterns_success ON ai_patterns(success_rate DESC);

-- ============================================
-- 8. API 키 테이블
-- ============================================
CREATE TABLE api_keys (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,

    key_hash VARCHAR(64) NOT NULL,          -- SHA-256 해시된 API 키
    key_prefix VARCHAR(10) NOT NULL,        -- 키 앞 8자 (식별용)
    name VARCHAR(100),

    -- 권한
    permissions JSONB DEFAULT '[]',         -- ['use_layout', 'use_ai_agent']
    allowed_services JSONB DEFAULT '[]',    -- 허용된 서비스 ID 목록

    -- 사용 제한
    rate_limit_per_minute INTEGER DEFAULT 60,
    rate_limit_per_day INTEGER DEFAULT 1000,

    -- 상태
    is_active BOOLEAN DEFAULT TRUE,
    last_used_at TIMESTAMP WITH TIME ZONE,
    expires_at TIMESTAMP WITH TIME ZONE,

    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_api_keys_user ON api_keys(user_id);
CREATE INDEX idx_api_keys_prefix ON api_keys(key_prefix);

-- ============================================
-- 9. 감사 로그 테이블
-- ============================================
CREATE TABLE audit_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    api_key_id UUID REFERENCES api_keys(id) ON DELETE SET NULL,

    action VARCHAR(100) NOT NULL,           -- 'document.create', 'document.convert', 'api.call'
    resource_type VARCHAR(50),              -- 'document', 'user', 'api_key'
    resource_id UUID,

    -- 요청 정보
    ip_address INET,
    user_agent TEXT,
    request_data JSONB,

    -- 결과
    is_success BOOLEAN DEFAULT TRUE,
    error_message TEXT,
    response_time_ms INTEGER,

    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 파티셔닝을 위한 인덱스 (대량 로그 처리)
CREATE INDEX idx_audit_created ON audit_logs(created_at DESC);
CREATE INDEX idx_audit_user ON audit_logs(user_id);
CREATE INDEX idx_audit_action ON audit_logs(action);

-- ============================================
-- 10. 시스템 설정 테이블
-- ============================================
CREATE TABLE system_settings (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    key VARCHAR(100) UNIQUE NOT NULL,
    value JSONB NOT NULL,
    description TEXT,
    is_public BOOLEAN DEFAULT FALSE,        -- 클라이언트에 노출 가능 여부
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 기본 시스템 설정
INSERT INTO system_settings (key, value, description, is_public) VALUES
    ('max_file_size_mb', '50', '최대 업로드 파일 크기 (MB)', true),
    ('max_pages_per_document', '100', '문서당 최대 페이지 수', true),
    ('default_output_format', '"html"', '기본 출력 형식', true),
    ('ai_learning_enabled', 'true', 'AI 학습 기능 활성화', false),
    ('maintenance_mode', 'false', '유지보수 모드', false);

-- ============================================
-- 뷰: 문서 통계
-- ============================================
CREATE VIEW document_stats AS
SELECT
    s.code AS service_code,
    s.name AS service_name,
    dt.code AS document_type_code,
    dt.name AS document_type_name,
    COUNT(d.id) AS total_documents,
    COUNT(CASE WHEN d.status = 'completed' THEN 1 END) AS completed_count,
    COUNT(CASE WHEN d.status = 'failed' THEN 1 END) AS failed_count,
    AVG(d.quality_score) AS avg_quality_score,
    AVG(d.processing_time_ms) AS avg_processing_time_ms
FROM services s
LEFT JOIN document_types dt ON dt.service_id = s.id
LEFT JOIN documents d ON d.document_type_id = dt.id
GROUP BY s.code, s.name, dt.code, dt.name;

-- ============================================
-- 함수: 업데이트 시간 자동 갱신
-- ============================================
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- 트리거 적용
CREATE TRIGGER update_services_updated_at
    BEFORE UPDATE ON services
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER update_users_updated_at
    BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER update_documents_updated_at
    BEFORE UPDATE ON documents
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER update_ai_patterns_updated_at
    BEFORE UPDATE ON ai_patterns
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

-- ============================================
-- 완료 메시지
-- ============================================
-- 스키마 생성 완료!
-- 테이블: 10개
-- 뷰: 1개
-- 함수: 1개
-- 트리거: 4개
