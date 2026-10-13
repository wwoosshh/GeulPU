"""31단계 탐침 — 계약의 Q8_0 행렬곱 한 칸을 Vulkan 으로 돌려 CPU 기준(유리수로 정확히)과 비트로 대조하고, 장치마다의 능력을 적는다.
   python -X utf8 탐침31.py [결과.json]   — 이 PC 의 Vulkan 장치 모두(NVIDIA · Intel 내장 그래픽 …)에서."""
import json
import os
import random
import struct
import sys
from fractions import Fraction

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import spv  # noqa: E402
import vk as V  # noqa: E402

TWO = Fraction(2)
MIN_NORMAL = Fraction(1, 2 ** 126)


# ---------------- CPU 기준: 짧은실수(binary32)로 정확히 한 번 반올림 ----------------
def bits(x):
    return struct.unpack("<I", struct.pack("<f", x))[0]


def neg(x):
    return bits(x) >> 31 == 1


def round_f32(q, zero_neg=False):
    if q == 0:
        return -0.0 if zero_neg else 0.0
    s = -1.0 if q < 0 else 1.0
    a = -q if q < 0 else q
    e = a.numerator.bit_length() - a.denominator.bit_length()
    if TWO ** e > a:
        e -= 1
    se = max(e, -126) - 23
    m = a / TWO ** se
    n = m.numerator // m.denominator
    rem = m - n
    if rem > Fraction(1, 2) or (rem == Fraction(1, 2) and n % 2 == 1):
        n += 1
    v = Fraction(n) * TWO ** se
    if v >= TWO ** 128:
        return s * float("inf")
    if v == 0:
        return -0.0 if s < 0 else 0.0
    return s * float(v)


def mul(a, b):
    return round_f32(Fraction(a) * Fraction(b), zero_neg=neg(a) != neg(b))


def add(a, b):
    return round_f32(Fraction(a) + Fraction(b), zero_neg=neg(a) and neg(b))


def fma(a, b, c):
    return round_f32(Fraction(a) * Fraction(b) + Fraction(c), zero_neg=(neg(a) != neg(b)) and neg(c))


def ftz(x):
    return (-0.0 if neg(x) else 0.0) if x != 0 and abs(Fraction(x)) < MIN_NORMAL else x


def reference(case, kind):
    """kind: fused · sep (곱 · 더하기 따로) · fused_ftz · sep_ftz (비정규수를 0 으로)"""
    M, N, K, A0, A1, W, P, D = (case[k] for k in ("M", "N", "K", "A0", "A1", "W", "P", "D"))
    NB = K // 32
    z = ftz if kind.endswith("ftz") else (lambda x: x)
    out = []
    for r in range(M):
        for c in range(N):
            y = 0.0
            for b in range(NB):
                s0 = s1 = 0
                for i in range(32):
                    w = W[c * K + b * 32 + i]
                    s0 += A0[r * K + b * 32 + i] * w
                    s1 += A1[r * K + b * 32 + i] * w
                u = round_f32(Fraction(s1 * 256 + s0))
                pd = z(mul(z(P[r * NB + b]), z(D[c * NB + b])))
                if kind.startswith("fused"):
                    y = z(fma(u, pd, z(y)))
                else:
                    y = z(add(z(mul(u, pd)), z(y)))
            out.append(bits(y))
    return out


# ---------------- 시험 자료 ----------------
def f16_value(h):
    return float(struct.unpack("<e", struct.pack("<H", h))[0])


def digits(n):
    d0 = ((n + 128) & 255) - 128
    return d0, (n - d0) >> 8


