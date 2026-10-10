#!/usr/bin/env python3
"""14단계 판정의 공식 측정 — Qwen2.5-0.5B-Instruct Q8_0 (공식 GGUF), 글(GeulPU) 대 llama.cpp b11496 (기본 설정 — KV F16 · 플래시 어텐션 자동).
판정 기준(문서/14단계.md)은 측정보다 먼저 커밋했다(0a3c012). llama.cpp 의 정확도는 판정 전에 잰 값(빌드/결과/기준14.json — 같은 재는 법).

  python 재기/재기14.py [정확도] [속도]

  14b 정확도 — GGUF 의 가중치를 그대로 푼 fp64 참값(시험/참값.py) 대비: 평가글(Qwen 토크나이저로 461 토큰 — 기준14 와 같은 [:512])의 모든 행
               로짓의 KL(참 ‖ 글) 평균 · 고른 토큰 일치 · 행 상대차 중앙값, 채팅 질문 셋 × 탐욕 64 걸음의 걸음마다 로짓 상대차 중앙값.
  14c 생성 — 토큰당 = (65 토큰 − 1 토큰) / 64 (기준14 와 같은 식): 채팅 질문(셋째) · 문맥 1024 · 8192, 엔진을 번갈아 일곱 번 × 세 묶음.
  14d 프롬프트 — 처리 + 첫 토큰: 128 · 512 · 2048 · 8192 토큰(문장 1 의 되풀이 — 기준14 와 같은 열), 엔진을 번갈아 일곱 번 × 세 묶음.
결과는 빌드/결과/재기14.json.
"""
import json
import os
import sys
import time

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.stderr.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import numpy as np            # noqa: E402

import 엔진들 as E            # noqa: E402

T = E.T
sys.path.insert(0, os.path.join(T.ROOT, "시험"))
import qwen2공통 as Q         # noqa: E402
import 기준14 as B            # noqa: E402


class 글큐엔진(E.글엔진):
    """엔진들.글엔진 과 같은 일(프롬프트 · 생성 · 잰_…)을 글Qwen2 로."""
    이름 = "글"

    def __init__(self, 이름=None, **kw):
        import 글qwen2
        self.m = 글qwen2.글Qwen2(Q.GGUF, **kw)
        self.m.판미리고르기()
        if 이름:
            self.이름 = 이름


def 정확도(res):
    import 참값
    tk = Q.토크나이저()
    기준 = json.load(open(os.path.join(T.결과폴더, "기준14.json"), encoding="utf-8"))
    Wq, 설정 = 참값.qwen2_gguf(Q.GGUF)
    글 = tk.나누기(open(T.평가글, encoding="utf-8").read())[:512]
    n = len(글)
    양참 = 참값.qwen2_로짓(Wq, 설정, 글)
    m = Q.엔진(최대행=1024, 최대길이=4096, 로짓행=512)
    m.토큰넣기(글)
    m.계산(1, n, 0, "전부")
    g = m.로짓(n).copy()
    r = {"평가글 토큰": n, "글": B.견줌(g, 양참), "llama.cpp (기준14)": 기준["숨은 손실 — 평가글 512 토큰 (GGUF 참값 대비)"]}
    r["KL 비 (글 / llama.cpp)"] = r["글"]["KL 평균"] / r["llama.cpp (기준14)"]["KL 평균"]
    print("숨은 손실", r, flush=True)
    res["14b 숨은 손실 — 평가글 (GGUF 참값 대비)"] = r
    생성 = {}
    for q in Q.질문들:
        ids = Q.채팅(tk, q)
        toks, logs = m.생성로짓(ids, 64)
        ref = 참값.qwen2_로짓(Wq, 설정, ids + toks[:-1])[len(ids) - 1:]
        rel = np.linalg.norm(logs.astype(np.float64) - ref, axis=-1) / np.linalg.norm(ref, axis=-1)
        끝 = toks.index(tk.특수["<|im_end|>"]) if tk.특수["<|im_end|>"] in toks else len(toks)
        라 = 기준["생성 64 걸음 — GGUF 참값 대비"][q]
        생성[q] = {"답": tk.잇기(toks[:끝]), "글 — 걸음마다 상대차 중앙값": float(np.median(rel)),
                 "글 — 참값과 고른 토큰이 다른 걸음": int((ref.argmax(-1) != np.asarray(toks)).sum()),
                 "llama.cpp — 걸음마다 상대차 중앙값": 라["걸음마다 상대차 중앙값"], "llama.cpp 답": 라["답"],
                 "비 (글 / llama.cpp)": float(np.median(rel)) / 라["걸음마다 상대차 중앙값"]}
        print("생성", q, 생성[q], flush=True)
    res["14b 생성 64 걸음 — GGUF 참값 대비"] = 생성
    res["오류 칸 (정확도)"] = m.오류칸()
    m.닫기()
    del Wq
    T.비우기()


def 속도(res):
    tk = Q.토크나이저()
    긴 = (tk.나누기(T.문장들[1]) * 400)[:8192]
    채팅 = Q.채팅(tk, Q.질문들[2])
    일 = E.일꾼()
    실패 = res.setdefault("실패", {})
    try:
        글 = 글큐엔진(최대행=8192, 최대길이=16384, 로짓행=64)
        라 = E.라마엔진(일, "llama.cpp", Q.GGUF, n_ctx=16384, n_batch=2048, n_ubatch=512)
        res["llama.cpp 문맥"] = 라.문맥
        엔진들 = [글, 라]
        p = {}
        for n in (128, 512, 2048, 8192):
            ids = 긴[:n]
            E.데우기(엔진들, lambda e: e.프롬프트(ids), 실패)
            중, 묶음 = E.세묶음(엔진들, lambda e: e.잰_프롬프트(ids), 실패)
            p[str(n)] = {"중앙값 ms": 중, "세 묶음": 묶음}
            print("프롬프트", n, 중, flush=True)
        res["14d 프롬프트 ms (처리 + 첫 토큰)"] = p
        g = {}
        for 이름, ids in (("채팅 질문", 채팅), ("문맥 1024", 긴[:1024]), ("문맥 8192", 긴[:8192])):
            E.데우기(엔진들, lambda e: e.생성(ids, 65), 실패)
            t1, _ = E.세묶음(엔진들, lambda e: e.잰_생성(ids, 1), 실패)
            t65, _ = E.세묶음(엔진들, lambda e: e.잰_생성(ids, 65), 실패)
            g[이름] = {k: round((t65[k] - t1[k]) / 64, 4) for k in t1 if k in t65}
            print("생성", 이름, g[이름], flush=True)
        res["14c 생성 ms/토큰"] = g
        res["오류 칸 (속도)"] = 글.m.오류칸()
        라.닫기()
        글.닫기()
    finally:
        일.끝()


def main():
    부분 = set(sys.argv[1:]) or {"정확도", "속도"}
    경로 = os.path.join(T.결과폴더, "재기14.json")
    res = json.load(open(경로, encoding="utf-8")) if os.path.exists(경로) else {}
    res["GPU"] = "RTX 4070 Ti"
    t0 = time.time()
    if "정확도" in 부분:
        정확도(res)
    if "속도" in 부분:
        속도(res)
    res["초"] = round(time.time() - t0, 1)
    os.makedirs(T.결과폴더, exist_ok=True)
    json.dump(res, open(경로, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("빌드/결과/재기14.json")


if __name__ == "__main__":
    main()
