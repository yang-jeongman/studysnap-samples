@echo off
echo ========================================
echo StudySnap Backend Server
echo ========================================
echo.

REM Python 가상환경 확인 및 활성화
if exist "venv\Scripts\activate.bat" (
    echo [INFO] 가상환경 활성화 중...
    call venv\Scripts\activate.bat
) else (
    echo [WARN] 가상환경이 없습니다. setup.bat를 먼저 실행하세요.
)

echo [INFO] 서버 시작 중...
echo [INFO] API 문서: http://localhost:8000/docs
echo [INFO] 종료하려면 Ctrl+C를 누르세요
echo.
echo ========================================

python app.py

pause
