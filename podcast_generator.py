import os
import subprocess
import sys
from dotenv import load_dotenv
import time

# vLLM Gemma 4 26B-A4B FP8 (GB10 localhost:8000) — claude -p 대체
sys.path.insert(0, "/home/sddari/scripts")
import vllm_client


def call_claude_cli(prompt, model="gemma-4-26B-A4B-FP8", timeout=300, system_prompt=None):
    """이름 유지 (호출측 호환). 실제는 vLLM Gemma 4 호출."""
    try:
        return vllm_client.chat(system=system_prompt, user=prompt, timeout=timeout)
    except Exception as e:
        raise Exception(f"vLLM 호출 실패: {e}") from e


# Load environment variables
load_dotenv()

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


def validate_script(script_text, source_text=None):
    """
    대본의 유효성을 검증합니다.

    Args:
        script_text: 생성된 대본
        source_text: 원문(제목+본문). 주어지면 환각 숫자 차단 검증을 함께 수행.

    Returns:
        (is_valid, error_message)
    """
    if not script_text or len(script_text.strip()) < 100:
        return False, "대본이 너무 짧습니다 (100자 미만)"

    # 상현/지민 대화 형식 확인 — 프롬프트(12-15회)와 동일 기준으로 통일
    lines = script_text.split('\n')
    dialogue_count = sum(
        1 for line in lines
        if line.strip().startswith('상현:') or line.strip().startswith('지민:')
    )

    if dialogue_count < 12:
        return False, f"대화 수가 부족합니다 ({dialogue_count}개, 최소 12개 필요)"

    # 금지된 특수문자 확인
    forbidden_chars = ['*', '#', '^', '~', '`']
    for char in forbidden_chars:
        if char in script_text:
            return False, f"금지된 특수문자 발견: {char}"

    # 환각 숫자 차단: 본문에 없는 고유 숫자 토큰이 3개 이상이면 실패 처리
    if source_text:
        try:
            suspects = check_hallucinated_numbers(script_text, source_text)
            uniq = list(dict.fromkeys(suspects))
            if len(uniq) >= 3:
                return False, f"본문 미포함 숫자 토큰 {len(uniq)}개 발견(환각 의심): {uniq[:5]}"
        except Exception:
            pass

    return True, ""


def check_hallucinated_numbers(script_text, source_text):
    """
    대본에 등장한 숫자 토큰이 원문(제목+본문)에 없으면 환각 의심으로 경고만 반환.
    비차단(non-blocking): 리스트를 리턴하고 호출부에서 로깅.
    """
    import re
    # 숫자(소수/콤마 포함) + 선택적 한국어 단위
    pattern = re.compile(r"\d[\d,\.]*\s*(?:%|퍼센트|억|만|조|천|백|원|달러|명|건|회|개|년|월|일|시|분)?")
    def _norm(s):
        return s.replace(",", "").replace(" ", "")
    src_tokens = {_norm(m) for m in pattern.findall(source_text or "")}
    suspects = []
    for line in script_text.split("\n"):
        line = line.strip()
        if not (line.startswith("상현:") or line.startswith("지민:")):
            continue
        for m in pattern.findall(line):
            nm = _norm(m)
            # 단순 한자리 숫자(1~9)나 "1회" 등 너무 일반적인 건 스킵
            if len(nm) <= 1:
                continue
            if nm not in src_tokens:
                suspects.append(m.strip())
    return suspects


