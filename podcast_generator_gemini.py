"""
Gemini API를 사용한 팟캐스트 대본 생성 테스트 스크립트
기존 Ollama 버전과 비교하여 품질을 검증합니다.
"""

import os
import time
from dotenv import load_dotenv

# .env 파일에서 환경 변수 로드
load_dotenv()

try:
    import google.generativeai as genai
except ImportError:
    print("❌ google-generativeai 패키지가 설치되지 않았습니다.")
    print("다음 명령어로 설치하세요:")
    print("   pip install google-generativeai python-dotenv")
    exit(1)


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
    
    # 형식적 클로징 멘트 확인 (사용자 요청으로 비활성화)
    # forbidden_phrases = ['감사합니다', '다음 시간', '청취해', '들어주셔서']
    # last_200 = script_text[-200:].lower()
    # for phrase in forbidden_phrases:
    #     if phrase in last_200:
    #         return False, f"형식적 클로징 멘트 발견: {phrase}"
    
    return True, ""


def generate_podcast_script_gemini(
    news_title, 
    news_content, 
    requirements=None, 
    model_name="gemini-2.5-flash",
    max_retries=2
):
    """
    Generates a podcast script from news content using Gemini API.
    
    Args:
        news_title: Title of the news article
        news_content: Content of the news article
        requirements: Additional custom requirements (optional)
        model_name: Gemini model to use ("gemini-2.5-flash" or "gemini-2.5-pro")
        max_retries: Maximum retry attempts if validation fails
    
    Returns:
        Generated podcast script or error message
    """
    # API 키 확인
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return "❌ GEMINI_API_KEY가 .env 파일에 설정되지 않았습니다.\n" \
               "GEMINI_API_GUIDE.md를 참고하여 API 키를 발급받으세요."
    
    # Gemini API 구성
    genai.configure(api_key=api_key)
    
    # Truncate content to fit within model's context window
    optimized_content = truncate_content_smart(news_content, max_chars=15000)
    
    # Show truncation info
    if len(news_content) > len(optimized_content):
        print(f"[본문 최적화] {len(news_content)}자 → {len(optimized_content)}자 (컨텍스트 제한)")
    
    custom_reqs = ""
    if requirements:
        custom_reqs = f"\n    [추가 요청사항] {requirements}"

    # [이전 프롬프트 보존]
    # prompt = f"""
    # 당신은 인기 있는 팟캐스트의 메인 작가입니다.
    # 다음 뉴스 기사를 바탕으로 두 명의 진행자(진행자 A, 진행자 B)가 대화하는 형식의 팟캐스트 대본을 작성해 주세요.
    # 
    # [기사 제목]
    # {news_title}
    # 
    # [기사 본문]
    # {optimized_content}
    # 
    # [요청 사항]
    # 1. 청취자가 중학교 3학년 수준으로 이해하기 쉽게 쉬운 말로 풀어서 설명해 주세요.
    # 2. 두 진행자의 티키타카(주고받는 대화)가 자연스럽고 재치 있게 구성해 주세요.
    # 3. 진행자 A의 이름은 '상현'(남성)이고, 차분하고 전문적인 톤입니다.
    # 4. 진행자 B의 이름은 '지민'(여성)이고, 호기심 많고 활기찬 톤입니다.
    # 5. 대본은 한국어로 작성해 주세요.    
    # 6. 특수문자는 대화 내용에서 제외 해 주세요.
    # 7. **상현과 지민은 서로에게 예의를 갖추어 반드시 존댓말(해요체)로 대화해 주세요.** (반말은 절대 사용하지 마세요)
    # 8. 대본 형식을 반드시 "상현: [대사]", "지민: [대사]" 형태로 작성해 주세요.
    # 9. **오프닝(인사)과 클로징(마무리 인사, 청취 감사 멘트 등)은 절대 넣지 마세요.** 본론만 깔끔하게 작성해 주세요.{custom_reqs}
    # """

    # [개선된 프롬프트 - 예시 추가]
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
    
    # 재시도 루프
    for attempt in range(max_retries + 1):
        try:
            # 모델 생성
            model = genai.GenerativeModel(model_name)
            
            # 시작 시간 기록
            start_time = time.time()
            
            print(f"🤖 {model_name} 모델로 대본 생성 중... (시도 {attempt + 1}/{max_retries + 1})")
            
            # 컨텐츠 생성
            response = model.generate_content(prompt)
            
            # 소요 시간 계산
            elapsed_time = time.time() - start_time
            
            # 토큰 사용량 로깅 (있는 경우)
            try:
                if hasattr(response, 'usage_metadata'):
                    print(f"📊 토큰 사용: {response.usage_metadata.total_token_count}개")
            except:
                pass
            
            print(f"✅ 생성 완료! (소요 시간: {elapsed_time:.2f}초)")
            
            # 대본 정제 및 검증
            raw_script = response.text
            script = clean_script_output(raw_script)
            
            if len(script) < len(raw_script):
                print(f"🧹 대본 정제됨: {len(raw_script)}자 → {len(script)}자 (불필요한 라인 제거)")
            
            is_valid, error_msg = validate_script(script)
            
            if is_valid:
                print("✅ 대본 검증 통과")
                return script
            else:
                print(f"⚠️ 대본 검증 실패: {error_msg}")
                if attempt < max_retries:
                    print(f"재시도 중... ({attempt + 1}/{max_retries})")
                    time.sleep(1)  # 짧은 대기 후 재시도
                    continue
                else:
                    # 마지막 시도였다면 검증 실패했어도 반환
                    print("⚠️ 최대 재시도 횟수 도달. 검증되지 않은 대본 반환.")
                    return script
            
        except Exception as e:
            print(f"❌ Gemini API 오류 (시도 {attempt + 1}): {e}")
            if attempt < max_retries:
                print(f"재시도 중... ({attempt + 1}/{max_retries})")
                time.sleep(2)  # 에러 발생 시 더 긴 대기
                continue
            else:
                return f"❌ Gemini API 호출 중 오류 발생: {e}\n" \
                       f"API 키가 올바른지, 할당량이 남아있는지 확인하세요."

