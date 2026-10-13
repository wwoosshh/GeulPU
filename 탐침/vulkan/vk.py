"""31단계 탐침 — vulkan-1.dll(드라이버에 들어 있는 로더)을 ctypes 로 직접 부르는 아주 작은 계산 호스트(연구용).
   장치 고르기 · 능력 묻기 · 저장 버퍼 · 계산 파이프라인 하나 돌리기만 한다."""
import ctypes as C
import struct

vk = C.WinDLL("vulkan-1.dll")
U32, U64, I32, VP, CP = C.c_uint32, C.c_uint64, C.c_int32, C.c_void_p, C.c_char_p
H = C.c_uint64                                                       # 디스패치 없는 핸들(64 비트)


def check(r, what):
    if r != 0:
        raise RuntimeError(f"{what}: VkResult {r}")


class AppInfo(C.Structure):
    _fields_ = [("sType", U32), ("pNext", VP), ("pApplicationName", CP), ("applicationVersion", U32),
                ("pEngineName", CP), ("engineVersion", U32), ("apiVersion", U32)]


class InstanceCI(C.Structure):
    _fields_ = [("sType", U32), ("pNext", VP), ("flags", U32), ("pApplicationInfo", C.POINTER(AppInfo)),
                ("enabledLayerCount", U32), ("ppEnabledLayerNames", VP), ("enabledExtensionCount", U32),
                ("ppEnabledExtensionNames", VP)]


class QueueFamilyProps(C.Structure):
    _fields_ = [("queueFlags", U32), ("queueCount", U32), ("timestampValidBits", U32), ("w", U32), ("h", U32), ("d", U32)]


class DeviceQueueCI(C.Structure):
    _fields_ = [("sType", U32), ("pNext", VP), ("flags", U32), ("queueFamilyIndex", U32), ("queueCount", U32),
                ("pQueuePriorities", C.POINTER(C.c_float))]


class DeviceCI(C.Structure):
    _fields_ = [("sType", U32), ("pNext", VP), ("flags", U32), ("queueCreateInfoCount", U32),
                ("pQueueCreateInfos", C.POINTER(DeviceQueueCI)), ("enabledLayerCount", U32), ("ppEnabledLayerNames", VP),
                ("enabledExtensionCount", U32), ("ppEnabledExtensionNames", VP), ("pEnabledFeatures", VP)]


class ExtProps(C.Structure):
    _fields_ = [("extensionName", C.c_char * 256), ("specVersion", U32)]


class BufferCI(C.Structure):
    _fields_ = [("sType", U32), ("pNext", VP), ("flags", U32), ("size", U64), ("usage", U32), ("sharingMode", U32),
                ("queueFamilyIndexCount", U32), ("pQueueFamilyIndices", VP)]


class MemReq(C.Structure):
    _fields_ = [("size", U64), ("alignment", U64), ("memoryTypeBits", U32)]


class MemType(C.Structure):
    _fields_ = [("propertyFlags", U32), ("heapIndex", U32)]


class MemHeap(C.Structure):
    _fields_ = [("size", U64), ("flags", U32)]


class MemProps(C.Structure):
    _fields_ = [("memoryTypeCount", U32), ("memoryTypes", MemType * 32), ("memoryHeapCount", U32), ("memoryHeaps", MemHeap * 16)]


class MemAllocInfo(C.Structure):
    _fields_ = [("sType", U32), ("pNext", VP), ("allocationSize", U64), ("memoryTypeIndex", U32)]


class ShaderModuleCI(C.Structure):
    _fields_ = [("sType", U32), ("pNext", VP), ("flags", U32), ("codeSize", C.c_size_t), ("pCode", VP)]


class DSLBinding(C.Structure):
    _fields_ = [("binding", U32), ("descriptorType", U32), ("descriptorCount", U32), ("stageFlags", U32), ("pImmutableSamplers", VP)]


class DSLCI(C.Structure):
    _fields_ = [("sType", U32), ("pNext", VP), ("flags", U32), ("bindingCount", U32), ("pBindings", C.POINTER(DSLBinding))]


class PipelineLayoutCI(C.Structure):
    _fields_ = [("sType", U32), ("pNext", VP), ("flags", U32), ("setLayoutCount", U32), ("pSetLayouts", C.POINTER(H)),
                ("pushConstantRangeCount", U32), ("pPushConstantRanges", VP)]


