import asyncio
from google.cloud import texttospeech
import os
from pydub import AudioSegment

# Voices (Google Cloud TTS Standard - 무료 400만 자/월)
# https://cloud.google.com/text-to-speech/docs/voices
VOICE_A = "ko-KR-Standard-C" # Male, Host A (Sanghyun) - Deep & Professional
VOICE_B = "ko-KR-Standard-A" # Female, Host B (Jimin) - Soft & Clear
VOICE_ANNOUNCER = "ko-KR-Standard-D" # Male, Title Announcer - Authoritative

async def generate_audio_segment(text, voice_name, output_file):
    """
    Generates audio using Google Cloud Text-to-Speech API.
    """
    try:
        # Clean up text
        text = text.replace("*", "").strip()
        if not text:
            return False

        # Initialize client
        client = texttospeech.TextToSpeechClient()

        # Set the text input to be synthesized
        synthesis_input = texttospeech.SynthesisInput(text=text)

        # Build the voice request
        # Note: language_code is 'ko-KR' for Korean
        voice = texttospeech.VoiceSelectionParams(
            language_code="ko-KR",
            name=voice_name
        )

        # Select the type of audio file you want returned
        audio_config = texttospeech.AudioConfig(
            audio_encoding=texttospeech.AudioEncoding.MP3,
            speaking_rate=1.1 # Slightly faster for natural conversation
        )

        # Perform the text-to-speech request
        response = client.synthesize_speech(
            input=synthesis_input, voice=voice, audio_config=audio_config
        )

        # The response's audio_content is binary.
        with open(output_file, "wb") as out:
            out.write(response.audio_content)
            
        return True

    except Exception as e:
        print(f"❌ Google Cloud TTS Error: {e}")
        return False

# Configure pydub to use ffmpeg
current_dir = os.path.dirname(os.path.abspath(__file__))
local_ffmpeg = os.path.join(current_dir, "ffmpeg.exe")

if os.path.exists(local_ffmpeg):
    # Local Windows environment with ffmpeg.exe
    print(f"Using local FFmpeg: {local_ffmpeg}")
    AudioSegment.converter = local_ffmpeg
    AudioSegment.ffmpeg = local_ffmpeg
    os.environ["PATH"] += os.pathsep + current_dir
else:
    # Cloud/Linux environment (ffmpeg installed via apt-get)
    print("Using system FFmpeg (Cloud/Linux environment)")

import re

async def create_podcast_audio(script_text, output_filename="podcast.mp3", title_text=None):
    """
    Parses the script and generates a combined MP3 file with title and opening music.
    """
    lines = script_text.split('\n')
    temp_files = []
    
    print(f"오디오 생성 시작 (Google Cloud TTS): {output_filename}")
    
    # 1. Generate Title Audio (if title provided)
    title_audio_file = "temp_title.mp3"
    has_title = False
    if title_text:
        print(f"제목 오디오 생성 중: {title_text}")
        # Clean title for TTS
        clean_title = title_text.replace("[", "").replace("]", "").strip()
        intro_text = f"오늘의 뉴스. {clean_title}."
        if await generate_audio_segment(intro_text, VOICE_ANNOUNCER, title_audio_file):
            has_title = True
    
    current_voice = VOICE_A # Default start
    segment_index = 0  # 실제 생성된 세그먼트 번호용
    
    for i, line in enumerate(lines):
        line = line.strip()
        if not line:
            continue
            
        # Skip headers and metadata
        if line.startswith("#") or line.startswith("[") or line.startswith("(") or "오프닝 멘트" in line or "클로징 멘트" in line or "본격적인 대화" in line or "본멘트" in line:
            continue

        voice = None
        text = ""
        
        # Parse "상현:" or "지민:"
        if re.search(r"^(상현|진행자\s*A|A\s*[:\.]|Host\s*A)", line, re.IGNORECASE):
            voice = VOICE_A
            current_voice = VOICE_A
            text = re.sub(r"^[\*]*(상현|진행자\s*A|A|Host\s*A)[\*]*\s*[:\.]?\s*", "", line)
        elif re.search(r"^(지민|진행자\s*B|B\s*[:\.]|Host\s*B)", line, re.IGNORECASE):
            voice = VOICE_B
            current_voice = VOICE_B
            text = re.sub(r"^[\*]*(지민|진행자\s*B|B|Host\s*B)[\*]*\s*[:\.]?\s*", "", line)
        else:
            # Continuation of previous speaker
            voice = current_voice
            text = line
            
        # Final cleanup of text
        text = text.replace("###", "").replace("**", "").strip()
        
        if text:
            temp_file = f"temp_{segment_index}.mp3"
            success = await generate_audio_segment(text, voice, temp_file)
            if success:
                temp_files.append(temp_file)
                print(f"세그먼트 {segment_index} 생성 완료: {text[:20]}...")
                segment_index += 1  # 성공한 경우에만 증가
            else:
                print(f"세그먼트 {segment_index} 생성 실패 (건너뜀)")

    # Validate that we have actual content to generate
    if not temp_files:
        print("❌ 오디오 생성 실패: 유효한 대본 세그먼트가 없습니다.")
        # Clean up title file if exists
        if has_title and os.path.exists(title_audio_file):
            os.remove(title_audio_file)
        return None
    
    # Combine files using pydub
    combined = AudioSegment.empty()
    
    # Add Title Announcer
    if has_title:
        try:
            title_segment = AudioSegment.from_mp3(title_audio_file)
            combined += title_segment
            combined += AudioSegment.silent(duration=500) 
            os.remove(title_audio_file)
        except Exception as e:
            print(f"Title merge error: {e}")

    # Add Opening Music if exists
    if os.path.exists("opening.mp3"):
        print("오프닝 음악 추가 중...")
        try:
            opening = AudioSegment.from_mp3("opening.mp3")
            combined += opening
        except Exception as e:
            print(f"Opening music error: {e}")
    else:
        print("오프닝 음악 파일(opening.mp3)이 없습니다.")

    for temp_file in temp_files:
        try:
            segment = AudioSegment.from_mp3(temp_file)
            combined += segment
            os.remove(temp_file)
        except Exception as e:
            print(f"Segment merge error: {e}")
            
    # Export
    combined.export(output_filename, format="mp3")
    print(f"✅ 팟캐스트 오디오 생성 완료 (총 {len(temp_files)}개 세그먼트): {output_filename}")
    return output_filename

def run_audio_generation(script, filename, title=None):
    return asyncio.run(create_podcast_audio(script, filename, title))

if __name__ == "__main__":
    # Test script
    test_script = """
    상현: 안녕하세요, 구글 클라우드 TTS 테스트입니다.
    지민: 와, 목소리가 훨씬 자연스러워졌네요!
    """
    run_audio_generation(test_script, "test_google_tts.mp3")