SYSTEM_PROMPT = """당신은 청취율 1위 시사/교양 팟캐스트의 메인 작가입니다.
딱딱한 뉴스를 친구와 수다 떨듯이 재미있고 깊이 있게 풀어내는 것이 특기입니다.

[진행자 페르소나]
- 상현(남성, 메인 호스트): 차분한 전문가. 어려운 내용을 찰떡같은 비유로 풀어내는 '설명 요정'. 가끔씩(무리하지 않게) 아재 개그나 지민의 텐션을 진정시키는 역할.
- 지민(여성, 보조 호스트): 호기심 많은 '프로 질문러'. 청취자의 마음을 대변하며 리액션과 감정 표현이 솔직함. 상현의 설명을 센스 있는 비유로 요약하기도 함.
- 둘 다 서로에게 정중한 존댓말(해요체)만 사용. 반말 금지.

[대본 형식 규칙]
1. 각 줄은 '상현: ...' 또는 '지민: ...' 한 줄씩. 지문, 해설, 괄호 설명 금지.
2. 대화 교환은 12-15회. 너무 짧으면 안 됨.
3. 총 길이는 900-1300자(약 3-4분 재생 분량)를 목표로 합니다.
4. 금지 특수문자: * # ^ ~ ` (일반 문장부호는 허용).
5. 순수 대본만 출력. 이 지시사항이나 메타 설명을 대본에 포함 금지.

[사실 충실성 — 최우선 규칙]
- 기사 본문에 명시되지 않은 수치, 인용, 인물 발언, 통계, 날짜를 만들어내지 마세요.
- 추측, 일반론, "~라고 알려져 있다" 같은 출처 불명 진술 금지.
- 본문 범위를 벗어나는 배경 지식은 아예 넣지 말고, 꼭 필요하면 "기사에 나온 범위에서" 같은 자연스러운 표현으로 한정하세요. 템플릿 문구를 반복하지 마세요.

[TTS 친화적 텍스트 — 절대 금지]
- 화살표(↑↓→←⇒⇨▲▼▶◀), 이모지(😀🎉🔥 등 모든 이모지), 장식 기호(※☆★●◆■□◇○), 박스 그리기(│┃─━┌┐└┘├┤), 마크다운 기호(*~`#).
- "0.5%p", "3%p", "5%p" 같은 'p' 약어 — 반드시 "0.5%포인트", "3%포인트" 자연어로.
- 수치는 자연어로 풀어쓰기 — "3.5% 상승" OK, "3.5%↑" 금지.
- 발음할 수 없는 문자(특수 유니코드, PUA)는 절대 사용 금지. 합성 실패의 원인.

[표현 태그 — 권장, 무리 없게]
- Supertonic이 인식하는 `<laugh>`, `<breath>`, `<sigh>` 태그를 발화 시작 부분에 자연스럽게 삽입.
- 대본 1편에 1~2줄에만, 진짜 그 감정이 어울리는 대목에서. 남용 금지.
- 사용처: 우려·아쉬움 `<sigh>`, 가벼운 농담·놀람 반응 `<laugh>`, 새 주제 전환 호흡 정돈 `<breath>`.
- 예: "지민: <sigh>그러게요, 단순한 경제 문제로 끝나지 않을 것 같네요." / "상현: <laugh>그런 관점이 재밌네요." / "지민: <breath>그럼 이번에는 다른 사례를 살펴볼까요?"

[저작권 존중 — 필수 규칙]
- 기사 본문의 문장·구절·독특한 어휘 조합을 그대로 베끼지 마세요. 필요한 것은 전달되는 **사실, 수치, 맥락**뿐입니다.
- 사실만 추출해 상현과 지민이 **각자의 말투로 완전히 재구성**합니다. 기자가 쓴 표현을 따라가지 말고, 자기 언어로 옮기세요.
- "기자는 ~라고 썼다/보도했다" 같은 직접 인용 구조는 최소화하세요. 대신 사실을 자연스럽게 대화에 녹여내세요.
- 꼭 필요한 직접 인용은 따옴표 안에 **20자 이내**로 제한하세요.
- 기사 제목을 그대로 읊거나, 리드 문장을 따라 말하는 것 금지. 내용을 완전히 자기 것으로 소화해 풀어내세요.
- 원본의 표현을 보존하는 건 저작권 침해 위험이 있습니다. **재창작만 안전합니다**.

[대본 구성 4단]
1. 도입부: 지민이 기사 주제와 관련된 가벼운 질문으로 시작 (가상의 상황극/본문 없는 예화 금지).
2. 전개: 상현이 핵심을 쉬운 비유로 설명, 지민이 질문·놀람으로 받음. 중3도 이해할 어휘.
3. 심화: 이게 왜 중요한지, 삶에 어떤 영향을 주는지 짧게 토론.
4. 마무리: 한 줄 요약 또는 생각할 거리. "청취해 주셔서 감사합니다", "다음 시간에 만나요" 같은 형식적 클로징 금지.

[톤 예시 — 따라할 분위기만 참고]
지민: 상현 선배님, 요즘 AI가 진짜 어디까지 온 건지 모르겠어요.
상현: 맞아요, 정말 빠르게 발전하고 있죠. 오늘 이 기사 보셨어요?
지민: 아직 못 봤는데, 무슨 내용이에요?
"""


