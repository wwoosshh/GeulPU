#!/usr/bin/env python3
"""15단계 판정 15a(계약 — 비트)의 시험: 생성 메가커널(생성메가qwen) 대 14단계의 생성 그래프(묶은 판) (문서/15단계.md).

  (1) 걸음마다 로짓 · 토큰이 비트까지 같다 — 채팅 질문 셋(채팅 틀) × 64 걸음, 문맥 1024 · 2100(두 층 접기) · 8192 에서 64 걸음.
      같은 엔진에서 메가쓰기 를 켜고 끄며(끄면 14단계의 생성 그래프 — 걸음마다 그래프 하나), 캐시를 비운 뒤 같은 프롬프트로.
  (2) 생성 뒤의 KV 캐시 바이트가 같다(위치 프롬프트 + 걸음 − 1 까지 — 마지막 토큰은 넣지 않는다).
  (3) 실행기의 세 차례 대화(실행.py 의 대화 — 이어넣기 · 이어생성, 끝 토큰에서 커널 안에서 멈춤)가 생성 그래프의 대화와 같은 토큰 · 같은 캐시.
  (4) GPT-2 모듈의 소스가 14단계 전과 바이트까지 같다(시험/gpt2소스해시.json); 오류 칸 0.
결과는 빌드/결과/시험15.json, 마지막 줄에 통과 여부(종료 코드 0 · 1).
  python 시험/메가15.py [빠르게]      (빠르게: 걸음 16, 문맥 8192 빼고)
"""
import hashlib
import json
import os
import sys
import time

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.stderr.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import numpy as np                 # noqa: E402

import qwen2공통 as Q              # noqa: E402
import 공통 as T                   # noqa: E402
import qwen2 as S                  # noqa: E402

import 커널생성 as K               # noqa: E402


def 걸음시험(m, ids, 걸음):
    """같은 프롬프트로 메가커널 · 생성 그래프의 (토큰, 걸음마다 로짓, 캐시 해시)."""
    out = {}
    for 메가 in (True, False):
        m.메가쓰기 = 메가
        S.캐시비우기(m)
        토큰, 로짓 = m.생성로짓(ids, 걸음)
        out[메가] = (토큰, 로짓, S.캐시모두(m, len(ids) + 걸음 - 1))
    m.메가쓰기 = True
    (t1, l1, c1), (t0, l0, c0) = out[True], out[False]
    return {"문맥": len(ids), "걸음": 걸음, "토큰 같음": t1 == t0,
            "로짓 다른 칸": int((l1.view(np.int32) != l0.view(np.int32)).sum()) if l1.shape == l0.shape else -1,
            "캐시 같음": c1 == c0, "답": t1[:12]}


def 대화견줌(m, tk, 생성=64):
    """실행기의 세 차례 대화를 메가커널 · 생성 그래프로 — 답 토큰 · 대화 토큰열 · 캐시."""
    sys.path.insert(0, Q.ROOT)
    import 실행
    out = {}
    for 메가 in (True, False):
        m.메가쓰기 = 메가
        d = 실행.대화(m, tk, 최대생성=생성)
        d.비우기()
        S.캐시비우기(m)
        답들 = [d.묻기(q)[0] for q in Q.질문들]
        out[메가] = (답들, list(d.토큰), d.위치, S.캐시모두(m, d.위치))
    m.메가쓰기 = True
    a, b = out[True], out[False]
    return {"답 같음": a[0] == b[0], "토큰열 같음": a[1] == b[1], "캐시 같음": a[3] == b[3], "토큰 수": len(a[1]),
            "답들": [tk.잇기(x) for x in a[0]]}


def main():
    빠르게 = "빠르게" in sys.argv[1:]
    res, 통과 = {}, True
    t시작 = time.time()

    def 적기(열쇠, 값, ok):
        nonlocal 통과
        res[열쇠] = 값
        통과 &= bool(ok)
        print(f"{'통과' if ok else '실패'}  {열쇠}", flush=True)
    # (4) GPT-2 모듈 소스
    옛 = json.load(open(os.path.join(HERE, "gpt2소스해시.json"), encoding="utf-8"))
    지금 = {이름: hashlib.sha256(K.source(*뜻).encode("utf-8")).hexdigest() for 이름, 뜻 in K.모듈들.items()}
    지금["gpt2XL.gl"] = hashlib.sha256(K.gpt2_source("XL").encode("utf-8")).hexdigest()
    지금["커널프롬.gl"] = hashlib.sha256(K.프롬소스().encode("utf-8")).hexdigest()
    지금["커널/gpt2.gl"] = hashlib.sha256(open(os.path.join(Q.ROOT, "커널", "gpt2.gl"), "rb").read()).hexdigest()
    다른 = [k for k in 옛 if 옛[k] != 지금.get(k)]
    적기("(4) GPT-2 모듈 소스 그대로", {"모듈 수": len(옛), "다른 것": 다른}, not 다른)
    if not Q.있나():
        print("건너뜀 — 모델이 없다:", Q.GGUF)
        sys.exit(1)
    tk = Q.토크나이저()
    m = Q.엔진(최대행=2048, 최대길이=16384, 로짓행=64)
    assert m.메가쓰기, "메가커널을 쓸 수 없는 엔진"
    걸음 = 16 if 빠르게 else 64
    # (1) · (2)
    경우들 = [(f"채팅 질문 {i}", Q.채팅(tk, q)) for i, q in enumerate(Q.질문들)]
    for n in ((1024, 2100) if 빠르게 else (1024, 2100, 8192)):
        경우들.append((f"문맥 {n}", (tk.나누기(T.문장들[1]) * 400)[:n]))
    r = {이름: 걸음시험(m, ids, 걸음) for 이름, ids in 경우들}
    for 이름, v in r.items():
        print(f"  {이름}: 문맥 {v['문맥']} · 걸음 {v['걸음']} — 토큰 {'같음' if v['토큰 같음'] else '다름'} · 로짓 다른 칸 {v['로짓 다른 칸']} · "
              f"캐시 {'같음' if v['캐시 같음'] else '다름'}", flush=True)
    적기("(1) · (2) 메가커널 대 생성 그래프 — 걸음마다 로짓 · 토큰 · 뒤의 KV 캐시", r,
         all(v["토큰 같음"] and v["로짓 다른 칸"] == 0 and v["캐시 같음"] for v in r.values()))
    # (3)
    r = 대화견줌(m, tk)
    적기("(3) 실행기의 세 차례 대화 — 메가커널 대 생성 그래프", r, r["답 같음"] and r["토큰열 같음"] and r["캐시 같음"])
    e = m.오류칸()
    적기("오류 칸", e, e == 0)
    res["초"] = round(time.time() - t시작, 1)
    os.makedirs(T.결과폴더, exist_ok=True)
    json.dump(res, open(os.path.join(T.결과폴더, "시험15.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    print("빌드/결과/시험15.json —", "모두 통과" if 통과 else "실패가 있다", f"({res['초']} 초)")
    sys.exit(0 if 통과 else 1)


if __name__ == "__main__":
    main()
