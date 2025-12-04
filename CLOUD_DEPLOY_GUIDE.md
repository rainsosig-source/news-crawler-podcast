# 🚀 구글 클라우드(Cloud Run) 배포 가이드

이 가이드는 로컬 PC에서 개발한 뉴스 크롤러를 구글 클라우드에 배포하여 24시간 자동으로 실행되게 하는 방법을 설명합니다.

## 1️⃣ 사전 준비

1.  **Google Cloud SDK 설치**: [다운로드 링크](https://cloud.google.com/sdk/docs/install)
2.  **프로젝트 생성**: Google Cloud Console에서 새 프로젝트 생성 (예: `news-crawler-project`)
3.  **결제 계정 연결**: 프로젝트에 결제 계정 연결 (무료 등급 사용을 위해 필수)

## 2️⃣ 초기 설정 (터미널에서 실행)

PowerShell을 열고 다음 명령어들을 순서대로 실행하세요.

```powershell
# 1. 구글 클라우드 로그인
gcloud auth login

# 2. 프로젝트 설정 (PROJECT_ID를 실제 프로젝트 ID로 변경)
gcloud config set project news-crawler-rainsosig

# 3. 필요한 서비스 활성화
gcloud services enable run.googleapis.com
gcloud services enable containerregistry.googleapis.com
gcloud services enable cloudbuild.googleapis.com
```

## 3️⃣ 배포하기 (한 방 명령어)

다음 명령어를 실행하면 이미지를 빌드하고 Cloud Run에 배포합니다.

```powershell
gcloud run deploy news-crawler `
  --source . `
  --region asia-northeast3 `
  --memory 1Gi `
  --cpu 1 `
  --timeout 10m `
  --set-env-vars "GEMINI_API_KEY=your_api_key_here" `
  --allow-unauthenticated
```
*   `asia-northeast3`: 서울 리전
*   `--timeout 10m`: 크롤링 및 오디오 생성 시간을 고려하여 10분으로 설정
*   `GEMINI_API_KEY`: `.env`에 있는 실제 키로 바꿔서 입력하세요!

## 4️⃣ 스케줄러 설정 (1시간마다 실행)

Cloud Run은 요청이 올 때만 실행됩니다. 1시간마다 자동으로 실행되게 하려면 **Cloud Scheduler**를 설정해야 합니다.

1.  [Cloud Scheduler 콘솔](https://console.cloud.google.com/cloudscheduler) 접속
2.  **"작업 만들기"** 클릭
3.  **이름**: `hourly-news-crawl`
4.  **빈도**: `0 * * * *` (매시 정각)
5.  **대상 유형**: HTTP
6.  **URL**: 방금 배포한 Cloud Run 서비스의 URL (예: `https://news-crawler-xyz.a.run.app`)
7.  **HTTP 메서드**: POST (또는 GET)

## ✅ 완료!

이제 PC를 꺼도 구글 클라우드가 1시간마다 뉴스를 크롤링하고 팟캐스트를 만들어줍니다.
