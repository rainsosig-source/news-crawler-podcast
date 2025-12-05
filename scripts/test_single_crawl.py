"""
간단한 크롤러 테스트 - 1개 기사만 처리
MP3 생성과 SFTP 업로드가 정상적으로 되는지 확인
"""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from naver_crawler import crawl_naver_news
import db_manager

if __name__ == "__main__":
    print("=" * 70)
    print("🧪 크롤러 테스트 (1개 기사)")
    print("=" * 70)
    
    # DB 초기화
    print("\n1️⃣ 데이터베이스 초기화...")
    try:
        db_manager.init_db()
        print("   ✅ DB 초기화 완료")
    except Exception as e:
        print(f"   ⚠️  DB 초기화 경고: {e}")
    
    # 크롤링 실행 (1개 기사만)
    print("\n2️⃣ 뉴스 크롤링 시작...")
    print("   검색어: '인공지능'")
    print("   처리할 기사 수: 1개")
    print()
    
    stats = crawl_naver_news(
        query="인공지능",
        keyword_id=None,
        requirements=None,
        use_ai=True,
        make_audio=True,
        max_articles=1  # 1개만 처리
    )
    
    print("\n" + "=" * 70)
    print("📊 테스트 결과")
    print("=" * 70)
    print(f"총 처리: {stats['total']}개")
    print(f"성공: {stats['success']}개")
    print(f"중복: {stats['duplicate']}개")
    print(f"실패: {stats['failed']}개")
    
    # MP3 디렉토리 확인
    print("\n3️⃣ 생성된 MP3 파일 확인...")
    mp3_dir = os.path.join(os.path.dirname(__file__), "MP3")
    if os.path.exists(mp3_dir):
        mp3_files = [f for f in os.listdir(mp3_dir) if f.endswith('.mp3')]
        if mp3_files:
            print(f"   ✅ MP3 파일 생성됨: {len(mp3_files)}개")
            for f in mp3_files:
                size = os.path.getsize(os.path.join(mp3_dir, f))
                print(f"      - {f} ({size:,} bytes)")
        else:
            print("   ❌ MP3 파일이 생성되지 않았습니다.")
    else:
        print("   ❌ MP3 디렉토리가 없습니다.")
    
    print("\n✅ 테스트 완료!")
