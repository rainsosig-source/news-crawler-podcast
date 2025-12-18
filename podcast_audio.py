import edge_tts
import asyncio
import os
from pydub import AudioSegment
import re

# Voices (Microsoft Edge TTS - 완전 무료)
# https://github.com/rany2/edge-tts
VOICE_A = "ko-KR-InJoonNeural"           # Male, Host A (상현) - Deep & Professional  
VOICE_B = "ko-KR-SunHiNeural"            # Female, Host B (지민) - Soft & Clear
VOICE_ANNOUNCER = "ko-KR-HyunsuMultilingualNeural"  # Male, Title Announcer

# ===== FFmpeg 경로 설정 =====
# SYSTEM 계정 스케줄러에서는 사용자 PATH를 상속받지 않으므로 절대 경로 필요
# 아래 경로를 실제 ffmpeg.exe 위치로 수정하세요
FFMPEG_SYSTEM_PATH = r"C:\ffmpeg\bin\ffmpeg.exe"  # TODO: 실제 경로로 수정

current_dir = os.path.dirname(os.path.abspath(__file__))
local_ffmpeg = os.path.join(current_dir, "ffmpeg.exe")

if os.path.exists(local_ffmpeg):
    # 프로젝트 폴더에 ffmpeg.exe가 있는 경우
    print(f"Using local FFmpeg: {local_ffmpeg}")
    AudioSegment.converter = local_ffmpeg
    AudioSegment.ffmpeg = local_ffmpeg
    os.environ["PATH"] += os.pathsep + current_dir
elif os.path.exists(FFMPEG_SYSTEM_PATH):
    # 시스템에 설치된 ffmpeg 사용 (스케줄러 SYSTEM 계정용)
    print(f"Using system FFmpeg: {FFMPEG_SYSTEM_PATH}")
    AudioSegment.converter = FFMPEG_SYSTEM_PATH
    AudioSegment.ffmpeg = FFMPEG_SYSTEM_PATH
    os.environ["PATH"] += os.pathsep + os.path.dirname(FFMPEG_SYSTEM_PATH)
else:
    # Cloud/Linux 환경 또는 PATH에서 ffmpeg 찾기
    print("Using system FFmpeg (from PATH or Cloud/Linux environment)")


async def generate_audio_segment_async(text, voice_name, output_file):
    """
    Generates audio using Microsoft Edge TTS (completely free).
    """
    try:
        # Clean up text
        text = text.replace("*", "").strip()
        if not text:
            return False

        # Create TTS communicate object
        communicate = edge_tts.Communicate(text, voice_name, rate="+10%")
        
        # Save to file
        await communicate.save(output_file)
        
        return True

    except Exception as e:
        print(f"❌ TTS 오류: {e}")
        return False


def generate_audio_segment(text, voice_name, output_file):
    """
    Sync wrapper for async TTS generation.
    """
    try:
        # Clean up text
        text = text.replace("*", "").strip()
        if not text:
            return False

        # Use asyncio.run for cleaner event loop handling
        async def _generate():
            communicate = edge_tts.Communicate(text, voice_name, rate="+10%")
            await communicate.save(output_file)
            return True
        
        return asyncio.run(_generate())
    except Exception as e:
        print(f"❌ TTS 오류: {e}")
        return False


def create_podcast_audio(script_text, output_filename="podcast.mp3", title_text=None):
    """
    Parses the script and generates a combined MP3 file with title and opening music.
    """
    lines = script_text.split('\n')
    temp_files = []
    
    print(f"오디오 생성 시작 (Edge TTS - 무료): {output_filename}")
    
    try:
        # 1. Generate Title Audio (if title provided)
        title_audio_file = "temp_title.mp3"
        has_title = False
        if title_text:
            print(f"제목 오디오 생성 중: {title_text}")
            # Clean title for TTS
            clean_title = title_text.replace("[", "").replace("]", "").strip()
            intro_text = f"오늘의 뉴스. {clean_title}."
            if generate_audio_segment(intro_text, VOICE_ANNOUNCER, title_audio_file):
                has_title = True
        
        current_voice = VOICE_A  # Default start
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
                success = generate_audio_segment(text, voice, temp_file)
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

        # Add Opening Music if exists (절대 경로 사용)
        script_dir = os.path.dirname(os.path.abspath(__file__))
        opening_path = os.path.join(script_dir, "opening.mp3")
        
        if os.path.exists(opening_path):
            print(f"오프닝 음악 추가 중: {opening_path}")
            try:
                opening = AudioSegment.from_mp3(opening_path)
                combined += opening
            except Exception as e:
                print(f"Opening music error: {e}")
        else:
            print(f"오프닝 음악 파일이 없습니다: {opening_path}")

        # Merge segments with error handling
        for temp_file in temp_files:
            try:
                segment = AudioSegment.from_mp3(temp_file)
                combined += segment
            except Exception as e:
                print(f"Segment merge error ({temp_file}): {e}")
                
        # Export
        combined.export(output_filename, format="mp3")
        
        # ✅ 파일 크기 검증 (1MB 최소 기준)
        try:
            file_size = os.path.getsize(output_filename)
            file_size_mb = file_size / (1024 * 1024)
            
            if file_size < 1048576:  # 1MB = 1048576 bytes
                print(f"❌ 파일 크기 부족: {file_size_mb:.2f}MB (최소 1MB 필요)")
                print(f"   생성된 파일 삭제: {output_filename}")
                os.remove(output_filename)
                return None
            
            print(f"✅ 팟캐스트 오디오 생성 완료 (크기: {file_size_mb:.2f}MB, 세그먼트: {len(temp_files)}개): {output_filename}")
        except Exception as e:
            print(f"❌ 파일 크기 확인 중 오류: {e}")
            return None
            
        return output_filename
        
    finally:
        # 임시 파일 정리 (항상 실행)
        for temp_file in temp_files:
            if os.path.exists(temp_file):
                try:
                    os.remove(temp_file)
                except Exception as e:
                    print(f"임시 파일 삭제 실패 ({temp_file}): {e}")


def run_audio_generation(script, filename, title=None):
    return create_podcast_audio(script, filename, title)


if __name__ == "__main__":
    # Test script
    test_script = """
    상현: 안녕하세요, Edge TTS 테스트입니다. 완전 무료로 사용할 수 있어요!
    지민: 와, 정말요? 음질도 상당히 좋네요!
    """
    run_audio_generation(test_script, "test_edge_tts.mp3")
