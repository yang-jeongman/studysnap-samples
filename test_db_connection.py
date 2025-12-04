"""
StudySnap Backend - Database Connection Test
"""

import sys
import os
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, 'c:\\StudySnap-Backend')

def test_connection():
    """데이터베이스 연결 테스트"""
    try:
        from database.models import get_database, Service, User, DocumentType

        # 연결 문자열 (PostgreSQL 설치 시 설정한 비밀번호로 변경)
        connection_string = "postgresql://studysnap:studysnap@localhost:5432/studysnap"

        print("=" * 50)
        print("StudySnap 데이터베이스 연결 테스트")
        print("=" * 50)

        # 데이터베이스 연결
        print("\n1. 데이터베이스 연결 중...")
        db = get_database(connection_string)
        print("   ✅ 연결 성공!")

        # 기본 데이터 초기화
        print("\n2. 기본 데이터 초기화 중...")
        db.init_default_data()
        print("   ✅ 초기화 완료!")

        # 세션 생성
        print("\n3. 데이터 조회 테스트...")
        session = db.get_session()

        # 서비스 목록 조회
        services = session.query(Service).all()
        print(f"\n   📦 등록된 서비스 ({len(services)}개):")
        for s in services:
            status = "✅ 활성" if s.is_active else "❌ 비활성"
            print(f"      - {s.name} ({s.code}) [{status}]")

        # 사용자 목록 조회
        users = session.query(User).all()
        print(f"\n   👤 등록된 사용자 ({len(users)}명):")
        for u in users:
            print(f"      - {u.name} ({u.email}) [역할: {u.role}]")

        # 문서 타입 조회
        doc_types = session.query(DocumentType).all()
        print(f"\n   📄 등록된 문서 타입 ({len(doc_types)}개):")
        for dt in doc_types:
            print(f"      - {dt.name} ({dt.code})")

        session.close()

        print("\n" + "=" * 50)
        print("✅ 모든 테스트 통과! 데이터베이스가 정상 작동합니다.")
        print("=" * 50)

        return True

    except ImportError as e:
        print(f"\n❌ 모듈 임포트 오류: {e}")
        print("\n필요한 패키지를 설치하세요:")
        print("   pip install psycopg2-binary sqlalchemy")
        return False

    except Exception as e:
        print(f"\n❌ 연결 오류: {e}")
        print("\n확인 사항:")
        print("   1. PostgreSQL이 설치되어 실행 중인가요?")
        print("   2. 'studysnap' 데이터베이스가 생성되었나요?")
        print("   3. 사용자명/비밀번호가 올바른가요?")
        print("   4. schema.sql이 적용되었나요?")
        return False


if __name__ == "__main__":
    success = test_connection()
    sys.exit(0 if success else 1)
