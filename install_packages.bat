@echo off
chcp 65001 >nul
echo ========================================
echo EEG 실시간 분석 시스템 - 패키지 설치
echo ========================================
echo.

echo 필요한 Python 패키지를 설치합니다...
echo.

python -m pip install --upgrade pip
python -m pip install -r requirements.txt

echo.
echo ========================================
echo 설치가 완료되었습니다!
echo ========================================
echo.
echo 이제 run_batch.bat 또는 run_interactive.bat을 실행하세요.
echo.

pause
