"""31단계 탐침 셋(31f) — SPIR-V 뒷단이 쓸 셈을 미리 확인한다. 연산 하나씩을 경계값과 무작위 값으로 이 PC 의 Vulkan 장치 모두와
   CUDA PTX(.ftz — GeulPU 커널의 길)에서 돌려 비트로 견준다. 기준은 PTX 이고, 나눗셈 · 제곱근 · 정수 → 실수 · 정수 내적은 CPU 의
   정확한 셈(유리수 · 정수)과도 견준다.
   - 큰쪽: GLSL NMax · FMax 가 PTX max.ftz 와 같은가(비정규수 입력 · NaN · ±0).
   - 비교 여섯(같음 · 다름 · 작음 · 큼 · 작거나같음 · 크거나같음): setp.*.ftz 와 같은가(비정규수 입력을 0 으로 보는가).
   - 부호반전: OpFNegate 가 neg.ftz 와 같은가.
   - 정수 → 짧은실수: OpConvertSToF(64 · 32 비트) · OpConvertUToF(64 비트)가 바른 반올림(같으면 짝수)인가.
   - 짧은실수 → 정수: 뒷단의 차례(넘치면 끝값으로 · NaN 은 0 — PTX 의 포화와 같게)가 cvt.rzi.ftz · cvt.rni.ftz 와 같은가.
   - 정수 내적: OpSDot · OpSUDot(+ c)이 dp4a.s32.s32 · dp4a.s32.u32 와 같은가.
   - 나눗셈 · 제곱근: 뒷단이 짤 규칙 R 의 바른 반올림 차례가 div.rn.ftz · sqrt.rn.ftz · CPU 기준과 같은가.
   - 뒷단의 대책: 큰쪽 · 부호반전 · 비교의 입력을 정수 셈으로 직접 버리는 판(maxflushN · maxflushF · negflush · cmp6flush),
     장치 컴파일러가 상수를 접는지(fma0 = 곱해더하기(a, b, +0) · add0 = a + 0 · mul1 = a · 1 — 접으면 −0 · 비정규수가 남는다).
   Intel 은 기본 · 버림 모드(DenormFlushToZero), NVIDIA 는 기본(버림 모드를 고를 수 없다) — 각각 SignedZeroInfNanPreserve 없이 · 있이.
   python -X utf8 탐침31_셋.py [결과.json]"""
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
from 탐침31 import bits, round_f32  # noqa: E402
import 탐침31_셈 as P2  # noqa: E402

MNF = 2.0 ** -126
GLSL_FMax, GLSL_NMax, GLSL_RoundEven, GLSL_Sqrt, GLSL_Fma = 40, 80, 2, 31, 50


def fb(u):
    return struct.unpack("<f", struct.pack("<I", u & 0xFFFFFFFF))[0]


