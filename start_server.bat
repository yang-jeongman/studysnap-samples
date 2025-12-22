@echo off
chcp 65001 >nul
cls

echo.
echo ========================================
echo    StudySnap Server 시작 스크립트
echo ========================================
echo.

cd /d %~dp0

echo [1] 기존 서버 종료 중...
taskkill /F /IM python.exe 2>nul
timeout /t 2 /nobreak >nul

echo.
echo ========================================
echo    접속 링크
echo ========================================
echo.
echo    메인: http://localhost:8000
echo    에디터: http://localhost:8000/static/editor.html
echo    여의도순복음교회 주보: http://localhost:8000/static/fg-converter.html
echo.
echo ========================================
echo.
echo [2] 서버 시작 중... (아래 로그 확인)
echo.
echo ========================================

python app.py
