import os
import requests
import json
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

try:
    import google.generativeai as genai
except ImportError:
    print("❌ google-generativeai 패키지가 설치되지 않았습니다.")

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

def generate_podcast_script(news_title, news_content, requirements=None, model="gemini-2.5-flash"):
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
        custom_reqs = f"\n    10. [추가 요청사항] {requirements}"

    prompt = f"""
    당신은 인기 있는 팟캐스트의 메인 작가입니다.
    다음 뉴스 기사를 바탕으로 두 명의 진행자(진행자 A, 진행자 B)가 대화하는 형식의 팟캐스트 대본을 작성해 주세요.
    
    [기사 제목]
    {news_title}
    
    [기사 본문]
    {optimized_content}
    
    [요청 사항]
    1. 청취자가 중학교 3학년 수준으로 이해하기 쉽게 쉬운 말로 풀어서 설명해 주세요.
    2. 두 진행자의 티키타카(주고받는 대화)가 자연스럽고 재치 있게 구성해 주세요.
    3. 진행자 A의 이름은 '상현'(남성)이고, 차분하고 전문적인 톤입니다.
    4. 진행자 B의 이름은 '지민'(여성)이고, 호기심 많고 활기찬 톤입니다.
    5. 대본은 한국어로 작성해 주세요.    
    7. **상현과 지민은 서로에게 예의를 갖추어 반드시 존댓말(해요체)로 대화해 주세요.** (반말은 절대 사용하지 마세요)
    8. 대본 형식을 반드시 "상현: [대사]", "지민: [대사]" 형태로 작성해 주세요.
    9. **오프닝(인사)과 클로징(마무리 인사, 청취 감사 멘트 등)은 절대 넣지 마세요.** 본론만 깔끔하게 작성해 주세요.
    10. **순수 대본만 출력**: 프롬프트 내용이나 지시사항을 대본에 포함하지 마세요. 오직 대화 내용만 출력하세요.
    {custom_reqs}
    """
    
    # Gemini API Only
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return "❌ 오류: .env 파일에 GEMINI_API_KEY가 설정되지 않았습니다."

    try:
        genai.configure(api_key=api_key)
        gemini_model = genai.GenerativeModel(model)
        
        print(f"🤖 Gemini API ({model})로 대본 생성 중...")
        response = gemini_model.generate_content(prompt)
        
        # 대본 정제
        script = clean_script_output(response.text)
        return script
        
    except Exception as e:
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
