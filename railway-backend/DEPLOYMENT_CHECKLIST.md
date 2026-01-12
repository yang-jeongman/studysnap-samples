# Railway 배포 체크리스트

## 🚀 Railway 배포를 위한 필수 작업

---

## 1단계: 준비물 확인 ✅

### 필요한 계정/토큰

#### ✅ Railway 계정
- [ ] Railway 계정 생성: https://railway.app
- [ ] GitHub 계정 연동 (추천)
- [ ] 신용카드 등록 (무료 $5 크레딧 사용, 초과 시 과금)

#### ✅ Anthropic API Key
- [ ] Anthropic 계정: https://console.anthropic.com
- [ ] API Key 발급: https://console.anthropic.com/settings/keys
- 📋 **복사해두기**: `sk-ant-api03-...` (약 100자)

#### ✅ GitHub Personal Access Token
- [ ] GitHub 설정: https://github.com/settings/tokens
- [ ] **New token (classic)** 클릭
- [ ] 권한 선택: ✅ `repo` (전체 선택)
- [ ] 만료 기간: `90 days` 또는 `No expiration`
- [ ] **Generate token** 클릭
- 📋 **즉시 복사**: `ghp_...` (한 번만 표시됨!)

#### ✅ Gmail App Password (이메일 발송용)
- [ ] Gmail 2단계 인증 활성화 필수
- [ ] https://myaccount.google.com/apppasswords 접속
- [ ] 앱 선택: **Mail**
- [ ] 기기 선택: **Other (Custom name)** → "StudySnap"
- [ ] **생성** 클릭
- 📋 **복사**: `xxxx xxxx xxxx xxxx` (16자리, 공백 제거)

#### ✅ Secret Key 생성
- [ ] Windows PowerShell에서 실행:
```powershell
-join ((48..57) + (65..90) + (97..122) | Get-Random -Count 32 | % {[char]$_})
```
- [ ] 또는 Git Bash에서:
```bash
openssl rand -hex 32
```
- 📋 **복사**: 64자리 랜덤 문자열

---

## 2단계: Railway 프로젝트 생성 🚂

### 옵션 A: Railway CLI 사용 (권장)

#### 1. Railway CLI 설치
```bash
# Node.js가 설치되어 있어야 함
npm install -g @railway/cli
```

#### 2. Railway 로그인
```bash
railway login
```
- 브라우저가 열리고 Railway 로그인 화면 표시
- **Authorize** 클릭

#### 3. 프로젝트 초기화
```bash
cd C:\StudySnap-Backend\railway-backend
railway init
```
- 프로젝트 이름 입력: `studysnap-backend`
- 또는 기존 프로젝트 선택

#### 4. GitHub 저장소 연동 (선택)
```bash
railway link
```

### 옵션 B: Railway 웹 대시보드 사용

#### 1. Railway 대시보드 접속
- https://railway.app/dashboard

#### 2. 새 프로젝트 생성
- **New Project** 클릭
- **Deploy from GitHub repo** 선택
- Repository: `yang-jeongman/StudySnap-Backend` 선택
- Root Directory: `/railway-backend` 설정 ⚠️ 중요!

---

## 3단계: PostgreSQL 데이터베이스 추가 🗄️

### Railway 대시보드에서:

1. 프로젝트 열기
2. **New** 버튼 클릭
3. **Database** 선택
4. **Add PostgreSQL** 클릭
5. 자동으로 `DATABASE_URL` 환경 변수 생성됨 ✅

**확인 방법:**
- **Variables** 탭에서 `DATABASE_URL` 확인
- 형식: `postgresql://postgres:password@host:5432/railway`

---

## 4단계: 환경 변수 설정 🔐

### Railway 대시보드 → Variables 탭

다음 환경 변수들을 **하나씩** 추가하세요:

#### 📝 입력해야 할 환경 변수

