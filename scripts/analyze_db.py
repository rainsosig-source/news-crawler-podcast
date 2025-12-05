import sys
import os
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db_manager import get_connection

conn = get_connection()
cursor = conn.cursor()

# 테이블 목록
cursor.execute("SHOW TABLES")
tables = [list(t.values())[0] for t in cursor.fetchall()]

print("=" * 70)
print("DATABASE: podcast")
print("=" * 70)
print(f"\nTables: {', '.join(tables)}")
print()

# 각 테이블 구조
for table in tables:
    print("-" * 70)
    print(f"TABLE: {table}")
    print("-" * 70)
    
    cursor.execute(f"DESCRIBE {table}")
    for col in cursor.fetchall():
        null = "NULL" if col['Null'] == 'YES' else "NOT NULL"
        key = f"({col['Key']})" if col['Key'] else ""
        print(f"  {col['Field']:<20} {col['Type']:<25} {null:<10} {key}")
    
    cursor.execute(f"SELECT COUNT(*) as cnt FROM {table}")
    cnt = cursor.fetchone()['cnt']
    print(f"  >> Records: {cnt}")
    print()

conn.close()
