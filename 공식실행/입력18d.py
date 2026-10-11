"""18d 의 입력 파일만(시험/호스트18.py 의 엔진() 앞부분과 같은 바이트) — 0.5B 회귀 확인용."""
import os
import sys

ROOT = sys.argv[1]
출력 = sys.argv[2]
sys.path.insert(0, os.path.join(ROOT, "시험"))
import qwen2공통 as Q          # noqa: E402
import 호스트18 as H          # noqa: E402
import 토크나이저 as TK        # noqa: E402

최대행, 최대길이, 로짓행, 걸음, 최대생성 = 2048, 16384, 64, 64, 64
tk = TK.Qwen토크나이저(gguf=Q.GGUF)
경우들 = H.엔진경우들(tk)
with open(출력, "wb") as f:
    w = lambda v: f.write(int(v).to_bytes(8, "little", signed=True))
    w(최대행), w(최대길이), w(로짓행), w(len(경우들))
    for ids in 경우들:
        w(len(ids)), w(걸음)
        for t in ids:
            w(t)
    w(len(Q.질문들))
    for q in Q.질문들:
        b = q.encode("utf-8")
        w(len(b))
        f.write(b)
    w(최대생성)
print("경우", [len(x) for x in 경우들])
