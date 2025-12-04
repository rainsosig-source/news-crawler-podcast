import os
from flask import Flask, request
from naver_crawler import run_crawling_job
import db_manager

app = Flask(__name__)

@app.route("/", methods=["GET", "POST"])
def index():
    """
    Cloud Scheduler calls this endpoint to trigger the crawling job.
    """
    print("🚀 크롤링 트리거 수신! 작업 시작...")
    
    # Initialize DB if needed
    try:
        db_manager.init_db()
    except Exception as e:
        print(f"DB 초기화 오류 (무시 가능): {e}")

    # Run the crawling job
    try:
        run_crawling_job()
        return "크롤링 작업 완료!", 200
    except Exception as e:
        print(f"크롤링 중 오류 발생: {e}")
        return f"오류 발생: {e}", 500

if __name__ == "__main__":
    # Cloud Run injects PORT environment variable
    port = int(os.environ.get("PORT", 8080))
    app.run(debug=True, host="0.0.0.0", port=port)
