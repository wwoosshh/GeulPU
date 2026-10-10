#!/usr/bin/env python3
"""22a (1) — 머리 128 의 새 커널(모듈 qwen2Q8_7b 의 RoPEKV정수로 · 정수어텐션묶음 · 정수묶음접기 · 정수묶음접기짧은)을 CPU 참조
(계약/정수계약.py — 머리 128 로 넓힌 계약)와 비트까지 견준다. 다른 칸이 0 이어야 한다.

  입력 (가) 무작위 q · k · v — 행 2100 (묶음 셋: 위치 1024 · 2048 을 넘는다), 머리마다 크기가 다르고 튀는 값을 섞는다.
       (나) 7B 층 0 의 실제 q · k · v — 채팅 질문 셋의 프롬프트(CPU 참조의 임베딩 · RMS · 행렬곱으로).
  덩이 — 한 번에(덩이 하나) · 나눠서(묶음 경계를 넘는 덩이) · 한 행씩(생성 길: 같은 묶음 판을 행 1 로). 덩이마다 RoPEKV정수로 →
  정수어텐션묶음 → 정수묶음접기(o 의 자리 둘 · 정보) · 정수묶음접기짧은(짧은실수 O/L) 을 띄우고, 끝에 KV 캐시(바이트 · 지수)를 내린다.

  python -I 시험/머리128.py <qwen2Q8_7b.ptx> <7B gguf> <출력.json> [--빠르게]
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
import 글gpt2 as G          # noqa: E402
import gguf읽기 as GR       # noqa: E402
import 정수계약 as C        # noqa: E402

f32 = np.float32
u64, i64 = G.c_u64, G.c_i64
D, NH, NKV, HD = 3584, 28, 4, 128
QKV = D + 2 * NKV * HD                     # 4608
KB = D // 32                               # 112
SH = 4 * HD + 4                            # 묶음 상태 하나의 칸 (M, L, 빈 둘, O 128)
질문들 = ["What is the capital of France? Answer in one word.", "대한민국의 수도는 어디야? 한 단어로 답해.",
         "Write a short poem about the sea."]


class 글커널:
    def __init__(self, ptx):
        self.dr = G.드라이버()
        mod = self.dr.모듈(open(ptx, "rb").read())
        self.f = {n: self.dr.함수(mod, n) for n in ("RoPEKV정수로", "정수어텐션묶음", "정수묶음접기", "정수묶음접기짧은")}
        self.dr.cu.cuFuncGetAttribute.argtypes = [ctypes.POINTER(ctypes.c_int), ctypes.c_int, ctypes.c_void_p]

    def 속성(self):
        """커널마다 레지스터 · 넘친 지역 메모리 · 공유 메모리(바이트)."""
        out = {}
        for n, fn in self.f.items():
            v = []
            for a in (4, 3, 1):                       # NUM_REGS · LOCAL_SIZE_BYTES · SHARED_SIZE_BYTES
                x = ctypes.c_int()
                self.dr.확인(self.dr.cu.cuFuncGetAttribute(ctypes.byref(x), a, fn))
                v.append(x.value)
            out[n] = {"레지스터": v[0], "지역(넘침) 바이트": v[1], "공유 바이트": v[2]}
        return out

    def 띄우기(self, 이름, grid, block, params):
        ps = [u64(p) if 참조 else i64(p) for 참조, p in params]
        args = (ctypes.c_void_p * len(ps))(*[ctypes.cast(ctypes.byref(p), ctypes.c_void_p) for p in ps])
        r = self.dr.cu.cuLaunchKernel(self.f[이름], grid[0], grid[1], 1, block, 1, 1, 0, None, args, None)
        assert r == 0, (이름, r)

    def 돌리기(self, X, 덩이들, 최대길이, cos, sin):
        """X [n][QKV] 짧은실수를 덩이들 [(위치시작, 행)] 차례로 — 행마다의 출력과 끝의 캐시."""
        dr = self.dr
        n = X.shape[0]
        Mmax = max(m for _, m in 덩이들)
        폭max = (Mmax + 63) // 64 * 64
        묶음수 = (최대길이 + 1023) // 1024
        p입력 = dr.할당(Mmax * QKV * 4)
        p자q, p정q = dr.할당(2 * Mmax * D), dr.할당(KB * 폭max * 4)
        p키, p값 = dr.할당(NKV * 2 * 최대길이 * HD), dr.할당(NKV * 최대길이 * 2 * HD)
        p키지, p값지 = dr.할당(NKV * 최대길이 * 4), dr.할당(NKV * 최대길이 * 4)
        p묶 = dr.할당(Mmax * NH * 묶음수 * SH * 4)
        p자, p정 = dr.할당(2 * Mmax * D), dr.할당(KB * 폭max * 4)
        p출 = dr.할당(Mmax * D * 4)
        p코, p사 = dr.할당(최대길이 * 64 * 4), dr.할당(최대길이 * 64 * 4)
        dr.올리기(p코, np.ascontiguousarray(cos, f32))
        dr.올리기(p사, np.ascontiguousarray(sin, f32))
        out = {"q자리": np.zeros((2, n, D), np.int8), "q정보": np.zeros((n, KB), np.int32), "o자리": np.zeros((2, n, D), np.int8),
               "o정보": np.zeros((n, KB), np.int32), "o짧은": np.zeros((n, D), f32)}
        KV = [(1, p키), (1, p값), (1, p키지), (1, p값지)]
        for s, m in 덩이들:
            폭 = (m + 63) // 64 * 64
            dr.올리기(p입력, np.ascontiguousarray(X[s:s + m], f32))
            self.띄우기("RoPEKV정수로", ((QKV // 32 + 31) // 32, m), 256,
                     [(1, p입력), (1, p자q), (1, p정q)] + KV + [(1, p코), (1, p사), (0, m), (0, m), (0, s), (0, 최대길이)])
            묶 = (s + m - 1) // 1024 + 1
            self.띄우기("정수어텐션묶음", ((m + 63) // 64 * NH * 묶, 1), 128,
                     [(1, p자q), (1, p정q)] + KV + [(1, p묶), (0, m), (0, m), (0, s), (0, 최대길이)])
            self.띄우기("정수묶음접기", (NH, m), 128, [(1, p묶), (1, p정), (1, p자), (0, m), (0, m), (0, s), (0, 최대길이)])
            self.띄우기("정수묶음접기짧은", (NH, m), 128, [(1, p묶), (1, p출), (0, m), (0, m), (0, s), (0, 최대길이)])
            dr.맞추기()
            out["q자리"][:, s:s + m] = dr.내리기(p자q, np.empty((2, m, D), np.int8))
            out["q정보"][s:s + m] = dr.내리기(p정q, np.empty((KB, 폭), np.int32))[:, :m].T
            out["o자리"][:, s:s + m] = dr.내리기(p자, np.empty((2, m, D), np.int8))
            out["o정보"][s:s + m] = dr.내리기(p정, np.empty((KB, 폭), np.int32))[:, :m].T
            out["o짧은"][s:s + m] = dr.내리기(p출, np.empty((m, D), f32))
        out["키"] = dr.내리기(p키, np.empty((NKV, 2, 최대길이, HD), np.int8))
        out["값"] = dr.내리기(p값, np.empty((NKV, 최대길이 // 32, 2, HD, 32), np.int8))
        out["키지수"] = dr.내리기(p키지, np.empty((NKV, 최대길이, 4), np.uint8))
        out["값지수"] = dr.내리기(p값지, np.empty((NKV, 최대길이, 4), np.uint8))
        dr.맞추기()
        for p in dr.할당들:                          # 메모리만 돌려준다(모듈은 둔다 — 다음 경우가 쓴다)
            dr.확인(dr.cu.cuMemFree_v2(u64(p)))
        dr.할당들 = []
        return out


def 자리바이트(x):
    """x [n][너비] → (자리 바이트 [2][n][너비] — 블록마다 낱말 차례, 정보 M_0 [n][블록]) — 정수로 · RoPEKV · 묶음 접기의 출력 배치."""
    Dg, E = C.자리로(np.asarray(x, f32), 2)
    n, w = Dg.shape[1], Dg.shape[2]
    바이트 = C.낱말차례(Dg.reshape(2, n, w // 32, 32)).reshape(2, n, w).astype(np.int8)
    M0 = (((137 + E) << 23) + 4194304).astype(np.int64).astype(np.int32)
    return 바이트, M0


def 참조(X, 최대길이, cos, sin):
    n = X.shape[0]
    위치 = np.arange(n)
    q, k, v = X[:, :D], X[:, D:D + NKV * HD], X[:, D + NKV * HD:]
    qr = np.concatenate([C.rope(q[:, HD * a:HD * a + HD], cos, sin, 위치) for a in range(NH)], 1)
    kr = [C.rope(k[:, HD * g:HD * g + HD], cos, sin, 위치) for g in range(NKV)]
    vv = [np.ascontiguousarray(v[:, HD * g:HD * g + HD]) for g in range(NKV)]
    out = {}
    out["q자리"], out["q정보"] = 자리바이트(qr)
    키들 = [C.키캐시(kr[g], 최대길이) for g in range(NKV)]
    값들 = [C.값캐시(vv[g], 최대길이) for g in range(NKV)]
    out["키"] = np.stack([a for a, _ in 키들])
    out["키지수"] = np.stack([b for _, b in 키들])
    out["값"] = np.stack([a for a, _ in 값들])
    out["값지수"] = np.stack([b for _, b in 값들]).astype(np.uint8)
    G_ = NH // NKV
    y = np.concatenate([C.어텐션(qr[:, HD * a:HD * a + HD], kr[a // G_], vv[a // G_]) for a in range(NH)], 1)
    out["o짧은"] = y
    out["o자리"], out["o정보"] = 자리바이트(y)
    return out


def 견주기(글, 참):
    결과 = {}
    for 이름 in ("q자리", "q정보", "키", "키지수", "값", "값지수", "o자리", "o정보", "o짧은"):
        a, b = np.asarray(글[이름]), np.asarray(참[이름])
        if a.dtype == f32:
            a, b = a.view(np.int32), b.astype(f32).view(np.int32)
        결과[이름] = int(np.count_nonzero(a.reshape(-1) != b.reshape(-1).astype(a.dtype)))
    return 결과


def 무작위(n, 씨):
    """머리마다 크기가 다르고(10^±1.5) 몇 칸은 튀는(×30) q · k · v."""
    r = np.random.default_rng(씨)
    X = r.standard_normal((n, QKV)).astype(f32)
    크기 = (10.0 ** r.uniform(-1.5, 1.5, QKV // HD)).astype(f32)
    X *= np.repeat(크기, HD)[None, :]
    튐 = r.random((n, QKV)) < 0.002
    X[튐] *= f32(30.0)
    return X.astype(f32)


def 층0qkv(gguf, ids):
    """7B 층 0 의 q · k · v (bias 포함, RoPE 앞) — CPU 참조의 임베딩 · RMS · 행렬곱빠른(계약 그대로)."""
    g = GR.GGUF(gguf)

    def q8(name):
        t, dims, raw = g.원(name)
        K, N = dims
        bl = np.asarray(raw).reshape(N, K // 32, 34)
        d = np.ascontiguousarray(bl[:, :, :2]).view(np.float16).reshape(N, K // 32).astype(f32)
        q = np.ascontiguousarray(bl[:, :, 2:]).view(np.int8).reshape(N, K)
        return q, d
    eq, ed = q8("token_embd.weight")
    x = (eq[ids].astype(f32) * np.repeat(ed[ids], 32, axis=1)).astype(f32)
    h = C.rms정규화(x, g.풀기("blk.0.attn_norm.weight"), 1e-6)
    out = []
    for a in ("q", "k", "v"):
        q, d = q8(f"blk.0.attn_{a}.weight")
        out.append(C.행렬곱빠른(h, q.T, np.ascontiguousarray(d.T), g.풀기(f"blk.0.attn_{a}.bias")))
    return np.concatenate(out, 1).astype(f32)


def 채팅토큰(질문):
    import 토크나이저 as TK
    tk = TK.Qwen토크나이저(os.path.join(ROOT, "모델", "qwen2.5-0.5b-instruct"))
    return tk.나누기(TK.채팅틀([{"role": "user", "content": 질문}]))


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    ptx, gguf, 출력 = sys.argv[1:4]
    빠르게 = "--빠르게" in sys.argv
    k = 글커널(ptx)
    결과 = {"커널 속성": k.속성(), "경우": []}
    print(json.dumps(결과["커널 속성"], ensure_ascii=False), flush=True)
    경우들 = []
    n = 300 if 빠르게 else 2100
    X = 무작위(n, 22)
    if 빠르게:
        경우들.append(("무작위 300", X, 1024, {"한 번에": [(0, n)], "나눠서": [(0, 100), (100, 150), (250, 50)],
                                          "한 행씩": [(0, 260)] + [(s, 1) for s in range(260, n)]}))
    else:
        경우들.append(("무작위 2100", X, 3072, {"한 번에": [(0, n)], "나눠서": [(0, 700), (700, 700), (1400, 700)],
                                           "한 행씩": [(0, 1024), (1024, 1000)] + [(s, 1) for s in range(2024, n)]}))
        for qi, 질문 in enumerate(질문들):
            ids = 채팅토큰(질문)
            Xr = 층0qkv(gguf, ids)
            m = len(ids)
            경우들.append((f"7B 층 0 · 질문 {qi + 1} (토큰 {m})", Xr, 1024,
                        {"한 번에": [(0, m)], "나눠서": [(0, m // 2), (m // 2, m - m // 2)], "한 행씩": [(s, 1) for s in range(m)]}))
    for 이름, X, 최대길이, 길들 in 경우들:
        t0 = time.time()
        cos, sin = C.rope표(최대길이, 1e6, hd=HD)
        참 = 참조(X, 최대길이, cos, sin)
        t1 = time.time()
        한 = {"경우": 이름, "행": int(X.shape[0]), "최대길이": 최대길이, "참조 초": round(t1 - t0, 1), "길": {}}
        for 길, 덩이들 in 길들.items():
            글 = k.돌리기(X, 덩이들, 최대길이, cos, sin)
            한["길"][길] = {"덩이 수": len(덩이들), "다른 칸": 견주기(글, 참)}
            print(이름, 길, 한["길"][길], flush=True)
        결과["경우"].append(한)
    결과["모두 0"] = all(v == 0 for c in 결과["경우"] for g in c["길"].values() for v in g["다른 칸"].values())
    print("모두 0:", 결과["모두 0"], flush=True)
    json.dump(결과, open(출력, "w", encoding="utf-8"), ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
