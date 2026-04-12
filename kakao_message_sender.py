#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
카카오톡 "나에게 보내기" API를 사용하여 메시지를 전송하는 스크립트
3개 국가 이름을 카카오톡으로 전송합니다.
"""

import requests
import json
import os
import webbrowser
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from dotenv import load_dotenv

# 환경 변수 로드
load_dotenv()

# 카카오 API 설정
KAKAO_REST_API_KEY = os.getenv('KAKAO_REST_API_KEY')
REDIRECT_URI = 'http://localhost:8000'
TOKEN_FILE = 'kakao_token.json'

# 글로벌 변수로 인증 코드 저장
auth_code = None


class CallbackHandler(BaseHTTPRequestHandler):
    """OAuth 콜백을 처리하는 HTTP 핸들러"""
    
    def do_GET(self):
        global auth_code
        
        # URL 파싱하여 인증 코드 추출
        parsed_url = urlparse(self.path)
        query_params = parse_qs(parsed_url.query)
        
        if 'code' in query_params:
            auth_code = query_params['code'][0]
            
            # 성공 응답 전송
            self.send_response(200)
            self.send_header('Content-type', 'text/html; charset=utf-8')
            self.end_headers()
            response = """
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="utf-8">
                <title>인증 완료</title>
                <style>
                    body {
                        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                        display: flex;
                        justify-content: center;
                        align-items: center;
                        height: 100vh;
                        margin: 0;
                        background: linear-gradient(135deg, #FEE500 0%, #FFD700 100%);
                    }
                    .container {
                        background: white;
                        padding: 40px;
                        border-radius: 20px;
                        box-shadow: 0 10px 40px rgba(0,0,0,0.1);
                        text-align: center;
                    }
                    h1 {
                        color: #3C1E1E;
                        margin-bottom: 20px;
                    }
                    p {
                        color: #666;
                        font-size: 16px;
                    }
                    .success-icon {
                        font-size: 64px;
                        margin-bottom: 20px;
                    }
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="success-icon">✅</div>
                    <h1>카카오 인증 완료!</h1>
                    <p>이 창을 닫으셔도 됩니다.</p>
                    <p>곧 메시지가 전송됩니다...</p>
                </div>
            </body>
            </html>
            """
            self.wfile.write(response.encode('utf-8'))
        else:
            # 에러 응답
            self.send_response(400)
            self.send_header('Content-type', 'text/html; charset=utf-8')
            self.end_headers()
            error_response = """
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="utf-8">
                <title>인증 실패</title>
            </head>
            <body>
                <h1>인증에 실패했습니다.</h1>
                <p>다시 시도해주세요.</p>
            </body>
            </html>
            """
            self.wfile.write(error_response.encode('utf-8'))
    
    def log_message(self, format, *args):
        """로그 메시지 출력 비활성화"""
        pass


def get_authorization_code():
    """브라우저를 통해 인증 코드 획득"""
    global auth_code
    
    # 카카오 인증 URL 생성
    auth_url = (
        f"https://kauth.kakao.com/oauth/authorize?"
        f"client_id={KAKAO_REST_API_KEY}&"
        f"redirect_uri={REDIRECT_URI}&"
        f"response_type=code"
    )
    
    print("🔐 카카오 로그인 페이지를 엽니다...")
    print(f"📋 인증 URL: {auth_url}\n")
    
    # 브라우저 열기
    webbrowser.open(auth_url)
    
    # 로컬 서버 시작하여 콜백 대기
    server = HTTPServer(('localhost', 8000), CallbackHandler)
    print("⏳ 카카오 로그인 및 인증 동의를 진행해주세요...")
    print("   (브라우저에서 로그인 후 동의하면 자동으로 진행됩니다)\n")
    
    # 한 번의 요청만 처리
    server.handle_request()
    
    return auth_code


def get_access_token(authorization_code):
    """인증 코드로 액세스 토큰 발급"""
    token_url = "https://kauth.kakao.com/oauth/token"
    
    data = {
        'grant_type': 'authorization_code',
        'client_id': KAKAO_REST_API_KEY,
        'redirect_uri': REDIRECT_URI,
        'code': authorization_code
    }
    
    response = requests.post(token_url, data=data)
    
    if response.status_code == 200:
        tokens = response.json()
        # 토큰을 파일에 저장
        with open(TOKEN_FILE, 'w') as f:
            json.dump(tokens, f, indent=2)
        print("✅ 액세스 토큰 발급 완료!\n")
        return tokens['access_token']
    else:
        print(f"❌ 토큰 발급 실패: {response.text}")
        return None


def load_access_token():
    """저장된 액세스 토큰 로드"""
    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE, 'r') as f:
            tokens = json.load(f)
            return tokens.get('access_token')
    return None


def send_message_to_me(access_token, countries):
    """나에게 메시지 보내기"""
    url = "https://kapi.kakao.com/v2/api/talk/memo/default/send"
    
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/x-www-form-urlencoded'
    }
    
    # 메시지 템플릿 생성
    country_list = "\n".join([f"{i+1}. {country}" for i, country in enumerate(countries)])
    
    template = {
        "object_type": "text",
        "text": f"🌍 세계 주요 국가 정보\n\n{country_list}",
        "link": {
            "web_url": "https://www.google.com",
            "mobile_web_url": "https://www.google.com"
        },
        "button_title": "자세히 보기"
    }
    
    data = {
        'template_object': json.dumps(template)
    }
    
    response = requests.post(url, headers=headers, data=data)
    
    if response.status_code == 200:
        print("✅ 메시지 전송 성공!")
        print(f"📱 카카오톡을 확인해보세요!\n")
        return True
    else:
        print(f"❌ 메시지 전송 실패: {response.status_code}")
        print(f"   상세: {response.text}\n")
        return False


def main():
    """메인 함수"""
    print("=" * 60)
    print("🎯 카카오톡 '나에게 보내기' 테스트")
    print("=" * 60)
    print()
    
    # API 키 확인
    if not KAKAO_REST_API_KEY:
        print("❌ 오류: KAKAO_REST_API_KEY가 설정되지 않았습니다.")
        print("   .env 파일을 확인해주세요.\n")
        return
    
    print(f"🔑 REST API 키: {KAKAO_REST_API_KEY[:10]}...\n")
    
    # 저장된 토큰 확인
    access_token = load_access_token()
    
    if not access_token:
        print("📝 저장된 토큰이 없습니다. 새로 인증을 진행합니다.\n")
        
        # 인증 코드 획득
        auth_code = get_authorization_code()
        
        if not auth_code:
            print("❌ 인증 코드 획득 실패")
            return
        
        print(f"✅ 인증 코드 획득: {auth_code[:20]}...\n")
        
        # 액세스 토큰 발급
        access_token = get_access_token(auth_code)
        
        if not access_token:
            print("❌ 액세스 토큰 발급 실패")
            return
    else:
        print("✅ 저장된 액세스 토큰을 사용합니다.\n")
    
    # 3개 국가 이름
    countries = ["대한민국 🇰🇷", "일본 🇯🇵", "미국 🇺🇸"]
    
    print("📤 메시지 전송 중...\n")
    
    # 메시지 전송
    success = send_message_to_me(access_token, countries)
    
    if success:
        print("=" * 60)
        print("✨ 모든 작업이 완료되었습니다!")
        print("=" * 60)
    else:
        print("⚠️  메시지 전송에 실패했습니다.")
        print("   토큰이 만료되었을 수 있습니다.")
        print(f"   '{TOKEN_FILE}' 파일을 삭제하고 다시 실행해보세요.\n")


if __name__ == "__main__":
    main()
