"""31단계 — 글(geul) 컴파일러의 SPIR-V 뒷단이 낸 커널을 돌리는 시험용 Vulkan 실행기(파이썬 · ctypes · vulkan-1.dll 만).
   GeulPU 의 CUDA 시험(시험/판23.py 등)이 쓰는 드라이버(엔진/글gpt2.py 의 드라이버)와 같은 꼴의 함수를 둔다 — 할당 · 올리기 · 내리기 ·
   맞추기 · 띄우기. 장치 메모리는 장치 주소(buffer device address)로 커널에 넘긴다(CUDA 의 장치 포인터와 같은 64 비트 값).
   - 메모리: 장치에 있고 호스트에서도 보이는 형(DEVICE_LOCAL | HOST_VISIBLE | HOST_COHERENT — NVIDIA 의 큰 BAR, Intel 의 공유 메모리).
   - 커널: .spvs(뒷단의 묶음)에서 이름으로. 블록 크기는 특수화 상수, 서브그룹 크기 32 를 요구(전체 서브그룹).
   - 장치에 없는 실행 모드(비정규수 버림 · SignedZeroInfNanPreserve)는 SPIR-V 에서 지운다(NVIDIA 는 버림을 고를 수 없고 기본이 버림).
   - 오류 칸(범위 검사): 4 바이트 버퍼 하나. 짧은실수 상수 +0 · −0 · +1 · −1 은 푸시 상수로."""
import ctypes as C
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import vk as V  # noqa: E402

U32, U64, VP, CP = C.c_uint32, C.c_uint64, C.c_void_p, C.c_char_p
vk = V.vk


class PushRange(C.Structure):
    _fields_ = [("stageFlags", U32), ("offset", U32), ("size", U32)]


class SpecEntry(C.Structure):
    _fields_ = [("constantID", U32), ("offset", U32), ("size", C.c_size_t)]


class SpecInfo(C.Structure):
    _fields_ = [("mapEntryCount", U32), ("pMapEntries", C.POINTER(SpecEntry)), ("dataSize", C.c_size_t), ("pData", VP)]


class QueryPoolCI(C.Structure):
    _fields_ = [("sType", U32), ("pNext", VP), ("flags", U32), ("queryType", U32), ("queryCount", U32), ("pipelineStatistics", U32)]


def _sig(name, restype, *args):
    f = getattr(vk, name)
    f.restype, f.argtypes = restype, list(args)


_sig("vkGetBufferDeviceAddress", U64, VP, VP)
_sig("vkCmdPushConstants", None, VP, V.H, U32, U32, U32, VP)
_sig("vkUnmapMemory", None, VP, V.H)
_sig("vkGetPhysicalDeviceFeatures2", None, VP, VP)
_sig("vkCreateQueryPool", V.I32, VP, VP, VP, VP)
_sig("vkCmdResetQueryPool", None, VP, V.H, U32, U32)
_sig("vkCmdWriteTimestamp", None, VP, U32, V.H, U32)
_sig("vkGetQueryPoolResults", V.I32, VP, V.H, U32, U32, C.c_size_t, VP, U64, U32)
_sig("vkDestroyQueryPool", None, VP, V.H, VP)
_sig("vkResetCommandBuffer", V.I32, VP, U32)
_sig("vkCreateFence", V.I32, VP, VP, VP, VP)
_sig("vkWaitForFences", V.I32, VP, U32, VP, U32, U64)
_sig("vkResetFences", V.I32, VP, U32, VP)
_sig("vkDestroyFence", None, VP, V.H, VP)
_sig("vkCmdPipelineBarrier", None, VP, U32, U32, U32, U32, VP, U32, VP, U32, VP)


def 묶음읽기(path):
    """.spvs → {이름: (낱말 list, 공유 바이트, 매개변수 종류 list)}"""
    b = open(path, "rb").read()
    assert b[:8] == b"GEULSPV1", path
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


def 모드지우기(words, 버림=True, szp=True):
    """장치가 지원하지 않는 float controls 를 SPIR-V 에서 지운다(능력 · 실행 모드)."""
    out = words[:5]
    i = 5
    while i < len(words):
        n, op = words[i] >> 16, words[i] & 0xFFFF
        ins = words[i:i + n]
        drop = False
        if op == 17 and ((ins[1] == 4465 and not 버림) or (ins[1] == 4466 and not szp)):
            drop = True
        if op == 16 and ((ins[2] == 4460 and not 버림) or (ins[2] == 4461 and not szp)):
            drop = True
        if not drop:
            out.extend(ins)
        i += n
    return out