# ---------------- SPIR-V: 원소마다 커널을 짜는 작은 도구 ----------------
class K:
    """입력 A · B · C (uint 비트), 출력 O0 · O1 (uint). 일꾼 묶음 64. body(k) 가 k.out0 · k.out1 을 채운다."""
    Op = dict(SDot=4450, SUDot=4452, FNegate=127, SNegate=126, IAdd=128, FAdd=129, ISub=130, FSub=131, IMul=132, FMul=133, UDiv=134,
              FDiv=136, Select=169, IEqual=170, INotEqual=171, UGreaterThan=172, SGreaterThan=173, UGreaterThanEqual=174,
              SGreaterThanEqual=175, ULessThan=176, SLessThan=177, ULessThanEqual=178, SLessThanEqual=179, FOrdEqual=180,
              FUnordNotEqual=183, FOrdLessThan=184, FOrdGreaterThan=186, FOrdLessThanEqual=188, FOrdGreaterThanEqual=190,
              ShiftRightLogical=194, ShiftRightArithmetic=195, ShiftLeftLogical=196, BitwiseOr=197, BitwiseXor=198, BitwiseAnd=199,
              Not=200, LogicalOr=166, LogicalAnd=167, LogicalNot=168, ConvertFToU=109, ConvertFToS=110, ConvertSToF=111,
              ConvertUToF=112, UConvert=113, SConvert=114, Bitcast=124, CompositeExtract=81)

    def __init__(self, denorm=None, dot=False, int64=False, szp=False):
        m = spv.Module()
        self.m = m
        I = m.ins
        I(m.caps, spv.OpCapability, spv.CapShader)
        if int64:
            I(m.caps, spv.OpCapability, 11)                           # Int64
        if dot:
            for c in (6019, 6018):                                    # DotProduct · DotProductInput4x8BitPacked
                I(m.caps, spv.OpCapability, c)
        if denorm or szp:
            I(m.exts, spv.OpExtension, spv._str("SPV_KHR_float_controls"))
        if denorm:
            I(m.caps, spv.OpCapability, spv.CapDenormPreserve if denorm == "preserve" else spv.CapDenormFlushToZero)
        if szp:
            I(m.caps, spv.OpCapability, spv.CapSignedZeroInfNanPreserve)
        self.glsl = m.id()
        I(m.imports, spv.OpExtInstImport, self.glsl, spv._str("GLSL.std.450"))
        I(m.memmodel, spv.OpMemoryModel, 0, 1)
        tv, tfn, self.tb, self.tu, self.ti, self.tf, tv3 = (m.id() for _ in range(7))
        I(m.types, spv.OpTypeVoid, tv)
        I(m.types, spv.OpTypeFunction, tfn, tv)
        I(m.types, spv.OpTypeBool, self.tb)
        I(m.types, spv.OpTypeInt, self.tu, 32, 0)
        I(m.types, spv.OpTypeInt, self.ti, 32, 1)
        I(m.types, spv.OpTypeFloat, self.tf, 32)
        I(m.types, spv.OpTypeVector, tv3, self.tu, 3)
        if int64:
            self.tu64, self.ti64 = m.id(), m.id()
            I(m.types, spv.OpTypeInt, self.tu64, 64, 0)
            I(m.types, spv.OpTypeInt, self.ti64, 64, 1)
        pin = m.id()
        I(m.types, spv.OpTypePointer, pin, spv.SCInput, tv3)
        ra, st, pst, pu = m.id(), m.id(), m.id(), m.id()
        I(m.types, spv.OpTypeRuntimeArray, ra, self.tu)
        I(m.types, spv.OpTypeStruct, st, ra)
        I(m.types, spv.OpTypePointer, pst, spv.SCStorageBuffer, st)
        I(m.types, spv.OpTypePointer, pu, spv.SCStorageBuffer, self.tu)
        I(m.decos, spv.OpDecorate, ra, spv.DecArrayStride, 4)
        I(m.decos, spv.OpDecorate, st, spv.DecBlock)
        I(m.decos, spv.OpMemberDecorate, st, 0, spv.DecOffset, 0)
        self.consts = {}
        gid = m.id()
        I(m.globals_, spv.OpVariable, pin, gid, spv.SCInput)
        I(m.decos, spv.OpDecorate, gid, spv.DecBuiltIn, spv.BuiltInGlobalInvocationId)
        bufs = []
        for b in range(5):
            v = m.id()
            I(m.globals_, spv.OpVariable, pst, v, spv.SCStorageBuffer)
            I(m.decos, spv.OpDecorate, v, spv.DecDescriptorSet, 0)
            I(m.decos, spv.OpDecorate, v, spv.DecBinding, b)
            bufs.append(v)
        main = m.id()
        I(m.entries, spv.OpEntryPoint, 5, main, spv._str("main"), gid, *bufs)   # SPIR-V 1.4 부터 쓰는 전역 변수 모두
        I(m.modes, spv.OpExecutionMode, main, spv.ExecModeLocalSize, 64, 1, 1)
        if denorm:
            I(m.modes, spv.OpExecutionMode, main, spv.ExecModeDenormPreserve if denorm == "preserve" else spv.ExecModeDenormFlushToZero, 32)
        if szp:
            I(m.modes, spv.OpExecutionMode, main, spv.ExecModeSignedZeroInfNanPreserve, 32)
        self.B = m.body
        I(self.B, spv.OpFunction, tv, main, 0, tfn)
        I(self.B, spv.OpLabel, m.id())
        idx = self.op(self.Op["CompositeExtract"], self.tu, self.op(spv.OpLoad, tv3, gid), 0)
        self.ptr = [self.op(spv.OpAccessChain, pu, bufs[k], self.cu(0), idx) for k in range(5)]
        self.a, self.b, self.c = (self.op(spv.OpLoad, self.tu, self.ptr[k]) for k in range(3))
        self.out0 = self.out1 = None

    def finish(self):
        I = self.m.ins
        for k, v in ((3, self.out0), (4, self.out1)):
            if v is not None:
                I(self.B, spv.OpStore, self.ptr[k], v)
        I(self.B, spv.OpReturn)
        I(self.B, spv.OpFunctionEnd)
        return self.m.binary(0x00010600)

    def op(self, o, t, *args):
        r = self.m.id()
        self.m.ins(self.B, o, t, r, *args)
        return r

    def _const(self, t, words, key):
        if key not in self.consts:
            self.consts[key] = self.m.id()
            self.m.ins(self.m.types, spv.OpConstant, t, self.consts[key], *words)
        return self.consts[key]

    def cu(self, v):
        return self._const(self.tu, [v & 0xFFFFFFFF], ("u", v & 0xFFFFFFFF))

    def ci(self, v):
        return self._const(self.ti, [v & 0xFFFFFFFF], ("i", v & 0xFFFFFFFF))

    def cf(self, x):
        u = bits(x) if isinstance(x, float) else x
        return self._const(self.tf, [u], ("f", u))

    def cu64(self, v):
        return self._const(self.tu64, [v & 0xFFFFFFFF, (v >> 32) & 0xFFFFFFFF], ("u64", v & (2 ** 64 - 1)))

    # 줄임말
    def u2f(self, x):
        return self.op(self.Op["Bitcast"], self.tf, x)

    def f2u(self, x):
        return self.op(self.Op["Bitcast"], self.tu, x)

    def u2i(self, x):
        return self.op(self.Op["Bitcast"], self.ti, x)

    def i2u(self, x):
        return self.op(self.Op["Bitcast"], self.tu, x)

    def ib(self, name, a, b, t=None):
        return self.op(self.Op[name], t or self.tu, a, b)

    def cmp(self, name, a, b):
        return self.op(self.Op[name], self.tb, a, b)

    def sel(self, c, x, y, t=None):
        return self.op(self.Op["Select"], t or self.tu, c, x, y)

    def nc(self, r):                                    # NoContraction — 곱 · 더하기를 FMA 로 합치지 못하게
        self.m.ins(self.m.decos, spv.OpDecorate, r, spv.DecNoContraction)
        return r

    def fop(self, name, a, b):
        return self.nc(self.op(self.Op[name], self.tf, a, b))

    def fma(self, a, b, c):
        return self.op(spv.OpExtInst, self.tf, self.glsl, GLSL_Fma, a, b, c)

    def ext(self, n, t, *args):
        return self.op(spv.OpExtInst, t, self.glsl, n, *args)

    def land(self, a, b):
        return self.op(self.Op["LogicalAnd"], self.tb, a, b)

    def lor(self, a, b):
        return self.op(self.Op["LogicalOr"], self.tb, a, b)

    def lnot(self, a):
        return self.op(self.Op["LogicalNot"], self.tb, a)


