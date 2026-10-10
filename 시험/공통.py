"""시험 · 재기의 공통 — 경로, 모델 파일, 로짓을 얻는 길들, 캐시 바이트.

모델 파일은 저장소에 넣지 않는다 — 모델/ (또는 환경 변수 GEULPU_MODELS 가 가리키는 폴더)에:
  gpt2/            GPT-2 small (safetensors · 토크나이저 — vocab.json · merges.txt)
  gpt2-xl/         GPT-2 XL
  gpt2-q8_0.gguf · gpt2-q4_0.gguf · gpt2-xl-q8_0.gguf · gpt2-xl-q4_0.gguf
  gpt2-long/       합성 긴 모델(위치 102400 — 속도 · 비트 시험용): gpt2-long100k-q8_0.gguf · gpt2-long100k-f32.gguf
"""
import gc
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, ".."))
for _d in ("엔진", "계약", "커널"):
    sys.path.insert(0, os.path.join(ROOT, _d))
import 글gpt2 as G          # noqa: E402
import gguf읽기 as GR       # noqa: E402
import 정수계약 as C        # noqa: E402

모델 = os.environ.get("GEULPU_MODELS", os.path.join(ROOT, "모델"))
결과폴더 = os.path.join(ROOT, "빌드", "결과")
N = 64                       # 생성 걸음 수(시험)
V = 50257
문장들 = ["The meaning of life is",
        "In a shocking finding, scientists discovered a herd of unicorns living in a remote, previously unexplored valley "
        "in the Andes Mountains. Even more surprising to the researchers was the fact that the unicorns spoke perfect English.",
        "Alan Turing was a"]
평가글 = os.path.join(HERE, "평가글.txt")
긴GGUF = os.path.join(모델, "gpt2-long", "gpt2-long100k-q8_0.gguf")
긴F32 = os.path.join(모델, "gpt2-long", "gpt2-long100k-f32.gguf")
u64, i64, f32 = G.c_u64, G.c_i64, np.float32


def 경로(크기, fmt):
    """실제 GPT-2 의 GGUF — 크기 small · XL, 형식 q8_0 · q4_0."""
    return os.path.join(모델, f"gpt2-{fmt}.gguf" if 크기 == "small" else f"gpt2-xl-{fmt}.gguf")


def 모델폴더(크기):
    return os.path.join(모델, "gpt2" if 크기 == "small" else "gpt2-xl")


def 있나(*경로들):
    return all(os.path.exists(p) for p in 경로들)


def 다른칸(a, b):
    """비트가 다른 칸의 수(4 바이트 칸 — 짧은실수는 비트 그대로)."""
    return int(np.count_nonzero(np.asarray(a).view(np.uint32) != np.asarray(b).view(np.uint32)))


def 비우기():
    gc.collect()
    if "torch" in sys.modules:
        sys.modules["torch"].cuda.empty_cache()


def 글엔진(크기, fmt, **kw):
    """정수 KV 계약의 엔진(자리 둘) — 실제 GPT-2."""
    return G.글GPT2(GR.gpt2정수(경로(크기, fmt)), KV형식="정수", 자리수=2, **kw)


def 토크나이저(크기="small"):
    return G.토크나이저(모델폴더(크기))


def 글로짓(m, seqs, 방식, p=None):
    """토큰열들(같은 길이)의 모든 행의 로짓 [문장][행][어휘] — 방식: 한번에 · 하나씩(캐시를 이어 가며) · 프롬프트+하나씩(앞 p 개를 한 번에) ·
    두조각(반씩)."""
    B, n = len(seqs), len(seqs[0])
    out = np.empty((B, n, V), np.float32)
    if 방식 == "하나씩":
        for t in range(n):
            m.토큰넣기([s[t] for s in seqs])
            m.계산(B, 1, t)
            out[:, t] = m.로짓(B)
    elif 방식 == "한번에":
        m.토큰넣기([x for s in seqs for x in s])
        m.계산(B, n, 0)
        out[:] = m.로짓(B * n).reshape(B, n, V)
    elif 방식 in ("프롬프트+하나씩", "두조각"):
        assert B == 1
        k = p if 방식 == "프롬프트+하나씩" else n // 2
        m.토큰넣기(seqs[0][:k])
        m.계산(1, k, 0)
        out[0, :k] = m.로짓(k)
        if 방식 == "두조각":
            m.토큰넣기(seqs[0][k:])
            m.계산(1, n - k, k)
            out[0, k:] = m.로짓(n - k)
        else:
            for t in range(k, n):
                m.토큰넣기([seqs[0][t]])
                m.계산(1, 1, t)
                out[0, t] = m.로짓(1)
    return out


