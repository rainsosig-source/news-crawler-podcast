# Gemini API 키 발급 가이드

## 1️⃣ Google AI Studio 접속

1. 브라우저에서 접속: https://aistudio.google.com/
2. Google 계정으로 로그인

## 2️⃣ API 키 생성

1. 왼쪽 메뉴에서 **"Get API key"** 클릭
2. **"Create API key"** 버튼 클릭
3. 프로젝트 선택 또는 **"Create API key in new project"** 선택
4. 생성된 API 키 복사 (예: `AIzaSy...`)

⚠️ **중요**: API 키는 한 번만 표시됩니다. 안전한 곳에 저장하세요!

## 3️⃣ .env 파일에 추가

프로젝트 루트 디렉토리의 `.env` 파일을 열어 다음 줄을 추가하세요:

```
GEMINI_API_KEY=여기에_복사한_API_키_붙여넣기
```

## 4️⃣ 무료 등급 확인

- **Gemini 1.5 Flash**: 하루 1,500회 무료
- **Gemini 1.5 Pro**: 하루 50회 무료
- 자세한 정보: https://ai.google.dev/pricing

## 5️⃣ 테스트 준비 완료!

이제 `podcast_generator_gemini.py`를 실행하여 테스트할 수 있습니다.
