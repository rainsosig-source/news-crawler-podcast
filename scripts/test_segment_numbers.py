"""
세그먼트 번호 테스트 - 수정된 코드 확인
"""
from podcast_audio import run_audio_generation

# 간단한 테스트 대본
test_script = """
상현: 안녕하세요, 첫 번째 대사입니다.
지민: 와, 두 번째 대사예요!
상현: 세 번째 대사입니다.
지민: 네 번째 대사네요.
상현: 다섯 번째 대사입니다.
지민: 여섯 번째 대사예요!
"""

print("=" * 70)
print("🧪 세그먼트 번호 테스트")
print("=" * 70)
print("\n기대 결과: 세그먼트 0, 1, 2, 3, 4, 5 순서대로 생성\n")

result = run_audio_generation(test_script, "test_segments.mp3", title="세그먼트 번호 테스트")

if result:
    print(f"\n✅ 오디오 생성 성공: {result}")
else:
    print("\n❌ 오디오 생성 실패")

print("\n" + "=" * 70)
