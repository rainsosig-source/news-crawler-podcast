"""
DB에서 최근 에피소드 조회
"""
import db_manager

conn = db_manager.get_connection()
cursor = conn.cursor()

query = """
SELECT id, title, mp3_path, created_at 
FROM episodes 
ORDER BY created_at DESC 
LIMIT 10
"""

cursor.execute(query)
episodes = cursor.fetchall()

print("최근 10개 에피소드:")
print("=" * 80)
for ep in episodes:
    print(f"ID: {ep['id']}")
    print(f"제목: {ep['title']}")
    print(f"파일: {ep['mp3_path']}")
    print(f"생성: {ep['created_at']}")
    print("-" * 80)

conn.close()
