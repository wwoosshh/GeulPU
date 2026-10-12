#!/usr/bin/env python3
"""26a (1) — k-양자화(Q4_K · Q5_K · Q6_K)의 판을 CPU 참조(계약/정수계약.행렬곱K블라스)와 비트까지. 7B k-양자화 파일의 층 0 의 실제 가중치
(파일의 정수 · 척도 그대로 — 엔진과 같은 배치로 깔아)와 무작위 활성값으로: 정수줄하나 × 끝손질 셋(qkv 의 구간 · o · down 잔차 · gate·up
SwiGLU정수 · 로짓), (뒤에) 타일 판 · 임베딩.

  python -I 시험/판26.py <ptx> <gguf …> <출력.json>
"""
import ctypes
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, ".."))
for _d in ("엔진", "계약"):
    sys.path.insert(0, os.path.join(ROOT, _d))
sys.path.insert(0, HERE)
import 글gpt2 as G          # noqa: E402
import gguf읽기 as GR       # noqa: E402
import 정수계약 as C        # noqa: E402
from 머리128 import 자리바이트    # noqa: E402

f32 = np.float32
u64, i64 = G.c_u64, G.c_i64
형식이름 = {12: "Q4_K", 13: "Q5_K", 14: "Q6_K"}
# 타일 판(생성타일.gl 의 판 표에서 — 이름 · BM = 16 · MT · WM · BN = 8 · NT · WN · 스레드 32 · WM · WN)
_판표 = [("정수타일선형", 2, 2, 2, 8), ("정수좁은타일선형", 2, 2, 2, 4), ("정수작은타일선형", 2, 2, 1, 4), ("정수아주작은타일선형", 2, 2, 1, 2),
        ("정수넓은타일선형", 2, 4, 2, 8), ("정수긴타일선형", 1, 4, 2, 8), ("정수긴4타일선형", 1, 4, 2, 8), ("정수긴2타일선형", 1, 4, 2, 8),
        ("정수깊은타일선형", 1, 4, 4, 4), ("정수깊은넓은타일선형", 2, 2, 4, 4), ("정수세판타일선형", 2, 2, 2, 8)]
타일판들 = [(이름, 16 * MT * WM, 8 * NT * WN, 32 * WM * WN, NT) for 이름, WM, WN, MT, NT in _판표]


def 엔진배치K(t, raw, N, K):
    """GGUF k-양자화 텐서(행 N · 깊이 K) → 엔진 배치의 (값 바이트 — 값 [KB][N][16] 뒤에 높은 [KB][N][4 · 8], 척 바이트 — [KS][N][16] 뒤에
    (Q6_K) d [KS][Np] 반실수) — 커널/생성K.gl 의 머리말 그대로."""
    형식, q, a, b = C.풀기K(t, raw, N, K)
    KB, KS = K // 32, K // 256
    Np = (N + 63) // 64 * 64
    qq = q.astype(np.int16)
    if 형식 == "Q6_K":
        qq = qq + 32                                                        # 6비트 그대로(0 … 63)
    u = qq.astype(np.uint8).reshape(N, KB, 4, 2, 4).transpose(1, 0, 2, 3, 4)   # [KB][N][j][h][m] — 칸 8j + 4h + m
    아래 = (u & 15)
    값 = (아래[:, :, :, 0, :] | (아래[:, :, :, 1, :] << 4)).astype(np.uint8)    # [KB][N][4][4]
    부분 = [np.ascontiguousarray(값).tobytes()]
    if 형식 == "Q5_K":
        h = ((u >> 4) & 1).astype(np.uint32)                                # [KB][N][j][h][m]
        바 = (h << (4 * np.arange(2)[None, None, None, :, None] + np.arange(4)[None, None, None, None, :])).sum((3, 4)).astype(np.uint8)  # [KB][N][j]
        부분.append(np.ascontiguousarray(바).tobytes())
    elif 형식 == "Q6_K":                                                    # 27단계 — 낱말 h′ 의 바이트 i, 비트 6 − 2G′ = 칸 16h′ + 4G′ + i 의 (높은 ^ 2)
        h = (((u >> 4) & 3) ^ 2).astype(np.uint32).reshape(KB, N, 2, 2, 2, 4)  # [KB][N][h′][j % 2][4 칸 묶음 반][i] — 칸 16h′ + 8(j % 2) + 4hh + i
        jl, hh, i = np.meshgrid(np.arange(2), np.arange(2), np.arange(4), indexing="ij")
        밀기 = (8 * i + 6 - 2 * (2 * jl + hh)).astype(np.uint32)            # G′ = 2(j % 2) + hh
        낱 = (h << 밀기[None, None, None]).sum((3, 4, 5)).astype(np.uint32)   # [KB][N][2]
        부분.append(np.ascontiguousarray(낱).tobytes())
    bb = {12: 144, 13: 176, 14: 210}[t]
    bl = np.asarray(raw).reshape(N, KS, bb)
    if 형식 == "Q6_K":
        척 = np.ascontiguousarray(bl[:, :, 192:208].transpose(1, 0, 2)).tobytes()
        d = np.zeros((KS, Np), np.uint16)
        d[:, :N] = np.ascontiguousarray(bl[:, :, 208:210]).view(np.uint16)[:, :, 0].T
        척 += d.tobytes()
    else:
        척 = np.ascontiguousarray(bl[:, :, 0:16].transpose(1, 0, 2)).tobytes()
    return b"".join(부분), 척, (형식, q, a, b)


