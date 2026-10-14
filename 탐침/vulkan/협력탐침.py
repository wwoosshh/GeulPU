"""34단계 탐침 — 협력 행렬로 공유 메모리의 판끼리 정수 행렬곱: CPU 와 같은가(무작위 · 극단값), 얼마나 빠른가.
   python -I -X utf8 협력탐침.py <탐침/vulkan 폴더> <spvs> [장치 이름]"""
import sys
import time

sys.path.insert(0, sys.argv[1])
import numpy as np  # noqa: E402
import vk뒷단 as B  # noqa: E402


def 진입(이름):
    return "_G" + 이름.encode("utf-8").hex()


d = B.장치(sys.argv[3] if len(sys.argv) > 3 else "NVIDIA")
print("장치", d.이름, "· 협력 행렬", d.협력)
d.모듈(sys.argv[2])
rng = np.random.default_rng(7)
다름 = 0
for 경우 in range(64):
    if 경우 % 4 == 0:      # 극단: −128 · 127 만
        A1, A0, Bm = (rng.choice(np.array([-128, 127], np.int8), (16, 32)), rng.choice(np.array([-128, 127], np.int8), (16, 32)),
                      rng.choice(np.array([-128, 127], np.int8), (32, 16)))
    else:
        A1, A0, Bm = (rng.integers(-128, 128, (16, 32)).astype(np.int8), rng.integers(-128, 128, (16, 32)).astype(np.int8),
                      rng.integers(-128, 128, (32, 16)).astype(np.int8))
    앞 = np.concatenate([A1.reshape(-1), A0.reshape(-1)]).view(np.int32)
    뒤 = np.ascontiguousarray(Bm.T).reshape(-1).view(np.int32)          # 열 먼저: 열마다 깊이 32 바이트
    p앞, p뒤, p둘, p하나 = d.할당(1024), d.할당(512), d.할당(1024), d.할당(1024)
    d.올리기(p앞, 앞)
    d.올리기(p뒤, 뒤)
    d.띄우기(진입("협력맞음"), (1,), (32, 1, 1), [(1, p앞), (1, p뒤), (1, p둘), (1, p하나)])
    d.맞추기()
    둘 = d.내리기(p둘, np.zeros(256, np.int32)).reshape(16, 16).astype(np.int64)
    하나 = d.내리기(p하나, np.zeros(256, np.int32)).reshape(16, 16).astype(np.int64)
    b64 = Bm.astype(np.int64)
    참하나 = A0.astype(np.int64) @ b64
    참둘 = (A1.astype(np.int64) @ b64) * 256 + 참하나
    다름 += int((둘 != 참둘).sum() + (하나 != 참하나).sum())
    d.놓기()
print("맞는지: 64 경우(무작위 48 · 극단 16) × 칸 512 — 다른 칸", 다름)
if 진입("협력짝맞음") in d.커널들:
    다름2 = 0
    for 경우 in range(32):
        A, A2 = rng.integers(-128, 128, (16, 32)).astype(np.int8), rng.integers(-128, 128, (16, 32)).astype(np.int8)
        Bm, B2 = rng.integers(-128, 128, (32, 16)).astype(np.int8), rng.integers(-128, 128, (32, 16)).astype(np.int8)
        if 경우 % 4 == 0:
            A, A2, Bm, B2 = [np.where(x >= 0, np.int8(127), np.int8(-128)) for x in (A, A2, Bm, B2)]
        p앞, p뒤, p답 = d.할당(1024), d.할당(1024), d.할당(1024)
        d.올리기(p앞, np.concatenate([A.reshape(-1), A2.reshape(-1)]).view(np.int32))
        d.올리기(p뒤, np.concatenate([np.ascontiguousarray(Bm.T).reshape(-1), np.ascontiguousarray(B2.T).reshape(-1)]).view(np.int32))
        d.띄우기(진입("협력짝맞음"), (1,), (32, 1, 1), [(1, p앞), (1, p뒤), (1, p답)])
        d.맞추기()
        답 = d.내리기(p답, np.zeros(256, np.int32)).reshape(16, 16).astype(np.int64)
        참 = A.astype(np.int64) @ Bm.astype(np.int64) + A2.astype(np.int64) @ B2.astype(np.int64)
        다름2 += int((답 != 참).sum())
        d.놓기()
    print("짝: 32 경우 × 칸 256 — 다른 칸", 다름2)

# 빠르기: 블록 240 × 워프 4, 워프마다 정수행렬판곱둘(곱셈 · 덧셈 2 × 16 × 16 × 32 = 16384) × 돌림
p합 = d.할당(240 * 128 * 4)
for 돌림 in (1000, 20000):
    d.띄우기(진입("협력빠르기"), (240,), (128, 1, 1), [(1, p합), (0, 돌림)])
    d.맞추기()
    ts = []
    for _ in range(5):
        t0 = time.perf_counter()
        d.띄우기(진입("협력빠르기"), (240,), (128, 1, 1), [(1, p합), (0, 돌림)])
        d.맞추기()
        ts.append(time.perf_counter() - t0)
    t = sorted(ts)[2]
    mac = 240 * 4 * 돌림 * 16384
    print(f"빠르기: 돌림 {돌림} — {t * 1e3:.2f} ms · {mac / t / 1e12:.1f} T 곱더하기/초 (int8 텐서 최고 약 158)")
d.닫기()

# 성분 대응 — 레인 ℓ 의 성분 j 가 D 의 어느 칸(행 · 열)인가. 정수텐서곱(m16n8k32)의 조각 칸과 견준다
if 진입("협력성분대응") in d.커널들:
    d2 = B.장치(sys.argv[3] if len(sys.argv) > 3 else "NVIDIA")
    d2.모듈(sys.argv[2])
    p = d2.할당(32 * 8 * 4)
    d2.띄우기(진입("협력성분대응"), (1,), (32, 1, 1), [(1, p)])
    d2.맞추기()
    v = d2.내리기(p, np.zeros(256, np.int32)).reshape(32, 8)
    칸 = [[divmod(int(x) + 128, 16) for x in v[l]] for l in range(32)]
    조각 = [[(l // 4 + 8 * ((j >> 1) & 1), 8 * (j >> 2) + 2 * (l % 4) + (j & 1)) for j in range(8)] for l in range(32)]
    print("성분 대응 — 레인 0 · 1 · 4 · 31:", 칸[0], 칸[1], 칸[4], 칸[31])
    print("정수텐서곱 조각 칸과 같은가(성분 j: 행 g + 8·(j>>1 & 1), 열 8·(j>>2) + 2t + (j & 1)):", 칸 == 조각)
    d2.닫기()
