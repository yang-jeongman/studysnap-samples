@echo off
echo ========================================
echo StudySnap Backend 설치
echo ========================================
echo.

REM Python 버전 확인
python --version
if errorlevel 1 (
    echo [ERROR] Python이 설치되어 있지 않습니다.
    echo Python 3.9 이상을 설치해주세요.
    pause
    exit /b 1
)

echo.
echo [STEP 1/4] 가상환경 생성 중...
python -m venv venv

echo [STEP 2/4] 가상환경 활성화 중...
call venv\Scripts\activate.bat

echo [STEP 3/4] 패키지 설치 중...
pip install --upgrade pip
pip install -r requirements.txt

echo [STEP 4/4] 환경변수 파일 생성...
if not exist ".env" (
    copy .env.example .env
    echo [INFO] .env 파일이 생성되었습니다. 필요시 수정하세요.
) else (
    echo [INFO] .env 파일이 이미 존재합니다.
)

echo.
echo ========================================
echo 설치 완료!
echo.
echo 서버 실행: run.bat
echo API 문서: http://localhost:8000/docs
echo ========================================
pause
