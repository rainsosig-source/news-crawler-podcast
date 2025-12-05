import paramiko
import os
from dotenv import load_dotenv

load_dotenv()

# Server Configuration (from environment variables)
HOST = os.getenv("SFTP_HOST", "")
PORT = int(os.getenv("SFTP_PORT", "22"))
USERNAME = os.getenv("SFTP_USER", "")
PASSWORD = os.getenv("SFTP_PASSWORD", "")

# Local and Remote paths
LOCAL_FILE = "templates/manager.html"
REMOTE_FILE = "/root/flask-app/templates/manager.html"

def upload_manager_page():
    print(f"Connecting to {HOST}...")
    try:
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(HOST, PORT, USERNAME, PASSWORD)
        sftp = client.open_sftp()
        
        print(f"Uploading {LOCAL_FILE} to {REMOTE_FILE}...")
        sftp.put(LOCAL_FILE, REMOTE_FILE)
        
        print("✅ Upload successful!")
        
        sftp.close()
        client.close()
        return True
        
    except Exception as e:
        print(f"❌ Upload Error: {e}")
        return False

if __name__ == "__main__":
    upload_manager_page()
