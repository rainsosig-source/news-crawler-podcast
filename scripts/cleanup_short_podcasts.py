"""
웹서버(SFTP)에서 1분 미만인 MP3 파일을 삭제하고 DB에서도 제거하는 스크립트
"""
import os
import paramiko
from dotenv import load_dotenv
import pymysql
from pydub import AudioSegment
import tempfile

load_dotenv()

# SFTP 설정
SFTP_HOST = os.getenv("SFTP_HOST", "")
SFTP_PORT = int(os.getenv("SFTP_PORT", "22"))
SFTP_USER = os.getenv("SFTP_USER", "")
SFTP_PASSWORD = os.getenv("SFTP_PASSWORD", "")
SFTP_REMOTE_DIR = "/root/flask-app/static/podcast"  # 수정된 경로

# DB 설정
DB_HOST = os.getenv("DB_HOST", "")
DB_USER = os.getenv("DB_USER", "")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")
DB_NAME = os.getenv("DB_NAME", "podcast")

def get_db_connection():
    return pymysql.connect(
        host=DB_HOST,
        user=DB_USER,
        password=DB_PASSWORD,
        db=DB_NAME,
        charset='utf8mb4',
        cursorclass=pymysql.cursors.DictCursor
    )

def get_mp3_duration(sftp, remote_path):
    """SFTP로 MP3 파일을 다운로드해서 길이를 확인"""
    tmp_path = None
    try:
        # 임시 파일 생성
        with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as tmp:
            tmp_path = tmp.name
            
        # SFTP에서 다운로드
        sftp.get(remote_path, tmp_path)
        
        # 파일 길이 확인
        audio = AudioSegment.from_mp3(tmp_path)
        duration_seconds = len(audio) / 1000  # milliseconds to seconds
        
        return duration_seconds
        
    except Exception as e:
        print(f"   ⚠️ 길이 확인 실패: {e}")
        return None
    finally:
        # 임시 파일 정리
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.unlink(tmp_path)
            except:
                pass

def cleanup_short_podcasts():
    """1분 미만인 팟캐스트 파일 삭제"""
    
    # SFTP 연결
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    try:
        print(f"🔗 SFTP 연결 중: {SFTP_HOST}")
        ssh.connect(SFTP_HOST, SFTP_PORT, SFTP_USER, SFTP_PASSWORD)
        sftp = ssh.open_sftp()
        
        # DB 연결
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 원격 디렉토리의 모든 MP3 파일 목록 (재귀적으로 검색)
        print(f"📂 디렉토리 확인: {SFTP_REMOTE_DIR}")
        
        mp3_files = []
        def list_recursive(path):
            """재귀적으로 MP3 파일 찾기"""
            try:
                for item in sftp.listdir_attr(path):
                    item_path = f"{path}/{item.filename}"
                    if item.st_mode & 0o040000:  # 디렉토리인 경우
                        list_recursive(item_path)
                    elif item.filename.endswith('.mp3'):
                        mp3_files.append(item_path)
            except Exception as e:
                print(f"   ⚠️ 경로 스캔 실패: {path} - {e}")
        
        list_recursive(SFTP_REMOTE_DIR)
        
        print(f"📊 총 {len(mp3_files)}개의 MP3 파일 발견")
        
        deleted_count = 0
        for remote_path in mp3_files:
            filename = os.path.basename(remote_path)
            
            # 파일 길이 확인
            duration = get_mp3_duration(sftp, remote_path)
            
            if duration is None:
                continue
                
            if duration < 60:  # 60초 = 1분
                print(f"\n🗑️ 삭제 대상: {filename} ({duration:.1f}초)")
                
                # DB에서 해당 파일 경로를 가진 레코드 찾기
                cursor.execute(
                    "SELECT id, title FROM episodes WHERE mp3_path LIKE %s",
                    (f"%{filename}%",)
                )
                episodes = cursor.fetchall()
                
                if episodes:
                    for episode in episodes:
                        print(f"   DB 삭제: ID={episode['id']}, 제목={episode['title'][:50]}")
                        cursor.execute("DELETE FROM episodes WHERE id = %s", (episode['id'],))
                    conn.commit()
                
                # SFTP에서 파일 삭제
                try:
                    sftp.remove(remote_path)
                    print(f"   ✅ 파일 삭제 완료: {filename}")
                    deleted_count += 1
                except Exception as e:
                    print(f"   ❌ 파일 삭제 실패: {e}")
            else:
                print(f"✓ 유지: {filename} ({duration:.1f}초)")
        
        print(f"\n{'='*60}")
        print(f"📊 작업 완료: {deleted_count}개 파일 삭제됨")
        print(f"{'='*60}")
        
        cursor.close()
        conn.close()
        sftp.close()
        ssh.close()
        
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        raise

if __name__ == "__main__":
    print("=" * 60)
    print("1분 미만 팟캐스트 파일 정리 시작")
    print("=" * 60)
    
    confirm = input("\n⚠️ 1분 미만인 모든 MP3 파일과 DB 레코드를 삭제합니다. 계속하시겠습니까? (yes/no): ")
    
    if confirm.lower() == 'yes':
        cleanup_short_podcasts()
    else:
        print("작업이 취소되었습니다.")
