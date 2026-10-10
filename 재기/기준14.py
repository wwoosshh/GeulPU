#!/usr/bin/env python3
"""14단계 판정 전에 재는 것 — Qwen2.5-0.5B-Instruct Q8_0(공식 GGUF)에서 llama.cpp b11496(CUDA, 기본 설정 — KV F16 · 플래시 어텐션 자동)의
(1) 숨은 손실: GGUF 의 가중치를 그대로 푼 fp64 참값 대비 — 평가글 512 토큰의 모든 행 로짓(KL(참 ‖ x) 평균 · 고른 토큰 일치 · 행 상대차
    중앙값), 채팅 질문 셋 × 탐욕 64 걸음의 걸음마다 로짓의 상대차 중앙값,
(2) 속도: 프롬프트 128 · 512 · 2048 · 8192 토큰(+ 첫 토큰), 생성 토큰당(문맥 채팅 · 1024 · 8192 — (65 토큰 − 1 토큰) / 64),
(3) 바닥(가중치 · KV 를 한 번 읽기 · int8 최고치).
결과는 빌드/결과/기준14.json. 실행: python 재기/기준14.py
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
sys.path.insert(0, os.path.join(T.ROOT, "엔진"))
import 토크나이저 as TK       # noqa: E402
import 참값                   # noqa: E402

폴더 = os.path.join(T.모델, "qwen2.5-0.5b-instruct")
GGUF = os.path.join(T.모델, "qwen2.5-0.5b-instruct-gguf", "qwen2.5-0.5b-instruct-q8_0.gguf")
질문들 = ["What is the capital of France? Answer in one word.", "대한민국의 수도는 어디야? 한 단어로 답해.",
         "Write a short poem about the sea."]


def lsm(x):
    x = x.astype(np.float64)
    x = x - x.max(-1, keepdims=True)
    return x - np.log(np.exp(x).sum(-1, keepdims=True))


def 견줌(x, ref):
    """로짓 x 를 참값 ref 와 (행마다): KL(ref ‖ x) 평균, 고른 토큰 일치율, 행 상대차 중앙값."""
    lx, lr = lsm(x), lsm(ref)
    kl = (np.exp(lr) * (lr - lx)).sum(-1)
    rel = np.linalg.norm(x.astype(np.float64) - ref, axis=-1) / np.linalg.norm(ref, axis=-1)
    return {"KL 평균": float(kl.mean()), "고른 토큰 일치": float((x.argmax(-1) == ref.argmax(-1)).mean()),
            "상대차 중앙값": float(np.median(rel))}


def main():
    tk = TK.Qwen토크나이저(폴더)
    res = {"모델": os.path.basename(GGUF), "llama.cpp": "b11496 (000bee54a), 기본 설정(KV F16, 플래시 어텐션 자동)"}
    Wq, 설정 = 참값.qwen2_gguf(GGUF)
    글 = tk.나누기(open(T.평가글, encoding="utf-8").read())[:512]
    t0 = time.time()
    양참 = 참값.qwen2_로짓(Wq, 설정, 글)
    print("참값", round(time.time() - t0, 1), "초", flush=True)
    일 = E.일꾼()
    try:
        라 = E.라마엔진(일, "llama.cpp q8_0", GGUF, n_ctx=16384, n_batch=2048, n_ubatch=512)
        res["llama.cpp 문맥"] = 라.문맥
        lx = 라.로짓들([글])
        res["숨은 손실 — 평가글 512 토큰 (GGUF 참값 대비)"] = 견줌(lx, 양참)
        print("숨은 손실", res["숨은 손실 — 평가글 512 토큰 (GGUF 참값 대비)"], flush=True)
        del lx, 양참
        생성 = {}
        for q in 질문들:
            ids = tk.나누기(TK.채팅틀([{"role": "user", "content": q}]))
            toks, logs = 라.생성로짓(ids, 64)
            ref = 참값.qwen2_로짓(Wq, 설정, ids + toks[:-1])[len(ids) - 1:]
            rel = np.linalg.norm(logs.astype(np.float64) - ref, axis=-1) / np.linalg.norm(ref, axis=-1)
            끝 = toks.index(tk.특수["<|im_end|>"]) if tk.특수["<|im_end|>"] in toks else len(toks)
            생성[q] = {"답": tk.잇기(toks[:끝]), "걸음마다 상대차 중앙값": float(np.median(rel)),
                     "참값과 고른 토큰이 다른 걸음": int((ref.argmax(-1) != np.asarray(toks)).sum())}
            print("생성", q, 생성[q], flush=True)
        res["생성 64 걸음 — GGUF 참값 대비"] = 생성
        # 속도
        긴 = (tk.나누기(T.문장들[1]) * 400)[:8192]
        p = {}
        for n in (128, 512, 2048, 8192):
            라.프롬프트(긴[:n])
            p[str(n)] = round(float(np.median([라.잰_프롬프트(긴[:n]) for _ in range(7)])), 3)
            print("프롬프트", n, p[str(n)], "ms", flush=True)
        res["프롬프트 ms (처리 + 첫 토큰, 일곱 번 중앙값)"] = p
        g = {}
        채팅 = tk.나누기(TK.채팅틀([{"role": "user", "content": 질문들[2]}]))
        for 이름, ids in (("채팅 질문", 채팅), ("문맥 1024", 긴[:1024]), ("문맥 8192", 긴[:8192])):
            라.생성(ids, 65)
            t1 = np.median([라.잰_생성(ids, 1) for _ in range(5)])
            t65 = np.median([라.잰_생성(ids, 65) for _ in range(5)])
            g[이름] = round(float((t65 - t1) / 64), 4)
            print("생성", 이름, g[이름], "ms/토큰", flush=True)
        res["생성 ms/토큰"] = g
        라.닫기()
    finally:
        일.끝()
    # 바닥: 가중치 바이트(Q8_0 — 34 바이트 / 32 값)와 KV(f16 기준 — 층 24 × KV 머리 2 × 64 × 2 × 2 바이트 / 위치), 504 GB/s
    층값 = 24 * (896 * 896 * 2 + 896 * 128 * 2 + 3 * 896 * 4864)
    출력값 = 151936 * 896
    가중바이트 = (층값 + 출력값) * 34 / 32
    res["바닥"] = {"생성 가중치 바이트": int(가중바이트), "생성 바닥 ms (KV 빼고)": round(가중바이트 / 504e9 * 1000, 3),
                 "위치마다 KV 바이트 (f16)": 24 * 2 * 64 * 2 * 2,
                 "프롬프트 n 의 선형 층 int8 일 (자리 둘, 곱 + 합)": "2 · 2 · 층값 · n / 3.2e14 초",
                 "프롬프트 2048 선형 바닥 ms (자리 둘)": round(2 * 2 * 층값 * 2048 / 3.2e14 * 1000, 3)}
    print("바닥", res["바닥"], flush=True)
    os.makedirs(T.결과폴더, exist_ok=True)
    json.dump(res, open(os.path.join(T.결과폴더, "기준14.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("빌드/결과/기준14.json")


if __name__ == "__main__":
    main()