class StageCI(C.Structure):
    _fields_ = [("sType", U32), ("pNext", VP), ("flags", U32), ("stage", U32), ("module", H), ("pName", CP),
                ("pSpecializationInfo", VP)]


class ComputePipelineCI(C.Structure):
    _fields_ = [("sType", U32), ("pNext", VP), ("flags", U32), ("stage", StageCI), ("layout", H), ("basePipelineHandle", H),
                ("basePipelineIndex", I32)]


class PoolSize(C.Structure):
    _fields_ = [("type", U32), ("descriptorCount", U32)]


class DescPoolCI(C.Structure):
    _fields_ = [("sType", U32), ("pNext", VP), ("flags", U32), ("maxSets", U32), ("poolSizeCount", U32), ("pPoolSizes", C.POINTER(PoolSize))]


class DescSetAI(C.Structure):
    _fields_ = [("sType", U32), ("pNext", VP), ("descriptorPool", H), ("descriptorSetCount", U32), ("pSetLayouts", C.POINTER(H))]


class DescBufferInfo(C.Structure):
    _fields_ = [("buffer", H), ("offset", U64), ("range", U64)]


class WriteDescSet(C.Structure):
    _fields_ = [("sType", U32), ("pNext", VP), ("dstSet", H), ("dstBinding", U32), ("dstArrayElement", U32),
                ("descriptorCount", U32), ("descriptorType", U32), ("pImageInfo", VP), ("pBufferInfo", C.POINTER(DescBufferInfo)),
                ("pTexelBufferView", VP)]


class CmdPoolCI(C.Structure):
    _fields_ = [("sType", U32), ("pNext", VP), ("flags", U32), ("queueFamilyIndex", U32)]


class CmdBufAI(C.Structure):
    _fields_ = [("sType", U32), ("pNext", VP), ("commandPool", H), ("level", U32), ("commandBufferCount", U32)]


class CmdBufBI(C.Structure):
    _fields_ = [("sType", U32), ("pNext", VP), ("flags", U32), ("pInheritanceInfo", VP)]


class SubmitInfo(C.Structure):
    _fields_ = [("sType", U32), ("pNext", VP), ("waitSemaphoreCount", U32), ("pWaitSemaphores", VP), ("pWaitDstStageMask", VP),
                ("commandBufferCount", U32), ("pCommandBuffers", C.POINTER(VP)), ("signalSemaphoreCount", U32), ("pSignalSemaphores", VP)]


class CoopMatProps(C.Structure):
    _fields_ = [("sType", U32), ("pNext", VP), ("MSize", U32), ("NSize", U32), ("KSize", U32), ("AType", U32), ("BType", U32),
                ("CType", U32), ("ResultType", U32), ("saturatingAccumulation", U32), ("scope", U32)]


def _proc(inst, name, restype, *argtypes):
    gp = vk.vkGetInstanceProcAddr
    gp.restype, gp.argtypes = VP, [VP, CP]
    addr = gp(inst, name.encode())
    if not addr:
        return None
    return C.CFUNCTYPE(restype, *argtypes)(addr)


