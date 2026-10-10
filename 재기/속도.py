#!/usr/bin/env python3
"""속도 견주기 — GeulPU 대 llama.cpp b11496(CUDA, 도구/llama-b11496) · PyTorch f16 참고선. 결과는 빌드/결과/속도.json.

  python 재기/속도.py [프롬프트] [생성] [긴넣기] [긴생성] [대화] [오래] [small] [XL]

고르지 않으면 모두(한 시간 남짓). 재는 법은 연구 12~13단계 그대로:
  프롬프트 — 문장의 되풀이 128 · 512 · 1024 토큰(XL; small 은 1024)의 처리 + 첫 토큰, 엔진을 번갈아 일곱 번의 중앙값(+ PyTorch f16 참고선)
  생성 — 짧은 문맥(문장 1) · 문맥 960 에서 64 토큰 탐욕 생성의 토큰당 시간 = (64 토큰 − 1 토큰) / 63, 번갈아 일곱 번 × 세 묶음
  긴넣기 — 합성 긴 모델, 문맥을 1024 덩이로 C(8192 · 32768 · 65536 · 98304)까지 채운 뒤 덩이 m(16 … 1024)을 세 번, 중앙값
  긴생성 — 합성 긴 모델, 문맥 32704 · 102336 에서의 생성 토큰당 시간
  대화 — 합성 긴 모델, 차례마다 덩이 16~1024 · 생성 16~128(무작위, 같은 씨앗), 문맥 10만까지, 구간(12800 씩)마다 중앙값
  오래 — XL Q8_0, 문맥 1024 안의 대화를 10 초 창으로 두 엔진 번갈아 2 분
"""
import json
import os
import subprocess
import sys
import time

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.stderr.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import numpy as np            # noqa: E402

import 엔진들 as E            # noqa: E402

T, G = E.T, E.G
GR = T.GR
N = 64


def 바닥ms(C_):
    """짧은 덩이 넣기의 바닥 — K · V 를 한 번 읽기: 층 12 × 머리 12 × 위치 × 256 바이트 / 504 GB/s, 가중치 0.17 ms 더해."""
    return 12 * 12 * C_ * 256 / 504e9 * 1000 + 0.17


def 프롬프트생성(일, 크기들, 부분, res):
    for 크기 in 크기들:
        tk = T.토크나이저(크기)
        prompts = [tk.나누기(s) for s in T.문장들]
        긴 = (tk.나누기(T.문장들[1]) * 40)[:1024]
        if "프롬프트" in 부분:
            try:
                res["프롬프트"][f"PyTorch f16 참고선 {크기}"] = E.참고선(크기, (128, 512, 1024))
            except ImportError:
                res["프롬프트"][f"PyTorch f16 참고선 {크기}"] = "torch 가 없다"
        for fmt in ("q8_0", "q4_0"):
            path = T.경로(크기, fmt)
            if not T.있나(path):
                continue
            글 = E.글엔진(GR.gpt2정수(path), 이름=f"글 {fmt}", KV형식="정수", 자리수=2)
            라 = E.라마엔진(일, f"llama.cpp {fmt}", path)
            엔진들 = [글, 라]
            실패 = res.setdefault("실패", {})
            if "프롬프트" in 부분:
                c = {}
                for n in ((128, 512, 1024) if 크기 == "XL" else (1024,)):
                    ids = 긴[:n]
                    E.데우기(엔진들, lambda e: e.프롬프트(ids), 실패)
                    c[str(n)] = E.번갈아(엔진들, lambda e: e.잰_프롬프트(ids), 7, 실패)
                    print("프롬프트", 크기, fmt, n, c[str(n)], flush=True)
                res["프롬프트"][f"{크기} {fmt}"] = c
            if "생성" in 부분:
                d = {}
                for 이름, ids in (("짧은 문맥 (문장 1)", prompts[0]), ("문맥 960", 긴[:960])):
                    E.데우기(엔진들, lambda e: e.생성(ids, N), 실패)
                    t1, _ = E.세묶음(엔진들, lambda e: e.잰_생성(ids, 1), 실패)
                    t64, _ = E.세묶음(엔진들, lambda e: e.잰_생성(ids, N), 실패)
                    d[이름] = {k: round((t64[k] - t1[k]) / (N - 1), 4) for k in t1 if k in t64}
                    print("생성", 크기, fmt, 이름, d[이름], flush=True)
                res["생성"][f"{크기} {fmt}"] = d
            라.닫기()
            글.닫기()
            T.비우기()


