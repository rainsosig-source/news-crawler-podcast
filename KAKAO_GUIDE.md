# 카카오톡 나에게 보내기 사용 가이드

## 1. 카카오 개발자 설정

### 1-1. 카카오 개발자 계정 생성
1. [Kakao Developers](https://developers.kakao.com/) 접속
2. 카카오 계정으로 로그인

### 1-2. 애플리케이션 추가
1. "내 애플리케이션" 메뉴 클릭
2. "애플리케이션 추가하기" 클릭
3. 앱 이름 입력 (예: "메시지 테스트")
4. 사업자명 입력 (개인은 이름 입력)
5. "저장" 클릭

### 1-3. REST API 키 복사
1. 생성한 앱 선택
2. "앱 설정" > "요약 정보" 이동
3. "REST API 키" 복사 (예: `abc123def456...`)

### 1-4. 플랫폼 설정
1. "앱 설정" > "플랫폼" 메뉴
2. "Web 플랫폼 등록" 클릭
3. 사이트 도메인: `http://localhost:8000` 입력
4. "저장" 클릭

### 1-5. 카카오 로그인 활성화
1. "제품 설정" > "카카오 로그인" 메뉴
2. "활성화 설정" 상태를 **ON**으로 변경
3. "Redirect URI" 섹션에서 "Redirect URI 등록" 클릭
4. `http://localhost:8000` 입력 후 "저장"

## 2. 환경 설정

### 2-1. 환경 변수 파일 생성
```bash
# .env.example 파일을 .env로 복사
copy .env.example .env
```

### 2-2. API 키 설정
`.env` 파일을 열어서 REST API 키를 입력:
```
KAKAO_REST_API_KEY=여기에_복사한_REST_API_키_붙여넣기
```

### 2-3. 패키지 설치
```bash
pip install -r requirements.txt
```

## 3. 실행

### 3-1. 스크립트 실행
```bash
python kakao_message_sender.py
```

### 3-2. 실행 과정
1. **브라우저 자동 실행**: 카카오 로그인 페이지가 열립니다
2. **로그인**: 카카오 계정으로 로그인
3. **동의**: 앱 권한 동의 화면이 나타나면 "동의하고 계속하기" 클릭
4. **인증 완료**: "카카오 인증 완료!" 메시지가 표시되면 브라우저 창 닫기
5. **메시지 전송**: 자동으로 카카오톡에 메시지 전송
6. **확인**: 카카오톡을 열어서 메시지 확인

## 4. 전송되는 메시지 예시

```
🌍 세계 주요 국가 정보

1. 대한민국 🇰🇷
2. 일본 🇯🇵
3. 미국 🇺🇸
```

## 5. 문제 해결

### 토큰 만료 에러
```bash
# kakao_token.json 파일 삭제 후 재실행
del kakao_token.json
python kakao_message_sender.py
```

### API 키 에러
- `.env` 파일의 `KAKAO_REST_API_KEY` 값 확인
- 카카오 개발자 콘솔에서 REST API 키 재확인

### Redirect URI 에러
- 카카오 개발자 콘솔에서 `http://localhost:8000` 등록 확인
- 대소문자, 슬래시 유무 정확히 일치해야 함

## 6. 파일 설명

| 파일 | 설명 |
|------|------|
| `kakao_message_sender.py` | 메인 스크립트 |
| `.env` | API 키 저장 (Git에 커밋하지 말 것) |
| `.env.example` | 환경 변수 템플릿 |
| `kakao_token.json` | 액세스 토큰 저장 (자동 생성) |
| `requirements.txt` | 필요한 Python 패키지 |
| `.gitignore` | Git 제외 파일 목록 |

## 7. 보안 주의사항

⚠️ **절대 공유하지 말 것**:
- `.env` 파일
- `kakao_token.json` 파일
- REST API 키

✅ **Git 커밋 전 확인**:
- `.gitignore`에 `.env`와 `kakao_token.json`이 포함되어 있는지 확인
