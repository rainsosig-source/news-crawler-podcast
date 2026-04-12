"""
SFTP 디렉토리 구조 확인
"""
import paramiko
import os
from dotenv import load_dotenv

load_dotenv()

SFTP_HOST = os.getenv("SFTP_HOST", "")
SFTP_PORT = int(os.getenv("SFTP_PORT", "22"))
SFTP_USER = os.getenv("SFTP_USER", "")
SFTP_PASSWORD = os.getenv("SFTP_PASSWORD", "")

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

try:
    print(f"🔗 연결 중: {SFTP_HOST}")
    ssh.connect(SFTP_HOST, SFTP_PORT, SFTP_USER, SFTP_PASSWORD)
    sftp = ssh.open_sftp()
    
    # 기본 디렉토리 확인
    print("\n📂 루트 디렉토리:")
    print(sftp.listdir("/"))
    
    # www 디렉토리 확인
    print("\n📂 /var/www:")
    try:
        print(sftp.listdir("/var/www"))
    except:
        print("   (접근 불가)")
    
    # sosig.shop 확인
    print("\n📂 /var/www/html:")
    try:
        print(sftp.listdir("/var/www/html"))
    except:
        print("   (접근 불가)")
        
    # 홈 디렉토리 확인
    print("\n📂 홈 디렉토리 (현재 위치):")
    print(sftp.listdir("."))
    
    sftp.close()
    ssh.close()
    
except Exception as e:
    print(f"❌ 오류: {e}")
