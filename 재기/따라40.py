#!/usr/bin/env python3
"""40단계 L 따라가기(문서/40단계.md '갈래' L) — llama.cpp C API(재기/라마.py)로 G 의 답을 따라가며 걸음마다 L 의 분포를 잰다.

프롬프트는 한 번에(llama.cpp 의 프롬프트 길), G 의 답 토큰은 하나씩 넣는다(생성할 때와 같은 셈의 길) — 줄 여덟을 함께(llama-server -np 8 처럼).
걸음 t 마다 적는 것: G 의 상위 20 번호에서 L 의 로그확률(20), L 의 1위 번호와 그 로그확률.

  python -I -X utf8 재기/따라40.py --모델 7b|r1|05b --작업 W --모델폴더 M --llama LL [--확인] [--통합KV 0|1]

--확인: 40a (5) — 모음40.py 확인L 의 50 문항을 줄 하나로(llama-server -np 1 · -c 3584 와 같은 설정) 따라가, 첫 갈림까지의 모든 걸음에서
L 의 1위가 llama-server 가 실제로 낸 토큰과 같은지 본다.
"""
import argparse
import ctypes
import json
import os
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)


def 기록(*a):
    print(time.strftime("%H:%M:%S"), *a, flush=True)


def 로그확률들(행, 번호들):
    x = 행.astype(np.float64)
    m = x.max()
    lse = m + np.log(np.exp(x - m).sum())
    i1 = int(np.argmax(행))
    return x[번호들] - lse, i1, x[i1] - lse


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--모델", required=True)
    ap.add_argument("--작업", required=True)
    ap.add_argument("--모델폴더", required=True)
    ap.add_argument("--llama", required=True)
    ap.add_argument("--확인", action="store_true")
    ap.add_argument("--통합KV", type=int, default=-1, help="-1: llama-server 의 기록에서 읽는다")
    a = ap.parse_args()
    os.environ["GEULPU_LLAMA"] = a.llama
    import 라마 as LM
    import 모음40 as MO
    from 셈40 import 색인
    GGUF = os.path.join(a.모델폴더, MO.GGUF[a.모델])
    토 = MO.jsonl읽기(os.path.join(a.작업, "토큰", f"{a.모델}.jsonl"))
    G = 색인(os.path.join(a.작업, "생성", f"G_{a.모델}.jsonl"))          # 답은 그때그때 읽는다(걸음마다 상위 20 — 크다)

    통합 = a.통합KV
    if 통합 < 0:
        로그 = os.path.join(a.작업, "logs", f"서버_{'L1' if a.확인 else 'L'}_{a.모델}.log")
        글 = open(로그, encoding="utf-8", errors="replace").read() if os.path.exists(로그) else ""
        import re
        통합 = 1 if re.search(r"kv_unified\s*=\s*'?true", 글) else 0
        기록(f"llama-server 의 kv_unified: {'참' if 통합 else '거짓'} (기록 {os.path.basename(로그)})")

    if a.확인:
        recs = [r["id"] for r in MO.확인문항(a.작업, a.모델)]
        n_seq, n_ctx = 1, MO.문맥
        폴더 = os.path.join(a.작업, "따라", f"확인_{a.모델}")
    else:
        recs = sorted(G.keys())
        n_seq, n_ctx = MO.슬롯, MO.문맥 * MO.슬롯
        폴더 = os.path.join(a.작업, "따라", a.모델)
    os.makedirs(폴더, exist_ok=True)
    할 = [k for k in recs if not os.path.exists(os.path.join(폴더, k + ".npz"))]
    기록(f"따라가기 {a.모델}{' (확인)' if a.확인 else ''}: {len(할)} 문항 / {len(recs)} · 줄 {n_seq} · 문맥 {n_ctx} · 통합KV {통합}")
    if not 할:
        return 확인셈(a, 폴더, MO) if a.확인 else None

    L = LM.라마(GGUF, n_ctx=n_ctx, n_batch=2048, n_ubatch=512, n_seq_max=n_seq, flash=-1, kv형식=1, 통합KV=bool(통합))
    L.L.llama_memory_seq_rm.restype = ctypes.c_bool
    L.L.llama_memory_seq_rm.argtypes = [ctypes.c_void_p, ctypes.c_int32, ctypes.c_int32, ctypes.c_int32]
    mem = L.L.llama_get_memory(L.ctx)
    기록("문맥 기록:", " ".join(l.strip() for l in L.문맥로그.splitlines() if "flash" in l or "unified" in l or "n_ctx" in l)[:400])

    줄 = [None] * n_seq                  # 줄마다: dict(rec, P, O, k, 결과들)
    대기 = list(할)
    t0 = time.time()
    끝낸 = [0, 0]

    def 시작(s, k):
        r = G[k]
        L.L.llama_memory_seq_rm(mem, s, -1, -1)
        P = 토[r["id"]]["ids"]
        O = r["tokens"]
        상 = r["top_ids"]
        n = len(O)
        st = {"rec": r, "P": P, "O": O, "상": 상, "k": 0, "lp": np.zeros((n, 20), np.float32), "a1": np.zeros(n, np.int32),
              "a1lp": np.zeros(n, np.float32)}
        # 프롬프트: n_batch 씩, 마지막 줄만 로짓
        for c0 in range(0, len(P), 2048):
            청 = P[c0:c0 + 2048]
            마지막 = c0 + len(청) == len(P)
            L.넣기(청, list(range(c0, c0 + len(청))), [s] * len(청), [0] * (len(청) - 1) + [1 if 마지막 else 0])
        행 = L.로짓(len(P) - 1 - (len(P) - 1) // 2048 * 2048)
        적기(st, 0, 행)
        st["k"] = 1
        줄[s] = st

    def 적기(st, k, 행):
        ids = st["상"][k] if k < len(st["상"]) else []        # 끝 토큰의 걸음은 G 의 상위 목록에 없다
        ids = (ids + [ids[-1]] * 20)[:20] if ids else [0] * 20
        lp, i1, l1 = 로그확률들(행, np.asarray(ids, np.int64))
        st["lp"][k] = lp
        st["a1"][k] = i1
        st["a1lp"][k] = l1

    def 끝내기(s):
        st = 줄[s]
        np.savez(os.path.join(폴더, st["rec"]["id"] + ".npz"), lp=st["lp"], a1=st["a1"], a1lp=st["a1lp"])
        끝낸[0] += 1
        끝낸[1] += len(st["O"])
        줄[s] = None
        if 끝낸[0] % 25 == 0:
            기록(f"  {끝낸[0]}/{len(할)} · 걸음 {끝낸[1]} · {끝낸[1] / (time.time() - t0):.0f} 걸음/초")

    while 대기 or any(줄):
        for s in range(n_seq):
            while 줄[s] is None and 대기:
                시작(s, 대기.pop(0))
                if 줄[s]["k"] >= len(줄[s]["O"]):
                    끝내기(s)
        활 = [s for s in range(n_seq) if 줄[s] is not None]
        if not 활:
            continue
        토큰들 = [줄[s]["O"][줄[s]["k"] - 1] for s in 활]
        위치들 = [len(줄[s]["P"]) + 줄[s]["k"] - 1 for s in 활]
        L.넣기(토큰들, 위치들, 활, [1] * len(활))
        for i, s in enumerate(활):
            적기(줄[s], 줄[s]["k"], L.로짓(i))
            줄[s]["k"] += 1
            if 줄[s]["k"] >= len(줄[s]["O"]):
                끝내기(s)
    L.닫기()
    기록(f"따라가기 끝 — {끝낸[0]} 문항 · {끝낸[1]} 걸음 · {time.time() - t0:.0f} 초")
    if a.확인:
        확인셈(a, 폴더, MO)


def 확인셈(a, 폴더, MO):
    """40a (5): 첫 갈림(L1 의 토큰 ≠ G 의 토큰)까지의 모든 걸음에서 따라가기의 1위 = L1 의 토큰."""
    from 셈40 import 색인
    G = 색인(os.path.join(a.작업, "생성", f"G_{a.모델}.jsonl"))
    L1 = MO.jsonl읽기(os.path.join(a.작업, "생성", f"L1확인_{a.모델}.jsonl"))
    n문 = n걸 = n같 = 0
    틀림 = []
    for k, l1 in L1.items():
        f = os.path.join(폴더, k + ".npz")
        if not os.path.exists(f):
            continue
        a1 = np.load(f)["a1"]
        g, lt = G[k]["tokens"], l1["tokens"]
        n문 += 1
        for t in range(min(len(g), len(lt), len(a1))):
            n걸 += 1
            if int(a1[t]) == lt[t]:
                n같 += 1
            else:
                틀림.append((k, t))
            if lt[t] != g[t]:
                break
    out = {"문항": n문, "걸음": n걸, "같음": n같, "다름": 틀림[:20]}
    json.dump(out, open(os.path.join(a.작업, "따라", f"확인_{a.모델}.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    기록(f"확인 — 문항 {n문} · 걸음 {n걸} · 1위 같음 {n같} · 다름 {len(틀림)}")


if __name__ == "__main__":
    main()
