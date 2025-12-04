
def test_prompt_format():
    requirements = "좀 더 재미있게 해줘"
    
    # User's current implementation
    custom_reqs = f"\n[추가 요청사항] {requirements}"
    
    prompt = f"""
    당신은 청취율 1위 시사/교양 팟캐스트의 메인 작가입니다.
    (중략)
    상현: 예를 들면 이미지를 보고 설명하는 능력이 훨씬 정교해졌어요. 마치 사람처럼요.

    {custom_reqs}

    [필수 제약 사항]
    1. 말투: ...
    """
    
    print("--- Generated Prompt ---")
    print(prompt)
    print("------------------------")

if __name__ == "__main__":
    test_prompt_format()
