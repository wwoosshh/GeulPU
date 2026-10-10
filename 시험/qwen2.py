#!/usr/bin/env python3
"""14단계 판정 14a(계약 — 비트)의 시험: Qwen2.5-0.5B-Instruct Q8_0 (문서/14단계.md).

  (1) 커널 대 CPU 참조(계약/정수계약.py): 선형 판 모두(타일 판 · 열먼저 판 · 줄 판 · 묶은 줄 판 — q · k · v · o · gate · up · down · 로짓의
      모양, 실제 층의 가중치 · 무작위 보통 · 극단 활성값), RMSNorm · RoPE · SwiGLU 의 바꾸기(_QKV정수 · _SwiGLU정수 · RMS정규화정수줄 ·
      RoPEKV정수로 · SwiGLU줄 · 묶은 줄 판), GQA 어텐션(프롬프트 판 넷 · 생성 판 — 합성 q · k · v, 맥락 · 덩이 여럿, 머리 둘 = KV 머리 둘).
  (2) 길: 한 번에 · 하나씩 · 두조각 · 나눠 넣기 · 대화(차례마다 이어 쓰기) — 로짓 · 캐시 바이트(짧은 열과 위치 1024 를 넘는 열).
  (3) 채팅 질문 셋(답까지)의 모든 행 로짓 대 CPU 참조의 Qwen2 전체 앞으로; 위치 1024 를 넘는 열의 끝 행들도.
  (4) GPT-2 모듈의 소스가 14단계 전(시험/gpt2소스해시.json — 커밋 0a3c012 에서 만든 것)과 바이트까지 같다; 오류 칸 0.
결과는 빌드/결과/시험14.json, 마지막 줄에 통과 여부(종료 코드 0 · 1).
  python 시험/qwen2.py [빠르게]
"""
import ctypes
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
from 행렬곱 import 활성값           # noqa: E402

C, GR = Q.C, Q.GR
import 글qwen2 as E                # noqa: E402
import 커널생성 as K               # noqa: E402

u64, i64, f32 = ctypes.c_uint64, ctypes.c_int64, np.float32


def _run(m, x):
    r = m.dr.cu.cuLaunchKernel(x.fn, x.grid[0], x.grid[1], 1, x.block[0], x.block[1], 1, 0, None, x.args, None)
    assert r == 0, r


def _영(m, p, nb, v=0):
    m.dr.확인(m.dr.cu.cuMemsetD8_v2(u64(p), v, ctypes.c_size_t(nb)))


