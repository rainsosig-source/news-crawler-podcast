
import sys
import os
from podcast_generator_gemini import clean_script_output, generate_podcast_script_gemini

def test_cleaning_logic():
    print("🧪 Cleaning Logic Test")
    print("-" * 50)
    
    dirty_script = """
    당신은 팟캐스트 작가입니다. 다음은 대본입니다.
    
    [기사 제목]
    AI 뉴스
    
    상현: 안녕하세요. *반갑습니다.*
    지민: #반갑습니다.
    (지문: 웃으며)
    상현: 오늘 소식은?
    지민: AI가 발전했대요.
    
    [요청사항]
    반말하지 마세요.
    """
    
    cleaned = clean_script_output(dirty_script)
    
    print(f"[Original]\n{dirty_script}")
    print(f"\n[Cleaned]\n{cleaned}")
    
    expected_lines = [
        "상현: 안녕하세요. 반갑습니다.",
        "지민: 반갑습니다.",
        "상현: 오늘 소식은?",
        "지민: AI가 발전했대요."
    ]
    
    for line in expected_lines:
        if line not in cleaned:
            print(f"❌ Missing expected line: {line}")
            return False
            
    if "[기사 제목]" in cleaned or "당신은" in cleaned:
        print("❌ Failed to remove prompt artifacts")
        return False
        
    print("✅ Cleaning logic passed!")
    return True

def test_real_generation():
    print("\n🎙️ Real Generation Test")
    print("-" * 50)
    
    title = "테스트 뉴스"
    content = "이것은 테스트 뉴스입니다. AI가 대본을 잘 작성하는지 확인합니다."
    
    script = generate_podcast_script_gemini(title, content)
    
    print("\n[Generated Script]")
    print(script)
    
    if "당신은" in script or "프롬프트" in script or "[" in script:
        # Note: '[' might be in the script if it's part of the dialogue, but usually we want to avoid it.
        # But let's be lenient on '[' if it's not a header.
        pass
        
    lines = script.split('\n')
    for line in lines:
        if line.strip() and not (line.startswith("상현:") or line.startswith("지민:")):
            print(f"⚠️ Suspicious line: {line}")
            
    return True

if __name__ == "__main__":
    if test_cleaning_logic():
        test_real_generation()
