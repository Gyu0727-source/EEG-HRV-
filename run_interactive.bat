@echo off
chcp 65001 >nul
echo ========================================
echo EEG 실시간 분석 시스템 - 대화형 모드
echo ========================================
echo.

REM 현재 디렉토리로 이동
cd /d "%~dp0"

python main.py

echo.
pause
