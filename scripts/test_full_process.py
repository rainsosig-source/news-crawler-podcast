"""
크롤러 테스트 - 더 일반적인 검색어로
"""
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from naver_crawler import crawl_naver_news
import db_manager

if __name__ == "__main__":
    print("=" * 70)
    print("🧪 크롤러 전체 프로세스 테스트")
    print("=" * 70)
    
    # DB 초기화
    print("\n1️⃣ 데이터베이스 초기화...")
    try:
        db_manager.init_db()
        print("   ✅ DB 초기화 완료")
    except Exception as e:
        print(f"   ⚠️  DB 초기화 경고: {e}")
    
    # 크롤링 실행
    print("\n2️⃣ 뉴스 크롤링 및 팟캐스트 생성...")
    print("   검색어: 'ChatGPT'")
    print("   처리할 기사 수: 1개")
    print()
    
    stats = crawl_naver_news(
        query="ChatGPT",
        keyword_id=None,
        requirements=None,
        use_ai=True,
        make_audio=True,
        max_articles=1
    )
    
    print("\n" + "=" * 70)
    print("📊 최종 결과")
    print("=" * 70)
    print(f"총 처리: {stats['total']}개")
    print(f"✅ 성공: {stats['success']}개")
    print(f"⚠️  중복: {stats['duplicate']}개")
    print(f"❌ 실패: {stats['failed']}개")
    
    # MP3 및 업로드 확인
    if stats['success'] > 0:
        print("\n✅ 성공! 다음을 확인하세요:")
        print("   1. MP3 파일이 생성되었습니다")
        print("   2. SFTP 서버로 업로드되었습니다")
        print("   3. 데이터베이스에 저장되었습니다")
        print("\n   웹사이트에서 확인: https://sosig.shop/podcast")
    else:
        print("\n⚠️  성공한 항목이 없습니다. 다른 검색어로 시도하세요.")
    
    print("\n" + "=" * 70)
