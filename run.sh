#!/bin/bash
set -e
export PATH="/home/sddari/.local/bin:/usr/local/bin:/usr/bin:/bin"
PROJECT=/mnt/nas/data2/news
VENV=/home/sddari/news_runtime/.venv

# 중복 실행 방지: 이미 실행 중이면 즉시 종료
LOCKFILE=/tmp/sosig_news_run.lock
exec 200>"$LOCKFILE"
if ! flock -n 200; then
    echo "[run.sh] 이미 실행 중 — 이번 실행 스킵 ($(date '+%F %T'))" >&2
    exit 0
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

# 월~금 09~18시에는 Claude CLI(sonnet), 그 외 시간/주말은 Gemini
DOW=$(date +%u)   # 1=월 ... 7=일
HOUR=$(date +%H)
if [ "$DOW" -le 5 ] && [ "$HOUR" -ge 9 ] && [ "$HOUR" -lt 18 ]; then
    export PODCAST_BACKEND=claude
else
    export PODCAST_BACKEND=gemini
fi
echo "[run.sh] PODCAST_BACKEND=$PODCAST_BACKEND (DOW=$DOW HOUR=$HOUR)" >> "$LOG"

exec python naver_crawler.py >> "$LOG" 2>&1
