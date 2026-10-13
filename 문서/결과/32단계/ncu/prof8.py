"""32단계 — 행 8 의 행렬곱 판을 하나씩(ncu 로 명령 수 · 텐서곱 수를 재려고). 값은 아무것이나(시간 · 명령 수는 값과 상관없다).
   python prof8.py <ptx (ASCII 경로)>  — cuProfilerStart/Stop 사이에서 판마다 한 번씩 띄운다."""
import ctypes
import os
import struct
import sys

cu = ctypes.WinDLL("nvcuda.dll")
u64 = ctypes.c_uint64
i64 = ctypes.c_int64


def ok(r, what):
    if r != 0:
        raise SystemExit(f"{what}: {r}")


ok(cu.cuInit(0), "cuInit")
dev = ctypes.c_int()
ok(cu.cuDeviceGet(ctypes.byref(dev), 0), "cuDeviceGet")
ctx = ctypes.c_void_p()
ok(cu.cuCtxCreate_v2(ctypes.byref(ctx), 0, dev), "cuCtxCreate")
ptx = open(sys.argv[1], "rb").read() + b"\0"
mod = ctypes.c_void_p()
ok(cu.cuModuleLoadData(ctypes.byref(mod), ptx), "cuModuleLoadData")


def fn(name):
    f = ctypes.c_void_p()
    ok(cu.cuModuleGetFunction(ctypes.byref(f), mod, ("_G" + name.encode("utf-8").hex()).encode()), name)
    return f


def alloc(n, data=None):
    p = u64()
    ok(cu.cuMemAlloc_v2(ctypes.byref(p), n), "cuMemAlloc")
    if data is None:
        data = os.urandom(n)
    ok(cu.cuMemcpyHtoD_v2(p, data, n), "cuMemcpyHtoD")
    return p.value


K7, N_qkv, N_o, N_gu, F = 3584, 4608, 3584, 37888, 18944
# 척도: 반실수 1/128 근처, 정보: 마법수(E 0 근처)
def 척도(K, N):
    Np = (N + 63) // 64 * 64
    return alloc((K // 32) * Np * 2, struct.pack("<H", 0x2000) * ((K // 32) * Np))


def 정보(K):
    m = ((137 + 0) << 23) + 4194304
    return alloc((K // 32) * 64 * 4, struct.pack("<i", m) * ((K // 32) * 64))


def launch(name, grid, block, args):
    vals = [u64(a) if isinstance(a, int) and a > 1 << 32 else i64(a) for a in args]
    arr = (ctypes.c_void_p * len(vals))(*[ctypes.cast(ctypes.byref(v), ctypes.c_void_p) for v in vals])
    ok(cu.cuLaunchKernel(fn(name), grid[0], grid[1], 1, block, 1, 1, 0, None, arr, None), name)
    ok(cu.cuCtxSynchronize(), name + " sync")


# (이름, 행, K, N, 끝손질, 판 종류: ("타일", BM, BN, T) 또는 ("줄타일", W, T) 또는 ("줄자리", W, T))
경우 = [
    ("정수긴2타일선형", 8, K7, N_qkv, "", ("타일", 32, 256, 128)),
    ("정수줄타일깊은", 8, K7, N_qkv, "", ("줄타일", 64, 128)),
    ("정수작은타일선형_잔차", 8, K7, N_o, "_잔차", ("타일", 32, 64, 128)),
    ("정수줄타일깊은_잔차", 8, K7, N_o, "_잔차", ("줄타일", 64, 128)),
    ("정수긴타일선형_SwiGLU정수", 8, K7, N_gu, "_SwiGLU정수", ("타일", 32, 256, 128)),
    ("정수줄타일깊은_SwiGLU정수", 8, K7, N_gu, "_SwiGLU정수", ("줄타일", 64, 128)),
    ("정수작은타일선형_잔차", 8, F, N_o, "_잔차", ("타일", 32, 64, 128)),
    ("정수줄타일깊은_잔차", 8, F, N_o, "_잔차", ("줄타일", 64, 128)),
    ("정수줄자리_잔차", 4, F, N_o, "_잔차", ("줄자리", 32, 256)),
    ("정수줄타일깊은_잔차", 4, F, N_o, "_잔차", ("줄타일", 64, 128)),
    ("정수줄하나_잔차", 1, F, N_o, "_잔차", ("줄자리", 32, 128)),
    ("정수줄타일깊은_잔차", 1, F, N_o, "_잔차", ("줄타일", 64, 128)),
]

ok(cu.cuProfilerStart(), "cuProfilerStart") if "--모두" in sys.argv else None
for 이름, M, K, N, e, 종류 in 경우:
    Np = (N + 63) // 64 * 64
    자 = alloc(2 * M * K)
    정 = 정보(K)
    값 = alloc((K // 32) * N * 32)
    척 = 척도(K, N)
    치 = alloc(N * 4, b"\0" * (N * 4))
    if e == "_SwiGLU정수":
        다정 = alloc((N // 64) * 64 * 4, b"\0" * ((N // 64) * 64 * 4))
        다자 = alloc(2 * M * (N // 2), b"\0" * (2 * M * (N // 2)))
        출 = [다정, 다자]
    else:
        o = alloc(M * N * 4, b"\0" * (M * N * 4))
        출 = [o, o] if e == "_잔차" else [o]
    if 종류[0] == "타일":
        _, BM, BN, T = 종류
        grid = ((M + BM - 1) // BM, (N + BN - 1) // BN)
        args = [자, 정, 값, 척, 치] + 출 + [M, K, N, Np, 0, 0]
    elif 종류[0] == "줄타일":
        _, W, T = 종류
        grid = ((N + W - 1) // W, 1)
        args = [자, 정, 값, 척, 치] + 출 + [M, K, N, Np, 0, 0]
    else:
        _, W, T = 종류
        grid = ((N + W - 1) // W, 1)
        args = [자, 정, 값, 척, 치] + 출 + [M, K, N]
    launch(이름, grid, T, args)                      # 데우기(JIT)
    ok(cu.cuProfilerStart(), "cuProfilerStart")
    launch(이름, grid, T, args)
    ok(cu.cuProfilerStop(), "cuProfilerStop")
    print(이름, M, K, N, "ok", flush=True)
