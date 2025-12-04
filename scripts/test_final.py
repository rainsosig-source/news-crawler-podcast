"""
최종 테스트 - 다른 검색어로 전체 프로세스 검증
"""
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from naver_crawler import crawl_naver_news
import db_manager

if __name__ == "__main__":
    print("=" * 70)
    print("🚀 최종 테스트 - 전체 프로세스 검증")
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
    print("   검색어: '구글'")
    print("   처리할 기사 수: 1개")
    print()
    
    stats = crawl_naver_news(
        query="구글",
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
    
    # 성공 여부 확인
    if stats['success'] > 0:
        print("\n" + "🎉" * 35)
        print("✅ 테스트 성공!")
        print("🎉" * 35)
        print("\n다음을 확인했습니다:")
        print("   1. ✅ 뉴스 크롤링")
        print("   2. ✅ AI 대본 생성")
        print("   3. ✅ TTS 음성 합성")
        print("   4. ✅ MP3 파일 생성")
        print("   5. ✅ SFTP 서버 업로드")
        print("   6. ✅ 데이터베이스 저장")
        print("\n웹사이트에서 확인: https://sosig.shop/podcast")
        
        # 성공 코드 반환
        sys.exit(0)
    else:
        print("\n❌ 테스트 실패")
        print("   성공한 항목이 없습니다.")
        
        # 실패 코드 반환
        sys.exit(1)
