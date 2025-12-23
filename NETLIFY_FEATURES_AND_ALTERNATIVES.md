# Netlify 기능 확인 및 대안 제시

## Netlify의 특성

### ✅ 지원하는 기능
1. **정적 사이트 호스팅** - HTML, CSS, JS 파일 제공
2. **폼 제출** - Netlify Forms (월 100개 무료)
3. **Identity (인증)** - Netlify Identity (월 1,000명 무료)
4. **Functions** - AWS Lambda 기반 서버리스 함수
5. **자동 배포** - GitHub 연동 시 자동 빌드/배포

### ❌ 지원하지 않는 기능
1. **데이터베이스** - MySQL, PostgreSQL 등 직접 호스팅 불가
2. **세션 관리** - 서버 사이드 세션 저장소 없음
3. **파일 업로드 저장** - 업로드된 파일을 Netlify에 직접 저장 불가
4. **백엔드 서버** - Express, Django 등 풀스택 서버 호스팅 불가

---

## 현재 구현: 이메일 기반 간단한 접근 방식

현재 홈페이지는 **이메일 문의 방식**으로 구현되어 있습니다.

### 장점
- ✅ 즉시 사용 가능 (추가 개발 불필요)
- ✅ 비용 없음
- ✅ 관리 간편 (이메일로 모든 요청 수신)
- ✅ 개인정보 관리 부담 없음

### 단점
- ❌ 사용자가 직접 PDF 업로드 불가
- ❌ 실시간 변환 불가
- ❌ 자동화 수준 낮음

---

## 대안 1: Netlify Forms + Functions (추천)

### 구조
```
사용자 → Netlify Form → Netlify Function → 변환 처리 → 이메일 발송
```

### 구현 방법

1. **폼 제출 페이지 (HTML)**
```html
<form name="pdf-conversion" method="POST" data-netlify="true" enctype="multipart/form-data">
  <input type="hidden" name="form-name" value="pdf-conversion">
  <input type="email" name="email" required placeholder="이메일">
  <select name="category" required>
    <option value="election-democratic">선거공보물 - 민주당</option>
    <option value="election-ppp">선거공보물 - 국민의힘</option>
    <option value="church">교회 주보</option>
  </select>
  <input type="file" name="pdf" accept=".pdf" required>
  <button type="submit">변환 요청</button>
</form>
```

2. **Netlify Function (JavaScript)**
```javascript
// netlify/functions/process-pdf.js
exports.handler = async (event) => {
  // 폼 데이터 파싱
  const { email, category, pdf } = parseFormData(event.body);

  // PDF 처리 (Claude API 호출)
  const html = await convertPdfToHtml(pdf, category);

  // 결과를 GitHub에 커밋
  await commitToGitHub(html, category);

  // 사용자에게 이메일 발송
  await sendEmail(email, resultUrl);

  return {
    statusCode: 200,
    body: JSON.stringify({ message: '변환 완료!' })
  };
};
```

### 장점
- ✅ 사용자가 직접 PDF 업로드 가능
- ✅ 자동 변환 처리
- ✅ Netlify 내에서 완결
- ✅ 무료 티어로 충분 (월 100건)

### 단점
- ❌ 개발 필요 (Functions 작성)
- ❌ Claude API 키 관리 필요
- ❌ 대용량 PDF 처리 제한 (Lambda 6MB 제한)

### 비용
- Netlify Forms: 월 100개 무료
- Netlify Functions: 월 125,000 요청 무료
- 총 비용: **$0**

---

## 대안 2: Netlify Identity + 외부 백엔드

### 구조
```
사용자 → Netlify 홈페이지 → Netlify Identity (인증)
                           ↓
                    외부 백엔드 서버 (Python Flask/FastAPI)
                           ↓
                    PDF 변환 → GitHub 커밋
```

### 필요한 구성 요소

1. **Netlify Identity** (회원 인증)
   - 가입, 로그인, 비밀번호 재설정 자동 처리
   - JWT 토큰 기반 인증

2. **외부 백엔드 서버**
   - 옵션 A: **Heroku** (무료 티어 중단)
   - 옵션 B: **Railway** (월 $5 무료 크레딧)
   - 옵션 C: **Render** (무료 티어 있음)
   - 옵션 D: **Python Anywhere** (무료 티어 있음)

3. **데이터베이스**
   - 옵션 A: **Supabase** (PostgreSQL, 무료 500MB)
   - 옵션 B: **Firebase** (NoSQL, 무료 1GB)
   - 옵션 C: **MongoDB Atlas** (무료 512MB)

### 구현 예시 (Netlify Identity)

