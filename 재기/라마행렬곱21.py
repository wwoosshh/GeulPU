#!/usr/bin/env python3
"""21단계 — llama.cpp(b11496, CUDA) 의 행렬곱을 ggml C API 로 직접(ggml_mul_mat, Q8_0 — MMQ). 7B 층 0 의 실제 가중치 일곱(q · k · v · o ·
gate · up · down)을 한 그래프로 — 행 512 · 2048 · 8192. 시간 = 그래프 계산(동기) 한 번의 벽시계, 20 ms 넘게 데운 뒤 일곱 번 × 세 묶음의
중앙값의 중앙값(ms). 행렬곱마다의 그래프도 따로 잰다(기록 — 부를 때마다 동기화 몫이 든다).

  python -I 재기/라마행렬곱21.py <7B gguf> <출력.json>
"""
import ctypes
import json
import os
import struct
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, ".."))
LL = os.path.join(ROOT, "도구", "llama-b11496")
F32, Q8_0 = 0, 8
P = ctypes.c_void_p
I64, SZ = ctypes.c_int64, ctypes.c_size_t


class InitParams(ctypes.Structure):
    _fields_ = [("mem_size", ctypes.c_size_t), ("mem_buffer", ctypes.c_void_p), ("no_alloc", ctypes.c_bool)]


class GG:
    """ggml 의 C API 중 여기서 쓰는 것만(감사 A3 의 라마검사.py 와 같은 꼴)."""

    def __init__(self):
        os.environ["PATH"] = LL + os.pathsep + os.environ.get("PATH", "")
        os.add_dll_directory(LL)
        self.libs = [ctypes.CDLL(os.path.join(LL, n)) for n in ("ggml-base.dll", "ggml.dll")]
        d = self.fn
        self.init = d("ggml_init", P, InitParams)
        self.free = d("ggml_free", None, P)
        self.new2 = d("ggml_new_tensor_2d", P, P, ctypes.c_int, I64, I64)
        self.mul_mat = d("ggml_mul_mat", P, P, P, P)
        self.new_graph = d("ggml_new_graph", P, P)
        self.build = d("ggml_build_forward_expand", None, P, P)
        self.tensor_overhead = d("ggml_tensor_overhead", SZ)
        self.graph_overhead = d("ggml_graph_overhead", SZ)
        self.load_all = d("ggml_backend_load_all_from_path", None, ctypes.c_char_p)
        self.init_by_name = d("ggml_backend_init_by_name", P, ctypes.c_char_p, ctypes.c_char_p)
        self.alloc_ctx = d("ggml_backend_alloc_ctx_tensors", P, P, P)
        self.tset = d("ggml_backend_tensor_set", None, P, P, SZ, SZ)
        self.compute = d("ggml_backend_graph_compute", ctypes.c_int, P, P)
        self.buf_free = d("ggml_backend_buffer_free", None, P)
        self.load_all(LL.encode())
        self.cuda = self.init_by_name(b"CUDA0", None)
        assert self.cuda, "CUDA0 백엔드를 열지 못했다"

    def fn(self, name, res, *args):
        for lib in self.libs:
            try:
                f = getattr(lib, name)
            except AttributeError:
                continue
            f.restype, f.argtypes = res, list(args)
            return f
        raise AttributeError(name)


