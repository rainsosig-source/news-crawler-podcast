# SFTP 업로드 문제 진단 결과

## 📋 진단 요약

### ✅ 정상 작동하는 항목
1. **SFTP 연결**: 웹 서버 `139.150.81.187:22`에 정상 연결됨
2. **파일 업로드**: 테스트 파일 업로드 및 확인 성공
3. **디렉토리 구조**: `/root/flask-app/static/podcast` 경로 정상 존재
4. **코드 변경**: `naver_crawler.py`에서 GCS → SFTP 전환 완료

### ❌ 발견된 문제
1. **Google Cloud TTS 인증**: 로컬 환경에 Google Cloud 자격 증명 없음
   - 오디오 파일(MP3) 생성 불가
   - Cloud Run에서는 자동 인증되어 정상 작동

## 🔍 상세 진단 내역

### 1. SFTP 연결 테스트
```
✅ SSH 연결 성공
✅ SFTP 세션 성공
✅ 디렉토리 존재: /root/flask-app/static/podcast
✅ 파일 업로드 성공
✅ 파일 확인됨 (크기: 48 bytes)
```

### 2. MP3 디렉토리 상태
```
✅ MP3 디렉토리 존재: E:\AI\웹크롤러\MP3
⚠️  MP3 파일이 없습니다 (생성된 파일 없음)
```

### 3. 크롤러 실행 테스트
```python
오류 메시지:
❌ Google Cloud TTS Error: Your default credentials were not found. 
   To set up Application Default Credentials, see 
   https://cloud.google.com/docs/authentication/external/set-up-adc
```

## 💡 해결 방안

### 옵션 1: Cloud Run에서 실행 (권장)
Cloud Run 환경에서는 자동으로 인증이 처리되므로 별도 설정 없이 작동합니다.

**확인 방법:**
1. Cloud Run 로그 확인
2. SFTP 서버에 MP3 파일 생성 여부 확인

### 옵션 2: 로컬에서 Google Cloud 인증 설정
로컬 환경에서 테스트하려면:

1. Google Cloud 서비스 계정 키 다운로드
2. 환경 변수 설정:
   ```powershell
   $env:GOOGLE_APPLICATION_CREDENTIALS="경로\서비스계정키.json"
   ```

### 옵션 3: 로컬 테스트용 간소화 버전
Google Cloud TTS 없이 텍스트만 생성하는 테스트 모드:
```python
crawl_naver_news("인공지능", use_ai=True, make_audio=False)
```

## 📊 현재 상태

| 항목 | 상태 | 비고 |
|-----|------|------|
| SFTP 연결 | ✅ 정상 | 139.150.81.187:22 |
| 코드 수정 | ✅ 완료 | GCS → SFTP 전환 |
| 로컬 TTS | ❌ 불가 | 인증 필요 |
| Cloud Run TTS | ✅ 예상 정상 | 자동 인증 |

## 🎯 권장 조치

1. **Cloud Run에서 실행 확인**
   - 배포 후 Cloud Run 로그에서 업로드 성공 메시지 확인
   - SFTP 서버에 파일이 생성되는지 확인

2. **로컬 테스트가 필요한 경우**
   - Google Cloud 콘솔에서 서비스 계정 키 발급
   - `GOOGLE_APPLICATION_CREDENTIALS` 환경 변수 설정

## 📝 참고 사항

- 로컬 환경 제한은 Google Cloud TTS만 해당
- SFTP 업로드 기능 자체는 정상 작동
- Cloud Run 환경에서는 모든 기능 정상 작동 예상

---
생성일: 2025-12-02
테스트 환경: Windows 로컬
