#!/usr/bin/env python3
"""23c · 23d 의 모음 — 글(호스트/재기_7B.gl 의 출력 셋)과 llama-bench(프롬프트 · 생성 표 셋)를 형식(Q8_0 · Q4_0)마다 모아 프로세스마다의 값,
셋의 가운데 값, 비 r = 글 / llama.cpp, 미리 적은 칸(문서/23단계.md)을 낸다. 판정이 아닌 기록: 바닥(토큰당 읽는 바이트 / 504 GB/s) 대비 배수,
Q4_0 과 Q8_0 의 생성 시간 비.

  python -I 재기/모음23.py <결과 폴더(문서/결과/23단계)> <출력.json>
"""
import json
import os
import re
import sys

형식들 = ("Q8_0", "Q4_0")
생성칸 = ("생성 짧음", "생성 2048", "생성 8192")
프롬프트칸 = ("프롬프트 2048", "프롬프트 8192")

# 7B(Qwen2.5-7B-Instruct)의 토큰당 가중치 수 — 층마다 qkv (3584 × 4608) · o (3584²) · gate·up (3584 × 37888) · down (18944 × 3584), 28 층,
# 그리고 출력(3584 × 152064). 낱말표는 행 하나만 읽는다(무시). KV 는 위치마다 · 층마다 (머리 4 × 128 × 자리 2 + 지수 4) × 2 (키 · 값)
층가중 = 3584 * 4608 + 3584 * 3584 + 3584 * 37888 + 18944 * 3584
가중수 = 28 * 층가중 + 3584 * 152064
블록바이트 = {"Q8_0": 34, "Q4_0": 18}
KV위치바이트 = 28 * 2 * (4 * 128 * 2 + 4 * 4)
문맥 = {"생성 짧음": 0, "생성 2048": 2048, "생성 8192": 8192}


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
    return "글이 빠르다" if r < 0.95 else ("같다" if r <= 1.05 else "느리다")


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    폴더, 출력 = sys.argv[1:3]
    결과 = {"판정": {}, "기록": {}}
    가운데글 = {}
    for f in 형식들:
        글 = [글읽기(os.path.join(폴더, f"23c_글_{f}_{i}.txt")) for i in (1, 2, 3)]
        라마 = []
        for i in (1, 2, 3):
            d = 라마읽기(os.path.join(폴더, f"23c_라마_{f}_프롬프트_{i}.txt"))
            d.update(라마읽기(os.path.join(폴더, f"23c_라마_{f}_생성_{i}.txt")))
            라마.append(d)
        결과[f] = {"글 (ms)": 글, "llama.cpp (ms)": 라마}
        가운데글[f] = {}
        for 이름 in 생성칸 + 프롬프트칸:
            g = 가운데([x[이름] for x in 글])
            l = 가운데([x[이름] for x in 라마])
            r = g / l
            가운데글[f][이름] = g
            한 = {"글 ms": round(g, 4), "llama.cpp ms": round(l, 4), "r": round(r, 4), "칸": 칸(이름, r)}
            if 이름 in 생성칸:
                바닥 = (가중수 * 블록바이트[f] / 32 + 문맥[이름] * KV위치바이트) / 504e9 * 1000.0
                한["바닥 ms (기록)"] = round(바닥, 4)
                한["글 / 바닥 (기록)"] = round(g / 바닥, 4)
                한["llama.cpp / 바닥 (기록)"] = round(l / 바닥, 4)
            (결과["판정"] if (이름 in 생성칸 or f == "Q4_0") else 결과["기록"])[f"{f} {이름}"] = 한
            print(f"{f} {이름}: 글 {g:.3f} ms · llama.cpp {l:.3f} ms · r {r:.4f} — {칸(이름, r)}", flush=True)
        결과["기록"][f"{f} 프롬프트 128 (글 ms)"] = 가운데([x["프롬프트 128"] for x in 글])
    for 이름 in 생성칸:
        결과["기록"][f"Q4_0 / Q8_0 {이름} (글)"] = round(가운데글["Q4_0"][이름] / 가운데글["Q8_0"][이름], 4)
    결과["23c 통과(여섯 칸 모두 r ≤ 1.05)"] = all(결과["판정"][f"{f} {이름}"]["r"] <= 1.05 for f in 형식들 for 이름 in 생성칸)
    print("23c 통과:", 결과["23c 통과(여섯 칸 모두 r ≤ 1.05)"], flush=True)
    json.dump(결과, open(출력, "w", encoding="utf-8"), ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
