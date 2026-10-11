#!/usr/bin/env python3
"""25c 의 기록 — 한 장치의 쿠다 문맥 둘이 번갈아 일할 때 GPU 쪽의 값(엔진과 따로인 탐침 — 파이썬 ctypes, 커널은 전역 시계를 4.5 ms 도는
PTX 열여섯 줄을 손으로 썼다. 엔진 · 도구의 길이 아니다).

'토큰' 하나 = 4.5 ms 커널 둘(한 조각씩 — 7B Q4_0 생성 9 ms 를 둘로 나눈 것과 비슷하다). 토큰의 시간에서 9 ms 를 뺀 것이 그 길의 값:
  문맥 하나            — 한 문맥에서 잇달아(한 조각의 길)
  문맥 하나 · 복사     — 그리고 엔진의 넘김과 같은 복사(잔차 14 KB 장치 안 · 토큰 8 B · 걸음 16 B — 고정 호스트 칸에서)
  문맥 둘 · 사건       — 커널마다 문맥이 다르다(사건으로 잇는다 — 호스트는 기다리지 않는다)
  문맥 둘 · 사건 · 복사 — 그리고 엔진의 넘김(잔차 14 KB 를 고정 호스트 칸을 지나 · 토큰 · 걸음)
  문맥 둘 · 호스트 기다림 — 커널마다 호스트가 기다리고 문맥을 바꾼다(25단계의 첫 판)
길마다 토큰 100 개를 세 번(번갈아), 가운데 값.

  python -I 재기/문맥바꾸기25.py
"""
import ctypes
import sys
import time

cu = ctypes.WinDLL("nvcuda.dll")
V = ctypes.c_void_p
U = ctypes.c_uint64
cu.cuCtxSetCurrent.argtypes = [V]
cu.cuEventCreate.argtypes = [ctypes.POINTER(V), ctypes.c_uint]
cu.cuEventRecord.argtypes = [V, V]
cu.cuStreamWaitEvent.argtypes = [V, V, ctypes.c_uint]
cu.cuModuleLoadData.argtypes = [ctypes.POINTER(V), ctypes.c_char_p]
cu.cuModuleGetFunction.argtypes = [ctypes.POINTER(V), V, ctypes.c_char_p]
cu.cuLaunchKernel.argtypes = [V, ctypes.c_uint, ctypes.c_uint, ctypes.c_uint, ctypes.c_uint, ctypes.c_uint, ctypes.c_uint,
                              ctypes.c_uint, V, ctypes.POINTER(V), V]
cu.cuMemAlloc_v2.argtypes = [ctypes.POINTER(U), ctypes.c_size_t]
cu.cuMemcpyDtoHAsync_v2.argtypes = [V, U, ctypes.c_size_t, V]
cu.cuMemcpyHtoDAsync_v2.argtypes = [U, V, ctypes.c_size_t, V]
cu.cuMemcpyDtoDAsync_v2.argtypes = [U, U, ctypes.c_size_t, V]
cu.cuMemHostAlloc.argtypes = [ctypes.POINTER(V), ctypes.c_size_t, ctypes.c_uint]

PTX = b""".version 7.8
.target sm_89
.address_size 64
.visible .entry spin(.param .u64 n)
{
  .reg .u64 %rd<4>;
  .reg .pred %p;
  ld.param.u64 %rd1, [n];
  mov.u64 %rd2, %globaltimer;
  add.u64 %rd3, %rd2, %rd1;
L:
  mov.u64 %rd2, %globaltimer;
  setp.lt.u64 %p, %rd2, %rd3;
  @%p bra L;
  ret;
}
"""


