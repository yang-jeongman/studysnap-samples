# StudySnap Railway Backend

FastAPI 기반 PDF to HTML 변환 백엔드 API

## 프로젝트 구조

```
railway-backend/
├── app/
│   ├── api/              # API 엔드포인트
│   │   ├── conversion.py # PDF 변환 API
│   │   └── health.py     # 헬스체크 API
│   ├── core/             # 핵심 설정
│   │   ├── config.py     # 환경 변수 설정
│   │   └── database.py   # DB 연결 설정
│   ├── models/           # 데이터베이스 모델
│   │   ├── user.py       # 사용자 모델
│   │   └── conversion.py # 변환 기록 모델
│   ├── services/         # 비즈니스 로직
│   │   ├── pdf_converter.py  # PDF 변환 서비스
│   │   └── email_service.py  # 이메일 발송 서비스
│   └── main.py           # FastAPI 메인 앱
├── requirements.txt      # Python 의존성
├── railway.json          # Railway 배포 설정
├── Procfile              # 실행 명령
└── .env.example          # 환경 변수 예시
```

## 주요 기능

### 1. PDF 변환 API
- **엔드포인트**: `POST /api/convert`
- **기능**: PDF 업로드 → Claude API로 변환 → GitHub 커밋 → 이메일 발송
- **지원 카테고리**:
  - `election_democratic` - 더불어민주당 선거공보물
  - `election_ppp` - 국민의힘 선거공보물
  - `election_progressive` - 진보당 선거공보물
  - `church` - 교회 주보
  - `newsletter` - 뉴스레터
  - `lecture` - 강의자료

### 2. 상태 확인 API
- **엔드포인트**: `GET /api/convert/{conversion_id}/status`
- **기능**: 변환 진행 상태 및 결과 확인

### 3. 헬스체크 API
- **엔드포인트**: `GET /health`
- **기능**: 서버 상태 확인
- **DB 체크**: `GET /health/db`

## 환경 변수 설정

`.env.example`을 `.env`로 복사하고 다음 값들을 설정하세요:

```bash
# API Keys
ANTHROPIC_API_KEY=sk-ant-xxx...

# Database (Railway에서 자동 제공)
DATABASE_URL=postgresql://user:password@host:port/database

# GitHub
GITHUB_TOKEN=ghp_xxx...
GITHUB_REPO_OWNER=yang-jeongman
GITHUB_REPO_NAME=StudySnap-Backend

# Email (Gmail 사용 시)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your_email@gmail.com
SMTP_PASSWORD=your_app_password
SMTP_FROM=support@studysnap.kr

# Security
SECRET_KEY=openssl_rand_hex_32로_생성
ALGORITHM=HS256

# CORS
ALLOWED_ORIGINS=https://studysnap-pdf.netlify.app,http://localhost:3000
```

## 로컬 개발

### 1. Python 환경 설정

```bash
# 가상환경 생성
python -m venv venv

# 가상환경 활성화 (Windows)
venv\Scripts\activate

# 가상환경 활성화 (Mac/Linux)
source venv/bin/activate

# 의존성 설치
pip install -r requirements.txt
```

### 2. 환경 변수 설정

```bash
# .env 파일 생성
cp .env.example .env

# .env 파일 수정 (필수 값 입력)
```

### 3. 데이터베이스 초기화

```bash
# PostgreSQL 실행 확인
# Railway 사용 시 자동 생성됨

# 테이블 자동 생성 (앱 실행 시)
```

### 4. 서버 실행

```bash
# 개발 서버 실행 (hot reload)
uvicorn app.main:app --reload --port 8000

# 또는
python -m app.main
```

서버가 http://localhost:8000 에서 실행됩니다.

### 5. API 문서 확인

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Railway 배포

### 1. Railway CLI 설치

```bash
npm install -g @railway/cli
```

### 2. Railway 로그인

```bash
railway login
```

### 3. 프로젝트 초기화

```bash
# railway-backend 폴더에서
cd railway-backend
railway init
```

### 4. PostgreSQL 추가

Railway 대시보드에서:
1. **New** → **Database** → **PostgreSQL** 선택
2. 자동으로 `DATABASE_URL` 환경 변수 생성됨

### 5. 환경 변수 설정

Railway 대시보드에서 **Variables** 탭:

```
ANTHROPIC_API_KEY=sk-ant-xxx...
GITHUB_TOKEN=ghp_xxx...
GITHUB_REPO_OWNER=yang-jeongman
GITHUB_REPO_NAME=StudySnap-Backend
SMTP_USER=your_email@gmail.com
SMTP_PASSWORD=your_app_password
SECRET_KEY=your_secret_key
ALLOWED_ORIGINS=https://studysnap-pdf.netlify.app
```

### 6. 배포