# ---- 뒷단이 쓸 차례: 규칙 R 의 나눗셈 (짧은실수 a / b) ----
def r_div(k, ua, ub):
    """정규수의 가수 A, B ∈ [1, 2) 의 몫 q = RN24(A / B) 를 FMA 로 구하고(뉴턴 한 번 + 남은 몫 둘 — 마지막 남은 몫은 정확),
    반올림 방향을 정확한 비교(2r vs B · ulp)로 가린 뒤 지수를 붙인다. 2⁻¹²⁶ 아래 → 부호를 지킨 0, 넘치면 무한. 특별한 값은 따로."""
    ea = k.ib("BitwiseAnd", k.ib("ShiftRightLogical", ua, k.cu(23)), k.cu(255))
    eb = k.ib("BitwiseAnd", k.ib("ShiftRightLogical", ub, k.cu(23)), k.cu(255))
    ma = k.ib("BitwiseAnd", ua, k.cu(0x7FFFFF))
    mb = k.ib("BitwiseAnd", ub, k.cu(0x7FFFFF))
    s = k.ib("BitwiseAnd", k.ib("BitwiseXor", ua, ub), k.cu(0x80000000))
    A = k.u2f(k.ib("BitwiseOr", ma, k.cu(0x3F800000)))
    B = k.u2f(k.ib("BitwiseOr", mb, k.cu(0x3F800000)))
    nB = k.op(k.Op["FNegate"], k.tf, B)
    one = k.cf(1.0)
    y0 = k.fop("FDiv", one, B)
    e0 = k.fma(nB, y0, one)
    y1 = k.fma(e0, y0, y0)
    q0 = k.fop("FMul", A, y1)
    r0 = k.fma(nB, q0, A)
    q1 = k.fma(r0, y1, q0)
    r1 = k.fma(nB, q1, A)                                          # 정확(q1 이 충실하므로)
    qb = k.f2u(q1)
    u = k.u2f(k.ib("ISub", k.ib("BitwiseAnd", qb, k.cu(0x7F800000)), k.cu(23 << 23)))     # ulp(q1)
    Bu = k.fop("FMul", B, u)                                       # 정확(2 의 거듭제곱 배)
    r2 = k.fop("FAdd", r1, r1)                                     # 정확
    pow2 = k.cmp("IEqual", k.ib("BitwiseAnd", qb, k.cu(0x7FFFFF)), k.cu(0))
    Bud = k.sel(pow2, k.fop("FMul", Bu, k.cf(0.5)), Bu, k.tf)
    zero = k.cf(0.0)
    up = k.land(k.cmp("FOrdGreaterThan", r1, zero), k.cmp("FOrdGreaterThan", r2, Bu))
    dn = k.land(k.cmp("FOrdLessThan", r1, zero), k.cmp("FOrdGreaterThan", k.op(k.Op["FNegate"], k.tf, r2), Bud))
    qb2 = k.sel(up, k.ib("IAdd", qb, k.cu(1)), k.sel(dn, k.ib("ISub", qb, k.cu(1)), qb))
    qe2 = k.ib("ShiftRightLogical", qb2, k.cu(23))                 # 126 · 127 (부호 0)
    ne = k.ib("ISub", k.ib("IAdd", k.u2i(qe2), k.u2i(ea), k.ti), k.u2i(eb), k.ti)
    res = k.ib("BitwiseOr", k.ib("BitwiseOr", s, k.ib("ShiftLeftLogical", k.i2u(ne), k.cu(23))), k.ib("BitwiseAnd", qb2, k.cu(0x7FFFFF)))
    under = k.cmp("SLessThanEqual", ne, k.ci(0))
    over = k.cmp("SGreaterThanEqual", ne, k.ci(255))
    sinf = k.ib("BitwiseOr", s, k.cu(0x7F800000))
    res = k.sel(under, s, k.sel(over, sinf, res))
    aZ, bZ = k.cmp("IEqual", ea, k.cu(0)), k.cmp("IEqual", eb, k.cu(0))
    aE, bE = k.cmp("IEqual", ea, k.cu(255)), k.cmp("IEqual", eb, k.cu(255))
    aI = k.land(aE, k.cmp("IEqual", ma, k.cu(0)))
    bI = k.land(bE, k.cmp("IEqual", mb, k.cu(0)))
    aN = k.land(aE, k.cmp("INotEqual", ma, k.cu(0)))
    bN = k.land(bE, k.cmp("INotEqual", mb, k.cu(0)))
    nan = k.lor(k.lor(aN, bN), k.lor(k.land(aZ, bZ), k.land(aI, bI)))
    inf = k.lor(aI, bZ)
    zer = k.lor(aZ, bI)
    return k.sel(nan, k.cu(0x7FFFFFFF), k.sel(inf, sinf, k.sel(zer, s, res)))


