#!/usr/bin/env python3
"""계약의 CPU 참조(계약/정수계약.py)가 스스로 맞는지 — GPU · 모델 파일 없이(빠른 점검 · CI). 같은 계약의 서로 다른 구현을 무작위 값으로
견주고, 바탕 연산은 정확한 유리수 셈과 견준다:
  1. fma32(반올림 한 번의 곱해더하기) 대 정확한 유리수의 반올림(가까운 쪽, 같으면 짝수)
  2. 행렬곱(느린 — 자리 둘) 대 행렬곱빠른 대 행렬곱블라스 — Q8_0 · Q4_0 의 정수와 반실수 척도
  3. 행렬곱K(느린) 대 행렬곱K블라스 — Q4_K · Q5_K · Q6_K 의 날 블록(GGUF 꼴)을 만들어 풀기K 로
  4. 임베딩K 대 날 블록에서 값 하나씩 푼 것(llama.cpp 의 dequantize_row_q*_K 와 같은 식) — 풀기K 의 배치도 함께 시험한다
활성값은 블록마다 크기가 다르게(2^−20 … 2^20) 하고, 0 인 블록 · 최댓값이 2 의 거듭제곱인 블록을 섞는다.

  python -I -X utf8 시험/계약자체.py
마지막 줄 "계약 자체 시험: 모두 통과"(종료 0) 또는 "못 미침"(종료 1).
"""
import os
import sys
from fractions import Fraction

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "계약"))
import 정수계약 as C        # noqa: E402

f32 = np.float32
실패 = []


def 확인(이름, 같음, 덧=""):
    print(f"{'통과' if 같음 else '못 미침'}  {이름}{(' — ' + 덧) if 덧 else ''}", flush=True)
    if not 같음:
        실패.append(이름)


def 다른칸(a, b):
    a = np.asarray(a, f32).view(np.int32)
    b = np.asarray(b, f32).view(np.int32)
    assert a.shape == b.shape, (a.shape, b.shape)
    return int(np.count_nonzero(a != b))


def 반올림32(r):
    """정확한 유리수 r → 가장 가까운 짧은실수(같으면 짝수) — 정규 범위(지수 −126 … 127)와 버금정규."""
    if r == 0:
        return f32(0.0)
    부호 = -1 if r < 0 else 1
    r = abs(r)
    e = r.numerator.bit_length() - r.denominator.bit_length()
    if Fraction(2) ** e > r:
        e -= 1
    밑 = max(e, -126) - 23                                          # 이 자리의 ulp = 2^밑
    q = r / (Fraction(2) ** 밑)
    n = q.numerator // q.denominator
    나머지 = q - n
    if 나머지 > Fraction(1, 2) or (나머지 == Fraction(1, 2) and n % 2 == 1):
        n += 1
    return f32(부호 * n * 2.0 ** 밑)                                 # fp64 로 정확(24 비트 · 2 의 거듭제곱) → 짧은실수로 정확


