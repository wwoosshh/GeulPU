#!/usr/bin/env python3
"""25단계의 기록 — 한 장치의 쿠다 문맥 둘 사이 넘김 방법의 값(엔진과 따로인 탐침 — 파이썬 ctypes, 커널 없이 복사만).
한 바퀴 = 조각 0 → 1 로 14 KB(7B 잔차 한 행) · 조각 1 → 0 으로 8 B(토큰). '띄우기' 는 호스트가 바퀴 하나를 내는 시간(막히면 길다),
'끝까지' 는 끝까지 기다린 시간:
  문맥 하나 · 장치 안 비동기 복사   — 견줄 바탕
  피어 동기(cuMemcpyPeer)            — 25단계 첫 판의 넘김
  피어 비동기(cuMemcpyPeerAsync)      — 사건 없이 · 문맥을 건너는 사건과 함께
  고정 호스트 칸 경유 비동기 + 사건   — 25단계의 넘김(같은 장치의 문맥 사이 — 피어 접근이 없다)
그리고 피어 접근을 켜 본 값(cuCtxEnablePeerAccess — 같은 장치의 문맥끼리는 217 이 온다).

  python -I 재기/넘김재기25.py
"""
import ctypes
import sys
import time

cu = ctypes.WinDLL("nvcuda.dll")
V = ctypes.c_void_p
U = ctypes.c_uint64
cu.cuMemAlloc_v2.argtypes = [ctypes.POINTER(U), ctypes.c_size_t]
cu.cuMemcpyPeerAsync.argtypes = [U, V, U, V, ctypes.c_size_t, V]
cu.cuMemcpyPeer.argtypes = [U, V, U, V, ctypes.c_size_t]
cu.cuMemcpyDtoDAsync_v2.argtypes = [U, U, ctypes.c_size_t, V]
cu.cuMemcpyDtoHAsync_v2.argtypes = [V, U, ctypes.c_size_t, V]
cu.cuMemcpyHtoDAsync_v2.argtypes = [U, V, ctypes.c_size_t, V]
cu.cuEventRecord.argtypes = [V, V]
cu.cuStreamWaitEvent.argtypes = [V, V, ctypes.c_uint]
cu.cuCtxSetCurrent.argtypes = [V]
cu.cuEventCreate.argtypes = [ctypes.POINTER(V), ctypes.c_uint]
cu.cuMemHostAlloc.argtypes = [ctypes.POINTER(V), ctypes.c_size_t, ctypes.c_uint]
cu.cuCtxEnablePeerAccess.argtypes = [V, ctypes.c_uint]