def make_case(rng, M, N, K, nrange, wrange, erange, drange, aligned=False):
    NB = K // 32
    A0, A1, W = [], [], []
    W = [rng.randint(-wrange, wrange) for _ in range(N * K)]
    for r in range(M):
        for k in range(K):
            if aligned:                                         # 큰 T(2^24 넘음 — 정수 → 실수 반올림을 시험)
                n = rng.randint(nrange // 2, nrange) * (1 if W[(r % N) * K + k] >= 0 else -1)
            else:
                n = rng.randint(-nrange, nrange)
            d0, d1 = digits(n)
            A0.append(d0)
            A1.append(d1)
    P = [float(TWO ** (rng.randint(*erange) - 13)) for _ in range(M * NB)]
    D = []
    for _ in range(N * NB):
        while True:
            h = rng.randint(drange[0], drange[1]) | (rng.randint(0, 1) << 15)
            v = f16_value(h)
            if v == v and abs(v) != float("inf") and v != 0:
                D.append(v)
                break
    return {"M": M, "N": N, "K": K, "A0": A0, "A1": A1, "W": W, "P": P, "D": D}


def cases():
    rng = random.Random(31)
    return {
        "무작위": make_case(rng, 64, 64, 256, 16384, 127, (-30, 30), (0x0400, 0x7BFF)),          # 4096 칸, 블록 8
        "큰T": make_case(rng, 16, 16, 256, 16384, 127, (-10, 10), (0x0400, 0x7BFF), aligned=True),
        "비정규수": make_case(rng, 16, 16, 64, 3, 2, (-98, -90), (0x0001, 0x07FF)),               # 아주 작은 척도 · 작은 자리
        "큰지수": make_case(rng, 16, 16, 128, 16384, 127, (40, 60), (0x3C00, 0x7BFF)),
    }


def pack_i(xs):
    return struct.pack("<%di" % len(xs), *xs)


def pack_f(xs):
    return struct.pack("<%df" % len(xs), *xs)


def run_case(dev, case, variant, denorm_mode=None):
    M, N, K = case["M"], case["N"], case["K"]
    code = spv.q8_block_kernel(M, N, K, variant, denorm_mode)
    bufs = [dev.buffer(pack_i(case["A0"])), dev.buffer(pack_i(case["A1"])), dev.buffer(pack_i(case["W"])),
            dev.buffer(pack_f(case["P"])), dev.buffer(pack_f(case["D"])), dev.buffer(b"\0" * (4 * M * N))]
    dev.run(code, bufs, (N // 8, M // 8, 1))
    import ctypes
    raw = ctypes.string_at(bufs[5][1], 4 * M * N)
    return list(struct.unpack("<%dI" % (M * N), raw))


COMP = {0: "FLOAT16", 1: "FLOAT32", 2: "FLOAT64", 3: "SINT8", 4: "SINT16", 5: "SINT32", 6: "SINT64", 7: "UINT8", 8: "UINT16",
        9: "UINT32", 10: "UINT64", 1000141000: "BFLOAT16"}
SCOPE = {1: "Device", 2: "Workgroup", 3: "Subgroup", 5: "QueueFamily"}


def main():
    out_path = sys.argv[1] if len(sys.argv) > 1 else None
    cs = cases()
    print("CPU 기준 계산 중 …", flush=True)
    refs = {name: {k: reference(c, k) for k in ("fused", "sep", "fused_ftz", "sep_ftz")} for name, c in cs.items()}
    for name in cs:
        r = refs[name]
        print(f"  {name}: 칸 {len(r['fused'])} · 합친 대 따로 다른 칸 {sum(a != b for a, b in zip(r['fused'], r['sep']))}"
              f" · 비정규수 보존 대 버림 다른 칸 {sum(a != b for a, b in zip(r['fused'], r['fused_ftz']))}")
    v = V.Vk()
    report = {"devices": []}
    for pd in v.pds:
        p = v.props(pd)
        exts = v.extensions(pd)
        cm = v.coopmat(pd) if "VK_KHR_cooperative_matrix" in exts else None
        int_cm = sorted({(a[0], a[1], a[2], COMP.get(a[3]), COMP.get(a[5]), COMP.get(a[6]), SCOPE.get(a[7])) for a in (cm or [])
                         if a[3] in (3, 7)})
        info = dict(p)
        info["VK_KHR_shader_fma"] = "VK_KHR_shader_fma" in exts
        info["VK_KHR_cooperative_matrix"] = "VK_KHR_cooperative_matrix" in exts
        info["coopmat_int8"] = [list(x) for x in int_cm]
        info["VK_NV_cooperative_matrix2"] = "VK_NV_cooperative_matrix2" in exts
        print(f"\n== {p['name']} (Vulkan {p['api']}, 업체 {p['vendor']})")
        for k in ("subgroup_size", "subgroup_min_max", "denorm_preserve_f32", "denorm_ftz_f32", "rte_f32", "denorm_independence",
                  "dot_4x8_packed_signed_accel", "VK_KHR_shader_fma", "VK_KHR_cooperative_matrix", "VK_NV_cooperative_matrix2"):
            print(f"  {k}: {info[k]}")
        print(f"  coopmat int8 모양: {int_cm if int_cm else '없음'}")
        dev = V.Device(v, pd)
        results = {}
        variants = [("fma", None), ("sep", None)]
        if p["denorm_preserve_f32"]:
            variants += [("fma", "preserve"), ("sep", "preserve")]
        if p["denorm_ftz_f32"]:
            variants += [("fma", "ftz")]
        for name, c in cs.items():
            for var, dm in variants:
                key = f"{name}/{var}" + (f"+{dm}" if dm else "")
                try:
                    got = run_case(dev, c, var, dm)
                except Exception as e:  # noqa: BLE001
                    results[key] = {"오류": str(e)}
                    print(f"  {key}: 오류 {e}")
                    continue
                m = {k: sum(a == b for a, b in zip(got, refs[name][k])) for k in refs[name]}
                total = len(got)
                best = [k for k, n in m.items() if n == total]
                import hashlib
                results[key] = {"칸": total, "맞음": m, "완전히맞는기준": best,
                                "출력_sha256": hashlib.sha256(struct.pack("<%dI" % total, *got)).hexdigest()}
                if name == "비정규수":
                    results[key]["출력"] = got
                    results[key]["기준"] = {k: refs[name][k] for k in ("fused", "fused_ftz")}
                print(f"  {key}: " + " · ".join(f"{k} {n}/{total}" for k, n in m.items()) + (f"  → {best}" if best else "  → 어느 기준과도 다 맞지 않음"))
        dev.close()
        info["결과"] = results
        report["devices"].append(info)
    if out_path:
        json.dump(report, open(out_path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        print("\n결과 →", out_path)


if __name__ == "__main__":
    main()