class Vk:
    def __init__(self):
        app = AppInfo(0, None, b"geulpu-probe", 1, b"geulpu", 1, (1 << 22) | (3 << 12))      # Vulkan 1.3
        ci = InstanceCI(1, None, 0, C.pointer(app), 0, None, 0, None)
        self.inst = VP()
        check(vk.vkCreateInstance(C.byref(ci), None, C.byref(self.inst)), "vkCreateInstance")
        n = U32()
        vk.vkEnumeratePhysicalDevices(self.inst, C.byref(n), None)
        arr = (VP * n.value)()
        vk.vkEnumeratePhysicalDevices(self.inst, C.byref(n), arr)
        self.pds = list(arr)

    def props(self, pd):
        """장치 이름 · 판 · 능력(서브그룹 · float controls · 정수 내적 · 서브그룹 크기 조절) — Properties2 의 pNext 사슬"""
        sub = (C.c_ubyte * 32)()
        struct.pack_into("<I", sub, 0, 1000094000)                        # SUBGROUP_PROPERTIES
        fc = (C.c_ubyte * 96)()
        struct.pack_into("<I", fc, 0, 1000197000)                         # FLOAT_CONTROLS_PROPERTIES
        dot = (C.c_ubyte * 160)()
        struct.pack_into("<I", dot, 0, 1000280001)                        # SHADER_INTEGER_DOT_PRODUCT_PROPERTIES
        ssc = (C.c_ubyte * 32)()
        struct.pack_into("<I", ssc, 0, 1000225000)                        # SUBGROUP_SIZE_CONTROL_PROPERTIES
        struct.pack_into("<Q", sub, 8, C.addressof(fc))
        struct.pack_into("<Q", fc, 8, C.addressof(dot))
        struct.pack_into("<Q", dot, 8, C.addressof(ssc))
        p2 = (C.c_ubyte * 4096)()
        struct.pack_into("<I", p2, 0, 1000059001)                         # PHYSICAL_DEVICE_PROPERTIES_2
        struct.pack_into("<Q", p2, 8, C.addressof(sub))
        vk.vkGetPhysicalDeviceProperties2(pd, p2)
        api, drv, vendor, dev_id, dtype = struct.unpack_from("<5I", p2, 16)
        name = bytes(p2[36:36 + 256]).split(b"\0")[0].decode("utf-8", "replace")
        s_size, s_stages, s_ops, _ = struct.unpack_from("<4I", sub, 16)
        f = struct.unpack_from("<17I", fc, 16)
        d6 = struct.unpack_from("<6I", dot, 16)
        smin, smax = struct.unpack_from("<2I", ssc, 16)
        return {
            "name": name, "api": f"{api >> 22}.{(api >> 12) & 1023}.{api & 4095}", "driver_raw": drv, "vendor": hex(vendor),
            "subgroup_size": s_size, "subgroup_min_max": (smin, smax),
            "denorm_preserve_f32": bool(f[6]), "denorm_ftz_f32": bool(f[9]), "rte_f32": bool(f[12]), "rtz_f32": bool(f[15]),
            "denorm_independence": f[0], "rounding_independence": f[1], "signed_zero_inf_nan_f32": bool(f[3]),
            "dot_8bit_signed_accel": bool(d6[1]), "dot_4x8_packed_signed_accel": bool(d6[4]),
        }

    def extensions(self, pd):
        n = U32()
        vk.vkEnumerateDeviceExtensionProperties(pd, None, C.byref(n), None)
        arr = (ExtProps * n.value)()
        vk.vkEnumerateDeviceExtensionProperties(pd, None, C.byref(n), arr)
        return sorted(e.extensionName.decode() for e in arr)

    def coopmat(self, pd):
        f = _proc(self.inst, "vkGetPhysicalDeviceCooperativeMatrixPropertiesKHR", I32, VP, C.POINTER(U32), VP)
        if f is None:
            return None
        n = U32()
        if f(pd, C.byref(n), None) != 0:
            return None
        arr = (CoopMatProps * n.value)()
        for a in arr:
            a.sType = 1000506001
        f(pd, C.byref(n), arr)
        return [(a.MSize, a.NSize, a.KSize, a.AType, a.BType, a.CType, a.ResultType, a.scope) for a in arr]