def ok(r, w):
    if r != 0:
        raise SystemExit(f"{w}: 쿠다 오류 {r}")


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    ok(cu.cuInit(0), "cuInit")
    dev = ctypes.c_int()
    ok(cu.cuDeviceGet(ctypes.byref(dev), 0), "cuDeviceGet")

    def 할당():
        x = U()
        ok(cu.cuMemAlloc_v2(ctypes.byref(x), 1 << 20), "cuMemAlloc")
        return x.value

    def 문맥(첫):
        c = V()
        if 첫:
            ok(cu.cuDevicePrimaryCtxRetain(ctypes.byref(c), dev), "cuDevicePrimaryCtxRetain")
        else:
            ok(cu.cuCtxCreate_v2(ctypes.byref(c), 0, dev), "cuCtxCreate")
        ok(cu.cuCtxSetCurrent(c), "cuCtxSetCurrent")
        m = V()
        ok(cu.cuModuleLoadData(ctypes.byref(m), PTX), "cuModuleLoadData")
        f = V()
        ok(cu.cuModuleGetFunction(ctypes.byref(f), m, b"spin"), "cuModuleGetFunction")
        e = V()
        ok(cu.cuEventCreate(ctypes.byref(e), 2), "cuEventCreate")
        return c, f, e

    c0, f0, e0 = 문맥(True)
    h0, t0, g0, h0b = 할당(), 할당(), 할당(), 할당()
    고정 = V()
    ok(cu.cuMemHostAlloc(ctypes.byref(고정), 1 << 20, 1), "cuMemHostAlloc")
    G = 고정.value
    c1, f1, e1 = 문맥(False)
    h1, t1 = 할당(), 할당()
    ns = U(4_500_000)
    인자 = (V * 1)(ctypes.cast(ctypes.pointer(ns), V))

    def 돌기(f):
        ok(cu.cuLaunchKernel(f, 1, 1, 1, 32, 1, 1, 0, None, 인자, None), "cuLaunchKernel")

    def 맞추기():
        for c in (c0, c1):
            ok(cu.cuCtxSetCurrent(c), "cuCtxSetCurrent")
            ok(cu.cuCtxSynchronize(), "cuCtxSynchronize")

    def 하나(n):
        ok(cu.cuCtxSetCurrent(c0), "s")
        for _ in range(n):
            돌기(f0)
            돌기(f0)

    def 하나_복사(n):
        ok(cu.cuCtxSetCurrent(c0), "s")
        for _ in range(n):
            ok(cu.cuMemcpyHtoDAsync_v2(t0, V(G + 65536), 8, None), "h2d")
            ok(cu.cuMemcpyHtoDAsync_v2(g0, V(G + 65544), 16, None), "h2d")
            돌기(f0)
            ok(cu.cuMemcpyDtoDAsync_v2(h0b, h0, 14336, None), "d2d")
            돌기(f0)
            ok(cu.cuMemcpyDtoHAsync_v2(V(G + 65536), t0, 8, None), "d2h")

    def 둘_사건(n, 복사=False):
        for _ in range(n):
            ok(cu.cuCtxSetCurrent(c0), "s")
            ok(cu.cuStreamWaitEvent(None, e1, 0), "wait")
            if 복사:
                ok(cu.cuMemcpyHtoDAsync_v2(t0, V(G + 65536), 8, None), "h2d")
                ok(cu.cuMemcpyHtoDAsync_v2(g0, V(G + 65544), 16, None), "h2d")
            돌기(f0)
            if 복사:
                ok(cu.cuMemcpyDtoHAsync_v2(V(G), h0, 14336, None), "d2h")
            ok(cu.cuEventRecord(e0, None), "record")
            ok(cu.cuCtxSetCurrent(c1), "s")
            ok(cu.cuStreamWaitEvent(None, e0, 0), "wait")
            if 복사:
                ok(cu.cuMemcpyHtoDAsync_v2(h1, V(G), 14336, None), "h2d")
            돌기(f1)
            if 복사:
                ok(cu.cuMemcpyDtoHAsync_v2(V(G + 65536), t1, 8, None), "d2h")
            ok(cu.cuEventRecord(e1, None), "record")

    def 둘_기다림(n):
        for _ in range(n):
            ok(cu.cuCtxSetCurrent(c0), "s")
            돌기(f0)
            ok(cu.cuCtxSynchronize(), "sync")
            ok(cu.cuCtxSetCurrent(c1), "s")
            돌기(f1)
            ok(cu.cuCtxSynchronize(), "sync")

    길들 = (("문맥 하나", 하나), ("문맥 하나 · 복사", 하나_복사), ("문맥 둘 · 사건", 둘_사건),
           ("문맥 둘 · 사건 · 복사", lambda n: 둘_사건(n, True)), ("문맥 둘 · 호스트 기다림", 둘_기다림))
    값 = {이름: [] for 이름, _ in 길들}
    N = 100
    for _ in range(3):
        for 이름, f in 길들:
            맞추기()
            f(5)
            맞추기()
            t = time.perf_counter()
            f(N)
            맞추기()
            값[이름].append((time.perf_counter() - t) / N * 1e3)
    for 이름, _ in 길들:
        xs = sorted(값[이름])
        print(f"{이름}: 토큰 {xs[1]:.4f} ms (세 번 {', '.join(f'{x:.4f}' for x in 값[이름])}) — 9 ms 를 넘는 것 {(xs[1] - 9.0) * 1e3:.1f} µs",
              flush=True)


if __name__ == "__main__":
    main()
