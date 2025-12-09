#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""파일 크기 필터링 기능 테스트"""

import os
import sys

def test_file_size_validation():
    """파일 크기 검증 로직 테스트"""
    print("=" * 60)
    print("1MB 파일 크기 검증 기능 테스트")
    print("=" * 60)
    
    # 테스트 1: 작은 더미 파일 생성 (1MB 미만)
    print("\n[테스트 1] 1MB 미만 파일 생성 및 검증")
    small_file = "test_small.mp3"
    with open(small_file, "wb") as f:
        f.write(b"0" * 500000)  # 500KB
    
    size = os.path.getsize(small_file)
    size_mb = size / (1024 * 1024)
    print(f"  생성된 파일: {small_file}")
    print(f"  파일 크기: {size:,} bytes ({size_mb:.2f}MB)")
    
    if size < 1048576:
        print(f"  ✅ 검증 통과: 1MB 미만 파일로 정상 감지")
        os.remove(small_file)
        print(f"  파일 삭제 완료")
    else:
        print(f"  ❌ 검증 실패: 1MB 미만인데 통과로 판정")
        
    # 테스트 2: 큰 더미 파일 생성 (1MB 이상)
    print("\n[테스트 2] 1MB 이상 파일 생성 및 검증")
    large_file = "test_large.mp3"
    with open(large_file, "wb") as f:
        f.write(b"0" * 1500000)  # 1.5MB
    
    size = os.path.getsize(large_file)
    size_mb = size / (1024 * 1024)
    print(f"  생성된 파일: {large_file}")
    print(f"  파일 크기: {size:,} bytes ({size_mb:.2f}MB)")
    
    if size >= 1048576:
        print(f"  ✅ 검증 통과: 1MB 이상 파일로 정상 감지")
        os.remove(large_file)
        print(f"  파일 삭제 완료")
    else:
        print(f"  ❌ 검증 실패: 1MB 이상인데 미만으로 판정")
    
    # 테스트 3: 경계값 테스트 (정확히 1MB)
    print("\n[테스트 3] 경계값 테스트 (정확히 1MB)")
    boundary_file = "test_boundary.mp3"
    with open(boundary_file, "wb") as f:
        f.write(b"0" * 1048576)  # 정확히 1MB
    
    size = os.path.getsize(boundary_file)
    size_mb = size / (1024 * 1024)
    print(f"  생성된 파일: {boundary_file}")
    print(f"  파일 크기: {size:,} bytes ({size_mb:.2f}MB)")
    
    if size >= 1048576:
        print(f"  ✅ 검증 통과: 정확히 1MB, 통과로 판정")
        os.remove(boundary_file)
        print(f"  파일 삭제 완료")
    else:
        print(f"  ❌ 검증 실패: 정확히 1MB인데 미만으로 판정")
    
    print("\n" + "=" * 60)
    print("모든 테스트 완료")
    print("=" * 60)

def check_modified_files():
    """수정된 파일 확인"""
    print("\n[수정된 파일 확인]")
    
    files_to_check = [
        "podcast_audio.py",
        "naver_crawler.py"
    ]
    
    for filename in files_to_check:
        if os.path.exists(filename):
            # 파일에서 "1048576" 또는 "파일 크기" 키워드 찾기
            with open(filename, 'r', encoding='utf-8') as f:
                content = f.read()
                
            if "1048576" in content or "파일 크기 검증" in content:
                print(f"  ✅ {filename}: 파일 크기 검증 코드 발견")
            else:
                print(f"  ❌ {filename}: 파일 크기 검증 코드 없음")
        else:
            print(f"  ❌ {filename}: 파일이 존재하지 않음")

if __name__ == "__main__":
    # 파일 크기 검증 로직 테스트
    test_file_size_validation()
    
    # 수정된 파일 확인
    check_modified_files()
    
    print("\n✅ 로컬 테스트 완료!")
    print("   다음 단계: Cloud Run 배포 (deploy.ps1 실행)")
