#!/usr/bin/env python3
"""40단계 사후 분석 — 엄격한 S2(S2′, 문서/40단계.md '사람 확인과 사후 분석'). 판정이 아니다.

  python -I -X utf8 재기/사후40.py --시험
  python -I -X utf8 재기/사후40.py --작업 W --모델폴더 M [--결과 문서/결과/40단계]
"""
import argparse
import json
import os
import re
import sys
import unicodedata

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, ".."))
sys.path.insert(0, HERE)
import 증상40 as Z      # noqa: E402

여닫이 = {"(": ")", "（": "）", "[": "]", "「": "」", "『": "』", "“": "”", "‘": "’"}
같은따옴 = ('"', "'")


def 가림(글):
    """따옴표 · 괄호 안의 글자 자리(가림=참). 줄을 넘지 않는다. ' 는 라틴 글자 사이(아포스트로피)면 따옴으로 보지 않는다."""
    m = [False] * len(글)
    더미 = []                 # (닫는 글자, 연 자리)
    for i, ch in enumerate(글):
        if ch == "\n":
            더미 = []
            continue
        if 더미 and ch == 더미[-1][0]:
            _, s = 더미.pop()
            for j in range(s, i + 1):
                m[j] = True
            continue
        if ch in 여닫이:
            더미.append((여닫이[ch], i))
            continue
        if ch in 같은따옴:
            if ch == "'" and 0 < i < len(글) - 1 and 글[i - 1].isascii() and 글[i - 1].isalpha() and 글[i + 1].isascii() and 글[i + 1].isalpha():
                continue
            더미.append((ch, i))
    return m


_라틴낱말 = re.compile(r"[A-Za-z][A-Za-z'’\-]+")


def S2_엄격(답, 질문):
    """(S2a′, S2b′, 자세히)."""
    글 = Z.코드빼기(답)
    m = 가림(글)
    질문글자 = set(질문)
    # S2a′: 가려지지 않은 다른 문자 두 자 이상 — 바로 뒤(빈칸 하나까지)에 한글이 든 괄호가 오면 세지 않음
    a = False
    처음 = None
    i = 0
    n = len(글)
    while i < n:
        if not m[i] and Z.다른문자인가(글[i]) and 글[i] not in 질문글자:
            j = i
            while j < n and not m[j] and Z.다른문자인가(글[j]) and 글[j] not in 질문글자:
                j += 1
            if j - i >= 2:
                k = j
                if k < n and 글[k] == " ":
                    k += 1
                풀이 = False
                if k < n and 글[k] in ("(", "（"):
                    e = 글.find(")" if 글[k] == "(" else "）", k)
                    if e > k and any(Z.한글인가(ord(c)) for c in 글[k + 1:e]):
                        풀이 = True
                if not 풀이:
                    a = True
                    처음 = 글[max(0, i - 12):j + 4]
                    break
            i = j
        else:
            i += 1
    # S2b′: 가려지지 않은 글자 중 한글 < 50 % — 질문에 있는 라틴 낱말은 빼고
    질문낱말 = {w.lower() for w in _라틴낱말.findall(질문)}
    빼 = [False] * n
    for mt in _라틴낱말.finditer(글):
        if mt.group().lower() in 질문낱말:
            for j in range(mt.start(), mt.end()):
                빼[j] = True
    한 = 글자 = 0
    for j, ch in enumerate(글):
        if m[j] or 빼[j]:
            continue
        if unicodedata.category(ch).startswith("L"):
            글자 += 1
            if Z.한글인가(ord(ch)):
                한 += 1
    b = 글자 > 0 and 한 / 글자 < 0.5
    return a, b, {"처음": 처음, "한글": 한, "글자": 글자}