# ---- 뒷단이 쓸 차례: 규칙 R 의 제곱근 ----
def r_sqrt(k, ux):
    """X ∈ [1, 4) (지수의 홀짝으로 맞춤)의 √X 를 GLSL Sqrt 로 어림한 뒤, 정수 Y(= √X · 2²³ 의 가까운 정수)를 64 비트 정수 비교
    (2Y ± 1)² vs 4N (N = X · 2⁴⁶) 로 세 번 바로잡는다 — 바른 반올림(같은 값은 생기지 않는다). 비정규수 입력은 부호를 지킨 0."""
    ex = k.ib("BitwiseAnd", k.ib("ShiftRightLogical", ux, k.cu(23)), k.cu(255))
    mx = k.ib("BitwiseAnd", ux, k.cu(0x7FFFFF))
    sx = k.ib("BitwiseAnd", ux, k.cu(0x80000000))
    E = k.ib("ISub", k.u2i(ex), k.ci(127), k.ti)
    odd = k.i2u(k.ib("BitwiseAnd", E, k.ci(1), k.ti))
    X = k.u2f(k.ib("BitwiseOr", k.sel(k.cmp("IEqual", odd, k.cu(1)), k.cu(0x40000000), k.cu(0x3F800000)), mx))
    half = k.ib("ShiftRightArithmetic", k.ib("ISub", E, k.u2i(odd), k.ti), k.ci(1), k.ti)
    y0 = k.ext(GLSL_Sqrt, k.tf, X)
    Y = k.op(k.Op["UConvert"], k.tu64, k.op(k.Op["ConvertFToU"], k.tu, k.fop("FMul", y0, k.cf(8388608.0))))
    Xm = k.op(k.Op["UConvert"], k.tu64, k.ib("ShiftLeftLogical", k.ib("BitwiseOr", mx, k.cu(0x800000)), odd))
    N4 = k.ib("ShiftLeftLogical", Xm, k.cu64(25), k.tu64)                     # 4N = Xm · 2²⁵
    one64, two64 = k.cu64(1), k.cu64(2)
    for _ in range(3):
        t = k.ib("IAdd", k.ib("IMul", Y, two64, k.tu64), one64, k.tu64)     # 2Y + 1
        upc = k.cmp("ULessThan", k.ib("IMul", t, t, k.tu64), N4)
        Y = k.sel(upc, k.ib("IAdd", Y, one64, k.tu64), Y, k.tu64)
        t2 = k.ib("ISub", k.ib("IMul", Y, two64, k.tu64), one64, k.tu64)    # 2Y − 1
        dnc = k.cmp("UGreaterThan", k.ib("IMul", t2, t2, k.tu64), N4)
        Y = k.sel(dnc, k.ib("ISub", Y, one64, k.tu64), Y, k.tu64)
    Y32 = k.op(k.Op["UConvert"], k.tu, Y)
    big = k.cmp("IEqual", Y32, k.cu(1 << 24))
    e2 = k.i2u(k.ib("IAdd", half, k.sel(big, k.ci(128), k.ci(127), k.ti), k.ti))
    res = k.ib("BitwiseOr", k.ib("ShiftLeftLogical", e2, k.cu(23)), k.sel(big, k.cu(0), k.ib("BitwiseAnd", Y32, k.cu(0x7FFFFF))))
    zero = k.cmp("IEqual", ex, k.cu(0))
    neg = k.land(k.cmp("INotEqual", sx, k.cu(0)), k.lnot(zero))
    nan = k.land(k.cmp("IEqual", ex, k.cu(255)), k.cmp("INotEqual", mx, k.cu(0)))
    pinf = k.cmp("IEqual", ux, k.cu(0x7F800000))
    return k.sel(zero, sx, k.sel(k.lor(neg, nan), k.cu(0x7FFFFFFF), k.sel(pinf, ux, res)))


# ---- 뒷단이 쓸 차례: 비정규수 버림(정수 셈 — 장치의 실수 셈에 기대지 않는다) · NaN 검사(정수 셈 — 실수 비교는 최적화로 사라질 수 있다) ----
def flush(k, x):
    u = k.f2u(x)
    sub = k.cmp("IEqual", k.ib("BitwiseAnd", u, k.cu(0x7F800000)), k.cu(0))
    return k.u2f(k.sel(sub, k.ib("BitwiseAnd", u, k.cu(0x80000000)), u))


def isnan_i(k, x):
    return k.cmp("UGreaterThan", k.ib("BitwiseAnd", k.f2u(x), k.cu(0x7FFFFFFF)), k.cu(0x7F800000))


# ---- 뒷단이 쓸 차례: 짧은실수 → 32 비트 정수(0 쪽으로 자름 / 가까운 쪽) — PTX 처럼 넘치면 끝값, NaN 은 0 ----
def f_to_i32(k, x, rni):
    if rni:
        x = k.ext(GLSL_RoundEven, k.tf, x)
    lo, hi = k.cf(-2147483648.0), k.cf(2147483520.0)              # 2147483520 = 2³¹ 아래 가장 큰 짧은실수
    c = k.ext(GLSL_NMax, k.tf, k.ext(37 + 42, k.tf, x, hi), lo)    # NMin(x, hi) 다음 NMax(·, lo)
    r = k.i2u(k.op(k.Op["ConvertFToS"], k.ti, c))
    isnan = isnan_i(k, x)
    toobig = k.cmp("FOrdGreaterThanEqual", x, k.cf(2147483648.0))
    return k.sel(isnan, k.cu(0), k.sel(toobig, k.cu(0x7FFFFFFF), r))


KERNELS = {}