def 서브그룹쓰는가(words):
    i = 5
    while i < len(words):
        n, op = words[i] >> 16, words[i] & 0xFFFF
        if op == 17 and words[i + 1] in (61, 65, 6022):      # 셔플 · 협력 행렬(34단계)은 서브그룹 32 를 요구한다
            return True
        i += n
    return False


class 장치:
    """Vulkan 장치 하나 — 이름에 '이름' 이 든 첫 장치"""

    def __init__(self, 이름=""):
        self.v = V.Vk()
        pd = None
        for x in self.v.pds:
            p = self.v.props(x)
            if 이름 in p["name"]:
                pd, self.props = x, p
                break
        assert pd is not None, f"Vulkan 장치 없음: {이름}"
        self.pd = pd
        self.이름 = self.props["name"]
        p2 = (C.c_ubyte * 4096)()
        struct.pack_into("<I", p2, 0, 1000059001)
        vk.vkGetPhysicalDeviceProperties2(pd, p2)
        self.공유한도 = struct.unpack_from("<I", p2, 312 + 216)[0]          # maxComputeSharedMemorySize
        n = U32()
        vk.vkGetPhysicalDeviceQueueFamilyProperties(pd, C.byref(n), None)
        qf = (V.QueueFamilyProps * n.value)()
        vk.vkGetPhysicalDeviceQueueFamilyProperties(pd, C.byref(n), qf)
        self.qfi = next(i for i, q in enumerate(qf) if q.queueFlags & 2)
        self.ts_bits = qf[self.qfi].timestampValidBits
        prio = (C.c_float * 1)(1.0)
        qci = V.DeviceQueueCI(2, None, 0, self.qfi, 1, prio)
        # 기능: 64 · 16 · 8 비트 정수, 8 · 16 비트 저장, 장치 주소, 정수 내적, 서브그룹 크기, maintenance4, 명시 배치
        fw = (C.c_ubyte * 32)()
        struct.pack_into("<I", fw, 0, 1000336000)
        struct.pack_into("<4I", fw, 16, 1, 1, 1, 1)
        f13 = (C.c_ubyte * (16 + 15 * 4))()
        struct.pack_into("<IxxxxQ", f13, 0, 53, C.addressof(fw))
        for k in (7, 8, 13, 14):                         # subgroupSizeControl · computeFullSubgroups · shaderIntegerDotProduct · maintenance4
            struct.pack_into("<I", f13, 16 + 4 * k, 1)
        f12 = (C.c_ubyte * (16 + 47 * 4))()
        struct.pack_into("<IxxxxQ", f12, 0, 51, C.addressof(f13))
        for k in (2, 8, 36, 38):                         # storageBuffer8BitAccess · shaderInt8 · hostQueryReset · bufferDeviceAddress
            struct.pack_into("<I", f12, 16 + 4 * k, 1)
        f11 = (C.c_ubyte * (16 + 12 * 4))()
        struct.pack_into("<IxxxxQ", f11, 0, 49, C.addressof(f12))
        struct.pack_into("<I", f11, 16, 1)               # storageBuffer16BitAccess
        f2 = (C.c_ubyte * (16 + 55 * 4 + 4))()
        struct.pack_into("<IxxxxQ", f2, 0, 1000059000, C.addressof(f11))
        struct.pack_into("<I", f2, 16 + 4 * 40, 1)       # shaderInt64
        struct.pack_into("<I", f2, 16 + 4 * 41, 1)       # shaderInt16
        self._keep = [fw, f13, f12, f11, f2]
        exts = [b"VK_KHR_workgroup_memory_explicit_layout"]
        self.협력 = "VK_KHR_cooperative_matrix" in self.v.extensions(pd)     # 34단계 — 협력 행렬(있으면 켠다)
        if self.협력:
            cm = (C.c_ubyte * 24)()
            struct.pack_into("<IxxxxQII", cm, 0, 1000506000, C.addressof(f13), 1, 0)   # COOPERATIVE_MATRIX_FEATURES: cooperativeMatrix
            struct.pack_into("<Q", f12, 8, C.addressof(cm))
            self._keep.append(cm)
            exts.append(b"VK_KHR_cooperative_matrix")
        ea = (CP * len(exts))(*exts)
        dci = V.DeviceCI(3, C.addressof(f2), 0, 1, C.pointer(qci), 0, None, len(exts), C.cast(ea, VP), None)
        self.dev = VP()
        V.check(vk.vkCreateDevice(pd, C.byref(dci), None, C.byref(self.dev)), "vkCreateDevice")
        self.queue = VP()
        vk.vkGetDeviceQueue(self.dev, self.qfi, 0, C.byref(self.queue))
        self.mp = V.MemProps()
        vk.vkGetPhysicalDeviceMemoryProperties(pd, C.byref(self.mp))
        want = 0x1 | 0x2 | 0x4
        self.mti = next(i for i in range(self.mp.memoryTypeCount) if (self.mp.memoryTypes[i].propertyFlags & want) == want)
        self.버퍼들 = {}                                  # 장치 주소 → (buffer, memory, 크기, 호스트 포인터)
        self.할당들 = []
        cp = V.H()
        V.check(vk.vkCreateCommandPool(self.dev, C.byref(V.CmdPoolCI(39, None, 2, self.qfi)), None, C.byref(cp)), "CmdPool")
        self.cp = cp
        cb = VP()
        V.check(vk.vkAllocateCommandBuffers(self.dev, C.byref(V.CmdBufAI(40, None, cp, 0, 1)), C.byref(cb)), "AllocCB")
        self.cb = cb
        self.기록중 = False
        self.파이프들 = {}
        self.오류칸 = self.할당(16)
        self.시각 = None

    # ---- 메모리 ----
    def 할당(self, nbytes):
        size = max(16, (nbytes + 15) // 16 * 16)
        bci = V.BufferCI(12, None, 0, size, 0x20 | 0x20000 | 0x1 | 0x2, 0, 0, None)
        buf = V.H()
        V.check(vk.vkCreateBuffer(self.dev, C.byref(bci), None, C.byref(buf)), "vkCreateBuffer")
        req = V.MemReq()
        vk.vkGetBufferMemoryRequirements(self.dev, buf, C.byref(req))
        flags = (C.c_ubyte * 24)()
        struct.pack_into("<IxxxxQII", flags, 0, 1000060000, 0, 0x2, 0)      # MEMORY_ALLOCATE_FLAGS_INFO · DEVICE_ADDRESS
        mem = V.H()
        V.check(vk.vkAllocateMemory(self.dev, C.byref(V.MemAllocInfo(5, C.addressof(flags), req.size, self.mti)), None, C.byref(mem)),
                "vkAllocateMemory")
        V.check(vk.vkBindBufferMemory(self.dev, buf, mem, U64(0)), "vkBindBufferMemory")
        ptr = VP()
        V.check(vk.vkMapMemory(self.dev, mem, U64(0), U64(size), U32(0), C.byref(ptr)), "vkMapMemory")
        C.memset(ptr, 0, size)
        info = (C.c_ubyte * 24)()
        struct.pack_into("<IxxxxQQ", info, 0, 1000244001, 0, buf.value)
        addr = vk.vkGetBufferDeviceAddress(self.dev, info)
        self.버퍼들[addr] = (buf, mem, size, ptr.value)
        self.할당들.append(addr)
        return addr

    def _찾기(self, addr):
        for a, (buf, mem, size, ptr) in self.버퍼들.items():
            if a <= addr < a + size:
                return ptr + (addr - a), a + size - addr
        raise KeyError(hex(addr))

    def 올리기(self, addr, arr):
        import numpy as np
        b = arr if isinstance(arr, bytes) else np.ascontiguousarray(arr).tobytes()
        p, room = self._찾기(addr)
        assert len(b) <= room
        self.맞추기()
        C.memmove(p, b, len(b))

    def 내리기(self, addr, arr):
        import numpy as np
        self.맞추기()
        p, room = self._찾기(addr)
        assert arr.nbytes <= room
        C.memmove(arr.ctypes.data, p, arr.nbytes)
        return arr

    def 놓기(self):
        self.맞추기()
        for a in self.할당들:
            if a == self.오류칸:
                continue
            buf, mem, size, ptr = self.버퍼들.pop(a)
            vk.vkDestroyBuffer(self.dev, buf, None)
            vk.vkFreeMemory(self.dev, mem, None)
        self.할당들 = [self.오류칸]

    # ---- 커널 ----
    def 모듈(self, path):
        self.커널들 = 묶음읽기(path)
        return self.커널들

    def _파이프(self, 이름, 블록):
        key = (이름, 블록)
        if key in self.파이프들:
            return self.파이프들[key]
        words, 공유, 종류 = self.커널들[이름]
        words = 모드지우기(words, 버림=self.props["denorm_ftz_f32"], szp=self.props["signed_zero_inf_nan_f32"])
        code = struct.pack("<%dI" % len(words), *words)
        cbuf = C.create_string_buffer(code, len(code))
        sm = V.H()
        V.check(vk.vkCreateShaderModule(self.dev, C.byref(V.ShaderModuleCI(16, None, 0, len(code), C.cast(cbuf, VP))), None, C.byref(sm)),
                "vkCreateShaderModule " + 이름)
        npush = 8 * (len(종류) + 1) + 16
        rng = PushRange(0x20, 0, npush)
        pl = V.H()
        V.check(vk.vkCreatePipelineLayout(self.dev, C.byref(V.PipelineLayoutCI(30, None, 0, 0, None, 1, C.addressof(rng))), None,
                                          C.byref(pl)), "PipelineLayout")
        ents = (SpecEntry * 3)(SpecEntry(0, 0, 4), SpecEntry(1, 4, 4), SpecEntry(2, 8, 4))
        data = (U32 * 3)(블록[0], 블록[1], 블록[2])
        spec = SpecInfo(3, ents, 12, C.addressof(data))
        sub = 서브그룹쓰는가(words)
        req = (C.c_ubyte * 24)()
        struct.pack_into("<IxxxxQI", req, 0, 1000225001, 0, 32)               # REQUIRED_SUBGROUP_SIZE 32
        nm = 이름.encode()
        stage = V.StageCI(18, C.addressof(req) if sub else None, 0x2 if sub else 0, 0x20, sm, nm, C.addressof(spec))
        pipe = V.H()
        r = vk.vkCreateComputePipelines(self.dev, V.H(0), 1, C.byref(V.ComputePipelineCI(29, None, 0, stage, pl, V.H(0), -1)), None,
                                        C.byref(pipe))
        V.check(r, "vkCreateComputePipelines " + 이름)
        self.파이프들[key] = (pipe, pl, npush, 종류, sm)
        return self.파이프들[key]

    def 띄우기(self, 이름, grid, block, params):
        """params: [(참조?, 값)] — 참조면 장치 주소, 아니면 정수(종류에 따라 64 · 32 비트, 짧은실수)"""
        blk = block if isinstance(block, tuple) else (block, 1, 1)
        pipe, pl, npush, 종류, _ = self._파이프(이름, blk)
        assert len(params) == len(종류), (이름, len(params), len(종류))
        pc = bytearray(npush)
        for k, ((참조, v), 종) in enumerate(zip(params, 종류)):
            if 종 == 2:
                struct.pack_into("<f", pc, 8 * k, float(v))
            elif 종 == 1:
                struct.pack_into("<i", pc, 8 * k, int(v))
            else:
                struct.pack_into("<Q", pc, 8 * k, int(v) & (2 ** 64 - 1))
        n = len(종류)
        struct.pack_into("<Q", pc, 8 * n, self.오류칸)
        struct.pack_into("<4I", pc, 8 * n + 8, 0x00000000, 0x80000000, 0x3F800000, 0xBF800000)
        self._시작()
        vk.vkCmdBindPipeline(self.cb, U32(1), pipe)
        pcb = (C.c_ubyte * npush).from_buffer(pc)
        vk.vkCmdPushConstants(self.cb, pl, 0x20, 0, npush, C.addressof(pcb))
        vk.vkCmdDispatch(self.cb, U32(grid[0]), U32(grid[1] if len(grid) > 1 else 1), U32(1))
        # 다음 띄움이 이 띄움의 쓰기를 보게
        mb = (C.c_ubyte * 24)()
        struct.pack_into("<IxxxxQII", mb, 0, 46, 0, 0x8000 | 0x10000, 0x8000 | 0x10000)   # MEMORY_BARRIER: SHADER_READ|WRITE
        vk.vkCmdPipelineBarrier(self.cb, 0x800, 0x800, 0, 1, mb, 0, None, 0, None)

    def _시작(self):
        if not self.기록중:
            V.check(vk.vkResetCommandBuffer(self.cb, 0), "ResetCB")
            V.check(vk.vkBeginCommandBuffer(self.cb, C.byref(V.CmdBufBI(42, None, 1, None))), "Begin")
            self.기록중 = True

    def 맞추기(self):
        if not self.기록중:
            return
        V.check(vk.vkEndCommandBuffer(self.cb), "End")
        cbs = (VP * 1)(self.cb)
        V.check(vk.vkQueueSubmit(self.queue, 1, C.byref(V.SubmitInfo(4, None, 0, None, None, 1, cbs, 0, None)), V.H(0)), "Submit")
        V.check(vk.vkQueueWaitIdle(self.queue), "WaitIdle")
        self.기록중 = False

    def 오류칸읽기(self):
        import numpy as np
        return int(self.내리기(self.오류칸, np.zeros(1, np.uint32))[0])

    def 닫기(self):
        self.맞추기()
        vk.vkDeviceWaitIdle(self.dev)
        for (pipe, pl, _, _, sm) in self.파이프들.values():
            vk.vkDestroyPipeline(self.dev, pipe, None)
            vk.vkDestroyPipelineLayout(self.dev, pl, None)
            vk.vkDestroyShaderModule(self.dev, sm, None)
        for a, (buf, mem, size, ptr) in self.버퍼들.items():
            vk.vkDestroyBuffer(self.dev, buf, None)
            vk.vkFreeMemory(self.dev, mem, None)
        vk.vkDestroyCommandPool(self.dev, self.cp, None)
        vk.vkDestroyDevice(self.dev, None)


# ---------------- CUDA 드라이버 꼴의 흉내 (시험이 그대로 돌게) ----------------
class _쿠다흉내:
    """시험(판23 · 판26 · 머리128 · 줄128)이 부르는 CUDA 드라이버 함수를 Vulkan 장치 위에서 — 매개변수는 8 바이트 값의 포인터 배열"""

    def __init__(self, d):
        self.d = d

        def cuFuncGetAttribute(out, attr, fn):          # 함수 객체로 둔다 — 시험이 .argtypes 를 단다(ctypes 함수 꼴)
            if attr == 1:                                # SHARED_SIZE_BYTES
                out._obj.value = self.d.커널들[fn][1]
            else:                                        # 레지스터 · 넘친 지역 메모리 — Vulkan 은 알려 주지 않는다
                out._obj.value = 0
            return 0
        self.cuFuncGetAttribute = cuFuncGetAttribute

    def cuLaunchKernel(self, fn, gx, gy, gz, bx, by, bz, shmem, stream, args, extra):
        종류 = self.d.커널들[fn][2]
        ptrs = C.cast(args, C.POINTER(VP))
        vals = []
        for k in range(len(종류)):
            raw = C.string_at(ptrs[k], 8)
            vals.append((0, struct.unpack("<Q", raw)[0]))
        self.d.띄우기(fn, (gx, gy), (bx, by, bz), vals)
        return 0

    def cuMemcpyHtoD_v2(self, dst, src, n):
        dst = dst.value if hasattr(dst, "value") else dst
        if isinstance(src, (bytes, bytearray)):
            self.d.올리기(dst, bytes(src[:n]))
        else:
            self.d.올리기(dst, C.string_at(src, n))
        return 0

    def cuMemsetD8_v2(self, dst, v, n):
        dst = dst.value if hasattr(dst, "value") else dst
        n = n.value if hasattr(n, "value") else n
        self.d.올리기(dst, bytes([v]) * n)
        return 0

    def cuMemFree_v2(self, p):
        p = p.value if hasattr(p, "value") else p
        if p == self.d.오류칸:                            # 오류 칸은 장치가 끝까지 쓴다(시험이 할당들을 모두 놓아도)
            return 0
        self.d.맞추기()
        buf, mem, size, ptr = self.d.버퍼들.pop(p)
        vk.vkDestroyBuffer(self.d.dev, buf, None)
        vk.vkFreeMemory(self.d.dev, mem, None)
        return 0

    def cuCtxSynchronize(self):
        self.d.맞추기()
        return 0


class 쿠다흉내드라이버(장치):
    """엔진/글gpt2.py 의 드라이버 꼴 — 모듈(바이트) 은 .spvs 의 내용, 함수(모듈, 이름) 은 진입점 이름"""

    def __init__(self, 이름=""):
        super().__init__(이름)
        self.cu = _쿠다흉내(self)
        self.모듈들 = []

    @staticmethod
    def 확인(r):
        if r != 0:
            raise RuntimeError(f"오류 {r}")

    def 모듈(self, 내용):
        import tempfile
        if isinstance(내용, (bytes, bytearray)) and 내용[:8] == b"GEULSPV1":
            with tempfile.NamedTemporaryFile(delete=False, suffix=".spvs") as f:
                f.write(내용)
                path = f.name
            self.커널들 = 묶음읽기(path)
            os.unlink(path)
        else:
            raise ValueError("Vulkan 시험에는 .spvs(글 SPIR-V 뒷단의 묶음)를 준다")
        return self.커널들

    def 함수(self, mod, name):
        ok = name.isascii() and (name[0].isalpha() or name[0] == "_") and all(c.isalnum() or c == "_" for c in name)
        e = name if ok else "_G" + name.encode("utf-8").hex()
        if e not in self.커널들:
            raise KeyError(f"커널이 없다: {name} ({e})")
        return e

    def 할당(self, nbytes):
        return super().할당(nbytes)

    def 놓기(self):
        super().놓기()
