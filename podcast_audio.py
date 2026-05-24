import edge_tts
import asyncio
import os
import fcntl
import subprocess
from pydub import AudioSegment
import re

# 영상 생성기와 공유하는 Edge TTS 호출 lock (Microsoft IP rate-limit 회피)
EDGE_GLOBAL_LOCK = "/tmp/sosig_edge_tts.lock"

# Voices (Microsoft Edge TTS - 무료, 폴백용)
# https://github.com/rany2/edge-tts
VOICE_A = "ko-KR-InJoonNeural"           # Male, Host A (상현) - Deep & Professional
VOICE_B = "ko-KR-SunHiNeural"            # Female, Host B (지민) - Soft & Clear
VOICE_ANNOUNCER = "ko-KR-HyunsuMultilingualNeural"  # Male, Title Announcer

# Edge TTS 호출 timeout (초). 네트워크 hiccup으로 무한 대기 방지.
TTS_TIMEOUT_SEC = 60

# ===== Supertonic 백엔드 (2026-05-17 도입) =====
# 환경변수 USE_EDGE_TTS=1 로 폴백 가능. 기본은 Supertonic.
USE_SUPERTONIC = os.getenv("USE_EDGE_TTS", "0") != "1"
_supertonic_tts = None
_supertonic_styles = {}

# Edge TTS voice → Supertonic voice style 매핑
_SUPERTONIC_VOICE_MAP = {
    VOICE_A:         "M1",  # 상현 (남성)
    VOICE_B:         "F1",  # 지민 (여성)
    VOICE_ANNOUNCER: "M2",  # 제목 announcer (다른 남성)
}


def _supertonic_load():
    """모듈 레벨 TTS 인스턴스 캐시 — 매 호출마다 9초 cold load 회피"""
    global _supertonic_tts
    if _supertonic_tts is None:
        from supertonic import TTS
        _supertonic_tts = TTS(auto_download=True)
    return _supertonic_tts


def _supertonic_style(voice_name):
    if voice_name not in _supertonic_styles:
        tts = _supertonic_load()
        # voice_name이 Edge TTS 이름(ko-KR-...)이면 매핑에서 Supertonic id로,
        # 이미 Supertonic id(M1~M5, F1~F5)면 그대로 사용
        st_name = _SUPERTONIC_VOICE_MAP.get(voice_name, voice_name)
        _supertonic_styles[voice_name] = tts.get_voice_style(voice_name=st_name)
    return _supertonic_styles[voice_name]


def _supertonic_segment(text, voice_name, output_file, speed=None):
    """Supertonic으로 WAV 생성 → ffmpeg로 mp3 변환 (호출자 호환).

    speed: 발화 속도 배수. None이면 환경변수 SUPERTONIC_SPEED 또는 기본 1.05.
    """
    if speed is None:
        speed = float(os.environ.get("SUPERTONIC_SPEED", "1.05"))
    try:
        tts = _supertonic_load()
        style = _supertonic_style(voice_name)
        wav, dur = tts.synthesize(
            text=text, lang="ko", voice_style=style,
            total_steps=8, speed=speed,
        )
        wav_tmp = output_file + ".tmp.wav"
        tts.save_audio(wav, wav_tmp)
        subprocess.run(
            ["ffmpeg", "-y", "-loglevel", "error", "-i", wav_tmp,
             "-c:a", "libmp3lame", "-b:a", "128k", output_file],
            check=True, timeout=30,
        )
        os.remove(wav_tmp)
        return True
    except Exception as e:
        print(f"❌ Supertonic 합성 실패: {e}")
        return False

# ===== FFmpeg 경로 설정 =====
# 우선순위: FFMPEG_PATH 환경변수 > 프로젝트 로컬 ffmpeg(.exe) > 시스템 PATH
import platform

current_dir = os.path.dirname(os.path.abspath(__file__))
_env_ffmpeg = os.getenv("FFMPEG_PATH", "")
_local_candidates = [
    os.path.join(current_dir, "ffmpeg"),
    os.path.join(current_dir, "ffmpeg.exe"),
]
_local_ffmpeg = next((p for p in _local_candidates if os.path.exists(p)), None)

if _env_ffmpeg and os.path.exists(_env_ffmpeg):
    print(f"Using FFmpeg from FFMPEG_PATH: {_env_ffmpeg}")
    AudioSegment.converter = _env_ffmpeg
    AudioSegment.ffmpeg = _env_ffmpeg
    os.environ["PATH"] += os.pathsep + os.path.dirname(_env_ffmpeg)
