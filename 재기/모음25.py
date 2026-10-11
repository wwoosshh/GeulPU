#!/usr/bin/env python3
"""25c 의 모음 — 층 나누기의 넘김 값. 글(호스트/재기_7B.gl)의 출력: 모델(7B Q4_0 · 14B Q4_0)마다 한 조각 · 두 조각(조각마다 문맥) ·
두 조각(문맥 하나 — 기록)을 번갈아 세 번, 그리고 세 조각 · 네 조각을 한 번씩. 칸마다 세 번의 가운데 값, 비 = t(P 조각) / t(한 조각).
판정(문서/25단계.md): 14B Q4_0 · 7B Q4_0 의 두 조각(조각마다 문맥)이 생성 셋 모두 1.03 이하. 나머지(문맥 하나 · 셋 · 넷 · 프롬프트)는 기록.

  python -I 재기/모음25.py <결과 폴더(문서/결과/25단계)> <출력.json>
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from 모음23 import 가운데, 글읽기       # noqa: E402

생성칸 = ("생성 짧음", "생성 2048", "생성 8192")
프롬프트칸 = ("프롬프트 2048", "프롬프트 8192")
모델들 = {"7b-q4": ("p1", "p2", "p2하나", "p3", "p4"), "14b-q4": ("p1", "p2", "p2하나", "p3")}
이름 = {"p1": "한 조각", "p2": "두 조각(조각마다 문맥)", "p2하나": "두 조각(문맥 하나 — 기록)", "p3": "세 조각(기록)", "p4": "네 조각(기록)"}


def 읽기(폴더, m, c):
    """세 번(있는 만큼)의 출력 — 없거나 비면(들지 않음) 빈 목록."""
    out = []
    for i in (1, 2, 3):
        p = os.path.join(폴더, f"25c_글_{m}_{c}_{i}.txt")
        if os.path.exists(p):
            d = 글읽기(p)
            if d:
                out.append(d)
    return out


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    폴더, 출력 = sys.argv[1:3]
    결과 = {"판정": {}, "기록": {}, "값 (ms)": {}}
    통과 = True
    for m, 판들 in 모델들.items():
        값 = {c: 읽기(폴더, m, c) for c in 판들}
        결과["값 (ms)"][m] = 값
        if not 값["p1"]:
            print(f"{m}: 한 조각의 값이 없다", flush=True)
            통과 = False
            continue
        기준 = {k: 가운데([x[k] for x in 값["p1"] if k in x]) for k in 생성칸 + 프롬프트칸}
        for c in 판들[1:]:
            if not 값[c]:
                결과["기록"][f"{m} {이름[c]}"] = "들지 않음(재지 못함)"
                print(f"{m} {이름[c]}: 들지 않음", flush=True)
                if c == "p2":
                    통과 = False
                continue
            한 = {}
            for k in 생성칸 + 프롬프트칸:
                xs = [x[k] for x in 값[c] if k in x]
                if not xs:
                    continue
                t = 가운데(xs)
                한[k] = {"한 조각 ms": round(기준[k], 4), "P 조각 ms": round(t, 4), "비": round(t / 기준[k], 4), "번": len(xs)}
            if c == "p2":
                결과["판정"][f"{m} {이름[c]}"] = 한
                for k in 생성칸:
                    if k not in 한 or 한[k]["비"] > 1.03:
                        통과 = False
            else:
                결과["기록"][f"{m} {이름[c]}"] = 한
            print(f"{m} {이름[c]}: " + " · ".join(f"{k} {v['비']:.4f}" for k, v in 한.items()), flush=True)
    결과["25c 통과(14B Q4_0 · 7B Q4_0 의 두 조각, 생성 셋 모두 비 ≤ 1.03)"] = 통과
    print("25c 통과:", 통과, flush=True)
    json.dump(결과, open(출력, "w", encoding="utf-8"), ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
