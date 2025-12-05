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

# Download podcast.html
sftp.get('/root/flask-app/templates/podcast.html', 'templates/podcast.html')
print("Downloaded podcast.html")

sftp.close()
client.close()
