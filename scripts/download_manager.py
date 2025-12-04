"""
원격 서버에서 manager.html 다운로드
"""
import paramiko
import os
from dotenv import load_dotenv

load_dotenv()

SFTP_HOST = os.getenv("SFTP_HOST", "")
SFTP_PORT = int(os.getenv("SFTP_PORT", "22"))
SFTP_USER = os.getenv("SFTP_USER", "")
SFTP_PASS = os.getenv("SFTP_PASSWORD", "")

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(SFTP_HOST, SFTP_PORT, SFTP_USER, SFTP_PASS)
sftp = client.open_sftp()

remote_file = "/root/flask-app/templates/manager.html"
local_file = "templates/manager_backup.html"

sftp.get(remote_file, local_file)
print(f"✅ Downloaded: {remote_file} → {local_file}")

sftp.close()
client.close()
