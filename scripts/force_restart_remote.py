import paramiko
import os
from dotenv import load_dotenv

load_dotenv()

# Server Configuration
HOST = os.getenv("SFTP_HOST", "")
PORT = int(os.getenv("SFTP_PORT", "22"))
USERNAME = os.getenv("SFTP_USER", "")
PASSWORD = os.getenv("SFTP_PASSWORD", "")

def force_restart():
    print(f"Connecting to {HOST}...")
    try:
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(HOST, PORT, USERNAME, PASSWORD)
        
        print("\n--- 1. Restarting Nginx ---")
        client.exec_command("systemctl restart nginx")
        print("Nginx restarted.")
        
        print("\n--- 2. Finding Python/Gunicorn Processes ---")
        stdin, stdout, stderr = client.exec_command("ps aux | grep python")
        print(stdout.read().decode())
        
        print("\n--- 3. Killing Gunicorn (if exists) ---")
        # Be careful not to kill system processes, but here we assume root's python apps are the target
        stdin, stdout, stderr = client.exec_command("pkill -f gunicorn")
        print("Sent kill signal to Gunicorn.")
        
        print("\n--- 4. Starting Gunicorn (Manual Start) ---")
        # Assuming we are in /root/flask-app and using venv or system python
        # This is a bit risky if we don't know the exact start command.
        # Let's first check if there's a start script.
        stdin, stdout, stderr = client.exec_command("ls -l /root/flask-app/")
        print(stdout.read().decode())

        client.close()
        
    except Exception as e:
        print(f"❌ Connection Error: {e}")

if __name__ == "__main__":
    force_restart()
