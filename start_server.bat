@echo off
echo ========================================
echo StudySnap Server 시작 스크립트
echo ========================================

cd /d %~dp0

echo.
echo [1] 기존 서버 종료 중...
taskkill /F /IM python.exe 2>nul
timeout /t 2 /nobreak >nul

echo.
echo [2] 서버 시작 중...
echo     URL: http://localhost:8000
echo     에디터: http://localhost:8000/static/editor.html
echo.
echo ========================================

python app.py
