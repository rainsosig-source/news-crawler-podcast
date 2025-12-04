@echo off
echo ====================================
echo 웹크롤러 프로젝트 정리 스크립트
echo ====================================
echo.

:: 1. scripts 폴더 생성
echo [1/5] scripts 폴더 생성 중...
if not exist scripts mkdir scripts

:: 2. 테스트 및 관리 스크립트 이동
echo [2/5] 관리 스크립트 이동 중...
move test_*.py scripts\ 2>nul
move check_*.py scripts\ 2>nul
move cleanup_*.py scripts\ 2>nul
move analyze_storage.py scripts\ 2>nul
move restart_*.py scripts\ 2>nul
move force_restart_remote.py scripts\ 2>nul
move upload_about.py scripts\ 2>nul
move download_manager.py scripts\ 2>nul
move list_models.py scripts\ 2>nul

:: 3. 임시 파일 및 로그 삭제
echo [3/5] 임시 파일 삭제 중...
del /q *.txt 2>nul
del /q temp_*.mp3 2>nul
del /q test_segments.mp3 2>nul
del /q tts_test.mp3 2>nul
del /q countries.geojson 2>nul
del /q .env.wsl 2>nul
del /q implementation_plan.md 2>nul
del /q task.md 2>nul
del /q walkthrough.md 2>nul
del /q setup_db.sql 2>nul

:: 4. Windows 실행 파일 삭제 (Cloud Run 불필요)
echo [4/5] Windows 실행 파일 삭제 중...
del /q ffmpeg.exe 2>nul
del /q ffplay.exe 2>nul
del /q ffprobe.exe 2>nul

:: 5. 백업 폴더 삭제
echo [5/5] 백업 폴더 정리 중...
rmdir /s /q backup 2>nul
rmdir /s /q check 2>nul
rmdir /s /q deploy 2>nul
rmdir /s /q utils 2>nul
rmdir /s /q mp3 2>nul

echo.
echo ====================================
echo ✅ 정리 완료!
echo ====================================
echo.
echo 핵심 파일만 남았습니다:
echo - Python 코드 파일
echo - 설정 파일 (Dockerfile, requirements.txt 등)
echo - 정적 리소스 (opening.mp3, templates, static)
echo - 관리 스크립트는 scripts 폴더로 이동됨
echo.
pause
