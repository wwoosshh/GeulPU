#!/usr/bin/env python3
"""22d 의 모음 — 글(호스트/재기_7B.gl 의 출력 셋)과 llama-bench(프롬프트 · 생성 표 셋)에서 프로세스마다의 값, 셋의 가운데 값, 비 r = 글 / llama.cpp,
미리 적은 칸(문서/22단계.md)을 낸다.

  python -I 재기/모음22d.py <결과 폴더(문서/결과/22단계)> <출력.json>
"""
import json
import os
import re
import sys


def 가운데(xs):
    s = sorted(xs)
    return s[len(s) // 2]


def 글읽기(경로):
    out = {}
    for 줄 in open(경로, encoding="utf-8"):
        m = re.match(r"생성 (채팅 질문|문맥 2048|문맥 8192) ([\d.]+)", 줄)
        if m:
            out[{"채팅 질문": "생성 짧음", "문맥 2048": "생성 2048", "문맥 8192": "생성 8192"}[m.group(1)]] = float(m.group(2))
        m = re.match(r"프롬프트 (\d+) ([\d.]+)", 줄)
        if m:
            out[f"프롬프트 {m.group(1)}"] = float(m.group(2))
    return out


def 라마읽기(경로):
    """llama-bench 의 md 표 — test 칸과 t/s(± 앞의 수) → ms (프롬프트: n / (t/s), 생성: 1 / (t/s))."""
    out = {}
    for 줄 in open(경로, encoding="utf-8", errors="replace"):
        칸 = [c.strip() for c in 줄.split("|")]
        if len(칸) < 3 or not 칸[-2] or "t/s" in 칸[-2] or 칸[-2].startswith("-"):
            continue
        test, ts = 칸[-3], 칸[-2]
        v = float(ts.split("±")[0])
        m = re.match(r"pp(\d+)$", test)
        if m:
            out[f"프롬프트 {m.group(1)}"] = int(m.group(1)) / v * 1000.0
        m = re.match(r"tg(\d+)(?: @ d(\d+))?$", test)
        if m:
            d = m.group(2)
            out["생성 짧음" if d in (None, "0") else f"생성 {d}"] = 1000.0 / v
    return out


def 칸(이름, r):
    if 이름.startswith("프롬프트"):
        return "글이 빠르다" if r <= 1 else ("느리지만 두 배 안" if r < 2 else "두 배 넘게 느리다")
    return "같다(바닥 쪽)" if r <= 1.05 else ("느리다" if r <= 1.5 else "많이 느리다")


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    폴더, 출력 = sys.argv[1:3]
    글 = [글읽기(os.path.join(폴더, f"22d_글_{i}.txt")) for i in (1, 2, 3)]
    라마 = []
    for i in (1, 2, 3):
        d = 라마읽기(os.path.join(폴더, f"22d_라마_프롬프트_{i}.txt"))
        d.update(라마읽기(os.path.join(폴더, f"22d_라마_생성_{i}.txt")))
        라마.append(d)
    결과 = {"글 (ms)": 글, "llama.cpp (ms)": 라마, "판정": {}}
    for 이름 in ("프롬프트 2048", "프롬프트 8192", "생성 짧음", "생성 2048", "생성 8192"):
        g = 가운데([x[이름] for x in 글])
        l = 가운데([x[이름] for x in 라마])
        r = g / l
        결과["판정"][이름] = {"글 ms": round(g, 4), "llama.cpp ms": round(l, 4), "r": round(r, 4), "칸": 칸(이름, r)}
        print(f"{이름}: 글 {g:.3f} ms · llama.cpp {l:.3f} ms · r {r:.3f} — {칸(이름, r)}", flush=True)
    결과["기록 — 프롬프트 128 (글 ms)"] = 가운데([x["프롬프트 128"] for x in 글])
    json.dump(결과, open(출력, "w", encoding="utf-8"), ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
