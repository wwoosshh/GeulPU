#!/usr/bin/env python3
"""37c · 37d 의 모음 — Qwen3-8B 의 파일 둘(Q8_0 · Q4_K_M)마다 글(호스트/재기_7B.gl 의 출력 셋)과 llama-bench(프롬프트 · 생성 표 셋)의
세 번의 가운데 값, 비 r = 글 / llama.cpp, 미리 적은 칸(문서/37단계.md — 37c 는 생성 여섯 칸 모두 r ≤ 1.05, 37d 는 프롬프트의 기록).
판정이 아닌 기록: 바닥(토큰당 읽는 바이트 / 504 GB/s — 층의 가중치와 출력 텐서의 파일 바이트 + 문맥만큼의 KV) 대비 배수, 머리 정규화 판의
시간(호스트/재기_7B커널.gl 의 q·k정규화 — 있으면).

  python -I 재기/모음37.py <결과 폴더(문서/결과/37단계)> <출력.json> <8B 모델 폴더>
"""
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "엔진"))
from 모음23 import 가운데, 글읽기, 라마읽기, 칸       # noqa: E402
import gguf읽기 as GR                               # noqa: E402

파일들 = {"q8_0": "Qwen3-8B-Q8_0.gguf", "q4_k_m": "Qwen3-8B-Q4_K_M.gguf"}
생성칸 = ("생성 짧음", "생성 2048", "생성 8192")
프롬프트칸 = ("프롬프트 2048", "프롬프트 8192")
문맥 = {"생성 짧음": 0, "생성 2048": 2048, "생성 8192": 8192}


def 토큰당바이트(gguf):
    """생성 토큰 하나가 읽는 가중치 바이트(층의 텐서 모두 + 출력 — 낱말표는 행 하나라 뺀다)와 위치 하나의 KV 바이트(계약 — 자리 둘 + 지수)."""
    g = GR.GGUF(gguf)
    m = g.meta
    a = m["general.architecture"] + "."
    NL, NKV = m[a + "block_count"], m[a + "attention.head_count_kv"]
    hd = int(m.get(a + "attention.key_length") or m[a + "embedding_length"] // m[a + "attention.head_count"])
    합 = 0
    머리 = "output.weight" if "output.weight" in g.tensors else "token_embd.weight"
    for 이름 in g.tensors:
        if 이름.startswith("blk.") or 이름 == 머리:
            합 += len(g.원(이름)[2])
    return 합, NL * 2 * (NKV * hd * 2 + NKV * (hd // 32))


def 커널읽기(경로):
    """재기_7B커널 의 출력 — 줄마다 '<이름> 합 <ms> <종류> <ms> …' 에서 q·k정규화 의 ms."""
    out = {}
    if not os.path.exists(경로):
        return out
    for 줄 in open(경로, encoding="utf-8"):
        m = re.match(r"(.+?) 합 ([\d.]+)(.*)$", 줄.strip())
        if not m:
            continue
        칸들 = m.group(3).split()
        값 = dict(zip(칸들[0::2], 칸들[1::2]))
        out[m.group(1)] = {"합 ms": float(m.group(2)), "q·k정규화 ms": float(값.get("q·k정규화", "0"))}
    return out


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    폴더, 출력, 모델폴더 = sys.argv[1:4]
    결과 = {"판정": {}, "기록": {}}
    for f, 파일 in 파일들.items():
        글 = [글읽기(os.path.join(폴더, f"37c_글_{f}_{i}.txt")) for i in (1, 2, 3)]
        라마 = []
        for i in (1, 2, 3):
            d = 라마읽기(os.path.join(폴더, f"37c_라마_{f}_프롬프트_{i}.txt"))
            d.update(라마읽기(os.path.join(폴더, f"37c_라마_{f}_생성_{i}.txt")))
            라마.append(d)
        가중, KV위치 = 토큰당바이트(os.path.join(모델폴더, 파일))
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
            결과["판정" if 이름 in 생성칸 else "기록"][f"{f} {이름}"] = 한
            print(f"{f} {이름}: 글 {g:.3f} ms · llama.cpp {l:.3f} ms · r {r:.4f} — {칸(이름, r)}", flush=True)
        결과["기록"][f"{f} 프롬프트 128 (글 ms)"] = 가운데([x["프롬프트 128"] for x in 글])
        k = 커널읽기(os.path.join(폴더, f"37기록_글_커널마다_{f}.txt"))
        if k:
            결과["기록"][f"{f} 커널마다(q·k 정규화)"] = k
    결과["37c 통과(여섯 칸 모두 r ≤ 1.05)"] = all(결과["판정"][f"{f} {이름}"]["r"] <= 1.05 for f in 파일들 for 이름 in 생성칸)
    print("37c 통과:", 결과["37c 통과(여섯 칸 모두 r ≤ 1.05)"], flush=True)
    json.dump(결과, open(출력, "w", encoding="utf-8"), ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
