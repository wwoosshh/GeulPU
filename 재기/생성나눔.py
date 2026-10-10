"""15단계 판정 전에 잰 것 — 14단계 생성 그래프의 시간 나누기(문서/15단계.md): 생성 그래프에서 커널 종류 하나만 남긴(층 24 개 모두 — 실제
DRAM 읽기) 그래프의 시간, 그리고 종류 하나를 뺀 그래프의 시간. 값은 틀린다(재는 데만). 인자: 문맥 길이(기본 채팅 질문)."""
import ctypes
import os
import sys
import time

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path.insert(0, os.path.join(ROOT, "시험"))
import numpy as np            # noqa: E402
import qwen2공통 as Q         # noqa: E402
import 공통 as T              # noqa: E402

문맥 = int(sys.argv[1]) if len(sys.argv) > 1 else 0
e = Q.엔진(최대행=2048, 최대길이=16384, 로짓행=64)
tk = Q.토크나이저()
ids = Q.채팅(tk, Q.질문들[2]) if 문맥 == 0 else (tk.나누기(T.문장들[1]) * 400)[:문맥]
e.생성(ids, 4)
L = e._생성그래프[0]
이름 = {}
for n, f in e.k.items():
    이름[f.value] = n
cu = e.dr.cu


def 그래프시간(L2, 번=50):
    ex, g, _ = e._그래프만들기(L2)
    for _ in range(5):
        e._걸음두기(len(ids) + 3)
        cu.cuGraphLaunch(ex, None)
    e.dr.맞추기()
    ts = []
    for _ in range(번):
        e._걸음두기(len(ids) + 3)
        e.dr.맞추기()
        t0 = time.perf_counter()
        cu.cuGraphLaunch(ex, None)
        e.dr.맞추기()
        ts.append((time.perf_counter() - t0) * 1000)
    cu.cuGraphExecDestroy(ex)
    cu.cuGraphDestroy(g)
    return float(np.median(ts))


전체 = 그래프시간(L)
print(f"전체 {전체:.4f} ms ({len(L)} 커널)")
종류들 = sorted(set(이름[x.fn.value] for x in L), key=lambda n: [이름[x.fn.value] for x in L].index(n))
for n in 종류들:
    만 = [x for x in L if 이름[x.fn.value] == n]
    빼 = [x for x in L if 이름[x.fn.value] != n]
    print(f"{n:24s} 개수 {len(만):3d}  그것만 {그래프시간(만):.4f} ms  뺀 것 {그래프시간(빼):.4f} ms (차 {전체 - 그래프시간(빼):.4f})")