def ok(r, w):
    if r != 0:
        raise SystemExit(f"{w}: 쿠다 오류 {r}")


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    ok(cu.cuInit(0), "cuInit")
    dev = ctypes.c_int()
    ok(cu.cuDeviceGet(ctypes.byref(dev), 0), "cuDeviceGet")
    c0, c1 = V(), V()
    ok(cu.cuDevicePrimaryCtxRetain(ctypes.byref(c0), dev), "cuDevicePrimaryCtxRetain")
    ok(cu.cuCtxSetCurrent(c0), "cuCtxSetCurrent")

    def 할당():
        x = U()
        ok(cu.cuMemAlloc_v2(ctypes.byref(x), 1 << 20), "cuMemAlloc")
        return x.value

    a0, t0, b0, u0 = 할당(), 할당(), 할당(), 할당()
    e0 = V()
    ok(cu.cuEventCreate(ctypes.byref(e0), 2), "cuEventCreate")
    h = V()
    ok(cu.cuMemHostAlloc(ctypes.byref(h), 1 << 20, 1), "cuMemHostAlloc")      # CU_MEMHOSTALLOC_PORTABLE
    H = h.value
    ok(cu.cuCtxCreate_v2(ctypes.byref(c1), 0, dev), "cuCtxCreate")
    a1, t1 = 할당(), 할당()
    e1 = V()
    ok(cu.cuEventCreate(ctypes.byref(e1), 2), "cuEventCreate")
    R = 14336

    def 문맥하나():
        ok(cu.cuMemcpyDtoDAsync_v2(b0, a0, R, None), "d2d")
        ok(cu.cuMemcpyDtoDAsync_v2(t0, u0, 8, None), "d2d")

    def 피어_동기():
        ok(cu.cuMemcpyPeer(a1, c1, a0, c0, R), "peer")
        ok(cu.cuMemcpyPeer(t0, c0, t1, c1, 8), "peer")

    def 피어_사건없이():
        ok(cu.cuCtxSetCurrent(c1), "s")
        ok(cu.cuMemcpyPeerAsync(a1, c1, a0, c0, R, None), "peer async")
        ok(cu.cuCtxSetCurrent(c0), "s")
        ok(cu.cuMemcpyPeerAsync(t0, c0, t1, c1, 8, None), "peer async")

    def 피어_사건():
        ok(cu.cuCtxSetCurrent(c1), "s")
        ok(cu.cuStreamWaitEvent(None, e0, 0), "wait")
        ok(cu.cuMemcpyPeerAsync(a1, c1, a0, c0, R, None), "peer async")
        ok(cu.cuEventRecord(e1, None), "record")
        ok(cu.cuCtxSetCurrent(c0), "s")
        ok(cu.cuStreamWaitEvent(None, e1, 0), "wait")
        ok(cu.cuMemcpyPeerAsync(t0, c0, t1, c1, 8, None), "peer async")
        ok(cu.cuEventRecord(e0, None), "record")

    def 호스트경유():
        ok(cu.cuCtxSetCurrent(c0), "s")
        ok(cu.cuMemcpyDtoHAsync_v2(V(H), a0, R, None), "d2h")
        ok(cu.cuEventRecord(e0, None), "record")
        ok(cu.cuCtxSetCurrent(c1), "s")
        ok(cu.cuStreamWaitEvent(None, e0, 0), "wait")
        ok(cu.cuMemcpyHtoDAsync_v2(a1, V(H), R, None), "h2d")
        ok(cu.cuMemcpyDtoHAsync_v2(V(H + 65536), t1, 8, None), "d2h")
        ok(cu.cuEventRecord(e1, None), "record")
        ok(cu.cuCtxSetCurrent(c0), "s")
        ok(cu.cuStreamWaitEvent(None, e1, 0), "wait")
        ok(cu.cuMemcpyHtoDAsync_v2(t0, V(H + 65536), 8, None), "h2d")

    def 맞추기():
        for c in (c0, c1):
            ok(cu.cuCtxSetCurrent(c), "s")
            ok(cu.cuCtxSynchronize(), "sync")

    길들 = (("문맥 하나 · 장치 안 비동기 복사", 문맥하나), ("피어 동기(cuMemcpyPeer)", 피어_동기),
           ("피어 비동기(cuMemcpyPeerAsync) · 사건 없이", 피어_사건없이), ("피어 비동기(cuMemcpyPeerAsync) + 사건", 피어_사건),
           ("고정 호스트 칸 경유 비동기 + 사건", 호스트경유))
    N = 1000
    for 이름, f in 길들:
        값 = []
        for _ in range(3):
            맞추기()
            ok(cu.cuCtxSetCurrent(c0), "s")
            for _ in range(20):
                f()
            맞추기()
            ok(cu.cuCtxSetCurrent(c0), "s")
            t = time.perf_counter()
            for _ in range(N):
                f()
            tq = time.perf_counter() - t
            맞추기()
            값.append((tq / N * 1e6, (time.perf_counter() - t) / N * 1e6))
        값.sort(key=lambda x: x[1])
        q, e = 값[1]
        print(f"{이름}: 띄우기 {q:.1f} µs/바퀴 · 끝까지 {e:.1f} µs/바퀴 (세 번의 가운데)", flush=True)
    ok(cu.cuCtxSetCurrent(c1), "s")
    print(f"피어 접근 켜기(cuCtxEnablePeerAccess, 같은 장치의 문맥 둘): {cu.cuCtxEnablePeerAccess(c0, 0)}", flush=True)


if __name__ == "__main__":
    main()
