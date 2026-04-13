import paramiko
import os
import time
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Server Configuration (from environment variables)
HOST = os.getenv("SFTP_HOST", "")
PORT = int(os.getenv("SFTP_PORT", "22"))
USERNAME = os.getenv("SFTP_USER", "")
PASSWORD = os.getenv("SFTP_PASSWORD", "")
KEY_FILE = os.getenv("SFTP_KEY_FILE", "")
# Flask static folder
REMOTE_DIR = "/root/flask-app/static/podcast" 
WEB_URL = "https://sosig.shop/podcast"

def create_remote_dir(sftp, path):
    """Recursively creates remote directories."""
    dirs = path.split("/")
    current_path = ""
    for d in dirs:
        if not d: continue
        current_path += "/" + d
        try:
            sftp.stat(current_path)
        except FileNotFoundError:
            # print(f"Creating remote directory: {current_path}")
            try:
                sftp.mkdir(current_path)
            except: pass

def upload_file(local_path):
    """Uploads a file to the Flask server's static folder."""
    
    # 환경변수 유효성 검사
    if not HOST or not USERNAME or not PASSWORD:
        print("❌ SFTP 설정이 누락되었습니다. .env 파일을 확인하세요.")
        print(f"   HOST: {'설정됨' if HOST else '미설정'}")
        print(f"   USERNAME: {'설정됨' if USERNAME else '미설정'}")
        print(f"   PASSWORD: {'설정됨' if PASSWORD else '미설정'}")
        return None
    
    # Generate timestamp for folder and filename
    now = datetime.now()
    year = now.strftime("%Y")
    month = now.strftime("%m")
    day = now.strftime("%d")
    time_str = now.strftime("%H-%M-%S")
    
    remote_filename = f"{time_str}.mp3"
    
    # Add index if present
    try:
        idx = local_path.split("_")[-1].replace(".mp3", "")
        if idx.isdigit():
            remote_filename = f"{time_str}_{idx}.mp3"
    except:
        pass

    remote_folder = f"{REMOTE_DIR}/{year}/{month}/{day}"
    remote_path = f"{remote_folder}/{remote_filename}"

    # 재시도: 최대 3회, 지수 백오프 (3s → 9s → 27s)
    max_attempts = 3
    for attempt in range(1, max_attempts + 1):
        client = None
        sftp = None
        try:
            client = paramiko.SSHClient()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            # password 전용 인증으로 강제.
            # paramiko 기본값(look_for_keys/allow_agent=True)으로 두면
            # ~/.ssh 키나 agent 키를 먼저 시도하다가 서버의
            # PubkeyAcceptedAlgorithms(ssh-rsa 제외) 정책에 막혀
            # password fallback 없이 실패하는 문제가 있음.
            if KEY_FILE and os.path.exists(KEY_FILE):
                client.connect(
                    HOST, PORT, USERNAME,
                    key_filename=KEY_FILE,
                    timeout=30, banner_timeout=30,
                    allow_agent=False, look_for_keys=False,
                )
            else:
                client.connect(
                    HOST, PORT, USERNAME, PASSWORD,
                    timeout=30, banner_timeout=30,
                    allow_agent=False, look_for_keys=False,
                )
            sftp = client.open_sftp()

            create_remote_dir(sftp, remote_folder)

            print(f"Uploading to {remote_path}... (시도 {attempt}/{max_attempts})")
            sftp.put(local_path, remote_path)
            print("Upload successful.")
            print(f"Web Player Updated: {WEB_URL}")
            return remote_path

        except Exception as e:
            print(f"SFTP Upload Error (시도 {attempt}/{max_attempts}): {e}")
            if attempt < max_attempts:
                backoff = 3 ** attempt
                print(f"  {backoff}초 후 재시도...")
                time.sleep(backoff)
        finally:
            try:
                if sftp: sftp.close()
                if client: client.close()
            except Exception:
                pass

    print(f"❌ SFTP 업로드 최종 실패 ({max_attempts}회 시도)")
    return None

if __name__ == "__main__":
    # Test upload if run directly
    with open("test_audio.mp3", "w") as f:
        f.write("dummy audio content")
    upload_file("test_audio.mp3")
    os.remove("test_audio.mp3")
