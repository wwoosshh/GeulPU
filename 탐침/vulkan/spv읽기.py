"""31단계 — SPIR-V 읽개(연구 도구). 글(geul) 컴파일러의 SPIR-V 뒷단이 낸 모듈을 사람이 읽는 글로 풀고, 몇 가지 꼴을 확인한다
   (아이디가 쓰기 전에 정의되는가, 블록마다 끝 명령이 하나인가, 병합 명령이 분기 바로 앞인가, 함수 변수가 첫 블록의 맨 앞인가).
   Khronos 의 spirv-val 이 없을 때 쓰는 가벼운 점검이다 — 모든 규칙을 보지는 않는다.
     python -X utf8 spv읽기.py <모듈.spv | 묶음.spvs> [커널이름] [--점검만]"""
import struct
import sys

OPS = {
    1: "OpUndef", 5: "OpName", 10: "OpExtension", 11: "OpExtInstImport", 12: "OpExtInst", 14: "OpMemoryModel", 15: "OpEntryPoint",
    16: "OpExecutionMode", 17: "OpCapability", 19: "OpTypeVoid", 20: "OpTypeBool", 21: "OpTypeInt", 22: "OpTypeFloat",
    23: "OpTypeVector", 28: "OpTypeArray", 29: "OpTypeRuntimeArray", 30: "OpTypeStruct", 32: "OpTypePointer", 33: "OpTypeFunction",
    41: "OpConstantTrue", 42: "OpConstantFalse", 43: "OpConstant", 44: "OpConstantComposite", 50: "OpSpecConstant",
    54: "OpFunction", 56: "OpFunctionEnd", 59: "OpVariable", 61: "OpLoad", 62: "OpStore", 65: "OpAccessChain", 71: "OpDecorate",
    72: "OpMemberDecorate", 80: "OpCompositeConstruct", 81: "OpCompositeExtract", 109: "OpConvertFToU", 110: "OpConvertFToS",
    111: "OpConvertSToF", 112: "OpConvertUToF", 113: "OpUConvert", 114: "OpSConvert", 117: "OpConvertPtrToU", 120: "OpConvertUToPtr",
    124: "OpBitcast", 126: "OpSNegate", 127: "OpFNegate", 128: "OpIAdd", 129: "OpFAdd", 130: "OpISub", 131: "OpFSub", 132: "OpIMul",
    133: "OpFMul", 134: "OpUDiv", 135: "OpSDiv", 136: "OpFDiv", 137: "OpUMod", 138: "OpSRem", 166: "OpLogicalOr", 167: "OpLogicalAnd",
    168: "OpLogicalNot", 169: "OpSelect", 170: "OpIEqual", 171: "OpINotEqual", 172: "OpUGreaterThan", 173: "OpSGreaterThan",
    174: "OpUGreaterThanEqual", 175: "OpSGreaterThanEqual", 176: "OpULessThan", 177: "OpSLessThan", 178: "OpULessThanEqual",
    179: "OpSLessThanEqual", 180: "OpFOrdEqual", 183: "OpFUnordNotEqual", 184: "OpFOrdLessThan", 186: "OpFOrdGreaterThan",
    188: "OpFOrdLessThanEqual", 190: "OpFOrdGreaterThanEqual", 194: "OpShiftRightLogical", 195: "OpShiftRightArithmetic",
    196: "OpShiftLeftLogical", 197: "OpBitwiseOr", 198: "OpBitwiseXor", 199: "OpBitwiseAnd", 200: "OpNot", 224: "OpControlBarrier",
    241: "OpAtomicOr", 246: "OpLoopMerge", 247: "OpSelectionMerge", 248: "OpLabel", 249: "OpBranch", 250: "OpBranchConditional",
    253: "OpReturn", 255: "OpUnreachable", 331: "OpExecutionModeId", 345: "OpGroupNonUniformShuffle", 4450: "OpSDot", 4452: "OpSUDot",
}
# 결과 타입 · 결과 아이디가 있는 명령 (자리: 0 = 결과 타입, 1 = 결과)
WITH_TYPE = {1, 12, 41, 42, 43, 44, 50, 54, 59, 61, 65, 80, 81, 109, 110, 111, 112, 113, 114, 117, 120, 124, 126, 127, 128, 129, 130, 131,
             132, 133, 134, 135, 136, 137, 138, 166, 167, 168, 169, 170, 171, 172, 173, 174, 175, 176, 177, 178, 179, 180, 183, 184, 186,
             188, 190, 194, 195, 196, 197, 198, 199, 200, 241, 345, 4450, 4452}
RESULT_ONLY = {11, 19, 20, 21, 22, 23, 28, 29, 30, 32, 33, 248}          # 결과 아이디가 첫 자리
TERM = {249, 250, 253, 255}


def 글(words):
    b = struct.pack("<%dI" % len(words), *words)
    return b.split(b"\0")[0].decode("utf-8", "replace")