```bash
# 자동 배포 (GitHub 연동)
git push origin main

# 또는 수동 배포
railway up
```

### 7. 도메인 확인

Railway가 자동으로 생성한 도메인:
- `https://your-app.up.railway.app`

커스텀 도메인 설정:
- Railway 대시보드 → **Settings** → **Domains**

## API 사용 예시

### PDF 변환 요청

```bash
curl -X POST https://your-app.up.railway.app/api/convert \
  -F "pdf=@/path/to/file.pdf" \
  -F "email=user@example.com" \
  -F "category=election_democratic" \
  -F "candidate_name=홍길동" \
  -F "party_name=더불어민주당" \
  -F "district=서울 강남구"
```

**응답:**
```json
{
  "conversion_id": 123,
  "status": "pending",
  "message": "PDF conversion started. You will receive an email when complete.",
  "html_url": null
}
```

### 변환 상태 확인

```bash
curl https://your-app.up.railway.app/api/convert/123/status
```

**응답:**
```json
{
  "conversion_id": 123,
  "status": "completed",
  "html_url": "https://studysnap-pdf.netlify.app/Election/Minjoo/홍길동/홍길동.html",
  "error_message": null,
  "progress_percent": 100
}
```

## 데이터베이스 스키마

### Users 테이블
```sql
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    hashed_password VARCHAR(255),
    full_name VARCHAR(255),
    is_active BOOLEAN DEFAULT TRUE,
    is_verified BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP
);
```

### Conversions 테이블
```sql
CREATE TABLE conversions (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    pdf_filename VARCHAR(255) NOT NULL,
    pdf_size_mb FLOAT,
    page_count INTEGER,
    category VARCHAR(50) NOT NULL,
    template_id VARCHAR(100),
    status VARCHAR(20) DEFAULT 'pending',
    html_url TEXT,
    github_commit_sha VARCHAR(40),
    output_folder_path VARCHAR(500),
    candidate_name VARCHAR(255),
    party_name VARCHAR(100),
    district VARCHAR(255),
    processing_time_seconds FLOAT,
    error_message TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    started_at TIMESTAMP,
    completed_at TIMESTAMP
);
```

## 모니터링 및 로깅

### Railway 로그 확인

```bash
railway logs
```

### 헬스체크

```bash
# 기본 헬스체크
curl https://your-app.up.railway.app/health

# DB 연결 포함
curl https://your-app.up.railway.app/health/db
```

## 트러블슈팅

### 1. Railway 배포 실패

**증상**: 빌드 중 에러 발생

**해결**:
```bash
# 로그 확인
railway logs

# requirements.txt 검증
pip install -r requirements.txt --dry-run
```

### 2. DB 연결 실패

**증상**: `DATABASE_URL` 연결 오류

**해결**:
- Railway 대시보드에서 PostgreSQL 플러그인 확인
- `DATABASE_URL` 환경 변수 자동 설정 확인

### 3. Claude API 에러

**증상**: PDF 변환 중 API 에러

**해결**:
- `ANTHROPIC_API_KEY` 유효성 확인
- API 사용 한도 확인
- https://console.anthropic.com

### 4. GitHub 커밋 실패

**증상**: GitHub에 파일 업로드 실패

**해결**:
- `GITHUB_TOKEN` 권한 확인 (repo 권한 필요)
- GitHub Personal Access Token 재생성

## 성능 최적화

### 1. 동시 요청 처리

Railway는 자동으로 스케일링하지만, 비용 절감을 위해:

```python
# app/main.py
app = FastAPI(
    # ... 기존 설정
)

# Worker 프로세스 수 조정 (railway.json)
{
  "deploy": {
    "startCommand": "uvicorn app.main:app --host 0.0.0.0 --port $PORT --workers 2"
  }
}
```

### 2. 데이터베이스 연결 풀

```python
# app/core/database.py
engine = create_engine(
    settings.DATABASE_URL,
    pool_size=10,        # 최대 10개 연결
    max_overflow=20,     # 추가 20개 허용
    pool_pre_ping=True   # 연결 유효성 체크
)
```

## 비용 관리

### Railway 무료 크레딧
- 월 $5 무료
- 약 500시간 실행 가능

### 예상 비용 (소규모)
- Backend: $5~$10/월
- PostgreSQL: 무료 (1GB)
- **총: $5~$10/월**

## 다음 단계

- [ ] 사용자 인증 시스템 (JWT)
- [ ] 변환 대기열 (Celery + Redis)
- [ ] 관리자 대시보드
- [ ] 변환 진행 상황 실시간 업데이트 (WebSocket)
- [ ] 다국어 지원

## 라이선스

MIT License

## 문의

- 이메일: support@studysnap.kr
- GitHub: https://github.com/yang-jeongman/StudySnap-Backend

---

*Last Updated: 2025-12-23*
*Version: 1.0.0*
