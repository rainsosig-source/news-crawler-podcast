import paramiko
import os
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Server Configuration (from environment variables)
HOST = os.getenv("SFTP_HOST", "")
PORT = int(os.getenv("SFTP_PORT", "22"))
USERNAME = os.getenv("SFTP_USER", "")
PASSWORD = os.getenv("SFTP_PASSWORD", "")
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
    
    try:
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(HOST, PORT, USERNAME, PASSWORD)
        sftp = client.open_sftp()
        
        # Ensure remote directory exists
        create_remote_dir(sftp, remote_folder)
        
        # Upload file
        remote_path = f"{remote_folder}/{remote_filename}"
        print(f"Uploading to {remote_path}...")
        sftp.put(local_path, remote_path)
        print("Upload successful.")
        
        # No need to update index.html anymore, Flask handles it dynamically.
        
        sftp.close()
        client.close()
        
        print(f"Web Player Updated: {WEB_URL}")
        return remote_path
        
    except Exception as e:
        print(f"SFTP Upload Error: {e}")
        return None

if __name__ == "__main__":
    # Test upload if run directly
    with open("test_audio.mp3", "w") as f:
        f.write("dummy audio content")
    upload_file("test_audio.mp3")
    os.remove("test_audio.mp3")
