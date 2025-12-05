import sys
sys.path.insert(0, '.')
from db_manager import get_connection

conn = get_connection()
with conn.cursor() as cursor:
    # 최근 에피소드 확인
    cursor.execute('SELECT id, title, created_at FROM episodes ORDER BY created_at DESC LIMIT 5')
    episodes = cursor.fetchall()
    print('=== 최근 생성된 에피소드 ===')
    for e in episodes:
        print(f"[{e['created_at']}] {e['title'][:40]}...")
    
    # keywords 테이블 확인
    cursor.execute('SELECT id, keyword, topic, priority FROM keywords ORDER BY priority DESC')
    keywords = cursor.fetchall()
    print('\n=== 키워드 설정 현황 ===')
    for k in keywords:
        topic = k.get('topic') or k['keyword']
        print(f"[P{k['priority']}] Topic: {topic} | Keyword: {k['keyword']}")
conn.close()