def 풀기(words):
    assert words[0] == 0x07230203, hex(words[0])
    out = []
    i = 5
    while i < len(words):
        n, op = words[i] >> 16, words[i] & 0xFFFF
        if n == 0:
            raise ValueError(f"낱말 {i}: 길이 0")
        out.append((op, words[i + 1:i + n]))
        i += n
    return out


def 점검(ins, bound):
    """가벼운 꼴 점검 — 문제의 목록"""
    문제 = []
    정의 = set()
    # 앞에서 쓰는 것을 허락하는 것: 이름표(분기 대상), 함수 · 진입점 · 꾸밈 · 이름 · 실행 모드의 대상
    이름표 = {ops[0] for op, ops in ins if op == 248}
    for op, ops in ins:
        if op in WITH_TYPE:
            정의.add(ops[1])
        elif op in RESULT_ONLY:
            정의.add(ops[0])
    for k, (op, ops) in enumerate(ins):
        if op in WITH_TYPE:
            if ops[1] >= bound:
                문제.append(f"#{k} {OPS.get(op, op)}: 결과 {ops[1]} ≥ 끝 {bound}")
    # 블록 꼴
    in_fn, first_block, block_open, after_term = False, False, False, False
    prev = None
    for k, (op, ops) in enumerate(ins):
        if op == 54:
            in_fn, first_block = True, True
        elif op == 56:
            if block_open:
                문제.append(f"#{k}: 끝 명령 없이 함수가 끝난다")
            in_fn = block_open = False
        elif in_fn and op == 248:
            if block_open:
                문제.append(f"#{k}: 앞 블록이 끝나지 않았다(이름표 {ops[0]})")
            if prev is not None and prev[0] == 248:
                first_block = False
            elif prev is not None and prev[0] != 54:
                first_block = False
            block_open = True
        elif in_fn and op == 59:
            if not first_block or (prev is not None and prev[0] not in (248, 59)):
                문제.append(f"#{k}: 함수 변수가 첫 블록의 맨 앞이 아니다")
        elif in_fn and op in TERM:
            if not block_open:
                문제.append(f"#{k}: 블록 밖의 끝 명령 {OPS.get(op)}")
            block_open = False
            first_block = False
        elif in_fn and op in (246, 247):
            nxt = ins[k + 1][0] if k + 1 < len(ins) else None
            if nxt not in (249, 250):
                문제.append(f"#{k}: {OPS[op]} 뒤가 분기가 아니다")
        elif in_fn and op == 250:
            pass
        elif in_fn and not block_open:
            문제.append(f"#{k}: 블록 밖의 명령 {OPS.get(op, op)}")
        if in_fn and op == 250:
            p = ins[k - 1][0]
            if p not in (246, 247):
                문제.append(f"#{k}: 병합 명령 없는 조건 분기")
        prev = (op, ops)
    # 분기 대상이 이름표인가
    for k, (op, ops) in enumerate(ins):
        tgts = []
        if op == 249:
            tgts = [ops[0]]
        elif op == 250:
            tgts = ops[1:3]
        elif op in (246, 247):
            tgts = ops[:2] if op == 246 else ops[:1]
        for t in tgts:
            if t not in 이름표:
                문제.append(f"#{k} {OPS[op]}: 대상 {t} 가 이름표가 아니다")
    return 문제


