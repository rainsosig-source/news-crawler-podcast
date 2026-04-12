"""
SFTP 서버에 업로드된 파일 확인
"""
import paramiko
import os
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

# SFTP 설정
HOST = os.getenv("SFTP_HOST", "")
PORT = int(os.getenv("SFTP_PORT", "22"))
USERNAME = os.getenv("SFTP_USER", "")
PASSWORD = os.getenv("SFTP_PASSWORD", "")
REMOTE_DIR = "/root/flask-app/static/podcast"

def check_uploaded_files():
    """오늘 날짜 폴더의 파일 목록 확인"""
    
    try:
        # SSH 연결
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(HOST, PORT, USERNAME, PASSWORD, timeout=10)
        sftp = client.open_sftp()
        
        # 오늘 날짜 경로
        now = datetime.now()
        year = now.strftime("%Y")
        month = now.strftime("%m")
        day = now.strftime("%d")
        today_path = f"{REMOTE_DIR}/{year}/{month}/{day}"
        
        print("=" * 70)
        print(f"📂 원격 디렉토리: {today_path}")
        print("=" * 70)
        
        try:
            files = sftp.listdir(today_path)
            
            if not files:
                print("\n⚠️  파일이 없습니다.")
            else:
                print(f"\n✅ 파일 {len(files)}개 발견:\n")
                
                for file in sorted(files):
                    file_path = f"{today_path}/{file}"
                    try:
                        stat = sftp.stat(file_path)
                        size = stat.st_size
                        mtime = datetime.fromtimestamp(stat.st_mtime)
                        
                        print(f"📄 {file}")
                        print(f"   크기: {size:,} bytes ({size/1024/1024:.2f} MB)")
                        print(f"   수정: {mtime.strftime('%Y-%m-%d %H:%M:%S')}")
                        print(f"   URL:  https://sosig.shop/static/podcast/{year}/{month}/{day}/{file}")
                        print()
                    except Exception as e:
                        print(f"   ⚠️  파일 정보 읽기 실패: {e}")
                        
        except FileNotFoundError:
            print(f"\n❌ 디렉토리를 찾을 수 없습니다: {today_path}")
            print("   아직 오늘 날짜로 업로드된 파일이 없습니다.")
        
        sftp.close()
        client.close()
        
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    check_uploaded_files()
    print("=" * 70)
