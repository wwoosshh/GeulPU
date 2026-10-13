"""31단계 탐침 — 아주 작은 SPIR-V 조립기(연구용). 낱말(32 비트) 배열을 직접 쓴다 — 툴킷(glslc 등) 없이.
   글(geul) 컴파일러의 SPIR-V 뒷단을 만들기 전에 Vulkan 의 셈 규칙을 확인하는 데만 쓴다."""
import struct

# 명령 번호 (SPIR-V 1.3 명세)
OpExtension, OpExtInstImport, OpExtInst, OpMemoryModel, OpEntryPoint, OpExecutionMode, OpCapability = 10, 11, 12, 14, 15, 16, 17
OpTypeVoid, OpTypeBool, OpTypeInt, OpTypeFloat, OpTypeVector = 19, 20, 21, 22, 23
OpTypeRuntimeArray, OpTypeStruct, OpTypePointer, OpTypeFunction = 29, 30, 32, 33
OpConstant, OpFunction, OpFunctionEnd, OpVariable, OpLoad, OpStore, OpAccessChain = 43, 54, 56, 59, 61, 62, 65
OpDecorate, OpMemberDecorate, OpCompositeExtract = 71, 72, 81
OpConvertSToF, OpBitcast, OpIAdd, OpFAdd, OpIMul, OpFMul, OpSLessThan = 111, 124, 128, 129, 132, 133, 177
OpLoopMerge, OpSelectionMerge, OpLabel, OpBranch, OpBranchConditional, OpReturn = 246, 247, 248, 249, 250, 253

# 열거값
CapShader = 1
CapDenormPreserve, CapDenormFlushToZero = 4464, 4465
ExecModeLocalSize = 17
ExecModeDenormPreserve, ExecModeDenormFlushToZero = 4459, 4460
SCInput, SCFunction, SCStorageBuffer = 1, 7, 12
DecBlock, DecArrayStride, DecBuiltIn, DecBinding, DecDescriptorSet, DecOffset, DecNoContraction = 2, 6, 11, 33, 34, 35, 42
BuiltInGlobalInvocationId = 28
GLSL_Fma = 50