def 활성값(r, M, K):
    """[M][K] 짧은실수 — 블록(32 칸)마다 크기를 2^−20 … 2^20 로, 0 인 블록과 최댓값이 2 의 거듭제곱인 블록을 섞는다."""
    x = r.standard_normal((M, K)).astype(np.float64)
    크기 = 2.0 ** r.integers(-20, 21, (M, K // 32))
    x = (x.reshape(M, K // 32, 32) * 크기[:, :, None]).reshape(M, K)
    x[0, :32] = 0.0                                                 # 0 인 블록
    x[1, 32:64] = 0.0
    x[1, 40] = 2.0 ** 7                                             # 최댓값이 2 의 거듭제곱
    x[2, 64:96] = -(2.0 ** -3)
    return x.astype(f32)


def 반실수(r, 모양, 아래, 위):
    """[아래, 위) 의 크기 · 부호 섞인 반실수 값(짧은실수로)."""
    v = r.uniform(아래, 위, 모양) * np.where(r.random(모양) < 0.2, -1.0, 1.0)
    return v.astype(np.float16).astype(f32)


def 시험_fma32(r):
    n = 4000
    a = (r.standard_normal(n) * 2.0 ** r.integers(-30, 30, n)).astype(f32)
    b = (r.standard_normal(n) * 2.0 ** r.integers(-30, 30, n)).astype(f32)
    c = (r.standard_normal(n) * 2.0 ** r.integers(-60, 60, n)).astype(f32)
    c[:500] = (-(a[:500].astype(np.float64) * b[:500])).astype(f32)  # 거의 지워지는 경우
    c[500:1000] = 0.0
    got = C.fma32(a, b, c)
    want = np.array([반올림32(Fraction(float(a[i])) * Fraction(float(b[i])) + Fraction(float(c[i]))) for i in range(n)], f32)
    d = 다른칸(got, want)
    확인("fma32 — 정확한 유리수의 반올림", d == 0, f"{n} 개 중 다른 칸 {d}")


def 시험_행렬곱(r):
    M, K, N = 9, 256, 40
    x = 활성값(r, M, K)
    치 = r.standard_normal(N).astype(f32)
    for 이름, 아래, 위 in (("Q8_0", -127, 128), ("Q4_0", -8, 8)):
        q = r.integers(아래, 위, (K, N)).astype(np.int64)
        d = 반실수(r, (K // 32, N), 1e-4, 0.05)
        느린 = C.행렬곱(x, q, d, 치, 자리수=2)
        빠른 = C.행렬곱빠른(x, q, d, 치)
        블라스 = C.행렬곱블라스(x, q.T.astype(np.int8), d.T, 치, 일꾼=2)
        확인(f"행렬곱 {이름} — 느린 대 빠른", 다른칸(느린, 빠른) == 0, f"다른 칸 {다른칸(느린, 빠른)} / {M * N}")
        확인(f"행렬곱 {이름} — 느린 대 블라스", 다른칸(느린, 블라스) == 0, f"다른 칸 {다른칸(느린, 블라스)} / {M * N}")


def 날블록(r, t, N, KS):
    """GGUF k-양자화의 날 바이트 [N][KS][블록 바이트] — d · m 은 유한한 반실수, 나머지는 무작위 바이트."""
    bb = {12: 144, 13: 176, 14: 210}[t]
    raw = r.integers(0, 256, (N, KS, bb)).astype(np.uint8)
    if t in (12, 13):
        raw[:, :, 0:2] = 반실수(r, (N, KS), 1e-4, 0.02).astype(np.float16)[..., None].view(np.uint8)
        raw[:, :, 2:4] = 반실수(r, (N, KS), 1e-4, 0.02).astype(np.float16)[..., None].view(np.uint8)
    else:
        raw[:, :, 208:210] = 반실수(r, (N, KS), 1e-5, 0.002).astype(np.float16)[..., None].view(np.uint8)
    return raw.reshape(-1)


def 값하나씩(t, raw, N, K):
    """날 블록 → 값 [N][K] (짧은실수) — llama.cpp 의 dequantize_row_q4_K · q5_K · q6_K 와 같은 식을 칸마다(풀기K 와 따로 쓴 것)."""
    bb = {12: 144, 13: 176, 14: 210}[t]
    bl = np.asarray(raw).reshape(N, K // 256, bb)
    y = np.zeros((N, K), f32)
    for n in range(N):
        for s in range(K // 256):
            b = bl[n, s]
            o = 256 * s
            if t in (12, 13):
                d = f32(b[0:2].view(np.float16)[0])
                m = f32(b[2:4].view(np.float16)[0])
                sc = [int(v) for v in b[4:16]]

                def 척(j):
                    if j < 4:
                        return sc[j] & 63, sc[j + 4] & 63
                    return (sc[j + 4] & 15) | ((sc[j - 4] >> 6) << 4), (sc[j + 4] >> 4) | ((sc[j] >> 6) << 4)
                qs = b[16:144] if t == 12 else b[48:176]
                qh = b[16:48] if t == 13 else None
                for c in range(4):                                  # 값 64 개 = 아래블록 2c · 2c + 1
                    for h in range(2):
                        sv, mv = 척(2 * c + h)
                        a_ = f32(d * f32(sv))
                        b_ = f32(m * f32(mv))
                        for l in range(32):
                            q = (int(qs[32 * c + l]) >> (4 * h)) & 15
                            if t == 13:
                                q |= ((int(qh[l]) >> (2 * c + h)) & 1) << 4
                            y[n, o + 64 * c + 32 * h + l] = f32(f32(a_ * f32(q)) - b_)
            else:
                ql, qh = b[0:128], b[128:192]
                sc = b[192:208].view(np.int8)
                d = f32(b[208:210].view(np.float16)[0])
                for h in range(2):                                  # 값 128 개마다
                    for l in range(32):
                        i = l // 16
                        q1 = ((int(ql[64 * h + l]) & 15) | (((int(qh[32 * h + l]) >> 0) & 3) << 4)) - 32
                        q2 = ((int(ql[64 * h + l + 32]) & 15) | (((int(qh[32 * h + l]) >> 2) & 3) << 4)) - 32
                        q3 = ((int(ql[64 * h + l]) >> 4) | (((int(qh[32 * h + l]) >> 4) & 3) << 4)) - 32
                        q4 = ((int(ql[64 * h + l + 32]) >> 4) | (((int(qh[32 * h + l]) >> 6) & 3) << 4)) - 32
                        for k, q in ((0, q1), (2, q2), (4, q3), (6, q4)):
                            a_ = f32(d * f32(int(sc[8 * h + i + k])))
                            y[n, o + 128 * h + 16 * k + l] = f32(a_ * f32(q))
    return y


def 시험_K(r):
    M, K, N = 7, 512, 24
    x = 활성값(r, M, K)
    치 = r.standard_normal(N).astype(f32)
    for t, 이름 in ((12, "Q4_K"), (13, "Q5_K"), (14, "Q6_K")):
        raw = 날블록(r, t, N, K // 256)
        w = C.풀기K(t, raw, N, K)
        느린 = C.행렬곱K(x, w, 치)
        블라스 = C.행렬곱K블라스(x, w, 치, 일꾼=2)
        확인(f"행렬곱K {이름} — 느린 대 블라스", 다른칸(느린, 블라스) == 0, f"다른 칸 {다른칸(느린, 블라스)} / {M * N}")
        ids = np.arange(N)
        풀린 = C.임베딩K(w, ids)
        하나씩 = 값하나씩(t, raw, N, K)
        확인(f"임베딩K {이름} — 날 블록에서 값 하나씩", 다른칸(풀린, 하나씩) == 0, f"다른 칸 {다른칸(풀린, 하나씩)} / {N * K}")


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    r = np.random.default_rng(27)
    시험_fma32(r)
    시험_행렬곱(r)
    시험_K(r)
    print("계약 자체 시험:", "모두 통과" if not 실패 else f"못 미침 {실패}", flush=True)
    return 0 if not 실패 else 1


if __name__ == "__main__":
    sys.exit(main())
