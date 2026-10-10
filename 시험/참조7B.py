#!/usr/bin/env python3
"""22a (2) — 7B 의 끝에서 끝: 글 엔진(호스트/시험_7B.gl)이 낸 모든 행 로짓(채팅 질문 셋 — 프롬프트 + 생성 16 토큰의 토큰열 S, 행마다)을
CPU 참조(정수 계약의 Qwen2 앞으로 — 계약/정수계약.py, 행렬곱은 행렬곱블라스)와 비트까지 견준다. 다른 칸이 0 이어야 한다.

  python -I 시험/참조7B.py <7B gguf> <글 도구의 출력폴더> <출력.json> [--자체시험만]

먼저 빠른 판(행렬곱블라스)이 정수계약.행렬곱(자리수=2)과 비트까지 같은지 무작위 값과 7B 층 0 의 실제 가중치 조각으로 본다(문서/22단계.md 에
미리 적은 대로). 앞으로는 층마다 가중치를 한 번 풀어 세 경우의 행을 함께 행렬곱하고, RoPE · 어텐션은 경우마다(위치 0 부터).
"""
import json
import os
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, ".."))
for _d in ("엔진", "계약"):
    sys.path.insert(0, os.path.join(ROOT, _d))
import gguf읽기 as GR       # noqa: E402
import 정수계약 as C        # noqa: E402

f32 = np.float32


