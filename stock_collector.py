#!/usr/bin/env python3
# 종목 감성 수집기 (analyze_only 키워드 전용). 팟캐스트/에피소드 안 만듦 — 수집+감성분석만.
# 흐름: keywords(analyze_only=1) → Naver/외신 검색 → 본문 → Gemma 감성(tag_one) → stock_sentiment.
# 중복 처리 3중: ① 링크 ② 정규화 제목 해시 ③ e5 의미 유사도(시스템 py3 서브프로세스, char-ngram 폴백).
import os, sys, hashlib, re, math, json, subprocess
from pathlib import Path
from collections import Counter

# DB 자격증명 .env 로드 (db_manager import 전)
_envf = Path("/home/sddari/.config/sosig/.env")
if _envf.exists():
    for _ln in _envf.read_text().splitlines():
        if "=" in _ln and not _ln.strip().startswith("#"):
            _k, _v = _ln.split("=", 1)
            os.environ.setdefault(_k.strip(), _v.strip().strip('"').strip("'"))

sys.path.insert(0, "/mnt/nas/data2/news")
sys.path.insert(0, "/home/sddari/news_sentiment")
import requests
from bs4 import BeautifulSoup
import db_manager
from naver_crawler import get_random_headers, get_news_content, _is_article_relevant
import tagger  # tag_one(title, summary)
import vllm_client  # 외신 제목 한국어 번역용


def translate_title_ko(en):
    """영문 뉴스 제목 → 한국어(외신 표시용). 실패 시 빈 문자열."""
    if not en:
        return ""
    try:
        out = vllm_client.chat(
            system="다음 영문 뉴스 제목을 한국어로 간결하고 자연스럽게 번역한다. 번역문만 출력(따옴표·설명 없이).",
            user=en, max_tokens=128, temperature=0.3, timeout=60).strip()
        return out.strip('"').strip()[:500]
    except Exception:
        return ""

MAX_PER_KW = 12
FOREIGN_QUERY = {"삼성전자": "Samsung Electronics", "SK하이닉스": "SK Hynix"}   # 외신(영문) 검색어 매핑
SEM_THRESHOLD = 0.92          # e5 의미 유사도 — 이 이상이면 같은 사건 중복
NGRAM_THRESHOLD = 0.78        # 폴백(char 3-gram 코사인) 임계값
SYS_PY = "/usr/bin/python3"
EMBED_HELPER = "/mnt/nas/data2/news/embed_dedup.py"


# ── 해시·정규화 ──────────────────────────────────────────────
def _hash(s):
    return hashlib.md5((s or "").encode("utf-8")).hexdigest()


def _norm(title):
    return re.sub(r"[^0-9a-z가-힣]", "", (title or "").lower())


def _title_hash(title):
    return hashlib.md5(_norm(title).encode("utf-8")).hexdigest()


# ── 폴백: char 3-gram 코사인 ─────────────────────────────────
def _ngrams(title, n=3):
    s = _norm(title)
    if len(s) < n:
        return Counter([s]) if s else Counter()
    return Counter(s[i:i + n] for i in range(len(s) - n + 1))


def _cosine(c1, c2):
    if not c1 or not c2:
        return 0.0
    dot = sum(c1[g] * c2[g] for g in (set(c1) & set(c2)))
    n1 = math.sqrt(sum(v * v for v in c1.values()))
    n2 = math.sqrt(sum(v * v for v in c2.values()))
    return dot / (n1 * n2) if n1 and n2 else 0.0


# ── DB ───────────────────────────────────────────────────────
def get_analyze_keywords():
    conn = db_manager.get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT id, keyword FROM keywords WHERE COALESCE(analyze_only,0)=1")
            return cur.fetchall()
    finally:
        conn.close()


def already(stock, link_hash, title_hash):
    conn = db_manager.get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT 1 FROM stock_sentiment WHERE stock=%s AND (link_hash=%s OR title_hash=%s) LIMIT 1",
                        (stock, link_hash, title_hash))
            return cur.fetchone() is not None
    finally:
        conn.close()


def recent_titles(stock, source, days=60, limit=300):
    conn = db_manager.get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT title FROM stock_sentiment WHERE stock=%s AND source=%s "
                        "AND collected_at >= (NOW() - INTERVAL %s DAY) ORDER BY id DESC LIMIT %s",
                        (stock, source, days, limit))
            return [r["title"] for r in cur.fetchall()]
    finally:
        conn.close()


def store(stock, source, title, link, press, sent, score, event, kws, title_ko=""):
    conn = db_manager.get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT IGNORE INTO stock_sentiment "
                "(stock, source, title, title_ko, link, link_hash, title_hash, press, sentiment, score, event, keywords) "
                "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                (stock, source, title[:500], (title_ko or "")[:500], (link or "")[:700], _hash(link),
                 _title_hash(title), (press or "")[:100], sent, score,
                 (event or "")[:60],
                 (",".join(kws) if isinstance(kws, list) else (kws or ""))[:300]))
        conn.commit()
    finally:
        conn.close()