def kernel(name, denorm, szp=False):
    key = (name, denorm, szp)
    if key in KERNELS:
        return KERNELS[key]
    dot = name in ("sdot", "sudot")
    i64 = name in ("i64tof", "u64tof", "sqrt")
    k = K(denorm, dot=dot, int64=i64, szp=szp)
    a, b, c = k.a, k.b, k.c
    fa, fbv = k.u2f(a), k.u2f(b)
    if name == "nmax":
        k.out0 = k.f2u(k.ext(GLSL_NMax, k.tf, fa, fbv))
    elif name == "fmax":
        k.out0 = k.f2u(k.ext(GLSL_FMax, k.tf, fa, fbv))
    elif name == "neg":
        k.out0 = k.f2u(k.op(k.Op["FNegate"], k.tf, fa))
    elif name == "maxflushN":
        k.out0 = k.f2u(k.ext(GLSL_NMax, k.tf, flush(k, fa), flush(k, fbv)))
    elif name == "maxflushF":
        k.out0 = k.f2u(k.ext(GLSL_FMax, k.tf, flush(k, fa), flush(k, fbv)))
    elif name == "negflush":
        k.out0 = k.f2u(k.op(k.Op["FNegate"], k.tf, flush(k, fa)))
    elif name == "cmp6flush":
        acc = k.cu(0)
        x, y = flush(k, fa), flush(k, fbv)
        for j, cn in enumerate(("FOrdEqual", "FUnordNotEqual", "FOrdLessThan", "FOrdGreaterThan", "FOrdLessThanEqual",
                                "FOrdGreaterThanEqual")):
            acc = k.ib("BitwiseOr", acc, k.sel(k.cmp(cn, x, y), k.cu(1 << j), k.cu(0)))
        k.out0 = acc
    elif name == "fma0":                                    # c 가 상수 +0 — 장치가 fma(a, b, 0) → a · b 로 접으면 −0 이 남는다
        k.out0 = k.f2u(k.fma(fa, fbv, k.cf(0.0)))
    elif name == "add0":
        k.out0 = k.f2u(k.fop("FAdd", fa, k.cf(0.0)))
    elif name == "mul1":                                    # x · 1 — 접으면 비정규수가 남는다
        k.out0 = k.f2u(k.fop("FMul", fa, k.cf(1.0)))
    elif name == "cmp6":
        acc = k.cu(0)
        for j, cn in enumerate(("FOrdEqual", "FUnordNotEqual", "FOrdLessThan", "FOrdGreaterThan", "FOrdLessThanEqual",
                                "FOrdGreaterThanEqual")):
            acc = k.ib("BitwiseOr", acc, k.sel(k.cmp(cn, fa, fbv), k.cu(1 << j), k.cu(0)))
        k.out0 = acc
    elif name == "i64tof":
        v = k.ib("BitwiseOr", k.op(k.Op["UConvert"], k.tu64, a), k.ib("ShiftLeftLogical", k.op(k.Op["UConvert"], k.tu64, b), k.cu64(32),
                                                                       k.tu64), k.tu64)
        k.out0 = k.f2u(k.op(k.Op["ConvertSToF"], k.tf, k.op(k.Op["Bitcast"], k.ti64, v)))
    elif name == "u64tof":
        v = k.ib("BitwiseOr", k.op(k.Op["UConvert"], k.tu64, a), k.ib("ShiftLeftLogical", k.op(k.Op["UConvert"], k.tu64, b), k.cu64(32),
                                                                       k.tu64), k.tu64)
        k.out0 = k.f2u(k.op(k.Op["ConvertUToF"], k.tf, v))
    elif name == "i32tof":
        k.out0 = k.f2u(k.op(k.Op["ConvertSToF"], k.tf, k.u2i(a)))
    elif name == "ftoi":
        k.out0 = f_to_i32(k, fa, False)
    elif name == "rni":
        k.out0 = f_to_i32(k, fa, True)
    elif name == "sdot":
        k.out0 = k.ib("IAdd", k.op(k.Op["SDot"], k.ti, a, b, 0), k.u2i(c), k.ti)
        k.out0 = k.i2u(k.out0)
    elif name == "sudot":
        k.out0 = k.i2u(k.ib("IAdd", k.op(k.Op["SUDot"], k.ti, a, b, 0), k.u2i(c), k.ti))
    elif name == "div":
        k.out0 = r_div(k, a, b)
    elif name == "sqrt":
        k.out0 = r_sqrt(k, a)
    else:
        raise ValueError(name)
    KERNELS[key] = k.finish()
    return KERNELS[key]


# ---------------- PTX(.ftz) ----------------
PTX_OPS = {"nmax": "max.ftz.f32 %f4, %f1, %f2; mov.b32 %r11, %f4;", "fmax": "max.ftz.f32 %f4, %f1, %f2; mov.b32 %r11, %f4;", "neg": "neg.ftz.f32 %f4, %f1; mov.b32 %r11, %f4;",
           "cmp6": None, "i64tof": "cvt.rn.f32.s64 %f4, %rd10; mov.b32 %r11, %f4;", "u64tof": "cvt.rn.f32.u64 %f4, %rd10; mov.b32 %r11, %f4;",
           "i32tof": "cvt.rn.f32.s32 %f4, %r10; mov.b32 %r11, %f4;", "ftoi": "cvt.rzi.ftz.s32.f32 %r11, %f1;",
           "rni": "cvt.rni.ftz.s32.f32 %r11, %f1;", "sdot": "dp4a.s32.s32 %r11, %r10, %r9, %r8;",
           "sudot": "dp4a.s32.u32 %r11, %r10, %r9, %r8;", "div": "div.rn.ftz.f32 %f4, %f1, %f2; mov.b32 %r11, %f4;",
           "sqrt": "sqrt.rn.ftz.f32 %f4, %f1; mov.b32 %r11, %f4;",
           "maxflushN": "max.ftz.f32 %f4, %f1, %f2; mov.b32 %r11, %f4;", "maxflushF": "max.ftz.f32 %f4, %f1, %f2; mov.b32 %r11, %f4;",
           "negflush": "neg.ftz.f32 %f4, %f1; mov.b32 %r11, %f4;", "cmp6flush": None,
           "fma0": "mov.f32 %f3, 0f00000000; fma.rn.ftz.f32 %f4, %f1, %f2, %f3; mov.b32 %r11, %f4;",
           "add0": "mov.f32 %f3, 0f00000000; add.rn.ftz.f32 %f4, %f1, %f3; mov.b32 %r11, %f4;",
           "mul1": "mov.f32 %f3, 0f3F800000; mul.rn.ftz.f32 %f4, %f1, %f3; mov.b32 %r11, %f4;"}
