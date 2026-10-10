#!/usr/bin/env python3
"""21a — 7B 층 0 의 네 가중치(qkv · o · gate·up · down)로 글 정수 타일 판(끝손질 없음)이 낸 출력을 CPU 참조(계약/정수계약.행렬곱,
자리 둘)와 비트까지 견준다. 글 쪽(호스트/재기_7B행렬곱.gl 의 '비트')이 판 11 개를 판 0 과 견주고 판 0 의 출력 · 활성값을 파일로 낸다.

  python -I 시험/행렬곱21.py <7B gguf> <글 도구의 폴더> <출력.json>
"""
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, ".."))
sys.path.insert(0, os.path.join(ROOT, "계약"))
sys.path.insert(0, os.path.join(ROOT, "재기"))
import 정수계약 as C          # noqa: E402
import 라마행렬곱21 as R      # noqa: E402 — GGUF 머리만 읽는 함수를 함께 쓴다


def q8(raw, dims):
    """Q8_0 날 바이트 → (q [N][K] int8, d [N][K/32] 짧은실수)."""
    K, N = dims
    bl = np.asarray(raw).reshape(N, K // 32, 34)
    d = np.ascontiguousarray(bl[:, :, :2]).view(np.float16).reshape(N, K // 32).astype(np.float32)
    q = np.ascontiguousarray(bl[:, :, 2:]).view(np.int8).reshape(N, K)
    return q, d


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    path, 폴더, 출력 = sys.argv[1:4]
    이름 = ["attn_q", "attn_k", "attn_v", "attn_output", "ffn_gate", "ffn_up", "ffn_down"]
    _, ts = R.gguf텐서(path, [f"blk.0.{n}.weight" for n in 이름])
    w = {n: q8(ts[f"blk.0.{n}.weight"][2], ts[f"blk.0.{n}.weight"][1]) for n in 이름}
    F = w["ffn_gate"][0].shape[0]
    # 엔진의 열 차례: qkv = [q | k | v], gu = 출력 32 열마다 [gate 32 | up 32] 로 번갈아
    qkv = (np.concatenate([w[n][0] for n in ("attn_q", "attn_k", "attn_v")]),
           np.concatenate([w[n][1] for n in ("attn_q", "attn_k", "attn_v")]))
    순 = np.empty(2 * F, np.int64)
    for j in range(F // 32):
        순[64 * j:64 * j + 32] = np.arange(32 * j, 32 * j + 32)
        순[64 * j + 32:64 * j + 64] = F + np.arange(32 * j, 32 * j + 32)
    gq = np.concatenate([w["ffn_gate"][0], w["ffn_up"][0]])[순]
    gd = np.concatenate([w["ffn_gate"][1], w["ffn_up"][1]])[순]
    가중 = {"qkv": qkv, "o": w["attn_output"], "gu": (gq, gd), "down": w["ffn_down"]}
    결과 = {"글 도구 요약": open(os.path.join(폴더, "요약.txt"), encoding="utf-8").read(), "가중치": {}}
    for 이름w, (q, d) in 가중.items():
        N, K = q.shape
        x = np.fromfile(os.path.join(폴더, "활성F.bin" if 이름w == "down" else "활성D.bin"), np.float32).reshape(64, K)
        y = np.fromfile(os.path.join(폴더, f"출력_{이름w}.bin"), np.float32).reshape(64, N)
        ref = C.행렬곱(x, q.T, np.ascontiguousarray(d.T), np.zeros(N, np.float32), 자리수=2)
        다른 = int((ref.view(np.uint32) != y.view(np.uint32)).sum())
        결과["가중치"][이름w] = {"K": K, "N": N, "다른 칸": 다른, "칸": int(y.size)}
        print(f"{이름w}: K {K} · N {N} — CPU 참조와 다른 칸 {다른} / {y.size}", flush=True)
    json.dump(결과, open(출력, "w", encoding="utf-8"), ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
