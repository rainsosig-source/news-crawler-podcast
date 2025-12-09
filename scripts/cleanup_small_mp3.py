#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""sosig.shop 서버의 MP3 파일 크기 상세 분석 및 삭제 스크립트"""

import paramiko
import pymysql
import os
from datetime import datetime

# 서버 및 DB 설정
SERVER = "139.150.81.187"
SSH_USER = "root"
SSH_PASSWORD = "L0&wpLWQ"
DB_USER = "admin"
DB_PASSWORD = "L0&wpLWQ"
DB_NAME = "podcast"

def ssh_execute(command):
    """SSH로 명령 실행"""
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(SERVER, username=SSH_USER, password=SSH_PASSWORD)
    stdin, stdout, stderr = ssh.exec_command(command)
    result = stdout.read().decode('utf-8')
    error = stderr.read().decode('utf-8')
    ssh.close()
    return result, error

def analyze_all_mp3_files():
    """모든 MP3 파일의 크기 분석"""
    print("=== 전체 MP3 파일 크기 분석 ===\n")
    
    # 모든 MP3 파일의 크기를 바이트 단위로 조회
    command = """
    find /var/www/html/podcast -name "*.mp3" -type f -exec sh -c 'size=$(stat -f%z "$1" 2>/dev/null || stat -c%s "$1" 2>/dev/null); echo "$1 $size"' _ {} \\; 2>/dev/null
    """
    
    result, error = ssh_execute(command)
    
    if error and "No such file" not in error:
        print(f"경고: {error}")
    
    small_files = []
    all_files = []
    
    if result:
        for line in result.strip().split('\n'):
            if line:
                parts = line.rsplit(' ', 1)
                if len(parts) == 2:
                    filepath = parts[0]
                    try:
                        size_bytes = int(parts[1])
                        filename = os.path.basename(filepath)
                        
                        file_info = {
                            'path': filepath,
                            'size_bytes': size_bytes,
                            'size_mb': size_bytes / (1024 * 1024),
                            'filename': filename
                        }
                        
                        all_files.append(file_info)
                        
                        # 1MB = 1048576 bytes
                        if size_bytes < 1048576:
                            small_files.append(file_info)
                    except ValueError:
                        continue
    
    print(f"총 MP3 파일 개수: {len(all_files)}")
    print(f"1MB 이하 파일 개수: {len(small_files)}\n")
    
    if small_files:
        print("1MB 이하 파일 목록:")
        for f in sorted(small_files, key=lambda x: x['size_bytes']):
            print(f"  - {f['filename']}: {f['size_bytes']:,} bytes ({f['size_mb']:.2f} MB)")
    
    # 크기별 통계
    if all_files:
        sizes_mb = [f['size_mb'] for f in all_files]
        print(f"\n파일 크기 통계:")
        print(f"  - 최소: {min(sizes_mb):.2f} MB")
        print(f"  - 최대: {max(sizes_mb):.2f} MB")
        print(f"  - 평균: {sum(sizes_mb)/len(sizes_mb):.2f} MB")
    
    return small_files, all_files

def check_episodes_table():
    """episodes 테이블 상세 확인"""
    print("\n=== episodes 테이블 상세 정보 ===\n")
    
    conn = pymysql.connect(
        host=SERVER,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME,
        charset='utf8mb4'
    )
    
    try:
        cursor = conn.cursor()
        
        # 테이블 구조
        cursor.execute("DESCRIBE episodes")
        columns = cursor.fetchall()
        print("테이블 구조:")
        for col in columns:
            print(f"  - {col[0]} ({col[1]})")
        
        # 전체 레코드 수
        cursor.execute("SELECT COUNT(*) FROM episodes")
        count = cursor.fetchone()[0]
        print(f"\n전체 레코드 수: {count}개")
        
        # 샘플 데이터 (파일경로 포함)
        cursor.execute("SELECT * FROM episodes LIMIT 3")
        samples = cursor.fetchall()
        
        # 컬럼명 가져오기
        cursor.execute("DESCRIBE episodes")
        column_names = [col[0] for col in cursor.fetchall()]
        
        print(f"\n샘플 데이터:")
        for sample in samples:
            print(f"\n레코드:")
            for i, value in enumerate(sample):
                if i < len(column_names):
                    print(f"  {column_names[i]}: {value}")
        
        return column_names
        
    finally:
        conn.close()

