#!/usr/bin/env python3
"""28단계 모음 — 28d 속도(미리 적은 기준: 문서/28단계.md)와 기록(llama-server · 다른 모델 · 첫 토큰).

  python -I 재기/모음28.py <결과 폴더(문서/결과/28단계)> <출력.json>

읽는 것: 28d_엔진_q4_0.txt(재기_7B — 생성 채팅 질문 = 엔진만 잰 생성), 28d_글_슬롯4.json · 28d_글_슬롯8.json(재기/서버재기28.py),
기록 28기록_*.json. 하네스의 바퀴마다 K 의 걸음 ms · 합 처리량 → K 마다 세 바퀴의 가운데 값.
"""
import glob
import json
import os
import re
import statistics
import sys


def 엔진생성(경로):
    for 줄 in open(경로, encoding="utf-8"):
        m = re.match(r"생성 채팅 질문 ([\d.]+)", 줄)
        if m:
            return float(m.group(1))
    return None


def 하네스(경로):
    """K → {걸음ms, 합처리량} (바퀴들의 가운데 값)"""
    if not os.path.exists(경로):
        return None
    out = {}
    for r in json.load(open(경로, encoding="utf-8")):
        out.setdefault(r["K"], []).append(r)
    return {K: {"걸음ms": statistics.median(x["걸음ms"] for x in v), "합처리량": statistics.median(x["합처리량"] for x in v), "바퀴": len(v)}
            for K, v in sorted(out.items())}


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    폴더, 출력 = sys.argv[1:3]
    결과 = {"판정": {}, "기록": {}}
    엔진 = 엔진생성(os.path.join(폴더, "28d_엔진_q4_0.txt"))
    글4 = 하네스(os.path.join(폴더, "28d_글_슬롯4.json"))
    글8 = 하네스(os.path.join(폴더, "28d_글_슬롯8.json"))
    비1 = 글4[1]["걸음ms"] / 엔진
    비4 = 글4[4]["합처리량"] / 글4[1]["합처리량"]
    비8 = 글8[8]["합처리량"] / 글8[1]["합처리량"]
    결과["판정"]["28d (1) 한 스트림"] = {"서버 걸음 ms": round(글4[1]["걸음ms"], 4), "엔진 ms": 엔진, "비": round(비1, 4), "기준": "≤ 1.03", "통과": 비1 <= 1.03}
    결과["판정"]["28d (2) 넷 스트림"] = {"합 토큰/초": round(글4[4]["합처리량"], 2), "한 스트림": round(글4[1]["합처리량"], 2), "배": round(비4, 4),
                                    "기준": "≥ 2.5", "통과": 비4 >= 2.5}
    결과["판정"]["28d (3) 슬롯 8 · 여덟 스트림"] = {"합 토큰/초": round(글8[8]["합처리량"], 2), "한 스트림": round(글8[1]["합처리량"], 2), "배": round(비8, 4),
                                           "기준": "≥ 4.0", "통과": 비8 >= 4.0}
    for k, v in 결과["판정"].items():
        print(f"{k}: {v}")
    결과["글 슬롯 4"] = 글4
    결과["글 슬롯 8"] = 글8
    for 이름 in ("28d_라마_슬롯4.json", "28d_라마_슬롯8.json"):
        결과["기록"][이름] = 하네스(os.path.join(폴더, 이름))
    for 경로 in sorted(glob.glob(os.path.join(폴더, "28기록_처리량_*.json"))):
        결과["기록"][os.path.basename(경로)] = 하네스(경로)
    for 경로 in sorted(glob.glob(os.path.join(폴더, "28기록_첫토큰_*.json"))):
        r = json.load(open(경로, encoding="utf-8"))
        결과["기록"][os.path.basename(경로)] = {k: statistics.median(v) for k, v in r.items()}
    라4 = 결과["기록"].get("28d_라마_슬롯4.json")
    if 라4:
        결과["기록"]["llama-server 대비 걸음 r(슬롯 4)"] = {K: round(글4[K]["걸음ms"] / 라4[K]["걸음ms"], 4) for K in 글4 if K in 라4}
    라8 = 결과["기록"].get("28d_라마_슬롯8.json")
    if 라8:
        결과["기록"]["llama-server 대비 걸음 r(슬롯 8)"] = {K: round(글8[K]["걸음ms"] / 라8[K]["걸음ms"], 4) for K in 글8 if K in 라8}
    for k, v in 결과["기록"].items():
        print(f"기록 {k}: {v}")
    json.dump(결과, open(출력, "w", encoding="utf-8"), ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
