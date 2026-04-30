@echo off
echo ========================================
echo  피부관리실 홍보 에이전트 - 스케줄 등록
echo ========================================
echo.

set PROJECT_PATH=%~dp0..

echo 매일 07:00에 텔레그램 대화형 모드를 실행합니다.
echo.

schtasks /create /tn "BeautyAgentMorning" /tr "cmd /c cd /d %PROJECT_PATH% && python -m src.main morning" /sc daily /st 07:00 /f

echo.
echo 등록 완료!
echo.
echo   매일 07:00 - 텔레그램: "오늘 만들 홍보물을 알려주세요"
echo   답장하면   - 자동으로 콘텐츠 생성 + 텔레그램 전송
echo.
echo 삭제: schtasks /delete /tn "BeautyAgentMorning" /f
pause
