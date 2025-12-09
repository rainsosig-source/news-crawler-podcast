#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Cloud Run 로그 분석 스크립트"""
import json
from datetime import datetime
from collections import Counter

# 로그 파일 읽기
with open('logs.json', 'r', encoding='utf-8') as f:
    logs = json.load(f)

print(f"=== Cloud Run 크롤링 로그 분석 ===\n")
print(f"전체 로그 항목 수: {len(logs)}")

# 시간대 분석
timestamps = [log['timestamp'] for log in logs if 'timestamp' in log]
if timestamps:
    earliest = min(timestamps)
    latest = max(timestamps)
    print(f"로그 범위: {earliest} ~ {latest}\n")

# 주요 메시지 분석
print("=== 주요 로그 메시지 분석 ===")

# 키워드별 로그 카운트
keywords = {
    "크롤링": 0,
    "팟캐스트": 0,
    "AI": 0,
    "MP3": 0,
    "SFTP": 0,
    "업로드": 0,
    "삭제": 0,
    "완료": 0,
    "실패": 0,
    "오류": 0,
    "ERROR": 0,
    "성공": 0
}

important_logs = []

for log in logs:
    text = log.get('textPayload', '')
    
    # 키워드 카운트
    for keyword in keywords:
        if keyword in text:
            keywords[keyword] += 1
    
    # 중요 로그 수집
    if any(k in text for k in ["완료", "실패", "오류", "ERROR", "성공", "MP3", "SFTP", "업로드"]):
        important_logs.append({
            'time': log.get('timestamp', 'N/A'),
            'message': text[:100]  # 메시지 길이 제한
        })

# 키워드 통계 출력
for keyword, count in keywords.items():
    if count > 0:
        print(f"  - '{keyword}': {count}회")

# 최근 중요 로그 출력
print(f"\n=== 최근 주요 로그 (최대 20개) ===")
for log in important_logs[:20]:
    print(f"[{log['time']}] {log['message']}")

# 로그 타입 분석
log_types = Counter([log.get('logName', 'unknown').split('/')[-1] for log in logs])
print(f"\n=== 로그 타입 분포 ===")
for log_type, count in log_types.items():
    print(f"  - {log_type}: {count}개")

# stderr 로그 (에러) 분석
stderr_logs = [log for log in logs if 'stderr' in log.get('logName', '')]
print(f"\n=== stderr (에러) 로그: {len(stderr_logs)}개 ===")
for log in stderr_logs[:10]:
    print(f"[{log.get('timestamp', 'N/A')}] {log.get('textPayload', 'N/A')[:100]}")

print("\n=== 분석 완료 ===")
