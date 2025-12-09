import paramiko
import os
from dotenv import load_dotenv

# Load env
load_dotenv()

HOST = os.getenv("SFTP_HOST", "139.150.81.187")
PORT = int(os.getenv("SFTP_PORT", 22))
USER = os.getenv("SFTP_USER", "root")
PASSWORD = os.getenv("SFTP_PASSWORD")

# Paths
LOCAL_FILE = r"e:\AI\웹크롤러\templates\about.html"
REMOTE_FILE = "/root/flask-app/templates/about.html"

def update_and_restart():
    try:
        print(f"Connecting to {HOST}...")
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(HOST, PORT, USER, PASSWORD)
        
        # 1. Upload File
        sftp = client.open_sftp()
        print(f"Uploading {LOCAL_FILE} to {REMOTE_FILE}...")
        sftp.put(LOCAL_FILE, REMOTE_FILE)
        sftp.close()
        print("Upload successful!")
        
        # Verify file content
        print(f"Verifying content of {REMOTE_FILE}...")
        stdin, stdout, stderr = client.exec_command(f"grep 'Windows' {REMOTE_FILE}")
        grep_result = stdout.read().decode()
        if grep_result:
            print("✅ Verification Successful: Found 'Windows' in remote file.")
        else:
            print("❌ Verification Failed: 'Windows' NOT found in remote file.")
            # Check file timestamp
            stdin, stdout, stderr = client.exec_command(f"ls -l {REMOTE_FILE}")
            print(f"File info: {stdout.read().decode()}")

        # 2. Restart Server & Nginx
        restart_cmds = [
            "systemctl restart flask-app",
            "systemctl restart nginx"  # Force Nginx reload too
        ]
        
        print("Restarting server services (Flask + Nginx)...")
        for cmd in restart_cmds:
            stdin, stdout, stderr = client.exec_command(cmd)
            exit_status = stdout.channel.recv_exit_status()
            if exit_status == 0:
                print(f"✅ Command successful: {cmd}")
            else:
                print(f"⚠️ Command failed: {cmd} (Exit: {exit_status})")
                print(f"   Error: {stderr.read().decode()}")
                
        # Check active processes
        stdin, stdout, stderr = client.exec_command("ps aux | grep gunicorn")
        print("\nRunning Gunicorn processes:")
        print(stdout.read().decode())

        client.close()
        print("Done.")
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    update_and_restart()
