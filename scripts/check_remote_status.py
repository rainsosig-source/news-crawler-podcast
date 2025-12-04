import paramiko
import os
from dotenv import load_dotenv

load_dotenv()

# Server Configuration
HOST = os.getenv("SFTP_HOST", "")
PORT = int(os.getenv("SFTP_PORT", "22"))
USERNAME = os.getenv("SFTP_USER", "")
PASSWORD = os.getenv("SFTP_PASSWORD", "")

def check_status():
    print(f"Connecting to {HOST}...")
    try:
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(HOST, PORT, USERNAME, PASSWORD)
        
        print("\n--- 1. Checking about.html ---")
        stdin, stdout, stderr = client.exec_command("ls -l /root/flask-app/templates/about.html")
        print(stdout.read().decode())
        
        print("\n--- 2. Checking Running Processes (Gunicorn) ---")
        stdin, stdout, stderr = client.exec_command("ps aux | grep gunicorn")
        print(stdout.read().decode())

        print("\n--- 3. Checking Systemd Services ---")
        stdin, stdout, stderr = client.exec_command("systemctl list-units --type=service --all | grep flask")
        print(stdout.read().decode())
        
        print("\n--- 4. Checking Nginx Status ---")
        stdin, stdout, stderr = client.exec_command("systemctl status nginx")
        print(stdout.read().decode())

        client.close()
        
    except Exception as e:
        print(f"❌ Connection Error: {e}")

if __name__ == "__main__":
    check_status()
