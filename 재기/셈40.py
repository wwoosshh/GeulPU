#!/usr/bin/env python3
"""40단계 셈(문서/40단계.md '판정') — 위험한 걸음 · 기울기 · 궤적 · 번짐 · 오염 · 흔들림.

  python -I -X utf8 재기/셈40.py 위험 --작업 W --모델폴더 M          (위험한 걸음 목록 · 40e 의 갈래 목록)
  python -I -X utf8 재기/셈40.py 모두 --작업 W --모델폴더 M --결과 문서/결과/40단계
"""
import argparse
import json
import os
import random
import sys
import time
from difflib import SequenceMatcher

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, ".."))
sys.path.insert(0, HERE)
import 증상40 as Z      # noqa: E402
import 모음40 as MO      # noqa: E402

씨앗 = 40
한국어묶음 = ("자연_LCB", "자연_긴글", "방아쇠_글자", "방아쇠_언어", "방아쇠_되풀이")
자연한국어 = ("자연_LCB", "자연_긴글")


def 기록(*a):
    print(time.strftime("%H:%M:%S"), *a, flush=True)


class 색인:
    """JSONL 의 줄을 id 로 찾아 읽는다(모두 메모리에 올리지 않는다)."""
    def __init__(self, p):
        self.p, self.off = p, {}
        if os.path.exists(p):
            with open(p, "rb") as f:
                pos = 0
                for line in f:
                    if line.strip():
                        self.off[json.loads(line)["id"]] = pos
                    pos += len(line)

    def __contains__(self, k):
        return k in self.off

    def keys(self):
        return list(self.off.keys())

    def __getitem__(self, k):
        with open(self.p, "rb") as f:
            f.seek(self.off[k])
            return json.loads(f.readline())

    def __len__(self):
        return len(self.off)


def 질문표():
    out = {}
    폴더 = os.path.join(ROOT, "시험", "질문40")
    for f in os.listdir(폴더):
        if f.endswith(".jsonl"):
            for l in open(os.path.join(폴더, f), encoding="utf-8"):
                r = json.loads(l)
                out[r["id"]] = r
    return out


def 글로(토큰들, 표):
    return b"".join(표[t] for t in 토큰들).decode("utf-8", errors="replace")


# ---------------------------------------------------------------- 증상
def 증상들(r, q, 묶음):
    tok, text, fin = r["tokens"], r["text"], r["finish"]
    길이 = fin == "length"
    out = {"S1": Z.S1_끝없는반복(tok, 길이) is not None, "S5": Z.S5_깨짐(tok, text, not 길이), "길이": 길이}
    if 묶음 == "자연_수학":
        s3, s4, x = Z.S3_S4(text, 길이, q["정답"])
        out.update(S3=s3, S4=s4)
    else:
        a, b, _ = Z.S2_다른문자(text, q["질문"])
        out.update(S2a=a, S2b=b, S2=a or b)
        if 묶음 == "방아쇠_글자":
            s6, 옮김, _ = Z.S6_맞춤법(text, q["원문"])
            out.update(S6=s6, 옮김=옮김)
    return out


def 증상표(색, Q):
    return {k: 증상들(r, Q[k], r["묶음"]) for k in 색.keys() for r in [색[k]]}


def 짝셈(A, B, ids, 키):
    """A 에만 있으면 생김(b), B 에만 있으면 사라짐(c)."""
    b = sum(1 for i in ids if A[i].get(키) and not B[i].get(키))
    c = sum(1 for i in ids if B[i].get(키) and not A[i].get(키))
    nA = sum(1 for i in ids if A[i].get(키))
    nB = sum(1 for i in ids if B[i].get(키))
    return {"문항": len(ids), "생김b": b, "사라짐c": c, "A증상": nA, "B증상": nB, "p": Z.McNemar(b, c)}


# ---------------------------------------------------------------- 위험한 걸음 · 기울기
def 모델표(작업, 모델폴더, 모델):
    표, 특수 = Z.바이트표(os.path.join(모델폴더, MO.GGUF[모델]))
    return 표, 특수, Z.계통표(표)


