import paramiko
import os
from dotenv import load_dotenv

# Load env
load_dotenv()

HOST = os.getenv("SFTP_HOST", "139.150.81.187")
PORT = int(os.getenv("SFTP_PORT", 22))
USER = os.getenv("SFTP_USER", "root")
PASSWORD = os.getenv("SFTP_PASSWORD")

def diagnose_server():
    try:
        print(f"Connecting to {HOST}...")
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(HOST, PORT, USER, PASSWORD)
        
        print("\n=== 1. Check Running Python/Flask Processes ===")
        stdin, stdout, stderr = client.exec_command("ps aux | grep -E 'flask|gunicorn|python' | grep -v grep")
        print(stdout.read().decode())
        
        print("\n=== 2. Find all 'about.html' files ===")
        stdin, stdout, stderr = client.exec_command("find / -name 'about.html' 2>/dev/null")
        print(stdout.read().decode())
        
        print("\n=== 3. Check Current Directory of Running Process ===")
        # Get PID of gunicorn or python
        stdin, stdout, stderr = client.exec_command("pgrep -f 'gunicorn|flask|python' | head -n 1")
        pid = stdout.read().decode().strip()
        if pid:
            print(f"PID: {pid}")
            stdin, stdout, stderr = client.exec_command(f"ls -l /proc/{pid}/cwd")
            print(stdout.read().decode())
        else:
            print("No relevant process found.")

        print("\n=== 4. Check Nginx Config ===")
        stdin, stdout, stderr = client.exec_command("grep -r 'root' /etc/nginx/sites-enabled/")
        print(stdout.read().decode())
        stdin, stdout, stderr = client.exec_command("grep -r 'proxy_pass' /etc/nginx/sites-enabled/")
        print(stdout.read().decode())

        client.close()
        print("Diagnosis Done.")
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    diagnose_server()
