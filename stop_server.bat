@echo off
echo ========================================
echo StudySnap Server 종료 스크립트
echo ========================================

echo.
echo [1] Python 서버 프로세스 찾는 중...
tasklist /FI "IMAGENAME eq python.exe" 2>nul | find /I "python.exe" >nul
if %ERRORLEVEL%==0 (
    echo [2] Python 프로세스 발견 - 종료 중...
    taskkill /F /IM python.exe 2>nul
    echo [OK] Python 서버가 종료되었습니다.
) else (
    echo [INFO] 실행 중인 Python 프로세스가 없습니다.
)

echo.
echo [3] 포트 8000 사용 중인 프로세스 확인...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :8000 ^| findstr LISTENING 2^>nul') do (
    echo [4] PID %%a 종료 중...
    taskkill /F /PID %%a 2>nul
)

echo.
echo ========================================
echo 서버 종료 완료!
echo 새 서버 시작: python app.py
echo ========================================
pause
