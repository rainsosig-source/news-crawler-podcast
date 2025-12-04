"""
Google Cloud TTS 간단한 테스트
"""
from google.cloud import texttospeech
import os

def test_tts():
    """TTS API 간단 테스트"""
    try:
        print("=" * 70)
        print("🎤 Google Cloud TTS 테스트")
        print("=" * 70)
        
        # 클라이언트 초기화
        print("\n1️⃣ TTS 클라이언트 초기화...")
        client = texttospeech.TextToSpeechClient()
        print("   ✅ 클라이언트 생성 성공")
        
        # 테스트 텍스트
        test_text = "안녕하세요. 구글 클라우드 음성 합성 테스트입니다."
        
        print(f"\n2️⃣ 음성 합성 요청...")
        print(f"   텍스트: {test_text}")
        
        # 입력 설정
        synthesis_input = texttospeech.SynthesisInput(text=test_text)
        
        # 음성 설정 (한국어 남성)
        voice = texttospeech.VoiceSelectionParams(
            language_code="ko-KR",
            name="ko-KR-Standard-C"
        )
        
        # 오디오 설정
        audio_config = texttospeech.AudioConfig(
            audio_encoding=texttospeech.AudioEncoding.MP3
        )
        
        # 합성 요청
        response = client.synthesize_speech(
            input=synthesis_input,
            voice=voice,
            audio_config=audio_config
        )
        
        print("   ✅ 음성 합성 성공")
        
        # 파일 저장
        output_file = "tts_test.mp3"
        with open(output_file, "wb") as out:
            out.write(response.audio_content)
        
        file_size = os.path.getsize(output_file)
        print(f"\n3️⃣ 파일 저장 완료")
        print(f"   파일: {output_file}")
        print(f"   크기: {file_size:,} bytes")
        
        print("\n" + "=" * 70)
        print("✅ Google Cloud TTS 정상 작동!")
        print("=" * 70)
        
        return True
        
    except Exception as e:
        print(f"\n❌ 오류 발생: {e}")
        print("\n인증 확인:")
        print("  gcloud auth application-default login")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    test_tts()
