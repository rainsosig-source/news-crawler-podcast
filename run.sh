#!/bin/bash
set -e
export PATH="/home/sddari/.local/bin:/usr/local/bin:/usr/bin:/bin"
PROJECT=/mnt/nas/data2/news
VENV=/home/sddari/news_runtime/.venv

# 중복 실행 방지 + stale lock 감지: 50분 이상 잡고 있는 프로세스는 stuck으로 판단해 강제 정리
LOCKFILE=/tmp/sosig_news_run.lock
STALE_LOCK_SEC=3000

exec 200>"$LOCKFILE"
if ! flock -n 200; then
    HOLDER_PID=$(lsof -t "$LOCKFILE" 2>/dev/null | head -1)
    if [ -z "$HOLDER_PID" ]; then
        echo "[run.sh] lock 점유 PID 확인 불가 — 스킵 ($(date '+%F %T'))" >&2
        exit 0
    fi
    HOLDER_AGE=$(ps -o etimes= -p "$HOLDER_PID" 2>/dev/null | tr -d ' ')
    if [ -z "$HOLDER_AGE" ]; then
        echo "[run.sh] PID $HOLDER_PID 정보 조회 실패 — 스킵" >&2
        exit 0
    fi
    if [ "$HOLDER_AGE" -le "$STALE_LOCK_SEC" ]; then
        echo "[run.sh] 이미 실행 중 (PID $HOLDER_PID, ${HOLDER_AGE}s) — 스킵 ($(date '+%F %T'))" >&2
        exit 0
    fi
    echo "[run.sh] stale lock 감지 (PID $HOLDER_PID, ${HOLDER_AGE}s 경과) — 강제 정리" >&2
    kill "$HOLDER_PID" 2>/dev/null
    sleep 3
    kill -9 "$HOLDER_PID" 2>/dev/null
    sleep 1
    if ! flock -n 200; then
        echo "[run.sh] stale 정리 후에도 lock 획득 실패 — 종료" >&2
        exit 1
    fi
    echo "[run.sh] stale lock 정리 완료, 정상 진행" >&2
fi

# 비밀 변수는 NAS가 아닌 로컬(600 권한)에서 로드
DOTENV=/home/sddari/.config/sosig/.env
if [ -f "$DOTENV" ]; then
    set -a
    . "$DOTENV"
    set +a
fi
LOG_DIR=$PROJECT/logs
mkdir -p "$LOG_DIR"
# 14일 이상 된 실행 로그 정리
find "$LOG_DIR" -maxdepth 1 -name 'run_*.log' -type f -mtime +14 -delete 2>/dev/null || true
LOG="$LOG_DIR/run_$(date +%Y%m%d_%H%M%S).log"

cd "$PROJECT"
source "$VENV/bin/activate"

# 월~금 09~18시에는 Claude Sonnet, 그 외 시간/주말은 Claude Haiku
DOW=$(date +%u)   # 1=월 ... 7=일
HOUR=$(date +%H)
if [ "$DOW" -le 5 ] && [ "$HOUR" -ge 9 ] && [ "$HOUR" -lt 18 ]; then
    export PODCAST_MODEL=claude-sonnet-4-6
else
    export PODCAST_MODEL=claude-haiku-4-5-20251001
fi
echo "[run.sh] PODCAST_MODEL=$PODCAST_MODEL (DOW=$DOW HOUR=$HOUR)" >> "$LOG"

exec python naver_crawler.py >> "$LOG" 2>&1