def _str(s):
    b = s.encode("utf-8") + b"\0"
    b += b"\0" * (-len(b) % 4)
    return list(struct.unpack("<%dI" % (len(b) // 4), b))


class Module:
    def __init__(self):
        self.next = 1
        self.caps, self.exts, self.imports, self.memmodel, self.entries, self.modes = [], [], [], [], [], []
        self.decos, self.types, self.globals_, self.body = [], [], [], []

    def id(self):
        i = self.next
        self.next += 1
        return i

    @staticmethod
    def ins(where, op, *ops):
        words = []
        for o in ops:
            words.extend(o if isinstance(o, list) else [o])
        where.append(((len(words) + 1) << 16) | op)
        where.extend(words)

    def words(self, version=0x00010300):
        out = [0x07230203, version, 0, self.next, 0]
        for part in (self.caps, self.exts, self.imports, self.memmodel, self.entries, self.modes, self.decos, self.types,
                     self.globals_, self.body):
            out.extend(part)
        return out

    def binary(self, version=0x00010300):
        w = self.words(version)
        return struct.pack("<%dI" % len(w), *w)


def q8_block_kernel(M, N, K, variant, denorm_mode=None):
    """계약의 Q8_0 행렬곱 한 칸(행 r = gid.y, 열 c = gid.x):
       블록 b 마다 S0 = Σ a0·w, S1 = Σ a1·w (정확한 정수), T = 256·S1 + S0, u = 실수(T), pd = P[r,b]·d[c,b],
       variant 'fma' — y = Fma(u, pd, y) (GLSL.std.450) · 'sep' — y = (u·pd) + y (곱 · 더하기 따로, 합치기 금지).
       바인딩: 0 A0[M·K] · 1 A1[M·K] · 2 W[N·K] (정수) · 3 P[M·NB] · 4 D[N·NB] (실수) · 5 Y[M·N] (실수)."""
    NB = K // 32
    m = Module()
    I = m.ins
    I(m.caps, OpCapability, CapShader)
    if denorm_mode:
        I(m.exts, OpExtension, _str("SPV_KHR_float_controls"))
        I(m.caps, OpCapability, CapDenormPreserve if denorm_mode == "preserve" else CapDenormFlushToZero)
    glsl = m.id()
    I(m.imports, OpExtInstImport, glsl, _str("GLSL.std.450"))
    I(m.memmodel, OpMemoryModel, 0, 1)                      # Logical, GLSL450
    t_void, t_fn, t_bool, t_int, t_uint, t_f32 = (m.id() for _ in range(6))
    t_v3u, p_in_v3u = m.id(), m.id()
    t_rai, t_raf, t_sti, t_stf = m.id(), m.id(), m.id(), m.id()
    p_sb_sti, p_sb_stf, p_sb_i, p_sb_f, p_fn_i, p_fn_f = (m.id() for _ in range(6))
    I(m.types, OpTypeVoid, t_void)
    I(m.types, OpTypeFunction, t_fn, t_void)
    I(m.types, OpTypeBool, t_bool)
    I(m.types, OpTypeInt, t_int, 32, 1)
    I(m.types, OpTypeInt, t_uint, 32, 0)
    I(m.types, OpTypeFloat, t_f32, 32)
    I(m.types, OpTypeVector, t_v3u, t_uint, 3)
    I(m.types, OpTypePointer, p_in_v3u, SCInput, t_v3u)
    I(m.types, OpTypeRuntimeArray, t_rai, t_int)
    I(m.types, OpTypeRuntimeArray, t_raf, t_f32)
    I(m.types, OpTypeStruct, t_sti, t_rai)
    I(m.types, OpTypeStruct, t_stf, t_raf)
    I(m.types, OpTypePointer, p_sb_sti, SCStorageBuffer, t_sti)
    I(m.types, OpTypePointer, p_sb_stf, SCStorageBuffer, t_stf)
    I(m.types, OpTypePointer, p_sb_i, SCStorageBuffer, t_int)
    I(m.types, OpTypePointer, p_sb_f, SCStorageBuffer, t_f32)
    I(m.types, OpTypePointer, p_fn_i, SCFunction, t_int)
    I(m.types, OpTypePointer, p_fn_f, SCFunction, t_f32)
    for t in (t_rai, t_raf):
        I(m.decos, OpDecorate, t, DecArrayStride, 4)
    for t in (t_sti, t_stf):
        I(m.decos, OpDecorate, t, DecBlock)
        I(m.decos, OpMemberDecorate, t, 0, DecOffset, 0)
    consts = {}

    def ci(v):
        if v not in consts:
            consts[v] = m.id()
            I(m.types, OpConstant, t_int, consts[v], v & 0xFFFFFFFF)
        return consts[v]

    f0 = m.id()
    I(m.types, OpConstant, t_f32, f0, 0)
    gid = m.id()
    I(m.globals_, OpVariable, p_in_v3u, gid, SCInput)
    I(m.decos, OpDecorate, gid, DecBuiltIn, BuiltInGlobalInvocationId)
    bufs = []
    for b, st in enumerate((p_sb_sti, p_sb_sti, p_sb_sti, p_sb_stf, p_sb_stf, p_sb_stf)):
        v = m.id()
        I(m.globals_, OpVariable, st, v, SCStorageBuffer)
        I(m.decos, OpDecorate, v, DecDescriptorSet, 0)
        I(m.decos, OpDecorate, v, DecBinding, b)
        bufs.append(v)
    A0, A1, W, Pb, Db, Yb = bufs
    main = m.id()
    I(m.entries, OpEntryPoint, 5, main, _str("main"), gid)
    I(m.modes, OpExecutionMode, main, ExecModeLocalSize, 8, 8, 1)
    if denorm_mode:
        I(m.modes, OpExecutionMode, main, ExecModeDenormPreserve if denorm_mode == "preserve" else ExecModeDenormFlushToZero, 32)

    B = m.body
    lab = {k: m.id() for k in ("entry", "oh", "oc", "ob", "ih", "ic", "ib", "icont", "im", "ocont", "om")}
    I(B, OpFunction, t_void, main, 0, t_fn)
    I(B, OpLabel, lab["entry"])
    v_blk, v_i, v_s0, v_s1, v_y = (m.id() for _ in range(5))
    for v, p in ((v_blk, p_fn_i), (v_i, p_fn_i), (v_s0, p_fn_i), (v_s1, p_fn_i), (v_y, p_fn_f)):
        I(B, OpVariable, p, v, SCFunction)

    def op(o, t, *args):
        r = m.id()
        I(B, o, t, r, *args)
        return r

    g = op(OpLoad, t_v3u, gid)
    c = op(OpBitcast, t_int, op(OpCompositeExtract, t_uint, g, 0))
    r = op(OpBitcast, t_int, op(OpCompositeExtract, t_uint, g, 1))
    rK = op(OpIMul, t_int, r, ci(K))
    cK = op(OpIMul, t_int, c, ci(K))
    rNB = op(OpIMul, t_int, r, ci(NB))
    cNB = op(OpIMul, t_int, c, ci(NB))
    I(B, OpStore, v_blk, ci(0))
    I(B, OpStore, v_y, f0)
    I(B, OpBranch, lab["oh"])
    # 바깥 반복: 블록
    I(B, OpLabel, lab["oh"])
    I(B, OpLoopMerge, lab["om"], lab["ocont"], 0)
    I(B, OpBranch, lab["oc"])
    I(B, OpLabel, lab["oc"])
    bk = op(OpLoad, t_int, v_blk)
    I(B, OpBranchConditional, op(OpSLessThan, t_bool, bk, ci(NB)), lab["ob"], lab["om"])
    I(B, OpLabel, lab["ob"])
    I(B, OpStore, v_s0, ci(0))
    I(B, OpStore, v_s1, ci(0))
    I(B, OpStore, v_i, ci(0))
    I(B, OpBranch, lab["ih"])
    # 안쪽 반복: 블록 안 32 값
    I(B, OpLabel, lab["ih"])
    I(B, OpLoopMerge, lab["im"], lab["icont"], 0)
    I(B, OpBranch, lab["ic"])
    I(B, OpLabel, lab["ic"])
    iv = op(OpLoad, t_int, v_i)
    I(B, OpBranchConditional, op(OpSLessThan, t_bool, iv, ci(32)), lab["ib"], lab["im"])
    I(B, OpLabel, lab["ib"])
    bk2 = op(OpLoad, t_int, v_blk)
    iv2 = op(OpLoad, t_int, v_i)
    off = op(OpIAdd, t_int, op(OpIMul, t_int, bk2, ci(32)), iv2)
    ia = op(OpIAdd, t_int, rK, off)
    iw = op(OpIAdd, t_int, cK, off)
    a0 = op(OpLoad, t_int, op(OpAccessChain, p_sb_i, A0, ci(0), ia))
    a1 = op(OpLoad, t_int, op(OpAccessChain, p_sb_i, A1, ci(0), ia))
    w = op(OpLoad, t_int, op(OpAccessChain, p_sb_i, W, ci(0), iw))
    I(B, OpStore, v_s0, op(OpIAdd, t_int, op(OpLoad, t_int, v_s0), op(OpIMul, t_int, a0, w)))
    I(B, OpStore, v_s1, op(OpIAdd, t_int, op(OpLoad, t_int, v_s1), op(OpIMul, t_int, a1, w)))
    I(B, OpBranch, lab["icont"])
    I(B, OpLabel, lab["icont"])
    I(B, OpStore, v_i, op(OpIAdd, t_int, op(OpLoad, t_int, v_i), ci(1)))
    I(B, OpBranch, lab["ih"])
    I(B, OpLabel, lab["im"])
    T = op(OpIAdd, t_int, op(OpIMul, t_int, op(OpLoad, t_int, v_s1), ci(256)), op(OpLoad, t_int, v_s0))
    u = op(OpConvertSToF, t_f32, T)
    bk3 = op(OpLoad, t_int, v_blk)
    p = op(OpLoad, t_f32, op(OpAccessChain, p_sb_f, Pb, ci(0), op(OpIAdd, t_int, rNB, bk3)))
    d = op(OpLoad, t_f32, op(OpAccessChain, p_sb_f, Db, ci(0), op(OpIAdd, t_int, cNB, bk3)))
    pd = op(OpFMul, t_f32, p, d)
    I(m.decos, OpDecorate, pd, DecNoContraction)
    y = op(OpLoad, t_f32, v_y)
    if variant == "fma":
        y2 = op(OpExtInst, t_f32, glsl, GLSL_Fma, u, pd, y)
    elif variant == "sep":
        prod = op(OpFMul, t_f32, u, pd)
        y2 = op(OpFAdd, t_f32, prod, y)
        I(m.decos, OpDecorate, prod, DecNoContraction)
        I(m.decos, OpDecorate, y2, DecNoContraction)
    else:
        raise ValueError(variant)
    I(B, OpStore, v_y, y2)
    I(B, OpBranch, lab["ocont"])
    I(B, OpLabel, lab["ocont"])
    I(B, OpStore, v_blk, op(OpIAdd, t_int, op(OpLoad, t_int, v_blk), ci(1)))
    I(B, OpBranch, lab["oh"])
    I(B, OpLabel, lab["om"])
    iy = op(OpIAdd, t_int, op(OpIMul, t_int, r, ci(N)), c)
    I(B, OpStore, op(OpAccessChain, p_sb_f, Yb, ci(0), iy), op(OpLoad, t_f32, v_y))
    I(B, OpReturn)
    I(B, OpFunctionEnd)
    return m.binary()