def clean_script_output(text):
    """
    모델 출력에서 순수 대화 내용만 추출하고 특수문자를 제거합니다.
    프롬프트가 포함되거나 불필요한 헤더/푸터를 제거합니다.
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
            
        # 대화 형식인 경우만 유지 (상현: ..., 지민: ...)
        # 또는 대화가 길어져서 줄바꿈된 경우도 고려해야 하지만, 
        # 일단은 명확한 화자가 있는 라인과 그 다음 라인들을 허용하는 식으로 접근하거나
        # 단순히 화자 이름으로 시작하는 라인만 필터링하는 것이 안전함.
        # 여기서는 화자 이름으로 시작하는 라인만 엄격하게 필터링.
        if line.startswith("상현:") or line.startswith("지민:") or \
           line.startswith("진행자 A:") or line.startswith("진행자 B:") or \
           line.startswith("A:") or line.startswith("B:"):
            cleaned_lines.append(line)
            
    # 만약 필터링 결과가 너무 짧으면(대화가 아님), 원본 반환 (혹시 모를 오류 방지)
    if len(cleaned_lines) < 2:
        return text
        
    return "\n".join(cleaned_lines)


def compare_with_ollama(news_title, news_content):
    """
    Gemini와 Ollama 결과를 비교합니다.
    """
    print("\n" + "="*70)
    print("🔬 Gemini vs Ollama 비교 테스트")
    print("="*70)
    
    # Gemini Flash 테스트
    print("\n1️⃣ Gemini 2.5 Flash 테스트")
    print("-"*70)
    flash_result = generate_podcast_script_gemini(
        news_title, 
        news_content, 
        model_name="gemini-2.5-flash"
    )
    print(f"\n[생성된 대본 미리보기]\n{flash_result[:300]}...\n")
    
    # Gemini Pro 테스트
    print("\n2️⃣ Gemini 2.5 Pro 테스트")
    print("-"*70)
    pro_result = generate_podcast_script_gemini(
        news_title, 
        news_content, 
        model_name="gemini-2.5-pro"
    )
    print(f"\n[생성된 대본 미리보기]\n{pro_result[:300]}...\n")
    
    # Ollama 테스트 (선택적)
    try:
        from podcast_generator import generate_podcast_script as generate_ollama
        print("\n3️⃣ Ollama (Qwen 2.5 14B) 테스트")
        print("-"*70)
        ollama_result = generate_ollama(news_title, news_content)
        print(f"\n[생성된 대본 미리보기]\n{ollama_result[:300]}...\n")
    except Exception as e:
        print(f"\n⚠️ Ollama 테스트 건너뜀 (서버 미실행 또는 오류): {e}")
    
    print("\n" + "="*70)
    print("✅ 테스트 완료!")
    print("="*70)
    
    # 전체 결과 저장
    with open("gemini_test_results.txt", "w", encoding="utf-8") as f:
        f.write("="*70 + "\n")
        f.write("Gemini API 테스트 결과\n")
        f.write("="*70 + "\n\n")
        
        f.write(f"[기사 제목]\n{news_title}\n\n")
        f.write(f"[기사 본문]\n{news_content[:500]}...\n\n")
        
        f.write("="*70 + "\n")
        f.write("1. Gemini 1.5 Flash 결과\n")
        f.write("="*70 + "\n")
        f.write(flash_result + "\n\n")
        
        f.write("="*70 + "\n")
        f.write("2. Gemini 1.5 Pro 결과\n")
        f.write("="*70 + "\n")
        f.write(pro_result + "\n\n")
    
    print("\n📄 전체 결과가 'gemini_test_results.txt' 파일에 저장되었습니다.")


if __name__ == "__main__":
    # 테스트 데이터
    test_title = "AI 기술 발전으로 의료 진단 정확도 크게 향상"
    test_content = """
    최근 인공지능(AI) 기술의 발전으로 의료 분야에서 진단 정확도가 크게 향상되고 있습니다.
    
    서울대학교 병원 연구팀은 AI를 활용한 암 진단 시스템을 개발했으며, 이 시스템은 기존 방식 대비 
    정확도가 15% 높은 것으로 나타났습니다. 특히 초기 단계의 암 발견율이 획기적으로 개선되어 
    조기 치료 가능성이 크게 높아졌다고 연구팀은 밝혔습니다.
    
    이 AI 진단 시스템은 딥러닝 기술을 기반으로 수만 건의 의료 영상 데이터를 학습했으며, 
    의사의 판단을 보조하는 역할을 합니다. 현재 서울대병원을 포함한 5개 대형 병원에서 
    시범 운영 중이며, 내년부터는 전국 주요 병원으로 확대될 예정입니다.
    
    의료계 전문가들은 "AI 기술이 의사를 대체하는 것이 아니라, 더 정확한 진단을 돕는 
    강력한 도구가 될 것"이라며 "환자들에게 더 나은 의료 서비스를 제공할 수 있을 것"이라고 
    기대를 표했습니다.
    """
    
    print("🎙️ Gemini API 팟캐스트 대본 생성 테스트")
    print("\n💡 테스트 항목:")
    print("  - Gemini 1.5 Flash (빠르고 무료 한도 높음)")
    print("  - Gemini 1.5 Pro (고품질, 무료 한도 낮음)")
    print("  - Ollama Qwen 2.5 14B (기존 로컬 모델)")
    
    input("\n⏎ Enter를 눌러 테스트를 시작하세요...")
    
    compare_with_ollama(test_title, test_content)
