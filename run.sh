#!/bin/bash
set -e
export PATH="/home/sddari/.local/bin:/usr/local/bin:/usr/bin:/bin"
PROJECT=/mnt/nas/data2/news
VENV=/home/sddari/news_runtime/.venv
LOG_DIR=$PROJECT/logs
mkdir -p "$LOG_DIR"
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
