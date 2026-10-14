"""31i — 잰 것을 모아 칸마다 세 바퀴의 가운데 값 · 비 · 판정. python -I 모음31i.py <잼 폴더> <출력 json>"""
import json
import os
import re
import statistics
import sys

W, 출력 = sys.argv[1:3]      # 재기/모음31i.py <잼 폴더 — 문서/결과/31단계/31i> <출력 json>
바닥 = {"Q4_0": {"생성 0": 7.89, "생성 2048": 8.13, "생성 8192": 8.84, "프롬프트 2048": 168.0, "프롬프트 8192": 673.0},
       "Q8_0": {"생성 0": 14.91, "생성 2048": 15.15, "생성 8192": 15.86, "프롬프트 2048": 168.0, "프롬프트 8192": 673.0}}
칸들 = ["프롬프트 2048", "프롬프트 8192", "생성 0", "생성 2048", "생성 8192"]


def 글읽기(p):
    out = {}
    if not os.path.exists(p):
        return out
    for 줄 in open(p, encoding="utf-8"):
        m = re.match(r"생성 채팅 질문 ([\d.]+)", 줄)
        if m:
            out["생성 0"] = float(m[1])
        m = re.match(r"생성 문맥 (\d+) ([\d.]+)", 줄)
        if m:
            out[f"생성 {m[1]}"] = float(m[2])
        m = re.match(r"프롬프트 (\d+) ([\d.]+)", 줄)
        if m:
            out[f"프롬프트 {m[1]}"] = float(m[2])
    return out


def 라마읽기(p프, p생):
    out = {}
    for p in (p프, p생):
        if not os.path.exists(p):
            continue
        for 줄 in open(p, encoding="utf-8"):
            칸 = [x.strip() for x in 줄.split("|")]
            if len(칸) < 8 or not re.match(r"[\d.]+", 칸[-2] or "x"):
                continue
            test, tps = 칸[-3], float(칸[-2].split("±")[0])
            m = re.match(r"pp(\d+)$", test)
            if m:
                out[f"프롬프트 {m[1]}"] = int(m[1]) / tps * 1000.0
            m = re.match(r"tg128(?: @ d(\d+))?$", test)
            if m:
                out[f"생성 {m[1] or 0}"] = 1000.0 / tps
    return out


결과 = {"칸": {}, "판정": {}}
for f in ("Q4_0", "Q8_0"):
    모 = {"글V": [], "글C": [], "라마": []}
    for i in (1, 2, 3):
        모["글V"].append(글읽기(os.path.join(W, f"글V_{f}_{i}.txt")))
        모["글C"].append(글읽기(os.path.join(W, f"글C_{f}_{i}.txt")))
        모["라마"].append(라마읽기(os.path.join(W, f"라마_{f}_프롬프트_{i}.txt"), os.path.join(W, f"라마_{f}_생성_{i}.txt")))
    결과["칸"][f] = {}
    for 칸 in 칸들:
        v = {}
        for 쪽, 값들 in 모.items():
            xs = [d[칸] for d in 값들 if 칸 in d]
            v[쪽] = {"바퀴": [round(x, 3) for x in xs], "가운데": round(statistics.median(xs), 3) if xs else None}
        b = 바닥[f][칸]
        g = lambda 쪽: v[쪽]["가운데"]
        r = {"바닥": b}
        if g("글V") and g("라마"):
            r["V ÷ 라마"] = round(g("글V") / g("라마"), 3)
        if g("글V") and g("글C"):
            r["V ÷ CUDA"] = round(g("글V") / g("글C"), 3)
        if g("글C") and g("라마"):
            r["CUDA ÷ 라마"] = round(g("글C") / g("라마"), 3)
        for 쪽 in ("글V", "글C", "라마"):
            if g(쪽):
                r[f"{쪽} ÷ 바닥"] = round(g(쪽) / b, 3)
        결과["칸"][f][칸] = {**v, **r}

모든칸 = [c for f in 결과["칸"].values() for c in f.values()]
A = all(c.get("V ÷ 라마", 9e9) <= 1.01 for c in 모든칸)
B = all(c.get("V ÷ CUDA", 9e9) <= 1.01 for c in 모든칸)
A12 = all(c.get("V ÷ 라마", 9e9) <= 1.2 for c in 모든칸)
결과["판정"] = {"목표 A (≤ 라마 × 1.01) 모든 칸": A, "목표 B (≤ CUDA × 1.01) 모든 칸": B, "라마 × 1.2 안 모든 칸": A12,
             "판정": "통과" if A else ("부분" if (B or A12) else "못 미침")}
json.dump(결과, open(출력, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
for f, cs in 결과["칸"].items():
    print(f)
    for 칸, c in cs.items():
        print(f"  {칸:10} 바닥 {c['바닥']:8.2f} · 글V {c['글V']['가운데']} · 글C {c['글C']['가운데']} · 라마 {c['라마']['가운데']}"
              f" · V÷라마 {c.get('V ÷ 라마')} · V÷CUDA {c.get('V ÷ CUDA')} · V÷바닥 {c.get('글V ÷ 바닥')}")
print(결과["판정"])
