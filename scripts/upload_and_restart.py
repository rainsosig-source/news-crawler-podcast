import paramiko
import os
from dotenv import load_dotenv
load_dotenv()

HOST = os.getenv('SFTP_HOST', '')
PORT = int(os.getenv('SFTP_PORT', '22'))
USERNAME = os.getenv('SFTP_USER', '')
PASSWORD = os.getenv('SFTP_PASSWORD', '')

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(HOST, PORT, USERNAME, PASSWORD)
sftp = client.open_sftp()

# Upload the modified app.py
print("Uploading app.py...")
sftp.put('remote_app.py', '/root/flask-app/app.py')
print("✅ app.py uploaded!")

sftp.close()

# Restart Flask app
print("Restarting Flask app...")
stdin, stdout, stderr = client.exec_command('pkill -f "python app.py" ; cd /root/flask-app && nohup python app.py > flask.log 2>&1 &')
print(stdout.read().decode())
print(stderr.read().decode())

import time
time.sleep(2)

# Check if it's running
stdin, stdout, stderr = client.exec_command('pgrep -f "python app.py"')
pid = stdout.read().decode().strip()
if pid:
    print(f"✅ Flask app is running (PID: {pid})")
else:
    print("❌ Flask app may not be running")

client.close()