| 변수명 | 값 | 설명 | 예시 |
|--------|-----|------|------|
| **ANTHROPIC_API_KEY** | `sk-ant-api03-...` | Anthropic API 키 | `sk-ant-api03-xxxxx` |
| **GITHUB_TOKEN** | `ghp_...` | GitHub Personal Access Token | `ghp_xxxxxxxxxxxxx` |
| **GITHUB_REPO_OWNER** | `yang-jeongman` | GitHub 사용자명 | `yang-jeongman` |
| **GITHUB_REPO_NAME** | `StudySnap-Backend` | 저장소 이름 | `StudySnap-Backend` |
| **SMTP_HOST** | `smtp.gmail.com` | 이메일 서버 | `smtp.gmail.com` |
| **SMTP_PORT** | `587` | 이메일 포트 | `587` |
| **SMTP_USER** | 이메일 주소 | Gmail 주소 | `your@gmail.com` |
| **SMTP_PASSWORD** | `xxxxxxxxxxxxxx` | Gmail App Password (공백 제거) | `abcdwxyz12345678` |
| **SMTP_FROM** | `support@studysnap.kr` | 발신자 이메일 | `support@studysnap.kr` |
| **SECRET_KEY** | 64자리 랜덤 문자열 | JWT 시크릿 키 | `abc123...` |
| **ALGORITHM** | `HS256` | JWT 알고리즘 | `HS256` |
| **ALLOWED_ORIGINS** | 도메인 | CORS 허용 도메인 (쉼표 구분) | `https://studysnap-pdf.netlify.app` |
| **DEBUG** | `False` | 디버그 모드 | `False` |

### ⚠️ 자동 생성되는 변수 (건드리지 마세요!)

- `DATABASE_URL` - PostgreSQL 연결 URL (자동)
- `PORT` - Railway가 자동 할당
- `RAILWAY_ENVIRONMENT` - 환경 정보 (자동)

### 📋 복사-붙여넣기용 템플릿

```
ANTHROPIC_API_KEY=여기에_입력
GITHUB_TOKEN=여기에_입력
GITHUB_REPO_OWNER=yang-jeongman
GITHUB_REPO_NAME=StudySnap-Backend
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=여기에_Gmail_주소_입력
SMTP_PASSWORD=여기에_App_Password_입력
SMTP_FROM=support@studysnap.kr
SECRET_KEY=여기에_64자리_랜덤_문자열_입력
ALGORITHM=HS256
ALLOWED_ORIGINS=https://studysnap-pdf.netlify.app
DEBUG=False
```

---

## 5단계: 배포 실행 🚀

### 옵션 A: GitHub 자동 배포 (권장)

1. Railway 대시보드 → **Settings** 탭
2. **Deploy Trigger** 확인
3. **Branch**: `main` 선택
4. **Root Directory**: `/railway-backend` 입력 ⚠️
5. **Save** 클릭

이제 GitHub에 push할 때마다 자동 배포됨! ✅

### 옵션 B: Railway CLI로 수동 배포

```bash
cd C:\StudySnap-Backend\railway-backend
railway up
```

### 배포 진행 상황 확인

Railway 대시보드에서:
- **Deployments** 탭 → 실시간 로그 확인
- ✅ 성공: "Build successful" 메시지
- ❌ 실패: 에러 로그 확인

---

## 6단계: 배포 확인 ✅

### 1. 도메인 확인

Railway 대시보드 → **Settings** 탭:
- 자동 생성 도메인: `https://studysnap-backend-production-xxxx.up.railway.app`
- 📋 **복사해두기**

### 2. 헬스체크

브라우저에서 접속:
```
https://your-app.up.railway.app/health
```

**예상 응답:**
```json
{
  "status": "healthy",
  "app": "StudySnap API",
  "version": "1.0.0",
  "timestamp": 1703345678.123
}
```

### 3. DB 연결 확인

```
https://your-app.up.railway.app/health/db
```

**예상 응답:**
```json
{
  "status": "healthy",
  "database": "connected"
}
```

