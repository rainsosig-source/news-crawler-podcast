"""
SFTP 연결 테스트 스크립트
웹 서버로 파일 전송이 제대로 되는지 확인합니다.
"""
import paramiko
import os
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

# SFTP 설정 (환경변수에서 로드)
HOST = os.getenv("SFTP_HOST", "")
PORT = int(os.getenv("SFTP_PORT", "22"))
USERNAME = os.getenv("SFTP_USER", "")
PASSWORD = os.getenv("SFTP_PASSWORD", "")
REMOTE_DIR = "/root/flask-app/static/podcast"

def test_sftp_connection():
    """SFTP 서버 연결 테스트"""
    print("=" * 60)
    print("🔍 SFTP 연결 테스트 시작")
    print("=" * 60)
    
    try:
        print(f"\n1️⃣ 서버 연결 시도: {HOST}:{PORT}")
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(HOST, PORT, USERNAME, PASSWORD, timeout=10)
        print("   ✅ SSH 연결 성공")
        
        print(f"\n2️⃣ SFTP 세션 열기")
        sftp = client.open_sftp()
        print("   ✅ SFTP 세션 성공")
        
        print(f"\n3️⃣ 원격 디렉토리 확인: {REMOTE_DIR}")
        try:
            sftp.stat(REMOTE_DIR)
            print(f"   ✅ 디렉토리 존재: {REMOTE_DIR}")
        except FileNotFoundError:
            print(f"   ❌ 디렉토리 없음: {REMOTE_DIR}")
            return False
        
        print(f"\n4️⃣ 테스트 파일 업로드")
        # 테스트 파일 생성
        test_file = "test_upload.txt"
        test_content = f"테스트 업로드 - {datetime.now()}"
        with open(test_file, "w", encoding="utf-8") as f:
            f.write(test_content)
        
        # 오늘 날짜 기준 경로
        now = datetime.now()
        year = now.strftime("%Y")
        month = now.strftime("%m")
        day = now.strftime("%d")
        remote_test_path = f"{REMOTE_DIR}/{year}/{month}/{day}/test_upload.txt"
        
        # 디렉토리 생성
        remote_dir = f"{REMOTE_DIR}/{year}/{month}/{day}"
        create_remote_dir(sftp, remote_dir)
        
        # 파일 업로드
        print(f"   업로드 경로: {remote_test_path}")
        sftp.put(test_file, remote_test_path)
        print(f"   ✅ 파일 업로드 성공")
        
        print(f"\n5️⃣ 업로드 확인")
        try:
            file_stat = sftp.stat(remote_test_path)
            print(f"   ✅ 파일 확인됨 (크기: {file_stat.st_size} bytes)")
        except FileNotFoundError:
            print(f"   ❌ 업로드된 파일을 찾을 수 없음")
            return False
        
        print(f"\n6️⃣ 테스트 파일 삭제")
        sftp.remove(remote_test_path)
        os.remove(test_file)
        print(f"   ✅ 정리 완료")
        
        sftp.close()
        client.close()
        
        print("\n" + "=" * 60)
        print("✅ SFTP 연결 테스트 성공!")
        print("=" * 60)
        return True
        
    except paramiko.AuthenticationException:
        print("\n❌ 인증 실패: 사용자명 또는 비밀번호가 잘못되었습니다.")
        return False
    except paramiko.SSHException as e:
        print(f"\n❌ SSH 연결 실패: {e}")
        return False
    except Exception as e:
        print(f"\n❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        return False

def create_remote_dir(sftp, path):
    """원격 디렉토리 재귀 생성"""
    dirs = path.split("/")
    current_path = ""
    for d in dirs:
        if not d: 
            continue
        current_path += "/" + d
        try:
            sftp.stat(current_path)
        except FileNotFoundError:
            try:
                sftp.mkdir(current_path)
                print(f"   📁 디렉토리 생성: {current_path}")
            except:
                pass

def test_mp3_directory():
    """로컬 MP3 디렉토리 확인"""
    print("\n" + "=" * 60)
    print("📁 로컬 MP3 디렉토리 확인")
    print("=" * 60)
    
    mp3_dir = os.path.join(os.path.dirname(__file__), "MP3")
    
    if not os.path.exists(mp3_dir):
        print(f"❌ MP3 디렉토리가 없습니다: {mp3_dir}")
        return
    
    print(f"✅ MP3 디렉토리 존재: {mp3_dir}")
    
    # MP3 파일 목록
    mp3_files = [f for f in os.listdir(mp3_dir) if f.endswith('.mp3')]
    
    if not mp3_files:
        print("   ⚠️  MP3 파일이 없습니다.")
    else:
        print(f"   📄 MP3 파일 개수: {len(mp3_files)}")
        for i, file in enumerate(mp3_files[:5], 1):
            file_path = os.path.join(mp3_dir, file)
            size = os.path.getsize(file_path)
            print(f"   {i}. {file} ({size:,} bytes)")
        if len(mp3_files) > 5:
            print(f"   ... 외 {len(mp3_files) - 5}개 파일")

if __name__ == "__main__":
    print("\n🔬 SFTP 업로드 문제 진단 도구\n")
    
    # 1. 로컬 파일 확인
    test_mp3_directory()
    
    # 2. SFTP 연결 테스트
    input("\n⏎ Enter를 눌러 SFTP 연결 테스트를 시작하세요...")
    test_sftp_connection()
    
    print("\n✅ 모든 테스트 완료!")
