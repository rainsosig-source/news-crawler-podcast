import paramiko
import os
from dotenv import load_dotenv

load_dotenv()

# Server Configuration
HOST = os.getenv("SFTP_HOST", "")
PORT = int(os.getenv("SFTP_PORT", "22"))
USERNAME = os.getenv("SFTP_USER", "")
PASSWORD = os.getenv("SFTP_PASSWORD", "")

def restart_server():
    print(f"Connecting to {HOST}...")
    try:
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(HOST, PORT, USERNAME, PASSWORD)
        
        # Try to restart the service (assuming it's named 'flask-app' or 'news-crawler')
        # If you know the exact service name, replace 'flask-app'
        service_name = "flask-app" 
        
        print(f"Restarting service '{service_name}'...")
        stdin, stdout, stderr = client.exec_command(f"systemctl restart {service_name}")
        
        exit_status = stdout.channel.recv_exit_status()
        
        if exit_status == 0:
            print("✅ Service restarted successfully!")
        else:
            print(f"⚠️ Restart failed (Exit Code: {exit_status})")
            print("Error:", stderr.read().decode())
            
            # Fallback: Try to reload Gunicorn if service restart failed
            print("Attempting to reload Gunicorn directly...")
            client.exec_command("pkill -HUP gunicorn")
            print("Sent HUP signal to Gunicorn.")

        client.close()
        return True
        
    except Exception as e:
        print(f"❌ Connection Error: {e}")
        return False

if __name__ == "__main__":
    restart_server()
