#!/usr/bin/env python3
"""22단계 — 글 시험 도구(호스트/시험_7B.gl)의 입력: 채팅 질문 셋의 채팅 틀(잡기시작 0 — 모든 행 로짓을 CPU 참조와 대조)과
문장 1 을 되풀이한 2100 토큰(잡기시작 2000 — 묶음 경계 1024 · 2048 을 넘는 길끼리의 대조). 걸음 17 (생성 16 걸음).
토크나이저는 7B GGUF 의 것(엔진/토크나이저.py).

  python -I 시험/입력7B.py <7B gguf> <입력.bin> [--최대길이 4096] [--로짓행 128]
  python -I 시험/입력7B.py <7B gguf> <재기입력.bin> --재기        (22d — 호스트/재기_7B.gl 의 입력)
  python -I 시험/입력7B.py <gguf> <입력.bin> --무작위 24          (24단계 — 합성 모델: 같은 길이의 정한 무작위 토큰열)
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, ".."))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, "엔진"))
import 토크나이저 as TK      # noqa: E402

질문들 = ["What is the capital of France? Answer in one word.", "대한민국의 수도는 어디야? 한 단어로 답해.",
         "Write a short poem about the sea."]
긴글 = ("In a shocking finding, scientists discovered a herd of unicorns living in a remote, previously unexplored valley "
       "in the Andes Mountains. Even more surprising to the researchers was the fact that the unicorns spoke perfect English.")


def 재기입력(tk, 출력):
    """22d 의 입력(호스트/재기_7B.gl) — 18e 와 같은 꼴: 채팅 질문(셋째)의 채팅 틀, 문장 1 의 되풀이 8192."""
    채팅 = tk.나누기(TK.채팅틀([{"role": "user", "content": 질문들[2]}]))
    긴 = (tk.나누기(긴글) * 400)[:8192]
    with open(출력, "wb") as f:
        w = lambda v: f.write(int(v).to_bytes(8, "little", signed=True))
        for ids in (채팅, 긴):
            w(len(ids))
            for t in ids:
                w(t)
    print("재기 입력: 채팅", len(채팅), "· 긴 글", len(긴))


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    gguf, 출력 = sys.argv[1:3]
    최대길이 = int(sys.argv[sys.argv.index("--최대길이") + 1]) if "--최대길이" in sys.argv else 4096
    로짓행 = int(sys.argv[sys.argv.index("--로짓행") + 1]) if "--로짓행" in sys.argv else 128
    tk = TK.Qwen토크나이저(gguf=gguf)
    if "--재기" in sys.argv:
        재기입력(tk, 출력)
        return
    경우들 = [(tk.나누기(TK.채팅틀([{"role": "user", "content": q}])), 17, 0) for q in 질문들]
    경우들.append(((tk.나누기(긴글) * 400)[:2100], 17, 2000))
    if "--무작위" in sys.argv:                 # 24단계 — 합성 모델: 정한 무작위 토큰열 셋(길이는 채팅 질문과 같게)과 2100 (보통 낱말 0 … 151642)
        import numpy as np
        r = np.random.default_rng(int(sys.argv[sys.argv.index("--무작위") + 1]))
        경우들 = [([int(t) for t in r.integers(0, 151643, len(ids))], n, 잡기) for ids, n, 잡기 in 경우들]
    with open(출력, "wb") as f:
        w = lambda v: f.write(int(v).to_bytes(8, "little", signed=True))
        w(최대길이), w(로짓행), w(len(경우들))
        for ids, n, 잡기 in 경우들:
            w(len(ids)), w(n), w(잡기)
            for t in ids:
                w(t)
    print("경우", [(len(ids), n, 잡기) for ids, n, 잡기 in 경우들])


if __name__ == "__main__":
    main()