def 명령_위험(a):
    """G 의 답마다 위험한 걸음을 W/위험/<모델>.jsonl 에, 40e 의 갈래 목록(유형마다 최대 100 — 씨앗 40)을 W/위험/갈래목록_7b.jsonl 에."""
    Q = 질문표()
    os.makedirs(os.path.join(a.작업, "위험"), exist_ok=True)
    for 모델 in ("7b", "r1"):
        G = 색인(os.path.join(a.작업, "생성", f"G_{모델}.jsonl"))
        if not len(G):
            continue
        표, 특수, 계통 = 모델표(a.작업, a.모델폴더, 모델)
        p = os.path.join(a.작업, "위험", f"{모델}.jsonl")
        n걸음 = 0
        수 = {"O": 0, "R": 0, "C": 0}
        with open(p, "w", encoding="utf-8", newline="\n") as f:
            for k in sorted(G.keys()):
                g = G[k]
                st = Z.위험한걸음들_빠르게(g["tokens"], g["top_ids"], g["top_lp"], 표, 계통, 특수)
                n걸음 += len(g["tokens"])
                for s in st:
                    수[s[1]] += 1
                f.write(json.dumps({"id": k, "묶음": g["묶음"], "n": len(g["tokens"]), "걸음": st}, ensure_ascii=False) + "\n")
        기록(f"위험 {모델}: 답 {len(G)} · 걸음 {n걸음} · O {수['O']} · R {수['R']} · C {수['C']}")
    # 40e 갈래 목록 — 7b: O · R 은 한국어 묶음 모두에서, C 는 방아쇠 · 글자(원문이 있어 번짐을 셀 수 있다)에서
    후보 = {"O": [], "R": [], "C": []}
    for l in open(os.path.join(a.작업, "위험", "7b.jsonl"), encoding="utf-8"):
        r = json.loads(l)
        for s in r["걸음"]:
            t, 유형, aa, b = s[0], s[1], s[2], s[3]
            if 유형 == "C" and r["묶음"] != "방아쇠_글자":
                continue
            후보[유형].append({"id": r["id"], "t": t, "유형": 유형, "a": aa, "b": b, "여유": s[4]})
    rng = random.Random(씨앗)
    목록 = []
    for 유형 in ("O", "R", "C"):
        c = sorted(후보[유형], key=lambda x: (x["id"], x["t"]))
        rng.shuffle(c)
        for x in c[:100]:
            x["key"] = f"{x['id']}@{x['t']}{유형}"
            x["창"] = 256
            목록.append(x)
    with open(os.path.join(a.작업, "위험", "갈래목록_7b.jsonl"), "w", encoding="utf-8", newline="\n") as f:
        for x in 목록:
            f.write(json.dumps(x, ensure_ascii=False) + "\n")
    기록(f"갈래 목록 7b: {len(목록)} (O {sum(1 for x in 목록 if x['유형'] == 'O')} · R {sum(1 for x in 목록 if x['유형'] == 'R')} · "
       f"C {sum(1 for x in 목록 if x['유형'] == 'C')})")


