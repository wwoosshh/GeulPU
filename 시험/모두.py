#!/usr/bin/env python3
"""GeulPU 의 비트 시험 모두 — 모델/ 에 있는 모델로. 결과는 빌드/결과/시험.json, 마지막 줄에 통과 여부(종료 코드 0 · 1).

  python 시험/모두.py [빠르게] [small] [XL] [긴]

고르지 않으면 있는 것 모두. 빠르게: 긴 문맥 대조를 작은 칸만(맥락 100 · 2048 · 8192 × 덩이 5 · 64 · 1024), 메가커널 대조를 맥락 둘로.
시험의 뜻은 문서/계약.md — 같은 계약이면 어느 길(판 · 묶음 · 나눠 넣기 · 대화 · 메가커널)로 계산해도 비트가 같고, CPU 참조와도 같다.
"""
import json
import os
import sys
import time

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.stderr.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import numpy as np                 # noqa: E402

import 공통 as T                   # noqa: E402
from 행렬곱 import 행렬곱시험        # noqa: E402
from 어텐션 import 층qkv, 커널대조, 긴대조     # noqa: E402
from 길 import 비트시험, 끝끝, 대화대조, 메가대조, 나눠넣기대조   # noqa: E402

G, GR = T.G, T.GR


def main():
    인자 = set(sys.argv[1:])
    빠르게 = "빠르게" in 인자
    고름 = 인자 & {"small", "XL", "긴"}
    res, 통과 = {}, True
    rng = np.random.default_rng(130)
    t시작 = time.time()
    평가글 = open(T.평가글, encoding="utf-8").read()

    def 적기(열쇠, 값):
        nonlocal 통과
        res[열쇠] = 값
        ok = 값.get("통과", True) if isinstance(값, dict) else True
        통과 &= bool(ok)
        print(f"{'통과' if ok else '실패'}  {열쇠}", flush=True)

    for 크기 in ("small", "XL"):
        if 고름 and 크기 not in 고름:
            continue
        if not T.있나(T.모델폴더(크기)):
            print(f"건너뜀  {크기} — 모델/{os.path.basename(T.모델폴더(크기))} 이 없다", flush=True)
            continue
        tk = T.토크나이저(크기)
        prompts = [tk.나누기(s) for s in T.문장들]
        평가 = tk.나누기(평가글)[:1024]
        긴 = (tk.나누기(T.문장들[1]) * 40)[:1024]
        D = 768 if 크기 == "small" else 1600
        for fmt in ("q8_0", "q4_0"):
            path = T.경로(크기, fmt)
            if not T.있나(path):
                print(f"건너뜀  {크기} {fmt} — {os.path.basename(path)} 이 없다", flush=True)
                continue
            m = T.글엔진(크기, fmt)
            열쇠 = f"{크기} {fmt}"
            mm = 행렬곱시험(m, GR.GGUF(path), rng)
            적기(f"{열쇠} 행렬곱 (판 모두 대 CPU 참조 — {len(mm)} 가지)", {"다른 칸 합": sum(v["다른 칸"] for v in mm.values()),
                                                                   "통과": all(v["다른 칸"] == 0 for v in mm.values())})
            if fmt == "q8_0" and T.있나(os.path.join(T.모델폴더(크기), "model.safetensors")):
                w = G.가중치읽기(os.path.join(T.모델폴더(크기), "model.safetensors"))
                qkv = 층qkv(w, 긴[:1024], 5 if 크기 == "small" else 20, D)
                del w
                for 판 in ("정수어텐션", "정수어텐션둘", "정수어텐션갈래"):
                    적기(f"{열쇠} 어텐션 커널 대 CPU 참조 ({판})", 커널대조(m, qkv, 1024, 커널=판))
            적기(f"{열쇠} 길 (한 번에 · 하나씩 · 두조각 · 메가커널 · 묶음 · 조각)", 비트시험(m, prompts, 긴))
            적기(f"{열쇠} 캐시 바이트 (길마다)", 끝끝(m, 평가[:469]))
            적기(f"{열쇠} 대화 길 대 한 번에", 대화대조(m, rng, [(37, 6), (5, 3), (120, 12), (16, 1), (200, 9), (1, 2), (64, 5), (33, 4),
                                                       (120, 7), (16, 3), (200, 1)]))
            적기(f"{열쇠} 대화 길 대 한 번에 — 덩이 2 · 3 · 4", 대화대조(m, rng, [(37, 2), (2, 3), (3, 1), (4, 2), (16, 1), (4, 1), (2, 2),
                                                                  (3, 4), (64, 1)]))
            적기(f"{열쇠} 오류 칸", {"오류 칸": m.오류칸(), "통과": m.오류칸() == 0})
            m.닫기()
            T.비우기()
    if (not 고름 or "긴" in 고름) and T.있나(T.긴GGUF):
        wq = GR.gpt2정수(T.긴GGUF)
        m = G.글GPT2(wq, KV형식="정수", 자리수=2, 최대행=1024, 최대문장=1, 최대길이=102400, 로짓행=16)
        맥락들, 덩이들 = (((100, 2048, 8192), (5, 64, 1024)) if 빠르게 else
                       ((100, 2048, 8192, 32768, 98000), (5, 16, 64, 128, 192, 512, 1024)))
        적기("긴 — 새 판 대 새 CPU 참조", 긴대조(m, np.random.default_rng(131), 맥락들, 덩이들))
        적기("긴 — 생성 메가커널 대 따로", 메가대조(m, np.random.default_rng(132), (300, 5000) if 빠르게 else (300, 5000, 70000, 100000)))
        m.닫기()
        T.비우기()
        적기("긴 — 나눠 넣기 대 한 번에 (위치 8192)", 나눠넣기대조(wq, np.random.default_rng(133)))
    elif not 고름 or "긴" in 고름:
        print("건너뜀  긴 — 모델/gpt2-long 이 없다", flush=True)
    res["초"] = round(time.time() - t시작)
    res["통과"] = 통과
    os.makedirs(T.결과폴더, exist_ok=True)
    json.dump(res, open(os.path.join(T.결과폴더, "시험.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    print(("모두 통과" if 통과 else "실패가 있다") + f" — {res['초']} 초, 빌드/결과/시험.json", flush=True)
    return 0 if 통과 else 1


if __name__ == "__main__":
    sys.exit(main())