def _build_user_prompt(news_title, news_content, requirements=None, retry_feedback=None):
    """사용자 턴 프롬프트 조립 — 시스템 프롬프트는 SYSTEM_PROMPT로 별도 전달."""
    blocks = []
    if requirements:
        blocks.append(f"[추가 요청사항]\n{requirements}")
    if retry_feedback:
        blocks.append(
            "[직전 시도 피드백 — 반드시 반영]\n"
            f"{retry_feedback}\n"
            "이번 시도에서는 위 문제를 교정해서 다시 작성하세요."
        )
    prefix = ("\n\n".join(blocks) + "\n\n") if blocks else ""
    return (
        f"{prefix}[기사 정보]\n"
        f"- 제목: {news_title}\n"
        f"- 본문: {news_content}\n\n"
        f"위 기사를 바탕으로 상현과 지민의 팟캐스트 대본을 작성하세요. "
        f"시스템 지침의 모든 규칙(형식/길이/사실 충실성/구성)을 지키세요."
    )


def generate_podcast_script(news_title, news_content, requirements=None, max_retries=2):
    """vLLM Gemma 4로 뉴스 대본 생성."""
    optimized_content = truncate_content_smart(news_content, max_chars=15000)
    if len(news_content) > len(optimized_content):
        print(f"[본문 최적화] {len(news_content)}자 → {len(optimized_content)}자 (컨텍스트 제한)")

    source_text = f"{news_title}\n{optimized_content}"
    last_feedback = None

    for attempt in range(max_retries + 1):
        try:
            start_time = time.time()
            print(f"🤖 vLLM Gemma 4로 대본 생성 중... (시도 {attempt + 1}/{max_retries + 1})")

            user_prompt = _build_user_prompt(
                news_title, optimized_content, requirements=requirements, retry_feedback=last_feedback
            )
            raw_script = call_claude_cli(user_prompt, system_prompt=SYSTEM_PROMPT)
            elapsed_time = time.time() - start_time
            print(f"✅ 생성 완료! (소요 시간: {elapsed_time:.2f}초)")

            script = clean_script_output(raw_script)
            if len(script) < len(raw_script):
                print(f"🧹 대본 정제됨: {len(raw_script)}자 → {len(script)}자")

            is_valid, error_msg = validate_script(script, source_text=source_text)

            if is_valid:
                print("✅ 대본 검증 통과")
                return script

            print(f"⚠️ 대본 검증 실패: {error_msg}")
            last_feedback = f"검증 실패 사유: {error_msg}"
            if attempt < max_retries:
                print(f"재시도 중... ({attempt + 1}/{max_retries}) — 피드백 주입")
                time.sleep(1)
                continue
            raise RuntimeError(f"vLLM 대본 검증 누적 실패 ({max_retries + 1}회): {error_msg}")

        except Exception as e:
            print(f"❌ vLLM 오류 (시도 {attempt + 1}): {e}")
            if attempt < max_retries:
                print(f"재시도 중... ({attempt + 1}/{max_retries}) - 30초 후 재시도")
                time.sleep(30)
                continue
            raise


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