CMP6 = "".join(f"setp.{c}.ftz.f32 %p1, %f1, %f2; selp.u32 %r7, {1 << j}, 0, %p1; or.b32 %r11, %r11, %r7; "
               for j, c in enumerate(("eq", "neu", "lt", "gt", "le", "ge")))
PTX_KERNEL = """
.visible .entry k_@NAME@(.param .u64 pa, .param .u64 pb, .param .u64 pc, .param .u64 po)
{
    .reg .pred %p<3>;
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
    ld.global.b32 %r9, [%rd7];
    ld.global.b32 %r8, [%rd8];
    mov.b32 %f1, %r10;
    mov.b32 %f2, %r9;
    mov.b64 %rd10, {%r10, %r9};
    mov.u32 %r11, 0;
    @OP@
    st.global.b32 [%rd9], %r11;
    ret;
}
"""


def ptx_source():
    parts = [".version 7.4\n.target sm_80\n.address_size 64\n"]
    for op, ins in PTX_OPS.items():
        if op in ("cmp6", "cmp6flush"):
            ins = CMP6
        if ins is None:
            continue
        parts.append(PTX_KERNEL.replace("@NAME@", op).replace("@OP@", ins))
    return "".join(parts)


class Dev(V.Device):
    """장치 — 뒷단이 쓸 기능(64 비트 정수 · 정수 내적)을 켜서 만든다"""

    def __init__(self, v, pd):
        self.v, self.pd = v, pd
        n = V.U32()
        V.vk.vkGetPhysicalDeviceQueueFamilyProperties(pd, ctypes.byref(n), None)
        qf = (V.QueueFamilyProps * n.value)()
        V.vk.vkGetPhysicalDeviceQueueFamilyProperties(pd, ctypes.byref(n), qf)
        self.qfi = next(i for i, q in enumerate(qf) if q.queueFlags & 2)
        prio = (ctypes.c_float * 1)(1.0)
        qci = V.DeviceQueueCI(2, None, 0, self.qfi, 1, prio)
        f13 = (ctypes.c_ubyte * (16 + 15 * 4))()
        struct.pack_into("<I", f13, 0, 53)                                   # VULKAN_1_3_FEATURES
        struct.pack_into("<I", f13, 16 + 4 * 13, 1)                          # shaderIntegerDotProduct
        f2 = (ctypes.c_ubyte * (16 + 55 * 4 + 4))()
        struct.pack_into("<IxxxxQ", f2, 0, 1000059000, ctypes.addressof(f13))
        struct.pack_into("<I", f2, 16 + 4 * 40, 1)                           # shaderInt64
        self._keep = (f13, f2)
        dci = V.DeviceCI(3, ctypes.addressof(f2), 0, 1, ctypes.pointer(qci), 0, None, 0, None, None)
        self.dev = ctypes.c_void_p()
        V.check(V.vk.vkCreateDevice(pd, ctypes.byref(dci), None, ctypes.byref(self.dev)), "vkCreateDevice")
        self.queue = ctypes.c_void_p()
        V.vk.vkGetDeviceQueue(self.dev, self.qfi, 0, ctypes.byref(self.queue))
        self.mp = V.MemProps()
        V.vk.vkGetPhysicalDeviceMemoryProperties(pd, ctypes.byref(self.mp))
        self.objs = []


class Cuda(P2.Cuda):
    def __init__(self):
        P2.ptx_source = ptx_source                     # 탐침 둘의 CUDA 틀에 이 탐침의 커널을
        super().__init__()


# ---------------- 시험 자료 ----------------
def 특별값():
    xs = [0.0, -0.0, 2.0 ** -149, -(2.0 ** -149), 2.0 ** -127, -(2.0 ** -127), fb(0x007FFFFF), fb(0x807FFFFF), fb(0x00400001),
          MNF, -MNF, fb(0x00800001), 1.0, -1.0, 1.5, -2.5, 3.0e38, -3.0e38, fb(0x7F7FFFFF), fb(0xFF7FFFFF), math.inf, -math.inf]
    us = [bits(x) for x in xs] + [0x7FC00000, 0xFFC00000, 0x7F800001, 0x7FFFFFFF]       # NaN 넷
    return us


def 무작위비트(rng, n):
    """지수가 고르게(비정규수 · 0 근처 많이) 퍼진 짧은실수 비트"""
    out = []
    for _ in range(n):
        r = rng.random()
        if r < 0.25:
            u = rng.getrandbits(23) | (rng.getrandbits(1) << 31)                          # 비정규수 · 0
        elif r < 0.5:
            u = ((rng.randint(1, 8)) << 23) | rng.getrandbits(23) | (rng.getrandbits(1) << 31)   # 막 정규수 둘레
        else:
            u = rng.getrandbits(32)
        out.append(u)
    return out


def 정수64(rng, n, signed=True):
    out = []
    for i in range(n):
        L = rng.randint(1, 63 if signed else 64)
        x = rng.getrandbits(L) | (1 << (L - 1))
        if L > 25 and i % 3 == 0:                          # 한가운데: 24 비트 아래를 정확히 100…0 (같으면 짝수)
            sh = L - 25
            x = ((x >> sh) | 1) << sh
            x += rng.choice((-1, 0, 0, 1))
        if signed and rng.random() < 0.5:
            x = -x
        x &= (1 << 64) - 1
        out.append((x & 0xFFFFFFFF, x >> 32))
    out += [(0, 0), (1, 0), (0xFFFFFFFF, 0xFFFFFFFF), (0, 0x80000000), (0xFFFFFFFF, 0x7FFFFFFF)]
    return out