elif _local_ffmpeg:
    print(f"Using local FFmpeg: {_local_ffmpeg}")
    AudioSegment.converter = _local_ffmpeg
    AudioSegment.ffmpeg = _local_ffmpeg
    os.environ["PATH"] += os.pathsep + current_dir
else:
    print(f"Using system FFmpeg from PATH ({platform.system()})")


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
        communicate = edge_tts.Communicate(text, voice_name, rate="+15%")

        # 공유 lock으로 영상 생성기와 직렬화
        with open(EDGE_GLOBAL_LOCK, "w") as lockf:
            fcntl.flock(lockf, fcntl.LOCK_EX)
            await asyncio.wait_for(communicate.save(output_file), timeout=TTS_TIMEOUT_SEC)

        return True

    except asyncio.TimeoutError:
        print(f"❌ TTS timeout ({TTS_TIMEOUT_SEC}s) — Edge TTS 응답 없음")
        if os.path.exists(output_file):
            try:
                os.remove(output_file)
            except Exception:
                pass
        return False
    except Exception as e:
        print(f"❌ TTS 오류: {e}")
        return False


def generate_audio_segment(text, voice_name, output_file):
    """
    TTS 합성 — 기본 Supertonic, 실패 시 Edge TTS 폴백.
    USE_EDGE_TTS=1 환경변수면 Edge TTS 우선.
    """
    text = text.replace("*", "").strip()
    if not text:
        return False

    # 1) Supertonic 시도 (기본)
    if USE_SUPERTONIC:
        if _supertonic_segment(text, voice_name, output_file):
            return True
        print("  ↩️ Edge TTS로 폴백")

    # 2) Edge TTS (폴백 또는 강제)
    try:
        async def _generate():
            communicate = edge_tts.Communicate(text, voice_name, rate="+15%")
            with open(EDGE_GLOBAL_LOCK, "w") as lockf:
                fcntl.flock(lockf, fcntl.LOCK_EX)
                await asyncio.wait_for(communicate.save(output_file), timeout=TTS_TIMEOUT_SEC)
            return True

        return asyncio.run(_generate())
    except asyncio.TimeoutError:
        print(f"❌ TTS timeout ({TTS_TIMEOUT_SEC}s) — Edge TTS 응답 없음")
        if os.path.exists(output_file):
            try:
                os.remove(output_file)
            except Exception:
                pass
        return False
    except Exception as e:
        print(f"❌ TTS 오류: {e}")
        return False


