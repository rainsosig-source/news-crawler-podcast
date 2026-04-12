import pymysql
from datetime import datetime
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import time

import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Database Configuration
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = int(os.getenv("DB_PORT", 3306))
DB_USER = os.getenv("DB_USER", "root")
DB_PASS = os.getenv("DB_PASSWORD", "")
DB_NAME = os.getenv("DB_NAME", "news_db")

# Email Alert Configuration
ALERT_EMAIL = os.getenv("ALERT_EMAIL", "")  # 알림 받을 이메일
SMTP_EMAIL = os.getenv("SMTP_EMAIL", "")    # Gmail 계정
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")  # Gmail 앱 비밀번호

# 알림 쿨다운 (중복 알림 방지)
_last_alert_time = 0
ALERT_COOLDOWN = 600  # 10분

def send_db_error_alert(error_message):
    """DB 연결 오류 발생 시 이메일 알림 발송"""
    global _last_alert_time
    
    # 쿨다운 체크 (10분 내 중복 알림 방지)
    current_time = time.time()
    if current_time - _last_alert_time < ALERT_COOLDOWN:
        print(f"⚠️ 알림 쿨다운 중 ({ALERT_COOLDOWN}초)")
        return False
    
    if not ALERT_EMAIL or not SMTP_EMAIL or not SMTP_PASSWORD:
        print("⚠️ 이메일 알림 설정이 없습니다. (ALERT_EMAIL, SMTP_EMAIL, SMTP_PASSWORD)")
        return False
    
    try:
        msg = MIMEMultipart()
        msg['From'] = SMTP_EMAIL
        msg['To'] = ALERT_EMAIL
        msg['Subject'] = f"🚨 [News Crawler] DB 연결 오류 발생!"
        
        body = f"""
DB 연결 오류가 발생했습니다.

━━━━━━━━━━━━━━━━━━━━━━━━
🕐 발생 시각: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
🖥️ DB 서버: {DB_HOST}:{DB_PORT}
👤 사용자: {DB_USER}
📁 데이터베이스: {DB_NAME}
━━━━━━━━━━━━━━━━━━━━━━━━

❌ 오류 내용:
{error_message}

━━━━━━━━━━━━━━━━━━━━━━━━
확인이 필요합니다.
"""
        msg.attach(MIMEText(body, 'plain', 'utf-8'))
        
        with smtplib.SMTP('smtp.gmail.com', 587) as server:
            server.starttls()
            server.login(SMTP_EMAIL, SMTP_PASSWORD)
            server.send_message(msg)
        
        _last_alert_time = current_time
        print(f"📧 DB 오류 알림 이메일 발송 완료: {ALERT_EMAIL}")
        return True
        
    except Exception as e:
        print(f"❌ 이메일 발송 실패: {e}")
        return False

def get_connection():
    """DB 연결. 실패 시 이메일 알림 발송."""
    try:
        return pymysql.connect(
            host=DB_HOST,
            port=DB_PORT,
            user=DB_USER,
            password=DB_PASS,
            db=DB_NAME,
            charset='utf8mb4',
            cursorclass=pymysql.cursors.DictCursor
        )
    except Exception as e:
        error_msg = str(e)
        print(f"❌ DB 연결 실패: {error_msg}")
        send_db_error_alert(error_msg)
        raise

def init_db():
    """Initialize the database table if it doesn't exist."""
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            # Create episodes table with keyword_id
            sql = """
            CREATE TABLE IF NOT EXISTS episodes (
                id INT AUTO_INCREMENT PRIMARY KEY,
                press VARCHAR(100),
                title VARCHAR(255),
                link TEXT,
                mp3_path VARCHAR(255),
                keyword_id INT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                INDEX idx_keyword (keyword_id),
                INDEX idx_created (created_at)
            )
            """
            cursor.execute(sql)
            
            # Add keyword_id column if it doesn't exist (for existing tables)
            try:
                cursor.execute("ALTER TABLE episodes ADD COLUMN keyword_id INT")
                cursor.execute("ALTER TABLE episodes ADD INDEX idx_keyword (keyword_id)")
                print("Added keyword_id column to existing episodes table.")
            except pymysql.err.OperationalError:
                pass  # Column already exists (expected)
            
            # Add topic column to keywords table if it doesn't exist
            try:
                cursor.execute("ALTER TABLE keywords ADD COLUMN topic VARCHAR(100)")
                print("Added topic column to keywords table.")
                
                # Migration: Copy existing keyword values to topic where topic is NULL
                cursor.execute("UPDATE keywords SET topic = keyword WHERE topic IS NULL")
                print("Migrated existing keywords to topic field.")
            except pymysql.err.OperationalError:
                pass  # Column already exists (expected)
                
        conn.commit()
        print("Database table 'episodes' checked/created.")
    finally:
        conn.close()

def insert_episode(press, title, link, mp3_path, keyword_id=None):
    """Insert a new episode record."""
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            sql = "INSERT INTO episodes (press, title, link, mp3_path, keyword_id) VALUES (%s, %s, %s, %s, %s)"
            cursor.execute(sql, (press, title, link, mp3_path, keyword_id))
        conn.commit()
        print(f"DB Logged: {title}")
    except Exception as e:
        print(f"DB Error: {e}")
    finally:
        conn.close()

def is_duplicate_news(link):
    """Check if news article already exists in DB by link."""
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            sql = "SELECT COUNT(*) as cnt FROM episodes WHERE link = %s"
            cursor.execute(sql, (link,))
            result = cursor.fetchone()
            return result['cnt'] > 0
    except Exception as e:
        print(f"DB Error (is_duplicate_news): {e}")
        return False  # If error, allow processing
    finally:
        conn.close()

def get_active_keywords():
    """Fetch all keywords sorted by priority (highest first)."""
    conn = get_connection()
    keywords = []
    try:
        with conn.cursor() as cursor:
            # COALESCE: topic이 NULL이면 keyword 값을 사용
            sql = "SELECT id, keyword, COALESCE(topic, keyword) as topic, requirements FROM keywords WHERE priority > 0 ORDER BY priority DESC"
            cursor.execute(sql)
            keywords = cursor.fetchall()
    except Exception as e:
        print(f"DB Error (get_keywords): {e}")
    finally:
        conn.close()
    return keywords

if __name__ == "__main__":
    # Test connection and init
    try:
        init_db()
        print("DB Connection Successful")
    except Exception as e:
        print(f"DB Connection Failed: {e}")
