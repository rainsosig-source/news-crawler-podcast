import os
import requests
import json
from dotenv import load_dotenv
import time

# Load environment variables
load_dotenv()

def call_gemini_rest_api(prompt, model="gemma-3-27b-it", api_key=None):
    """
    Gemini API를 REST로 직접 호출 (Cloud Run ADC 충돌 방지)
    """
    if not api_key:
        api_key = os.getenv("GEMINI_API_KEY")
    
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
    
    headers = {
        "Content-Type": "application/json"
    }
    
    data = {
        "contents": [{
            "parts": [{"text": prompt}]
        }],
        "generationConfig": {
            "temperature": 0.7,
            "maxOutputTokens": 8192
        }
    }
    
    response = requests.post(url, headers=headers, json=data, timeout=120)
    response.raise_for_status()
    
    result = response.json()
    
    if "candidates" in result and len(result["candidates"]) > 0:
        return result["candidates"][0]["content"]["parts"][0]["text"]
    else:
        raise Exception(f"Gemini API 응답 오류: {result}")

def truncate_content_smart(content, max_chars=15000):
    """
    Intelligently truncate content to fit within context window.
    
    Args:
        content: The news article content
        max_chars: Maximum characters to keep (default: 15000)
    
    Returns:
        Truncated content that fits within the limit
    """
    if not content or len(content) <= max_chars:
        return content
    
    # Find the last sentence boundary before max_chars
    truncated = content[:max_chars]
    
    # Try to end at a sentence boundary
    sentence_enders = ['다.', '요.', '습니다.', '까요.', '세요.']
    last_sentence_pos = -1
    
    for ender in sentence_enders:
        pos = truncated.rfind(ender)
        if pos > last_sentence_pos:
            last_sentence_pos = pos
    
    if last_sentence_pos > max_chars * 0.7:  # At least 70% of content
        return truncated[:last_sentence_pos + len(sentence_enders[0])]
    
    # Fallback: just cut at word boundary
    last_space = truncated.rfind(' ')
    if last_space > 0:
        return truncated[:last_space] + '...'
    
    return truncated + '...'


def validate_script(script_text):
    """
    대본의 유효성을 검증합니다.
    
    Returns:
        (is_valid, error_message)
    """
    if not script_text or len(script_text.strip()) < 100:
        return False, "대본이 너무 짧습니다 (100자 미만)"
    
    # 상현/지민 대화 형식 확인
    lines = script_text.split('\n')
    dialogue_count = 0
    
    for line in lines:
        if line.strip().startswith('상현:') or line.strip().startswith('지민:'):
            dialogue_count += 1
    
    if dialogue_count < 6:  # 최소 6개 대화 (각자 3번씩)
        return False, f"대화 수가 부족합니다 ({dialogue_count}개, 최소 6개 필요)"
    
    # 금지된 특수문자 확인
    forbidden_chars = ['*', '#', '^', '~', '`']
    for char in forbidden_chars:
        if char in script_text:
            return False, f"금지된 특수문자 발견: {char}"
    
    return True, ""