### 4. API 문서 확인 (DEBUG=True인 경우만)

```
https://your-app.up.railway.app/docs
```

---

## 7단계: 테스트 🧪

### API 테스트 (Postman 또는 curl)

```bash
# 1. 헬스체크
curl https://your-app.up.railway.app/health

# 2. PDF 변환 테스트
curl -X POST https://your-app.up.railway.app/api/convert \
  -F "pdf=@test.pdf" \
  -F "email=test@example.com" \
  -F "category=election_democratic" \
  -F "candidate_name=테스트"

# 3. 변환 상태 확인
curl https://your-app.up.railway.app/api/convert/1/status
```

---

## 문제 해결 🔧

### 배포 실패 시

#### 1. 로그 확인
```bash
railway logs
```

또는 Railway 대시보드 → **Deployments** 탭

#### 2. 흔한 문제

**에러: `requirements.txt not found`**
- 해결: Root Directory를 `/railway-backend`로 설정

**에러: `DATABASE_URL not set`**
- 해결: PostgreSQL 플러그인 추가 확인

**에러: `ModuleNotFoundError: No module named 'anthropic'`**
- 해결: requirements.txt 파일 확인, 재배포

**에러: `401 Unauthorized` (Anthropic)**
- 해결: ANTHROPIC_API_KEY 확인
- https://console.anthropic.com/settings/keys

**에러: `403 Forbidden` (GitHub)**
- 해결: GITHUB_TOKEN 권한 확인 (repo 권한 필요)

**에러: `SMTP Authentication failed`**
- 해결:
  - Gmail 2단계 인증 활성화 확인
  - App Password 재생성
  - SMTP_PASSWORD에 공백 없는지 확인

---

## 커스텀 도메인 설정 (선택) 🌐

### Railway에서 커스텀 도메인 연결

1. Railway 대시보드 → **Settings** → **Domains**
2. **Add Domain** 클릭
3. 도메인 입력: `api.studysnap.kr`
4. DNS 레코드 추가 (도메인 제공업체):
   - Type: `CNAME`
   - Name: `api`
   - Value: `your-app.up.railway.app`
5. 저장 및 확인 대기 (최대 48시간)

---

## 모니터링 및 유지보수 📊

### 1. 로그 모니터링

```bash
# 실시간 로그
railway logs --follow

# 최근 100줄
railway logs --tail 100
```

### 2. 리소스 사용량 확인

Railway 대시보드:
- **Metrics** 탭
- CPU, Memory, Network 사용량 확인

### 3. 비용 확인

Railway 대시보드:
- **Usage** 탭
- 현재 크레딧 사용량 확인
- 월 $5 무료 크레딧

---

## 체크리스트 요약 ✅

### 배포 전
- [ ] Railway 계정 생성
- [ ] Anthropic API Key 발급
- [ ] GitHub Token 생성
- [ ] Gmail App Password 생성
- [ ] Secret Key 생성

### Railway 설정
- [ ] 프로젝트 생성
- [ ] PostgreSQL 추가
- [ ] 환경 변수 11개 입력
- [ ] Root Directory 설정 (`/railway-backend`)
- [ ] GitHub 연동 (자동 배포)

### 배포 확인
- [ ] 헬스체크 성공 (`/health`)
- [ ] DB 연결 성공 (`/health/db`)
- [ ] 도메인 복사
- [ ] API 테스트

### 다음 단계
- [ ] Netlify 프론트엔드에 Railway URL 연동
- [ ] 실제 PDF 변환 테스트
- [ ] 이메일 수신 확인

---

## 🆘 도움이 필요하면

1. **Railway 로그 확인**
   ```bash
   railway logs
   ```

2. **Railway 문서**
   - https://docs.railway.app

3. **StudySnap 이슈**
   - GitHub Issues 생성

---

**배포 성공을 기원합니다!** 🎉

준비되면 "배포 시작!" 이라고 말씀해주세요!
