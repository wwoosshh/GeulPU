"""31단계 탐침 둘 — 셈 규칙. 연산 하나씩(곱 · 더하기 · 곱해더하기 · 나눗셈 · 제곱근 · 짝수로 반올림 · 반실수 읽기)을 경계값과 무작위
   값으로 이 PC 의 Vulkan 장치 모두(비정규수 모드별)와 CUDA PTX(.ftz 없음 · 있음)에서 돌려, CPU 기준(유리수로 정확히)과 비트로 견준다.
   - 31d: 비정규수 버림은 규칙 후보(입력을 버리는가 · 반올림 앞/뒤 어디서 판단하는가 · 버린 0 의 부호 · FMA 의 곱을 따로 반올림하는가)
     마다 기준을 내서, 장치의 결과를 모두 설명하는 후보를 찾는다.
   - 31e: 나눗셈 · 제곱근 · 짝수 반올림 · 반실수 읽기가 바른 반올림(정확한 값)과 같은지 본다 — 무작위 + 한가운데에 아주 가까운 값.
   python -X utf8 탐침31_셈.py [결과.json]"""
import ctypes
import hashlib
import json
import math
import os
import random
import struct
import sys
import time
from fractions import Fraction

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import spv  # noqa: E402
import vk as V  # noqa: E402
from 탐침31 import MIN_NORMAL, TWO, bits, neg, round_f32  # noqa: E402

MNF = 2.0 ** -126
INF = float("inf")


def fb(u):
    return struct.unpack("<f", struct.pack("<I", u))[0]


def f32ok(x):
    return struct.unpack("<f", struct.pack("<f", x))[0] == x


def F(m, e):
    """m · 2^e (짧은실수로 정확해야 한다)"""
    x = math.ldexp(m, e)
    assert f32ok(x), (m, e)
    return x


def 비정규(x):
    return x != 0.0 and abs(x) < MNF


# ---------------- CPU 기준: 규칙 후보 ----------------
입력들 = ("그대로", "0(부호지킴)", "+0")                                   # 비정규수 입력을 어떻게 보는가
판단들 = ("없음", "반올림앞", "반올림뒤(지수무한)", "반올림뒤(IEEE)")         # 결과를 버리는 판단을 어디서 하는가
부호들 = ("지킴", "+0")                                                   # 버린 결과의 0 부호


def 규칙들(fma=False):
    out = []
    for dz in 입력들:
        for jd in 판단들:
            for zs in (부호들 if jd != "없음" else ("지킴",)):
                for fu in ((True, False) if fma else (True,)):
                    out.append((dz, jd, zs, fu))
    return out


def 이름(rule):
    dz, jd, zs, fu = rule
    s = "IEEE(비정규수 그대로)" if (dz == "그대로" and jd == "없음") else f"입력 {dz} · 판단 {jd}" + (f" · 버린0 {zs}" if jd != "없음" else "")
    return s + ("" if fu else " · 곱 따로 반올림")


def daz(x, dz):
    if dz != "그대로" and 비정규(x):
        return -0.0 if (dz == "0(부호지킴)" and neg(x)) else 0.0
    return x


def 무한지수반올림(q):
    """|q| 를 가수 24 비트로(지수 제한 없이 — 비정규수 칸 없이) 가까운 쪽 · 같으면 짝수"""
    a = abs(q)
    e = a.numerator.bit_length() - a.denominator.bit_length()
    if TWO ** e > a:
        e -= 1
    se = e - 23
    m = a / TWO ** se
    n = m.numerator // m.denominator
    rem = m - n
    if rem > Fraction(1, 2) or (rem == Fraction(1, 2) and n % 2 == 1):
        n += 1
    return n * TWO ** se


def 냄(q, zero_neg, jd, zs):
    if q == 0:
        return -0.0 if zero_neg else 0.0
    if jd == "없음":
        return round_f32(q, zero_neg)
    z = -0.0 if (q < 0 and zs == "지킴") else 0.0
    if jd == "반올림앞":
        return z if abs(q) < MIN_NORMAL else round_f32(q)
    if jd == "반올림뒤(지수무한)":
        return z if 무한지수반올림(q) < MIN_NORMAL else round_f32(q)
    r = round_f32(q)
    if r in (INF, -INF):
        return r
    return z if abs(Fraction(r)) < MIN_NORMAL else r