def 기울기셈(a, 모델, 묶음들):
    """위험한 걸음마다 Δ_L · Δ_V · 대조 Δ_L. 문항마다 (합, 수)."""
    G = 색인(os.path.join(a.작업, "생성", f"G_{모델}.jsonl"))
    V = 색인(os.path.join(a.작업, "생성", f"V점수_{모델}.jsonl"))
    따라 = os.path.join(a.작업, "따라", 모델)
    위험 = {}
    for l in open(os.path.join(a.작업, "위험", f"{모델}.jsonl"), encoding="utf-8"):
        r = json.loads(l)
        if r["묶음"] in 묶음들:
            위험[r["id"]] = r
    문항 = {(갈, 유형): {} for 갈 in ("L", "V", "L대조") for 유형 in "ORC"}
    뒤집힘 = {유형: [0, 0] for 유형 in "ORC"}
    여유칸 = {유형: {} for 유형 in "ORC"}
    빠짐V = {유형: 0 for 유형 in "ORC"}
    n토큰 = 0
    없음 = 0
    for k, r in 위험.items():
        n토큰 += r["n"]
        g = G[k]
        f = os.path.join(따라, k + ".npz")
        if not os.path.exists(f):
            없음 += 1
            continue
        z = np.load(f)
        lpL, a1 = z["lp"], z["a1"]
        v = V[k] if k in V else None
        for s in r["걸음"]:
            t, 유형, aa, b, m, bc, lpGb, lpGbc = s
            ids = g["top_ids"][t]
            lpGa = g["top_lp"][t][0]
            jb = ids.index(b)
            dL = (float(lpL[t][jb]) - float(lpL[t][0])) - (lpGb - lpGa)
            문항[("L", 유형)].setdefault(k, [0.0, 0])
            문항[("L", 유형)][k][0] += dL
            문항[("L", 유형)][k][1] += 1
            뒤집힘[유형][0] += 1
            뒤집힘[유형][1] += int(a1[t]) == b
            칸 = min(int(m / 0.25), 9)
            e = 여유칸[유형].setdefault(칸, [0, 0])
            e[0] += 1
            e[1] += int(a1[t]) == b
            if bc is not None:
                jc = ids.index(bc)
                dc = (float(lpL[t][jc]) - float(lpL[t][0])) - (lpGbc - lpGa)
                문항[("L대조", 유형)].setdefault(k, [0.0, 0])
                문항[("L대조", 유형)][k][0] += dc
                문항[("L대조", 유형)][k][1] += 1
            if v is not None and t < len(v["top_ids"]) and v["top_ids"][t]:
                vi, vl = v["top_ids"][t], v["top_lp"][t]
                if aa in vi and b in vi:
                    dV = (vl[vi.index(b)] - vl[vi.index(aa)]) - (lpGb - lpGa)
                    문항[("V", 유형)].setdefault(k, [0.0, 0])
                    문항[("V", 유형)][k][0] += dV
                    문항[("V", 유형)][k][1] += 1
                else:
                    빠짐V[유형] += 1
    out = {"답": len(위험), "따라가기없음": 없음, "토큰": n토큰}
    for (갈, 유형), d in 문항.items():
        합 = [x[0] for x in d.values()]
        수 = [x[1] for x in d.values()]
        평균, 구간, p = Z.묶음붓스트랩(합, 수)
        out[f"{갈}_{유형}"] = {"평균": 평균, "구간": 구간, "p": p, "걸음": int(sum(수)), "문항": len(수)}
    for 유형 in "ORC":
        out[f"뒤집힘_{유형}"] = {"걸음": 뒤집힘[유형][0], "L이b": 뒤집힘[유형][1],
                              "여유칸(0.25 nat)": {str(k): v for k, v in sorted(여유칸[유형].items())}}
        out[f"V빠짐_{유형}"] = 빠짐V[유형]
        out[f"밀도_{유형}(천 토큰마다)"] = (out[f"L_{유형}"]["걸음"] / n토큰 * 1000) if n토큰 else None
    return out


# ---------------------------------------------------------------- 번짐 · 오염
def 베낌수(토큰들, 시작):
    """토큰들[시작:] 의 각 자리에서 끝나는 8-묶음이 그 앞에 있었던 횟수(앞선 8-토큰 묶음을 베낌)."""
    본 = set()
    n = 0
    for i in range(len(토큰들)):
        if i >= 7:
            g = tuple(토큰들[i - 7:i + 1])
            if i >= 시작 and g in 본:
                n += 1
            본.add(g)
    return n


