"""
StudySnap Backend - 데이터베이스 연결 관리
SQLite (개발/소규모) 및 PostgreSQL (프로덕션) 지원
"""

import os
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List
from contextlib import contextmanager

# SQLite용 (기본)
import sqlite3

logger = logging.getLogger(__name__)


def _serialize_value(value):
    """값을 JSON 직렬화 가능한 형태로 변환"""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.isoformat()
    # SQLite TIMESTAMP 타입 처리 (문자열로 반환될 수 있음)
    if hasattr(value, 'isoformat'):
        return value.isoformat()
    return value


def _serialize_row(row: Dict) -> Dict:
    """행 데이터의 datetime 값을 문자열로 변환"""
    return {key: _serialize_value(value) for key, value in row.items()}


# 데이터베이스 경로
DB_DIR = Path(__file__).parent
SQLITE_DB_PATH = DB_DIR / "studysnap.db"


class DatabaseManager:
    """데이터베이스 연결 및 작업 관리"""

    def __init__(self, db_type: str = "sqlite", connection_string: str = None):
        """
        Args:
            db_type: "sqlite" 또는 "postgresql"
            connection_string: PostgreSQL 연결 문자열 (postgresql://user:pass@host:port/db)
        """
        self.db_type = db_type
        self.connection_string = connection_string
        self._connection = None

        if db_type == "sqlite":
            self._init_sqlite()
        elif db_type == "postgresql":
            self._init_postgresql()

    def _init_sqlite(self):
        """SQLite 초기화"""
        try:
            self._connection = sqlite3.connect(
                str(SQLITE_DB_PATH),
                check_same_thread=False,
                detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES
            )
            self._connection.row_factory = sqlite3.Row
            self._create_tables_sqlite()
            logger.info(f"SQLite 데이터베이스 연결 완료: {SQLITE_DB_PATH}")
        except Exception as e:
            logger.error(f"SQLite 초기화 실패: {e}")
            raise

    def _init_postgresql(self):
        """PostgreSQL 초기화"""
        try:
            import psycopg2
            from psycopg2.extras import RealDictCursor

            self._connection = psycopg2.connect(
                self.connection_string,
                cursor_factory=RealDictCursor
            )
            logger.info("PostgreSQL 데이터베이스 연결 완료")
        except ImportError:
            logger.warning("psycopg2가 설치되지 않음, SQLite로 폴백")
            self.db_type = "sqlite"
            self._init_sqlite()
        except Exception as e:
            logger.error(f"PostgreSQL 연결 실패: {e}, SQLite로 폴백")
            self.db_type = "sqlite"
            self._init_sqlite()

    def _create_tables_sqlite(self):
        """SQLite 테이블 생성"""
        cursor = self._connection.cursor()

        # 서비스 테이블
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS services (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code TEXT UNIQUE NOT NULL,
                name TEXT NOT NULL,
                description TEXT,
                is_active INTEGER DEFAULT 1,
                config TEXT DEFAULT '{}',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # 사용자 테이블
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT,
                name TEXT,
                role TEXT DEFAULT 'user',
                is_active INTEGER DEFAULT 1,
                last_login_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # 문서 타입 테이블
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS document_types (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                service_id INTEGER REFERENCES services(id),
                code TEXT NOT NULL,
                name TEXT NOT NULL,
                description TEXT,
                template_config TEXT DEFAULT '{}',
                is_active INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(service_id, code)
            )
        ''')

        # 문서 (변환 작업) 테이블
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS documents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER REFERENCES users(id),
                service_id INTEGER REFERENCES services(id),
                document_type_id INTEGER REFERENCES document_types(id),

                original_filename TEXT NOT NULL,
                original_file_path TEXT,
                original_file_hash TEXT,
                file_size_bytes INTEGER,
                page_count INTEGER,

                output_filename TEXT,
                output_file_path TEXT,
                output_format TEXT DEFAULT 'html',

                status TEXT DEFAULT 'pending',
                error_message TEXT,

                quality_score REAL,
                processing_time_ms INTEGER,
                metadata TEXT DEFAULT '{}',

                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                processed_at TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # AI 학습 기록 테이블
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS ai_learning_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                document_id INTEGER REFERENCES documents(id),
                service_id INTEGER REFERENCES services(id),
                document_type_id INTEGER REFERENCES document_types(id),

                input_features TEXT NOT NULL,
                output_result TEXT NOT NULL,

                quality_score REAL,
                user_rating INTEGER CHECK (user_rating BETWEEN 1 AND 5),
                user_feedback TEXT,
                is_successful INTEGER DEFAULT 1,

                pattern_id TEXT,
                pattern_matched INTEGER DEFAULT 0,

                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # 고객 테이블 (비즈니스용)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS customers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER REFERENCES users(id),
                company_name TEXT,
                contact_name TEXT,
                contact_email TEXT,
                contact_phone TEXT,
                plan_type TEXT DEFAULT 'free',
                subscription_start TIMESTAMP,
                subscription_end TIMESTAMP,
                usage_limit INTEGER DEFAULT 100,
                usage_count INTEGER DEFAULT 0,
                metadata TEXT DEFAULT '{}',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # 교회 주보 전용 테이블
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS church_bulletins (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                document_id INTEGER REFERENCES documents(id),
                church_name TEXT NOT NULL,
                bulletin_date DATE NOT NULL,
                theme TEXT DEFAULT 'default',

                sermon_title TEXT,
                sermon_scripture TEXT,
                sermon_preacher TEXT,

                worship_services TEXT,
                choir_info TEXT,
                news_items TEXT,

                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(church_name, bulletin_date)
            )
        ''')

        # 교회 템플릿 테이블 (머신러닝 고도화)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS church_templates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                church_name TEXT NOT NULL,
                template_name TEXT NOT NULL,

                -- 기본 설정
                theme TEXT DEFAULT 'default',
                color_primary TEXT DEFAULT '#5b4b9e',
                color_secondary TEXT DEFAULT '#7c6bb8',
                logo_url TEXT,

                -- 예배 순서 템플릿
                worship_order TEXT,
                common_hymns TEXT,
                service_times TEXT,

                -- 생명의 말씀 기본 구조
                sermon_structure TEXT,
                pastor_name TEXT,

                -- 섹션 표시 설정
                show_sections TEXT DEFAULT '{"verse":true,"worship":true,"sermon_word":true,"choir":true,"news":true}',

                -- 머신러닝 데이터
                usage_count INTEGER DEFAULT 0,
                success_rate REAL DEFAULT 0.0,
                avg_quality_score REAL,
                learned_patterns TEXT,

                is_active INTEGER DEFAULT 1,
                is_default INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

                UNIQUE(church_name, template_name)
            )
        ''')

        # 외국어 학습 콘텐츠 테이블
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS language_contents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                document_id INTEGER REFERENCES documents(id),
                language_pair TEXT NOT NULL,
                content_type TEXT NOT NULL,
                occupation TEXT,
                difficulty_level TEXT DEFAULT 'intermediate',

                source_text TEXT,
                target_text TEXT,
                pronunciation TEXT,
                audio_url TEXT,

                vocabulary TEXT,
                grammar_points TEXT,
                cultural_notes TEXT,

                usage_count INTEGER DEFAULT 0,
                avg_rating REAL,

                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # 선거 공보물 테이블
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS election_materials (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                document_id INTEGER REFERENCES documents(id),
                candidate_name TEXT,
                party_name TEXT,
                district TEXT,
                election_type TEXT,

                profile_data TEXT,
                pledges TEXT,
                career TEXT,

                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # 감사 로그 테이블
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS audit_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER REFERENCES users(id),
                action TEXT NOT NULL,
                resource_type TEXT,
                resource_id INTEGER,

                ip_address TEXT,
                user_agent TEXT,
                request_data TEXT,

                is_success INTEGER DEFAULT 1,
                error_message TEXT,
                response_time_ms INTEGER,

                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # 인덱스 생성
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_documents_status ON documents(status)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_documents_service ON documents(service_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_documents_created ON documents(created_at DESC)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_church_bulletins_church ON church_bulletins(church_name)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_audit_logs_action ON audit_logs(action)')

        # 기본 데이터 삽입
        self._insert_default_data(cursor)

        self._connection.commit()
        logger.info("SQLite 테이블 생성 완료")

    def _insert_default_data(self, cursor):
        """기본 데이터 삽입"""
        # 기본 서비스 확인 및 삽입
        cursor.execute("SELECT COUNT(*) FROM services")
        if cursor.fetchone()[0] == 0:
            services = [
                ('studysnap', 'StudySnap', 'PDF 학습 자료를 모바일 최적화 HTML로 변환'),
                ('church', '교회 주보', '교회 주보/설교 변환 서비스'),
                ('election', '선거 공보물', '선거 홍보물 변환 서비스'),
                ('language', '외국어 학습기', '언어 학습 콘텐츠 변환'),
                ('catalog', '기업용 카탈로그', '제품 카탈로그 변환 서비스'),
                ('newsletter', '지자체 소식지', '지자체/기관 소식지 변환'),
                ('lectures', '강의 자료', '강의 콘텐츠 변환 서비스'),
            ]
            cursor.executemany(
                "INSERT INTO services (code, name, description) VALUES (?, ?, ?)",
                services
            )
            logger.info(f"기본 서비스 {len(services)}개 등록")

        # 기본 문서 타입 확인 및 삽입
        cursor.execute("SELECT COUNT(*) FROM document_types")
        if cursor.fetchone()[0] == 0:
            # 서비스 ID 조회
            cursor.execute("SELECT id, code FROM services")
            service_map = {row[1]: row[0] for row in cursor.fetchall()}

            doc_types = [
                (service_map.get('church'), 'bulletin', '주보', '교회 주보'),
                (service_map.get('church'), 'sermon', '설교', '주일 설교 자료'),
                (service_map.get('election'), 'campaign', '공보물', '선거 홍보물'),
                (service_map.get('language'), 'vocabulary', '어휘', '단어장'),
                (service_map.get('language'), 'dialogue', '회화', '회화 자료'),
                (service_map.get('catalog'), 'product', '제품', '제품 카탈로그'),
                (service_map.get('newsletter'), 'monthly', '월간', '월간 소식지'),
                (service_map.get('lectures'), 'slide', '슬라이드', '강의 슬라이드'),
            ]
            cursor.executemany(
                "INSERT INTO document_types (service_id, code, name, description) VALUES (?, ?, ?, ?)",
                [(s, c, n, d) for s, c, n, d in doc_types if s]
            )
            logger.info("기본 문서 타입 등록")

    @contextmanager
    def get_cursor(self):
        """커서 컨텍스트 매니저"""
        cursor = self._connection.cursor()
        try:
            yield cursor
            self._connection.commit()
        except Exception as e:
            self._connection.rollback()
            logger.error(f"DB 작업 실패: {e}")
            raise
        finally:
            cursor.close()

    def execute(self, query: str, params: tuple = None) -> List[Dict]:
        """쿼리 실행 및 결과 반환"""
        with self.get_cursor() as cursor:
            cursor.execute(query, params or ())
            if query.strip().upper().startswith('SELECT'):
                columns = [desc[0] for desc in cursor.description]
                rows = [dict(zip(columns, row)) for row in cursor.fetchall()]
                return [_serialize_row(row) for row in rows]
            return []

    def execute_many(self, query: str, params_list: List[tuple]):
        """여러 쿼리 일괄 실행"""
        with self.get_cursor() as cursor:
            cursor.executemany(query, params_list)

    def insert(self, table: str, data: Dict[str, Any]) -> int:
        """데이터 삽입 및 ID 반환"""
        columns = ', '.join(data.keys())
        placeholders = ', '.join(['?' for _ in data])
        query = f"INSERT INTO {table} ({columns}) VALUES ({placeholders})"

        with self.get_cursor() as cursor:
            cursor.execute(query, tuple(data.values()))
            return cursor.lastrowid

    def update(self, table: str, data: Dict[str, Any], where: str, params: tuple = None):
        """데이터 업데이트"""
        set_clause = ', '.join([f"{k} = ?" for k in data.keys()])
        query = f"UPDATE {table} SET {set_clause}, updated_at = CURRENT_TIMESTAMP WHERE {where}"

        with self.get_cursor() as cursor:
            cursor.execute(query, tuple(data.values()) + (params or ()))

    def close(self):
        """연결 종료"""
        if self._connection:
            self._connection.close()
            logger.info("데이터베이스 연결 종료")


# ============================================
# 비즈니스 로직 헬퍼 함수
# ============================================

class DocumentRepository:
    """문서 관련 데이터베이스 작업"""

    def __init__(self, db: DatabaseManager):
        self.db = db

    def create_document(self, service_code: str, filename: str,
                        file_path: str = None, file_size: int = None,
                        page_count: int = None, metadata: Dict = None) -> int:
        """새 문서 레코드 생성"""
        # 서비스 ID 조회
        result = self.db.execute(
            "SELECT id FROM services WHERE code = ?", (service_code,)
        )
        service_id = result[0]['id'] if result else None

        return self.db.insert('documents', {
            'service_id': service_id,
            'original_filename': filename,
            'original_file_path': file_path,
            'file_size_bytes': file_size,
            'page_count': page_count,
            'metadata': json.dumps(metadata or {}),
            'status': 'pending'
        })

    def update_document_status(self, doc_id: int, status: str,
                               output_path: str = None, error: str = None,
                               processing_time: int = None):
        """문서 상태 업데이트"""
        data = {'status': status}
        if output_path:
            data['output_file_path'] = output_path
            data['output_filename'] = os.path.basename(output_path)
        if error:
            data['error_message'] = error
        if processing_time:
            data['processing_time_ms'] = processing_time
        if status == 'completed':
            data['processed_at'] = datetime.now().isoformat()

        self.db.update('documents', data, 'id = ?', (doc_id,))

    def get_recent_documents(self, service_code: str = None, limit: int = 50) -> List[Dict]:
        """최근 문서 목록 조회"""
        if service_code:
            return self.db.execute('''
                SELECT d.*, s.name as service_name
                FROM documents d
                JOIN services s ON d.service_id = s.id
                WHERE s.code = ?
                ORDER BY d.created_at DESC
                LIMIT ?
            ''', (service_code, limit))
        else:
            return self.db.execute('''
                SELECT d.*, s.name as service_name
                FROM documents d
                LEFT JOIN services s ON d.service_id = s.id
                ORDER BY d.created_at DESC
                LIMIT ?
            ''', (limit,))

    def get_statistics(self, service_code: str = None) -> Dict:
        """통계 조회"""
        if service_code:
            result = self.db.execute('''
                SELECT
                    COUNT(*) as total,
                    SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed,
                    SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed,
                    AVG(processing_time_ms) as avg_time,
                    AVG(quality_score) as avg_quality
                FROM documents d
                JOIN services s ON d.service_id = s.id
                WHERE s.code = ?
            ''', (service_code,))
        else:
            result = self.db.execute('''
                SELECT
                    COUNT(*) as total,
                    SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed,
                    SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed,
                    AVG(processing_time_ms) as avg_time,
                    AVG(quality_score) as avg_quality
                FROM documents
            ''')
        return result[0] if result else {}


class ChurchBulletinRepository:
    """교회 주보 전용 데이터베이스 작업"""

    def __init__(self, db: DatabaseManager):
        self.db = db

    def save_bulletin(self, doc_id: int, church_name: str, bulletin_date: str,
                      theme: str = 'default', sermon_data: Dict = None,
                      services_data: List = None, news_data: List = None) -> int:
        """주보 데이터 저장"""
        sermon = sermon_data or {}

        # 기존 데이터 확인 (중복 방지)
        existing = self.db.execute(
            "SELECT id FROM church_bulletins WHERE church_name = ? AND bulletin_date = ?",
            (church_name, bulletin_date)
        )

        data = {
            'document_id': doc_id,
            'church_name': church_name,
            'bulletin_date': bulletin_date,
            'theme': theme,
            'sermon_title': sermon.get('title', ''),
            'sermon_scripture': sermon.get('scripture', ''),
            'sermon_preacher': sermon.get('preacher', ''),
            'worship_services': json.dumps(services_data or [], ensure_ascii=False),
            'news_items': json.dumps(news_data or [], ensure_ascii=False)
        }

        if existing:
            self.db.update('church_bulletins', data, 'id = ?', (existing[0]['id'],))
            return existing[0]['id']
        else:
            return self.db.insert('church_bulletins', data)

    def get_church_bulletins(self, church_name: str, limit: int = 20) -> List[Dict]:
        """교회별 주보 목록 조회"""
        return self.db.execute('''
            SELECT * FROM church_bulletins
            WHERE church_name = ?
            ORDER BY bulletin_date DESC
            LIMIT ?
        ''', (church_name, limit))

    def get_churches(self) -> List[Dict]:
        """등록된 교회 목록"""
        return self.db.execute('''
            SELECT church_name, COUNT(*) as bulletin_count,
                   MAX(bulletin_date) as last_bulletin
            FROM church_bulletins
            GROUP BY church_name
            ORDER BY last_bulletin DESC
        ''')


class ChurchTemplateRepository:
    """교회 템플릿 데이터베이스 작업 (머신러닝 고도화)"""

    def __init__(self, db: DatabaseManager):
        self.db = db

    def save_template(self, church_name: str, template_name: str,
                      template_data: Dict) -> int:
        """템플릿 저장/업데이트"""
        # 기존 템플릿 확인
        existing = self.db.execute(
            "SELECT id FROM church_templates WHERE church_name = ? AND template_name = ?",
            (church_name, template_name)
        )

        data = {
            'church_name': church_name,
            'template_name': template_name,
            'theme': template_data.get('theme', 'default'),
            'color_primary': template_data.get('color_primary', '#5b4b9e'),
            'color_secondary': template_data.get('color_secondary', '#7c6bb8'),
            'logo_url': template_data.get('logo_url', ''),
            'worship_order': json.dumps(template_data.get('worship_order', []), ensure_ascii=False),
            'common_hymns': json.dumps(template_data.get('common_hymns', {}), ensure_ascii=False),
            'service_times': json.dumps(template_data.get('service_times', []), ensure_ascii=False),
            'sermon_structure': json.dumps(template_data.get('sermon_structure', []), ensure_ascii=False),
            'pastor_name': template_data.get('pastor_name', ''),
            'show_sections': json.dumps(template_data.get('show_sections', {}), ensure_ascii=False),
            'learned_patterns': json.dumps(template_data.get('learned_patterns', {}), ensure_ascii=False),
            'updated_at': datetime.now().isoformat()
        }

        if existing:
            self.db.update('church_templates', data, 'id = ?', (existing[0]['id'],))
            return existing[0]['id']
        else:
            return self.db.insert('church_templates', data)

    def get_template(self, church_name: str, template_name: str = None) -> Optional[Dict]:
        """템플릿 조회 (기본 템플릿 또는 지정 템플릿)"""
        if template_name:
            result = self.db.execute(
                "SELECT * FROM church_templates WHERE church_name = ? AND template_name = ?",
                (church_name, template_name)
            )
        else:
            # 기본 템플릿 조회
            result = self.db.execute(
                "SELECT * FROM church_templates WHERE church_name = ? AND is_default = 1",
                (church_name,)
            )
            if not result:
                # 기본이 없으면 최신 템플릿
                result = self.db.execute(
                    "SELECT * FROM church_templates WHERE church_name = ? ORDER BY updated_at DESC LIMIT 1",
                    (church_name,)
                )

        if result:
            template = dict(result[0])
            # JSON 필드 파싱
            for field in ['worship_order', 'common_hymns', 'service_times',
                          'sermon_structure', 'show_sections', 'learned_patterns']:
                if template.get(field):
                    try:
                        template[field] = json.loads(template[field])
                    except:
                        pass
            return template
        return None

    def get_churches_with_templates(self) -> List[Dict]:
        """템플릿이 있는 교회 목록"""
        return self.db.execute('''
            SELECT church_name, COUNT(*) as template_count,
                   MAX(updated_at) as last_updated,
                   AVG(avg_quality_score) as avg_quality
            FROM church_templates
            WHERE is_active = 1
            GROUP BY church_name
            ORDER BY last_updated DESC
        ''')

    def update_learning_stats(self, template_id: int, quality_score: float,
                              is_successful: bool = True):
        """학습 통계 업데이트"""
        template = self.db.execute(
            "SELECT usage_count, success_rate, avg_quality_score FROM church_templates WHERE id = ?",
            (template_id,)
        )

        if template:
            t = template[0]
            new_count = (t['usage_count'] or 0) + 1
            old_success = (t['success_rate'] or 0) * (t['usage_count'] or 0)
            new_success_rate = (old_success + (1 if is_successful else 0)) / new_count

            old_quality = (t['avg_quality_score'] or 0) * (t['usage_count'] or 0)
            new_avg_quality = (old_quality + quality_score) / new_count

            self.db.update('church_templates', {
                'usage_count': new_count,
                'success_rate': round(new_success_rate, 4),
                'avg_quality_score': round(new_avg_quality, 2),
                'updated_at': datetime.now().isoformat()
            }, 'id = ?', (template_id,))

    def save_learned_pattern(self, template_id: int, pattern_key: str, pattern_data: Dict):
        """학습된 패턴 저장"""
        template = self.db.execute(
            "SELECT learned_patterns FROM church_templates WHERE id = ?",
            (template_id,)
        )

        if template:
            patterns = {}
            if template[0]['learned_patterns']:
                try:
                    patterns = json.loads(template[0]['learned_patterns'])
                except:
                    pass

            patterns[pattern_key] = pattern_data
            self.db.update('church_templates', {
                'learned_patterns': json.dumps(patterns, ensure_ascii=False),
                'updated_at': datetime.now().isoformat()
            }, 'id = ?', (template_id,))

    def create_default_template(self, church_name: str) -> int:
        """여의도순복음교회 기본 템플릿 생성"""
        default_template = {
            'theme': 'default',
            'color_primary': '#5b4b9e',
            'color_secondary': '#7c6bb8',
            'pastor_name': '이영훈 위임목사',
            'worship_order': [
                {'order': 1, 'name': '예배로 부르심', 'content': '요 4:24', 'participant': '사회자'},
                {'order': 2, 'name': '찬송', 'content': '8장(통9장) 4절', 'participant': '다같이'},
                {'order': 3, 'name': '신앙고백', 'content': '사도신경', 'participant': '다같이'},
                {'order': 4, 'name': '찬송', 'content': '', 'participant': '다같이'},
                {'order': 5, 'name': '기도', 'content': '', 'participant': '대표기도자'},
                {'order': 6, 'name': '성경봉독', 'content': '', 'participant': '사회자'},
                {'order': 7, 'name': '찬양', 'content': '', 'participant': '찬양대'},
                {'order': 8, 'name': '설교', 'content': '', 'participant': '담임목사'},
                {'order': 9, 'name': '기도와 결신', 'content': '', 'participant': '설교자'},
                {'order': 10, 'name': '헌금기도', 'content': '', 'participant': '헌금기도자'},
                {'order': 11, 'name': '찬송', 'content': '635장 주기도문', 'participant': '다같이'},
                {'order': 12, 'name': '축도', 'content': '', 'participant': '설교자'}
            ],
            'service_times': [
                {'name': '1부 예배', 'time': '오전 7:00'},
                {'name': '2부 예배', 'time': '오전 9:00'},
                {'name': '3부 예배', 'time': '오전 11:00'},
                {'name': '4부 예배', 'time': '오후 1:00'},
                {'name': '5부 대학청년 예배', 'time': '오후 2:00'},
                {'name': '주일저녁 예배', 'time': '오후 7:00'}
            ],
            'sermon_structure': [
                {'subtitle': '1. 마음의 골짜기를 메우라', 'key_verse': '눅 3:5'},
                {'subtitle': '2. 교만의 산을 낮추라', 'key_verse': '눅 3:5'},
                {'subtitle': '3. 굽은 것을 곧게 하라', 'key_verse': '눅 3:5'}
            ],
            'show_sections': {
                'verse': True, 'worship': True, 'sermon_word': True,
                'choir': True, 'news': True, 'devotional': True
            }
        }

        return self.save_template(church_name, 'default', default_template)


class AuditLogger:
    """감사 로그 기록"""

    def __init__(self, db: DatabaseManager):
        self.db = db

    def log(self, action: str, resource_type: str = None, resource_id: int = None,
            user_id: int = None, ip_address: str = None, is_success: bool = True,
            error_message: str = None, response_time_ms: int = None):
        """로그 기록"""
        self.db.insert('audit_logs', {
            'user_id': user_id,
            'action': action,
            'resource_type': resource_type,
            'resource_id': resource_id,
            'ip_address': ip_address,
            'is_success': 1 if is_success else 0,
            'error_message': error_message,
            'response_time_ms': response_time_ms
        })


# ============================================
# 싱글톤 인스턴스
# ============================================
_db_instance: Optional[DatabaseManager] = None


def get_db() -> DatabaseManager:
    """데이터베이스 싱글톤 인스턴스 반환"""
    global _db_instance
    if _db_instance is None:
        # 환경변수에서 설정 읽기
        db_type = os.environ.get('DB_TYPE', 'sqlite')
        db_url = os.environ.get('DATABASE_URL')

        _db_instance = DatabaseManager(
            db_type=db_type,
            connection_string=db_url
        )
    return _db_instance


def init_db():
    """데이터베이스 초기화"""
    db = get_db()
    logger.info(f"데이터베이스 초기화 완료 (타입: {db.db_type})")
    return db


if __name__ == "__main__":
    # 테스트 실행
    logging.basicConfig(level=logging.INFO)

    db = init_db()

    # 서비스 목록 확인
    services = db.execute("SELECT * FROM services")
    print("\n등록된 서비스:")
    for s in services:
        print(f"  - {s['name']} ({s['code']})")

    # 문서 저장소 테스트
    doc_repo = DocumentRepository(db)
    doc_id = doc_repo.create_document(
        service_code='church',
        filename='test_bulletin.pdf',
        metadata={'test': True}
    )
    print(f"\n테스트 문서 생성: ID={doc_id}")

    # 통계 확인
    stats = doc_repo.get_statistics()
    print(f"\n전체 통계: {stats}")

    db.close()
    print("\n데이터베이스 테스트 완료!")
