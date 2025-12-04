# PostgreSQL 데이터베이스 설치 및 설정 가이드

## 1. PostgreSQL 설치 (Windows)

### 방법 1: 공식 설치 프로그램 (권장)
1. https://www.postgresql.org/download/windows/ 접속
2. "Download the installer" 클릭
3. 최신 버전 (PostgreSQL 16) 다운로드
4. 설치 시 설정:
   - **포트**: 5432 (기본값)
   - **슈퍼유저 비밀번호**: 안전한 비밀번호 설정 (기억해두세요!)
   - **로케일**: Korean, Korea 또는 Default

### 방법 2: winget 설치
```powershell
winget install PostgreSQL.PostgreSQL
```

---

## 2. 데이터베이스 생성

### pgAdmin 사용 (GUI)
1. 시작 메뉴 → pgAdmin 4 실행
2. 왼쪽 트리에서 "Servers" → "PostgreSQL 16" 클릭
3. 비밀번호 입력
4. "Databases" 우클릭 → "Create" → "Database"
5. 이름: `studysnap` 입력 → Save

### 명령줄 사용 (CMD/PowerShell)
```powershell
# PostgreSQL bin 폴더로 이동 (설치 경로에 따라 다름)
cd "C:\Program Files\PostgreSQL\16\bin"

# psql 접속
psql -U postgres

# 데이터베이스 생성
CREATE DATABASE studysnap;

# 전용 사용자 생성 (선택사항)
CREATE USER studysnap WITH PASSWORD 'studysnap';
GRANT ALL PRIVILEGES ON DATABASE studysnap TO studysnap;

# 접속 종료
\q
```

---

## 3. 스키마 적용

### 방법 1: pgAdmin 사용
1. pgAdmin에서 `studysnap` 데이터베이스 선택
2. "Tools" → "Query Tool" 클릭
3. `database/schema.sql` 파일 내용 복사하여 붙여넣기
4. F5 또는 ▶️ 버튼으로 실행

### 방법 2: 명령줄 사용
```powershell
cd "C:\Program Files\PostgreSQL\16\bin"
psql -U postgres -d studysnap -f "c:\StudySnap-Backend\database\schema.sql"
```

---

## 4. Python 환경 설정

### 필요 패키지 설치
```powershell
pip install psycopg2-binary sqlalchemy
```

### 환경 변수 설정
`.env` 파일 생성:
```
DATABASE_URL=postgresql://studysnap:studysnap@localhost:5432/studysnap
```

---

## 5. 연결 테스트

### Python 스크립트로 테스트
```python
# test_db_connection.py
from database.models import get_database

db = get_database("postgresql://studysnap:studysnap@localhost:5432/studysnap")

# 테이블 생성 (이미 schema.sql 실행했다면 불필요)
# db.create_tables()

# 기본 데이터 초기화
db.init_default_data()

# 세션으로 쿼리 테스트
session = db.get_session()
from database.models import Service
services = session.query(Service).all()
for s in services:
    print(f"서비스: {s.name} ({s.code})")
session.close()
```

실행:
```powershell
cd c:\StudySnap-Backend
python test_db_connection.py
```

---

## 6. 연결 문자열 형식

```
postgresql://[사용자명]:[비밀번호]@[호스트]:[포트]/[데이터베이스명]
```

### 예시
- 로컬 기본: `postgresql://postgres:비밀번호@localhost:5432/studysnap`
- 전용 사용자: `postgresql://studysnap:studysnap@localhost:5432/studysnap`

---

## 7. 자주 사용하는 psql 명령어

```sql
-- 데이터베이스 목록
\l

-- 테이블 목록
\dt

-- 테이블 구조 보기
\d 테이블명

-- 현재 연결 정보
\conninfo

-- 종료
\q
```

---

## 8. 문제 해결

### PostgreSQL 서비스 시작/중지
```powershell
# 서비스 시작
net start postgresql-x64-16

# 서비스 중지
net stop postgresql-x64-16

# 서비스 상태 확인
sc query postgresql-x64-16
```

### 연결 오류 시
1. PostgreSQL 서비스가 실행 중인지 확인
2. 방화벽에서 5432 포트 허용 확인
3. pg_hba.conf 파일에서 연결 허용 설정 확인

---

## 9. 데이터베이스 구조 요약

| 테이블 | 설명 |
|--------|------|
| services | 서비스 목록 (StudySnap, Lectures 등) |
| users | 사용자 계정 |
| user_service_access | 사용자별 서비스 접근 권한 |
| document_types | 문서 타입 (선거공보물, 뉴스레터 등) |
| documents | 업로드된 문서 |
| document_blocks | 문서 내 블록 (제목, 본문, 이미지 등) |
| ai_learning_records | AI 학습 기록 |
| ai_patterns | AI 패턴 데이터 |
| api_keys | API 키 관리 |
| audit_logs | 감사 로그 |
| system_settings | 시스템 설정 |

---

*작성일: 2025-12-04*
