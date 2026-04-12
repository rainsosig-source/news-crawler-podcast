"""
서버 스토리지 용량 및 데이터 보관 기간 분석
"""
import paramiko
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

SFTP_HOST = os.getenv("SFTP_HOST", "")
SFTP_PORT = int(os.getenv("SFTP_PORT", "22"))
SFTP_USER = os.getenv("SFTP_USER", "")
SFTP_PASSWORD = os.getenv("SFTP_PASSWORD", "")
SFTP_REMOTE_DIR = "/root/flask-app/static/podcast"

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

try:
    print("=" * 70)
    print("📊 sosig.shop 스토리지 용량 분석")
    print("=" * 70)
    
    ssh.connect(SFTP_HOST, SFTP_PORT, SFTP_USER, SFTP_PASSWORD)
    sftp = ssh.open_sftp()
    
    # 1. 디스크 용량 확인
    stdin, stdout, stderr = ssh.exec_command("df -h /root")
    disk_info = stdout.read().decode()
    print("\n💾 디스크 용량 정보:")
    print(disk_info)
    
    # 숫자만 추출
    stdin, stdout, stderr = ssh.exec_command("df -BG /root | tail -1 | awk '{print $2, $3, $4}'")
    disk_nums = stdout.read().decode().strip().split()
    total_gb = int(disk_nums[0].replace('G', ''))
    used_gb = int(disk_nums[1].replace('G', ''))
    avail_gb = int(disk_nums[2].replace('G', ''))
    
    print(f"\n전체 용량: {total_gb}GB")
    print(f"사용 중: {used_gb}GB")
    print(f"남은 용량: {avail_gb}GB")
    
    # 2. MP3 파일 총 크기 및 개수 확인
    print(f"\n📂 팟캐스트 디렉토리 분석: {SFTP_REMOTE_DIR}")
    
    total_size = 0
    file_count = 0
    files_by_date = {}
    
    def analyze_recursive(path):
        global total_size, file_count
        try:
            for item in sftp.listdir_attr(path):
                item_path = f"{path}/{item.filename}"
                if item.st_mode & 0o040000:  # 디렉토리
                    analyze_recursive(item_path)
                elif item.filename.endswith('.mp3'):
                    total_size += item.st_size
                    file_count += 1
                    
                    # 날짜별 분류 (경로에서 날짜 추출: YYYY/MM/DD)
                    parts = path.split('/')
                    if len(parts) >= 3:
                        try:
                            date_str = f"{parts[-3]}-{parts[-2]}-{parts[-1]}"
                            if date_str not in files_by_date:
                                files_by_date[date_str] = {'count': 0, 'size': 0}
                            files_by_date[date_str]['count'] += 1
                            files_by_date[date_str]['size'] += item.st_size
                        except:
                            pass
        except Exception as e:
            pass
    
    analyze_recursive(SFTP_REMOTE_DIR)
    
    total_size_mb = total_size / (1024 * 1024)
    total_size_gb = total_size / (1024 * 1024 * 1024)
    
    print(f"\n총 MP3 파일 개수: {file_count}개")
    print(f"총 MP3 파일 크기: {total_size_mb:.1f}MB ({total_size_gb:.2f}GB)")
    
    # 3. 일일 평균 데이터 생성량 계산
    if files_by_date:
        dates = sorted(files_by_date.keys())
        print(f"\n📅 데이터 보관 기간: {dates[0]} ~ {dates[-1]}")
        
        # 최근 7일 데이터로 평균 계산
        recent_dates = dates[-7:] if len(dates) >= 7 else dates
        recent_total_size = sum(files_by_date[d]['size'] for d in recent_dates)
        recent_total_count = sum(files_by_date[d]['count'] for d in recent_dates)
        
        daily_avg_size_mb = (recent_total_size / len(recent_dates)) / (1024 * 1024)
        daily_avg_count = recent_total_count / len(recent_dates)
        
        print(f"\n📈 최근 {len(recent_dates)}일 평균:")
        print(f"   - 일일 생성량: {daily_avg_size_mb:.1f}MB")
        print(f"   - 일일 파일 수: {daily_avg_count:.1f}개")
        
        # 4. 예상 보관 가능 일수 계산
        days_until_full = (avail_gb * 1024) / daily_avg_size_mb if daily_avg_size_mb > 0 else 0
        
        print("\n" + "=" * 70)
        print("📊 보관 가능 기간 예측")
        print("=" * 70)
        print(f"\n현재 남은 용량: {avail_gb}GB ({avail_gb * 1024:.0f}MB)")
        print(f"일일 데이터 생성량: {daily_avg_size_mb:.1f}MB")
        print(f"\n✅ 예상 보관 가능 기간: 약 {days_until_full:.0f}일 ({days_until_full/30:.1f}개월)")
        
        if days_until_full < 30:
            print("\n⚠️ 경고: 1개월 이내에 용량이 부족할 수 있습니다!")
        elif days_until_full < 90:
            print("\n⚠️ 주의: 3개월 이내에 용량 관리가 필요합니다.")
        else:
            print("\n✅ 충분한 저장 공간이 있습니다.")
        
        # 5. 권장 사항
        print("\n" + "=" * 70)
        print("💡 권장 사항")
        print("=" * 70)
        
        if days_until_full < 60:
            print("• 30일 이상 된 파일 자동 삭제 설정 권장")
        elif days_until_full < 180:
            print("• 60일 이상 된 파일 정기 백업 및 삭제 권장")
        else:
            print("• 현재 설정 유지 (90일 이상 된 파일 정리)")
        
        retention_30 = (avail_gb * 1024 + (30 * daily_avg_size_mb)) / daily_avg_size_mb
        retention_60 = (avail_gb * 1024 + (60 * daily_avg_size_mb)) / daily_avg_size_mb
        
        print(f"\n현재 용량으로:")
        print(f"• 30일 보관 정책 시: 계속 운영 가능 (매일 {daily_avg_size_mb:.1f}MB 삭제, {daily_avg_size_mb:.1f}MB 생성)")
        print(f"• 60일 보관 정책 시: 약 {retention_60:.0f}일간 운영 가능")
    
    sftp.close()
    ssh.close()
    
except Exception as e:
    print(f"\n❌ 오류 발생: {e}")
finally:
    print("\n" + "=" * 70)
