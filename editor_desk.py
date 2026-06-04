#!/usr/bin/env python3
# 에이전틱 뉴스 데스크 T1 — 편집장 에이전트(로컬 vLLM Gemma, claude CLI 미사용).
# 입력: 전 키워드 후보 헤드라인. 출력: 사건 클러스터링 + 중요도 랭킹 + 키워드간 중복통합 후
#       '오늘 다룰' 스토리 선별 + 앵글. build_brief()는 link→{importance,angle,cluster} dict.
# 실패 시 None 반환 → 호출측은 게이팅 없이 기존 동작으로 폴백(무중단 보장).
import json
import re
import sys

sys.path.insert(0, "/home/sddari/scripts")
import vllm_client

MAX_SELECT = 8

SYSTEM = """너는 한국어 경제·기술 뉴스 편집장이다. 아래는 이번 시간대에 수집된 뉴스 후보 헤드라인 목록이다(여러 주제 키워드에서 모음).
다음을 수행해 '오늘 팟캐스트로 다룰 기사'를 고른다.

1. 같은 사건을 다룬 중복 기사는 하나의 클러스터로 묶는다(키워드가 달라도 같은 사건이면 묶음).
2. 각 클러스터의 뉴스 가치를 평가한다: 파급력·신선도·독자 관심·구체성. 단순 시황 나열, 광고성, 추측성 제목은 낮게.
3. 가치 높은 순으로 최대 N개의 '서로 다른' 스토리를 고른다. 클러스터당 대표 기사 1개만.
4. 각 선택에 대해 한 문장 '앵글'(어떤 관점으로 다룰지)을 쓴다.

반드시 아래 JSON만 출력한다(설명·코드펜스 금지):
{"selected":[{"i":<후보번호>,"importance":<1~10>,"cluster":"<사건 요약 5~12자>","angle":"<한 문장 앵글>"}]}
중요도 동률이면 더 구체적·신선한 것을 우선. 광고/추측/단순중복은 제외."""


def _parse_json(text):
    text = text.strip()
    text = re.sub(r"^```[a-zA-Z]*\n?|\n?```$", "", text.strip())
    # 첫 { 부터 마지막 } 까지
    a, b = text.find("{"), text.rfind("}")
    if a == -1 or b == -1:
        return None
    return json.loads(text[a:b + 1])


def build_brief(candidates, max_select=MAX_SELECT):
    """candidates: [{keyword,title,link,press,...}] → {link: {importance,angle,cluster}} 또는 None."""
    if not candidates:
        return None
    lines = []
    for i, c in enumerate(candidates):
        lines.append(f"{i}. [{c.get('keyword','')}] {c.get('title','')} ({c.get('press','')})")
    user = (f"후보 {len(candidates)}건. 최대 {max_select}개 선택.\n\n" + "\n".join(lines))
    try:
        out = vllm_client.chat(system=SYSTEM, user=user, max_tokens=2048,
                               temperature=0.3, timeout=300)
        data = _parse_json(out)
        if not data or "selected" not in data:
            print("[편집장] JSON 파싱 실패 → 폴백")
            return None
        allow = {}
        for s in data["selected"][:max_select]:
            try:
                idx = int(s["i"])
            except (KeyError, ValueError, TypeError):
                continue
            if 0 <= idx < len(candidates):
                link = candidates[idx].get("link")
                if link:
                    allow[link] = {
                        "importance": s.get("importance", 0),
                        "angle": (s.get("angle") or "").strip(),
                        "cluster": (s.get("cluster") or "").strip(),
                    }
        return allow or None
    except Exception as e:
        print(f"[편집장] 실패 → 폴백: {e}")
        return None


if __name__ == "__main__":
    # 드라이런: 표준입력 JSON [{keyword,title,link,press}] 또는 내장 샘플
    raw = sys.stdin.read().strip() if not sys.stdin.isatty() else ""
    if raw:
        cands = json.loads(raw)
    else:
        cands = [
            {"keyword": "반도체", "title": "삼성전자 HBM4 양산 임박…엔비디아 공급 가시화", "link": "L1", "press": "전자신문"},
            {"keyword": "증시", "title": "코스피 2700 회복, 외국인 순매수 전환", "link": "L2", "press": "한경"},
            {"keyword": "인공지능", "title": "삼성 HBM4 엔비디아 납품 협상 막바지", "link": "L3", "press": "머니투데이"},
            {"keyword": "경제", "title": "[속보] 한은 기준금리 동결", "link": "L4", "press": "연합"},
            {"keyword": "증시", "title": "오늘의 추천주 TOP5 공개", "link": "L5", "press": "광고성매체"},
        ]
    brief = build_brief(cands)
    print(json.dumps(brief, ensure_ascii=False, indent=2))
