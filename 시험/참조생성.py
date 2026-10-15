#!/usr/bin/env python3
"""37단계 — CPU 참조(정수 계약의 앞으로 — 시험/참조7B.py 의 앞으로)로 채팅 질문에 탐욕 생성한다. 판정이 아니다: 참조가 모델의 뜻대로
셈하는지(머리 정규화의 자리 · 묶인 출력 · 치우침 없음) 글로 보고, llama.cpp 의 탐욕 생성(같은 프롬프트)과 견준다. 걸음마다 전체 앞으로를
다시 한다(느리지만 단순 — 작은 모델의 짧은 대화용). 채팅 틀은 구조에 맞춰(qwen3 는 기본 시스템 말 없음 — 엔진/토크나이저.py).

  python -I -X utf8 시험/참조생성.py <gguf> <출력.json> [--걸음 16] [--생각] "질문" …
--생각 이 없으면 Qwen3 는 생각 끔(enable_thinking=False — '<think>\\n\\n</think>\\n\\n' 를 붙임).
"""
import json
import os
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, ".."))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, "엔진"))
import gguf읽기 as GR       # noqa: E402
import 토크나이저 as TK     # noqa: E402
import 참조7B as R          # noqa: E402


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    a = sys.argv[1:]
    gguf, 출력 = a[0], a[1]
    걸음, 생각, 질문들 = 16, False, []
    i = 2
    while i < len(a):
        if a[i] == "--걸음":
            걸음 = int(a[i + 1])
            i += 2
            continue
        if a[i] == "--생각":
            생각 = True
        else:
            질문들.append(a[i])
        i += 1
    g = GR.GGUF(gguf)
    tk = TK.Qwen토크나이저(gguf=g)
    구조 = R.설정(g)["구조"]
    결과 = {"모델": os.path.basename(gguf), "구조": 구조, "생각": 생각, "걸음": 걸음, "경우": []}
    for q in 질문들:
        말 = [{"role": "user", "content": q}]
        글 = TK.채팅틀qwen3(말, 생각=생각) if 구조 == "qwen3" else TK.채팅틀(말)
        ids = tk.나누기(글)
        S = list(ids)
        t0 = time.time()
        for _ in range(걸음):
            로짓, _ = R.앞으로(g, [np.array(S, np.int64)], 말=False, 끝행만=True)
            t = int(np.argmax(로짓[0]))                     # 가장 큰 번호 중 가장 작은 것(계약 5절 1)
            S.append(t)
            if t in tk.끝들:
                break
        생성 = S[len(ids):]
        한 = {"질문": q, "프롬프트": ids, "생성": 생성, "글": tk.잇기(생성), "초": round(time.time() - t0, 1)}
        결과["경우"].append(한)
        print(f"[{q}] → {한['글']!r} ({len(생성)} 토큰 · {한['초']} 초)", flush=True)
    json.dump(결과, open(출력, "w", encoding="utf-8"), ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