def 로짓들(m, seqs, 방식="한번에", 조각=64):
    """첫 열의 모든 행 로짓 — 한번에(묶음 전체) · 조각(조각 개씩 캐시를 이어 가며) · 하나씩."""
    B, L = len(seqs), len(seqs[0])
    if 방식 == "한번에":
        m.토큰넣기([t for s in seqs for t in s])
        m.계산(B, L, 0, "전부")
        return m.로짓(B * L)[:L].copy()
    s, out = seqs[0], []
    k = 1 if 방식 == "하나씩" else 조각
    for a in range(0, L, k):
        c = s[a:a + k]
        m.토큰넣기(c)
        m.계산(1, len(c), a, "전부")
        out.append(m.로짓(len(c)).copy())
    return np.concatenate(out, 0)


def 캐시(m, l=0):
    """층 l 의 정수 KV 캐시 바이트 전부(키 · 값 · 키지수 · 값지수)."""
    D, NH, L = m.D, m.NH, m.최대길이
    return [m.dr.내리기(p, np.empty(nb, dt)).copy() for p, nb, dt in
            ((m.kc[l], NH * 2 * L * 64, np.int8), (m.vc[l], NH * L * 128, np.int8), (m.ke[l], NH * L * 2, np.uint8), (m.ve[l], NH * L * 2, np.uint8))]


def 캐시앞(m, l, n):
    """층 l 의 캐시 중 위치 0 … n−1 의 바이트(키 · 값 · 지수) — 머리마다 이어 붙인 것(긴 엔진에서 캐시 전부를 내리지 않게)."""
    NH, L = m.NH, m.최대길이
    dr = m.dr
    키, 값, 키지, 값지 = [], [], [], []
    for h in range(NH):
        for j in range(2):                                  # 키 [머리][자리 2][L][64]
            키.append(dr.내리기(m.kc[l] + ((h * 2 + j) * L) * 64, np.empty(n * 64, np.int8)).copy())
        값.append(dr.내리기(m.vc[l] + h * (L // 32) * 4096, np.empty(n // 32 * 4096, np.int8)).copy())     # 값 [머리][L/32][2][64][32]
        키지.append(dr.내리기(m.ke[l] + h * L * 2, np.empty(n * 2, np.uint8)).copy())
        값지.append(dr.내리기(m.ve[l] + h * L * 2, np.empty(n * 2, np.uint8)).copy())
    return [np.concatenate(x) for x in (키, 값, 키지, 값지)]


def 캐시비우기(m):
    """KV 캐시(층 모두)를 0 으로 — 같은 엔진으로 다른 길을 견줄 때."""
    NL = len(m.kc)
    for 바탕, 크기 in ((m.kc바탕, NL * (m.kc[1] - m.kc[0]) if NL > 1 else 0), (m.vc바탕, NL * (m.vc[1] - m.vc[0]) if NL > 1 else 0),
                     (m.ke바탕, NL * (m.ke[1] - m.ke[0]) if NL > 1 else 0), (m.ve바탕, NL * (m.ve[1] - m.ve[0]) if NL > 1 else 0)):
        m.dr.확인(m.dr.cu.cuMemsetD8_v2(u64(바탕), 0, G.ctypes.c_size_t(크기)))
    m.dr.맞추기()
