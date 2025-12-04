"""
잘못 생성된 팟캐스트 파일 정리 스크립트
- opening 음악만 있는 파일을 DB와 SFTP 서버에서 삭제
- 파일 길이가 30초 미만인 경우 opening만 있다고 판단
"""

import db_manager
import paramiko
import requests
import time
import os
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

# SFTP 설정
SFTP_HOST = os.getenv("SFTP_HOST", "")
SFTP_PORT = int(os.getenv("SFTP_PORT", "22"))
SFTP_USER = os.getenv("SFTP_USER", "")
SFTP_PASS = os.getenv("SFTP_PASSWORD", "")

def get_audio_duration_from_url(url):
    """
    URL에서 MP3 파일을 다운로드하여 길이를 확인
    """
    try:
        # MP3 헤더만 가져와서 길이 추정
        response = requests.head(url, timeout=5)
        if response.status_code != 200:
            return None
        
        # 파일 크기로 대략적인 길이 추정
        # 128kbps MP3 기준: 1MB ≈ 60초
        file_size_mb = int(response.headers.get('Content-Length', 0)) / 1024 / 1024
        estimated_duration = file_size_mb * 60
        
        return estimated_duration
    except Exception as e:
        print(f"   길이 확인 실패: {e}")
        return None

def delete_file_from_sftp(remote_path):
    """
    SFTP 서버에서 파일 삭제
    """
    try:
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(SFTP_HOST, SFTP_PORT, SFTP_USER, SFTP_PASS, timeout=10)
        sftp = client.open_sftp()
        
        sftp.remove(remote_path)
        
        sftp.close()
        client.close()
        return True
    except Exception as e:
        print(f"   SFTP 삭제 실패: {e}")
        return False

def cleanup_invalid_podcasts(min_duration_seconds=30, dry_run=True):
    """
    잘못된 팟캐스트 파일 정리
    
    Args:
        min_duration_seconds: 최소 파일 길이 (초). 이보다 짧으면 삭제 대상
        dry_run: True면 실제 삭제 없이 목록만 출력
    """
    print("=" * 70)
    print("🧹 잘못된 팟캐스트 파일 정리 스크립트")
    print("=" * 70)
    print(f"설정: 최소 길이 {min_duration_seconds}초 미만 파일을 삭제 대상으로 간주")
    print(f"모드: {'[DRY RUN] 실제 삭제 안 함' if dry_run else '[LIVE] 실제 삭제 실행'}")
    print()
    
    # DB에서 모든 에피소드 가져오기
    conn = db_manager.get_connection()
    cursor = conn.cursor()
    
    # 최근 7일 에피소드만 체크 (안전장치)
    query = """
    SELECT id, title, press, link, mp3_path, created_at 
    FROM episodes 
    WHERE created_at >= DATE_SUB(NOW(), INTERVAL 7 DAY)
    ORDER BY created_at DESC
    """
    
    cursor.execute(query)
    episodes = cursor.fetchall()
    
    print(f"📊 총 {len(episodes)}개 에피소드 검사 중...\n")
    
    invalid_episodes = []
    
    for episode in episodes:
        ep_id = episode['id']
        title = episode['title']
        mp3_path = episode['mp3_path']
        created_at = episode['created_at']
        
        print(f"[{ep_id}] {title[:40]}...")
        print(f"   생성 시간: {created_at}")
        
        # 오디오 경로가 없으면 건너뛰기
        if not mp3_path:
            print("   ⚠️ 오디오 경로 없음 (건너뜀)")
            continue
        
        # 전체 URL 생성
        if mp3_path.startswith('/'):
            full_url = f"https://sosig.shop{mp3_path}"
        else:
            full_url = mp3_path
        
        # 파일 길이 확인
        duration = get_audio_duration_from_url(full_url)
        
        if duration is None:
            print("   ⚠️ 파일 길이 확인 불가 (건너뜀)")
            continue
        
        print(f"   예상 길이: {duration:.1f}초")
        
        # 너무 짧은 파일 = opening만 있음
        if duration < min_duration_seconds:
            print(f"   ❌ 삭제 대상! ({duration:.1f}초 < {min_duration_seconds}초)")
            invalid_episodes.append({
                'id': ep_id,
                'title': title,
                'mp3_path': mp3_path,
                'duration': duration
            })
        else:
            print(f"   ✅ 정상 파일")
        
        print()
        time.sleep(0.5)  # Rate limiting
    
    # 삭제 요약
    print("=" * 70)
    print(f"🗑️ 삭제 대상: {len(invalid_episodes)}개")
    print("=" * 70)
    
    if len(invalid_episodes) == 0:
        print("✅ 삭제할 파일이 없습니다!")
        conn.close()
        return
    
    for ep in invalid_episodes:
        print(f"• [{ep['id']}] {ep['title'][:50]} ({ep['duration']:.1f}초)")
    
    print()
    
    if dry_run:
        print("⚠️ DRY RUN 모드: 실제 삭제하지 않았습니다.")
        print("실제로 삭제하려면 dry_run=False로 실행하세요.")
    else:
        confirm = input(f"\n정말로 {len(invalid_episodes)}개 파일을 삭제하시겠습니까? (yes/no): ")
        
        if confirm.lower() != 'yes':
            print("❌ 취소되었습니다.")
            conn.close()
            return
        
        print("\n🗑️ 삭제 시작...")
        deleted_count = 0
        
        for ep in invalid_episodes:
            print(f"\n[{ep['id']}] {ep['title'][:40]}...")
            
            # 1. SFTP에서 파일 삭제
            remote_path = ep['mp3_path']
            if delete_file_from_sftp(remote_path):
                print(f"   ✅ SFTP 파일 삭제 완료: {remote_path}")
            else:
                print(f"   ⚠️ SFTP 파일 삭제 실패 (계속 진행)")
            
            # 2. DB에서 레코드 삭제
            try:
                delete_query = "DELETE FROM episodes WHERE id = %s"
                cursor.execute(delete_query, (ep['id'],))
                conn.commit()
                print(f"   ✅ DB 레코드 삭제 완료")
                deleted_count += 1
            except Exception as e:
                print(f"   ❌ DB 삭제 실패: {e}")
                conn.rollback()
        
        print("\n" + "=" * 70)
        print(f"✅ 정리 완료! {deleted_count}/{len(invalid_episodes)}개 삭제됨")
        print("=" * 70)
    
    conn.close()

if __name__ == "__main__":
    import sys
    
    # 인자로 dry_run 모드 조절
    dry_run = True
    if len(sys.argv) > 1 and sys.argv[1] == "--delete":
        dry_run = False
    
    cleanup_invalid_podcasts(min_duration_seconds=30, dry_run=dry_run)
