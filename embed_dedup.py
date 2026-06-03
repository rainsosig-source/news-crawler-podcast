#!/usr/bin/env python3
# 의미 유사도 중복 판정 헬퍼 — 시스템 python3로 실행(torch+sentence-transformers 보유).
# stdin JSON: {"recent":[제목...], "candidates":[제목...], "threshold":0.92}
# stdout JSON: {"keep":[bool...]}  candidate별 신규(True)/유사중복(False).
import sys, json


def main():
    data = json.load(sys.stdin)
    recent = data.get("recent", []) or []
    cands = data.get("candidates", []) or []
    thr = float(data.get("threshold", 0.92))
    if not cands:
        print(json.dumps({"keep": []}))
        return
    from sentence_transformers import SentenceTransformer
    import numpy as np
    m = SentenceTransformer("intfloat/multilingual-e5-small", device="cpu")
    all_t = recent + cands
    vecs = m.encode(["query: " + (t or "") for t in all_t],
                    normalize_embeddings=True).astype("float32")
    rv = list(vecs[:len(recent)])
    cv = vecs[len(recent):]
    kept = list(rv)            # recent + 이번에 채택된 candidate
    keep = []
    for i in range(len(cands)):
        v = cv[i]
        dup = any(float(v @ kvec) >= thr for kvec in kept)
        keep.append(not dup)
        if not dup:
            kept.append(v)
    print(json.dumps({"keep": keep}))


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        sys.stderr.write(f"embed_dedup error: {e}\n")
        sys.exit(1)
