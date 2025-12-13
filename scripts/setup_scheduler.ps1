# 관리자 권한 확인
if (-NOT ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole] "Administrator")) {
    Write-Warning "관리자 권한으로 실행해주세요!"
    pause
    exit
}

# 현재 폴더 경로
$ProjectPath = $PWD.Path

# Python 경로 자동 찾기
$PythonPath = (Get-Command python).Source

# 기존 작업 삭제 (있으면)
Unregister-ScheduledTask -TaskName "Newscrawler" -Confirm:$false -ErrorAction SilentlyContinue
Write-Host "기존 작업 정리 완료" -ForegroundColor Yellow

# 작업 액션 설정
$Action = New-ScheduledTaskAction -Execute $PythonPath -Argument "naver_crawler.py" -WorkingDirectory $ProjectPath

# 트리거 설정: 매시간 반복 (Once 트리거 + RepetitionInterval 사용)
$Trigger = New-ScheduledTaskTrigger -Once -At (Get-Date).Date -RepetitionInterval (New-TimeSpan -Hours 1) -RepetitionDuration (New-TimeSpan -Days 365)

# 설정
$Settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable -RunOnlyIfNetworkAvailable

# 작업 등록
Register-ScheduledTask -TaskName "Newscrawler" -Action $Action -Trigger $Trigger -Settings $Settings -Description "매시간 뉴스 크롤링 및 팟캐스트 생성" -User "SYSTEM" -RunLevel Highest

Write-Host ""
Write-Host "작업 스케줄러 등록 완료!" -ForegroundColor Green
Write-Host "매시간 정각에 자동 실행됩니다." -ForegroundColor Cyan
Write-Host ""
Write-Host "확인 명령어: Get-ScheduledTask -TaskName 'Newscrawler'" -ForegroundColor Gray

pause
