#!/usr/bin/env python3
"""27c · 27d 의 모음 — 26단계 빌드와 27단계 빌드(같은 실행에서 세 번 번갈아 — 호스트/재기_7B.gl 의 출력)를 형식마다 모아, 칸마다 세 번의
가운데 값과 비 t₂₇ / t₂₆, 미리 적은 기준(문서/27단계.md)의 통과. 판정이 아닌 기록: llama.cpp(같은 실행의 llama-bench) 대비 프롬프트 r.

  python -I 재기/모음27.py <결과 폴더(문서/결과/27단계)> <출력.json>
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from 모음23 import 가운데, 글읽기, 라마읽기       # noqa: E402

형식들 = ("q8_0", "q4_0", "q4_k_m", "q5_k_m", "q6_k")
생성칸 = ("생성 짧음", "생성 2048", "생성 8192")
프롬프트칸 = ("프롬프트 2048", "프롬프트 8192")
프롬프트기준 = {"q6_k": 0.80, "q4_k_m": 0.90, "q5_k_m": 0.95, "q4_0": 0.95, "q8_0": 1.02}
생성기준 = 1.02


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    폴더, 출력 = sys.argv[1:3]
    결과 = {"판정": {}, "기록": {}}
    통과c, 통과d = True, True
    for f in 형식들:
        값 = {b: [글읽기(os.path.join(폴더, f"27c_{b}_{f}_{i}.txt")) for i in (1, 2, 3)] for b in ("26", "27")}
        결과[f] = {"26 (ms)": 값["26"], "27 (ms)": 값["27"]}
        for 이름 in 프롬프트칸 + 생성칸:
            a = 가운데([x[이름] for x in 값["26"]])
            b = 가운데([x[이름] for x in 값["27"]])
            비 = b / a
            기준 = 프롬프트기준[f] if 이름 in 프롬프트칸 else 생성기준
            된 = 비 <= 기준
            if 이름 in 프롬프트칸:
                통과c = 통과c and 된
            else:
                통과d = 통과d and 된
            결과["판정"][f"{f} {이름}"] = {"26 ms": round(a, 4), "27 ms": round(b, 4), "t27/t26": round(비, 4), "기준": 기준, "통과": 된}
            print(f"{f} {이름}: 26 {a:.3f} ms · 27 {b:.3f} ms · 비 {비:.4f} (기준 ≤ {기준}) {'통과' if 된 else '못 미침'}", flush=True)
        라마 = os.path.join(폴더, f"27기록_라마_{f}_프롬프트.txt")
        if os.path.exists(라마):
            l = 라마읽기(라마)
            for 이름 in 프롬프트칸:
                if 이름 in l:
                    g = 결과["판정"][f"{f} {이름}"]["27 ms"]
                    결과["기록"][f"{f} {이름} r (27 / llama.cpp)"] = {"llama.cpp ms": round(l[이름], 4), "r": round(g / l[이름], 4)}
                    print(f"  기록 {f} {이름}: llama.cpp {l[이름]:.3f} ms · r {g / l[이름]:.4f}", flush=True)
    결과["27c 통과"] = 통과c
    결과["27d 통과"] = 통과d
    print("27c 통과:", 통과c, "· 27d 통과:", 통과d, flush=True)
    json.dump(결과, open(출력, "w", encoding="utf-8"), ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
