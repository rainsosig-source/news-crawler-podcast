"""
로컬에서 전체 크롤링 작업 실행 (Cloud Run과 동일)
"""
import sys
import os

# Force unbuffered output
sys.stdout.reconfigure(line_buffering=True)

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from naver_crawler import run_crawling_job
import db_manager

if __name__ == "__main__":
    print("=" * 70)
    print("🚀 로컬 크롤링 작업 시작 (Cloud Run과 동일)")
    print("=" * 70)
    
    db_manager.init_db()
    run_crawling_job()
    
    print("=" * 70)
    print("✅ 크롤링 작업 완료!")
    print("=" * 70)
