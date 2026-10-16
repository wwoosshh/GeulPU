#!/usr/bin/env python3
"""40단계 사람 확인 2차 — 엄격한 S2(S2′, 재기/사후40.py)를 새 표본으로 확인한다.

첫 확인(사람확인.md)의 20 항목은 S2′ 의 규칙을 정하는 데 쓰였으므로 독립된 확인이 아니다. 여기서는 그 항목을 빼고,
G · L(7B · 한국어 묶음)의 답 가운데 S2′ 양성 20 · 음성 20 을 씨앗 41 로 뽑아 사람이 볼 표를 쓴다. 발췌는 길게 — 양성은 처음
잡힌 자리의 앞뒤 400 자(S2b′ 는 앞 800 자), 음성은 앞 1,200 자와 끝 600 자. 질문도 함께 보인다.

  python -I -X utf8 재기/사람확인2.py --작업 W [--결과 문서/결과/40단계] [--씨앗 41] [--수 20]
"""
import argparse
import os
import random
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, ".."))
sys.path.insert(0, HERE)
import 사후40 as H      # noqa: E402
import 셈40 as S        # noqa: E402

한국어묶음 = ("자연_LCB", "자연_긴글", "방아쇠_글자", "방아쇠_언어", "방아쇠_되풀이")


def 첫확인항목(결과폴더):
    """사람확인.md 의 S2 항목 (문항, 갈래) — 새 표본에서 뺀다."""
    s = open(os.path.join(결과폴더, "사람확인.md"), encoding="utf-8").read()
    return {(k, 갈) for k, 갈 in re.findall(r"### S2-(?:양성|음성)-\d+ — 판정기: [^·]+· `([^`]+)` \((\w)\)", s)}


def 발췌(글, 자세히, 양성):
    if 양성:
        처음 = 자세히.get("처음")
        if 처음 and 처음 in 글:
            i = 글.find(처음)
            s, e = max(0, i - 400), min(len(글), i + len(처음) + 400)
            머리 = "" if s == 0 else f"… (앞 {s} 자 생략)\n"
            꼬리 = "" if e == len(글) else f"\n… (뒤 {len(글) - e} 자 생략)"
            return 머리 + 글[s:e] + 꼬리
        return 글[:800] + ("" if len(글) <= 800 else f"\n… (뒤 {len(글) - 800} 자 생략)")
    if len(글) <= 1800:
        return 글
    return 글[:1200] + f"\n… (가운데 {len(글) - 1800} 자 생략) …\n" + 글[-600:]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--작업", required=True)
    ap.add_argument("--결과", default=os.path.join(ROOT, "문서", "결과", "40단계"))
    ap.add_argument("--씨앗", type=int, default=41)
    ap.add_argument("--수", type=int, default=20)
    a = ap.parse_args()
    Q = S.질문표()
    뺄 = 첫확인항목(a.결과)
    양, 음 = [], []
    for 갈 in ("G", "L"):
        색 = S.색인(os.path.join(a.작업, "생성", f"{갈}_7b.jsonl"))
        for k in 색.keys():
            r = 색[k]
            if r["묶음"] not in 한국어묶음 or (k, 갈) in 뺄:
                continue
            s2a, s2b, 자 = H.S2_엄격(r["text"], Q[k]["질문"])
            (양 if (s2a or s2b) else 음).append((갈, k, bool(s2a), bool(s2b), 자, r["text"]))
    양.sort(key=lambda x: (x[1], x[0]))
    음.sort(key=lambda x: (x[1], x[0]))
    rng = random.Random(a.씨앗)
    rng.shuffle(양)
    rng.shuffle(음)
    줄 = ["# 40단계 사람 확인 2차 — 엄격한 S2 판정기(S2′)는 맞게 판정하는가", "",
         f"[사후40.py](../../../재기/사후40.py)의 엄격한 판정기(S2′: 따옴표 · 괄호 안, 한글 읽기가 붙은 외국 글, 질문에 있는 라틴 낱말은 세지 않음)를",
         f"첫 확인에 쓰지 않은 새 항목으로 확인한다 — 양성 {a.수} · 음성 {a.수}(G · L 의 7B 한국어 답, 씨앗 {a.씨앗}). 후보: 양성 {len(양)} · 음성 {len(음)}.", "",
         "**판정의 뜻** — '증상 있음' = 한국어로 답해야 하는데 한글 · 라틴이 아닌 문자(한자 · 가나 · 키릴 …)가 **설명 · 인용이 아닌 자리에** 두 자 이상",
         "이어지거나, 답의 대부분이 한국어가 아니다. 한자말을 풀이하려고 괄호 안에 쓴 한자, 인용한 제목 · 고유명사, 질문이 영어 답을 요구한 경우는",
         "증상이 아니다. 판정기의 판정이 사람의 판단과 같으면 '맞음', 다르면 '틀림' — 첫 확인처럼 **틀린 항목 번호만** 알려 주셔도 된다.", ""]
    for 판, 고른 in (("양성", 양[:a.수]), ("음성", 음[:a.수])):
        줄.append(f"## S2′ {판} — 판정기: {'증상 있음' if 판 == '양성' else '증상 없음'}")
        줄.append("")
        for i, (갈, k, s2a, s2b, 자, 글) in enumerate(고른):
            까닭 = ("S2a′ 다른 문자 이어짐" if s2a else "") + (" · " if s2a and s2b else "") + ("S2b′ 한글 50 % 미만" if s2b else "")
            줄.append(f"### S2′-{판}-{i + 1} — 판정기: {'증상 있음 (' + 까닭 + ')' if 판 == '양성' else '증상 없음'} · `{k}` ({갈})")
            줄.append("")
            질문 = Q[k]["질문"]
            줄.append("질문:")
            줄.append("```text")
            줄.append((질문[:400] + ("" if len(질문) <= 400 else " …")).replace("```", "ˋˋˋ"))
            줄.append("```")
            줄.append(f"답({len(글)} 자):")
            줄.append("```text")
            줄.append(발췌(글, 자, 판 == "양성").replace("```", "ˋˋˋ"))
            줄.append("```")
            줄.append("")
            줄.append("사람: (맞음 / 틀림)")
            줄.append("")
    p = os.path.join(a.결과, "사람확인2.md")
    with open(p, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(줄) + "\n")
    print(f"{p} 씀 — 양성 {min(a.수, len(양))} · 음성 {min(a.수, len(음))} (후보 {len(양)} · {len(음)}, 첫 확인 항목 {len(뺄)} 개 뺌)")


if __name__ == "__main__":
    main()