def 긴넣기(일, Cs=(8192, 32768, 65536, 98304), ms=(16, 64, 128, 256, 512, 1024), 씨=13):
    wq = GR.gpt2정수(T.긴GGUF)
    글 = E.글엔진(wq, KV형식="정수", 자리수=2, 최대행=1024, 최대문장=1, 최대길이=102400, 로짓행=16)
    글.m.판미리고르기()
    라 = E.라마엔진(일, "llama.cpp q8_0", T.긴GGUF, n_ctx=102400, n_batch=1024)
    rng = np.random.default_rng(씨)
    끝 = {"글": 0, "라": 0}
    위치, 처음 = 0, True
    칸들 = {}
    for C_ in Cs:
        while 위치 + 1024 <= C_:
            새 = [int(x) for x in rng.integers(0, 50257, 1023)]
            for 이름, e in (("글", 글), ("라", 라)):
                끝[이름] = e.대화([[끝[이름]] + 새], 1, 처음=처음)[0]["끝토큰"]
            처음 = False
            위치 += 1024
        for m_ in ms:
            if 위치 + 3 * m_ + 8 > 102400:
                break
            줄들 = []
            for _ in range(3):
                새 = [int(x) for x in rng.integers(0, 50257, m_ - 1)]
                줄 = {"문맥": 위치}
                for 이름, e in (("글", 글), ("라", 라)):
                    r = e.대화([[끝[이름]] + 새], 1, 처음=False)[0]
                    끝[이름] = r["끝토큰"]
                    줄[이름] = r["넣기 ms"]
                위치 += m_
                줄들.append(줄)
            g_, l_ = float(np.median([x["글"] for x in 줄들])), float(np.median([x["라"] for x in 줄들]))
            칸 = {"글 ms": round(g_, 2), "llama.cpp ms": round(l_, 2), "글 / llama.cpp": round(g_ / l_, 3)}
            if m_ == 16:
                칸["바닥 ms"] = round(바닥ms(줄들[0]["문맥"]), 2)
            칸들[f"{C_} × {m_}"] = 칸
            print("긴넣기", C_, m_, 칸, flush=True)
    라.닫기()
    글.닫기()
    return 칸들


def 긴생성(일):
    out = {}
    wq = GR.gpt2정수(T.긴GGUF)
    ids전체 = [int(x) for x in np.random.default_rng(1).integers(0, 50257, 102400)]
    for C_ in (32768, 102400):
        ids = ids전체[:C_]
        라 = E.라마엔진(일, "llama.cpp q8_0", T.긴GGUF, n_ctx=C_, n_batch=2048)
        라.생성(ids[:-64], N)
        t1 = np.median([라.잰_생성(ids[:-64], 1) for _ in range(3)])
        t64 = np.median([라.잰_생성(ids[:-64], N) for _ in range(3)])
        d = {라.이름: round(float((t64 - t1) / (N - 1)), 4)}
        라.닫기()
        글 = E.글엔진(wq, KV형식="정수", 자리수=2, 최대행=C_, 최대문장=1, 최대길이=C_, 로짓행=16)
        글.생성(ids[:-64], N)
        t1 = np.median([글.잰_생성(ids[:-64], 1) for _ in range(3)])
        t64 = np.median([글.잰_생성(ids[:-64], N) for _ in range(3)])
        d[글.이름] = round(float((t64 - t1) / (N - 1)), 4)
        글.닫기()
        T.비우기()
        out[f"문맥 {C_ - 64}"] = d
        print("긴생성", C_ - 64, d, flush=True)
    return out


