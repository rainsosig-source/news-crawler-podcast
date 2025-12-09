# 관리자 권한 확인
if (-NOT ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole] "Administrator")) {
    Write-Warning "⚠️ 이 스크립트는 관리자 권한이 필요합니다!"
    Write-Host "PowerShell을 관리자 권한으로 다시 실행해주세요." -ForegroundColor Yellow
    pause
    exit
}

Write-Host "🚀 뉴스 크롤러 자동 실행 설정을 시작합니다..." -ForegroundColor Green
Write-Host ""

# 현재 폴더 경로
$ProjectPath = $PWD.Path
Write-Host "프로젝트 경로: $ProjectPath" -ForegroundColor Cyan

# Python 경로 자동 찾기
try {
    $PythonPath = (Get-Command python).Source
    Write-Host "Python 경로: $PythonPath" -ForegroundColor Cyan
} catch {
    Write-Host "❌ Python을 찾을 수 없습니다. Python이 설치되어 있고 PATH에 추가되어 있는지 확인하세요." -ForegroundColor Red
    pause
    exit
}

Write-Host ""
Write-Host "📅 작업 스케줄러에 등록 중..." -ForegroundColor Yellow

# 작업 스케줄러 등록
try {
    # 기존 작업 삭제 (있다면)
    Unregister-ScheduledTask -TaskName "Newscrawler" -Confirm:$false -ErrorAction SilentlyContinue
    
    # 새 작업 생성
    $Action = New-ScheduledTaskAction -Execute $PythonPath -Argument "naver_crawler.py" -WorkingDirectory $ProjectPath
    $Trigger = New-ScheduledTaskTrigger -Daily -At "00:00" -RepetitionInterval (New-TimeSpan -Hours 1) -RepetitionDuration ([TimeSpan]::MaxValue)
    $Settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable -ExecutionTimeLimit (New-TimeSpan -Hours 0)
    
    Register-ScheduledTask -TaskName "Newscrawler" -Action $Action -Trigger $Trigger -Settings $Settings -Description "매시간 뉴스 크롤링 및 팟캐스트 생성" -Force | Out-Null
    
    Write-Host ""
    Write-Host "✅ 작업 스케줄러 등록 완료!" -ForegroundColor Green
    Write-Host ""
    Write-Host "⏰ 실행 일정:" -ForegroundColor Cyan
    Write-Host "   - 시작 시간: 매일 00:00" -ForegroundColor White
    Write-Host "   - 반복 간격: 1시간마다" -ForegroundColor White
    Write-Host "   - 다음 실행: " -NoNewline
    
    $NextRun = (Get-ScheduledTask -TaskName "Newscrawler").Triggers[0].StartBoundary
    Write-Host $NextRun -ForegroundColor Yellow
    
    Write-Host ""
    Write-Host "💡 작업 스케줄러를 열어서 확인하려면: Win + R → taskschd.msc" -ForegroundColor Cyan
    Write-Host "💡 지금 수동으로 테스트하려면: Start-ScheduledTask -TaskName 'Newscrawler'" -ForegroundColor Cyan
    
} catch {
    Write-Host "❌ 작업 스케줄러 등록 실패: $_" -ForegroundColor Red
    pause
    exit
}

Write-Host ""
pause
