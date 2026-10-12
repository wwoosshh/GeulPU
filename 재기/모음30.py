#!/usr/bin/env python3
"""30c · 30d · 30e 의 모음 — 29단계 빌드와 30단계 빌드(같은 실행에서 세 번 번갈아)를 모아 미리 적은 기준(문서/30단계.md)의 통과를 낸다.

  30c 프롬프트: 호스트/재기_프롬프트30.gl 의 출력(프롬프트 32 · 128 · 512 · 1024 · 2048 · 4096 · 8192 — 칸마다 일곱 번 × 세 묶음의 중앙값)
  30d 생성:     호스트/재기_7B.gl 의 출력(생성 짧을 때 · 문맥 2048 · 8192)
  30e 첫 토큰:  재기/서버재기28.py --첫토큰 --막기 의 JSON(캐시 끔 · 같은 프롬프트 · 다음 차례 — 되풀이 다섯)
판정의 비는 번갈아 잰 세 번마다의 비 t₃₀ / t₂₉ 의 가운데 값이다(문서 그대로 — "시간 비의 세 번 중 가운데 값"). 세 번의 가운데 값끼리의
비도 함께 적는다. 판정이 아닌 기록: llama.cpp(같은 실행의 llama-bench — 최신 공식 릴리스) 대비 r, llama-server 의 첫 토큰.

  python -I 재기/모음30.py <결과 폴더(문서/결과/30단계)> <출력.json>
"""
import json
import os
import statistics
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from 모음23 import 가운데, 글읽기, 라마읽기       # noqa: E402

형식들 = ("q8_0", "q4_0", "q4_k_m", "q5_k_m", "q6_k")
길이들 = (32, 128, 512, 1024, 2048, 4096, 8192)
판정길이 = (32, 128, 512, 2048, 8192)
생성칸 = ("생성 짧음", "생성 2048", "생성 8192")
생성기준 = 1.02
첫칸 = {"같은프롬프트": 0.70, "다음차례": 0.90, "캐시끔": 1.00}


def 프롬프트기준(f, n):
    if f == "q4_0":
        return 0.85 if n == 32 else (0.99 if n == 8192 else 0.98)
    if f == "q8_0":
        return 0.90 if n == 32 else 0.99
    return 0.92 if n == 32 else 1.03


def 판정칸(결과, 이름, 셋29, 셋30, 기준):
    비들 = [b / a for a, b in zip(셋29, 셋30)]
    비 = 가운데(비들)
    된 = 비 <= 기준
    결과["판정"][이름] = {"29 (ms)": [round(x, 4) for x in 셋29], "30 (ms)": [round(x, 4) for x in 셋30],
                       "세 번의 비": [round(x, 4) for x in 비들], "t30/t29 (세 비의 가운데)": round(비, 4),
                       "가운데끼리의 비": round(가운데(셋30) / 가운데(셋29), 4), "기준": 기준, "통과": 된}
    print(f"{이름}: 29 {가운데(셋29):.3f} · 30 {가운데(셋30):.3f} ms · 비 {비:.4f} (기준 ≤ {기준}) {'통과' if 된 else '못 미침'}", flush=True)
    return 된


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    폴더, 출력 = sys.argv[1:3]
    결과 = {"판정": {}, "기록": {}}
    통과 = {"30c": True, "30d": True, "30e": True}
    가운데30 = {}
    for f in 형식들:
        c = {b: [글읽기(os.path.join(폴더, f"30c_{b}_{f}_{i}.txt")) for i in (1, 2, 3)] for b in ("29", "30")}
        d = {b: [글읽기(os.path.join(폴더, f"30d_{b}_{f}_{i}.txt")) for i in (1, 2, 3)] for b in ("29", "30")}
        for n in 길이들:
            칸 = f"프롬프트 {n}"
            셋29 = [x[칸] for x in c["29"]]
            셋30 = [x[칸] for x in c["30"]]
            가운데30[(f, 칸)] = 가운데(셋30)
            if n in 판정길이:
                통과["30c"] &= 판정칸(결과, f"30c {f} {칸}", 셋29, 셋30, 프롬프트기준(f, n))
            else:
                결과["기록"][f"프롬프트 {f} {n} (판정 밖)"] = {"29 (ms)": 셋29, "30 (ms)": 셋30, "가운데끼리의 비": round(가운데(셋30) / 가운데(셋29), 4)}
        for 칸 in 생성칸:
            통과["30d"] &= 판정칸(결과, f"30d {f} {칸}", [x[칸] for x in d["29"]], [x[칸] for x in d["30"]], 생성기준)
    e = {b: [json.load(open(os.path.join(폴더, f"30e_{b}_{i}.json"), encoding="utf-8")) for i in (1, 2, 3)] for b in ("29", "30")}
    for 칸, 기준 in 첫칸.items():
        셋29 = [statistics.median(x[칸]) for x in e["29"]]
        셋30 = [statistics.median(x[칸]) for x in e["30"]]
        통과["30e"] &= 판정칸(결과, f"30e {칸}", 셋29, 셋30, 기준)
    # 기록 — llama.cpp
    for f in 형식들:
        p = os.path.join(폴더, f"30기록_라마_{f}_프롬프트.txt")
        if not os.path.exists(p):
            continue
        라마 = 라마읽기(p)
        r = {}
        for n in 길이들:
            칸 = f"프롬프트 {n}"
            if 칸 in 라마:
                r[str(n)] = {"글 30 (ms)": round(가운데30[(f, 칸)], 4), "llama.cpp (ms)": round(라마[칸], 4), "r": round(가운데30[(f, 칸)] / 라마[칸], 4)}
        결과["기록"][f"llama.cpp 대비 프롬프트 {f}"] = r
        print(f"기록 {f} — llama.cpp 대비 r: " + " · ".join(f"{n} {v['r']:.3f}" for n, v in r.items()), flush=True)
    p = os.path.join(폴더, "30기록_첫토큰_라마.json")
    if os.path.exists(p):
        라마 = json.load(open(p, encoding="utf-8"))
        결과["기록"]["llama-server 첫 토큰 (ms, 가운데)"] = {k: round(statistics.median(v), 2) for k, v in 라마.items()}
        print("기록 llama-server 첫 토큰: " + " · ".join(f"{k} {statistics.median(v):.1f}" for k, v in 라마.items()), flush=True)
    결과["통과"] = 통과
    json.dump(결과, open(출력, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("30c " + ("통과" if 통과["30c"] else "못 미침") + " · 30d " + ("통과" if 통과["30d"] else "못 미침") + " · 30e " + ("통과" if 통과["30e"] else "못 미침"))


if __name__ == "__main__":
    main()