def 실수정수범위(rng, n):
    out = []
    for i in range(n):
        r = rng.random()
        if r < 0.3:
            x = rng.randint(-(2 ** 30), 2 ** 30) + rng.choice((0.5, -0.5, 0.25, 0.75, 0.0))
        elif r < 0.6:
            x = math.ldexp(rng.random() * 2 - 1, rng.randint(-30, 31))
        else:
            x = math.ldexp(rng.random() * 2 - 1, rng.randint(-149, -100))
        out.append(bits(round_f32(Fraction(x)) if x != 0 else x))
    out += [bits(x) for x in (2147483520.0, -2147483648.0, 2147483648.0, -2147483904.0, 1e10, -1e10, math.inf, -math.inf)]
    out += [0x7FC00000, 0xFFC00000]
    return out


def 정확한변환(lo, hi, signed):
    v = lo | (hi << 32)
    if signed and v >= 1 << 63:
        v -= 1 << 64
    return bits(round_f32(Fraction(v)) if v else 0.0)


def 바이트넷(a, b, c, b_unsigned):
    s = 0
    for i in range(4):
        x = (a >> (8 * i)) & 255
        y = (b >> (8 * i)) & 255
        x = x - 256 if x >= 128 else x
        if not b_unsigned:
            y = y - 256 if y >= 128 else y
        s += x * y
    c = c - (1 << 32) if c >= 1 << 31 else c
    return (s + c) & 0xFFFFFFFF


def 자료():
    rng = random.Random(3134)
    D = {}
    sp = 특별값()
    pairs = [(x, y) for x in sp for y in sp]
    rnd = 무작위비트(rng, 200000)
    rpairs = list(zip(rnd[:100000], rnd[100000:]))
    for name in ("nmax", "fmax", "cmp6"):
        D[name] = {"특별값쌍": pairs, "무작위쌍": rpairs}
    D["neg"] = {"특별값": [(x, 0) for x in sp], "무작위": [(x, 0) for x in rnd[:100000]]}
    for name in ("maxflushN", "maxflushF", "cmp6flush"):
        D[name] = {"특별값쌍": pairs, "무작위쌍": rpairs}
    D["negflush"] = D["neg"]
    for name in ("fma0", "add0", "mul1"):
        D[name] = {"특별값쌍": pairs, "무작위쌍": rpairs[:50000]}
    D["i64tof"] = {"무작위·한가운데": 정수64(rng, 100000, True)}
    D["u64tof"] = {"무작위·한가운데": 정수64(rng, 100000, False)}
    D["i32tof"] = {"무작위": [(rng.getrandbits(32), 0) for _ in range(100000)]}
    fi = 실수정수범위(rng, 100000)
    D["ftoi"] = {"정수범위·작은값·끝": [(x, 0) for x in fi]}
    D["rni"] = {"정수범위·작은값·끝": [(x, 0) for x in fi]}
    D["sdot"] = {"무작위": [(rng.getrandbits(32), rng.getrandbits(32), rng.getrandbits(32)) for _ in range(100000)]}
    D["sudot"] = {"무작위": [(rng.getrandbits(32), rng.getrandbits(32), rng.getrandbits(32)) for _ in range(100000)]}
    # 나눗셈 · 제곱근: 탐침 둘의 경계 자료(규칙 R 을 가른 칸) · 정밀 자료(한가운데 근처 · 계약 모양) + 특별값 쌍 + 무작위
    경계 = P2.경계자료()
    정밀 = P2.정밀자료()
    dv = {"특별값쌍": pairs}
    for n, xs in 경계["div"].items():
        dv["경계 " + n] = [(bits(a), bits(b)) for a, b, _ in xs]
    for n, (A, B, _, _) in 정밀["div"].items():
        dv["정밀 " + n] = list(zip(A, B))
    dv["무작위 비트"] = rpairs
    지수끝 = []
    for _ in range(20000):                                 # 몫이 2⁻¹²⁶ · 2¹²⁸ 둘레
        a = P2.rf(rng, -126, 127)
        t = rng.choice((-127, -126, -125, 126, 127, 128))
        b = P2.rf(rng, max(-126, min(127, P2.지수(a) - t)), max(-126, min(127, P2.지수(a) - t)))
        지수끝.append((bits(a), bits(b)))
    dv["몫의 지수 끝"] = 지수끝
    D["div"] = dv
    sq = {"특별값": [(x, 0) for x in sp]}
    for n, xs in 경계["sqrt"].items():
        sq["경계 " + n] = [(bits(a), 0) for a, _, _ in xs]
    for n, (A, _, _, _) in 정밀["sqrt"].items():
        sq["정밀 " + n] = [(x, 0) for x in A]
    sq["무작위 비트"] = [(x, 0) for x in rnd[:100000]]
    D["sqrt"] = sq
    return D


# ---------------- CPU 기준 (나눗셈 · 제곱근 · 정수 → 실수 · 내적) ----------------
R규칙 = ("0(부호지킴)", "반올림뒤(지수무한)", "지킴", True)