**HTML (로그인 버튼)**
```html
<script src="https://identity.netlify.com/v1/netlify-identity-widget.js"></script>
<button onclick="netlifyIdentity.open()">로그인</button>

<script>
  netlifyIdentity.on('login', user => {
    const token = user.token.access_token;
    // 외부 백엔드 API 호출 시 토큰 사용
  });
</script>
```

**Python 백엔드 (Flask)**
```python
from flask import Flask, request
import jwt

app = Flask(__name__)

@app.route('/api/convert', methods=['POST'])
def convert_pdf():
    # Netlify Identity JWT 토큰 검증
    token = request.headers.get('Authorization')
    user = verify_netlify_token(token)

    # PDF 업로드 처리
    pdf_file = request.files['pdf']
    category = request.form['category']

    # 변환 실행
    html = convert_to_html(pdf_file, category)

    # 결과 저장
    save_to_github(html, user.email)

    return {'url': result_url}
```

### 장점
- ✅ 완전한 회원 시스템
- ✅ 대용량 PDF 처리 가능
- ✅ 복잡한 로직 처리 가능
- ✅ 데이터베이스 사용 가능

### 단점
- ❌ 개발 복잡도 높음
- ❌ 외부 서버 관리 필요
- ❌ 비용 발생 가능

### 비용
- Netlify Identity: 월 1,000명 무료
- 외부 서버: $0 ~ $5/월
- 데이터베이스: 무료 티어 사용 가능
- 총 비용: **$0 ~ $5/월**

---

## 대안 3: Google Forms + Google Apps Script (가장 간단)

### 구조
```
사용자 → Google Forms → Google Drive (PDF 저장)
                      ↓
              Google Apps Script (자동 처리)
                      ↓
              이메일로 결과 전송
```

### 구현 방법

1. **Google Forms 생성**
   - 이메일 입력 필드
   - 카테고리 선택 (드롭다운)
   - 파일 업로드 필드 (PDF)

2. **Google Apps Script**
```javascript
function onFormSubmit(e) {
  const email = e.values[1];  // 이메일
  const category = e.values[2];  // 카테고리
  const pdfUrl = e.values[3];  // PDF URL

  // PDF 다운로드
  const pdf = DriveApp.getFileById(extractFileId(pdfUrl));

  // 외부 API 호출 (Claude API)
  const html = callConversionAPI(pdf, category);

  // GitHub에 커밋
  commitToGitHub(html);

  // 이메일 발송
  MailApp.sendEmail(email, '변환 완료', resultUrl);
}
```

### 장점
- ✅ 매우 간단한 설정
- ✅ 완전 무료
- ✅ Google 계정으로 자동 인증
- ✅ 파일 저장 자동 (Google Drive)

### 단점
- ❌ UI가 Google Forms (커스터마이징 제한)
- ❌ Netlify와 별도 시스템
- ❌ Apps Script 6분 실행 제한

### 비용
- 총 비용: **$0**

---

## 추천 방안

### 현재 단계 (MVP): 이메일 문의 방식 (현재 구현)
- **이유**: 즉시 사용 가능, 개발 불필요, 무료
- **적합**: 초기 테스트, 소규모 사용자

### 단기 개선 (1-2주): Netlify Forms + Functions
- **이유**: 자동화, 사용자 직접 업로드, Netlify 내 완결
- **적합**: 중소 규모 사용자 (월 100건 이하)

### 중기 개선 (1-2개월): Google Forms + Apps Script
- **이유**: 완전 무료, 간단 구현, 파일 관리 자동
- **적합**: 예산 제약, 빠른 구현 필요

### 장기 개선 (3개월+): Netlify Identity + 외부 백엔드
- **이유**: 완전한 서비스, 확장 가능, 프로페셔널
- **적합**: 대규모 사용자, 상용 서비스

---

## 현재 홈페이지 상태

✅ **이미 구현된 기능**
- 공개 랜딩 페이지
- 카테고리별 문의 이메일 링크
- SEO 최적화 (meta tags, sitemap)
- 모바일 최적화 반응형 디자인

📧 **현재 동작 방식**
1. 사용자가 카테고리 선택
2. 이메일 클라이언트 자동 실행
3. PDF 첨부하여 문의 메일 발송
4. 관리자가 수동으로 변환 처리
5. 변환 완료 후 링크 회신

---

## 결론

**즉시 사용**: 현재 이메일 방식으로 서비스 시작
**1주일 내**: Netlify Forms로 업그레이드 (추천)
**필요시**: Google Forms로 완전 자동화
**장기적**: 외부 백엔드 + 회원 시스템 도입

**현재 홈페이지는 배포 가능한 상태입니다!**

---

*작성일: 2025-12-23*
*버전: 1.0.0*
