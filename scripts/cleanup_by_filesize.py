"""
SFTP 파일 크기 기반으로 잘못된 팟캐스트 정리
"""
import db_manager
import paramiko
import os
from dotenv import load_dotenv

load_dotenv()

SFTP_HOST = os.getenv("SFTP_HOST", "")
SFTP_PORT = int(os.getenv("SFTP_PORT", "22"))
SFTP_USER = os.getenv("SFTP_USER", "")
SFTP_PASS = os.getenv("SFTP_PASSWORD", "")

MIN_FILE_SIZE_KB = 50  # 50KB 미만= opening만 있음 (opening.mp3 ≈ 280KB이지만 작게 설정)

print("=" * 70)
print("🧹 파일 크기 기반 팟캐스트 정리")
print("=" * 70)
print(f"설정: {MIN_FILE_SIZE_KB}KB 미만 파일 삭제")
print()

# SFTP 연결
client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(SFTP_HOST, SFTP_PORT, SFTP_USER, SFTP_PASS)
sftp = client.open_sftp()

# DB 연결
conn = db_manager.get_connection()
cursor = conn.cursor()

# 최근 7일 에피소드 조회
query = """
SELECT id, title, mp3_path, created_at 
FROM episodes 
WHERE created_at >= DATE_SUB(NOW(), INTERVAL 7 DAY)
ORDER BY created_at DESC
"""

cursor.execute(query)
episodes = cursor.fetchall()

print(f"📊 총 {len(episodes)}개 에피소드 검사 중...\n")

invalid_episodes = []

for ep in episodes:
    try:
        ep_id = ep['id']
        title = ep['title']
        mp3_path = ep['mp3_path']
        
        print(f"[{ep_id}] {title[:50]}...")
        
        if not mp3_path:
            print("   ⚠️ 파일 경로 없음 (건너뜀)\n")
            continue
        
        # 파일 크기 확인
        stat = sftp.stat(mp3_path)
        file_size_kb = stat.st_size / 1024
        
        print(f"   파일 크기: {file_size_kb:.1f}KB")
        
        if file_size_kb < MIN_FILE_SIZE_KB:
            print(f"   ❌ 삭제 대상! ({file_size_kb:.1f}KB < {MIN_FILE_SIZE_KB}KB)")
            invalid_episodes.append({
                'id': ep_id,
                'title': title,
                'mp3_path': mp3_path,
                'size_kb': file_size_kb
            })
        else:
            print(f"   ✅ 정상 파일")
        
        print()
        
    except FileNotFoundError:
        print(f"   ⚠️ 파일이 서버에 없음 (DB만 정리 대상)")
        invalid_episodes.append({
            'id': ep_id,
            'title': title,
            'mp3_path': mp3_path,
            'size_kb': 0
        })
        print()
    except Exception as e:
        print(f"   ❌ 오류: {e}\n")

# 삭제 요약
print("=" * 70)
print(f"🗑️ 삭제 대상: {len(invalid_episodes)}개")
print("=" * 70)

if len(invalid_episodes) == 0:
    print("✅ 삭제할 파일이 없습니다!")
else:
    for ep in invalid_episodes:
        print(f"• [{ep['id']}] {ep['title'][:50]} ({ep['size_kb']:.1f}KB)")
    
    print()
    confirm = input(f"\n정말로 {len(invalid_episodes)}개 삭제하시겠습니까? (yes 입력): ")
    
    if confirm.lower() == 'yes':
        print("\n🗑️ 삭제 시작...")
        deleted_count = 0
        
        for ep in invalid_episodes:
            print(f"\n[{ep['id']}] {ep['title'][:40]}...")
            
            # 1. SFTP에서 파일 삭제
            try:
                sftp.remove(ep['mp3_path'])
                print(f"   ✅ SFTP 파일 삭제 완료")
            except:
                print(f"   ⚠️ SFTP 파일 삭제 실패 (파일 없음 또는 오류)")
            
            # 2. DB에서 레코드 삭제
            try:
                delete_query = "DELETE FROM episodes WHERE id = %s"
                cursor.execute(delete_query, (ep['id'],))
                conn.commit()
                print(f"   ✅ DB 레코드 삭제 완료")
                deleted_count += 1
            except Exception as e:
                print(f"   ❌ DB 삭제 실패: {e}")
                conn.rollback()
        
        print("\n" + "=" * 70)
        print(f"✅ 정리 완료! {deleted_count}/{len(invalid_episodes)}개 삭제됨")
        print("=" * 70)
    else:
        print("❌ 취소되었습니다.")

sftp.close()
client.close()
conn.close()
