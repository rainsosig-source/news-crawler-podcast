import paramiko
import time
import os
from dotenv import load_dotenv

load_dotenv()

# Server Configuration
HOST = os.getenv("SFTP_HOST", "")
PORT = int(os.getenv("SFTP_PORT", "22"))
USERNAME = os.getenv("SFTP_USER", "")
PASSWORD = os.getenv("SFTP_PASSWORD", "")

def restart_app_manually():
    print(f"Connecting to {HOST}...")
    try:
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(HOST, PORT, USERNAME, PASSWORD)
        
        print("\n--- 1. Killing existing app.py ---")
        client.exec_command("pkill -f 'python -u /root/flask-app/app.py'")
        time.sleep(2) # Wait for it to die
        
        print("\n--- 2. Starting app.py in background ---")
        # Using nohup to keep it running after disconnect
        # Assuming python3 is available and venv is at /root/flask-app/venv
        start_cmd = "nohup /root/flask-app/venv/bin/python -u /root/flask-app/app.py > /root/flask-app/app.log 2>&1 &"
        stdin, stdout, stderr = client.exec_command(start_cmd)
        
        print("App started. Checking process...")
        time.sleep(2)
        stdin, stdout, stderr = client.exec_command("ps aux | grep app.py")
        print(stdout.read().decode())

        client.close()
        return True
        
    except Exception as e:
        print(f"❌ Connection Error: {e}")
        return False

if __name__ == "__main__":
    restart_app_manually()