def 타입점검(ins):
    """값의 타입이 맞는가 — 저장 · 읽기의 포인터 대상, 정수 · 실수 셈의 피연산자, 고르기, 비트 바꾸기의 폭"""
    문제 = []
    T = {}            # 아이디 → 타입 아이디
    정의 = {}         # 타입 아이디 → (종류, …)
    for op, ops in ins:
        if op in (19, 20):
            정의[ops[0]] = ("void",) if op == 19 else ("bool",)
        elif op == 21:
            정의[ops[0]] = ("int", ops[1], ops[2])
        elif op == 22:
            정의[ops[0]] = ("float", ops[1])
        elif op == 23:
            정의[ops[0]] = ("vec", ops[1], ops[2])
        elif op == 28:
            정의[ops[0]] = ("array", ops[1], ops[2])
        elif op == 30:
            정의[ops[0]] = ("struct",) + tuple(ops[1:])
        elif op == 32:
            정의[ops[0]] = ("ptr", ops[1], ops[2])
        if op in WITH_TYPE:
            T[ops[1]] = ops[0]
    def 폭(t):
        d = 정의.get(t)
        if d is None:
            return None
        if d[0] in ("int", "float"):
            return d[1]
        if d[0] == "vec":
            return 폭(d[1]) * d[2]
        if d[0] == "ptr":
            return 64
        return None
    def 같은꼴(a, b):
        """정수는 폭만 같으면(부호는 상관없다)"""
        if a == b:
            return True
        da, db = 정의.get(a), 정의.get(b)
        return da is not None and db is not None and da[0] == db[0] == "int" and da[1] == db[1]
    for k, (op, ops) in enumerate(ins):
        name = OPS.get(op, op)
        if op == 62:                                     # OpStore ptr val
            pt = 정의.get(T.get(ops[0]))
            if pt and pt[0] == "ptr" and T.get(ops[1]) is not None and pt[2] != T[ops[1]]:
                문제.append(f"#{k} OpStore %{ops[0]}: 대상 타입 %{pt[2]} 인데 값 %{ops[1]} 은 %{T[ops[1]]}")
        elif op == 61:                                   # OpLoad rt res ptr
            pt = 정의.get(T.get(ops[2]))
            if pt and pt[0] == "ptr" and pt[2] != ops[0]:
                문제.append(f"#{k} OpLoad %{ops[1]}: 결과 %{ops[0]} 인데 포인터 대상 %{pt[2]}")
        elif op in (128, 130, 132, 134, 135, 137, 138, 197, 198, 199):
            ta, tb = T.get(ops[2]), T.get(ops[3])
            if ta is not None and tb is not None and not (같은꼴(ta, ops[0]) and 같은꼴(tb, ops[0])):
                문제.append(f"#{k} {name} %{ops[1]}: 결과 %{ops[0]} · 피연산자 %{ta} %{tb}")
        elif op in (194, 195, 196):
            ta = T.get(ops[2])
            if ta is not None and not 같은꼴(ta, ops[0]):
                문제.append(f"#{k} {name} %{ops[1]}: 결과 %{ops[0]} · 바탕 %{ta}")
        elif op in (129, 131, 133, 136):
            ta, tb = T.get(ops[2]), T.get(ops[3])
            if ta != ops[0] or tb != ops[0]:
                문제.append(f"#{k} {name} %{ops[1]}: 결과 %{ops[0]} · 피연산자 %{ta} %{tb}")
        elif op in (170, 171, 172, 173, 174, 175, 176, 177, 178, 179, 180, 183, 184, 186, 188, 190):
            ta, tb = T.get(ops[2]), T.get(ops[3])
            if ta is not None and tb is not None and not 같은꼴(ta, tb):
                문제.append(f"#{k} {name} %{ops[1]}: 피연산자 %{ta} %{tb}")
        elif op == 169:
            ta, tb = T.get(ops[3]), T.get(ops[4])
            if not (ta == tb == ops[0]):
                문제.append(f"#{k} OpSelect %{ops[1]}: 결과 %{ops[0]} · 갈래 %{ta} %{tb}")
        elif op == 124:
            ta = T.get(ops[2])
            if ta is not None and 폭(ta) != 폭(ops[0]):
                문제.append(f"#{k} OpBitcast %{ops[1]}: 폭 {폭(ta)} → {폭(ops[0])}")
        elif op in (113, 114):
            ta = T.get(ops[2])
            if ta is not None and 정의.get(ta, ("?",))[0] != "int":
                문제.append(f"#{k} {name} %{ops[1]}: 정수가 아닌 피연산자 %{ta}")
    return 문제


def 보이기(ins):
    for op, ops in ins:
        name = OPS.get(op, f"Op{op}")
        if op in (10, 11) or (op == 15):
            if op == 15:
                print(f"{name} {ops[0]} %{ops[1]} \"{글(ops[2:])}\" …")
            elif op == 11:
                print(f"%{ops[0]} = {name} \"{글(ops[1:])}\"")
            else:
                print(f"{name} \"{글(ops)}\"")
        elif op in WITH_TYPE:
            print(f"%{ops[1]} = {name} %{ops[0]} " + " ".join(f"%{x}" for x in ops[2:]))
        elif op in RESULT_ONLY:
            print(f"%{ops[0]} = {name} " + " ".join(str(x) for x in ops[1:]))
        else:
            print(f"{name} " + " ".join(str(x) for x in ops))


def 묶음읽기(path):
    b = open(path, "rb").read()
    if b[:8] != b"GEULSPV1":
        w = struct.unpack("<%dI" % (len(b) // 4), b)
        return {"(하나)": (list(w), 0, [])}
    n = struct.unpack_from("<I", b, 8)[0]
    p = 12
    out = {}
    for _ in range(n):
        ln = struct.unpack_from("<I", b, p)[0]
        p += 4
        name = b[p:p + ln].decode()
        p += ln + (-ln % 4)
        공유, 매개수 = struct.unpack_from("<II", b, p)
        p += 8
        종류 = list(struct.unpack_from("<%dI" % 매개수, b, p))
        p += 4 * 매개수
        nw = struct.unpack_from("<I", b, p)[0]
        p += 4
        out[name] = (list(struct.unpack_from("<%dI" % nw, b, p)), 공유, 종류)
        p += 4 * nw
    return out


def main():
    path = sys.argv[1]
    which = next((a for a in sys.argv[2:] if not a.startswith("--")), None)
    only = "--점검만" in sys.argv
    mods = 묶음읽기(path)
    for name, (w, 공유, 종류) in mods.items():
        if which and name != which:
            continue
        ins = 풀기(w)
        문제 = 점검(ins, w[3]) + 타입점검(ins)
        print(f"== {name}: 낱말 {len(w)} · 명령 {len(ins)} · 공유 {공유} · 매개변수 {종류} · 문제 {len(문제)}")
        for x in 문제[:20]:
            print("  !", x)
        if not only:
            보이기(ins)


if __name__ == "__main__":
    main()