def 제곱근(x):
    """바르게 반올림한 짧은실수 √x (x > 0) — 정수 제곱근 + 남은 몫 표시"""
    q = Fraction(x)
    n, d = q.numerator, q.denominator
    E = -(d.bit_length() - 1)
    N = n
    if E % 2:
        N <<= 1
        E -= 1
    k = 40
    s = math.isqrt(N << (2 * k))
    exact = s * s == (N << (2 * k))
    return round_f32(Fraction(2 * s + (0 if exact else 1), 2) * TWO ** (E // 2 - k))


def 기준(op, a, b, c, rule):
    dz, jd, zs, fu = rule
    a, b, c = daz(a, dz), daz(b, dz), daz(c, dz)
    Fa, Fb, Fc = Fraction(a), Fraction(b), Fraction(c)
    if op == "mul":
        return 냄(Fa * Fb, neg(a) != neg(b), jd, zs)
    if op == "add":
        return 냄(Fa + Fb, neg(a) and neg(b), jd, zs)
    if op == "fma":
        if fu:
            return 냄(Fa * Fb + Fc, (neg(a) != neg(b)) and neg(c), jd, zs)
        p = daz(냄(Fa * Fb, neg(a) != neg(b), jd, zs), dz)
        return 냄(Fraction(p) + Fc, neg(p) and neg(c), jd, zs)
    if op == "div":
        if b == 0:
            return -INF if neg(a) != neg(b) else INF
        return 냄(Fa / Fb, neg(a) != neg(b), jd, zs)
    if op == "sqrt":
        return a if a == 0 else 제곱근(a)
    raise ValueError(op)


def 짝수반올림(x):
    n = round(Fraction(x))                       # Fraction 의 round 는 같으면 짝수
    return (-0.0 if neg(x) else 0.0) if n == 0 else float(n)


def 반실수(h):
    return struct.unpack("<e", struct.pack("<H", h))[0]


# ---------------- 시험 자료 ----------------
def rf(rng, emin, emax, sign=True):
    """가수 24 비트 무작위 · 지수 [emin, emax] 의 정규수"""
    x = math.ldexp((1 << 23) | rng.getrandbits(23), rng.randint(emin, emax) - 23)
    return -x if sign and rng.random() < 0.5 else x


def rsub(rng, sign=True):
    x = math.ldexp(rng.randint(1, (1 << 23) - 1), -149)
    return -x if sign and rng.random() < 0.5 else x


def sgn(rng, x):
    return -x if rng.random() < 0.5 else x


def 지수(x):
    return math.frexp(abs(x))[1] - 1


def 경계자료():
    rng = random.Random(3132)
    S = {}
    # ── 곱 ──  a = (1 + k·2⁻²³)/2, b = 2⁻¹²⁵(1 − k·2⁻²³) → a·b = 2⁻¹²⁶ − k²·2⁻¹⁷² (막 정규수 바로 아래)
    ks = list(range(1, 41)) + list(range(1440, 1461)) + list(range(2040, 2061)) + [rng.randint(1, 2100) for _ in range(100)]
    올림 = [(sgn(rng, F((1 << 23) + k, -24)), sgn(rng, F((1 << 24) - 2 * k, -149)), 0.0) for k in ks]
    # (1 − j·2⁻²⁴) · 2⁻¹²⁶ = 2⁻¹²⁶ − j·2⁻¹⁵⁰ — 비정규수 칸의 한가운데(j 홀수)와 칸 위(j 짝수)
    가운데 = [(sgn(rng, F((1 << 24) - j, -24)), sgn(rng, MNF), 0.0) for j in list(range(1, 17)) + [rng.randint(17, 1 << 20) for _ in range(40)]]
    비정규결과 = []
    for _ in range(300):
        a = rf(rng, -70, -60)
        t = rng.randint(-150, -127)
        비정규결과.append((a, rf(rng, t - 지수(a), t - 지수(a)), 0.0))
    바로위 = [(sgn(rng, F((1 << 23) + k, -23)), sgn(rng, MNF), 0.0) for k in range(50)]
    바로위 += [(rf(rng, -63, -63), rf(rng, -63, -62), 0.0) for _ in range(100)]
    비정규입력 = [(rsub(rng), rf(rng, 0, 40), 0.0) for _ in range(200)] + [(rsub(rng), rsub(rng), 0.0) for _ in range(10)]
    영 = [(x, y, 0.0) for x in (0.0, -0.0) for y in (1.5, -1.5, 2.0 ** -130, -(2.0 ** -130))]
    정규 = [(rf(rng, -60, 60), rf(rng, -60, 60), 0.0) for _ in range(300)]
    S["mul"] = {"막정규수로올림": 올림, "비정규수칸가운데": 가운데, "비정규수결과": 비정규결과, "정규수바로위": 바로위,
                "비정규수입력": 비정규입력, "0": 영, "무작위정규": 정규}
    # ── 더하기 ──
    상쇄 = []
    for i in range(330):
        ma = rng.randint(1 << 23, (1 << 24) - 1)
        mb = rng.randint(1 << 23, (1 << 24) - 1) if i < 300 else min(max(ma + rng.randint(-10, 10), 1 << 23), (1 << 24) - 1)
        s = rng.choice((1, -1))
        상쇄.append((s * F(ma, -149), -s * F(mb, -149), 0.0))
    막정규 = []
    for _ in range(60):
        mb = rng.randint(1 << 22, (1 << 23) - 1) * 2
        for dlt in (1 << 23, (1 << 23) - 2, (1 << 23) + 2):
            s = rng.choice((1, -1))
            막정규.append((s * F(mb + dlt, -149), -s * F(mb, -149), 0.0))
    비정규입력더 = [(rsub(rng), rf(rng, -126, -120), 0.0) for _ in range(200)] + [(rsub(rng), rf(rng, -100, 10), 0.0) for _ in range(50)]
    비정규끼리 = [(rsub(rng), rsub(rng), 0.0) for _ in range(90)]
    for _ in range(10):
        m = rng.randint(1, (1 << 23) - 1)
        비정규끼리.append((F(m, -149), F((1 << 23) - m, -149), 0.0))
    영더 = [(x, y, 0.0) for x in (0.0, -0.0) for y in (0.0, -0.0)] + [(x, -x, 0.0) for x in (1.5, -1.5, 2.0 ** -130, MNF)]
    정규더 = [(rf(rng, -60, 60), rf(rng, -60, 60), 0.0) for _ in range(300)]
    S["add"] = {"상쇄로비정규수": 상쇄, "상쇄로막정규수근처": 막정규, "비정규수입력": 비정규입력더, "비정규수끼리": 비정규끼리, "0": 영더,
                "무작위정규": 정규더}
    # ── 곱해더하기 ──
    올림f = [(a, b, rng.choice((0.0, -0.0))) for (a, b, _) in 올림]
    곱만 = []
    for _ in range(300):
        a = rf(rng, -70, -60)
        t = rng.randint(-149, -127)
        곱만.append((a, rf(rng, t - 지수(a), t - 지수(a)), rf(rng, -126, -122)))
    # 동점깨기: a·b = N·2⁻²⁴ (N 홀수 25 비트 — 짧은실수 두 수의 한가운데). 합친 FMA 이고 c 를 버리지 않으면 c 의 부호로 갈린다.
    동점 = []
    while len(동점) < 720:
        N = rng.randrange((1 << 24) + 1, 1 << 25, 2)
        p = next((p for p in range(3, 4096, 2) if N % p == 0), None)
        if p is None or N // p >= (1 << 24):
            continue
        sh = rng.randint(-10, 10)
        작게 = rng.random() < 0.3                                          # 곱을 2⁻¹⁰⁰ 쯤으로
        a = sgn(rng, F(p, sh - 12 - (50 if 작게 else 0)))
        b = F(N // p, -sh - 12 - (50 if 작게 else 0))
        작은정규 = 2.0 ** -125 if 작게 else 2.0 ** -100
        for c in (rsub(rng, False), -rsub(rng, False), 작은정규, -작은정규, 0.0, -0.0):
            동점.append((a, b, c))
    # 상쇄로 막정규수 근처: a·b ∈ [2⁻¹²⁴, 2⁻¹²²), c = ±k·2⁻¹⁴⁹ − RN(a·b) → 정확한 값 = (a·b − RN(a·b)) ± k·2⁻¹⁴⁹ (잘게 남는 비트)
    경계f = []
    while len(경계f) < 400:
        a, b = rf(rng, -62, -62), rf(rng, -62, -62)
        P = Fraction(a) * Fraction(b)
        r = round_f32(P)
        s = 1 if P > 0 else -1
        k = rng.choice([(1 << 23) - 8, (1 << 23) - 4, 1 << 23, 1 << 23, 1 << 23, (1 << 23) + 4, 4 * rng.randint(1, 1 << 21)])
        cq = s * k * TWO ** -149 - Fraction(r)
        c = float(cq)
        if Fraction(c) != cq or not f32ok(c):
            continue
        경계f.append((a, b, c))
    비정규입력f = [(rsub(rng), rf(rng, 10, 40), rf(rng, -100, -90)) for _ in range(100)]
    비정규입력f += [(rf(rng, -63, -60), rf(rng, -63, -60), rsub(rng)) for _ in range(100)]
    영f = [(x, y, z) for x in (0.0, -0.0) for y in (1.5, -1.5) for z in (0.0, -0.0)] + [(1.5, 2.0, -3.0), (-1.5, 2.0, 3.0)]
    정규f = [(rf(rng, -40, 40), rf(rng, -40, 40), rf(rng, -40, 40)) for _ in range(300)]
    S["fma"] = {"막정규수로올림(c=±0)": 올림f, "곱만비정규수": 곱만, "동점깨기": 동점, "상쇄로막정규수근처": 경계f, "비정규수입력": 비정규입력f,
                "0": 영f, "무작위정규": 정규f}
    # ── 나눗셈 ──
    # 몫 = 2⁻¹²⁶(1 − j·2⁻²⁴) — 나눗셈에서 '반올림 뒤' 판단의 두 갈래(지수무한 · IEEE)를 가르는 유일한 꼴(나뉨수 가수가 모두 1, 나눔수 2 의 거듭제곱)
    칸가운데 = []
    for j in list(range(1, 17)) + [rng.randint(17, 1 << 20) for _ in range(24)]:
        e = rng.randint(-20, 1)                                          # 나눔수 2^(e+126) ≤ 2¹²⁷
        칸가운데.append((sgn(rng, F((1 << 24) - j, e - 24)), sgn(rng, F(1, e + 126)), 0.0))
    S["div"] = {"비정규수칸가운데": 칸가운데,
                "비정규수결과": [(rf(rng, -126, -110), rf(rng, 1, 30), 0.0) for _ in range(500)],
                "비정규수입력(나뉨수)": [(rsub(rng), rf(rng, -30, 0), 0.0) for _ in range(200)],
                "비정규수입력(나눔수)": [(rf(rng, -126, -100), rsub(rng), 0.0) for _ in range(100)]}
    # ── 제곱근 ──
    S["sqrt"] = {"비정규수입력": [(rsub(rng, False), 0.0, 0.0) for _ in range(200)], "0": [(0.0, 0.0, 0.0), (-0.0, 0.0, 0.0)]}
    return S


def 제곱근_mod(k, n):
    """r² ≡ k (mod 2ⁿ) 인 홀수 r (k ≡ 1 mod 8)"""
    r = 1
    for i in range(3, n):
        if (r * r - k) % (1 << (i + 1)):
            r += 1 << (i - 1)
    return r % (1 << n)


def 정밀자료():
    """나눗셈 · 제곱근 · 짝수 반올림 · 반실수 — (A, B, C) 비트와 기준 비트"""
    rng = random.Random(3133)
    P = {}
    # 나눗셈
    무 = [(rf(rng, -30, 30), rf(rng, -30, 30)) for _ in range(80000)]
    가 = []
    while len(가) < 20000:                                    # a/b 가 한가운데에서 ≈ 2⁻⁴⁸ 만 벗어난다
        bi = rng.randrange((1 << 23) + 1, 1 << 24, 2)
        k = rng.choice((-1, 1)) * rng.randrange(1, 1 << 10, 2)
        t = (k * pow(bi, -1, 1 << 25)) % (1 << 25)            # bi · t ≡ k (mod 2²⁵), t 홀수
        if t < (1 << 24):
            continue
        j, rem = divmod(bi * t - k, 1 << 25)
        assert rem == 0
        if not ((1 << 23) <= j < (1 << 24)):
            continue
        eb, et = rng.randint(-10, 10), rng.randint(-10, 10)
        b = F(bi, eb - 23)
        a = F(j, 25 + (eb - 23) + (et - 24))
        가.append((sgn(rng, a), sgn(rng, b)))
    계 = []
    for _ in range(10000):
        kind = rng.randrange(3)
        if kind == 0:                                            # RMSNorm 평균 = 합 / 너비
            계.append((rf(rng, -20, 20, sign=False), float(rng.choice((896, 1536, 2048, 3584, 4096, 5120, 8192, 18944)))))
        elif kind == 1:                                          # SwiGLU: g / (1 + e)
            계.append((rf(rng, -10, 7), F((1 << 23) + rng.getrandbits(23), -23)))
        else:                                                    # 어텐션: O / L (L ≥ 1)
            계.append((rf(rng, -20, 10), rf(rng, 0, 12, sign=False)))
    P["div"] = {n: ([bits(a) for a, b in xs], [bits(b) for a, b in xs], [0] * len(xs),
                    [bits(round_f32(Fraction(a) / Fraction(b))) for a, b in xs])
                for n, xs in (("무작위", 무), ("한가운데근처", 가), ("계약모양", 계))}
    # 제곱근
    무 = [rf(rng, -60, 60, sign=False) for _ in range(80000)]
    가 = []
    while len(가) < 20000:                                    # √x 가 한가운데에서 ≈ 2⁻⁵⁰ 만 벗어난다: T² = x·2²⁶ + k
        k = rng.choice((-1, 1)) * rng.randrange(1, 1 << 20)
        if k % 8 != 1:
            continue
        r = 제곱근_mod(k, 26)
        for T in {r, (1 << 26) - r, (r + (1 << 25)) % (1 << 26), ((1 << 26) - r + (1 << 25)) % (1 << 26)}:
            if (1 << 24) <= T < (1 << 25) and T % 2:
                xi, rem = divmod(T * T - k, 1 << 26)
                assert rem == 0
                if xi >= (1 << 24):
                    continue
                et = rng.randint(-30, 30)
                가.append(F(xi, 26 + 2 * (et - 24)))
    계 = [rf(rng, -20, 10, sign=False) + 1e-6 for _ in range(10000)]   # RMSNorm: 평균 + eps
    계 = [struct.unpack("<f", struct.pack("<f", x))[0] for x in 계]
    P["sqrt"] = {n: ([bits(x) for x in xs], [0] * len(xs), [0] * len(xs), [bits(제곱근(x)) for x in xs])
                 for n, xs in (("무작위", 무), ("한가운데근처", 가[:20000]), ("계약모양", 계))}
    # 짝수 반올림
    반 = [sgn(rng, rng.randint(0, (1 << 22) - 1) + 0.5) for _ in range(30000)]
    무 = [rf(rng, -5, 24) for _ in range(60000)]
    작은 = [sgn(rng, x) for x in (0.5, F((1 << 24) - 1, -25), F((1 << 23) + 1, -24), 1.5, 2.5, 0.0) for _ in range(20)]
    작은 += [rf(rng, -30, -1) for _ in range(9000)] + [rsub(rng) for _ in range(880)]
    P["roundeven"] = {n: ([bits(x) for x in xs], [0] * len(xs), [0] * len(xs), [bits(짝수반올림(x)) for x in xs])
                      for n, xs in (("반", 반), ("무작위", 무), ("1보다작은값", 작은))}
    # 반실수 읽기 — 모든 반실수(NaN 빼고)
    hs = [h for h in range(1 << 16) if not (((h >> 10) & 31) == 31 and (h & 1023))]
    sub_h = [h for h in hs if (h >> 10) & 31 == 0 and h & 1023]
    P["half"] = {n: (xs, [0] * len(xs), [0] * len(xs), [bits(반실수(h)) for h in xs]) for n, xs in (("모든반실수", hs), ("반실수비정규수", sub_h))}
    return P


# ---------------- 돌리기: Vulkan ----------------
def pack_u(xs):
    return struct.pack("<%dI" % len(xs), *xs)


def run_vk(dev, op, A, B, C, dm, szp):
    n = len(A)
    N = (n + 63) // 64 * 64
    pad = [0] * (N - n)
    bufs = [dev.buffer(pack_u(list(A) + pad)), dev.buffer(pack_u(list(B) + pad)), dev.buffer(pack_u(list(C) + pad)), dev.buffer(b"\0" * (4 * N))]
    dev.run(spv.elementwise_kernel(op, dm, szp), bufs, (N // 64, 1, 1))
    out = list(struct.unpack("<%dI" % N, ctypes.string_at(bufs[3][1], 4 * N)))[:n]
    dev.release()
    return out


# ---------------- 돌리기: CUDA PTX ----------------
PTX_HEAD = ".version 7.4\n.target sm_80\n.address_size 64\n"
PTX_KERNEL = """
.visible .entry @NAME@(.param .u64 pa, .param .u64 pb, .param .u64 pc, .param .u64 po)
{
    .reg .b16 %h<3>;
    .reg .b32 %r<12>;
    .reg .f32 %f<6>;
    .reg .b64 %rd<12>;
    mov.u32 %r1, %ctaid.x;
    mov.u32 %r2, %ntid.x;
    mov.u32 %r3, %tid.x;
    mad.lo.u32 %r4, %r1, %r2, %r3;
    mul.wide.u32 %rd1, %r4, 4;
    ld.param.u64 %rd2, [pa];
    ld.param.u64 %rd3, [pb];
    ld.param.u64 %rd4, [pc];
    ld.param.u64 %rd5, [po];
    add.u64 %rd6, %rd2, %rd1;
    add.u64 %rd7, %rd3, %rd1;
    add.u64 %rd8, %rd4, %rd1;
    add.u64 %rd9, %rd5, %rd1;
    ld.global.b32 %r10, [%rd6];
    ld.global.f32 %f1, [%rd6];
    ld.global.f32 %f2, [%rd7];
    ld.global.f32 %f3, [%rd8];
    mov.b32 {%h1, %h2}, %r10;
    @OP@
    st.global.f32 [%rd9], %f4;
    ret;
}
"""
PTX_OPS = {"mul": "mul.rn@Z@.f32 %f4, %f1, %f2;", "add": "add.rn@Z@.f32 %f4, %f1, %f2;", "fma": "fma.rn@Z@.f32 %f4, %f1, %f2, %f3;",
           "div": "div.rn@Z@.f32 %f4, %f1, %f2;", "sqrt": "sqrt.rn@Z@.f32 %f4, %f1;", "roundeven": "cvt.rni@Z@.f32.f32 %f4, %f1;",
           "half": "cvt.f32.f16 %f4, %h1;"}


def ptx_source():
    parts = [PTX_HEAD]
    for op, ins in PTX_OPS.items():
        for z in ("", ".ftz"):
            if op == "half" and z:
                continue
            parts.append(PTX_KERNEL.replace("@NAME@", "k_" + op + ("_ftz" if z else "")).replace("@OP@", ins.replace("@Z@", z)))
    return "".join(parts)


class Cuda:
    def __init__(self):
        cu = ctypes.WinDLL("nvcuda.dll")
        u64 = ctypes.c_uint64
        cu.cuMemAlloc_v2.argtypes = [ctypes.POINTER(u64), ctypes.c_size_t]
        cu.cuMemcpyHtoD_v2.argtypes = [u64, ctypes.c_void_p, ctypes.c_size_t]
        cu.cuMemcpyDtoH_v2.argtypes = [ctypes.c_void_p, u64, ctypes.c_size_t]
        cu.cuMemFree_v2.argtypes = [u64]
        cu.cuLaunchKernel.argtypes = [ctypes.c_void_p] + [ctypes.c_uint] * 7 + [ctypes.c_void_p] * 3
        cu.cuModuleLoadData.argtypes = [ctypes.POINTER(ctypes.c_void_p), ctypes.c_char_p]
        cu.cuModuleGetFunction.argtypes = [ctypes.POINTER(ctypes.c_void_p), ctypes.c_void_p, ctypes.c_char_p]
        self.cu = cu
        self.ok(cu.cuInit(0))
        ctx = ctypes.c_void_p()
        self.ok(cu.cuDevicePrimaryCtxRetain(ctypes.byref(ctx), 0))
        self.ok(cu.cuCtxSetCurrent(ctx))
        dev = ctypes.c_int()
        self.ok(cu.cuDeviceGet(ctypes.byref(dev), 0))
        name = ctypes.create_string_buffer(256)
        self.ok(cu.cuDeviceGetName(name, 256, dev))
        drv = ctypes.c_int()
        self.ok(cu.cuDriverGetVersion(ctypes.byref(drv)))
        self.name, self.driver = name.value.decode(), drv.value
        self.mod = ctypes.c_void_p()
        self.ok(cu.cuModuleLoadData(ctypes.byref(self.mod), ptx_source().encode() + b"\0"))

    @staticmethod
    def ok(r):
        if r:
            raise RuntimeError(f"CUDA 드라이버 오류 {r}")

    def run(self, kname, A, B, C):
        n = len(A)
        N = (n + 63) // 64 * 64
        fn = ctypes.c_void_p()
        self.ok(self.cu.cuModuleGetFunction(ctypes.byref(fn), self.mod, kname.encode()))
        ptrs = []
        for arr in (A, B, C, None):
            p = ctypes.c_uint64()
            self.ok(self.cu.cuMemAlloc_v2(ctypes.byref(p), 4 * N))
            ptrs.append(p)
            data = pack_u(list(arr) + [0] * (N - n)) if arr is not None else b"\0" * (4 * N)
            self.ok(self.cu.cuMemcpyHtoD_v2(p.value, data, 4 * N))
        params = (ctypes.c_void_p * 4)(*[ctypes.cast(ctypes.byref(p), ctypes.c_void_p) for p in ptrs])
        self.ok(self.cu.cuLaunchKernel(fn, N // 64, 1, 1, 64, 1, 1, 0, None, ctypes.cast(params, ctypes.c_void_p), None))
        self.ok(self.cu.cuCtxSynchronize())
        out = ctypes.create_string_buffer(4 * N)
        self.ok(self.cu.cuMemcpyDtoH_v2(out, ptrs[3].value, 4 * N))
        for p in ptrs:
            self.ok(self.cu.cuMemFree_v2(p))
        return list(struct.unpack("<%dI" % N, out.raw))[:n]


# ---------------- 견주기 ----------------
def 순서(u):
    return u if u < 0x80000000 else -(u & 0x7FFFFFFF)


def 견주기(run, 경계, 경계기준, 정밀):
    """run(op, A, B, C) → 출력 비트. 경계: 규칙마다 맞는지 · 정밀: 바른 반올림과 같은지"""
    out = {}
    for op, cats in 경계.items():
        A, B, C = [], [], []
        for cases in cats.values():
            for a, b, c in cases:
                A.append(bits(a))
                B.append(bits(b))
                C.append(bits(c))
        got = run(op, A, B, C)
        rules = list(경계기준[op])
        r_op = {"갈래": {}, "출력": got}
        i = 0
        ok_all = set(rules)
        for cat, cases in cats.items():
            g = got[i:i + len(cases)]
            맞음 = {이름(r): sum(x == y for x, y in zip(g, 경계기준[op][r][cat])) for r in rules}
            full = [r for r in rules if 경계기준[op][r][cat] == g]
            ok_all &= set(full)
            ieee = 경계기준[op][("그대로", "없음", "지킴", True)][cat]
            예 = [{"a": hex(A[i + j]), "b": hex(B[i + j]), "c": hex(C[i + j]), "장치": hex(g[j]), "IEEE": hex(ieee[j])}
                 for j in range(len(g)) if g[j] != ieee[j]][:6]
            r_op["갈래"][cat] = {"칸": len(g), "IEEE와같음": sum(x == y for x, y in zip(g, ieee)), "모두맞는규칙": [이름(r) for r in full],
                               "규칙별맞음": 맞음, "IEEE와다른예": 예}
            i += len(cases)
        r_op["모든갈래가맞는규칙"] = [이름(r) for r in rules if r in ok_all]
        if not ok_all:
            총 = {r: sum(x == y for x, y in zip(got, [v for cat in cats for v in 경계기준[op][r][cat]])) for r in rules}
            best = max(총, key=총.get)
            r_op["가장가까운규칙"] = {"규칙": 이름(best), "맞음": 총[best], "칸": len(got)}
        out[op] = r_op
    for op, cats in 정밀.items():
        r_op = {}
        for cat, (A, B, C, want) in cats.items():
            g = run(op, A, B, C)
            차 = [abs(순서(x) - 순서(y)) for x, y in zip(g, want)]
            다름 = [j for j in range(len(g)) if g[j] != want[j]]
            분포 = {}
            for j in 다름:
                분포[차[j]] = 분포.get(차[j], 0) + 1
            r_op[cat] = {"칸": len(g), "다름": len(다름), "ULP차분포": {str(k): v for k, v in sorted(분포.items())},
                         "다른예": [{"a": hex(A[j]), "b": hex(B[j]), "장치": hex(g[j]), "바른값": hex(want[j])} for j in 다름[:6]],
                         "출력_sha256": hashlib.sha256(pack_u(g)).hexdigest()}
        out.setdefault("정밀", {})[op] = r_op
    return out


이름표 = {"mul": "곱", "add": "더하기", "fma": "곱해더하기", "div": "나눗셈", "sqrt": "제곱근", "roundeven": "짝수반올림", "half": "반실수읽기"}


def 알리기(제목, res):
    print(f"\n== {제목}")
    for op, r in res.items():
        if op == "정밀":
            continue
        규 = r["모든갈래가맞는규칙"]
        칸 = sum(v["칸"] for v in r["갈래"].values())
        ieee = sum(v["IEEE와같음"] for v in r["갈래"].values())
        if 규:
            print(f"  {이름표[op]} 경계 {칸}칸 (IEEE 와 같음 {ieee}) → 모두 맞는 규칙 {len(규)}: " + " | ".join(규))
        else:
            b = r["가장가까운규칙"]
            print(f"  {이름표[op]} 경계 {칸}칸 (IEEE 와 같음 {ieee}) → 모두 맞는 규칙 없음 · 가장 가까움 {b['규칙']} {b['맞음']}/{b['칸']}")
            for cat, v in r["갈래"].items():
                print(f"      {cat}: {v['칸']}칸 · 모두 맞는 규칙 {len(v['모두맞는규칙'])}")
    for op, cats in res.get("정밀", {}).items():
        print(f"  {이름표[op]}: " + " · ".join(f"{cat} {v['칸']}칸 다름 {v['다름']}" + (f" (ULP {v['ULP차분포']})" if v["다름"] else "")
                                         for cat, v in cats.items()))


def main():
    out_path = sys.argv[1] if len(sys.argv) > 1 else None
    t0 = time.time()
    print("시험 자료 · CPU 기준 계산 중 …", flush=True)
    경계 = 경계자료()
    경계기준 = {op: {r: {cat: [bits(기준(op, a, b, c, r)) for a, b, c in cases] for cat, cases in cats.items()} for r in 규칙들(op == "fma")}
             for op, cats in 경계.items()}
    정밀 = 정밀자료()
    print(f"  경계 {sum(len(x) for c in 경계.values() for x in c.values())}칸 · 정밀 "
          f"{sum(len(v[0]) for c in 정밀.values() for v in c.values())}칸 · {time.time() - t0:.0f}초", flush=True)
    report = {"Vulkan": [], "CUDA": None, "경계자료수": {op: {cat: len(x) for cat, x in cats.items()} for op, cats in 경계.items()},
              "정밀자료수": {op: {cat: len(v[0]) for cat, v in cats.items()} for op, cats in 정밀.items()}}
    v = V.Vk()
    for pd in v.pds:
        p = v.props(pd)
        info = {k: p[k] for k in ("name", "api", "driver_raw", "vendor", "denorm_preserve_f32", "denorm_ftz_f32", "signed_zero_inf_nan_f32",
                                  "rte_f32", "denorm_independence")}
        modes = [("기본", None, False)]
        if p["signed_zero_inf_nan_f32"]:
            modes.append(("기본+SignedZeroInfNanPreserve", None, True))
        if p["denorm_preserve_f32"]:
            modes.append(("보존(DenormPreserve)", "preserve", False))
        if p["denorm_ftz_f32"]:
            modes.append(("버림(DenormFlushToZero)", "ftz", False))
        dev = V.Device(v, pd)
        info["실행"] = {}
        for label, dm, szp in modes:
            try:
                res = 견주기(lambda op, A, B, C: run_vk(dev, op, A, B, C, dm, szp), 경계, 경계기준, 정밀)
            except Exception as e:  # noqa: BLE001
                info["실행"][label] = {"오류": str(e)}
                print(f"\n== {p['name']} · {label}: 오류 {e}")
                continue
            info["실행"][label] = res
            알리기(f"{p['name']} (Vulkan {p['api']}) · {label}", res)
        dev.close()
        report["Vulkan"].append(info)
    try:
        cu = Cuda()
        report["CUDA"] = {"name": cu.name, "driver": cu.driver, "실행": {}}
        for label, z in (("PTX", ""), ("PTX .ftz", "_ftz")):
            res = 견주기(lambda op, A, B, C: cu.run("k_" + op + (z if op != "half" else ""), A, B, C), 경계, 경계기준, 정밀)
            report["CUDA"]["실행"][label] = res
            알리기(f"{cu.name} (CUDA 드라이버 {cu.driver}) · {label}", res)
    except Exception as e:  # noqa: BLE001
        report["CUDA"] = {"오류": str(e)}
        print("\nCUDA: 오류", e)
    report["경계자료"] = {op: {cat: [[hex(bits(x)) for x in t] for t in cases] for cat, cases in cats.items()} for op, cats in 경계.items()}
    if out_path:
        json.dump(report, open(out_path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        print("\n결과 →", out_path)
    print(f"걸린 시간 {time.time() - t0:.0f}초")


if __name__ == "__main__":
    main()