def gguf텐서(path, 이름들):
    """GGUF 의 텐서 날 바이트(np.memmap) — 머리만 읽는다(8 GB 를 통째로 읽지 않게). {이름: (형식, (ne0, ne1), 바이트)}"""
    with open(path, "rb") as f:
        b = f.read(64 << 20)

    def s(o):
        n = struct.unpack_from("<Q", b, o)[0]
        return b[o + 8:o + 8 + n].decode("utf-8", "replace"), o + 8 + n

    def v(o, t):
        fm = {0: "<B", 1: "<b", 2: "<H", 3: "<h", 4: "<I", 5: "<i", 6: "<f", 7: "<?", 10: "<Q", 11: "<q", 12: "<d"}
        if t in fm:
            return struct.unpack_from(fm[t], b, o)[0], o + struct.calcsize(fm[t])
        if t == 8:
            return s(o)
        et, n = struct.unpack_from("<IQ", b, o)
        o += 12
        for _ in range(n):
            _, o = v(o, et)
        return None, o
    ver, nt, nkv = struct.unpack_from("<IQQ", b, 4)
    o = 24
    meta = {}
    for _ in range(nkv):
        k, o = s(o)
        t = struct.unpack_from("<I", b, o)[0]
        meta[k], o = v(o + 4, t)
    info = {}
    for _ in range(nt):
        name, o = s(o)
        nd = struct.unpack_from("<I", b, o)[0]
        dims = struct.unpack_from(f"<{nd}Q", b, o + 4)
        t, off = struct.unpack_from("<IQ", b, o + 4 + 8 * nd)
        o += 4 + 8 * nd + 12
        info[name] = (t, dims, off)
    al = meta.get("general.alignment", 32)
    data0 = (o + al - 1) // al * al
    mm = np.memmap(path, dtype=np.uint8, mode="r")
    out = {}
    for name in 이름들:
        t, dims, off = info[name]
        assert t == Q8_0, name
        nb = int(np.prod(dims)) // 32 * 34
        out[name] = (t, dims, mm[data0 + off:data0 + off + nb])
    return meta, out


def 중앙(v):
    return sorted(v)[len(v) // 2]


def 재기(g, graph):
    t0 = time.perf_counter()
    while time.perf_counter() - t0 < 0.02:
        assert g.compute(g.cuda, graph) == 0
    묶 = []
    for _ in range(3):
        v = []
        for _ in range(7):
            a = time.perf_counter()
            assert g.compute(g.cuda, graph) == 0
            v.append((time.perf_counter() - a) * 1000)
        묶.append(중앙(v))
    return 중앙(묶)


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    path, 출력 = sys.argv[1], sys.argv[2]
    이름 = ["attn_q", "attn_k", "attn_v", "attn_output", "ffn_gate", "ffn_up", "ffn_down"]
    meta, ts = gguf텐서(path, [f"blk.0.{n}.weight" for n in 이름])
    D = ts["blk.0.attn_q.weight"][1][0]
    F = ts["blk.0.ffn_gate.weight"][1][1]
    g = GG()
    결과 = {"시작": time.strftime("%Y-%m-%d %H:%M:%S"), "D": D, "F": F, "행": {}}
    rng = np.random.default_rng(2112)
    for M in (512, 2048, 8192):
        ctx = g.init(InitParams(g.tensor_overhead() * 64 + g.graph_overhead() * 16 + (1 << 20), None, True))
        W = {n: g.new2(ctx, Q8_0, ts[f"blk.0.{n}.weight"][1][0], ts[f"blk.0.{n}.weight"][1][1]) for n in 이름}
        xD = g.new2(ctx, F32, D, M)
        xF = g.new2(ctx, F32, F, M)
        outs = {n: g.mul_mat(ctx, W[n], xF if n == "ffn_down" else xD) for n in 이름}
        전체 = g.new_graph(ctx)
        for n in 이름:
            g.build(전체, outs[n])
        따로 = {}
        for n in 이름:
            gr = g.new_graph(ctx)
            g.build(gr, outs[n])
            따로[n] = gr
        buf = g.alloc_ctx(ctx, g.cuda)
        assert buf, "CUDA 버퍼를 잡지 못했다"
        for n in 이름:
            raw = np.ascontiguousarray(ts[f"blk.0.{n}.weight"][2])
            g.tset(W[n], raw.ctypes.data, 0, raw.nbytes)
        a = rng.uniform(-1, 1, (M, D)).astype(np.float32)
        g.tset(xD, a.ctypes.data, 0, a.nbytes)
        a2 = rng.uniform(-1, 1, (M, F)).astype(np.float32)
        g.tset(xF, a2.ctypes.data, 0, a2.nbytes)
        한 = 재기(g, 전체)
        각 = {n: 재기(g, 따로[n]) for n in 이름}
        결과["행"][M] = {"층 하나(한 그래프) ms": 한, "행렬곱마다 ms": 각}
        print(f"행 {M}: 층 하나 {한:.4f} ms · " + " · ".join(f"{n} {t:.4f}" for n, t in 각.items()), flush=True)
        g.buf_free(buf)
        g.free(ctx)
    json.dump(결과, open(출력, "w", encoding="utf-8"), ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
