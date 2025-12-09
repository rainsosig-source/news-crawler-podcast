import paramiko
import os
import sys
from dotenv import load_dotenv
import time

# Load env variables
load_dotenv()

HOST = os.getenv("SFTP_HOST", "139.150.81.187")
PORT = int(os.getenv("SFTP_PORT", 22))
USER = os.getenv("SFTP_USER", "root")
PASSWORD = os.getenv("SFTP_PASSWORD")

LOCAL_FILE = r"e:\AI\웹크롤러\templates\about.html"
REMOTE_FILE = "/root/flask-app/templates/about.html"
CHECK_KEYWORD = "Windows Task Scheduler"

def force_deploy():
    print(f"🚀 Starting Force Deploy for {HOST}...")

    # 1. Verify Local File
    try:
        with open(LOCAL_FILE, 'r', encoding='utf-8') as f:
            content = f.read()
            if CHECK_KEYWORD not in content:
                print(f"❌ LOCAL CHECK FAILED: '{CHECK_KEYWORD}' not found in local file.")
                print("   Please check if the file edit was saved.")
                return
            print(f"✅ Local file verified ({len(content)} bytes).")
            
        # Prepare content for upload (binary)
        with open(LOCAL_FILE, 'rb') as f:
            content_bytes = f.read()
            
    except Exception as e:
        print(f"❌ Error reading local file: {e}")
        return

    # 2. Connect
    try:
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(HOST, PORT, USER, PASSWORD)
        print("✅ SSH Connected.")

        # 3. Force Upload via cat
        print(f"📤 Uploading via stream to {REMOTE_FILE}...")
        # First, remove existing file to avoid permission/lock weirdness
        client.exec_command(f"rm -f {REMOTE_FILE}")
        
        # Write new file
        stdin, stdout, stderr = client.exec_command(f"cat > {REMOTE_FILE}")
        stdin.write(content_bytes)
        stdin.channel.shutdown_write() # EOF
        
        exit_status = stdout.channel.recv_exit_status()
        if exit_status != 0:
            print(f"❌ Upload Failed! Exit code: {exit_status}")
            print(stderr.read().decode())
            return
            
        print("✅ Upload completed.")

        # 4. Verify Remote File
        print("🔍 Verifying remote content...")
        cmd = f"grep '{CHECK_KEYWORD}' {REMOTE_FILE}"
        stdin, stdout, stderr = client.exec_command(cmd)
        if stdout.read().decode().strip():
            print(f"✅ REMOTE VERIFY SUCCESS: Found '{CHECK_KEYWORD}' on server.")
        else:
            print(f"❌ REMOTE VERIFY FAILED: Keyword not found on server!")
            return

        # 5. Restart Services
        print("🔄 Restarting Services...")
        
        # Kill gunicorn just in case
        client.exec_command("pkill -9 -f gunicorn")
        
        # Restart Flask Service
        stdin, stdout, stderr = client.exec_command("systemctl restart flask-app")
        if stdout.channel.recv_exit_status() == 0:
            print("✅ Flask App Restarted.")
        else:
            print(f"⚠️ Flask Restart Failed: {stderr.read().decode()}")

        # Restart Nginx
        client.exec_command("systemctl restart nginx")
        print("✅ Nginx Restarted.")

        client.close()
        print("\n🎉 DEPLOY SUCCESS! Site should be updated now.")

    except Exception as e:
        print(f"❌ Critical Error: {e}")

if __name__ == "__main__":
    force_deploy()
