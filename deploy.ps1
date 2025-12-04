# Google Cloud Run 배포 자동화 스크립트

$PROJECT_ID = "news-crawler-rainsosig"
$SERVICE_NAME = "news-crawler"
$REGION = "asia-northeast3"

Write-Host "🚀 구글 클라우드 배포를 시작합니다..." -ForegroundColor Green
Write-Host "프로젝트: $PROJECT_ID"
Write-Host "서비스명: $SERVICE_NAME"
Write-Host "리전: $REGION"
Write-Host "----------------------------------------"

# 프로젝트 설정 확인 및 변경
$current_project = gcloud config get-value project 2>$null
if ($current_project -ne $PROJECT_ID) {
    Write-Host "🔄 프로젝트를 $PROJECT_ID 로 전환합니다..." -ForegroundColor Yellow
    gcloud config set project $PROJECT_ID
}

# 배포 실행
Write-Host "📦 코드를 빌드하고 배포 중입니다... (약 1~2분 소요)" -ForegroundColor Cyan
gcloud run deploy $SERVICE_NAME `
    --source . `
    --region $REGION `
    --allow-unauthenticated

if ($LASTEXITCODE -eq 0) {
    Write-Host "`n✅ 배포가 성공적으로 완료되었습니다!" -ForegroundColor Green
    Write-Host "이제 클라우드에서 새 코드가 실행됩니다."
}
else {
    Write-Host "`n❌ 배포 중 오류가 발생했습니다." -ForegroundColor Red
    Write-Host "위의 에러 메시지를 확인해 주세요."
}

# Pause
