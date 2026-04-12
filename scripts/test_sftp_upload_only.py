"""
SFTP 업로드 직접 테스트
기존 MP3 파일을 서버로 업로드하는 테스트
"""
import os
from sftp_uploader import upload_file

def test_upload_existing_file():
    """기존 파일을 SFTP로 업로드 테스트"""
    
    # opening.mp3 파일이 있는지 확인
    test_file = "opening.mp3"
    
    if not os.path.exists(test_file):
        print(f"❌ 테스트 파일을 찾을 수 없습니다: {test_file}")
        print("   다른 작은 파일을 생성합니다...")
        
        # 더미 테스트 파일 생성
        test_file = "test_dummy.mp3"
        with open(test_file, "wb") as f:
            f.write(b"This is a test MP3 file" * 1000)  # ~23KB
        print(f"   ✅ 테스트 파일 생성: {test_file}")
    
    print(f"\n📤 파일 업로드 테스트: {test_file}")
    print(f"   파일 크기: {os.path.getsize(test_file):,} bytes")
    print()
    
    # SFTP 업로드 실행
    remote_path = upload_file(test_file)
    
    if remote_path:
        print(f"\n✅ 업로드 성공!")
        print(f"   원격 경로: {remote_path}")
        print(f"   웹 URL: https://sosig.shop/podcast")
        
        # 테스트 파일 정리
        if test_file == "test_dummy.mp3":
            os.remove(test_file)
            print(f"\n   🗑️  테스트 파일 삭제: {test_file}")
    else:
        print(f"\n❌ 업로드 실패")
        
        # 실패 시 테스트 파일 유지
        if test_file == "test_dummy.mp3":
            print(f"   테스트 파일 유지: {test_file}")

if __name__ == "__main__":
    print("=" * 70)
    print("🧪 SFTP 업로드 단독 테스트")
    print("=" * 70)
    print()
    
    test_upload_existing_file()
    
    print("\n" + "=" * 70)
    print("✅ 테스트 완료!")
    print("=" * 70)
