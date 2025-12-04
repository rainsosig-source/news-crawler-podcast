import paramiko
import os
from dotenv import load_dotenv

load_dotenv()

HOST = os.getenv("SFTP_HOST", "")
PORT = int(os.getenv("SFTP_PORT", "22"))
USERNAME = os.getenv("SFTP_USER", "")
PASSWORD = os.getenv("SFTP_PASSWORD", "")

def check_crawler():
    try:
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(HOST, PORT, USERNAME, PASSWORD)
        
        print("=" * 80)
        print("1. 크롤러 파일 확인")
        print("=" * 80)
        stdin, stdout, stderr = client.exec_command("ls -la /root/flask-app/ | grep -E '(crawler|podcast|naver)'")
        result = stdout.read().decode()
        if result:
            print(result)
        else:
            print("❌ 크롤러 파일이 서버에 없습니다!")
        
        print("\n" + "=" * 80)
        print("2. 실행 중인 Python 프로세스")
        print("=" * 80)
        stdin, stdout, stderr = client.exec_command("ps aux | grep python | grep -v grep")
        print(stdout.read().decode())
        
        print("\n" + "=" * 80)
        print("3. Systemd 서비스 확인")
        print("=" * 80)
        stdin, stdout, stderr = client.exec_command("ls -la /etc/systemd/system/*.service | grep -E '(crawler|podcast)'")
        result = stdout.read().decode()
        if result:
            print(result)
        else:
            print("❌ Systemd 서비스로 등록된 크롤러가 없습니다!")
        
        print("\n" + "=" * 80)
        print("4. 최근 로그 (app.log)")
        print("=" * 80)
        stdin, stdout, stderr = client.exec_command("tail -30 /root/flask-app/app.log")
        print(stdout.read().decode())
        
        print("\n" + "=" * 80)
        print("5. 최근 팟캐스트 파일 확인")
        print("=" * 80)
        stdin, stdout, stderr = client.exec_command("find /root/flask-app/static/podcast -type f -name '*.mp3' -mmin -120 | head -10")
        result = stdout.read().decode()
        if result:
            print("✅ 최근 2시간 이내 생성된 팟캐스트:")
            print(result)
        else:
            print("❌ 최근 2시간 이내 생성된 팟캐스트가 없습니다!")
        
        client.close()
        
    except Exception as e:
        print(f"❌ 연결 오류: {e}")

if __name__ == "__main__":
    check_crawler()