# ── 의미 유사도 dedup (e5 서브프로세스 → 폴백 char-ngram) ─────
def semantic_keep(recent, candidates):
    """candidate별 신규(True)/유사중복(False). e5 실패 시 char-ngram 폴백."""
    if not candidates:
        return []
    try:
        payload = json.dumps({"recent": recent, "candidates": candidates,
                              "threshold": SEM_THRESHOLD})
        r = subprocess.run([SYS_PY, EMBED_HELPER], input=payload,
                           capture_output=True, text=True, timeout=240)
        if r.returncode == 0:
            keep = json.loads(r.stdout).get("keep")
            if isinstance(keep, list) and len(keep) == len(candidates):
                return keep
        print(f"  [의미dedup 폴백] e5 실패(rc={r.returncode}) → char-ngram")
    except Exception as e:
        print(f"  [의미dedup 폴백] {e} → char-ngram")
    # 폴백: char 3-gram 코사인
    seen = [_ngrams(t) for t in recent]
    keep = []
    for t in candidates:
        ng = _ngrams(t)
        dup = any(_cosine(ng, s) >= NGRAM_THRESHOLD for s in seen)
        keep.append(not dup)
        if not dup:
            seen.append(ng)
    return keep


# ── 검색 ─────────────────────────────────────────────────────
def search_naver(query, max_n=MAX_PER_KW):
    from urllib.parse import quote
    url = (f"https://search.naver.com/search.naver?ssc=tab.news.all&query={quote(query)}"
           f"&sm=tab_opt&sort=1&nso=so%3Add")
    try:
        r = requests.get(url, headers=get_random_headers(), timeout=15)
        r.raise_for_status()
    except Exception as e:
        print(f"[검색 실패] {query}: {e}")
        return []
    soup = BeautifulSoup(r.text, "html.parser")
    root = soup.select_one("ul.list_news") or soup
    selectors = [
        lambda c: c and "sds-comps-text-type-headline1" in c,
        lambda c: c and "news_tit" in c,
        lambda c: c and "title" in c.lower() and "news" in c.lower(),
    ]
    heads = []
    for sel in selectors:
        heads = root.find_all(class_=sel)
        if heads:
            break
    out = []
    for h in heads[:max_n]:
        title = h.get_text(strip=True)
        a = h.find_parent("a")
        link = a.get("href", "") if a else ""
        if title and link:
            out.append((title, link))
    return out


def search_foreign(query, max_n=MAX_PER_KW):
    from urllib.parse import quote
    import feedparser
    url = f"https://news.google.com/rss/search?q={quote(query)}&hl=en-US&gl=US&ceid=US:en"
    try:
        feed = feedparser.parse(url, agent=get_random_headers().get("User-Agent", "Mozilla/5.0"))
    except Exception as e:
        print(f"  [외신 검색 실패] {e}")
        return []
    out = []
    for e in feed.entries[:max_n]:
        title = (e.get("title") or "").strip()
        link = (e.get("link") or "").strip()
        press = e.source.title if e.get("source") and e.source.get("title") else ""
        summary = re.sub(r"<[^>]+>", "", e.get("summary", "") or "")
        if title and link:
            out.append((title, link, press, summary))
    return out


# ── 종목별 수집(국내/외신 공통 구조) ─────────────────────────
def collect(stock, source):
    if source == "domestic":
        cands = [(t, l, "", None) for t, l in search_naver(stock)]
    else:
        q = FOREIGN_QUERY.get(stock)
        cands = search_foreign(q) if q else []
    # ① 정확 중복(링크/제목해시) 제거
    cands = [c for c in cands if not already(stock, _hash(c[1]), _title_hash(c[0]))]
    if not cands:
        print(f"  '{stock}' {source}: 신규 0건")
        return 0
    # ② 의미 유사 중복 제거 (최근 제목 대비 + 후보 간)
    keep = semantic_keep(recent_titles(stock, source), [c[0] for c in cands])
    survivors = [c for c, kp in zip(cands, keep) if kp]
    skipped = len(cands) - len(survivors)
    n = 0
    for title, link, press, summary in survivors:
        if source == "domestic":
            content = get_news_content(link) if link else ""
            if content and "본문 내용을 추출할 수 없습니다" in content:
                content = ""
            if content and not _is_article_relevant(title, content, stock):
                continue
            text = content[:1500]
        else:
            text = (summary or "")[:1500]
        try:
            sent, score, secs, tics, event, kw = tagger.tag_one(title, text)
        except Exception as e:
            print(f"  ✗ 감성분석 실패: {e}")
            continue
        tko = translate_title_ko(title) if source == "foreign" else ""
        store(stock, source, title, link, press, sent, score, event, kw, tko)
        n += 1
        print(f"  +[{source[:3]} {sent} {score:+.2f}]")
    print(f"  '{stock}' {source}: 신규 {n}건 (유사중복 {skipped} 스킵)")
    return n


def run():
    kws = get_analyze_keywords()
    if not kws:
        print("analyze_only 키워드 없음 — 종료")
        return
    print(f"=== 종목 감성 수집: {len(kws)}개 키워드 ===")
    for k in kws:
        stock = k["keyword"]
        print(f"\n>>> '{stock}'")
        collect(stock, "domestic")
        collect(stock, "foreign")


if __name__ == "__main__":
    run()