def generate_podcast_script(news_title, news_content, requirements=None, model="gemma-3-27b-it", max_retries=2):
    """
    Generates a podcast script from news content using Gemini API (Flash model).
    """
    # Truncate content to fit within model's context window
    optimized_content = truncate_content_smart(news_content, max_chars=15000)
    
    # Show truncation info
    if len(news_content) > len(optimized_content):
        print(f"[본문 최적화] {len(news_content)}자 → {len(optimized_content)}자 (컨텍스트 제한)")
    
    custom_reqs = ""
    if requirements:
        custom_reqs = f"\n    [추가 요청사항] {requirements}"

    # [개선된 프롬프트 - 상세한 페르소나와 대화 예시 포함]
    prompt = f"""
    당신은 청취율 1위 시사/교양 팟캐스트의 메인 작가입니다.
    딱딱한 뉴스를 친구랑 수다 떨듯이 재미있고 깊이 있게 풀어내는 것이 당신의 특기입니다.
    다음 뉴스 기사를 바탕으로 두 진행자(상현, 지민)의 '티키타카'가 돋보이는 대본을 작성해 주세요.

    [기사 정보]
    - 제목: {news_title}
    - 본문: {optimized_content}

    [진행자 페르소나]
    1. **상현 (남성, 메인 호스트)**: 
       - 뉴스 내용의 전문가 느낌. 차분하고 신뢰감 있는 목소리.
       - 어려운 내용을 찰떡같은 비유로 쉽게 설명해주는 '설명 요정'.
       - 가끔 아재 개그를 던지거나 지민의 텐션을 진정시키는 역할.
    2. **지민 (여성, 보조 호스트)**: 
       - 호기심 많은 '프로 질문러'. 청취자의 마음을 대변함.
       - 리액션이 풍부하고 감정 표현이 솔직함.
       - 상현의 설명에 센스 있게 비유로 요약함.

    [대화 구성 가이드]
    1. **도입부 (Hook)**: 
       - 지민이 기사와 관련된 가벼운 질문이나 상황극으로 시작하며 청취자의 귀를 사로잡으세요.
    2. **전개 (Body)**: 
       - 상현이 기사의 핵심 내용을 설명하면, 지민이 질문하고 놀라워하며 대화를 이어가세요.
       - 중학교 3학년도 이해할 수 있는 쉬운 단어와 비유를 적극 사용하세요.
    3. **심화 (Insight)**: 
       - 단순 사실 전달을 넘어, 이게 왜 중요한지, 앞으로 우리 삶이 어떻게 바뀔지에 대해 짧게 토론하세요.
    4. **마무리 (Outro)**: 
       - 내용을 깔끔하게 한 줄로 요약하거나, 청취자에게 생각할 거리를 던지며 자연스럽게 끝내세요.
       - 주의: 청취해 주셔서 감사합니다, 다음 시간에 만나요 같은 형식적인 클로징 멘트는 절대 하지 마세요.

    [대화 예시 - 이런 느낌으로 작성하세요]
    지민: 상현 선배님, 요즘 AI가 진짜 어디까지 온 건지 모르겠어요.
    상현: 맞아요, 정말 빠르게 발전하고 있죠. 오늘 이 기사 보셨어요?
    지민: 아직 못 봤는데, 무슨 내용이에요?
    상현: 이번에 새로운 AI 모델이 나왔는데요, 기존보다 성능이 두 배나 좋아졌대요.
    지민: 우와, 두 배요? 그럼 뭐가 더 잘 되는 건가요?
    상현: 예를 들면 이미지를 보고 설명하는 능력이 훨씬 정교해졌어요. 마치 사람처럼요.

    {custom_reqs}

    [필수 제약 사항]
    1. **말투**: 서로에게 정중한 존댓말(해요체)을 사용하세요. 반말 절대 금지.
    2. **형식**: 반드시 상현: 대사, 지민: 대사 형태로만 작성하세요. 지문, 해설, 괄호 설명 절대 금지.
    3. **길이**: 대화 교환은 최소 12-15회 이상으로 작성하세요. 너무 짧으면 안 됩니다.
    4. **특수문자**: 대사 속에 별표, 샵, 하이픈 같은 특수문자를 절대 넣지 마세요.
    5. **순수 대본만 출력**: 프롬프트 내용이나 지시사항을 대본에 포함하지 마세요. 오직 대화 내용만 출력하세요.    
    """
    
    # Gemini API Only (REST API 직접 호출)
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return "❌ 오류: .env 파일에 GEMINI_API_KEY가 설정되지 않았습니다."

    # 재시도 루프
    for attempt in range(max_retries + 1):
        try:
            start_time = time.time()
            print(f"🤖 Gemini API ({model})로 대본 생성 중... (시도 {attempt + 1}/{max_retries + 1})")
            
            # REST API 직접 호출 (Cloud Run ADC 충돌 방지)
            raw_script = call_gemini_rest_api(prompt, model=model, api_key=api_key)
            elapsed_time = time.time() - start_time
            
            print(f"✅ 생성 완료! (소요 시간: {elapsed_time:.2f}초)")
            
            # Rate limit 보호: API 호출 후 7초 대기
            print("⏳ API Rate Limit 보호를 위해 7초 대기 중...")
            time.sleep(7)
            
            # 대본 정제 및 검증
            script = clean_script_output(raw_script)
            
            if len(script) < len(raw_script):
                print(f"🧹 대본 정제됨: {len(raw_script)}자 → {len(script)}자")
            
            is_valid, error_msg = validate_script(script)
            
            if is_valid:
                print("✅ 대본 검증 통과")
                return script
            else:
                print(f"⚠️ 대본 검증 실패: {error_msg}")
                if attempt < max_retries:
                    print(f"재시도 중... ({attempt + 1}/{max_retries})")
                    time.sleep(1)
                    continue
                else:
                    print("⚠️ 최대 재시도 횟수 도달. 검증되지 않은 대본 반환.")
                    return script
            
        except Exception as e:
            print(f"❌ Gemini API 오류 (시도 {attempt + 1}): {e}")
            if attempt < max_retries:
                print(f"재시도 중... ({attempt + 1}/{max_retries}) - 30초 후 재시도")
                time.sleep(30)  # Rate limit 회복을 위해 30초 대기
                continue
            else:
                return f"⚠️ Gemini API 오류 발생: {e}"


def clean_script_output(text):
    """
    모델 출력에서 순수 대화 내용만 추출하고 특수문자를 제거합니다.
    """
    # 금지된 특수문자 제거
    forbidden_chars = ['*', '#', '^', '~', '`']
    for char in forbidden_chars:
        text = text.replace(char, '')

    lines = text.split('\n')
    cleaned_lines = []
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        if line.startswith("상현:") or line.startswith("지민:") or \
           line.startswith("진행자 A:") or line.startswith("진행자 B:") or \
           line.startswith("A:") or line.startswith("B:"):
            cleaned_lines.append(line)
            
    if len(cleaned_lines) < 2:
        return text
        
    return "\n".join(cleaned_lines)

if __name__ == "__main__":
    # Test data
    title = "파이썬 4.0 출시 예정"
    content = "파이썬 소프트웨어 재단은 2026년 파이썬 4.0을 출시한다고 밝혔다. 이번 버전에서는 GIL(Global Interpreter Lock)이 완전히 제거되어 멀티코어 성능이 비약적으로 향상될 예정이다."
    
    print("팟캐스트 대본 생성 중... (시간이 걸릴 수 있습니다)")
    script = generate_podcast_script(title, content)
    print("\n[생성된 대본]")
    print(script)
