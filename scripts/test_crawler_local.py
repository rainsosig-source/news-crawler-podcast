"""
로컬에서 크롤러를 테스트하여 오류를 확인합니다.
"""
from naver_crawler import crawl_naver_news
import db_manager

# DB 초기화
db_manager.init_db()

# 테스트 크롤링 (1개 기사만)
print("=" * 80)
print("테스트 크롤링 시작...")
print("=" * 80)

try:
    stats = crawl_naver_news(
        query="인공지능",
        keyword_id=None,
        requirements=None,
        use_ai=True,
        make_audio=True,
        max_articles=1  # 1개만 테스트
    )
    print("\n" + "=" * 80)
    print(f"✅ 테스트 완료: {stats}")
    print("=" * 80)
except Exception as e:
    print("\n" + "=" * 80)
    print(f"❌ 오류 발생: {e}")
    print("=" * 80)
    import traceback
    traceback.print_exc()
