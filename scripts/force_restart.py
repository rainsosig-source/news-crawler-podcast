import paramiko
import os
from dotenv import load_dotenv
import time

# Load env
load_dotenv()

HOST = os.getenv("SFTP_HOST", "139.150.81.187")
PORT = int(os.getenv("SFTP_PORT", 22))
USER = os.getenv("SFTP_USER", "root")
PASSWORD = os.getenv("SFTP_PASSWORD")

def force_restart():
    try:
        print(f"Connecting to {HOST}...")
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(HOST, PORT, USER, PASSWORD)
        
        # 1. Clear Python Cache
        print("Clearing Python __pycache__...")
        client.exec_command("find /root/flask-app -name '__pycache__' -type d -exec rm -rf {} +")
        
        # 2. Kill Gunicorn Processes Forcefully
        print("Killing Gunicorn processes...")
        client.exec_command("pkill -9 -f gunicorn")
        time.sleep(2) # Wait for kill
        
        # 3. Start Service
        print("Starting Flask App Service...")
        stdin, stdout, stderr = client.exec_command("systemctl start flask-app")
        exit_status = stdout.channel.recv_exit_status()
        
        if exit_status == 0:
            print("✅ Service Start Command Successful")
        else:
            print(f"❌ Service Start Failed: {stderr.read().decode()}")

        # 4. Restart Nginx
        print("Restarting Nginx...")
        client.exec_command("systemctl restart nginx")
        
        # 5. Verify Running Process
        time.sleep(2)
        stdin, stdout, stderr = client.exec_command("ps aux | grep gunicorn")
        print("\nRunning Processes:")
        print(stdout.read().decode())
        
        client.close()
        print("Done.")
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    force_restart()