def 자리기대(x):
    """CPU 의 자리 둘(x [M][K]) → GPU 의 배치: 바이트 [2][M][K] (블록의 낱말 [0 4 1 5 2 6 3 7] 차례), 정보 [KB][M] (마법수 M_0)."""
    D, E_ = C.자리로(np.asarray(x, f32), 2)
    M, Kd = x.shape
    b = C.낱말차례(D.reshape(2, M, Kd // 32, 32)).reshape(2, M, Kd).astype(np.int8)
    return b, ((((137 + E_.T) << 23) + 0x400000).astype(np.int32))


def 자리읽기(m, 자p, 정p, M, Kd):
    정보폭 = (M + 63) // 64 * 64
    return (m.dr.내리기(자p, np.empty(2 * M * Kd, np.int8)).reshape(2, M, Kd),
            m.dr.내리기(정p, np.empty(Kd // 32 * 정보폭, np.int32)).reshape(Kd // 32, 정보폭)[:, :M])


def 자리다름(got, ref):
    return int((got[0] != ref[0]).sum()) + int((got[1] != ref[1]).sum())


def 층정수(g, name):
    """GGUF Q8_0 텐서 → (q [K][N] int64, d [KB][N] 짧은실수)."""
    q, d = Q._q8(g, name)
    return q.T.astype(np.int64), np.ascontiguousarray(d.T)


def 극단가중(q, d):
    """앞 두 블록의 가중치를 가장 작은 값(−128), 척도 1 로(S 가 가장 커지는 경우)."""
    q, d = q.copy(), d.copy()
    q[64:128, :] = -128
    d[2:4, :] = 1.0
    return q, d


def 깔아올림(m, p, q, d):
    """(q [K][N], d [KB][N]) 를 정수 배치(값 [블록][열][32], 척도 [블록][척도폭] 반실수)로 p 에 — (값 주소, 척도 주소)."""
    Kd, N = q.shape
    Np = (N + 63) // 64 * 64
    sc = np.zeros((Kd // 32, Np), np.float16)
    sc[:, :N] = d
    v = q.reshape(Kd // 32, 32, N).transpose(0, 2, 1).astype(np.int8).reshape(-1).view(np.uint8)
    m.dr.올리기(p, np.concatenate([v, sc.reshape(-1).view(np.uint8)]))
    return (p, p + v.nbytes)


# ── (1) 커널 대 CPU 참조 ──────────────────────────────────────────────────────────────────────────────

def 선형시험(m, g, rng, 빠르게):
    """타일 판(행먼저 · 열먼저, 끝손질 "" · _잔차) · 정수줄선형(o · down 묶은 줄 판 포함) · 로짓 판 대 CPU 정수계약.행렬곱 (+ 잔차)."""
    dr, D, F, V = m.dr, m.D, m.F, m.V
    out = {}
    입력 = dr.할당(512 * F * 4)
    출력 = dr.할당(200 * V * 4)
    잔차 = dr.할당(512 * max(D, 2 * F) * 4)
    가중칸 = dr.할당(V * D + (D // 32) * V * 2 + 1024)
    치우칸 = dr.할당(max(V, 2 * F) * 4)
    층들 = {"QKV (q·k·v 이음)": None, "o": "blk.5.attn_output.weight", "gate·up (번갈아)": None, "down": "blk.9.ffn_down.weight",
           "로짓": "output.weight"}
    for 이름, gname in 층들.items():
        if 이름.startswith("QKV"):
            qs = [층정수(g, f"blk.3.attn_{a}.weight") for a in "qkv"]
            q0, d0 = np.concatenate([x[0] for x in qs], 1), np.concatenate([x[1] for x in qs], 1)
        elif 이름.startswith("gate"):
            qg, dg = 층정수(g, "blk.7.ffn_gate.weight")
            qu, du = 층정수(g, "blk.7.ffn_up.weight")
            Kd = qg.shape[0]
            q0 = np.stack([qg.reshape(Kd, F // 32, 32), qu.reshape(Kd, F // 32, 32)], 2).reshape(Kd, 2 * F)
            d0 = np.stack([dg.reshape(Kd // 32, F // 32, 32), du.reshape(Kd // 32, F // 32, 32)], 2).reshape(Kd // 32, 2 * F)
        else:
            q0, d0 = 층정수(g, gname)
        Kd, N = q0.shape
        로짓 = 이름 == "로짓"
        for 종류 in ("보통", "극단"):
            q, d = (q0, d0) if 종류 == "보통" else 극단가중(q0, d0)
            wt = 깔아올림(m, 가중칸, q, d)
            Ms = (1, 3, 37, 200) if not 로짓 else (1, 3, 70)
            if 빠르게:
                Ms = Ms[1:3]
            for M in Ms:
                x = 활성값(rng, M, Kd, 종류)
                bias = (rng.standard_normal(N) * 0.1).astype(f32)
                res = (rng.standard_normal((M, N)) * 2).astype(f32)
                ref = C.행렬곱빠른(x, q, d, bias)
                dr.올리기(입력, x)
                dr.올리기(치우칸, bias)
                판들 = ["정수줄선형"] + (m.판이름들 if not 로짓 else list(m.로짓선형)[:-1])
                for 판 in 판들:
                    for epi in (("",) if 로짓 or 이름.startswith(("QKV", "gate")) else ("", "_잔차")):
                        if 판 != "정수줄선형" and not 로짓 and (판, epi) not in m.선형:
                            continue
                        fn = m.로짓선형[판] if 로짓 else m.선형[(판, epi)]
                        잔 = [u64(잔차)] if epi == "_잔차" else []
                        if epi == "_잔차":
                            dr.올리기(잔차, res)
                        if 판 == "정수줄선형":
                            ps = [u64(입력), u64(wt[0]), u64(wt[1]), u64(치우칸)] + 잔 + [u64(출력), i64(M), i64(Kd), i64(N)]
                        else:
                            x0 = E._띄움(m.k["정수로"], ((Kd // 32 + 31) // 32, M), (256, 1),
                                        [u64(입력), u64(m.자릿값2), u64(m.정보2), i64(M), i64(Kd)])
                            _run(m, x0)
                            ps = [u64(m.자릿값2), u64(m.정보2), u64(wt[0]), u64(wt[1]), u64(치우칸)] + 잔 + \
                                 [u64(출력), i64(M), i64(Kd), i64(N), i64((N + 63) // 64 * 64), i64(0), i64(0)]
                        _영(m, 출력, M * N * 4, 0xFF)
                        _run(m, E._띄움(fn, *m._격자(판, M, N, Kd, False), ps))
                        dr.맞추기()
                        got = dr.내리기(출력, np.empty((M, N), f32))
                        기대 = (res + ref).astype(f32) if epi == "_잔차" else ref
                        out[f"{이름} {종류} 행 {M} {판}{epi}"] = Q.다른칸(got, 기대)
    # 묶은 줄 판(o · down — 끝손질 _잔차, 열 묶음이 다른 판)
    for 이름, gname, 판 in (("o", "blk.5.attn_output.weight", "정수줄선형o"), ("down", "blk.9.ffn_down.weight", "정수줄선형down")):
        q, d = 층정수(g, gname)
        Kd, N = q.shape
        wt = 깔아올림(m, 가중칸, q, d)
        for M in (1, 4):
            x = 활성값(rng, M, Kd, "극단")
            res = (rng.standard_normal((M, N)) * 2).astype(f32)
            dr.올리기(입력, x)
            dr.올리기(잔차, res)
            _영(m, 치우칸, N * 4)
            w = m.줄판[이름][3]
            _run(m, E._띄움(m.k[판], ((N + w - 1) // w, 1), (256, 1),
                           [u64(입력), u64(wt[0]), u64(wt[1]), u64(치우칸), u64(잔차), u64(출력), i64(M), i64(N)]))
            dr.맞추기()
            got = dr.내리기(출력, np.empty((M, N), f32))
            out[f"{이름} 극단 행 {M} {판}"] = Q.다른칸(got, (res + C.행렬곱빠른(x, q, d, np.zeros(N, f32))).astype(f32))
    return out


def 바꾸기시험(m, g, rng, W, 설정):
    """RMSNorm · RoPE · SwiGLU 의 바꾸기 커널 대 CPU: RMS정규화정수줄 · RMS정규화줄, _QKV정수(타일 판 모두 · 행먼저 · 열먼저) · 정수줄선형QKV ·
    RoPEKV정수로 (q 자리 · 키 · 값 캐시 바이트 · 지수), _SwiGLU정수(타일 판 모두) · 정수줄선형gu · SwiGLU줄, 정수줄선형로짓 + 가장큰번호부분."""
    dr, D, F, NKV, L최대 = m.dr, m.D, m.F, m.NKV, m.최대길이
    out = {}
    입력 = dr.할당(512 * 2 * F * 4)
    출력 = dr.할당(512 * 2 * F * 4)
    cos, sin = C.rope표(L최대, 설정["theta"])
    l = 3
    w1 = W[f"{l}.n1"]
    n1p = m.층[l]["n1"]
    # RMS
    for M in (1, 5, 77):
        h = 활성값(rng, M, D, "극단") * np.float32(3)
        if M > 1:
            h[0, :] = 0                                         # 0 인 행(역rms = 1/√eps)
        dr.올리기(입력, h)
        _run(m, E._띄움(m.k["RMS정규화정수줄"], (M, 1), (256, 1), [u64(입력), u64(n1p), u64(m.자릿값2), u64(m.정보2), i64(M)]))
        _run(m, E._띄움(m.k["RMS정규화줄"], (M, 1), (256, 1), [u64(입력), u64(n1p), u64(출력)]))
        dr.맞추기()
        y = C.rms정규화(h, w1, 설정["eps"])
        out[f"RMS정규화정수줄 행 {M}"] = 자리다름(자리읽기(m, m.자릿값2, m.정보2, M, D), 자리기대(y))
        out[f"RMS정규화줄 행 {M}"] = Q.다른칸(dr.내리기(출력, np.empty((M, D), f32)), y)
    # QKV — 캐시 바이트는 시험KV(문장 하나)에
    qs = [층정수(g, f"blk.{l}.attn_{a}.weight") for a in "qkv"]
    qq, qd = np.concatenate([x[0] for x in qs], 1), np.concatenate([x[1] for x in qs], 1)
    bias = W[f"{l}.bq"], W[f"{l}.bk"], W[f"{l}.bv"]
    bias = np.concatenate(bias).astype(f32)
    wt = m.층[l]["qkv"]
    bp = m.층[l]["qkv치우침"]
    자q, 정q, kc, vc, ke, ve = m.시험KV

    def 캐시기대(y, C0, M):
        """y [M][QKV] (치우침까지) → (q′ 자리 기대, 키 · 값 캐시 [KV 머리] (바이트, 지수) 의 위치 C0 … C0+M−1)."""
        위치 = np.arange(C0, C0 + M)
        qr = np.concatenate([C.rope(y[:, 64 * a:64 * a + 64], cos, sin, 위치) for a in range(D // 64)], 1)
        kv = []
        for a in range(NKV):
            k = C.rope(y[:, D + 64 * a:D + 64 * a + 64], cos, sin, 위치)
            v = y[:, D + 64 * NKV + 64 * a:D + 64 * NKV + 64 * a + 64]
            kf, vf = np.zeros((C0 + M, 64), f32), np.zeros((C0 + M, 64), f32)
            kf[C0:], vf[C0:] = k, v
            kv.append((C.키캐시(kf, L최대), C.값캐시(vf, L최대)))
        return 자리기대(qr), kv

    def 캐시다름(M, C0, kv):
        n = 0
        정보폭 = (M + 63) // 64 * 64
        kb = dr.내리기(kc, np.empty(NKV * 2 * L최대 * 64, np.int8)).reshape(NKV, 2, L최대, 64)
        vb = dr.내리기(vc, np.empty(NKV * L최대 * 128, np.int8)).reshape(NKV, L최대 // 32, 2, 64, 32)
        keb = dr.내리기(ke, np.empty(NKV * L최대 * 2, np.uint8)).reshape(NKV, L최대, 2)
        veb = dr.내리기(ve, np.empty(NKV * L최대 * 2, np.uint8)).reshape(NKV, L최대, 2)
        for a in range(NKV):
            (kr, ker), (vr, ver) = kv[a]
            n += int((kb[a][:, C0:C0 + M] != kr[:, C0:C0 + M]).sum()) + int((keb[a][C0:C0 + M] != ker[C0:C0 + M]).sum())
            n += int((veb[a][C0:C0 + M] != ver[C0:C0 + M]).sum())
            # 값 캐시: 위치 C0 … C0+M−1 가 든 키 블록들 — 블록 안의 다른 위치는 0 (기대도 0)
            b0, b1 = C0 // 32, (C0 + M - 1) // 32 + 1
            n += int((vb[a][b0:b1] != vr[b0:b1]).sum())
        return n
    for M, C0 in ((5, 0), (37, 1000), (200, 3)):
        x = 활성값(rng, M, D, "보통")
        y = C.행렬곱빠른(x, qq, qd, bias)
        (qb, qi), kv = 캐시기대(y, C0, M)
        dr.올리기(입력, x)
        판들 = [판 for 판 in m.판이름들 if (판, "_QKV정수") in m.선형]
        for 판 in 판들:
            for p_, nb in ((자q, 2 * M * D), (kc, NKV * 2 * L최대 * 64), (vc, NKV * L최대 * 128), (ke, NKV * L최대 * 2), (ve, NKV * L최대 * 2)):
                _영(m, p_, nb)
            _run(m, E._띄움(m.k["정수로"], ((D // 32 + 31) // 32, M), (256, 1), [u64(입력), u64(m.자릿값2), u64(m.정보2), i64(M), i64(D)]))
            ps = [u64(m.자릿값2), u64(m.정보2), u64(wt[0]), u64(wt[1]), u64(bp)] + [u64(p_) for p_ in m.시험KV] + [u64(m.코사인), u64(m.사인)] + \
                 [i64(M), i64(D), i64(m.QKV), i64((m.QKV + 63) // 64 * 64), i64(M), i64(C0), i64(L최대), i64(0), i64(0)]
            _run(m, E._띄움(m.선형[(판, "_QKV정수")], *m._격자(판, M, m.QKV), ps))
            dr.맞추기()
            out[f"_QKV정수 {판} 행 {M} 위치 {C0}"] = 자리다름(자리읽기(m, 자q, 정q, M, D), (qb, qi)) + 캐시다름(M, C0, kv)
    # 줄 길: 정수줄선형QKV (RMS 묶음) · RoPEKV정수로(따로 도는 판)
    for M, C0 in ((1, 0), (3, 2047), (4, 500)):
        h = (rng.standard_normal((M, D)) * 2).astype(f32)
        xr = C.rms정규화(h, w1, 설정["eps"])
        y = C.행렬곱빠른(xr, qq, qd, bias)
        (qb, qi), kv = 캐시기대(y, C0, M)
        for 판 in ("정수줄선형QKV", "RoPEKV정수로"):
            for p_, nb in ((자q, 2 * M * D), (kc, NKV * 2 * L최대 * 64), (vc, NKV * L최대 * 128), (ke, NKV * L최대 * 2), (ve, NKV * L최대 * 2)):
                _영(m, p_, nb)
            if 판 == "정수줄선형QKV":
                dr.올리기(입력, h)
                _run(m, E._띄움(m.k[판], (m.QKV // 64, 1), (256, 1),
                               [u64(입력), u64(n1p), u64(wt[0]), u64(wt[1]), u64(bp)] + [u64(p_) for p_ in m.시험KV] +
                               [u64(m.코사인), u64(m.사인), i64(M), i64(m.QKV), i64(M), i64(C0), i64(L최대)]))
            else:
                dr.올리기(입력, y)
                _run(m, E._띄움(m.k[판], ((m.QKV // 32 + 31) // 32, M), (256, 1),
                               [u64(입력)] + [u64(p_) for p_ in m.시험KV] + [u64(m.코사인), u64(m.사인), i64(M), i64(M), i64(C0), i64(L최대)]))
            dr.맞추기()
            out[f"{판} 행 {M} 위치 {C0}"] = 자리다름(자리읽기(m, 자q, 정q, M, D), (qb, qi)) + 캐시다름(M, C0, kv)
    # SwiGLU
    qg, dg = 층정수(g, f"blk.{l}.ffn_gate.weight")
    qu, du = 층정수(g, f"blk.{l}.ffn_up.weight")
    wgu = m.층[l]["gu"]
    for M in (5, 64, 200):
        x = 활성값(rng, M, D, "보통")
        hh = C.swiglu(C.행렬곱빠른(x, qg, dg, np.zeros(F, f32)), C.행렬곱빠른(x, qu, du, np.zeros(F, f32)))
        기대 = 자리기대(hh)
        dr.올리기(입력, x)
        for 판 in [판 for 판 in m.판이름들 if (판, "_SwiGLU정수") in m.선형]:
            _run(m, E._띄움(m.k["정수로"], ((D // 32 + 31) // 32, M), (256, 1), [u64(입력), u64(m.자릿값), u64(m.정보), i64(M), i64(D)]))
            _영(m, m.자릿값2, 2 * M * F, 0x5A)
            ps = [u64(m.자릿값), u64(m.정보), u64(wgu[0]), u64(wgu[1]), u64(m.영치우침), u64(m.정보2), u64(m.자릿값2),
                  i64(M), i64(D), i64(2 * F), i64(2 * F), i64(0), i64(0)]
            _run(m, E._띄움(m.선형[(판, "_SwiGLU정수")], *m._격자(판, M, 2 * F), ps))
            dr.맞추기()
            out[f"_SwiGLU정수 {판} 행 {M}"] = 자리다름(자리읽기(m, m.자릿값2, m.정보2, M, F), 기대)
    for M in (1, 4):
        h = (rng.standard_normal((M, D)) * 2).astype(f32)
        xr = C.rms정규화(h, W[f"{l}.n2"], 설정["eps"])
        g_, u_ = C.행렬곱빠른(xr, qg, dg, np.zeros(F, f32)), C.행렬곱빠른(xr, qu, du, np.zeros(F, f32))
        dr.올리기(입력, h)
        _run(m, E._띄움(m.k["정수줄선형gu"], (2 * F // 64, 1), (256, 1),
                       [u64(입력), u64(m.층[l]["n2"]), u64(wgu[0]), u64(wgu[1]), u64(m.영치우침), u64(출력), i64(M), i64(2 * F)]))
        dr.맞추기()
        out[f"정수줄선형gu 행 {M}"] = Q.다른칸(dr.내리기(출력, np.empty((M, F), f32)), C.swiglu(g_, u_))
        gu = np.stack([g_.reshape(M, F // 32, 32), u_.reshape(M, F // 32, 32)], 2).reshape(M, 2 * F)
        dr.올리기(입력, gu)
        _run(m, E._띄움(m.k["SwiGLU줄"], ((M * F + 255) // 256, 1), (256, 1), [u64(입력), u64(출력), i64(M)]))
        dr.맞추기()
        out[f"SwiGLU줄 행 {M}"] = Q.다른칸(dr.내리기(출력, np.empty((M, F), f32)), C.swiglu(g_, u_))
    # 로짓(RMS 묶음) + 가장큰번호부분
    hq, hd = W["head"]
    h = (rng.standard_normal((1, D)) * 3).astype(f32)
    xr = C.rms정규화(h, W["norm"], 설정["eps"])
    ref = C.행렬곱빠른(xr, hq, hd, np.zeros(m.V, f32))
    dr.올리기(입력, h)
    _run(m, m._로짓줄(입력, 출력, 0))
    _run(m, E._띄움(m.k["가장큰번호부분"], (1, 1), (256, 1), [u64(m.부분값), u64(m.부분번호), u64(m.생성칸), i64(1), i64(m.부분수)]))
    dr.맞추기()
    got = dr.내리기(출력, np.empty((1, m.V), f32))
    tok = int(dr.내리기(m.생성칸, np.zeros(1, np.int64))[0])
    out["정수줄선형로짓 + 가장큰번호부분"] = Q.다른칸(got, ref) + int(tok != int(np.argmax(ref[0])))
    return out


def 어텐션시험(m, rng, 맥락들, 덩이들, 참조머리=(0, 13), 알림=print):
    """GQA 정수 KV 어텐션: 합성 QKV 행(치우침까지의 짧은실수)을 RoPEKV정수로로 캐시 · q 자리에 두고, 덩이 M 행(위치 C …)을 판 모두로 —
    (1) 프롬프트 판끼리(묶음64 · 묶음16 · 두층 · C + M ≤ 1024 면 차례 · 갈래 — 모든 머리), (2) 머리 둘(KV 머리 0 · 1 을 읽는 질의 머리 0 · 13)의
    CPU 참조(RoPE 뒤 정수계약.어텐션 — 질의 머리 h 는 KV 머리 ⌊h/7⌋)와 출력 자리 · 정보, 생성 판(정수조각어텐션 + 정수조각접기, 행 64 개씩)의 O/L."""
    dr, D, NH, NKV, 최대길이 = m.dr, m.D, m.NH, m.NKV, m.최대길이
    k = m.k
    QKV = m.QKV
    cos, sin = C.rope표(최대길이, m.설정["theta"])
    최대행 = max(맥락들) + max(덩이들)
    입력 = (rng.standard_normal((최대행, QKV)) * rng.uniform(0.3, 3.0, (최대행, 1))).astype(f32)
    g입력 = dr.할당(입력.nbytes)
    dr.올리기(g입력, 입력)
    KV = [u64(m.kc[0]), u64(m.vc[0]), u64(m.ke[0]), u64(m.ve[0])]
    덩큰 = 4096
    자q큰, 정q큰 = dr.할당(2 * 덩큰 * D), dr.할당(D // 32 * 덩큰 * 4)

    def kv(a, n, 자q, 정q):
        _run(m, E._띄움(k["RoPEKV정수로"], ((QKV // 32 + 31) // 32, n), (256, 1),
                       [u64(g입력 + a * QKV * 4), u64(자q), u64(정q)] + KV + [u64(m.코사인), u64(m.사인), i64(n), i64(n), i64(a), i64(최대길이)]))
    for a in range(0, 최대행, 덩큰):
        kv(a, min(덩큰, 최대행 - a), 자q큰, 정q큰)
    dr.맞추기()
    M최대 = max(덩이들)
    폭 = (M최대 + 63) // 64 * 64
    자q, 정q = dr.할당(2 * M최대 * D), dr.할당(D // 32 * 폭 * 4)
    출 = {nm: (dr.할당(2 * M최대 * D), dr.할당(D // 32 * 폭 * 4)) for nm in ("묶음64", "묶음16", "두층", "차례", "갈래")}
    조각칸, 출력 = dr.할당(64 * NH * (최대길이 // 64) * 68 * 4), dr.할당(64 * D * 4)
    묶음칸 = dr.할당(max(M최대 * NH * ((최대길이 + 1023) // 1024) * 68 * 4, NH * (폭 // 64 + 1) * 40 * 128 * 4))

    def 띄움들(판, C0, M):
        자, 정 = 출[판]
        G묶 = (C0 + M - 1) // 1024 + 1
        접기 = E._띄움(k["정수묶음접기"], (NH, M), (64, 1), [u64(묶음칸), u64(정), u64(자), i64(M), i64(M), i64(C0), i64(최대길이)])
        if 판 == "묶음64":
            return [E._띄움(k["정수어텐션묶음"], ((M + 63) // 64 * NH * G묶, 1), (128, 1),
                            [u64(자q), u64(정q)] + KV + [u64(묶음칸), i64(M), i64(M), i64(C0), i64(최대길이)]), 접기]
        if 판 == "묶음16":
            return [E._띄움(k["정수어텐션갈래묶음"], ((M + 15) // 16 * NH * G묶, 1), (256, 1),
                            [u64(자q), u64(정q)] + KV + [u64(묶음칸), i64(M), i64(M), i64(C0), i64(최대길이)]), 접기]
        if 판 == "두층":
            return [E._띄움(k["정수어텐션두층"], (NH, (M + 63) // 64), (128, 1),
                            [u64(자q), u64(정q)] + KV + [u64(묶음칸), u64(정), u64(자), i64(M), i64(M), i64(C0), i64(최대길이)])]
        if 판 == "갈래":
            return [E._띄움(k["정수어텐션갈래"], (NH, (M + 15) // 16), (32 * K.갈래워프, 1),
                            [u64(자q), u64(정q)] + KV + [u64(정), u64(자), i64(M), i64(M), i64(C0), i64(최대길이)])]
        return [E._띄움(k["정수어텐션"], (NH, (M + 63) // 64), (128, 1),
                        [u64(자q), u64(정q)] + KV + [u64(정), u64(자), i64(M), i64(M), i64(C0), i64(최대길이)])]
    out = {"프롬프트 판끼리 (모든 머리)": {}, "CPU 참조 (머리 0 · 13)": {}}
    for C0 in 맥락들:
        for M in 덩이들:
            if C0 + M > 최대길이:
                continue
            kv(C0, M, 자q, 정q)
            판들 = ["묶음64", "묶음16", "두층"] + (["차례", "갈래"] if C0 + M <= 1024 else [])
            for 판 in 판들:
                _영(m, 출[판][0], 2 * M최대 * D, 0x5A)
                _영(m, 출[판][1], D // 32 * 폭 * 4, 0x5A)
                for x in 띄움들(판, C0, M):
                    _run(m, x)
            dr.맞추기()
            o = {판: 자리읽기(m, 출[판][0], 출[판][1], M, D) for 판 in 판들}
            칸 = f"맥락 {C0} 덩이 {M}"
            out["프롬프트 판끼리 (모든 머리)"][칸] = {f"묶음64 대 {판}": 자리다름(o["묶음64"], o[판]) for 판 in 판들[1:]}
            y = 입력[:C0 + M]
            위치 = np.arange(C0 + M)
            ref = np.zeros((M, D), f32)
            t0 = time.time()
            for h in 참조머리:
                a = h // (NH // NKV)
                qh = C.rope(y[:, 64 * h:64 * h + 64], cos, sin, 위치)
                kh = C.rope(y[:, D + 64 * a:D + 64 * a + 64], cos, sin, 위치)
                vh = y[:, D + 64 * NKV + 64 * a:D + 64 * NKV + 64 * a + 64]
                ref[:, 64 * h:64 * h + 64] = C.어텐션(qh, kh, vh, 첫행=C0)
            초 = round(time.time() - t0, 1)
            rb, ri = 자리기대(ref)
            cols = np.zeros(D, bool)
            bl = np.zeros(D // 32, bool)
            for h in 참조머리:
                cols[64 * h:64 * h + 64] = True
                bl[2 * h:2 * h + 2] = True
            r = {판: int((o[판][0][:, :, cols] != rb[:, :, cols]).sum()) + int((o[판][1][bl] != ri[bl]).sum()) for 판 in ("묶음64",)}
            go = np.zeros((M, D), f32)
            for a in range(0, M, 64):
                n = min(64, M - a)
                kv(C0 + a, n, 자q, 정q)
                _run(m, E._띄움(k["정수조각어텐션"], (((C0 + a + n - 1) // 64 + 1 + 7) // 8, n * NH), (256, 1),
                               [u64(자q), u64(정q)] + KV + [u64(조각칸), i64(n), i64(n), i64(C0 + a), i64(최대길이)]))
                _run(m, E._띄움(k["정수조각접기"], (n * NH, 1), (256, 1), [u64(조각칸), u64(출력), i64(n), i64(n), i64(C0 + a), i64(최대길이)]))
                dr.맞추기()
                go[a:a + n] = dr.내리기(출력, np.empty(64 * D, f32)).reshape(64, D)[:n]
            r["생성 판 O/L"] = int((go[:, cols].view(np.int32) != ref[:, cols].view(np.int32)).sum())
            r["CPU 참조 초"] = 초
            out["CPU 참조 (머리 0 · 13)"][칸] = r
            if 알림:
                알림(f"  어텐션 {칸}: 판끼리 {out['프롬프트 판끼리 (모든 머리)'][칸]} · CPU 참조 {r}")
    return out


# ── (2) 길 ─────────────────────────────────────────────────────────────────────────────────────────

def 캐시모두(m, n, 층들=None):
    """층들(없으면 모두)의 키 · 값 캐시 · 지수 바이트의 해시 — 위치 n 까지(값 캐시는 블록 [0, ⌈n/32⌉))."""
    dr, NKV, L = m.dr, m.NKV, m.최대길이
    h = hashlib.sha256()
    # 값 캐시 블록 안의 바이트 → 위치(KV정수로의 배치: 위치 r 은 낱말 ((r%16%8)/2)·2 + r/16 의 바이트 (r%16/8)·2 + r%2) — n 뒤의 위치는 가린다
    r = np.arange(32)
    r16 = r % 16
    바이트위치 = np.empty(32, np.int64)
    바이트위치[((r16 % 8) // 2 * 2 + r // 16) * 4 + (r16 // 8) * 2 + r16 % 2] = r
    for l in (층들 if 층들 is not None else range(m.NL)):
        kb = dr.내리기(m.kc[l], np.empty(NKV * 2 * L * 64, np.int8)).reshape(NKV, 2, L, 64)[:, :, :n]
        vb = dr.내리기(m.vc[l], np.empty(NKV * L * 128, np.int8)).reshape(NKV, L // 32, 2, 64, 32)[:, :(n + 31) // 32].copy()
        if n % 32:
            vb[:, -1, :, :, 바이트위치 >= n % 32] = 0
        eb = dr.내리기(m.ke[l], np.empty(NKV * L * 2, np.uint8)).reshape(NKV, L, 2)[:, :n]
        fb = dr.내리기(m.ve[l], np.empty(NKV * L * 2, np.uint8)).reshape(NKV, L, 2)[:, :n]
        for a in (kb, vb, eb, fb):
            h.update(np.ascontiguousarray(a).tobytes())
    return h.hexdigest()


def 캐시비우기(m):
    for b, nb in ((m.kc바탕, m.kc[1] - m.kc[0]), (m.vc바탕, m.vc[1] - m.vc[0]), (m.ke바탕, m.ke[1] - m.ke[0]), (m.ve바탕, m.ve[1] - m.ve[0])):
        _영(m, b, nb * m.NL)


def 길시험(m, ids, 끝행=8):
    """같은 토큰열 ids 의 마지막 끝행 행 로짓 · 캐시 바이트를 길마다: 한 번에, 하나씩(끝행만 — 앞은 한 번에), 두조각, 나눠 넣기(조각 n/3),
    셋째 조각을 작은 덩이로(4 · 3 · 1). 기준(한 번에)과 다른 칸 · 같은 캐시."""
    n = len(ids)
    out = {}

    def 계산들(조각들):
        캐시비우기(m)
        s = 0
        rows = []
        for b in 조각들:
            m.토큰넣기(ids[s:b])
            if b - s <= 4:
                m.계산(1, b - s, s, "전부")
                rows.append(m.로짓(b - s).copy())
            else:
                k = min(b - s, 끝행)
                m.계산(1, b - s, s, k)
                rows.append(np.concatenate([np.zeros((b - s - k, m.V), f32), m.로짓(k).copy()]))
            s = b
        return np.concatenate(rows)[-끝행:], 캐시모두(m, n)
    기준, 기준캐시 = 계산들([n])
    길들 = {"하나씩(끝 8 행)": [n - 끝행] + list(range(n - 끝행 + 1, n + 1)),
           "두조각": [n // 2, n], "나눠 넣기(셋)": [n // 3, 2 * n // 3, n], "작은 덩이": [n - 8, n - 4, n - 1, n]}
    for 이름, 조각들 in 길들.items():
        r, c = 계산들(조각들)
        out[이름] = {"로짓 다른 칸": Q.다른칸(r, 기준), "캐시 같음": c == 기준캐시}
    return out, 기준


def 대화시험(m, tk, 생성=64):
    """세 차례 대화(실행.py 의 대화 — 실행기와 같은 코드): 차례마다 덩이를 앞 캐시에 이어 넣고(이어넣기) 답을 생성 그래프로(이어생성 — 끝 토큰까지,
    생성 한도까지). (가) 대화 전체의 토큰열(마지막 토큰 앞까지)을 한 번에 넣은 탐욕과 답의 토큰이 모두 같은가, 캐시 바이트가 같은가,
    (나) 같은 대화를 두 번 돌리면 같은 답인가."""
    sys.path.insert(0, Q.ROOT)
    import 실행
    d = 실행.대화(m, tk, 최대생성=생성)
    결과 = []
    for _ in range(2):
        d.비우기()
        캐시비우기(m)
        답들 = [d.묻기(q)[0] for q in Q.질문들]
        결과.append((답들, list(d.토큰), d.위치, 캐시모두(m, d.위치)))
    답들, 토큰, 위치, 캐시 = 결과[0]
    전 = 토큰[:-1]
    assert len(전) == 위치
    캐시비우기(m)
    고름 = []
    for a in range(0, len(전), m.로짓행):
        조각 = 전[a:a + m.로짓행]
        m.토큰넣기(조각)
        m.계산(1, len(조각), a, "전부")
        고름 += [int(x) for x in m.로짓(len(조각)).argmax(1)]
    캐시2 = 캐시모두(m, len(전))
    # 답의 토큰 자리: 토큰열에서 답마다의 시작(덩이 뒤)을 다시 세어 — 답 i 의 토큰 j 는 앞 행의 탐욕이어야
    다름, 자리 = 0, 0
    d2 = 실행.대화(m, tk, 최대생성=생성)
    for q, 답 in zip(Q.질문들, 답들):
        덩이 = d2.덩이(q)
        자리 += len(덩이) - (1 if d2.토큰 else 0)
        for j, t in enumerate(답):
            다름 += int(고름[자리 + j - 1] != t)
        d2.토큰 = 토큰[:자리 + len(답)]
        자리 += len(답)
    return {"답들": [tk.잇기(a) for a in 답들], "토큰 수": len(토큰),
            "한 번에 대 차례마다 — 고른 토큰 다른 수": 다름, "캐시 같음": 캐시 == 캐시2,
            "두 번 돌림 — 답 같음": 결과[0][0] == 결과[1][0] and 결과[0][3] == 결과[1][3]}


def 실행기시험(답들기대):
    """14e — 터미널 실행기(실행.py)를 프로세스로 두 번: 채팅 질문 셋을 표준 입력으로 이어서. 두 번의 출력(시간 숫자를 뺀 것)이 같고, 차례마다
    첫 토큰까지의 시간 · 초당 토큰 줄이 있고, 답의 글이 대화 시험(같은 코드 — 한 번에 계산과 토큰까지 같음을 확인한 것)의 답과 같은가."""
    import re
    import subprocess
    입력 = "\n".join(Q.질문들 + ["/끝"]) + "\n"
    출력들 = []
    for _ in range(2):
        r = subprocess.run([sys.executable, os.path.join(Q.ROOT, "실행.py"), Q.GGUF, "--최대길이", "4096", "--생성", "64"],
                           input=입력.encode("utf-8"), capture_output=True, timeout=600)
        출력들.append(r.stdout.decode("utf-8", "replace").replace("\r\n", "\n"))     # 윈도의 표준 출력은 줄바꿈이 \r\n
    통계 = [re.findall(r"\[첫 토큰까지 [0-9.]+ ms · 생성 \d+ 토큰 [0-9.]+ 토큰/초 · 문맥 \d+\]", o) for o in 출력들]
    지움 = [re.sub(r"[0-9.]+ ms|[0-9.]+ 토큰/초|올림 [0-9.]+ 초", "#", o) for o in 출력들]
    답글 = [x.split("\n[첫 토큰까지")[0].strip() for x in 출력들[0].split("\n> ")[1:4]]
    return {"두 번 출력 같음(시간 숫자 빼고)": 지움[0] == 지움[1], "통계 줄 수": [len(x) for x in 통계],
            "답 = 대화 시험의 답": 답글 == [a.replace("<|im_end|>", "").strip() for a in 답들기대],
            "출력 (첫 번)": 출력들[0][-2000:]}


# ── (3) CPU 참조 전체 앞으로 ────────────────────────────────────────────────────────────────────────────

def 전체앞으로시험(m, tk, W, 설정, 알림=print):
    """채팅 질문 셋(답까지 — 글의 탐욕 답 32 토큰)의 모든 행 로짓 대 CPU 참조의 Qwen2 전체 앞으로."""
    out = {}
    for q in Q.질문들:
        ids = Q.채팅(tk, q)
        답 = m.생성(ids, 32)
        열 = ids + 답[:-1]
        캐시비우기(m)
        m.토큰넣기(열)
        m.계산(1, len(열), 0, "전부")
        g = m.로짓(len(열)).copy()
        t0 = time.time()
        c = Q.참조로짓(W, 설정, 열)
        out[q] = {"행": len(열), "다른 칸": Q.다른칸(g, c), "CPU 초": round(time.time() - t0, 1)}
        if 알림:
            알림(f"  전체 앞으로 {q[:30]}…: {out[q]}")
    return out


def 긴전체시험(m, tk, W, 설정, n=1100, 끝행=4, 알림=print):
    """위치 1024 를 넘는 열(n 토큰)의 마지막 끝행 행 로짓 — 글(한 번에 · 나눠 넣기) 대 CPU 참조 전체 앞으로(두 층 접기가 들어간다)."""
    긴 = (tk.나누기(T.문장들[1]) * 100)[:n]
    캐시비우기(m)
    m.토큰넣기(긴)
    m.계산(1, n, 0, 끝행)
    g = m.로짓(끝행).copy()
    t0 = time.time()
    c = 참조끝로짓(W, 설정, 긴, 끝행)
    r = {"행": n, "끝 행": 끝행, "다른 칸": Q.다른칸(g, c), "CPU 초": round(time.time() - t0, 1)}
    if 알림:
        알림(f"  긴 전체 앞으로: {r}")
    return r


def 참조끝로짓(W, 설정, ids, 끝행):
    """CPU 참조 전체 앞으로의 마지막 끝행 행 로짓(긴 열의 CPU 시간 — 로짓 행렬곱만 끝 행으로)."""
    cos, sin = C.rope표(max(64, len(ids)), 설정["theta"])
    return C.qwen2_앞으로(W, 설정, ids, cos, sin, 끝행=끝행)


# ── 모두 ────────────────────────────────────────────────────────────────────────────────────────────

def main():
    빠르게 = "빠르게" in sys.argv[1:]
    res, 통과 = {}, True
    t시작 = time.time()
    rng = np.random.default_rng(140)

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
    g = GR.GGUF(Q.GGUF)
    W, 설정 = Q.참조가중치()
    tk = Q.토크나이저()
    m = Q.엔진(최대행=3072, 최대길이=4096, 로짓행=512)
    # (1)
    r = 선형시험(m, g, rng, 빠르게)
    적기("(1) 선형 판 모두 대 CPU", {"칸 수": len(r), "다른 칸이 있는 것": {k: v for k, v in r.items() if v}}, all(v == 0 for v in r.values()))
    r = 바꾸기시험(m, g, rng, W, 설정)
    적기("(1) RMSNorm · RoPE · SwiGLU 바꾸기 대 CPU", r, all(v == 0 for v in r.values()))
    맥락들, 덩이들 = ((0, 900, 2100), (5, 64, 300)) if 빠르게 else ((0, 100, 900, 1000, 2100, 3000), (1, 5, 64, 300, 1000))
    r = 어텐션시험(m, rng, 맥락들, 덩이들)
    ok = all(v == 0 for c in r["프롬프트 판끼리 (모든 머리)"].values() for v in c.values()) and \
        all(v == 0 for c in r["CPU 참조 (머리 0 · 13)"].values() for k, v in c.items() if k != "CPU 참조 초")
    적기("(1) GQA 어텐션 — 판끼리 · CPU 참조", r, ok)
    # (2)
    짧은 = Q.채팅(tk, Q.질문들[2])
    짧은 = 짧은 + m.생성(짧은, 20)
    r1, _ = 길시험(m, 짧은)
    긴 = (tk.나누기(T.문장들[1]) * 100)[:2600]
    r2, _ = 길시험(m, 긴)
    r = {"짧은 열 (" + str(len(짧은)) + ")": r1, "긴 열 (2600)": r2}
    ok = all(v["로짓 다른 칸"] == 0 and v["캐시 같음"] for x in r.values() for v in x.values())
    적기("(2) 길 — 한 번에 · 하나씩 · 두조각 · 나눠 넣기 · 작은 덩이 (로짓 · 캐시)", r, ok)
    r = 대화시험(m, tk)
    적기("(2) 대화 — 차례마다 이어 쓰기 대 한 번에 · 되풀이", r,
         r["한 번에 대 차례마다 — 고른 토큰 다른 수"] == 0 and r["캐시 같음"] and r["두 번 돌림 — 답 같음"])
    r = 실행기시험(r["답들"])
    적기("(14e) 실행기 — 세 차례 대화, 두 번 같은 답, 통계 줄", r,
         r["두 번 출력 같음(시간 숫자 빼고)"] and r["통계 줄 수"] == [3, 3] and r["답 = 대화 시험의 답"])
    # (3)
    r = 전체앞으로시험(m, tk, W, 설정)
    적기("(3) 채팅 질문 셋의 모든 행 로짓 대 CPU 참조", r, all(v["다른 칸"] == 0 for v in r.values()))
    if not 빠르게:
        r = 긴전체시험(m, tk, W, 설정)
        적기("(3) 위치 1024 를 넘는 열의 끝 행 대 CPU 참조", r, r["다른 칸"] == 0)
    e = m.오류칸()
    적기("오류 칸", e, e == 0)
    res["초"] = round(time.time() - t시작, 1)
    os.makedirs(T.결과폴더, exist_ok=True)
    json.dump(res, open(os.path.join(T.결과폴더, "시험14.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    print("빌드/결과/시험14.json —", "모두 통과" if 통과 else "실패가 있다", f"({res['초']} 초)")
    sys.exit(0 if 통과 else 1)


if __name__ == "__main__":
    main()