def 대화(일, 최대=100000, 씨=12):
    wq = GR.gpt2정수(T.긴GGUF)
    글 = E.글엔진(wq, KV형식="정수", 자리수=2, 최대행=1024, 최대문장=1, 최대길이=102400, 로짓행=16)
    글.m.판미리고르기()
    라 = E.라마엔진(일, "llama.cpp q8_0", T.긴GGUF, n_ctx=102400, n_batch=1024)
    rng = np.random.default_rng(씨)
    끝 = {"글": 0, "라": 0}
    기록, 위치, 차례 = [], 0, 0
    while True:
        덩이길이, n = int(rng.integers(16, 1025)), int(rng.integers(16, 129))
        if 위치 + 덩이길이 + n > 최대:
            break
        새 = [int(x) for x in rng.integers(0, 50257, 덩이길이 - 1)]
        줄 = {"앞 문맥": 위치, "덩이": 덩이길이, "생성": n}
        for 이름, e in (("글", 글), ("라", 라)):
            r = e.대화([[끝[이름]] + 새], n, 처음=(차례 == 0))[0]
            끝[이름] = r["끝토큰"]
            줄[이름] = {"넣기 ms": round(r["넣기 ms"], 3), "토큰당 ms": round(r["생성 ms"] / (n - 1), 4)}
        기록.append(줄)
        위치 += 덩이길이 + n - 1
        차례 += 1
    라.닫기()
    글.닫기()
    구간 = {}
    for b in range(8):
        r = [x for x in 기록 if b * 12800 <= x["앞 문맥"] < (b + 1) * 12800]
        if r:
            구간[f"{b * 12800}~{(b + 1) * 12800}"] = {
                "넣기 ms 중앙값 (글 · llama.cpp)": [round(float(np.median([x[k]["넣기 ms"] for x in r])), 3) for k in ("글", "라")],
                "토큰당 ms 중앙값 (글 · llama.cpp)": [round(float(np.median([x[k]["토큰당 ms"] for x in r])), 4) for k in ("글", "라")]}
            print("대화", b, 구간[f"{b * 12800}~{(b + 1) * 12800}"], flush=True)
    return {"차례 수": len(기록), "마지막 문맥": 위치, "구간": 구간}


def 오래(일, 창초=10.0, 창수=6, 씨=13):
    path = T.경로("XL", "q8_0")
    글 = E.글엔진(GR.gpt2정수(path), KV형식="정수", 자리수=2, 최대문장=1)
    글.m.판미리고르기()
    라 = E.라마엔진(일, "llama.cpp q8_0", path)

    def 창(e):
        rng = np.random.default_rng(씨)
        위치, 처음, 끝, 토큰 = 0, True, int(rng.integers(0, 50257)), 0
        t0 = time.perf_counter()
        while time.perf_counter() - t0 < 창초:
            덩이길이, n = int(rng.integers(16, 257)), int(rng.integers(16, 129))
            if 위치 + 덩이길이 + n > 1024:
                위치, 처음 = 0, True
            새 = [int(x) for x in rng.integers(0, 50257, 덩이길이 - 1)]
            r = e.대화([[끝] + 새], n, 처음=처음)[0]
            끝, 처음 = r["끝토큰"], False
            위치 += 덩이길이 + n - 1
            토큰 += 덩이길이 + n - 1
        초 = time.perf_counter() - t0
        q = subprocess.run(["nvidia-smi", "--query-gpu=clocks.sm,temperature.gpu,power.draw", "--format=csv,noheader,nounits"],
                           capture_output=True, text=True).stdout.strip()
        return {"토큰/초": round(토큰 / 초, 1), "GPU (MHz, °C, W)": q}
    창들 = []
    for i in range(창수):
        창들.append({"창": i, "llama.cpp": 창(라), "글": 창(글)})
        print("오래", 창들[-1], flush=True)
    라.닫기()
    글.닫기()
    return {"창": 창들, "글의 마지막 창 / 첫 창": round(창들[-1]["글"]["토큰/초"] / 창들[0]["글"]["토큰/초"], 3)}


def main():
    인자 = set(sys.argv[1:])
    부분 = 인자 & {"프롬프트", "생성", "긴넣기", "긴생성", "대화", "오래"} or {"프롬프트", "생성", "긴넣기", "긴생성", "대화", "오래"}
    크기들 = tuple(k for k in ("small", "XL") if not (인자 & {"small", "XL"}) or k in 인자)
    res = {"프롬프트": {}, "생성": {}}
    일 = E.일꾼()
    try:
        if 부분 & {"프롬프트", "생성"}:
            프롬프트생성(일, 크기들, 부분, res)
        if T.있나(T.긴GGUF):
            if "긴넣기" in 부분:
                res["긴넣기"] = 긴넣기(일)
            if "긴생성" in 부분:
                res["긴생성"] = 긴생성(일)
            if "대화" in 부분:
                res["대화"] = 대화(일)
        if "오래" in 부분 and T.있나(T.경로("XL", "q8_0")):
            res["오래"] = 오래(일)
    finally:
        일.끝()
        os.makedirs(T.결과폴더, exist_ok=True)
        json.dump(res, open(os.path.join(T.결과폴더, "속도.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        print("빌드/결과/속도.json", flush=True)


if __name__ == "__main__":
    main()
