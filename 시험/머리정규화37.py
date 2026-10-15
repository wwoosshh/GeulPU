#!/usr/bin/env python3
"""37a (1) — 머리 정규화 판(모듈 qwen3… 의 머리정규화128 — 계약 4.6)을 CPU 참조(계약/정수계약.py 의 머리정규화)와 비트까지 견준다.
무게는 Qwen3 GGUF 의 층마다 실제 attn_q_norm · attn_k_norm(F32 128 칸), 입력 버qkv [행][QKV] 는 무작위 — 머리마다 크기를 넓게
(10^−25 … 10^17), 0 인 머리 · 칸 몇이 0 인 머리 · 비정규수 머리 · 2 의 거듭제곱을 섞는다. 판은 q · k 칸을 제자리에서 바꾸고 v 칸은
그대로 둬야 한다. 행 1 · 4 · 64 · 2048 × 모든 층의 무게. 다른 칸이 0 이어야 한다.

  python -I -X utf8 시험/머리정규화37.py <qwen3 모듈 .ptx (Vulkan 은 .spvs)> <qwen3 gguf> <출력.json>
환경 변수 GEULPU_VULKAN 이 있으면 그 Vulkan 장치에서(시험/시험장치.py).
"""
import ctypes
import json
import os
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, ".."))
for _d in ("엔진", "계약"):
    sys.path.insert(0, os.path.join(ROOT, _d))
sys.path.insert(0, HERE)
import 글gpt2 as G          # noqa: E402
import 시험장치               # noqa: E402
import gguf읽기 as GR       # noqa: E402
import 정수계약 as C        # noqa: E402

f32 = np.float32
u64, i64 = G.c_u64, G.c_i64
HD = 128


def 다른칸(a, b):
    a, b = np.asarray(a, f32), np.asarray(b, f32)
    assert a.shape == b.shape, (a.shape, b.shape)
    return int(np.count_nonzero(a.view(np.int32) != b.view(np.int32)))


def 입력(r, R, NH, NKV):
    """버qkv [R][QKV] — q · k 머리마다 크기를 따로, 튀는 머리를 섞고, v 는 보통 값."""
    H = NH + NKV
    x = (r.standard_normal((R, H, HD)) * 10.0 ** r.uniform(-25, 17, (R, H, 1))).astype(f32)
    m = r.random((R, H))
    x[m < 0.03] = 0                                                       # 0 인 머리
    x[(m >= 0.03) & (m < 0.06), ::5] = 0                                 # 칸 몇이 0
    s = (m >= 0.06) & (m < 0.09)
    x[s] = (r.standard_normal((int(s.sum()), HD)) * 2.0 ** -140).astype(f32)     # 비정규수
    p = (m >= 0.09) & (m < 0.12)
    x[p, :7] = (2.0 ** r.integers(-126, 60, (int(p.sum()), 7))).astype(f32)      # 2 의 거듭제곱
    v = r.standard_normal((R, NKV * HD)).astype(f32)
    return np.ascontiguousarray(np.concatenate([x.reshape(R, H * HD), v], 1))


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    모듈, gguf, 출력 = sys.argv[1:4]
    g = GR.GGUF(gguf)
    m = g.meta
    assert m["general.architecture"] == "qwen3", "Qwen3 GGUF 가 아니다"
    NL, NH, NKV = m["qwen3.block_count"], m["qwen3.attention.head_count"], m["qwen3.attention.head_count_kv"]
    eps = float(m["qwen3.attention.layer_norm_rms_epsilon"])
    A = NH * HD
    QKV = A + 2 * NKV * HD
    무게 = [(g.풀기(f"blk.{l}.attn_q_norm.weight"), g.풀기(f"blk.{l}.attn_k_norm.weight")) for l in range(NL)]
    del g
    dr = 시험장치.드라이버()
    mod = dr.모듈(open(모듈, "rb").read())
    fn = dr.함수(mod, "머리정규화128")
    한도 = 시험장치.한도넘음(dr, "머리정규화128")
    assert 한도 is None, 한도
    r = np.random.default_rng(37)
    Rmax = 2048
    p버 = dr.할당(Rmax * QKV * 4)
    pq, pk = dr.할당(HD * 4), dr.할당(HD * 4)
    결과 = {"모듈": os.path.basename(모듈), "모델": os.path.basename(gguf), "층": NL, "머리": NH, "KV머리": NKV, "eps": eps,
          "장치": os.environ.get("GEULPU_VULKAN") or "CUDA", "경우": []}
    t0 = time.time()
    for R in (1, 4, 64, 2048):
        다름q = 다름k = 다름v = 0
        for l in range(NL):
            X = 입력(r, R, NH, NKV)
            wq, wk = 무게[l]
            dr.올리기(p버, X)
            dr.올리기(pq, np.ascontiguousarray(wq, f32))
            dr.올리기(pk, np.ascontiguousarray(wk, f32))
            ps = [u64(p버), u64(pq), u64(pk), i64(R)]
            args = (ctypes.c_void_p * 4)(*[ctypes.cast(ctypes.byref(p), ctypes.c_void_p) for p in ps])
            rr = dr.cu.cuLaunchKernel(fn, (R * (NH + NKV) + 3) // 4, 1, 1, 128, 1, 1, 0, None, args, None)
            assert rr == 0, rr
            dr.맞추기()
            Y = np.zeros((R, QKV), f32)
            dr.내리기(p버, Y)
            다름q += 다른칸(Y[:, :A], C.머리정규화(X[:, :A], wq, eps))
            다름k += 다른칸(Y[:, A:A + NKV * HD], C.머리정규화(X[:, A:A + NKV * HD], wk, eps))
            다름v += 다른칸(Y[:, A + NKV * HD:], X[:, A + NKV * HD:])
        한 = {"행": R, "층": NL, "q 다른 칸": 다름q, "k 다른 칸": 다름k, "v 바뀐 칸": 다름v, "칸": int(R * QKV * NL)}
        결과["경우"].append(한)
        print(f"행 {R} × 층 {NL}: q 다른 칸 {다름q} · k 다른 칸 {다름k} · v 바뀐 칸 {다름v} ({time.time() - t0:.1f} 초)", flush=True)
    결과["모두 0"] = all(c["q 다른 칸"] == 0 and c["k 다른 칸"] == 0 and c["v 바뀐 칸"] == 0 for c in 결과["경우"])
    print("모두 0:", 결과["모두 0"], flush=True)
    json.dump(결과, open(출력, "w", encoding="utf-8"), ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
