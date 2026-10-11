#!/usr/bin/env python3
"""24d 의 모음 — 14B Q4_0 의 글(호스트/재기_7B.gl 의 출력 셋)과 llama-bench(프롬프트 · 생성 표 셋)에서 셋의 가운데 값, r = 글 / llama.cpp,
미리 적은 칸(문서/24단계.md). 기록: 합성 모델(층 넷)마다 한 번씩의 r, 14B 의 바닥(토큰당 읽는 바이트 / 504 GB/s) 대비 배수.

  python -I 재기/모음24.py <결과 폴더(문서/결과/24단계)> <출력.json>
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from 모음23 import 가운데, 글읽기, 라마읽기       # noqa: E402

생성칸 = ("생성 짧음", "생성 2048", "생성 8192")
프롬프트칸 = ("프롬프트 2048", "프롬프트 8192")
# 14B (Qwen2.5-14B-Instruct): 층 48 · 너비 5120 · 머리 40 · KV 8 · 확장폭 13824 · 낱말 152064
층가중14 = 5120 * (5120 + 2 * 1024) + 5120 * 5120 + 5120 * 2 * 13824 + 13824 * 5120
가중수14 = 48 * 층가중14 + 5120 * 152064
KV위치바이트14 = 48 * 2 * (8 * 128 * 2 + 8 * 4)
문맥 = {"생성 짧음": 0, "생성 2048": 2048, "생성 8192": 8192}
합성들 = ("32b-l4-q4_0", "32b-l4-q8_0", "72b-l4-q4_0", "72b-l4-q8_0")


def 칸(이름, r):
    if 이름.startswith("프롬프트"):
        return "글이 빠르다" if r <= 1 else ("느리지만 두 배 안" if r < 2 else "두 배 넘게 느리다")
    return "글이 빠르다" if r < 0.95 else ("같다" if r <= 1.05 else "느리다")


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    폴더, 출력 = sys.argv[1:3]
    결과 = {"판정": {}, "기록": {}}
    글 = [글읽기(os.path.join(폴더, f"24d_글_14b_{i}.txt")) for i in (1, 2, 3)]
    라마 = []
    for i in (1, 2, 3):
        d = 라마읽기(os.path.join(폴더, f"24d_라마_14b_프롬프트_{i}.txt"))
        d.update(라마읽기(os.path.join(폴더, f"24d_라마_14b_생성_{i}.txt")))
        라마.append(d)
    결과["14B"] = {"글 (ms)": 글, "llama.cpp (ms)": 라마}
    for 이름 in 생성칸 + 프롬프트칸:
        gs = [x[이름] for x in 글 if 이름 in x]
        ls = [x[이름] for x in 라마 if 이름 in x]
        if len(gs) < 3 or len(ls) < 3:
            결과["판정"][f"14B {이름}"] = {"칸": "들지 않음(재지 못함)", "글 ms": gs, "llama.cpp ms": ls}
            print(f"14B {이름}: 들지 않음", flush=True)
            continue
        g, l = 가운데(gs), 가운데(ls)
        r = g / l
        한 = {"글 ms": round(g, 4), "llama.cpp ms": round(l, 4), "r": round(r, 4), "칸": 칸(이름, r)}
        if 이름 in 생성칸:
            바닥 = (가중수14 * 18 / 32 + 문맥[이름] * KV위치바이트14) / 504e9 * 1000.0
            한["바닥 ms (기록)"] = round(바닥, 4)
            한["글 / 바닥 (기록)"] = round(g / 바닥, 4)
            한["llama.cpp / 바닥 (기록)"] = round(l / 바닥, 4)
        결과["판정"][f"14B {이름}"] = 한
        print(f"14B {이름}: 글 {g:.3f} ms · llama.cpp {l:.3f} ms · r {r:.4f} — {칸(이름, r)}", flush=True)
    결과["24d 통과(생성 셋 모두 r ≤ 1.05)"] = all(
        "r" in 결과["판정"][f"14B {이름}"] and 결과["판정"][f"14B {이름}"]["r"] <= 1.05 for 이름 in 생성칸)
    print("24d 통과:", 결과["24d 통과(생성 셋 모두 r ≤ 1.05)"], flush=True)
    for m in 합성들:
        g = 글읽기(os.path.join(폴더, f"24기록_글_{m}.txt"))
        l = 라마읽기(os.path.join(폴더, f"24기록_라마_{m}_프롬프트.txt"))
        l.update(라마읽기(os.path.join(폴더, f"24기록_라마_{m}_생성.txt")))
        한 = {}
        for 이름 in 생성칸 + 프롬프트칸:
            if 이름 in g and 이름 in l:
                한[이름] = {"글 ms": round(g[이름], 4), "llama.cpp ms": round(l[이름], 4), "r": round(g[이름] / l[이름], 4)}
        결과["기록"][f"합성 {m}"] = 한
        print(f"합성 {m}:", {k: v["r"] for k, v in 한.items()}, flush=True)
    json.dump(결과, open(출력, "w", encoding="utf-8"), ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