def cpu(op, a, b, c):
    if op == "div":
        x, y = fb(a), fb(b)
        if math.isnan(x) or math.isnan(y):
            return None
        x0, y0 = P2.daz(x, "0(부호지킴)"), P2.daz(y, "0(부호지킴)")
        if (x0 == 0 and y0 == 0) or (math.isinf(x0) and math.isinf(y0)):
            return None                                     # NaN — 비트는 PTX 와만 견준다
        if math.isinf(x0) or y0 == 0:
            return bits(-math.inf if (bits(x0) ^ bits(y0)) >> 31 else math.inf)
        if math.isinf(y0):
            return bits(-0.0 if (bits(x0) ^ bits(y0)) >> 31 else 0.0)
        return bits(P2.기준("div", x, y, 0.0, R규칙))
    if op == "sqrt":
        x = fb(a)
        if math.isnan(x):
            return None
        x0 = P2.daz(x, "0(부호지킴)")
        if x0 == 0:
            return bits(x0)
        if x0 < 0:
            return None
        if math.isinf(x0):
            return bits(x0)
        return bits(P2.제곱근(x0))
    if op == "i64tof":
        return 정확한변환(a, b, True)
    if op == "u64tof":
        return 정확한변환(a, b, False)
    if op == "i32tof":
        v = a - (1 << 32) if a >= 1 << 31 else a
        return bits(round_f32(Fraction(v)) if v else 0.0)
    if op == "sdot":
        return 바이트넷(a, b, c, False)
    if op == "sudot":
        return 바이트넷(a, b, c, True)
    return None


# ---------------- 돌리기 ----------------
def run_vk(dev, name, denorm, rows, szp=False):
    n = len(rows)
    N = (n + 63) // 64 * 64
    cols = [[r[j] if j < len(r) else 0 for r in rows] + [0] * (N - n) for j in range(3)]
    bufs = [dev.buffer(P2.pack_u(col)) for col in cols] + [dev.buffer(b"\0" * (4 * N)), dev.buffer(b"\0" * (4 * N))]
    dev.run(kernel(name, denorm, szp), bufs, (N // 64, 1, 1))
    out = list(struct.unpack("<%dI" % N, ctypes.string_at(bufs[3][1], 4 * N)))[:n]
    dev.release()
    return out


def run_cuda(cu, name, rows):
    cols = [[r[j] if j < len(r) else 0 for r in rows] for j in range(3)]
    return cu.run("k_" + name, *cols)


def main():
    out_path = sys.argv[1] if len(sys.argv) > 1 else None
    t0 = time.time()
    D = 자료()
    print(f"자료: {sum(len(v) for d in D.values() for v in d.values()):,} 칸 ({time.time() - t0:.1f} 초)", flush=True)
    결과 = {"자료": {op: {k: len(v) for k, v in d.items()} for op, d in D.items()}, "장치": [], "판정": {}}
    cu = Cuda()
    결과["CUDA"] = {"장치": cu.name, "드라이버": cu.driver}
    ref = {op: {k: run_cuda(cu, op, rows) for k, rows in d.items()} for op, d in D.items()}
    # CPU 기준과 PTX
    cpu차 = {}
    for op in ("div", "sqrt", "i64tof", "u64tof", "i32tof", "sdot", "sudot"):
        for k, rows in D[op].items():
            exp = [cpu(op, *(list(r) + [0, 0])[:3]) for r in rows]
            got = ref[op][k]
            다름 = [(i, rows[i], hex(got[i]), hex(e)) for i, e in enumerate(exp) if e is not None and e != got[i]]
            nan칸 = sum(1 for e in exp if e is None)
            cpu차[f"{op} · {k}"] = {"칸": len(rows), "PTX 가 CPU 와 다름": len(다름), "NaN · 견주지 않음": nan칸, "예": [str(x) for x in 다름[:5]]}
    결과["PTX 대 CPU"] = cpu차
    print("PTX 대 CPU:", {k: v["PTX 가 CPU 와 다름"] for k, v in cpu차.items()}, flush=True)
    v = V.Vk()
    for pd in v.pds:
        p = v.props(pd)
        modes = [(None, False), (None, True)] + ([("ftz", False), ("ftz", True)] if p["denorm_ftz_f32"] else [])
        dev = Dev(v, pd)
        for dm, szp in modes:
            label = f"{p['name']} · {'버림 모드' if dm else '기본'}" + (" · SignedZeroInfNanPreserve" if szp else "")
            res = {"장치": label, "갈래": {}}
            for op, d in D.items():
                if op in ("sdot", "sudot") and not p["dot_4x8_packed_signed_accel"] and False:
                    continue
                for k, rows in d.items():
                    got = run_vk(dev, op, dm, rows, szp)
                    want = ref[op][k]
                    다름 = [i for i in range(len(rows)) if got[i] != want[i]]
                    # NaN 은 NaN 이면 같다고도 센다(NaN 의 비트는 장치마다 다를 수 있다)
                    nan같음 = [i for i in 다름 if math.isnan(fb(got[i])) and math.isnan(fb(want[i])) and op not in ("cmp6", "ftoi", "rni", "sdot", "sudot")]
                    res["갈래"][f"{op} · {k}"] = {"칸": len(rows), "PTX 와 다름": len(다름), "그중 둘 다 NaN": len(nan같음),
                                                  "예": [(hex(rows[i][0]), hex(rows[i][1]) if len(rows[i]) > 1 else "", hex(got[i]), hex(want[i]))
                                                        for i in 다름[:6]],
                                                  "출력해시": hashlib.sha256(P2.pack_u(got)).hexdigest()[:16]}
            결과["장치"].append(res)
            틀 = {k: (r["PTX 와 다름"], r["그중 둘 다 NaN"]) for k, r in res["갈래"].items() if r["PTX 와 다름"]}
            print(label, "— PTX 와 다른 갈래:", 틀 if 틀 else "없음", flush=True)
        dev.close()
    결과["시간(초)"] = round(time.time() - t0, 1)
    if out_path:
        json.dump(결과, open(out_path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
