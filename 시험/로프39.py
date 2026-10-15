#!/usr/bin/env python3
"""39a (1) — RoPE 표(계약 4.7 — 늘이기 인자): 글 호스트(`호스트/시험_로프.gl`)가 GGUF 의 θ · rope_freqs 로 지은 cos · sin 표 [위치][64] 의
SHA-256 이 CPU 참조(`계약/정수계약.py` 의 rope표 — decimal 로 바르게)와 같은가. 위치 0 ~ 길이 − 1 전부.

  python -I 시험/로프39.py <시험_로프.exe> <출력.json> <gguf> [<gguf> …] [--길이 131072]
"""
import hashlib
import json
import os
import subprocess
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, ".."))
for _d in ("엔진", "계약"):
    sys.path.insert(0, os.path.join(ROOT, _d))
import gguf읽기 as GR       # noqa: E402
import 정수계약 as C        # noqa: E402


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    a = [x for x in sys.argv[1:] if not x.startswith("--")]
    길이 = 131072
    if "--길이" in sys.argv:
        길이 = int(sys.argv[sys.argv.index("--길이") + 1])
        a = [x for x in a if x != str(길이)]
    exe, 출력, 파일들 = a[0], a[1], a[2:]
    결과 = {"길이": 길이, "파일": []}
    for f in 파일들:
        g = GR.GGUF(f)
        m = g.meta
        구조 = m["general.architecture"]
        θ = float(m[구조 + ".rope.freq_base"])
        D, NH = m[구조 + ".embedding_length"], m[구조 + ".attention.head_count"]
        hd = int(m.get(구조 + ".attention.key_length", D // NH))
        인자 = g.풀기("rope_freqs.weight") if 구조 == "llama" and "rope_freqs.weight" in g.tensors else None
        t0 = time.time()
        cos, sin = C.rope표(길이, θ, hd=hd, 인자=인자)
        참조 = (hashlib.sha256(np.ascontiguousarray(cos, np.float32).tobytes()).hexdigest(),
              hashlib.sha256(np.ascontiguousarray(sin, np.float32).tobytes()).hexdigest())
        t1 = time.time()
        p = subprocess.run([exe, f, str(길이)], capture_output=True, text=True, encoding="utf-8", errors="replace")
        글 = {}
        for 줄 in p.stdout.splitlines():
            if 줄.startswith("코사인 "):
                글["cos"] = 줄.split()[1]
            elif 줄.startswith("사인 "):
                글["sin"] = 줄.split()[1]
        한 = {"파일": os.path.basename(f), "구조": 구조, "θ": θ, "머리": hd, "인자": None if 인자 is None else [float(x) for x in 인자],
              "참조 cos": 참조[0], "참조 sin": 참조[1], "글 cos": 글.get("cos"), "글 sin": 글.get("sin"),
              "같음": 글.get("cos") == 참조[0] and 글.get("sin") == 참조[1], "참조 초": round(t1 - t0, 1),
              "글 출력": p.stdout.strip().splitlines()[:1], "글 오류": p.stderr.strip()[-300:]}
        결과["파일"].append(한)
        print(f"{한['파일']}: θ {θ:g} · 인자 {'있음' if 인자 is not None else '없음'} — {'같음' if 한['같음'] else '다름'}"
              f" (참조 {한['참조 초']} 초 · 글 {한['글 출력']})", flush=True)
    결과["모두 같음"] = all(x["같음"] for x in 결과["파일"])
    print("39a (1):", "모두 같음" if 결과["모두 같음"] else "다른 표가 있다", flush=True)
    json.dump(결과, open(출력, "w", encoding="utf-8"), ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