def 번짐셈(a, Q):
    G = 색인(os.path.join(a.작업, "생성", "G_7b.jsonl"))
    B = 색인(os.path.join(a.작업, "생성", "갈래_7b.jsonl"))
    표, 특수, 계통 = 모델표(a.작업, a.모델폴더, "7b")
    목록 = [json.loads(l) for l in open(os.path.join(a.작업, "위험", "갈래목록_7b.jsonl"), encoding="utf-8")]
    셈 = {유형: {"수": 0, "b번짐": 0, "a번짐": 0, "둘다": 0, "b만": 0, "a만": 0} for 유형 in "ORC"}
    for x in 목록:
        if x["key"] not in B:
            continue
        g = G[x["id"]]
        br = B[x["key"]]
        t, 유형 = x["t"], x["유형"]
        창 = len(br["tokens"])
        a이음 = g["tokens"][t + 1:t + 1 + 창]
        b이음 = br["tokens"]
        q = Q[x["id"]]
        if 유형 == "O":
            fb = Z.S2_다른문자(글로(b이음, 표), q["질문"])[0]
            fa = Z.S2_다른문자(글로(a이음, 표), q["질문"])[0]
        elif 유형 == "R":
            앞 = g["tokens"][:t]
            fb = (Z.S1_끝없는반복(b이음, br["finish"] == "length") is not None) or 베낌수(앞 + [x["b"]] + b이음, t + 1) >= 3
            fa = (Z.S1_끝없는반복(a이음, len(a이음) >= 창) is not None) or 베낌수(앞 + [x["a"]] + a이음, t + 1) >= 3
        else:
            src = q["원문"]
            앞 = g["tokens"][:t]

            def 틀린글자(답):
                sm = SequenceMatcher(None, src, 답, autojunk=False)
                return len(src) - sum(bl.size for bl in sm.get_matching_blocks())
            fb = 틀린글자(글로(앞 + [x["b"]] + b이음, 표)) >= 2
            fa = 틀린글자(글로(앞 + [x["a"]] + a이음, 표)) >= 2
        e = 셈[유형]
        e["수"] += 1
        e["b번짐"] += fb
        e["a번짐"] += fa
        e["둘다"] += fb and fa
        e["b만"] += fb and not fa
        e["a만"] += fa and not fb
    for 유형, e in 셈.items():
        e["p"] = Z.McNemar(e["b만"], e["a만"])
    return 셈


def 오염셈(a, Q):
    둘 = 색인(os.path.join(a.작업, "생성", "오염둘_7b.jsonl"))
    rows = {json.loads(l)["id"]: json.loads(l) for l in open(os.path.join(ROOT, "시험", "질문40", "오염.jsonl"), encoding="utf-8")}
    증 = {}
    for k in 둘.keys():
        r = 둘[k]
        q = rows[r["대화"]]
        길이 = r["finish"] == "length"
        s2a, s2b, _ = Z.S2_다른문자(r["text"], q["q2"])
        s6, 옮김, _ = Z.S6_맞춤법(r["text"], q["원문"])
        증[k] = {"S1": Z.S1_끝없는반복(r["tokens"], 길이) is not None, "S2": s2a or s2b, "S6": s6, "옮김": 옮김,
                 "되풀이문장": _문장되풀이(r["text"])}
    out = {}
    for 종류 in ("다른문자", "맞춤법", "되풀이"):
        ids = [d for d in rows if f"{d}_{종류}" in 증 and f"{d}_깨끗" in 증]
        A = {d: 증[f"{d}_{종류}"] for d in ids}
        B = {d: 증[f"{d}_깨끗"] for d in ids}
        out[종류] = {키: 짝셈(A, B, ids, 키) for 키 in ("S1", "S2", "S6", "되풀이문장")}
    return out


def _문장되풀이(글):
    """같은 문장(8 자 이상)이 두 번 이상 나오는가."""
    import re
    본 = set()
    for s in re.split(r"(?<=[.!?。])\s+|\n+", 글):
        s = s.strip()
        if len(s) >= 8:
            if s in 본:
                return True
            본.add(s)
    return False


