import pymysql
from datetime import datetime

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

def get_connection():
    return pymysql.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASS,
        db=DB_NAME,
        charset='utf8mb4',
        cursorclass=pymysql.cursors.DictCursor
    )

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
            except:
                pass  # Column already exists
                
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
            sql = "SELECT id, keyword, requirements FROM keywords WHERE priority > 0 ORDER BY priority DESC"
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
