@echo off
chcp 65001 >nul
echo ========================================
echo EEG 실시간 분석 시스템 - 배치 처리
echo ========================================
echo.

REM 현재 디렉토리로 이동
cd /d "%~dp0"

echo 분석 데이터 폴더의 모든 파일을 처리합니다...
echo.

python main.py --folder "분석 데이터"

echo.
echo ========================================
echo 처리가 완료되었습니다!
echo ========================================
echo.
echo 결과 확인:
echo - HTML 보고서: reports 폴더
echo - 그래프: graphs 폴더
echo - 분석 데이터: analysis_data 폴더
echo.

pause