def delete_small_files(small_files, dry_run=True):
    """1MB 이하 파일 삭제 (dry_run=False일 때만 실제 삭제)"""
    if not small_files:
        print("\n삭제할 파일이 없습니다.")
        return
    
    print(f"\n=== 삭제 작업 {'(시뮬레이션)' if dry_run else '(실제 삭제)'} ===\n")
    
    conn = pymysql.connect(
        host=SERVER,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME,
        charset='utf8mb4'
    )
    
    deleted_count = 0
    db_deleted_count = 0
    
    try:
        cursor = conn.cursor()
        
        for file_info in small_files:
            filepath = file_info['path']
            filename = file_info['filename']
            
            print(f"처리 중: {filename} ({file_info['size_bytes']} bytes)")
            
            # 1. DB에서 해당 파일 찾기 (audio_file 컬럼 사용)
            cursor.execute("SELECT id, title FROM episodes WHERE audio_file LIKE %s", (f"%{filename}%",))
            db_records = cursor.fetchall()
            
            if db_records:
                for record in db_records:
                    episode_id, title = record
                    print(f"  - DB 레코드 발견: ID={episode_id}, Title={title}")
                    
                    if not dry_run:
                        # DB에서 삭제
                        cursor.execute("DELETE FROM episodes WHERE id = %s", (episode_id,))
                        db_deleted_count += 1
                        print(f"  ✓ DB 레코드 삭제 완료")
                    else:
                        print(f"  (시뮬레이션) DB 레코드 삭제 예정")
            
            if not dry_run:
                # 2. 파일 삭제
                delete_cmd = f'rm -f "{filepath}"'
                result, error = ssh_execute(delete_cmd)
                if not error:
                    deleted_count += 1
                    print(f"  ✓ 파일 삭제 완료: {filepath}")
                else:
                    print(f"  ✗ 파일 삭제 실패: {error}")
            else:
                print(f"  (시뮬레이션) 파일 삭제 예정: {filepath}")
            
            print()
        
        if not dry_run:
            conn.commit()
            print(f"=== 삭제 완료 ===")
            print(f"파일 삭제: {deleted_count}개")
            print(f"DB 레코드 삭제: {db_deleted_count}개")
        else:
            print(f"=== 시뮬레이션 완료 ===")
            print(f"삭제 예정 파일: {len(small_files)}개")
            print(f"삭제 예정 DB 레코드: {db_deleted_count}개 (추정)")
            print(f"\n실제로 삭제하려면 dry_run=False로 스크립트를 다시 실행하세요.")
            
    finally:
        conn.close()

if __name__ == "__main__":
    print("=" * 60)
    print("sosig.shop MP3 파일 정리 - 상세 분석")
    print("=" * 60)
    
    # 1. 모든 MP3 파일 분석
    try:
        small_files, all_files = analyze_all_mp3_files()
    except Exception as e:
        print(f"\n파일 분석 오류: {e}")
        import traceback
        traceback.print_exc()
        small_files = []
    
    # 2. episodes 테이블 확인
    try:
        columns = check_episodes_table()
    except Exception as e:
        print(f"\n데이터베이스 확인 오류: {e}")
        import traceback
        traceback.print_exc()
    
    # 3. 삭제 시뮬레이션
    if small_files:
        try:
            delete_small_files(small_files, dry_run=True)
        except Exception as e:
            print(f"\n삭제 시뮬레이션 오류: {e}")
            import traceback
            traceback.print_exc()
    
    print("\n" + "=" * 60)
    print("분석 완료")
    print("=" * 60)