def 다른칸(a, b):
    a, b = np.asarray(a), np.asarray(b)
    assert a.shape == b.shape, (a.shape, b.shape)
    if a.dtype == f32:
        a, b = a.view(np.int32), np.asarray(b, f32).view(np.int32)
    return int(np.count_nonzero(a != b))


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    ptx, 출력 = sys.argv[1], sys.argv[-1]
    파일들 = sys.argv[2:-1]
    dr = G.드라이버()
    mod = dr.모듈(open(ptx, "rb").read())
    fn = {}

    def 함수(이름):
        if 이름 not in fn:
            fn[이름] = dr.함수(mod, 이름)
        return fn[이름]

    def 띄우기(이름, grid, block, params):
        ps = [u64(p) if 참조 else i64(p) for 참조, p in params]
        args = (ctypes.c_void_p * len(ps))(*[ctypes.cast(ctypes.byref(p), ctypes.c_void_p) for p in ps])
        r = dr.cu.cuLaunchKernel(함수(이름), grid[0], grid[1], 1, block, 1, 1, 0, None, args, None)
        assert r == 0, (이름, r)

    def up(b):
        b = b if isinstance(b, bytes) else np.ascontiguousarray(b).tobytes()
        p = dr.할당(len(b))
        dr.확인(dr.cu.cuMemcpyHtoD_v2(p, b, len(b)))
        return p

    def 놓기():
        dr.맞추기()
        for p in dr.할당들:
            dr.확인(dr.cu.cuMemFree_v2(u64(p)))
        dr.할당들 = []

    r = np.random.default_rng(26)
    결과 = {"경우": []}
    for 파일 in 파일들:
        g = GR.GGUF(파일)
        이름파일 = os.path.basename(파일)
        print("파일", 이름파일, flush=True)
        # 행렬: (이름, 텐서들(열로 잇는다), 끝손질, 치우침)
        행렬들 = [("q·k", ["blk.0.attn_q.weight", "blk.0.attn_k.weight"], "", ["blk.0.attn_q.bias", "blk.0.attn_k.bias"]),
                 ("v", ["blk.0.attn_v.weight"], "", ["blk.0.attn_v.bias"]),
                 ("o", ["blk.0.attn_output.weight"], "_잔차", None),
                 ("down", ["blk.0.ffn_down.weight"], "_잔차", None),
                 ("down3", ["blk.3.ffn_down.weight"], "_잔차", None),
                 ("gu", ["blk.0.ffn_gate.weight", "blk.0.ffn_up.weight"], "_SwiGLU정수", None),
                 ("로짓", ["output.weight"], "", None)]
        for 이름, 텐서들, e, 치들 in 행렬들:
            원들 = [g.원(n) for n in 텐서들]
            ts = {t for t, _, _ in 원들}
            assert len(ts) == 1, (이름, ts)
            t = ts.pop()
            K = 원들[0][1][0]
            Ns = [dims[1] for _, dims, _ in 원들]
            N = sum(Ns)
            raw = np.concatenate([np.asarray(x) for _, _, x in 원들])
            if 이름 == "gu":                                     # gate · up 을 출력 32 열마다 번갈아(엔진과 같다)
                F = Ns[0]
                bb = {12: 144, 13: 176, 14: 210}[t]
                rows = raw.reshape(N, K // 256 * bb)
                순 = np.empty(2 * F, np.int64)
                for j in range(F // 32):
                    순[64 * j:64 * j + 32] = np.arange(32 * j, 32 * j + 32)
                    순[64 * j + 32:64 * j + 64] = F + np.arange(32 * j, 32 * j + 32)
                raw = np.ascontiguousarray(rows[순]).reshape(-1)
            값, 척, w = 엔진배치K(t, raw, N, K)
            형식 = w[0]
            p값, p척 = up(값), up(척)
            치 = np.concatenate([g.풀기(n) for n in 치들]).astype(f32) if 치들 else np.zeros(N, f32)
            p치 = up(치)
            X = (r.standard_normal((1, K)) * 10.0 ** r.uniform(-1, 1, (1, 1))).astype(f32)
            바이트, M0 = 자리바이트(X)
            정보 = np.zeros((K // 32, 64), np.int32)
            정보[:, :1] = M0.T
            p자, p정 = up(바이트), up(정보)
            y = C.행렬곱K블라스(X, w, 치)
            W = 64 if e == "_SwiGLU정수" else 32
            kn = f"정수줄하나{e}_{형식}"
            if e == "_SwiGLU정수":
                gcol = np.concatenate([np.arange(64 * j, 64 * j + 32) for j in range(N // 64)])
                참자리, 참정보 = 자리바이트(C.swiglu(y[:, gcol], y[:, gcol + 32]))
                p다자, p다정 = dr.할당(2 * N // 2), dr.할당((N // 64) * 64 * 4)
                띄우기(kn, ((N + W - 1) // W, 1), 128, [(1, p자), (1, p정), (1, p값), (1, p척), (1, p치), (1, p다정), (1, p다자), (0, 1), (0, K), (0, N)])
                dr.맞추기()
                다 = {"자리": 다른칸(dr.내리기(p다자, np.empty((2, 1, N // 2), np.int8)), 참자리[:, :1]),
                     "정보": 다른칸(dr.내리기(p다정, np.empty((N // 64, 64), np.int32))[:, :1].T, 참정보[:1])}
            else:
                p출 = dr.할당(N * 4)
                참 = y
                if e == "_잔차":
                    잔 = (r.standard_normal((1, N)) * 3.0).astype(f32)
                    p잔 = up(잔)
                    참 = (잔 + y).astype(f32)
                    띄우기(kn, ((N + W - 1) // W, 1), 128, [(1, p자), (1, p정), (1, p값), (1, p척), (1, p치), (1, p잔), (1, p출), (0, 1), (0, K), (0, N)])
                else:
                    띄우기(kn, ((N + W - 1) // W, 1), 128, [(1, p자), (1, p정), (1, p값), (1, p척), (1, p치), (1, p출), (0, 1), (0, K), (0, N)])
                dr.맞추기()
                다 = {"출력": 다른칸(dr.내리기(p출, np.empty((1, N), f32)), 참)}
            한 = {"파일": 이름파일, "가중치": 이름, "형식": 형식, "판": kn, "K": int(K), "N": int(N), "다른 칸": 다}
            결과["경우"].append(한)
            print(("다름! " if sum(다.values()) else "") + f"{이름} ({형식}) {kn} K {K} · N {N}: {다}", flush=True)
            # 타일 판 — 행 M (64 의 배수가 아니게)
            M = 100
            Xm = (r.standard_normal((M, K)) * 10.0 ** r.uniform(-1, 1, (M, 1))).astype(f32)
            바이트m, M0m = 자리바이트(Xm)
            폭 = (M + 63) // 64 * 64
            정보m = np.zeros((K // 32, 폭), np.int32)
            정보m[:, :M] = M0m.T
            p자m, p정m = up(바이트m), up(정보m)
            ym = C.행렬곱K블라스(Xm, w, 치)
            Np = (N + 63) // 64 * 64
            for 판, BM, BN, T, NT in 타일판들:
                if e == "_SwiGLU정수" and NT != 8:
                    continue
                kn2 = f"{판}{e}_{형식}"
                grid = ((M + BM - 1) // BM, (N + BN - 1) // BN)
                앞 = [(1, p자m), (1, p정m), (1, p값), (1, p척), (1, p치)]
                뒤 = [(0, M), (0, K), (0, N), (0, Np), (0, 0), (0, 0), (0, N)]          # 출력폭 = N
                if e == "_SwiGLU정수":
                    gcol = np.concatenate([np.arange(64 * j, 64 * j + 32) for j in range(N // 64)])
                    참자리m, 참정보m = 자리바이트(C.swiglu(ym[:, gcol], ym[:, gcol + 32]))
                    p다자, p다정 = dr.할당(2 * M * (N // 2)), dr.할당((N // 64) * 폭 * 4)
                    띄우기(kn2, grid, T, 앞 + [(1, p다정), (1, p다자)] + 뒤)
                    dr.맞추기()
                    다2 = {"자리": 다른칸(dr.내리기(p다자, np.empty((2, M, N // 2), np.int8)), 참자리m),
                          "정보": 다른칸(dr.내리기(p다정, np.empty((N // 64, 폭), np.int32))[:, :M].T, 참정보m)}
                else:
                    p출 = dr.할당(M * N * 4)
                    참m = ym
                    if e == "_잔차":
                        잔m = (r.standard_normal((M, N)) * 3.0).astype(f32)
                        참m = (잔m + ym).astype(f32)
                        dr.확인(dr.cu.cuMemcpyHtoD_v2(p출, 잔m.ctypes.data, 잔m.nbytes))
                        띄우기(kn2, grid, T, 앞 + [(1, p출), (1, p출)] + 뒤)
                    else:
                        띄우기(kn2, grid, T, 앞 + [(1, p출)] + 뒤)
                    dr.맞추기()
                    다2 = {"출력": 다른칸(dr.내리기(p출, np.empty((M, N), f32)), 참m)}
                한 = {"파일": 이름파일, "가중치": 이름, "형식": 형식, "판": kn2, "행": M, "K": int(K), "N": int(N), "다른 칸": 다2}
                결과["경우"].append(한)
                print(("다름! " if sum(다2.values()) else "") + f"{이름} ({형식}) {kn2} 행 {M}: {다2}", flush=True)
            놓기()
        # 임베딩 — 낱말표(token_embd)
        t, dims, raw = g.원("token_embd.weight")
        D, V = dims
        값, 척, w = 엔진배치K(t, raw, V, D)
        p값, p척 = up(값), up(척)
        토큰 = r.integers(0, V, 37).astype(np.int64)
        for 칸 in (False, True):
            kn3 = ("임베딩칸_" if 칸 else "임베딩_") + w[0]
            if 칸:
                걸음 = np.array([5, 3], np.int64)
                p토 = up(np.concatenate([np.zeros(3, np.int64), 토큰]))
                p걸 = up(걸음)
                p출 = dr.할당(D * 4)
                띄우기(kn3, ((D + 255) // 256, 1), 256, [(1, p토), (1, p값), (1, p척), (1, p출), (0, 1), (1, p걸)])
                dr.맞추기()
                참e = C.임베딩K(w, 토큰[:1])
                다3 = {"출력": 다른칸(dr.내리기(p출, np.empty((1, D), f32)), 참e)}
            else:
                p토, p출 = up(토큰), dr.할당(37 * D * 4)
                띄우기(kn3, ((37 * D + 255) // 256, 1), 256, [(1, p토), (1, p값), (1, p척), (1, p출), (0, 37)])
                dr.맞추기()
                다3 = {"출력": 다른칸(dr.내리기(p출, np.empty((37, D), f32)), C.임베딩K(w, 토큰))}
            결과["경우"].append({"파일": 이름파일, "가중치": "낱말표", "형식": w[0], "판": kn3, "다른 칸": 다3})
            print(("다름! " if sum(다3.values()) else "") + f"낱말표 ({w[0]}) {kn3}: {다3}", flush=True)
        놓기()
    결과["모두 0"] = all(v == 0 for c in 결과["경우"] for v in c["다른 칸"].values())
    print("경우", len(결과["경우"]), "· 모두 0:", 결과["모두 0"], flush=True)
    json.dump(결과, open(출력, "w", encoding="utf-8"), ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
