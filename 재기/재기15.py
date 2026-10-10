#!/usr/bin/env python3
"""15단계 판정의 공식 측정 — Qwen2.5-0.5B-Instruct Q8_0 (공식 GGUF): 생성 메가커널 대 14단계 생성 그래프 대 llama.cpp b11496 (기본 설정).
판정 기준(문서/15단계.md)은 측정보다 먼저 커밋했다(2187d65). 재는 법은 14단계(재기/재기14.py)와 같다.

  python 재기/재기15.py

  15b 생성 — 토큰당 = (65 토큰 − 1 토큰) / 64: 채팅 질문(셋째) · 문맥 1024 · 8192, 엔진을 번갈아(메가커널 · 14단계 그래프 · llama.cpp)
               일곱 번 × 세 묶음. 메가커널과 그래프는 같은 엔진(같은 가중치 · 같은 캐시 자리)에서 메가쓰기 만 바꾼다.
  15c 바닥 — 채팅 질문의 메가커널 토큰당 ÷ 가중치를 한 번 읽는 시간(525 MB ÷ 504 GB/s = 1.041 ms).
  15d 프롬프트 — 처리 + 첫 토큰: 128 · 2048 · 8192 토큰(문장 1 의 되풀이 — 14단계와 같은 열), 엔진을 번갈아(글 · llama.cpp) 일곱 번 × 세 묶음.
결과는 빌드/결과/재기15.json.
"""
import json
import os
import sys
import time

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.stderr.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import 엔진들 as E            # noqa: E402

T = E.T
sys.path.insert(0, os.path.join(T.ROOT, "시험"))
import qwen2공통 as Q         # noqa: E402

바닥 = 1.041                  # ms — 가중치 525 MB ÷ 504 GB/s (문서/15단계.md)
기준14 = {"생성": {"채팅 질문": 1.623, "문맥 1024": 1.695, "문맥 8192": 1.999}, "프롬프트": {"128": 3.77, "2048": 24.3, "8192": 160.8}}


class 글큐(E.글엔진):
    """엔진들.글엔진 과 같은 일을 글Qwen2 하나로 — 메가: 생성을 메가커널로(거짓이면 14단계의 생성 그래프). 둘이 엔진 하나를 함께 쓴다."""

    def __init__(self, m, 이름, 메가):
        self.m, self.이름, self.메가 = m, 이름, 메가

    def 프롬프트(self, ids):
        self.m.메가쓰기 = self.메가
        self.m.생성(ids, 1)

    def 생성(self, ids, n):
        self.m.메가쓰기 = self.메가
        return self.m.생성(ids, n)

    def 닫기(self):
        pass


def 속도(res):
    import 글qwen2
    tk = Q.토크나이저()
    긴 = (tk.나누기(T.문장들[1]) * 400)[:8192]
    채팅 = Q.채팅(tk, Q.질문들[2])
    일 = E.일꾼()
    실패 = res.setdefault("실패", {})
    m = 글qwen2.글Qwen2(Q.GGUF, 최대행=8192, 최대길이=16384, 로짓행=64)
    m.판미리고르기()
    assert m.메가쓰기, "메가커널을 쓸 수 없는 엔진"
    try:
        메가, 그래프 = 글큐(m, "글 메가커널", True), 글큐(m, "글 그래프 (14단계)", False)
        라 = E.라마엔진(일, "llama.cpp", Q.GGUF, n_ctx=16384, n_batch=2048, n_ubatch=512)
        res["llama.cpp 문맥"] = 라.문맥
        g = {}
        for 이름, ids in (("채팅 질문", 채팅), ("문맥 1024", 긴[:1024]), ("문맥 8192", 긴[:8192])):
            엔진들 = [메가, 그래프, 라]
            E.데우기(엔진들, lambda e: e.생성(ids, 65), 실패)
            t1, _ = E.세묶음(엔진들, lambda e: e.잰_생성(ids, 1), 실패)
            t65, _ = E.세묶음(엔진들, lambda e: e.잰_생성(ids, 65), 실패)
            g[이름] = {k: round((t65[k] - t1[k]) / 64, 4) for k in t1 if k in t65}
            g[이름]["기준 (14단계 공식의 0.85 배)"] = round(0.85 * 기준14["생성"][이름], 4)
            print("생성", 이름, g[이름], flush=True)
        res["15b 생성 ms/토큰"] = g
        c = g["채팅 질문"]["글 메가커널"]
        res["15c 바닥 비 (채팅 질문 ÷ 1.041 ms)"] = round(c / 바닥, 4)
        print("바닥 비", res["15c 바닥 비 (채팅 질문 ÷ 1.041 ms)"], flush=True)
        p = {}
        글 = 글큐(m, "글", True)                         # 프롬프트는 메가커널과 상관없다(생성 1 토큰 — 프롬프트 판 + 첫 토큰)
        for n in (128, 2048, 8192):
            ids = 긴[:n]
            엔진들 = [글, 라]
            E.데우기(엔진들, lambda e: e.프롬프트(ids), 실패)
            중, 묶음 = E.세묶음(엔진들, lambda e: e.잰_프롬프트(ids), 실패)
            p[str(n)] = {"중앙값 ms": 중, "세 묶음": 묶음, "14단계 공식": 기준14["프롬프트"][str(n)],
                         "비 (글 / 14단계)": round(중["글"] / 기준14["프롬프트"][str(n)], 4)}
            print("프롬프트", n, p[str(n)]["중앙값 ms"], p[str(n)]["비 (글 / 14단계)"], flush=True)
        res["15d 프롬프트 ms (처리 + 첫 토큰)"] = p
        res["오류 칸 (속도)"] = m.오류칸()
        라.닫기()
    finally:
        m.닫기()
        일.끝()


def main():
    경로 = os.path.join(T.결과폴더, "재기15.json")
    res = {"GPU": "RTX 4070 Ti"}
    t0 = time.time()
    속도(res)
    res["초"] = round(time.time() - t0, 1)
    os.makedirs(T.결과폴더, exist_ok=True)
    json.dump(res, open(경로, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("빌드/결과/재기15.json")


if __name__ == "__main__":
    main()
