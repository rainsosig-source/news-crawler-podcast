import pymysql
from datetime import datetime
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import time
import hashlib

import os
from dotenv import load_dotenv

STATIC_PREFIX = "/root/flask-app/static/"


def compute_title_hash(title):
    return hashlib.sha256((title or "").encode("utf-8")).hexdigest()


def normalize_mp3_path(mp3_path):
    if mp3_path and mp3_path.startswith(STATIC_PREFIX):
        return mp3_path[len(STATIC_PREFIX):]
    return mp3_path

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

def _try_alter(cursor, sql, label):
    try:
        cursor.execute(sql)
        print(f"[migrate] {label}")
    except pymysql.err.OperationalError:
        pass


def init_db():
    """Initialize the database table if it doesn't exist."""
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            sql = """
            CREATE TABLE IF NOT EXISTS episodes (
                id INT AUTO_INCREMENT PRIMARY KEY,
                press VARCHAR(100),
                title VARCHAR(255),
                title_hash CHAR(64),
                link VARCHAR(500) NOT NULL,
                mp3_path VARCHAR(255),
                duration_sec INT UNSIGNED,
                summary VARCHAR(280),
                keyword_id INT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE KEY uk_link (link),
                INDEX idx_keyword_created (keyword_id, created_at),
                INDEX idx_title_hash_created (title_hash, created_at),
                INDEX idx_created_at (created_at),
                FULLTEXT KEY ft_title (title)
            )
            """
            cursor.execute(sql)

            _try_alter(cursor, "ALTER TABLE episodes ADD COLUMN keyword_id INT",
                       "add keyword_id")
            _try_alter(cursor, "ALTER TABLE episodes ADD COLUMN title_hash CHAR(64) AFTER title",
                       "add title_hash")
            _try_alter(cursor, "ALTER TABLE episodes ADD COLUMN duration_sec INT UNSIGNED AFTER mp3_path",
                       "add duration_sec")
            _try_alter(cursor, "ALTER TABLE episodes ADD COLUMN summary VARCHAR(280) AFTER duration_sec",
                       "add summary")
            _try_alter(cursor, "ALTER TABLE episodes MODIFY COLUMN link VARCHAR(500) NOT NULL",
                       "link → VARCHAR(500) NOT NULL")
            _try_alter(cursor, "ALTER TABLE episodes ADD UNIQUE KEY uk_link (link)",
                       "unique(link)")
            _try_alter(cursor, "ALTER TABLE episodes ADD INDEX idx_title_hash_created (title_hash, created_at)",
                       "index(title_hash, created_at)")
            _try_alter(cursor, "ALTER TABLE episodes ADD FULLTEXT KEY ft_title (title)",
                       "fulltext(title)")

            _try_alter(cursor, "ALTER TABLE keywords ADD COLUMN topic VARCHAR(100)",
                       "add keywords.topic")
            cursor.execute("UPDATE keywords SET topic = keyword WHERE topic IS NULL")

        conn.commit()
        print("Database table 'episodes' checked/created.")
    finally:
        conn.close()

def insert_episode(press, title, link, mp3_path, keyword_id=None,
                   duration_sec=None, summary=None):
    """Insert a new episode record."""
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            sql = ("INSERT INTO episodes "
                   "(press, title, title_hash, link, mp3_path, duration_sec, summary, keyword_id) "
                   "VALUES (%s,%s,%s,%s,%s,%s,%s,%s)")
            cursor.execute(sql, (
                press, title, compute_title_hash(title), link,
                normalize_mp3_path(mp3_path), duration_sec, summary, keyword_id,
            ))
        conn.commit()
        print(f"DB Logged: {title}")
    except pymysql.err.IntegrityError as e:
        # UNIQUE(link) 충돌 → 조용히 스킵
        print(f"DB Skip (duplicate link): {title}")
    except Exception as e:
        print(f"DB Error: {e}")
    finally:
        conn.close()

def is_duplicate_news(link):
    """Check if news article already exists in DB by link."""
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            sql = "SELECT 1 FROM episodes WHERE link = %s LIMIT 1"
            cursor.execute(sql, (link,))
            return cursor.fetchone() is not None
    except Exception as e:
        print(f"DB Error (is_duplicate_news): {e}")
        return False  # If error, allow processing
    finally:
        conn.close()

def is_duplicate_title_recent(title, days=7):
    """최근 N일 내 동일 제목 에피소드 존재 여부 (Claude/TTS 재비용 방지)."""
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            sql = ("SELECT 1 FROM episodes "
                   "WHERE title_hash = %s AND created_at >= DATE_SUB(NOW(), INTERVAL %s DAY) "
                   "LIMIT 1")
            cursor.execute(sql, (compute_title_hash(title), days))
            return cursor.fetchone() is not None
    except Exception as e:
        print(f"DB Error (is_duplicate_title_recent): {e}")
        return False
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
