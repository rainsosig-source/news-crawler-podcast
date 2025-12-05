import paramiko
import os
import time
from dotenv import load_dotenv
load_dotenv()

HOST = os.getenv('SFTP_HOST', '')
PORT = int(os.getenv('SFTP_PORT', '22'))
USERNAME = os.getenv('SFTP_USER', '')
PASSWORD = os.getenv('SFTP_PASSWORD', '')

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(HOST, PORT, USERNAME, PASSWORD)

# Kill any process using port 5000
print("Killing process using port 5000...")
stdin, stdout, stderr = client.exec_command('fuser -k 5000/tcp')
time.sleep(2)

# Also kill any python flask processes
stdin, stdout, stderr = client.exec_command('pkill -f "flask"')
stdin, stdout, stderr = client.exec_command('pkill -f "app.py"')
time.sleep(2)

# Start Flask app with venv
print("Starting Flask app...")
stdin, stdout, stderr = client.exec_command('cd /root/flask-app && source venv/bin/activate && nohup python3 app.py > flask.log 2>&1 &')
time.sleep(3)

# Check if it's running
stdin, stdout, stderr = client.exec_command('pgrep -f "app.py"')
pid = stdout.read().decode().strip()
if pid:
    print(f'✅ Flask app is running (PID: {pid})')
else:
    # Check logs for error
    print("❌ Flask app not running - checking logs:")
    stdin, stdout, stderr = client.exec_command('tail -20 /root/flask-app/flask.log')
    print(stdout.read().decode())

client.close()
