#!/usr/bin/env python3
"""26c · 26d 의 모음 — k-양자화 파일 셋(7B Q4_K_M · Q5_K_M · Q6_K)마다 글(호스트/재기_7B.gl 의 출력 셋)과 llama-bench(프롬프트 · 생성 표 셋)의
세 번의 가운데 값, 비 r = 글 / llama.cpp, 미리 적은 칸(문서/26단계.md). 판정이 아닌 기록: 바닥(토큰당 읽는 바이트 / 504 GB/s — 층의 가중치와
출력 텐서의 파일 바이트 + 문맥만큼의 KV) 대비 배수, 14B Q4_K_M(있으면)의 r.

  python -I 재기/모음26.py <결과 폴더(문서/결과/26단계)> <출력.json> <7B 모델 폴더> [14B Q4_K_M gguf]
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "엔진"))
from 모음23 import 가운데, 글읽기, 라마읽기, 칸       # noqa: E402
import gguf읽기 as GR                               # noqa: E402

형식들 = ("q4_k_m", "q5_k_m", "q6_k")
생성칸 = ("생성 짧음", "생성 2048", "생성 8192")
프롬프트칸 = ("프롬프트 2048", "프롬프트 8192")
문맥 = {"생성 짧음": 0, "생성 2048": 2048, "생성 8192": 8192}


def 토큰당바이트(gguf):
    """생성 토큰 하나가 읽는 가중치 바이트(층의 텐서 모두 + 출력 — 낱말표는 행 하나라 뺀다)와 위치 하나의 KV 바이트(계약 — 자리 둘 + 지수)."""
    g = GR.GGUF(gguf)
    m = g.meta
    NL, NKV = m["qwen2.block_count"], m["qwen2.attention.head_count_kv"]
    hd = m["qwen2.embedding_length"] // m["qwen2.attention.head_count"]
    합 = 0
    머리 = "output.weight" if "output.weight" in g.tensors else "token_embd.weight"
    for 이름 in g.tensors:
        if 이름.startswith("blk.") or 이름 == 머리:
            합 += len(g.원(이름)[2])
    return 합, NL * 2 * (NKV * hd * 2 + NKV * (hd // 32))


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    폴더, 출력, 모델폴더 = sys.argv[1:4]
    결과 = {"판정": {}, "기록": {}}
    for f in 형식들:
        글 = [글읽기(os.path.join(폴더, f"26c_글_{f}_{i}.txt")) for i in (1, 2, 3)]
        라마 = []
        for i in (1, 2, 3):
            d = 라마읽기(os.path.join(폴더, f"26c_라마_{f}_프롬프트_{i}.txt"))
            d.update(라마읽기(os.path.join(폴더, f"26c_라마_{f}_생성_{i}.txt")))
            라마.append(d)
        가중, KV위치 = 토큰당바이트(os.path.join(모델폴더, f"qwen2.5-7b-instruct-{f}-req.gguf"))
        결과[f] = {"글 (ms)": 글, "llama.cpp (ms)": 라마, "토큰당 가중치 바이트": 가중}
        for 이름 in 생성칸 + 프롬프트칸:
            g = 가운데([x[이름] for x in 글])
            l = 가운데([x[이름] for x in 라마])
            r = g / l
            한 = {"글 ms": round(g, 4), "llama.cpp ms": round(l, 4), "r": round(r, 4), "칸": 칸(이름, r)}
            if 이름 in 생성칸:
                바닥 = (가중 + 문맥[이름] * KV위치) / 504e9 * 1000.0
                한["바닥 ms (기록)"] = round(바닥, 4)
                한["글 / 바닥 (기록)"] = round(g / 바닥, 4)
                한["llama.cpp / 바닥 (기록)"] = round(l / 바닥, 4)
            결과["판정"][f"{f} {이름}"] = 한
            print(f"{f} {이름}: 글 {g:.3f} ms · llama.cpp {l:.3f} ms · r {r:.4f} — {칸(이름, r)}", flush=True)
        결과["기록"][f"{f} 프롬프트 128 (글 ms)"] = 가운데([x["프롬프트 128"] for x in 글])
    결과["26c 통과(아홉 칸 모두 r ≤ 1.05)"] = all(결과["판정"][f"{f} {이름}"]["r"] <= 1.05 for f in 형식들 for 이름 in 생성칸)
    print("26c 통과:", 결과["26c 통과(아홉 칸 모두 r ≤ 1.05)"], flush=True)
    if len(sys.argv) > 4 and os.path.exists(os.path.join(폴더, "26기록_글_14b-q4_k_m.txt")):
        g = 글읽기(os.path.join(폴더, "26기록_글_14b-q4_k_m.txt"))
        l = 라마읽기(os.path.join(폴더, "26기록_라마_14b-q4_k_m_프롬프트.txt"))
        l.update(라마읽기(os.path.join(폴더, "26기록_라마_14b-q4_k_m_생성.txt")))
        한 = {이름: {"글 ms": round(g[이름], 4), "llama.cpp ms": round(l[이름], 4), "r": round(g[이름] / l[이름], 4)}
             for 이름 in 생성칸 + 프롬프트칸 if 이름 in g and 이름 in l}
        결과["기록"]["14B Q4_K_M (한 번)"] = 한
        print("14B Q4_K_M:", {k: v["r"] for k, v in 한.items()}, flush=True)
    json.dump(결과, open(출력, "w", encoding="utf-8"), ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