class Device:
    """장치 하나 — 계산 큐 하나, 호스트에서 보이는 저장 버퍼, 파이프라인 하나씩 돌리기"""

    def __init__(self, v, pd, extensions=()):
        self.v, self.pd = v, pd
        n = U32()
        vk.vkGetPhysicalDeviceQueueFamilyProperties(pd, C.byref(n), None)
        qf = (QueueFamilyProps * n.value)()
        vk.vkGetPhysicalDeviceQueueFamilyProperties(pd, C.byref(n), qf)
        self.qfi = next(i for i, q in enumerate(qf) if q.queueFlags & 2)        # COMPUTE
        prio = (C.c_float * 1)(1.0)
        qci = DeviceQueueCI(2, None, 0, self.qfi, 1, prio)
        exts = (CP * max(1, len(extensions)))(*[e.encode() for e in extensions])
        dci = DeviceCI(3, None, 0, 1, C.pointer(qci), 0, None, len(extensions), C.cast(exts, VP) if extensions else None, None)
        self.dev = VP()
        check(vk.vkCreateDevice(pd, C.byref(dci), None, C.byref(self.dev)), "vkCreateDevice")
        self.queue = VP()
        vk.vkGetDeviceQueue(self.dev, self.qfi, 0, C.byref(self.queue))
        self.mp = MemProps()
        vk.vkGetPhysicalDeviceMemoryProperties(pd, C.byref(self.mp))
        self.objs = []

    def buffer(self, data: bytes):
        size = max(16, len(data))
        bci = BufferCI(12, None, 0, size, 0x20, 0, 0, None)                        # STORAGE_BUFFER
        buf = H()
        check(vk.vkCreateBuffer(self.dev, C.byref(bci), None, C.byref(buf)), "vkCreateBuffer")
        req = MemReq()
        vk.vkGetBufferMemoryRequirements(self.dev, buf, C.byref(req))
        want = 0x2 | 0x4                                                            # HOST_VISIBLE | HOST_COHERENT
        ti = next(i for i in range(self.mp.memoryTypeCount)
                  if (req.memoryTypeBits >> i) & 1 and (self.mp.memoryTypes[i].propertyFlags & want) == want)
        mem = H()
        check(vk.vkAllocateMemory(self.dev, C.byref(MemAllocInfo(5, None, req.size, ti)), None, C.byref(mem)), "vkAllocateMemory")
        check(vk.vkBindBufferMemory(self.dev, buf, mem, U64(0)), "vkBindBufferMemory")
        ptr = VP()
        check(vk.vkMapMemory(self.dev, mem, U64(0), U64(size), U32(0), C.byref(ptr)), "vkMapMemory")
        C.memmove(ptr, data, len(data))
        self.objs.append((buf, mem))
        return buf, ptr, size

    def run(self, spirv: bytes, buffers, groups):
        code = C.create_string_buffer(spirv, len(spirv))
        sm = H()
        check(vk.vkCreateShaderModule(self.dev, C.byref(ShaderModuleCI(16, None, 0, len(spirv), C.cast(code, VP))), None, C.byref(sm)),
              "vkCreateShaderModule")
        nb = len(buffers)
        binds = (DSLBinding * nb)(*[DSLBinding(i, 7, 1, 0x20, None) for i in range(nb)])
        dsl = H()
        check(vk.vkCreateDescriptorSetLayout(self.dev, C.byref(DSLCI(32, None, 0, nb, binds)), None, C.byref(dsl)), "DSL")
        pl = H()
        check(vk.vkCreatePipelineLayout(self.dev, C.byref(PipelineLayoutCI(30, None, 0, 1, C.pointer(dsl), 0, None)), None, C.byref(pl)),
              "PipelineLayout")
        stage = StageCI(18, None, 0, 0x20, sm, b"main", None)
        pipe = H()
        check(vk.vkCreateComputePipelines(self.dev, H(0), 1, C.byref(ComputePipelineCI(29, None, 0, stage, pl, H(0), -1)), None,
                                          C.byref(pipe)), "vkCreateComputePipelines")
        ps = PoolSize(7, nb)
        pool = H()
        check(vk.vkCreateDescriptorPool(self.dev, C.byref(DescPoolCI(33, None, 0, 1, 1, C.pointer(ps))), None, C.byref(pool)), "Pool")
        ds = H()
        check(vk.vkAllocateDescriptorSets(self.dev, C.byref(DescSetAI(34, None, pool, 1, C.pointer(dsl))), C.byref(ds)), "AllocDS")
        infos = [DescBufferInfo(b[0], 0, 0xFFFFFFFFFFFFFFFF) for b in buffers]
        writes = (WriteDescSet * nb)(*[WriteDescSet(35, None, ds, i, 0, 1, 7, None, C.pointer(infos[i]), None) for i in range(nb)])
        vk.vkUpdateDescriptorSets(self.dev, nb, writes, 0, None)
        cp = H()
        check(vk.vkCreateCommandPool(self.dev, C.byref(CmdPoolCI(39, None, 0, self.qfi)), None, C.byref(cp)), "CmdPool")
        cb = VP()
        check(vk.vkAllocateCommandBuffers(self.dev, C.byref(CmdBufAI(40, None, cp, 0, 1)), C.byref(cb)), "AllocCB")
        check(vk.vkBeginCommandBuffer(cb, C.byref(CmdBufBI(42, None, 1, None))), "Begin")
        vk.vkCmdBindPipeline(cb, U32(1), pipe)
        vk.vkCmdBindDescriptorSets(cb, U32(1), pl, U32(0), U32(1), C.byref(ds), U32(0), None)
        vk.vkCmdDispatch(cb, U32(groups[0]), U32(groups[1]), U32(groups[2]))
        check(vk.vkEndCommandBuffer(cb), "End")
        cbs = (VP * 1)(cb)
        check(vk.vkQueueSubmit(self.queue, 1, C.byref(SubmitInfo(4, None, 0, None, None, 1, cbs, 0, None)), H(0)), "Submit")
        check(vk.vkQueueWaitIdle(self.queue), "WaitIdle")
        vk.vkDestroyCommandPool(self.dev, cp, None)
        vk.vkDestroyDescriptorPool(self.dev, pool, None)
        vk.vkDestroyPipeline(self.dev, pipe, None)
        vk.vkDestroyPipelineLayout(self.dev, pl, None)
        vk.vkDestroyDescriptorSetLayout(self.dev, dsl, None)
        vk.vkDestroyShaderModule(self.dev, sm, None)

    def release(self):
        """지금까지 만든 버퍼를 모두 돌려준다(시험 여럿을 한 장치에서 돌릴 때)."""
        vk.vkDeviceWaitIdle(self.dev)
        for buf, mem in self.objs:
            vk.vkDestroyBuffer(self.dev, buf, None)
            vk.vkFreeMemory(self.dev, mem, None)
        self.objs = []

    def close(self):
        vk.vkDeviceWaitIdle(self.dev)
        for buf, mem in self.objs:
            vk.vkDestroyBuffer(self.dev, buf, None)
            vk.vkFreeMemory(self.dev, mem, None)
        vk.vkDestroyDevice(self.dev, None)