def create_podcast_audio(script_text, output_filename="podcast.mp3", title_text=None,
                         voice_a=None, voice_b=None,
                         host_name="상현", analyst_name="지민"):
    """
    Parses the script and generates a combined MP3 file with title and opening music.

    voice_a/voice_b: Edge TTS voice name. None → 기본(상현·지민). Supertonic 매핑은
    _SUPERTONIC_VOICE_MAP 기반. 새 화자(M3/F3 등)는 매핑 dict가 자동으로 처리.
    host_name/analyst_name: 대본 파싱용 화자 이름.
    """
    if voice_a is None:
        voice_a = VOICE_A
    if voice_b is None:
        voice_b = VOICE_B

    lines = script_text.split('\n')
    temp_files = []

    # 동적 화자명 매칭 정규식 (re.escape로 안전)
    host_pat = re.compile(rf"^(?:{re.escape(host_name)}|진행자\s*A|A\s*[:\.]|Host\s*A)", re.IGNORECASE)
    analyst_pat = re.compile(rf"^(?:{re.escape(analyst_name)}|진행자\s*B|B\s*[:\.]|Host\s*B)", re.IGNORECASE)
    host_strip = re.compile(rf"^[\*]*(?:{re.escape(host_name)}|진행자\s*A|A|Host\s*A)[\*]*\s*[:\.]?\s*", re.IGNORECASE)
    analyst_strip = re.compile(rf"^[\*]*(?:{re.escape(analyst_name)}|진행자\s*B|B|Host\s*B)[\*]*\s*[:\.]?\s*", re.IGNORECASE)

    print(f"오디오 생성 시작 ({host_name}/{analyst_name}): {output_filename}")

    try:
        # 1. Generate Title Audio (if title provided)
        title_audio_file = "temp_title.mp3"
        has_title = False
        if title_text:
            print(f"제목 오디오 생성 중: {title_text}")
            # Clean title for TTS
            clean_title = title_text.replace("[", "").replace("]", "").strip()
            intro_text = f"{clean_title}."
            if generate_audio_segment(intro_text, VOICE_ANNOUNCER, title_audio_file):
                has_title = True

        current_voice = voice_a  # Default start
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

            # Parse host/analyst 발화
            if host_pat.search(line):
                voice = voice_a
                current_voice = voice_a
                text = host_strip.sub("", line)
            elif analyst_pat.search(line):
                voice = voice_b
                current_voice = voice_b
                text = analyst_strip.sub("", line)
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
        
        # 공통 부품 미리 로드
        title_segment = None
        if has_title:
            try:
                title_segment = AudioSegment.from_mp3(title_audio_file)
                os.remove(title_audio_file)
            except Exception as e:
                print(f"Title load error: {e}")

        script_dir = os.path.dirname(os.path.abspath(__file__))
        opening_path = os.path.join(script_dir, "opening.mp3")
        opening_segment = None
        if os.path.exists(opening_path):
            try:
                opening_segment = AudioSegment.from_mp3(opening_path)
            except Exception as e:
                print(f"Opening load error: {e}")
        else:
            print(f"오프닝 음악 파일이 없습니다: {opening_path}")

        body_segments = []
        for temp_file in temp_files:
            try:
                body_segments.append(AudioSegment.from_mp3(temp_file))
            except Exception as e:
                print(f"Segment load error ({temp_file}): {e}")

        def _assemble(include_opening: bool) -> AudioSegment:
            out = AudioSegment.empty()
            if title_segment is not None:
                out += title_segment + AudioSegment.silent(duration=500)
            if include_opening and opening_segment is not None:
                out += opening_segment
            for seg in body_segments:
                out += seg
            return out

        # 1) intro 버전 (오프닝 포함, 기존 호환)
        combined_intro = _assemble(include_opening=True)
        combined_intro.export(output_filename, format="mp3")

        try:
            file_size = os.path.getsize(output_filename)
            file_size_mb = file_size / (1024 * 1024)
            if file_size < 1048576:
                print(f"❌ 파일 크기 부족: {file_size_mb:.2f}MB (최소 1MB 필요)")
                print(f"   생성된 파일 삭제: {output_filename}")
                os.remove(output_filename)
                return None
            print(f"✅ 팟캐스트 오디오 생성 완료 (크기: {file_size_mb:.2f}MB, 세그먼트: {len(temp_files)}개): {output_filename}")
        except Exception as e:
            print(f"❌ 파일 크기 확인 중 오류: {e}")
            return None

        # 2) clean 버전 (오프닝 없음, 모음 합치기용)
        clean_filename = output_filename[:-4] + "_clean.mp3" if output_filename.endswith(".mp3") else output_filename + "_clean.mp3"
        try:
            combined_clean = _assemble(include_opening=False)
            combined_clean.export(clean_filename, format="mp3")
            clean_size = os.path.getsize(clean_filename)
            if clean_size < 524288:  # 0.5MB 미만이면 비정상으로 판단
                print(f"⚠️ clean 파일 크기 부족: {clean_size/1024/1024:.2f}MB → 삭제 (intro 파일은 유지)")
                os.remove(clean_filename)
            else:
                print(f"✅ clean 버전 생성 완료 ({clean_size/1024/1024:.2f}MB): {clean_filename}")
        except Exception as e:
            print(f"⚠️ clean 버전 생성 실패 (intro 파일은 유지): {e}")
            try:
                if os.path.exists(clean_filename):
                    os.remove(clean_filename)
            except Exception:
                pass

        return output_filename
        
    finally:
        # 임시 파일 정리 (항상 실행)
        for temp_file in temp_files:
            if os.path.exists(temp_file):
                try:
                    os.remove(temp_file)
                except Exception as e:
                    print(f"임시 파일 삭제 실패 ({temp_file}): {e}")


def run_audio_generation(script, filename, title=None,
                         voice_a=None, voice_b=None,
                         host_name="상현", analyst_name="지민"):
    return create_podcast_audio(
        script, filename, title,
        voice_a=voice_a, voice_b=voice_b,
        host_name=host_name, analyst_name=analyst_name,
    )


if __name__ == "__main__":
    # Test script
    test_script = """
    상현: 안녕하세요, Edge TTS 테스트입니다. 완전 무료로 사용할 수 있어요!
    지민: 와, 정말요? 음질도 상당히 좋네요!
    """
    run_audio_generation(test_script, "test_edge_tts.mp3")
