#!/usr/bin/env python3
# 종목 감성 급변 알림 (#7). stock_collector 수집 직후 1일 1회 실행.
# 조건(OR):  |오늘점수 - 어제점수| >= 0.3   (급변)
#        OR  오늘점수 <= -0.4  또는  >= +0.4   (강한 수위)
# 비교 대상: 데이터가 있는 최근 2개 날짜(차트 ◆ 마커와 동일). 같은 날 1회만 발송.
import os, sys, json
from pathlib import Path

_envf = Path("/home/sddari/.config/sosig/.env")
if _envf.exists():
    for _ln in _envf.read_text().splitlines():
        if "=" in _ln and not _ln.strip().startswith("#"):
            _k, _v = _ln.split("=", 1)
            os.environ.setdefault(_k.strip(), _v.strip().strip('"').strip("'"))

sys.path.insert(0, "/mnt/nas/data2/news")
import requests
import db_manager

STOCK = "삼성전자"
DELTA_TH = 0.3      # 전일 대비 급변 임계
LEVEL_TH = 0.4      # 절대 강한 수위 임계
PAGE_URL = "https://sosig.shop/sentiment/samsung"
STATE = Path("/mnt/nas/data2/news/.stock_alert_state.json")
BOT = os.environ.get("TELEGRAM_BOT_TOKEN", "")
CHAT = os.environ.get("TELEGRAM_ADMIN_CHAT_ID", "")


def recent_days(n=2):
    conn = db_manager.get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT DATE(collected_at) d, ROUND(AVG(score),3) s, "
                "SUM(sentiment='호재') p, SUM(sentiment='악재') nn "
                "FROM stock_sentiment WHERE stock=%s "
                "GROUP BY DATE(collected_at) ORDER BY d DESC LIMIT %s", (STOCK, n))
            return cur.fetchall()
    finally:
        conn.close()


def send(text):
    if not BOT or not CHAT:
        print("텔레그램 자격증명 없음 — 발송 생략"); return False
    r = requests.post(f"https://api.telegram.org/bot{BOT}/sendMessage",
                      data={"chat_id": CHAT, "text": text,
                            "parse_mode": "HTML", "disable_web_page_preview": "false"},
                      timeout=20)
    return r.ok


def main():
    rows = recent_days(2)
    if not rows:
        print("데이터 없음"); return
    today = rows[0]
    td = str(today["d"]); ts = float(today["s"] or 0)
    tp = int(today["p"] or 0); tn = int(today["nn"] or 0)
    ys = float(rows[1]["s"] or 0) if len(rows) > 1 else None

    reasons = []
    if ys is not None and abs(ts - ys) >= DELTA_TH:
        arrow = "개선" if ts > ys else "악화"
        reasons.append(f"전일 대비 급{arrow} ({ys:+.2f}→{ts:+.2f}, Δ{ts - ys:+.2f})")
    if ts <= -LEVEL_TH:
        reasons.append(f"강한 악재 수위 ({ts:+.2f})")
    elif ts >= LEVEL_TH:
        reasons.append(f"강한 호재 수위 ({ts:+.2f})")

    if not reasons:
        print(f"조건 미충족 (오늘 {ts:+.2f}, 어제 {ys if ys is None else round(ys,2)})"); return

    # 같은 날 1회만
    last = {}
    if STATE.exists():
        try: last = json.loads(STATE.read_text())
        except Exception: last = {}
    if last.get("date") == td:
        print(f"오늘({td}) 이미 발송함 — 생략"); return

    mood = "🟢" if ts > 0 else ("🔴" if ts < 0 else "⚪")
    msg = (f"{mood} <b>삼성전자 감성 급변 알림</b>\n"
           f"날짜: {td}\n"
           f"오늘 감성점수: <b>{ts:+.2f}</b> (호재 {tp} · 악재 {tn})\n"
           f"사유: " + " / ".join(reasons) + "\n"
           f'<a href="{PAGE_URL}">→ 대시보드 보기</a>')
    if send(msg):
        STATE.write_text(json.dumps({"date": td, "score": ts, "reasons": reasons}))
        print(f"✓ 알림 발송: {td} {ts:+.2f} | {' / '.join(reasons)}")
    else:
        print("✗ 발송 실패")


if __name__ == "__main__":
    main()