def _sig(name, restype, *args):
    f = getattr(vk, name)
    f.restype, f.argtypes = restype, list(args)


_sig("vkCreateInstance", I32, VP, VP, VP)
_sig("vkEnumeratePhysicalDevices", I32, VP, VP, VP)
_sig("vkGetPhysicalDeviceProperties2", None, VP, VP)
_sig("vkEnumerateDeviceExtensionProperties", I32, VP, VP, VP, VP)
_sig("vkGetPhysicalDeviceQueueFamilyProperties", None, VP, VP, VP)
_sig("vkCreateDevice", I32, VP, VP, VP, VP)
_sig("vkGetDeviceQueue", None, VP, U32, U32, VP)
_sig("vkGetPhysicalDeviceMemoryProperties", None, VP, VP)
_sig("vkCreateBuffer", I32, VP, VP, VP, VP)
_sig("vkGetBufferMemoryRequirements", None, VP, H, VP)
_sig("vkAllocateMemory", I32, VP, VP, VP, VP)
_sig("vkBindBufferMemory", I32, VP, H, H, U64)
_sig("vkMapMemory", I32, VP, H, U64, U64, U32, VP)
_sig("vkCreateShaderModule", I32, VP, VP, VP, VP)
_sig("vkCreateDescriptorSetLayout", I32, VP, VP, VP, VP)
_sig("vkCreatePipelineLayout", I32, VP, VP, VP, VP)
_sig("vkCreateComputePipelines", I32, VP, H, U32, VP, VP, VP)
_sig("vkCreateDescriptorPool", I32, VP, VP, VP, VP)
_sig("vkAllocateDescriptorSets", I32, VP, VP, VP)
_sig("vkUpdateDescriptorSets", None, VP, U32, VP, U32, VP)
_sig("vkCreateCommandPool", I32, VP, VP, VP, VP)
_sig("vkAllocateCommandBuffers", I32, VP, VP, VP)
_sig("vkBeginCommandBuffer", I32, VP, VP)
_sig("vkCmdBindPipeline", None, VP, U32, H)
_sig("vkCmdBindDescriptorSets", None, VP, U32, H, U32, U32, VP, U32, VP)
_sig("vkCmdDispatch", None, VP, U32, U32, U32)
_sig("vkEndCommandBuffer", I32, VP)
_sig("vkQueueSubmit", I32, VP, U32, VP, H)
_sig("vkQueueWaitIdle", I32, VP)
_sig("vkDestroyCommandPool", None, VP, H, VP)
_sig("vkDestroyDescriptorPool", None, VP, H, VP)
_sig("vkDestroyPipeline", None, VP, H, VP)
_sig("vkDestroyPipelineLayout", None, VP, H, VP)
_sig("vkDestroyDescriptorSetLayout", None, VP, H, VP)
_sig("vkDestroyShaderModule", None, VP, H, VP)
_sig("vkDeviceWaitIdle", I32, VP)
_sig("vkDestroyBuffer", None, VP, H, VP)
_sig("vkFreeMemory", None, VP, H, VP)
_sig("vkDestroyDevice", None, VP, VP)
