"""행렬곱 시험 — 정수 블록 계약(자리 둘)의 선형 판 모두를 CPU 참조(계약/정수계약.py)와 비트로 대조한다.

GGUF 의 실제 층 다섯의 가중치(극단 시험은 앞 두 블록의 가중치를 가장 작은 값 · 척도 1 로) · 무작위 활성값(보통 · 극단) · 무작위 치우침으로,
모듈의 정수 텐서 코어 타일 판 모두(커널생성.정수판표 — 프롬프트의 판)와 dp4a 줄 판(정수줄선형 — 생성 메가커널과 같은 코드). 타일 판은
정수로(활성값 바꾸기)를 거친다. (연구 6단계 재기7.py 의 행렬곱시험 — 11단계부터 모듈의 판 표 전부.)
"""
import numpy as np

from 공통 import G, GR, C, u64, i64, 다른칸


def 층정수(g, name):
    """GGUF 텐서 → (q [K][N] int64, d [KB][N] float32 — 반실수 값)."""
    t, (K, N), raw = g.원(name)
    bl = raw.reshape(N, K // 32, GR.블록[t][1])
    d = np.ascontiguousarray(bl[:, :, :2]).view(np.float16).reshape(N, K // 32).T.astype(np.float32)
    if t == GR.Q8_0:
        q = bl[:, :, 2:].view(np.int8).astype(np.int64)
    else:
        qs = bl[:, :, 2:]
        q = np.concatenate([(qs & 15).astype(np.int64) - 8, (qs >> 4).astype(np.int64) - 8], 2)
    return np.ascontiguousarray(q.reshape(N, K).T), d


def 활성값(rng, M, K, 종류):
    """무작위 활성값 [M][K]: "보통"(정규분포, 1% 를 40 배), "극단"(블록마다 S 가 가장 커지는 값 · E 가 잘리는 값 · 정규수 끝)."""
    x = rng.standard_normal((M, K)).astype(np.float32) * np.where(rng.random((M, K)) < 0.01, 40, 1).astype(np.float32)
    if 종류 == "극단":
        for r in range(M):
            k = int(rng.integers(-20, 20))
            v = np.float32(np.nextafter(np.float32(2), np.float32(0))) * np.float32(2.0 ** k) * (-1 if r % 2 else 1)
            x[r, 64:96], x[r, 96:128] = v, -v                  # 칸 모두 ±(2 − 2⁻²³)·2^k — 맨 위 자리가 가장 크다
        x[1 % M, 128:160] = np.float32(1e-35)                 # E 가 −98 로 잘리는 블록
        x[2 % M, 160:192] = np.float32(3e29)                  # E = 98
        x[3 % M, 192:224] = np.float32(-2.0 ** -126)          # 정규수 끝
    x[0, 32:64] = 0                                           # 0 인 블록
    return x


def 행렬곱시험(m, g, rng):
    """엔진 m 의 선형 판 모두 대 CPU 참조 — {"층 종류 행 M 판": {"다른 칸", "칸 수"}}."""
    dr, out = m.dr, {}
    층 = {"c_attn": ("blk.3.attn_qkv.weight", "attn.c_attn.weight", 3),
         "c_proj": ("blk.5.attn_output.weight", "attn.c_proj.weight", 5),
         "c_fc": ("blk.7.ffn_up.weight", "mlp.c_fc.weight", 7),
         "mlp c_proj": ("blk.9.ffn_down.weight", "mlp.c_proj.weight", 9),
         "로짓 (낱말표)": ("token_embd.weight", None, None)}
    D, V = m.D, m.V
    입력 = dr.할당(1024 * 4 * D * 4)
    출력 = dr.할당(1024 * ((V + 63) // 64 * 64) * 4)
    가중칸 = dr.할당(((V + 63) // 64 * 64) * D * 2 + 4 * D * D)
    치우칸 = dr.할당(((V + 63) // 64 * 64) * 4)
    for 이름, (gname, wname, l) in 층.items():
        로짓 = wname is None
        wt0 = m.wteT if 로짓 else m.층[l][wname]
        q0, d0 = 층정수(g, gname)
        K, N = q0.shape
        for 종류 in ("보통", "극단"):
            q, d, wt = q0, d0, wt0
            if 종류 == "극단":                                 # 앞 두 블록의 가중치를 가장 작은 값(Q8_0 −128 · Q4_0 −8)으로, 척도 1
                형식 = m.낱말형식 if 로짓 else m.층형식
                q, d = q0.copy(), d0.copy()
                q[64:128, :] = -128 if 형식 == "Q8_0" else -8
                d[2:4, :] = 1.0
                Np = (N + 63) // 64 * 64
                sc = np.zeros((K // 32, Np), np.float16)
                sc[:, :N] = d
                qb = q.reshape(K // 32, 32, N).transpose(0, 2, 1)
                if 형식 == "Q8_0":
                    v = qb.astype(np.int8).reshape(-1).view(np.uint8)
                else:
                    u = (qb + 8).astype(np.uint8).reshape(K // 32, N, 4, 2, 4)
                    v = (u[:, :, :, 0, :] | (u[:, :, :, 1, :] << 4)).astype(np.uint8).reshape(-1)
                dr.올리기(가중칸, np.concatenate([v, sc.reshape(-1).view(np.uint8)]))
                wt = (가중칸, 가중칸 + v.nbytes)
            for M in ((1, 3, 37, 200) if not 로짓 else (1, 3, 70)):
                x = 활성값(rng, M, K, 종류)
                bias = (rng.standard_normal(N) * 0.1).astype(np.float32)
                ref = C.행렬곱(x, q, d, bias, m.자리수)
                dr.올리기(입력, x)
                dr.올리기(치우칸, bias)
                for 판 in ["정수줄선형"] + list(G.정수판표(m.자리수, m.정수KV)):
                    fn = m.로짓선형[판] if 로짓 else m.선형[(판, "")]
                    if 판 == "정수줄선형":
                        ps = [u64(입력)] + G._가중인자(wt) + [u64(치우칸), u64(출력), i64(M), i64(K), i64(N)]
                    else:
                        x0 = G._띄움(m.k["정수로"], ((K // 32 + 31) // 32, M), (256, 1),
                                    [u64(입력), u64(m.자릿값), u64(m.정보), i64(M), i64(K)])
                        dr.확인(dr.cu.cuLaunchKernel(x0.fn, *x0.grid, 1, *x0.block, 1, 0, None, x0.args, None))
                        ps = [u64(m.자릿값), u64(m.정보)] + G._가중인자(wt) + [u64(치우칸), u64(출력), i64(M), i64(K),
                                                                          i64(N), i64((N + 63) // 64 * 64)] + \
                             ([i64(0), i64(0)] if m.정수KV else [])            # 정수 KV 판의 타일은 행 · 열 시작을 받는다
                    dr.확인(dr.cu.cuMemsetD8_v2(u64(출력), 0xFF, M * N * 4))
                    y = G._띄움(fn, *m._격자(판, M, N, K, m.크기 == "small"), ps)   # 줄 판의 열 묶음은 깊이 · 크기에 따른다(호스트와 같은 규칙)
                    dr.확인(dr.cu.cuLaunchKernel(y.fn, *y.grid, 1, *y.block, 1, 0, None, y.args, None))
                    dr.맞추기()
                    got = dr.내리기(출력, np.empty((M, N), np.float32))
                    out[f"{이름} {종류} 행 {M} {판}"] = {"다른 칸": 다른칸(got, ref), "칸 수": M * N}
    return out
