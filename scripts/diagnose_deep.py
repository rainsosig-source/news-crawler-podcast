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

def diagnose_deep():
    try:
        print(f"Connecting to {HOST}...")
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(HOST, PORT, USER, PASSWORD)
        
        print("\n=== 1. Flask Service Config ===")
        stdin, stdout, stderr = client.exec_command("systemctl cat flask-app")
        print(stdout.read().decode())
        
        print("\n=== 2. Check File Content on Disk ===")
        # Check specifically for the changed lines
        cmd = "grep -C 2 'Windows' /root/flask-app/templates/about.html"
        stdin, stdout, stderr = client.exec_command(cmd)
        result = stdout.read().decode()
        if result:
            print(f"✅ FOUND in file:\n{result}")
        else:
            print("❌ NOT FOUND in file")
            
        print("\n=== 3. Check Flask Response (Localhost:5000) ===")
        # Curl the flask app directly
        cmd = "curl -s http://127.0.0.1:5000/about | grep 'Windows'"
        stdin, stdout, stderr = client.exec_command(cmd)
        result = stdout.read().decode()
        if result:
            print(f"✅ FOUND in Flask response:\n{result[:200]}...")
        else:
            print("❌ NOT FOUND in Flask response")
            # Print what it actually returns for debugging
            cmd = "curl -s http://127.0.0.1:5000/about | grep -o 'Google Cloud Run' | head -n 1"
            stdin, stdout, stderr = client.exec_command(cmd)
            OLD_result = stdout.read().decode()
            if OLD_result:
                print(f"⚠️ FOUND OLD CONTENT 'Google Cloud Run' in response")

        print("\n=== 4. Check Nginx Response (Localhost:80) ===")
        cmd = "curl -s http://127.0.0.1/about | grep 'Windows'"
        stdin, stdout, stderr = client.exec_command(cmd)
        result = stdout.read().decode()
        if result:
            print(f"✅ FOUND in Nginx response")
        else:
            print("❌ NOT FOUND in Nginx response")

        client.close()
        print("\nDiagnosis Done.")
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    diagnose_deep()
