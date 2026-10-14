"""34단계 탐침 — 뒷단의 "이미 버린 값" 분석(큰쪽 · 실수 비교 · 부호반전의 입력 버림을 다시 하지 않음)이 값을 바꾸지 않는가.
   같은 버림탐침.gl 을 예전 뒷단(늘 버림)과 새 뒷단으로 만든 둘을 돌려 출력이 비트까지 같은지, 그리고 읽은 값 쪽은 CPU 의 규칙 R
   (비정규수 입력 → 부호를 지킨 0)과 같은지 본다.
   python -I -X utf8 버림탐침.py <탐침/vulkan 폴더> <예전 spvs> <새 spvs> [장치 이름]"""
import sys

sys.path.insert(0, sys.argv[1])
import numpy as np  # noqa: E402
import vk뒷단 as B  # noqa: E402


def 진입(이름):
    return "_G" + 이름.encode("utf-8").hex()


rng = np.random.default_rng(34)
N = 1 << 16


def 무늬(n):
    """비정규수 · ±0 · 정규수 경계 · 보통 · 무한 · NaN 을 섞은 짧은실수의 비트"""
    k = rng.integers(0, 16, n)
    부호 = rng.integers(0, 2, n).astype(np.uint32) << 31
    가수 = rng.integers(0, 1 << 23, n).astype(np.uint32)
    지수 = rng.integers(1, 255, n).astype(np.uint32)
    b = 부호 | (지수 << 23) | 가수                                         # 보통
    b = np.where(k < 4, 부호 | 가수, b)                                    # 비정규수(가수 0 이면 ±0)
    b = np.where(k == 4, 부호, b)                                          # ±0
    b = np.where(k == 5, 부호 | (np.uint32(1) << 23) | 가수, b)            # 가장 작은 정규수 둘레
    b = np.where(k == 6, 부호 | (rng.integers(100, 130, n).astype(np.uint32) << 23) | 가수, b)   # 곱하면 비정규수가 되는 쪽
    b = np.where(k == 7, 부호 | np.uint32(0x7F800000), b)                  # ±무한
    b = np.where((k == 8) & (rng.integers(0, 8, n) == 0), np.uint32(0x7FC00000) | 가수, b)       # NaN 조금
    return b.astype(np.uint32)


def 버림(b):
    return np.where((b & 0x7F800000) == 0, b & 0x80000000, b).astype(np.uint32)


def 실(b):
    return b.view(np.float32)


def 돌리기(spvs, 이름, a, bb, s):
    d = B.장치(sys.argv[4] if len(sys.argv) > 4 else "NVIDIA")
    d.모듈(spvs)
    out = {}
    pa, pb, pd = d.할당(N * 4 * 4), d.할당(N * 4 * 4), d.할당(N * 4 * 4)
    d.올리기(pa, a)
    d.올리기(pb, bb)
    if 이름 == "읽은값버림":
        d.띄우기(진입(이름), (N // 256,), (256, 1, 1), [(1, pa), (1, pb), (1, pd), (0, N)])
    elif 이름 == "산술값버림":
        d.띄우기(진입(이름), (N // 256,), (256, 1, 1), [(1, pa), (1, pb), (1, pd), (0, s), (0, N)])
    else:
        d.띄우기(진입(이름), (N // 256,), (256, 1, 1), [(1, pa), (1, pd), (0, s), (0, N)])
    d.맞추기()
    out = d.내리기(pd, np.zeros(N * 4, np.uint32))
    d.닫기()
    return out


a = 무늬(N * 4)
b = 무늬(N * 4)
다름 = 0
for 이름, 비늘 in [("읽은값버림", [0.0]), ("산술값버림", [1.0, 2.0 ** -20, 2.0 ** -40, 3.0]), ("지역값버림", [1.0, 2.0 ** -20, 2.0 ** -30])]:
    for s in 비늘:
        옛 = 돌리기(sys.argv[2], 이름, a, b, s)
        새 = 돌리기(sys.argv[3], 이름, a, b, s)
        칸 = N * 4 if 이름 != "지역값버림" else N
        d = int((옛[:칸] != 새[:칸]).sum())
        다름 += d
        덧 = ""
        if 이름 == "읽은값버림":
            fa, fb = 버림(a[:N]), 버림(b[:N])
            r = 새[:N * 4].reshape(N, 4)
            xa, xb = 실(fa), 실(fb)
            큼 = np.where(np.isnan(xa), fb, np.where(np.isnan(xb), fa, np.where(xa > xb, fa, np.where(xb > xa, fb, 0))))
            같음칸 = (xa == xb) & ~np.isnan(xa)
            둘다NaN = np.isnan(xa) & np.isnan(xb)
            맞음 = np.where(같음칸, (r[:, 0] == fa) | (r[:, 0] == fb), r[:, 0] == 큼)
            맞음 = np.where(둘다NaN, np.isnan(실(r[:, 0].copy())), 맞음)
            맞음 &= r[:, 1] == (xa < xb).astype(np.uint32)
            # 부호반전: NaN 은 어떤 NaN 이든(31f — 장치가 NaN 의 비트를 지키지 않는다: 0x7FFFFFFF)
            맞음 &= np.where(np.isnan(xa), np.isnan(실(r[:, 2].copy())), r[:, 2] == (fa ^ np.uint32(0x80000000)))
            맞음 &= r[:, 3] == (xa == 0).astype(np.uint32)
            덧 = f" · CPU 규칙 R 과 다른 칸 {int((~맞음).sum())}"
            다름 += int((~맞음).sum())
        print(f"{이름} s={s:g}: 예전 대 새 다른 칸 {d}{덧}")
print("버림 탐침:", "모두 같음" if 다름 == 0 else f"다름 {다름}")
