"""34단계 탐침 — 범위가 증명되지 않은 64 비트 나눗셈 · 나머지(SPIR-V 뒷단: 32 비트 빠른 길 · 긴 나눗셈)가 CPU 와 같은가.
   python -I -X utf8 나눗셈탐침.py <탐침/vulkan 폴더> <spvs> [장치 이름]"""
import sys

sys.path.insert(0, sys.argv[1])
import numpy as np  # noqa: E402
import vk뒷단 as B  # noqa: E402


def 진입(이름):
    return "_G" + 이름.encode("utf-8").hex()


def 참(a, b):
    """잘라내는 나눗셈(C · PTX 의 div.s64) — 몫은 0 쪽으로, 나머지는 나뉘는 수의 부호"""
    q = abs(a) // abs(b)
    if (a < 0) != (b < 0):
        q = -q
    return q, a - b * q


def 넣기(목록, a, b):
    if b == 0 or (a == -(1 << 63) and b == -1):     # 언어의 정의 밖(UB)
        return
    목록.append((a, b))


rng = np.random.default_rng(34)
쌍 = []
경계 = [0, 1, 2, 3, 7, 255, 256, 65535, 65536, (1 << 31) - 1, 1 << 31, (1 << 32) - 1, 1 << 32, (1 << 33) + 5,
        (1 << 62), (1 << 63) - 1]
경계 = 경계 + [-x for x in 경계] + [-(1 << 63)]
for a in 경계:
    for b in 경계:
        넣기(쌍, a, b)
무리 = [
    ("작은 둘(빠른 길)", lambda n: (rng.integers(0, 1 << 31, n), rng.integers(1, 1 << 31, n))),
    ("작은 나눗수", lambda n: (rng.integers(0, 1 << 31, n), rng.integers(1, 1 << 12, n))),
    ("음수 나뉘는 수", lambda n: (rng.integers(-(1 << 31), 0, n), rng.integers(1, 1 << 20, n))),
    ("음수 나누는 수", lambda n: (rng.integers(0, 1 << 31, n), rng.integers(-(1 << 20), 0, n))),
    ("둘 다 음수", lambda n: (rng.integers(-(1 << 40), 0, n), rng.integers(-(1 << 20), 0, n))),
    ("큰 나뉘는 수", lambda n: (rng.integers(1 << 31, 1 << 62, n), rng.integers(1, 1 << 31, n))),
    ("2³¹ 둘레", lambda n: (rng.integers((1 << 31) - 64, (1 << 31) + 64, n), rng.integers((1 << 31) - 64, (1 << 31) + 64, n))),
    ("64 비트 전부", lambda n: (rng.integers(-(1 << 63), (1 << 63) - 1, n, dtype=np.int64),
                             rng.integers(-(1 << 63), (1 << 63) - 1, n, dtype=np.int64))),
]
for _, f in 무리:
    xa, xb = f(4096)
    for a, b in zip(xa.tolist(), xb.tolist()):
        넣기(쌍, int(a), int(b))
n = len(쌍)
앞 = np.array([a for a, _ in 쌍], np.int64)
뒤 = np.array([b for _, b in 쌍], np.int64)

d = B.장치(sys.argv[3] if len(sys.argv) > 3 else "NVIDIA")
print("장치", d.이름)
d.모듈(sys.argv[2])
p앞, p뒤, p몫, p나 = d.할당(n * 8), d.할당(n * 8), d.할당(n * 8), d.할당(n * 8)
d.올리기(p앞, 앞)
d.올리기(p뒤, 뒤)
d.띄우기(진입("나눗셈맞음"), ((n + 255) // 256,), (256, 1, 1), [(1, p앞), (1, p뒤), (1, p몫), (1, p나), (0, n)])
d.맞추기()
몫 = d.내리기(p몫, np.zeros(n, np.int64))
나 = d.내리기(p나, np.zeros(n, np.int64))
다름 = 0
for i, (a, b) in enumerate(쌍):
    q, r = 참(a, b)
    if int(몫[i]) != q or int(나[i]) != r:
        if 다름 < 5:
            print("  다름:", a, b, "→", int(몫[i]), int(나[i]), "참", q, r)
        다름 += 1
print(f"나눗셈맞음: {n} 쌍(경계 {len(경계)}² 남짓 · 무리 {len(무리)} × 4096) — 다른 쌍 {다름}")
d.놓기()

m = 1 << 16
다름2 = 0
for 나눌 in [1, 2, 3, 7, 28, 1024, 1025, 65535, 65536, 65537, (1 << 31) - 1, 1 << 31, 1 << 40, -1, -3, -(1 << 31), -(1 << 40)]:
    p몫, p나 = d.할당(m * 8), d.할당(m * 8)
    d.띄우기(진입("매개나눗셈"), (m // 256,), (256, 1, 1), [(1, p몫), (1, p나), (0, 나눌), (0, m)])
    d.맞추기()
    몫 = d.내리기(p몫, np.zeros(m, np.int64))
    나 = d.내리기(p나, np.zeros(m, np.int64))
    for r in range(m):
        q, rr = 참(r, 나눌)
        if int(몫[r]) != q or int(나[r]) != rr:
            if 다름2 < 5:
                print("  다름(매개):", r, 나눌, "→", int(몫[r]), int(나[r]), "참", q, rr)
            다름2 += 1
    d.놓기()
print(f"매개나눗셈: 나누는 수 17 개 × 나뉘는 수 {m} — 다른 칸 {다름2}")
d.닫기()
