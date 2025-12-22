# -*- coding: utf-8 -*-
"""StudySnap Demo Homepage Generator"""

html_content = """<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>StudySnap - AI 기반 PDF 모바일 변환 솔루션</title>
    <meta name="description" content="PDF를 모바일에 최적화된 HTML로 자동 변환. 대학강의, 교회주보, 상품카탈로그, 선거공보, 소식지, 어학학습 등">
    <meta name="theme-color" content="#E11D48">
    <meta name="apple-mobile-web-app-capable" content="yes">
    <meta property="og:title" content="StudySnap - PDF to Mobile HTML">
    <meta property="og:description" content="PDF 문서를 모바일 최적화 HTML로 자동 변환">
    <link href="https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@300;400;500;700;900&display=swap" rel="stylesheet">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: 'Noto Sans KR', sans-serif; background: linear-gradient(135deg, #1a1a2e, #16213e, #0f3460); min-height: 100vh; color: #fff; }
        .nav { position: fixed; top: 0; left: 0; right: 0; padding: 15px 30px; display: flex; justify-content: space-between; align-items: center; z-index: 1000; background: rgba(26, 26, 46, 0.95); backdrop-filter: blur(10px); border-bottom: 1px solid rgba(255,255,255,0.1); }
        .logo { font-size: 1.5em; font-weight: 700; background: linear-gradient(135deg, #E11D48, #F97316); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
        .nav-links { display: flex; gap: 25px; align-items: center; }
        .nav-links a { color: rgba(255,255,255,0.8); text-decoration: none; font-weight: 500; }
        .btn-beta { background: linear-gradient(135deg, #E11D48, #BE123C); color: white !important; padding: 10px 20px; border-radius: 25px; font-weight: 600; }

        .hero { min-height: 100vh; display: flex; align-items: center; justify-content: center; padding: 100px 20px; text-align: center; }
        .hero-content { max-width: 900px; }
        .hero-badge { display: inline-block; background: rgba(225, 29, 72, 0.2); border: 1px solid rgba(225, 29, 72, 0.3); color: #F97316; padding: 8px 20px; border-radius: 30px; font-size: 0.9em; font-weight: 600; margin-bottom: 25px; }
        .hero h1 { font-size: clamp(2.2em, 7vw, 4em); font-weight: 900; margin-bottom: 20px; line-height: 1.2; }
        .hero h1 span { background: linear-gradient(135deg, #E11D48, #F97316); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
        .hero p { font-size: clamp(1em, 2.5vw, 1.3em); color: rgba(255,255,255,0.7); margin-bottom: 35px; line-height: 1.7; }
        .cta-buttons { display: flex; gap: 15px; justify-content: center; flex-wrap: wrap; }
        .btn { padding: 16px 35px; font-size: 1em; font-weight: 600; border-radius: 50px; text-decoration: none; display: inline-flex; align-items: center; gap: 8px; border: none; cursor: pointer; transition: all 0.3s; }
        .btn-primary { background: linear-gradient(135deg, #E11D48, #BE123C); color: white; box-shadow: 0 8px 25px rgba(225, 29, 72, 0.4); }
        .btn-primary:hover { transform: translateY(-3px); box-shadow: 0 12px 35px rgba(225, 29, 72, 0.5); }
        .btn-secondary { background: rgba(255,255,255,0.1); color: white; border: 2px solid rgba(255,255,255,0.2); }

        /* Demo Upload Section */
        .demo-section { padding: 100px 20px; background: rgba(0,0,0,0.3); }
        .demo-container { max-width: 900px; margin: 0 auto; }
        .section-title { text-align: center; font-size: clamp(1.8em, 4vw, 2.8em); font-weight: 700; margin-bottom: 20px; }
        .section-title span { background: linear-gradient(135deg, #E11D48, #F97316); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
        .section-subtitle { text-align: center; color: rgba(255,255,255,0.6); font-size: 1.1em; margin-bottom: 40px; }

        .upload-area { background: rgba(255,255,255,0.05); border: 3px dashed rgba(255,255,255,0.2); border-radius: 20px; padding: 60px 40px; text-align: center; transition: all 0.3s; cursor: pointer; }
        .upload-area:hover, .upload-area.dragover { border-color: #E11D48; background: rgba(225, 29, 72, 0.1); }
        .upload-icon { font-size: 4em; margin-bottom: 20px; }
        .upload-area h3 { font-size: 1.5em; margin-bottom: 15px; }
        .upload-area p { color: rgba(255,255,255,0.6); margin-bottom: 25px; }
        .upload-area input[type="file"] { display: none; }

        .category-select { display: flex; flex-wrap: wrap; gap: 10px; justify-content: center; margin-top: 30px; }
        .category-btn { padding: 12px 24px; background: rgba(255,255,255,0.1); border: 1px solid rgba(255,255,255,0.2); border-radius: 30px; color: white; cursor: pointer; transition: all 0.3s; font-size: 0.95em; }
        .category-btn:hover, .category-btn.active { background: linear-gradient(135deg, #E11D48, #BE123C); border-color: transparent; }
        .category-btn .icon { margin-right: 8px; }

        .convert-btn { margin-top: 30px; padding: 18px 50px; font-size: 1.1em; }
        .convert-btn:disabled { opacity: 0.5; cursor: not-allowed; }

        /* Progress */
        .progress-container { display: none; margin-top: 30px; }
        .progress-bar { height: 8px; background: rgba(255,255,255,0.1); border-radius: 10px; overflow: hidden; }
        .progress-fill { height: 100%; background: linear-gradient(135deg, #E11D48, #F97316); width: 0%; transition: width 0.3s; }
        .progress-text { text-align: center; margin-top: 15px; color: rgba(255,255,255,0.7); }

        /* Result */
        .result-container { display: none; margin-top: 30px; background: rgba(255,255,255,0.05); border-radius: 20px; padding: 30px; }
        .result-preview { background: white; border-radius: 15px; overflow: hidden; margin-bottom: 20px; }
        .result-preview iframe { width: 100%; height: 400px; border: none; }
        .result-actions { display: flex; gap: 15px; justify-content: center; flex-wrap: wrap; }

        /* Use Cases Section */
        .use-cases { padding: 100px 20px; background: rgba(0,0,0,0.2); }
        .use-cases-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 25px; max-width: 1200px; margin: 0 auto; }
        .use-case-card { background: rgba(255,255,255,0.05); border: 1px solid rgba(255,255,255,0.1); border-radius: 20px; padding: 35px; text-align: center; transition: all 0.3s; }
        .use-case-card:hover { transform: translateY(-8px); background: rgba(255,255,255,0.08); border-color: rgba(225, 29, 72, 0.3); }
        .use-case-card.featured { background: linear-gradient(135deg, rgba(225, 29, 72, 0.15), rgba(249, 115, 22, 0.1)); border-color: rgba(225, 29, 72, 0.3); }
        .use-case-icon { font-size: 3em; margin-bottom: 20px; }
        .use-case-card h3 { font-size: 1.3em; margin-bottom: 12px; }
        .use-case-card p { color: rgba(255,255,255,0.6); line-height: 1.6; }
        .badge-new { display: inline-block; background: #E11D48; color: white; font-size: 0.7em; padding: 3px 10px; border-radius: 15px; margin-left: 8px; }

        /* Beta Section */
        .beta-section { padding: 100px 20px; }
        .beta-container { max-width: 800px; margin: 0 auto; text-align: center; }
        .beta-badge { display: inline-block; background: linear-gradient(135deg, #E11D48, #F97316); color: white; padding: 10px 25px; border-radius: 30px; font-weight: 700; margin-bottom: 25px; }
        .beta-container h2 { font-size: 2.5em; margin-bottom: 20px; }
        .beta-container > p { color: rgba(255,255,255,0.7); font-size: 1.1em; margin-bottom: 40px; }
        .beta-benefits { display: grid; grid-template-columns: repeat(3, 1fr); gap: 20px; margin-bottom: 40px; }
        .beta-benefit { background: rgba(255,255,255,0.05); border: 1px solid rgba(255,255,255,0.1); border-radius: 15px; padding: 25px; }
        .beta-benefit .icon { font-size: 2em; margin-bottom: 12px; }
        .beta-benefit h4 { font-size: 1em; margin-bottom: 8px; }
        .beta-benefit p { color: rgba(255,255,255,0.6); font-size: 0.85em; }
        .beta-form { background: rgba(255,255,255,0.05); border: 1px solid rgba(255,255,255,0.1); border-radius: 20px; padding: 30px; max-width: 500px; margin: 0 auto; }
        .form-group { margin-bottom: 20px; text-align: left; }
        .form-group label { display: block; margin-bottom: 8px; font-weight: 500; }
        .form-group input, .form-group select { width: 100%; padding: 14px 18px; border: 1px solid rgba(255,255,255,0.2); border-radius: 10px; background: rgba(255,255,255,0.05); color: white; font-size: 1em; }
        .form-group select option { background: #1a1a2e; color: white; }
        .btn-submit { width: 100%; padding: 16px; background: linear-gradient(135deg, #E11D48, #BE123C); color: white; border: none; border-radius: 10px; font-size: 1.1em; font-weight: 600; cursor: pointer; }

        /* Features Section */
        .features { padding: 100px 20px; background: rgba(0,0,0,0.2); }
        .features-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 25px; max-width: 1200px; margin: 0 auto; }
        .feature-card { background: rgba(255,255,255,0.05); border: 1px solid rgba(255,255,255,0.1); border-radius: 16px; padding: 30px; }
        .feature-icon { font-size: 2.5em; margin-bottom: 15px; }
        .feature-card h3 { font-size: 1.2em; margin-bottom: 10px; }
        .feature-card p { color: rgba(255,255,255,0.6); line-height: 1.6; }

        /* Contact & Footer */
        .contact { padding: 80px 20px; text-align: center; }
        .contact h2 { font-size: 2em; margin-bottom: 30px; }
        .contact-info { display: flex; justify-content: center; gap: 50px; flex-wrap: wrap; }
        .contact-item { text-align: center; }
        .contact-item .icon { font-size: 2em; margin-bottom: 10px; }
        .contact-item a { color: #E11D48; text-decoration: none; }
        .footer { padding: 30px 20px; text-align: center; border-top: 1px solid rgba(255,255,255,0.1); }
        .footer p { color: rgba(255,255,255,0.4); font-size: 0.85em; }

        @media (max-width: 768px) {
            .nav-links { display: none; }
            .cta-buttons, .contact-info, .result-actions { flex-direction: column; align-items: center; }
            .beta-benefits { grid-template-columns: 1fr; }
            .category-select { flex-direction: column; }
        }
    </style>
</head>
<body>
    <nav class="nav">
        <div class="logo">StudySnap</div>
        <div class="nav-links">
            <a href="#demo">변환 체험</a>
            <a href="#use-cases">적용 분야</a>
            <a href="#features">기능</a>
            <a href="#beta" class="btn-beta">베타테스터 신청</a>
        </div>
    </nav>

    <section class="hero">
        <div class="hero-content">
            <div class="hero-badge">🚀 무료 체험 가능</div>
            <h1>PDF를 <span>모바일 최적화</span><br>HTML로 자동 변환</h1>
            <p>AI 기반 레이아웃 분석으로 A4 PDF 문서를 스마트폰에서도<br>편리하게 읽을 수 있는 반응형 웹페이지로 변환합니다.</p>
            <div class="cta-buttons">
                <a href="#demo" class="btn btn-primary">지금 바로 변환해보기</a>
                <a href="#use-cases" class="btn btn-secondary">적용 분야 보기</a>
            </div>
        </div>
    </section>

    <!-- Demo Upload Section -->
    <section class="demo-section" id="demo">
        <div class="demo-container">
            <h2 class="section-title">PDF <span>변환 체험</span></h2>
            <p class="section-subtitle">PDF 파일을 업로드하면 모바일 최적화 HTML로 변환해 드립니다</p>

            <div class="upload-area" id="uploadArea" onclick="document.getElementById('fileInput').click()">
                <div class="upload-icon">📄</div>
                <h3>PDF 파일을 드래그하거나 클릭하세요</h3>
                <p>최대 10MB / PDF 파일만 가능</p>
                <input type="file" id="fileInput" accept=".pdf">
                <div id="fileName" style="color: #E11D48; font-weight: 600; margin-top: 10px;"></div>
            </div>

            <div class="category-select">
                <button class="category-btn active" data-category="lecture"><span class="icon">🎓</span>대학 강의교재</button>
                <button class="category-btn" data-category="church"><span class="icon">⛪</span>교회 주보</button>
                <button class="category-btn" data-category="catalog"><span class="icon">📦</span>상품 카탈로그</button>
                <button class="category-btn" data-category="election"><span class="icon">🗳️</span>선거 홍보물</button>
                <button class="category-btn" data-category="newsletter"><span class="icon">📰</span>지자체 소식지</button>
                <button class="category-btn" data-category="language"><span class="icon">📚</span>외국어 학습</button>
            </div>

            <button class="btn btn-primary convert-btn" id="convertBtn" disabled>
                변환 시작하기
            </button>

            <div class="progress-container" id="progressContainer">
                <div class="progress-bar">
                    <div class="progress-fill" id="progressFill"></div>
                </div>
                <p class="progress-text" id="progressText">변환 준비 중...</p>
            </div>

            <div class="result-container" id="resultContainer">
                <h3 style="margin-bottom: 20px; text-align: center;">✅ 변환 완료!</h3>
                <div class="result-preview">
                    <iframe id="resultPreview" src=""></iframe>
                </div>
                <div class="result-actions">
                    <a href="#" class="btn btn-primary" id="downloadBtn">HTML 다운로드</a>
                    <button class="btn btn-secondary" onclick="resetDemo()">다른 파일 변환</button>
                </div>
            </div>
        </div>
    </section>

    <!-- Use Cases Section -->
    <section class="use-cases" id="use-cases">
        <h2 class="section-title">다양한 <span>적용 분야</span></h2>
        <p class="section-subtitle">PDF 문서 종류에 맞는 최적화된 모바일 변환을 제공합니다</p>
        <div class="use-cases-grid">
            <div class="use-case-card">
                <div class="use-case-icon">🎓</div>
                <h3>lecture - 대학 강의교재</h3>
                <p>대학 PDF 강의교재를 모바일에서 학습하기 편리한 형태로 최적화 변환합니다.</p>
            </div>
            <div class="use-case-card">
                <div class="use-case-icon">⛪</div>
                <h3>church - 교회 주보</h3>
                <p>교회 PDF 주보를 성도들이 스마트폰에서 쉽게 확인할 수 있도록 모바일 최적화 변환합니다.</p>
            </div>
            <div class="use-case-card">
                <div class="use-case-icon">📦</div>
                <h3>catalog - 상품 카탈로그</h3>
                <p>기업 상품 카탈로그를 모바일에서 편리하게 열람할 수 있도록 최적화 변환합니다.</p>
            </div>
            <div class="use-case-card">
                <div class="use-case-icon">🗳️</div>
                <h3>election - 선거 홍보물</h3>
                <p>선거 후보 홍보물을 유권자들에게 효과적으로 전달할 수 있도록 모바일 최적화 변환합니다.</p>
            </div>
            <div class="use-case-card">
                <div class="use-case-icon">📰</div>
                <h3>newsletter - 지자체 소식지</h3>
                <p>지자체 소식지를 주민들이 스마트폰에서 편리하게 읽을 수 있도록 모바일 최적화 변환합니다.</p>
            </div>
            <div class="use-case-card featured">
                <div class="use-case-icon">📚</div>
                <h3>language - 외국어 학습기 <span class="badge-new">NEW</span></h3>
                <p>특정 직군을 위한 외국어 학습 자료를 모바일에서 효과적으로 학습할 수 있도록 최적화 변환합니다.</p>
            </div>
        </div>
    </section>

    <!-- Beta Section -->
    <section class="beta-section" id="beta">
        <div class="beta-container">
            <div class="beta-badge">🎁 BETA TESTER</div>
            <h2>베타테스터 모집</h2>
            <p>StudySnap의 새로운 기능을 먼저 체험하고 피드백을 주세요.<br>베타테스터에게는 특별한 혜택이 제공됩니다.</p>
            <div class="beta-benefits">
                <div class="beta-benefit">
                    <div class="icon">🆓</div>
                    <h4>무료 이용</h4>
                    <p>베타 기간 동안 모든 기능 무료</p>
                </div>
                <div class="beta-benefit">
                    <div class="icon">⚡</div>
                    <h4>우선 액세스</h4>
                    <p>신규 기능 우선 체험</p>
                </div>
                <div class="beta-benefit">
                    <div class="icon">🎁</div>
                    <h4>정식 출시 할인</h4>
                    <p>정식 서비스 50% 할인</p>
                </div>
            </div>
            <div class="beta-form">
                <form onsubmit="event.preventDefault(); alert('베타테스터 신청이 완료되었습니다!');">
                    <div class="form-group">
                        <label>이메일 *</label>
                        <input type="email" placeholder="example@email.com" required>
                    </div>
                    <div class="form-group">
                        <label>이름</label>
                        <input type="text" placeholder="홍길동">
                    </div>
                    <div class="form-group">
                        <label>관심 분야</label>
                        <select>
                            <option value="">선택해주세요</option>
                            <option value="lecture">대학 강의교재</option>
                            <option value="church">교회 주보</option>
                            <option value="catalog">상품 카탈로그</option>
                            <option value="election">선거 홍보물</option>
                            <option value="newsletter">지자체 소식지</option>
                            <option value="language">외국어 학습</option>
                            <option value="other">기타</option>
                        </select>
                    </div>
                    <button type="submit" class="btn-submit">베타테스터 신청하기</button>
                </form>
            </div>
        </div>
    </section>

    <!-- Features Section -->
    <section class="features" id="features">
        <h2 class="section-title">핵심 <span>기능</span></h2>
        <p class="section-subtitle">강력하고 편리한 PDF 변환 기능</p>
        <div class="features-grid">
            <div class="feature-card">
                <div class="feature-icon">🤖</div>
                <h3>AI 레이아웃 분석</h3>
                <p>AI로 문서 구조를 자동 분석하여 최적의 모바일 레이아웃을 생성합니다.</p>
            </div>
            <div class="feature-card">
                <div class="feature-icon">📱</div>
                <h3>반응형 디자인</h3>
                <p>모든 스마트폰과 태블릿에서 완벽하게 표시되는 반응형 웹페이지를 생성합니다.</p>
            </div>
            <div class="feature-card">
                <div class="feature-icon">⚡</div>
                <h3>빠른 변환</h3>
                <p>10페이지 PDF 기준 3~5초 내에 변환이 완료됩니다.</p>
            </div>
            <div class="feature-card">
                <div class="feature-icon">🌙</div>
                <h3>다크모드 지원</h3>
                <p>눈의 피로를 줄이는 다크모드와 폰트 크기 조절 기능을 제공합니다.</p>
            </div>
            <div class="feature-card">
                <div class="feature-icon">🔗</div>
                <h3>간편한 공유</h3>
                <p>카카오톡, 문자 등 다양한 채널로 손쉽게 공유할 수 있습니다.</p>
            </div>
            <div class="feature-card">
                <div class="feature-icon">🔒</div>
                <h3>보안 처리</h3>
                <p>업로드된 파일은 변환 후 자동 삭제되어 안전하게 처리됩니다.</p>
            </div>
        </div>
    </section>

    <!-- Contact Section -->
    <section class="contact" id="contact">
        <h2>문의하기</h2>
        <div class="contact-info">
            <div class="contact-item">
                <div class="icon">📧</div>
                <p><a href="mailto:jmyangkr@gmail.com">jmyangkr@gmail.com</a></p>
            </div>
            <div class="contact-item">
                <div class="icon">📱</div>
                <p><a href="tel:010-8665-8150">010-8665-8150</a></p>
            </div>
        </div>
    </section>

    <footer class="footer">
        <p>&copy; 2024 StudySnap. All rights reserved.</p>
    </footer>

    <script>
        // API Endpoint (change this to your actual server)
        const API_BASE = 'http://115.21.251.90:8000';

        let selectedFile = null;
        let selectedCategory = 'lecture';

        // Smooth scroll
        document.querySelectorAll('a[href^="#"]').forEach(a => {
            a.addEventListener('click', e => {
                e.preventDefault();
                const t = document.querySelector(a.getAttribute('href'));
                if (t) window.scrollTo({ top: t.offsetTop - 80, behavior: 'smooth' });
            });
        });

        // File upload handling
        const uploadArea = document.getElementById('uploadArea');
        const fileInput = document.getElementById('fileInput');
        const convertBtn = document.getElementById('convertBtn');
        const fileName = document.getElementById('fileName');

        // Drag and drop
        uploadArea.addEventListener('dragover', e => {
            e.preventDefault();
            uploadArea.classList.add('dragover');
        });

        uploadArea.addEventListener('dragleave', () => {
            uploadArea.classList.remove('dragover');
        });

        uploadArea.addEventListener('drop', e => {
            e.preventDefault();
            uploadArea.classList.remove('dragover');
            const file = e.dataTransfer.files[0];
            if (file && file.type === 'application/pdf') {
                handleFile(file);
            } else {
                alert('PDF 파일만 업로드 가능합니다.');
            }
        });

        fileInput.addEventListener('change', e => {
            const file = e.target.files[0];
            if (file) handleFile(file);
        });

        function handleFile(file) {
            if (file.size > 10 * 1024 * 1024) {
                alert('파일 크기는 10MB 이하여야 합니다.');
                return;
            }
            selectedFile = file;
            fileName.textContent = '선택된 파일: ' + file.name;
            convertBtn.disabled = false;
        }

        // Category selection
        document.querySelectorAll('.category-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                document.querySelectorAll('.category-btn').forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                selectedCategory = btn.dataset.category;
            });
        });

        // Convert button
        convertBtn.addEventListener('click', async () => {
            if (!selectedFile) return;

            const progressContainer = document.getElementById('progressContainer');
            const progressFill = document.getElementById('progressFill');
            const progressText = document.getElementById('progressText');
            const resultContainer = document.getElementById('resultContainer');

            progressContainer.style.display = 'block';
            resultContainer.style.display = 'none';
            convertBtn.disabled = true;

            // Progress animation
            let progress = 0;
            const progressInterval = setInterval(() => {
                progress += Math.random() * 15;
                if (progress > 90) progress = 90;
                progressFill.style.width = progress + '%';

                if (progress < 30) progressText.textContent = 'PDF 분석 중...';
                else if (progress < 60) progressText.textContent = 'AI 레이아웃 최적화 중...';
                else progressText.textContent = 'HTML 생성 중...';
            }, 500);

            try {
                const formData = new FormData();
                formData.append('file', selectedFile);
                formData.append('category', selectedCategory);

                const response = await fetch(API_BASE + '/api/convert', {
                    method: 'POST',
                    body: formData
                });

                if (!response.ok) throw new Error('변환 실패');

                const result = await response.json();

                clearInterval(progressInterval);
                progressFill.style.width = '100%';
                progressText.textContent = '변환 완료!';

                setTimeout(() => {
                    progressContainer.style.display = 'none';
                    resultContainer.style.display = 'block';
                    document.getElementById('resultPreview').src = result.preview_url || '#';
                    document.getElementById('downloadBtn').href = result.download_url || '#';
                }, 500);

            } catch (error) {
                clearInterval(progressInterval);
                progressFill.style.width = '100%';
                progressText.textContent = '데모 서버 연결이 필요합니다. 베타테스터로 신청해주세요!';

                // Demo mode - show sample result
                setTimeout(() => {
                    alert('현재 데모 서버가 연결되지 않았습니다.\\n\\n베타테스터로 신청하시면 실제 변환 기능을 체험하실 수 있습니다!');
                    progressContainer.style.display = 'none';
                    convertBtn.disabled = false;
                }, 1500);
            }
        });

        function resetDemo() {
            selectedFile = null;
            fileInput.value = '';
            fileName.textContent = '';
            convertBtn.disabled = true;
            document.getElementById('progressContainer').style.display = 'none';
            document.getElementById('resultContainer').style.display = 'none';
        }
    </script>
</body>
</html>"""

# Write to file
with open('c:/StudySnap-Backend/outputs/netlify_deploy/index.html', 'w', encoding='utf-8') as f:
    f.write(html_content)

print('StudySnap demo homepage created successfully!')
print('File: c:/StudySnap-Backend/outputs/netlify_deploy/index.html')