def q8(g, name):
    """GGUF Q8_0 텐서 → (q [N][K] int8, d [N][K/32] 짧은실수) — GGUF 의 배치 그대로."""
    t, dims, raw = g.원(name)
    assert t == GR.Q8_0, name
    K, N = dims
    bl = np.asarray(raw).reshape(N, K // 32, 34)
    d = np.ascontiguousarray(bl[:, :, :2]).view(np.float16).reshape(N, K // 32).astype(f32)
    q = np.ascontiguousarray(bl[:, :, 2:]).view(np.int8).reshape(N, K)
    return q, d


def 다른칸(a, b):
    a, b = np.asarray(a, f32), np.asarray(b, f32)
    assert a.shape == b.shape, (a.shape, b.shape)
    return int(np.count_nonzero(a.view(np.int32) != b.view(np.int32)))


def 자체시험(g):
    """행렬곱블라스 == 행렬곱(자리수=2)."""
    r = np.random.default_rng(7)
    결과 = []
    for M, K, N in ((5, 256, 96), (37, 1024, 200), (3, 3584, 64)):
        x = (r.standard_normal((M, K)) * 10.0 ** r.uniform(-3, 3, (M, 1))).astype(f32)
        q = r.integers(-128, 128, (N, K), dtype=np.int64).astype(np.int8)
        d = (r.standard_normal((N, K // 32)) * 0.01).astype(np.float16).astype(f32)
        b = r.standard_normal(N).astype(f32)
        a = C.행렬곱블라스(x, q, d, b)
        c = C.행렬곱(x, q.T.astype(np.int64), d.T, b, 자리수=2)
        결과.append({"꼴": f"무작위 M {M} · K {K} · N {N}", "다른 칸": 다른칸(a, c)})
    for 이름, K in (("blk.0.ffn_gate.weight", 3584), ("blk.0.ffn_down.weight", 18944)):
        q, d = q8(g, 이름)
        q, d = q[:96], d[:96]
        x = (r.standard_normal((6, K)) * 0.5).astype(f32)
        a = C.행렬곱블라스(x, q, d, np.zeros(96, f32))
        c = C.행렬곱(x, q.T.astype(np.int64), np.ascontiguousarray(d.T), np.zeros(96, f32), 자리수=2)
        결과.append({"꼴": f"7B {이름} 열 96 · K {K} · 행 6", "다른 칸": 다른칸(a, c)})
    for x in 결과:
        print("자체시험", x, flush=True)
    return 결과


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    gguf, 폴더, 출력 = sys.argv[1:4]
    g = GR.GGUF(gguf)
    m = g.meta
    NL, NH, NKV = m["qwen2.block_count"], m["qwen2.attention.head_count"], m["qwen2.attention.head_count_kv"]
    eps = float(m["qwen2.attention.layer_norm_rms_epsilon"])
    θ = float(m["qwen2.rope.freq_base"])
    결과 = {"자체시험": 자체시험(g)}
    if "--자체시험만" in sys.argv:
        json.dump(결과, open(출력, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        return
    # 경우들 — 글 도구가 쓴 토큰열 S 와 로짓
    경우 = []
    i = 0
    while os.path.exists(os.path.join(폴더, f"경우{i}_토큰.bin")):
        S = np.fromfile(os.path.join(폴더, f"경우{i}_토큰.bin"), np.int64)
        경우.append(S)
        i += 1
    print("경우", [len(S) for S in 경우], flush=True)
    t0 = time.time()
    eq, ed = q8(g, "token_embd.weight")
    D = eq.shape[1]
    HD = D // NH
    G_ = NH // NKV
    x = np.concatenate([(eq[S].astype(f32) * np.repeat(ed[S], 32, axis=1)).astype(f32) for S in 경우], 0)
    del eq, ed
    시작 = np.cumsum([0] + [len(S) for S in 경우])
    cos, sin = C.rope표(max(64, int(max(len(S) for S in 경우))), θ, hd=HD)
    for l in range(NL):
        tl = time.time()
        p = f"blk.{l}."
        h = C.rms정규화(x, g.풀기(p + "attn_norm.weight"), eps)
        qs, ds = zip(*(q8(g, p + f"attn_{a}.weight") for a in ("q", "k", "v")))
        bias = np.concatenate([g.풀기(p + f"attn_{a}.bias") for a in ("q", "k", "v")])
        qkv = C.행렬곱블라스(h, np.concatenate(qs), np.concatenate(ds), bias)
        ys = []
        for s, S in enumerate(경우):
            n = len(S)
            r = qkv[시작[s]:시작[s + 1]]
            위치 = np.arange(n)
            qh = [C.rope(r[:, HD * a:HD * a + HD], cos, sin, 위치) for a in range(NH)]
            kh = [C.rope(r[:, D + HD * a:D + HD * a + HD], cos, sin, 위치) for a in range(NKV)]
            vh = [np.ascontiguousarray(r[:, D + NKV * HD + HD * a:D + NKV * HD + HD * a + HD]) for a in range(NKV)]
            ys.append(np.concatenate([C.어텐션(qh[a], kh[a // G_], vh[a // G_]) for a in range(NH)], 1))
        y = np.concatenate(ys, 0)
        wo, do = q8(g, p + "attn_output.weight")
        x = (x + C.행렬곱블라스(y, wo, do, np.zeros(D, f32))).astype(f32)
        h = C.rms정규화(x, g.풀기(p + "ffn_norm.weight"), eps)
        wg, dg = q8(g, p + "ffn_gate.weight")
        wu, du = q8(g, p + "ffn_up.weight")
        F = wg.shape[0]
        gg = C.행렬곱블라스(h, wg, dg, np.zeros(F, f32))
        uu = C.행렬곱블라스(h, wu, du, np.zeros(F, f32))
        f = C.swiglu(gg, uu)
        wd, dd = q8(g, p + "ffn_down.weight")
        x = (x + C.행렬곱블라스(f, wd, dd, np.zeros(D, f32))).astype(f32)
        print(f"층 {l}: {time.time() - tl:.1f} 초", flush=True)
    h = C.rms정규화(x, g.풀기("output_norm.weight"), eps)
    wh, dh = q8(g, "output.weight")
    로짓 = C.행렬곱블라스(h, wh, dh, np.zeros(wh.shape[0], f32))
    V = wh.shape[0]
    결과["경우"] = []
    for s, S in enumerate(경우):
        A = np.fromfile(os.path.join(폴더, f"경우{s}_로짓.bin"), f32).reshape(len(S), V)
        R = 로짓[시작[s]:시작[s + 1]]
        한 = {"토큰": len(S), "다른 칸": 다른칸(A, R), "칸": int(A.size), "행마다 다른 칸": [다른칸(A[k], R[k]) for k in range(len(S))]}
        결과["경우"].append(한)
        print(f"경우 {s}: 행 {len(S)} — 다른 칸 {한['다른 칸']} / {한['칸']}", flush=True)
    결과["CPU 참조 초"] = round(time.time() - t0, 1)
    결과["모두 0"] = all(c["다른 칸"] == 0 for c in 결과["경우"]) and all(x["다른 칸"] == 0 for x in 결과["자체시험"])
    print("모두 0:", 결과["모두 0"], flush=True)
    json.dump(결과, open(출력, "w", encoding="utf-8"), ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
