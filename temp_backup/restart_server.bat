@echo off
echo ========================================
echo StudySnap Server 재시작 스크립트
echo ========================================

cd /d %~dp0

echo.
echo [1] 기존 서버 종료 중...
taskkill /F /IM python.exe 2>nul

echo [2] 포트 8000 정리 중...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :8000 ^| findstr LISTENING 2^>nul') do (
    taskkill /F /PID %%a 2>nul
)

echo [3] 2초 대기...
timeout /t 2 /nobreak >nul

echo.
echo [4] 서버 시작 중...
echo ========================================
echo     URL: http://localhost:8000
echo     에디터: http://localhost:8000/static/editor.html
echo     파일목록: http://localhost:8000/static/files.html
echo ========================================
echo.

python app.py