# ---------------------------------------------------------------- 모두
def 명령_모두(a):
    Q = 질문표()
    결 = {"만든때": time.strftime("%Y-%m-%d %H:%M:%S")}
    색 = {}
    for 갈 in ("G", "V", "L"):
        for 모델 in ("7b", "r1"):
            p = os.path.join(a.작업, "생성", f"{갈}_{모델}.jsonl")
            if os.path.exists(p):
                색[(갈, 모델)] = 색인(p)
    증 = {k: 증상표(v, Q) for k, v in 색.items()}

    # 40a (2) 같은 입력 · 뺀 문항
    입력 = {}
    for (갈, 모델), v in 색.items():
        다름 = [k for k in v.keys() for r in [v[k]] if r.get("prompt_n") is not None and r["prompt_n"] != r["보낸수"]]
        입력[f"{갈}_{모델}"] = {"문항": len(v), "받은 수 ≠ 보낸 수": len(다름), "예": 다름[:5]}
    결["40a(2) 같은 입력"] = 입력
    # 40a (3) 결정성
    재 = {}
    for 갈 in ("G", "V"):
        p = os.path.join(a.작업, "생성", f"재현{갈}_7b.jsonl")
        if os.path.exists(p) and (갈, "7b") in 색:
            R = 색인(p)
            재[갈] = {"문항": len(R), "다름": sum(1 for k in R.keys() if R[k]["tokens"] != 색[(갈, "7b")][k]["tokens"])}
    p = os.path.join(a.작업, "생성", "재현갈래_7b.jsonl")
    if os.path.exists(p):
        R, B = 색인(p), 색인(os.path.join(a.작업, "생성", "갈래_7b.jsonl"))
        재["갈래"] = {"수": len(R), "다름": sum(1 for k in R.keys() if k in B and R[k]["tokens"] != B[k]["tokens"])}
    결["40a(3) 결정성"] = 재
    # 40a (5) 따라가기 확인
    p = os.path.join(a.작업, "따라", "확인_7b.json")
    결["40a(5) 따라가기"] = json.load(open(p, encoding="utf-8")) if os.path.exists(p) else None

    # 40c 궤적 (1차) — H1: 7b 자연 한국어 S2, H2: r1 수학 S4
    궤 = {}
    if ("G", "7b") in 증 and ("L", "7b") in 증:
        ids = sorted(k for k in 증[("G", "7b")] if k in 증[("L", "7b")] and 색[("G", "7b")][k]["묶음"] in 자연한국어)
        궤["H1"] = 짝셈(증[("L", "7b")], 증[("G", "7b")], ids, "S2")
    if ("G", "r1") in 증 and ("L", "r1") in 증:
        ids = sorted(k for k in 증[("G", "r1")] if k in 증[("L", "r1")])
        궤["H2"] = 짝셈(증[("L", "r1")], 증[("G", "r1")], ids, "S4")
    if 궤:
        고친 = Z.Holm([궤[h]["p"] for h in 궤])
        for h, p in zip(궤, 고친):
            궤[h]["고친p"] = p
            궤[h]["판정"] = Z.궤적판정(궤[h]["생김b"], 궤[h]["사라짐c"], p)
    결["40c 궤적"] = 궤
    # 40d 한 손실 — 궤적(보조)
    보 = {}
    if ("V", "7b") in 증:
        ids = sorted(k for k in 증[("V", "7b")] if k in 증[("G", "7b")] and 색[("G", "7b")][k]["묶음"] in 자연한국어)
        보["H1′"] = 짝셈(증[("V", "7b")], 증[("G", "7b")], ids, "S2")
    if ("V", "r1") in 증:
        ids = sorted(k for k in 증[("V", "r1")] if k in 증[("G", "r1")])
        보["H2′"] = 짝셈(증[("V", "r1")], 증[("G", "r1")], ids, "S4")
    for h in 보:
        보[h]["판정"] = Z.궤적판정(보[h]["생김b"], 보[h]["사라짐c"], 보[h]["p"])
    # 보조 궤적: 방아쇠 묶음(L ↔ G) — S1 · S2 · S6, 수학의 S1 · S3
    for 묶음, 키들 in (("방아쇠_글자", ("S6", "S2", "S1")), ("방아쇠_언어", ("S2", "S1")), ("방아쇠_되풀이", ("S1", "S2")),
                    ("자연_긴글", ("S1",)), ("자연_LCB", ("S1",))):
        if ("L", "7b") in 증:
            ids = sorted(k for k in 증[("G", "7b")] if k in 증[("L", "7b")] and 색[("G", "7b")][k]["묶음"] == 묶음)
            for 키 in 키들:
                보[f"{묶음}·{키}(L↔G)"] = 짝셈(증[("L", "7b")], 증[("G", "7b")], ids, 키)
    if ("L", "r1") in 증:
        ids = sorted(k for k in 증[("G", "r1")] if k in 증[("L", "r1")])
        for 키 in ("S3", "S1"):
            보[f"수학·{키}(L↔G)"] = 짝셈(증[("L", "r1")], 증[("G", "r1")], ids, 키)
    결["40d·보조 궤적"] = 보

    # 40b 기울기 (1차) — 7b 의 한국어 묶음 모두
    if os.path.exists(os.path.join(a.작업, "위험", "7b.jsonl")):
        기 = 기울기셈(a, "7b", 한국어묶음)
        ps = [기[f"L_{u}"]["p"] if 기[f"L_{u}"]["p"] is not None else 1.0 for u in "ORC"]
        고친 = Z.Holm(ps)
        for u, p in zip("ORC", 고친):
            e = 기[f"L_{u}"]
            e["고친p"] = p
            e["판정"] = Z.기울기판정(e["평균"], e["구간"], p, e["걸음"])
            v = 기[f"V_{u}"]
            if v["평균"] is not None:
                v["판정(보조)"] = Z.기울기판정(v["평균"], v["구간"], v["p"], v["걸음"])
        결["40b 기울기 7b"] = 기
    if os.path.exists(os.path.join(a.작업, "위험", "r1.jsonl")) and os.path.isdir(os.path.join(a.작업, "따라", "r1")):
        결["보조 기울기 r1"] = 기울기셈(a, "r1", ("자연_수학",))

    # 40e 번짐 · 오염
    if os.path.exists(os.path.join(a.작업, "생성", "갈래_7b.jsonl")):
        결["40e(1) 번짐"] = 번짐셈(a, Q)
    if os.path.exists(os.path.join(a.작업, "생성", "오염둘_7b.jsonl")):
        결["40e(2) 오염"] = 오염셈(a, Q)

    # 40e (3) 세 인수의 곱 — 위험한 걸음 밀도 × 뒤집힘(L 의 1위가 b) × 번짐(b 를 넣었을 때 − a 일 때), 실제 생김(L 에만 증상)과 나란히
    if "40b 기울기 7b" in 결 and "40e(1) 번짐" in 결:
        기, 번 = 결["40b 기울기 7b"], 결["40e(1) 번짐"]
        곱 = {}
        for u, 증상, 묶음들 in (("O", "S2", 한국어묶음), ("R", "S1", 한국어묶음), ("C", "S6", ("방아쇠_글자",))):
            e = 번[u]
            뒤 = 기[f"뒤집힘_{u}"]
            밀도 = 기[f"밀도_{u}(천 토큰마다)"]
            뒤율 = 뒤["L이b"] / 뒤["걸음"] if 뒤["걸음"] else None
            번차 = (e["b번짐"] - e["a번짐"]) / e["수"] if e["수"] else None
            예측 = 밀도 * 뒤율 * 번차 if None not in (밀도, 뒤율, 번차) else None
            실제 = None
            if ("L", "7b") in 증:
                ids = [k for k in 증[("G", "7b")] if k in 증[("L", "7b")] and 색[("G", "7b")][k]["묶음"] in 묶음들]
                토큰 = sum(len(색[("G", "7b")][k]["tokens"]) for k in ids)
                생 = sum(1 for k in ids if 증[("L", "7b")][k].get(증상) and not 증[("G", "7b")][k].get(증상))
                실제 = 생 / 토큰 * 1000 if 토큰 else None
            곱[u] = {"증상": 증상, "밀도(천 토큰마다)": 밀도, "뒤집힘율": 뒤율, "번짐 차": 번차, "예측 생김(천 토큰마다)": 예측,
                    "실제 생김(천 토큰마다, L 에만)": 실제}
        결["40e(3) 세 인수의 곱"] = 곱

    # 40f 흔들림
    흔 = {}
    for (갈, 모델), v in 색.items():
        if 갈 == "G" or (("G", 모델) not in 색):
            continue
        Gv = 색[("G", 모델)]
        by = {}
        for k in v.keys():
            if k not in Gv:
                continue
            r, g = v[k], Gv[k]
            e = by.setdefault(r["묶음"], [0, 0, []])
            e[0] += 1
            다름 = r["tokens"][:len(g["tokens"])] != g["tokens"][:len(r["tokens"])] or len(r["tokens"]) != len(g["tokens"])
            e[1] += 다름
            if 다름:
                f = next((i for i, (x, y) in enumerate(zip(r["tokens"], g["tokens"])) if x != y), min(len(r["tokens"]), len(g["tokens"])))
                e[2].append(f)
        흔[f"{갈}↔G {모델}"] = {b: {"문항": e[0], "글이 다름": e[1], "비율": e[1] / e[0] if e[0] else None,
                                "첫 갈림 걸음 중앙값": float(np.median(e[2])) if e[2] else None} for b, e in by.items()}
    결["40f 흔들림"] = 흔
    # 증상 비율(갈래마다)
    비 = {}
    for (갈, 모델), d in 증.items():
        by = {}
        for k, s in d.items():
            m = 색[(갈, 모델)][k]["묶음"]
            e = by.setdefault(m, {"문항": 0})
            e["문항"] += 1
            for 키, v in s.items():
                if isinstance(v, bool) and 키 not in ("길이", "옮김"):
                    e[키] = e.get(키, 0) + int(v)
        비[f"{갈}_{모델}"] = by
    결["증상 수"] = 비
    os.makedirs(a.결과, exist_ok=True)
    json.dump(결, open(os.path.join(a.결과, "40_판정.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    기록("40_판정.json 씀")
    사람확인표(a, Q, 색, 증)


def 사람확인표(a, Q, 색, 증):
    """40a (1) 사람 확인 — S1 · S2 마다 판정기의 양성 10 · 음성 10(씨앗 40). 사용자가 '맞음 / 틀림' 을 적는다."""
    rng = random.Random(씨앗)
    줄 = ["# 40단계 사람 확인 — 판정기가 맞게 판정했는가 (40a (1))", "",
         "판정기의 판정(양성 = 증상 있음)이 사람의 판단과 같으면 '맞음', 다르면 '틀림' 을 칸에 적어 주세요.", ""]
    for 키, 설명 in (("S1", "끝없는 반복 — 길이 한도에 닿았고 끝이 같은 말의 되풀이"),
                   ("S2", "다른 문자 — 한국어 답에 한글 · 라틴이 아닌 문자(한자 · 가나 · 키릴 …)가 두 자 이상 이어짐, 또는 답 대부분이 한국어가 아님")):
        양, 음 = [], []
        for (갈, 모델), d in 증.items():
            if 모델 != "7b" or 갈 == "V":
                continue
            for k, s in d.items():
                if 키 in s:
                    (양 if s[키] else 음).append((갈, k))
        양.sort()
        음.sort()
        rng.shuffle(양)
        rng.shuffle(음)
        줄.append(f"## {키} — {설명}")
        줄.append("")
        for 판, 고른 in (("양성", 양[:10]), ("음성", 음[:10])):
            for i, (갈, k) in enumerate(고른):
                r = 색[(갈, "7b")][k]
                글 = r["text"]
                if 키 == "S2":
                    _, _, 자 = Z.S2_다른문자(글, Q[k]["질문"])
                    보일 = 자["처음"] if 자["처음"] else 글[:300]
                    보일 = 글[max(0, 글.find(보일) - 150):글.find(보일) + 150] if 자["처음"] and 보일 in 글 else 글[:300]
                else:
                    보일 = 글[-400:]
                줄.append(f"### {키}-{판}-{i + 1} — 판정기: {'증상 있음' if 판 == '양성' else '증상 없음'} · `{k}` ({갈})")
                줄.append("")
                줄.append("```text")
                줄.append(보일.replace("```", "ˋˋˋ"))
                줄.append("```")
                줄.append("")
                줄.append("사람: (맞음 / 틀림)")
                줄.append("")
    with open(os.path.join(a.결과, "사람확인.md"), "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(줄) + "\n")
    기록("사람확인.md 씀")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("명령")
    ap.add_argument("--작업", required=True)
    ap.add_argument("--모델폴더", required=True)
    ap.add_argument("--결과", default=os.path.join(ROOT, "문서", "결과", "40단계"))
    a = ap.parse_args()
    {"위험": 명령_위험, "모두": 명령_모두}[a.명령](a)


if __name__ == "__main__":
    main()