def _시험():
    n = 0

    def 맞다(x, 말):
        nonlocal n
        n += 1
        assert x, 말
    a, b, _ = S2_엄격("남경(南京)은 중국의 도시입니다.", "")
    맞다(not a, "괄호 안의 한자는 가림")
    a, b, _ = S2_엄격("南京(난징)은 중국 장쑤성의 성도입니다.", "")
    맞다(not a, "한자 뒤에 한글 읽기 괄호")
    a, b, _ = S2_엄격("南京 (난징)은 중국의 도시입니다.", "")
    맞다(not a, "빈칸 하나 뒤의 읽기 괄호")
    a, b, _ = S2_엄격("'南京'이라는 말은 남쪽의 수도를 뜻합니다.", "")
    맞다(not a, "따옴표 안의 한자")
    a, b, _ = S2_엄격("그래서 우리는 因此 다음으로 넘어갑니다.", "")
    맞다(a, "그냥 섞인 한자는 센다")
    a, b, _ = S2_엄격("Taylor Swift의 앨범은 \"Death by a Thousand Cuts\"와 \"Dress\"를 담고 있다.", "Taylor Swift … Death by a Thousand Cuts, Dress")
    맞다(not a and not b, "인용한 영어 제목 · 질문의 이름은 빼고 센다")
    a, b, _ = S2_엄격("Taylor Swift의 앨범은 \"Death by a Thousand Cuts\"와 \"Dress\"를 담고 있다.", "Death by a Thousand Cuts, Dress")
    맞다(b, "질문에 없는 영어 이름이 한글보다 많으면 여전히 S2b′")
    a, b, _ = S2_엄격("Swift's album is great and the songs are lovely.", "Reply in Korean.")
    맞다(b, "아포스트로피는 따옴 아님 — 영어 답은 S2b′")
    a, b, _ = S2_엄격("The scene opens in a restaurant where Ray sits.", "Use Korean. Ray Liotta")
    맞다(b, "질문의 낱말을 빼도 영어 답은 S2b′")
    a, b, _ = S2_엄격("Привет 친구", "")
    맞다(a, "키릴은 센다")
    a, b, _ = S2_엄격("한국어 답 (and some English) 입니다", "")
    맞다(not b, "괄호 안 영어는 빼고 한글 비율")
    m = 가림("a (b\nc) d")
    맞다(not any(m), "닫히지 않고 줄을 넘는 괄호는 가리지 않음")
    print(f"사후 단위 시험 {n} 개 통과")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--작업")
    ap.add_argument("--모델폴더")
    ap.add_argument("--결과", default=os.path.join(ROOT, "문서", "결과", "40단계"))
    ap.add_argument("--시험", action="store_true")
    a = ap.parse_args()
    if a.시험:
        return _시험()
    import 셈40 as S
    Q = S.질문표()
    색 = {k: S.색인(os.path.join(a.작업, "생성", f"{k}_7b.jsonl")) for k in ("G", "L", "V")}

    def 표(색인):
        out = {}
        for k in 색인.keys():
            r = 색인[k]
            if r["묶음"] in ("자연_수학",):
                continue
            q = Q[k]["질문"]
            a1, b1, _ = Z.S2_다른문자(r["text"], q)
            a2, b2, _ = S2_엄격(r["text"], q)
            out[k] = {"S2": a1 or b1, "S2′": a2 or b2, "S2a′": a2, "S2b′": b2, "묶음": r["묶음"]}
        return out
    T = {g: 표(c) for g, c in 색.items()}
    결 = {"정의": "문서/40단계.md '사람 확인과 사후 분석' — 판정이 아니다"}
    # 사람 확인 20 항목(S2)과의 일치 — 규칙을 정하는 데 쓴 항목이라 독립된 확인이 아니다
    사람틀림 = {"S2-양성-1", "S2-양성-3", "S2-양성-6"}
    s = open(os.path.join(ROOT, "문서", "결과", "40단계", "사람확인.md"), encoding="utf-8").read()
    항목 = re.findall(r"### (S2-(?:양성|음성)-\d+) — 판정기: ([^·]+)· `([^`]+)` \((\w)\)", s)
    일치 = []
    for 이름, 판, k, 갈 in 항목:
        사람증상 = ("있음" in 판) != (이름 in 사람틀림)
        엄격 = T[갈][k]["S2′"]
        일치.append({"항목": 이름, "사람": 사람증상, "S2": "있음" in 판, "S2′": 엄격})
    결["사람 확인과의 일치(S2 · S2′)"] = {"S2": sum(x["사람"] == x["S2"] for x in 일치), "S2′": sum(x["사람"] == x["S2′"] for x in 일치),
                                    "항목": len(일치), "다른 항목": [x for x in 일치 if x["사람"] != x["S2′"]]}
    # H1 · H1′ (S2′)
    for 이름, A in (("H1(L↔G)", "L"), ("H1′(V↔G)", "V")):
        ids = sorted(k for k in T[A] if k in T["G"] and T["G"][k]["묶음"] in ("자연_LCB", "자연_긴글"))
        for 키 in ("S2", "S2′"):
            결[f"{이름} · {키}"] = S.짝셈(T[A], T["G"], ids, 키)
    # 묶음마다의 비율
    비 = {}
    for g, t in T.items():
        by = {}
        for k, v in t.items():
            e = by.setdefault(v["묶음"], {"문항": 0, "S2": 0, "S2′": 0})
            e["문항"] += 1
            e["S2"] += v["S2"]
            e["S2′"] += v["S2′"]
        비[g] = by
    결["묶음마다 S2 · S2′"] = 비
    # 방아쇠 · 언어 (L ↔ G, 보조)
    ids = sorted(k for k in T["L"] if k in T["G"] and T["G"][k]["묶음"] == "방아쇠_언어")
    결["방아쇠_언어 L↔G · S2′"] = S.짝셈(T["L"], T["G"], ids, "S2′")
    # 오염 — 둘째 답의 S2′
    둘 = S.색인(os.path.join(a.작업, "생성", "오염둘_7b.jsonl"))
    rows = {json.loads(l)["id"]: json.loads(l) for l in open(os.path.join(ROOT, "시험", "질문40", "오염.jsonl"), encoding="utf-8")}
    증 = {}
    for k in 둘.keys():
        r = 둘[k]
        a2, b2, _ = S2_엄격(r["text"], rows[r["대화"]]["q2"])
        증[k] = {"S2′": a2 or b2}
    for 종류 in ("다른문자", "맞춤법", "되풀이"):
        ids2 = [d for d in rows if f"{d}_{종류}" in 증 and f"{d}_깨끗" in 증]
        결[f"오염 {종류} · S2′"] = S.짝셈({d: 증[f"{d}_{종류}"] for d in ids2}, {d: 증[f"{d}_깨끗"] for d in ids2}, ids2, "S2′")
    # 번짐 O — S2a′ 로
    표_, 특수, 계통 = S.모델표(None, a.모델폴더, "7b")
    G = 색["G"]
    B = S.색인(os.path.join(a.작업, "생성", "갈래_7b.jsonl"))
    목록 = [json.loads(l) for l in open(os.path.join(a.작업, "위험", "갈래목록_7b.jsonl"), encoding="utf-8")]
    e = {"수": 0, "b번짐": 0, "a번짐": 0, "b만": 0, "a만": 0}
    for x in 목록:
        if x["유형"] != "O" or x["key"] not in B:
            continue
        g = G[x["id"]]
        br = B[x["key"]]
        창 = len(br["tokens"])
        q = Q[x["id"]]["질문"]
        fb = S2_엄격(S.글로(br["tokens"], 표_), q)[0]
        fa = S2_엄격(S.글로(g["tokens"][x["t"] + 1:x["t"] + 1 + 창], 표_), q)[0]
        e["수"] += 1
        e["b번짐"] += fb
        e["a번짐"] += fa
        e["b만"] += fb and not fa
        e["a만"] += fa and not fb
    e["p"] = Z.McNemar(e["b만"], e["a만"])
    결["번짐 O · S2a′"] = e
    p = os.path.join(a.결과, "40_사후_S2엄격.json")
    json.dump(결, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps(결, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
