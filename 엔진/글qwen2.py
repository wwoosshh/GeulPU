#!/usr/bin/env python3
"""14단계 — Qwen2(Llama 계열 블록 — RMSNorm · RoPE · SwiGLU · GQA)를 글 커널로 돌리는 호스트. PyTorch 를 쓰지 않는다.

GGUF(Q8_0)를 그대로 읽어 정수 계약의 배치로 깔고(값은 그대로 — 자리만 옮긴다), qwen2Q8.gl 의 커널(커널생성.qwen2_source)을 부르는 차례를
정한다. 계약은 문서/14단계.md · 문서/계약.md — 어느 길(한 번에 · 하나씩 · 나눠 넣기 · 대화 · 생성 그래프)로 계산해도 같은 비트이고,
계약/정수계약.qwen2_앞으로 (CPU 참조)와 같은 비트다.

판(행 수에 따라 — 값은 같다):
  프롬프트(행 다섯 이상): RMS정규화정수줄 → QKV 타일(_QKV정수 — 치우침 · RoPE · q 자리 · KV 캐시) → 정수 KV 어텐션(13단계 판) → o 타일(_잔차)
                         → RMS정규화정수줄 → gate·up 타일(_SwiGLU정수 — down 의 자리) → down 타일(_잔차).
  줄 길(행 넷까지): RMS정규화줄 → 정수줄선형(QKV) → RoPEKV정수로 → 정수조각어텐션 + 정수조각접기 → 정수줄선형_잔차(o) → RMS정규화줄 →
                   정수줄선형(gate·up) → SwiGLU줄 → 정수줄선형_잔차(down).
  생성 그래프(토큰 하나씩): 줄 길과 같은 커널, 위치 · 토큰을 걸음칸(GPU)에서 읽는 칸 판 — 그래프 하나를 고치지 않고 걸음마다 다시 띄운다
                         (가장큰번호칸이 다음 토큰을 생성칸에 쓰고 걸음칸을 올린다). 호스트는 걸음마다 기다리지 않는다.
계획 · 그래프 · 판 고르기의 장치는 글GPT2 의 것을 물려받는다(_판 · _분할열 · 계산 · _그래프만들기 · _묶음판고르기 …).
"""
import ctypes
import gc
import os
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, ".."))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, "커널"))
sys.path.insert(0, os.path.join(ROOT, "계약"))
from 커널생성 import 어텐션질의수, 갈래워프, 정수판표, 정수판모양, 줄판Q, 메가블록qwen, 층크기정수      # noqa: E402 — 커널과 같은 표
import 커널모듈                     # noqa: E402
import gguf읽기 as GR               # noqa: E402
import 정수계약                     # noqa: E402 — RoPE 표(rope표)는 CPU 참조와 같은 함수로
from 글gpt2 import 글GPT2, 드라이버, _띄움, 묶음판행     # noqa: E402

c_u64, c_i64 = ctypes.c_uint64, ctypes.c_int64


class Q8:
    """정수 배치(gguf읽기.깔기정수)의 Q8_0 가중치 하나 — 값 [블록][열][32 바이트], 척도 [블록][척도폭] (반실수). 바이트() = [값][척도]."""

    def __init__(self, q):
        assert q.형식 == "Q8_0" and q.배치 == "정수"
        self.K, self.N, self.Np, self.q = q.K, q.N, q.척도폭, q
        self.값바이트 = q.값.nbytes
        self.nbytes = q.nbytes

    def 바이트(self):
        return self.q.바이트()


def _블록들(g, name):
    """GGUF 텐서(Q8_0)의 날 블록 [N][KB][34] 과 K."""
    t, dims, raw = g.원(name)
    assert t == GR.Q8_0, f"{name}: Q8_0 만 (형식 {t})"
    K, N = dims
    return raw.reshape(N, K // 32, 34), K


def _깔기(블록, K):
    return Q8(GR.깔기정수(GR.Q8_0, (K, 블록.shape[0]), np.ascontiguousarray(블록).reshape(-1)))


def qwen2가중치(path):
    """GGUF(qwen2, Q8_0)를 엔진의 배치로 — (가중치 사전, 설정). 선형은 정수 배치(값은 그대로):
      qkv — q · k · v 의 열을 이어(열 [q 너비 | k | v]), qkv치우침 — 같은 차례로 이은 치우침,
      gu — gate · up 을 출력 블록(32 열)마다 [gate 32 | up 32] 로 번갈아, o · down — 그대로, embed — token_embd(임베딩과 로짓이 함께 —
      output.weight 가 바이트까지 같을 때; 아니면 head 를 따로). 정규화 가중치는 짧은실수."""
    g = GR.GGUF(path)
    m = g.meta
    assert m["general.architecture"] == "qwen2", m["general.architecture"]
    설정 = {"층": m["qwen2.block_count"], "머리": m["qwen2.attention.head_count"], "KV머리": m["qwen2.attention.head_count_kv"],
           "너비": m["qwen2.embedding_length"], "확장폭": m["qwen2.feed_forward_length"], "위치": m["qwen2.context_length"],
           "theta": float(m["qwen2.rope.freq_base"]), "eps": float(m["qwen2.attention.layer_norm_rms_epsilon"])}
    W = {"embed": _깔기(*_블록들(g, "token_embd.weight")), "norm": g.풀기("output_norm.weight")}
    if "output.weight" in g.tensors:
        a, b = g.원("token_embd.weight")[2], g.원("output.weight")[2]
        W["head같음"] = bool(a.shape == b.shape and np.array_equal(a, b))
        if not W["head같음"]:
            W["head"] = _깔기(*_블록들(g, "output.weight"))
    else:
        W["head같음"] = True
    for l in range(설정["층"]):
        p = f"blk.{l}."
        bq, K = _블록들(g, p + "attn_q.weight")
        bk, _ = _블록들(g, p + "attn_k.weight")
        bv, _ = _블록들(g, p + "attn_v.weight")
        W[f"{l}.qkv"] = _깔기(np.concatenate([bq, bk, bv], 0), K)
        W[f"{l}.qkv치우침"] = np.concatenate([g.풀기(p + "attn_q.bias"), g.풀기(p + "attn_k.bias"), g.풀기(p + "attn_v.bias")]).astype(np.float32)
        W[f"{l}.o"] = _깔기(*_블록들(g, p + "attn_output.weight"))
        bg, K = _블록들(g, p + "ffn_gate.weight")
        bu, _ = _블록들(g, p + "ffn_up.weight")
        F = bg.shape[0]
        W[f"{l}.gu"] = _깔기(np.stack([bg.reshape(F // 32, 32, -1, 34), bu.reshape(F // 32, 32, -1, 34)], 1).reshape(2 * F, -1, 34), K)
        W[f"{l}.down"] = _깔기(*_블록들(g, p + "ffn_down.weight"))
        W[f"{l}.n1"] = g.풀기(p + "attn_norm.weight")
        W[f"{l}.n2"] = g.풀기(p + "ffn_norm.weight")
    return W, 설정


class 글Qwen2(글GPT2):
    """Qwen2(GGUF Q8_0) 엔진. 문장 B 개 × m 행의 계산(계산) · 탐욕 생성(생성 · 이어넣기 · 이어생성 — 생성 메가커널, 메가쓰기 가 거짓이면
    14단계의 생성 그래프 — 같은 비트)."""

    def __init__(self, gguf, 최대행=2048, 최대문장=1, 최대길이=32768, 로짓행=512, 묶음판행=묶음판행, 가중치=None, ptx경로=None):
        W, 설정 = 가중치 if 가중치 is not None else qwen2가중치(gguf)
        self.설정 = 설정
        self.D, self.NH, self.NKV, self.NL, self.F = 설정["너비"], 설정["머리"], 설정["KV머리"], 설정["층"], 설정["확장폭"]
        D, NH, NKV, NL, F = self.D, self.NH, self.NKV, self.NL, self.F
        assert (D, NH, NKV, NL, F) == (896, 14, 2, 24, 4864), f"모듈이 없는 크기: {(D, NH, NKV, NL, F)}"
        self.V = W["embed"].N
        V = self.V
        self.QKV = D + 128 * NKV
        assert 최대길이 % 64 == 0 and 최대길이 <= min(131072, 설정["위치"]), "최대길이는 64 의 배수, 모델의 위치 수까지"
        self.자리수, self.정수, self.정수KV, self.양자 = 2, True, True, True
        self.KV형식, self.크기 = "정수", "qwen2"
        self.최대행, self.최대문장, self.최대길이 = 최대행, 최대문장, 최대길이
        self.dr = dr = 드라이버()
        self.mods = [dr.모듈(open(ptx경로 or 커널모듈.ptx("qwen2Q8.gl"), "rb").read())]     # ptx경로: 재기용(생성기 깃발을 바꾼 모듈)
        mod = self.mods[0]
        이름들 = ("정수로", "RMS정규화정수줄", "RMS정규화줄", "임베딩", "RoPEKV정수로", "SwiGLU줄", "가장큰번호",
                 "정수어텐션", "정수어텐션갈래", "정수조각어텐션", "정수조각접기", "정수어텐션묶음", "정수어텐션갈래묶음", "정수묶음접기",
                 "정수어텐션두층", "임베딩칸", "RoPEKV정수로칸", "정수조각어텐션칸", "정수조각접기칸", "가장큰번호칸",
                 "정수줄선형QKV", "정수줄선형o", "정수줄선형gu", "정수줄선형down", "정수줄선형로짓", "정수줄선형QKV칸", "가장큰번호부분",
                 "가장큰번호부분칸")
        self.k = {n: dr.함수(mod, n) for n in 이름들}
        판표 = 정수판표(2, True)
        self.선형 = {(판, epi): dr.함수(mod, f"{판}{epi}") for 판 in (*판표, "정수줄선형") for epi in ("", "_잔차")}
        self.선형.update({(판, epi): dr.함수(mod, f"{판}{epi}") for 판 in 판표 if 판표[판][3] == 8 for epi in ("_QKV정수", "_SwiGLU정수")})
        # 열먼저 판(블록이 열 먼저 — 행이 많아 활성값이 L2 를 넘을 때; 같은 비트)
        self.선형.update({(판 + "열먼저", epi): dr.함수(mod, f"{판}열먼저{epi}") for 판 in 판표
                        for epi in (("_잔차", "_QKV정수", "_SwiGLU정수") if 판표[판][3] == 8 else ("_잔차",))})
        self.판이름들 = list(판표) + [판 + "열먼저" for 판 in 판표]
        self.로짓선형 = {판: dr.함수(mod, f"로짓{판}") for 판 in (*판표, "정수줄선형")}

        def up(a):
            p = dr.할당(a.nbytes)
            dr.올리기(p, a)
            return p

        def 층올림(이름):
            """층마다의 가중치를 이어 올린다 — 층 l 의 (값, 척도) 주소. 정수 배치는 층마다 [값][척도]."""
            x0 = W[f"0.{이름}"]
            if isinstance(x0, Q8):
                한층 = x0.nbytes
                assert 한층 % 16 == 0 and x0.값바이트 % 16 == 0
                바탕 = up(np.concatenate([W[f"{l}.{이름}"].바이트() for l in range(NL)]))
                return [(바탕 + l * 한층, 바탕 + l * 한층 + x0.값바이트) for l in range(NL)], x0
            한층 = x0.nbytes
            assert 한층 % 16 == 0
            바탕 = up(np.concatenate([np.ascontiguousarray(W[f"{l}.{이름}"], np.float32).reshape(-1) for l in range(NL)]))
            return [바탕 + l * 한층 for l in range(NL)], x0
        self.층 = [{} for _ in range(NL)]
        self.모양 = {}
        for 이름 in ("qkv", "qkv치우침", "o", "gu", "down", "n1", "n2"):
            주소들, x0 = 층올림(이름)
            for l in range(NL):
                self.층[l][이름] = 주소들[l]
            if isinstance(x0, Q8):
                self.모양[이름] = (x0.K, x0.N)
        assert self.모양 == {"qkv": (D, self.QKV), "o": (D, D), "gu": (D, 2 * F), "down": (F, D)}, self.모양
        e = W["embed"]
        p = up(e.바이트())
        self.낱말 = (p, p + e.값바이트)
        if W["head같음"]:
            self.머리 = self.낱말                      # output.weight 가 token_embd 와 바이트까지 같다 — 한 벌을 함께(값은 같다)
        else:
            h = W["head"]
            p = up(h.바이트())
            self.머리 = (p, p + h.값바이트)
        self.norm = up(np.ascontiguousarray(W["norm"], np.float32))
        self.영치우침 = up(np.zeros(max(V, 2 * F), np.float32))
        코, 사 = 정수계약.rope표(최대길이, 설정["theta"])
        self.코사인, self.사인 = up(코), up(사)
        M = 최대행
        정보폭 = (M + 63) // 64 * 64
        # 활성값: 잔차 흐름 h, 줄 길의 짧은실수 칸(행 넷까지), 자리 둘 · 정보(깊이 D — RMS · 어텐션 출력; 깊이 F — SwiGLU 출력), q 의 자리
        self.h = dr.할당(M * D * 4)
        R4 = 4
        self.x = dr.할당(max(R4, 최대문장) * D * 4)
        self.qkv = dr.할당(R4 * self.QKV * 4)
        self.att = dr.할당(R4 * D * 4)
        self.gu = dr.할당(R4 * 2 * F * 4)
        self.f = dr.할당(R4 * F * 4)
        self.자릿값, self.정보 = dr.할당(2 * M * D), dr.할당(D // 32 * 정보폭 * 4)
        self.자릿값2, self.정보2 = dr.할당(2 * M * F), dr.할당(F // 32 * 정보폭 * 4)
        self.자릿값q, self.정보q = dr.할당(2 * M * D), dr.할당(D // 32 * 정보폭 * 4)
        self.로짓행 = max(min(로짓행, M), 최대문장)
        self.logits = dr.할당(self.로짓행 * V * 4)
        self.시험칸 = dr.할당(max(M * max(D, F) * 8, self.로짓행 * V * 4))
        self.시험입력 = dr.할당(M * F * 4)          # 판 고르기의 활성값(0 — 오류 칸이 켜지지 않게)
        # KV 캐시(층마다): 키 [문장 · KV 머리][자리 2][위치][64 바이트], 값 [문장 · KV 머리][위치/32][자리 2][d 64][32 바이트], 지수 [문장 · KV 머리][위치][2]
        kv = 최대문장 * NKV * 2 * 최대길이 * 64
        ek = 최대문장 * NKV * 최대길이 * 2
        self.kc바탕, self.vc바탕, self.ke바탕, self.ve바탕 = dr.할당(NL * kv), dr.할당(NL * kv), dr.할당(NL * ek), dr.할당(NL * ek)
        self.kc = [self.kc바탕 + l * kv for l in range(NL)]
        self.vc = [self.vc바탕 + l * kv for l in range(NL)]
        self.ke = [self.ke바탕 + l * ek for l in range(NL)]
        self.ve = [self.ve바탕 + l * ek for l in range(NL)]
        self.시험KV = [dr.할당(n) for n in (2 * M * D, D // 32 * 정보폭 * 4, NKV * 2 * 최대길이 * 64, NKV * 2 * 최대길이 * 64,
                                           NKV * 최대길이 * 2, NKV * 최대길이 * 2)]
        self.조각칸 = dr.할당(max(최대문장, R4) * NH * (최대길이 // 64) * 68 * 4)
        self.묶음수 = (최대길이 + 1023) // 1024
        self.묶음판행 = min(M, 묶음판행)
        if 최대길이 > 1024:
            assert self.묶음수 <= 128
            self.묶음칸 = dr.할당(max(self.묶음판행 * NH * self.묶음수 * 68 * 4, NH * ((M + 63) // 64 + 최대문장) * 40 * 128 * 4))
        # 줄 길의 묶은 판(14단계): 열 묶음(커널과 같은 표), 로짓의 블록마다 가장 큰 값 · 번호 [문장][블록]
        self.줄판 = 줄판Q(D, F)
        self.부분수 = (V + self.줄판["로짓"][3] - 1) // self.줄판["로짓"][3]
        self.부분값, self.부분번호 = dr.할당(max(최대문장, R4) * self.부분수 * 4), dr.할당(max(최대문장, R4) * self.부분수 * 8)
        self.줄묶음 = True                          # 줄 길 · 생성 그래프에서 묶은 판을 쓴다(거짓이면 따로 도는 판 — 대조용, 같은 비트)
        self.토큰칸 = dr.할당(M * 8)
        self.생성최대 = 1 << 16
        self.생성칸 = dr.할당(self.생성최대 * 8)
        self.걸음칸 = dr.할당(256)                  # [위치, 걸음] (정수) — 생성 그래프의 칸 판이 읽고 가장큰번호칸이 올린다
        sm = ctypes.c_int()
        dr.확인(dr.cu.cuDeviceGetAttribute(ctypes.byref(sm), 16, 0))
        self.SM수 = sm.value
        self.갈래쓰기, self.묶음판쓰기 = True, True
        # 15단계 — 생성 메가커널(협력 실행): 격자 = SM 수 × 점유(실행한도까지). 문장 하나의 캐시(층 걸음 = 문장 하나 몫)만
        cu = dr.cu
        cu.cuLaunchCooperativeKernel.argtypes = [ctypes.c_void_p] + [ctypes.c_uint] * 7 + [ctypes.c_void_p] * 2
        self.k["생성메가qwen"] = dr.함수(mod, "생성메가qwen")
        점유 = ctypes.c_int()
        dr.확인(cu.cuOccupancyMaxActiveBlocksPerMultiprocessor(ctypes.byref(점유), self.k["생성메가qwen"], 256, ctypes.c_size_t(0)))
        self.메가격자 = self.SM수 * min(점유.value, 메가블록qwen)
        for 이름, K, N in (("qkv", D, self.QKV), ("o", D, D), ("gu", D, 2 * F), ("down", F, D)):     # 커널이 셈하는 층 걸음과 같은가
            assert self.층[1][이름][0] - self.층[0][이름][0] == sum(층크기정수("Q8_0", K, N)), 이름
        # 생성 · 이어생성이 메가커널을(거짓이면 14단계의 생성 그래프 — 같은 비트). 메가커널의 두 층 접기는 묶음 16 개(위치 16384)까지
        self.메가쓰기 = 최대문장 == 1 and self.메가격자 > 0 and 최대길이 <= 16384
        self.메가장벽 = dr.할당(256)
        self.주의셈 = dr.할당(64 * 8)
        self.메가부분값, self.메가부분번호 = dr.할당(max(self.메가격자, 1) * 4), dr.할당(max(self.메가격자, 1) * 8)
        self._로짓기록 = (None, 0)
        self.시각칸, self.시각재기 = dr.할당(8 * (1 + 130 * 1100)), 0     # 재기용: 0 이 아니면 블록 (값 − 1) 이 장벽마다 GPU 시각을 남긴다
        self._계획, self._그래프, self._고른판, self._계획쓰임, self._격자식들, self._점유칸 = {}, {}, {}, {}, {}, {}
        self.그래프쓰기 = True
        self._생성그래프 = None
        cu = dr.cu
        cu.cuEventCreate.argtypes = [ctypes.POINTER(ctypes.c_void_p), ctypes.c_uint]
        cu.cuEventRecord.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
        cu.cuEventSynchronize.argtypes = [ctypes.c_void_p]
        cu.cuEventElapsedTime.argtypes = [ctypes.POINTER(ctypes.c_float), ctypes.c_void_p, ctypes.c_void_p]

    def 닫기(self):
        if self._생성그래프 is not None:
            self.dr.확인(self.dr.cu.cuGraphExecDestroy(self._생성그래프[1]))
            self.dr.확인(self.dr.cu.cuGraphDestroy(self._생성그래프[2]))
            self._생성그래프 = None
        super().닫기()

    # ── 판 고르기 ──

    @staticmethod
    def _격자(판, rows, N, K=None, 작음=True):
        """글GPT2._격자 + 열먼저 판(격자의 가로가 열 블록, 세로가 행 블록)."""
        if 판.endswith("열먼저"):
            BM, BN, T = 정수판모양(판)
            return ((N + BN - 1) // BN, (rows + BM - 1) // BM), (T, 1)
        return 글GPT2._격자(판, rows, N, K, 작음)

    def _가중치(self, K, N, 로짓):
        if 로짓:
            return self.머리
        return self.층[0][{(self.D, self.QKV): "qkv", (self.D, self.D): "o", (self.D, 2 * self.F): "gu", (self.F, self.D): "down"}[(K, N)]]

    def _정수판재기(self, rows, K, N, 로짓, epi=""):
        """글GPT2._정수판재기 와 같은 재기(후보를 번갈아, 꼬리 자르기까지) — Qwen2 의 가중치 · 끝손질 인자로. 출력 · 캐시는 모두 시험칸 ·
        시험KV 에(진짜 버퍼를 건드리지 않는다). 활성값은 0 (값과 상관없이 시간만)."""
        cu, 시 = self.dr.cu, self.시험칸
        x = _띄움(self.k["정수로"], ((K // 32 + 31) // 32, rows), (256, 1),
                  [c_u64(self.시험입력), c_u64(self.자릿값2), c_u64(self.정보2), c_i64(rows), c_i64(K)])
        cu.cuLaunchKernel(x.fn, x.grid[0], x.grid[1], 1, x.block[0], x.block[1], 1, 0, None, x.args, None)
        wt = self._가중치(K, N, 로짓)
        치 = self.층[0]["qkv치우침"] if epi == "_QKV정수" else self.영치우침
        extra = {"_잔차": [시], "_SwiGLU정수": [시 + 4 * self.최대행 * self.F],            # 다음자리 [2][행][F] 바이트 뒤에 다음정보
                 "_QKV정수": self.시험KV + [self.코사인, self.사인]}.get(epi, [])

        def 띄움(판, 격자, 행시작=0, 열시작=0):
            fn = self.로짓선형[판] if 로짓 else self.선형[(판, epi)]
            ps = [c_u64(self.자릿값2), c_u64(self.정보2)] + [c_u64(v) for v in wt] + [c_u64(치)] + [c_u64(v) for v in extra] + \
                 ([] if epi == "_QKV정수" else [c_u64(시)]) + [c_i64(rows), c_i64(K), c_i64(N), c_i64((N + 63) // 64 * 64)] + \
                 ([c_i64(rows), c_i64(0), c_i64(self.최대길이)] if epi == "_QKV정수" else []) + [c_i64(행시작), c_i64(열시작)]
            y = _띄움(fn, 격자, (정수판모양(판)[2], 1), ps)
            return lambda y=y: cu.cuLaunchKernel(y.fn, y.grid[0], y.grid[1], 1, y.block[0], y.block[1], 1, 0, None, y.args, None)

        def 재기(runs):
            t0 = time.perf_counter()
            while time.perf_counter() - t0 < 0.02:
                for run in runs.values():
                    run()
                self.dr.맞추기()
            ts = {판: [] for 판 in runs}
            e0, e1 = ctypes.c_void_p(), ctypes.c_void_p()
            cu.cuEventCreate(ctypes.byref(e0), 0)
            cu.cuEventCreate(ctypes.byref(e1), 0)
            for _ in range(3):
                for 판, run in runs.items():
                    cu.cuEventRecord(e0, None)
                    for _ in range(3):
                        run()
                    cu.cuEventRecord(e1, None)
                    cu.cuEventSynchronize(e1)
                    ms = ctypes.c_float()
                    cu.cuEventElapsedTime(ctypes.byref(ms), e0, e1)
                    ts[판].append(ms.value)
            cu.cuEventDestroy_v2(e0)
            cu.cuEventDestroy_v2(e1)
            return {판: sorted(v)[1] for 판, v in ts.items()}

        판들 = [판 for 판 in self.판이름들 if (판 in self.로짓선형) if 로짓] or [판 for 판 in self.판이름들 if (판, epi) in self.선형]
        runs = {판: 띄움(판, self._격자(판, rows, N)[0]) for 판 in 판들}
        ts = 재기(runs)
        best = min(ts, key=ts.get)
        nsm = ctypes.c_int()
        self.dr.확인(cu.cuDeviceGetAttribute(ctypes.byref(nsm), 16, 0))
        후보 = {}
        for 큰 in sorted(ts, key=ts.get)[:2]:
            BM, BN, T = 정수판모양(큰)
            gx, gy = (rows + BM - 1) // BM, (N + BN - 1) // BN
            열먼저 = 큰.endswith("열먼저")
            점유 = ctypes.c_int()
            fn = self.로짓선형[큰] if 로짓 else self.선형[(큰, epi)]
            self.dr.확인(cu.cuOccupancyMaxActiveBlocksPerMultiprocessor(ctypes.byref(점유), fn, T, ctypes.c_size_t(0)))
            자리 = nsm.value * 점유.value
            if 자리 <= 0 or gx * gy <= 자리 or (gx * gy) % 자리 == 0:
                continue
            ny = ((gx * gy) // 자리 * 자리) // gx
            if ny < 1 or ny >= gy:
                continue
            Nb = ny * BN
            for 작 in 판들:
                BMs, BNs, Ts = 정수판모양(작)
                if 2 * BMs * BNs > BM * BN:
                    continue
                if epi in ("_QKV정수", "_SwiGLU정수") and Nb % 64:
                    continue
                a = 띄움(큰, (ny, gx) if 열먼저 else (gx, ny))
                gb = ((rows + BMs - 1) // BMs, (N - Nb + BNs - 1) // BNs)
                b = 띄움(작, gb[::-1] if 작.endswith("열먼저") else gb, 0, Nb)
                후보[("분할", 큰, 작, Nb)] = lambda a=a, b=b: (a(), b())
        if not 후보:
            return best
        후보[best] = runs[best]
        ts2 = 재기(후보)
        고름 = min(ts2, key=ts2.get)
        return 고름[:3] if isinstance(고름, tuple) else 고름

    def 판미리고르기(self):
        """모델을 올릴 때 행 수 묶음(8 … 최대행)마다 네 행렬곱의 타일 판을 미리 재서 고른다(값과 상관없다)."""
        D, F = self.D, self.F
        b = 8
        while True:
            r = self._묶음행(b)
            if r > 4:
                for K, N, epi in ((D, self.QKV, "_QKV정수"), (D, D, "_잔차"), (D, 2 * F, "_SwiGLU정수"), (F, D, "_잔차")):
                    self._판(None, None, None, r, K, N, False, epi)
            if r >= self.최대행:
                break
            b *= 2
        if self._생성그래프 is None:              # 생성 그래프도 미리(첫 답이 그래프 만들기를 치르지 않게)
            self._생성그래프만들기()
        gc.freeze()

    # ── 계획 ──

    def _만들기(self, B, m, 로짓):
        """문장 B 개 × m 행의 한 번 계산. 로짓: "전부"(모든 행), "끝"(문장마다 마지막 행 + 가장큰번호), 정수 k(문장 하나의 마지막 k 행)."""
        M = B * m
        assert M <= self.최대행 and B <= self.최대문장
        assert 로짓 != "전부" or M <= self.로짓행, "모든 행의 로짓은 로짓행 행까지"
        k, D, F, NH = self.k, self.D, self.F, self.NH
        pos, tok, out = c_i64(0), c_u64(self.토큰칸), c_u64(self.생성칸)
        P, I = c_u64, c_i64
        L = []
        L.append(_띄움(k["임베딩"], ((M * D + 255) // 256, 1), (256, 1), [tok, P(self.낱말[0]), P(self.낱말[1]), P(self.h), I(M)]))

        def lin(epi, src, wt, b, dst, K, N, extra=(), rows=M, kv=False, 로짓=False, 자리=None):
            if rows <= 4:                       # dp4a 줄 판 — 판 안에서 행마다 자리 둘로
                fn = self.로짓선형["정수줄선형"] if 로짓 else self.선형[("정수줄선형", epi)]
                ps = [P(src), P(wt[0]), P(wt[1]), P(b)] + [P(x) for x in extra] + [P(dst), I(rows), I(K), I(N)]
                return _띄움(fn, *self._격자("정수줄선형", rows, N, K, False), ps)
            판 = self._판(None, wt, b, rows, K, N, 로짓, epi)
            자리 = 자리 or (self.자릿값, self.정보)
            ps0 = [P(자리[0]), P(자리[1]), P(wt[0]), P(wt[1]), P(b)] + [P(x) for x in extra] + \
                  ([] if epi == "_QKV정수" else [P(dst)]) + [I(rows), I(K), I(N), I((N + 63) // 64 * 64)]
            if kv:
                ps0 += [I(m), pos, I(self.최대길이)]
            if isinstance(판, tuple):                # 꼬리 자르기: 큰 판(열 [0, Nb)) 다음에 작은 판(열 [Nb, N)) — 같은 비트
                _, 큰, 작 = 판[:3]
                Nb = self._분할열(큰, rows, N, 로짓, epi)
                if Nb and epi in ("_QKV정수", "_SwiGLU정수") and Nb % 64:
                    Nb = None
                판 = 판 if Nb else 큰
            if isinstance(판, tuple):
                BM, BN, T = 정수판모양(큰)
                ga = ((rows + BM - 1) // BM, Nb // BN)
                L.append(_띄움(self.로짓선형[큰] if 로짓 else self.선형[(큰, epi)], ga[::-1] if 큰.endswith("열먼저") else ga, (T, 1),
                               ps0 + [I(0), I(0)]))
                BMs, BNs, Ts = 정수판모양(작)
                gb = ((rows + BMs - 1) // BMs, (N - Nb + BNs - 1) // BNs)
                return _띄움(self.로짓선형[작] if 로짓 else self.선형[(작, epi)], gb[::-1] if 작.endswith("열먼저") else gb, (Ts, 1),
                             ps0 + [I(0), I(Nb)])
            fn = self.로짓선형[판] if 로짓 else self.선형[(판, epi)]
            return _띄움(fn, *self._격자(판, rows, N), ps0 + [I(0), I(0)])

        KV인자 = lambda l: [P(self.kc[l]), P(self.vc[l]), P(self.ke[l]), P(self.ve[l])]
        조각수 = self.최대길이 // 64
        if M > 4:
            assert m >= 2
            질조각수 = (m + 63) // 64
            if self.최대길이 > 1024:
                if self._묶음쓰나(B, m):
                    def 어텐션(l):
                        x = _띄움(k["정수어텐션묶음"], (질조각수 * NH, B), (128, 1),
                                 [P(self.자릿값q), P(self.정보q)] + KV인자(l) + [P(self.묶음칸), I(M), I(m), pos, I(self.최대길이)])
                        x.고르기 = lambda 위치, mm=m, b=B: self._묶음판고르기(위치, mm, b)
                        return [x, _띄움(k["정수묶음접기"], (NH, M), (64, 1),
                                        [P(self.묶음칸), P(self.정보), P(self.자릿값), I(M), I(m), pos, I(self.최대길이)])]
                else:
                    어텐션 = lambda l: [_띄움(k["정수어텐션두층"], (NH, B * 질조각수), (128, 1),
                                          [P(self.자릿값q), P(self.정보q)] + KV인자(l) + [P(self.묶음칸), P(self.정보), P(self.자릿값), I(M), I(m), pos,
                                                                                     I(self.최대길이)])]
            elif self._갈래쓰나(B, m):
                어텐션 = lambda l: [_띄움(k["정수어텐션갈래"], (NH, B * ((m + 15) // 16)), (32 * 갈래워프, 1),
                                      [P(self.자릿값q), P(self.정보q)] + KV인자(l) + [P(self.정보), P(self.자릿값), I(M), I(m), pos, I(self.최대길이)])]
            else:
                어텐션 = lambda l: [_띄움(k["정수어텐션"], (NH, B * ((m + 어텐션질의수 - 1) // 어텐션질의수)), (2 * 어텐션질의수, 1),
                                      [P(self.자릿값q), P(self.정보q)] + KV인자(l) + [P(self.정보), P(self.자릿값), I(M), I(m), pos, I(self.최대길이)])]
            for l, w in enumerate(self.층):
                L.append(_띄움(k["RMS정규화정수줄"], (M, 1), (256, 1), [P(self.h), P(w["n1"]), P(self.자릿값), P(self.정보), I(M)]))
                L.append(lin("_QKV정수", None, w["qkv"], w["qkv치우침"], None, D, self.QKV,
                             [self.자릿값q, self.정보q, self.kc[l], self.vc[l], self.ke[l], self.ve[l], self.코사인, self.사인], kv=True))
                L += 어텐션(l)
                L.append(lin("_잔차", None, w["o"], self.영치우침, self.h, D, D, (self.h,)))
                L.append(_띄움(k["RMS정규화정수줄"], (M, 1), (256, 1), [P(self.h), P(w["n2"]), P(self.자릿값), P(self.정보), I(M)]))
                L.append(lin("_SwiGLU정수", None, w["gu"], self.영치우침, self.자릿값2, D, 2 * F, (self.정보2,)))
                L.append(lin("_잔차", None, w["down"], self.영치우침, self.h, F, D, (self.h,), 자리=(self.자릿값2, self.정보2)))
        elif self.줄묶음:
            for l, w in enumerate(self.층):
                L += self._줄층(l, w, M, m, pos)
        else:
            for l, w in enumerate(self.층):
                L.append(_띄움(k["RMS정규화줄"], (M, 1), (256, 1), [P(self.h), P(w["n1"]), P(self.x)]))
                L.append(lin("", self.x, w["qkv"], w["qkv치우침"], self.qkv, D, self.QKV))
                L.append(_띄움(k["RoPEKV정수로"], ((self.QKV // 32 + 31) // 32, M), (256, 1),
                               [P(self.qkv), P(self.자릿값q), P(self.정보q)] + KV인자(l) + [P(self.코사인), P(self.사인), I(M), I(m), pos,
                                                                                         I(self.최대길이)]))
                L.append(_띄움(k["정수조각어텐션"], ((조각수 + 7) // 8, M * NH), (256, 1),
                               [P(self.자릿값q), P(self.정보q)] + KV인자(l) + [P(self.조각칸), I(M), I(m), pos, I(self.최대길이)]))
                L.append(_띄움(k["정수조각접기"], (M * NH, 1), (256, 1), [P(self.조각칸), P(self.att), I(M), I(m), pos, I(self.최대길이)]))
                L.append(lin("_잔차", self.att, w["o"], self.영치우침, self.h, D, D, (self.h,)))
                L.append(_띄움(k["RMS정규화줄"], (M, 1), (256, 1), [P(self.h), P(w["n2"]), P(self.x)]))
                L.append(lin("", self.x, w["gu"], self.영치우침, self.gu, D, 2 * F))
                L.append(_띄움(k["SwiGLU줄"], ((M * F + 255) // 256, 1), (256, 1), [P(self.gu), P(self.f), I(M)]))
                L.append(lin("_잔차", self.f, w["down"], self.영치우침, self.h, F, D, (self.h,)))
        V = self.V
        if 로짓 == "전부":
            if M > 4:
                L.append(_띄움(k["RMS정규화정수줄"], (M, 1), (256, 1), [P(self.h), P(self.norm), P(self.자릿값), P(self.정보), I(M)]))
                L.append(lin("", None, self.머리, self.영치우침, self.logits, D, V, 로짓=True))
            else:
                L.append(_띄움(k["RMS정규화줄"], (M, 1), (256, 1), [P(self.h), P(self.norm), P(self.x)]))
                L.append(lin("", self.x, self.머리, self.영치우침, self.logits, D, V, 로짓=True))
        elif isinstance(로짓, int):                # 문장 하나의 마지막 로짓 행만
            assert B == 1 and 0 < 로짓 <= min(m, self.로짓행, 4 if M <= 4 else self.로짓행)
            if 로짓 <= 4:
                L.append(_띄움(k["RMS정규화줄"], (로짓, 1), (256, 1), [P(self.h + (m - 로짓) * D * 4), P(self.norm), P(self.x)]))
                L.append(lin("", self.x, self.머리, self.영치우침, self.logits, D, V, rows=로짓, 로짓=True))
            else:
                L.append(_띄움(k["RMS정규화정수줄"], (로짓, 1), (256, 1), [P(self.h + (m - 로짓) * D * 4), P(self.norm), P(self.자릿값), P(self.정보),
                                                                          I(로짓)]))
                L.append(lin("", None, self.머리, self.영치우침, self.logits, D, V, rows=로짓, 로짓=True))
        elif self.줄묶음:                            # 문장마다 마지막 행만 → 로짓의 행 b (RMS 를 묶은 판), 블록마다의 가장 큰 값에서 번호
            for b in range(B):
                L.append(self._로짓줄(self.h + (b * m + m - 1) * D * 4, self.logits + b * V * 4, b))
            L.append(_띄움(k["가장큰번호부분"], (B, 1), (256, 1), [P(self.부분값), P(self.부분번호), out, I(1), I(self.부분수)]))
        else:                                       # 문장마다 마지막 행만 → 로짓의 행 b, 가장큰번호
            for b in range(B):
                L.append(_띄움(k["RMS정규화줄"], (1, 1), (256, 1), [P(self.h + (b * m + m - 1) * D * 4), P(self.norm), P(self.x + b * D * 4)]))
            if B == 1:
                L.append(lin("", self.x, self.머리, self.영치우침, self.logits, D, V, rows=1, 로짓=True))
            else:
                for b in range(B):
                    L.append(lin("", self.x + b * D * 4, self.머리, self.영치우침, self.logits + b * V * 4, D, V, rows=1, 로짓=True))
            L.append(_띄움(k["가장큰번호"], (B, 1), (256, 1), [P(self.logits), out, I(1), I(V)]))
        return pos, tok, out, L

    def _생성그래프만들기(self):
        """생성 그래프 — 토큰 하나(위치 걸음칸[0], 토큰 생성칸[걸음칸[1]])의 계산 전체: 줄 길과 같은 커널(칸 판), 끝에 가장큰번호칸이 생성칸[걸음 + 1] 에
        쓰고 걸음칸을 올린다. 매개변수가 바뀌지 않으니 그래프를 한 번 만들어 걸음마다 다시 띄운다."""
        k, D, F, NH, V = self.k, self.D, self.F, self.NH, self.V
        P, I = c_u64, c_i64
        걸 = P(self.걸음칸)
        조각수 = self.최대길이 // 64

        def lin(epi, src, wt, b, dst, K, N, extra=(), 로짓=False):
            fn = self.로짓선형["정수줄선형"] if 로짓 else self.선형[("정수줄선형", epi)]
            ps = [P(src), P(wt[0]), P(wt[1]), P(b)] + [P(x) for x in extra] + [P(dst), I(1), I(K), I(N)]
            return _띄움(fn, *self._격자("정수줄선형", 1, N, K, False), ps)
        L = [_띄움(k["임베딩칸"], ((D + 255) // 256, 1), (256, 1), [P(self.생성칸), P(self.낱말[0]), P(self.낱말[1]), P(self.h), I(1), 걸])]
        if self.줄묶음:
            for l, w in enumerate(self.층):
                L += self._줄층(l, w, 1, 1, 걸, 칸=True)
            L.append(self._로짓줄(self.h, self.logits, 0))
            L.append(_띄움(k["가장큰번호부분칸"], (1, 1), (256, 1), [P(self.부분값), P(self.부분번호), P(self.생성칸), I(1), I(self.부분수), 걸]))
            ex, g, _ = self._그래프만들기(L)
            self._생성그래프 = (L, ex, g)
            return
        for l, w in enumerate(self.층):
            KV = [P(self.kc[l]), P(self.vc[l]), P(self.ke[l]), P(self.ve[l])]
            L.append(_띄움(k["RMS정규화줄"], (1, 1), (256, 1), [P(self.h), P(w["n1"]), P(self.x)]))
            L.append(lin("", self.x, w["qkv"], w["qkv치우침"], self.qkv, D, self.QKV))
            L.append(_띄움(k["RoPEKV정수로칸"], ((self.QKV // 32 + 31) // 32, 1), (256, 1),
                           [P(self.qkv), P(self.자릿값q), P(self.정보q)] + KV + [P(self.코사인), P(self.사인), I(1), I(1), 걸, I(self.최대길이)]))
            L.append(_띄움(k["정수조각어텐션칸"], ((조각수 + 7) // 8, NH), (256, 1),
                           [P(self.자릿값q), P(self.정보q)] + KV + [P(self.조각칸), I(1), I(1), 걸, I(self.최대길이)]))
            L.append(_띄움(k["정수조각접기칸"], (NH, 1), (256, 1), [P(self.조각칸), P(self.att), I(1), I(1), 걸, I(self.최대길이)]))
            L.append(lin("_잔차", self.att, w["o"], self.영치우침, self.h, D, D, (self.h,)))
            L.append(_띄움(k["RMS정규화줄"], (1, 1), (256, 1), [P(self.h), P(w["n2"]), P(self.x)]))
            L.append(lin("", self.x, w["gu"], self.영치우침, self.gu, D, 2 * F))
            L.append(_띄움(k["SwiGLU줄"], ((F + 255) // 256, 1), (256, 1), [P(self.gu), P(self.f), I(1)]))
            L.append(lin("_잔차", self.f, w["down"], self.영치우침, self.h, F, D, (self.h,)))
        L.append(_띄움(k["RMS정규화줄"], (1, 1), (256, 1), [P(self.h), P(self.norm), P(self.x)]))
        L.append(lin("", self.x, self.머리, self.영치우침, self.logits, D, V, 로짓=True))
        L.append(_띄움(k["가장큰번호칸"], (1, 1), (256, 1), [P(self.logits), P(self.생성칸), I(1), I(V), 걸]))
        ex, g, _ = self._그래프만들기(L)
        self._생성그래프 = (L, ex, g)

    def _줄층(self, l, w, M, m, pos, 칸=False):
        """줄 길(행 넷까지)의 층 하나 — 묶은 판: QKV(RMS · 치우침 · RoPE · q 자리 · KV 캐시) → 정수조각어텐션 + 정수조각접기 → o(_잔차) →
        gate·up(RMS · SwiGLU → f) → down(_잔차). 칸: 생성 그래프의 판(위치를 걸음칸에서 — pos 는 걸음칸의 주소)."""
        k, D, F, NH = self.k, self.D, self.F, self.NH
        P, I = c_u64, c_i64
        KV = [P(self.kc[l]), P(self.vc[l]), P(self.ke[l]), P(self.ve[l])]
        조각수 = self.최대길이 // 64
        묶 = lambda 이름, N: ((N + self.줄판[이름][3] - 1) // self.줄판[이름][3], 1)
        q = "칸" if 칸 else ""
        return [_띄움(k["정수줄선형QKV" + q], 묶("QKV", self.QKV), (256, 1),
                      [P(self.h), P(w["n1"]), P(w["qkv"][0]), P(w["qkv"][1]), P(w["qkv치우침"]), P(self.자릿값q), P(self.정보q)] + KV +
                      [P(self.코사인), P(self.사인), I(M), I(self.QKV), I(m), pos, I(self.최대길이)]),
                _띄움(k["정수조각어텐션" + q], ((조각수 + 7) // 8, M * NH), (256, 1),
                      [P(self.자릿값q), P(self.정보q)] + KV + [P(self.조각칸), I(M), I(m), pos, I(self.최대길이)]),
                _띄움(k["정수조각접기" + q], (M * NH, 1), (256, 1), [P(self.조각칸), P(self.att), I(M), I(m), pos, I(self.최대길이)]),
                _띄움(k["정수줄선형o"], 묶("o", D), (256, 1), [P(self.att), P(w["o"][0]), P(w["o"][1]), P(self.영치우침), P(self.h), P(self.h),
                                                          I(M), I(D)]),
                _띄움(k["정수줄선형gu"], 묶("gu", 2 * F), (256, 1), [P(self.h), P(w["n2"]), P(w["gu"][0]), P(w["gu"][1]), P(self.영치우침),
                                                               P(self.f), I(M), I(2 * F)]),
                _띄움(k["정수줄선형down"], 묶("down", D), (256, 1), [P(self.f), P(w["down"][0]), P(w["down"][1]), P(self.영치우침), P(self.h),
                                                              P(self.h), I(M), I(D)])]

    def _로짓줄(self, src, dst, b):
        """행 하나의 로짓(RMS 를 묶은 판) — 출력 dst, 블록마다의 가장 큰 값 · 번호를 부분값 · 부분번호의 행 b 에."""
        P, I = c_u64, c_i64
        w = self.줄판["로짓"][3]
        return _띄움(self.k["정수줄선형로짓"], (self.부분수, 1), (256, 1),
                     [P(src), P(self.norm), P(self.머리[0]), P(self.머리[1]), P(self.영치우침), P(dst), P(self.부분값 + b * self.부분수 * 4),
                      P(self.부분번호 + b * self.부분수 * 8), I(1), I(self.V)])

    # ── 생성 ──

    def _메가띄우기(self, 토큰시작, 시작위치, 생성수, 끝들=(), 기록칸=None):
        """15단계 생성 메가커널을 한 번(협력 실행): 생성칸[토큰시작] 의 토큰(위치 시작위치)부터 토큰 생성수 − 1 개를 생성칸[토큰시작 + 1 …] 에.
        끝들(둘까지)이 나오면 거기서 멈춘다. 기록칸: 걸음마다의 로짓 [생성수 − 1][어휘] 을 둘 곳(시험용). 기다리지 않는다."""
        assert 시작위치 + 생성수 - 1 <= self.최대길이 and 토큰시작 + 생성수 <= self.생성최대
        P, I = c_u64, c_i64
        cu = self.dr.cu
        self.dr.확인(cu.cuMemsetD8_v2(c_u64(self.메가장벽), 0, ctypes.c_size_t(256)))
        w0 = self.층[0]
        끝 = list(끝들)[:2] + [-1, -1]
        ps = [P(self.생성칸), P(self.낱말[0]), P(self.낱말[1]), P(self.머리[0]), P(self.머리[1]), P(self.norm), P(w0["n1"]), P(w0["n2"]),
              P(w0["qkv"][0]), P(w0["qkv"][1]), P(w0["qkv치우침"]), P(w0["o"][0]), P(w0["o"][1]), P(w0["gu"][0]), P(w0["gu"][1]),
              P(w0["down"][0]), P(w0["down"][1]), P(self.kc바탕), P(self.vc바탕), P(self.ke바탕), P(self.ve바탕), P(self.코사인), P(self.사인),
              P(self.영치우침), P(self.h), P(self.자릿값q), P(self.정보q), P(self.att), P(self.f), P(self.자릿값2), P(self.정보2), P(기록칸 or self.logits),
              P(self.메가부분값), P(self.메가부분번호), P(self.메가장벽), P(self.주의셈), P(self.조각칸), P(self.시각칸),
              I(토큰시작), I(시작위치), I(생성수), I(self.최대길이), I(self.메가격자), I(끝[0]), I(끝[1]), I(1 if 기록칸 else 0),
              I(self.시각재기)]
        assert all(x.value % 16 == 0 for x in ps if isinstance(x, c_u64)), "메가커널의 참조 매개변수가 16 바이트 정렬이 아니다"
        args = (ctypes.c_void_p * len(ps))(*[ctypes.cast(ctypes.byref(x), ctypes.c_void_p) for x in ps])
        self._메가인자 = (ps, args)                   # 실행이 끝날 때까지 살려 둔다
        r = cu.cuLaunchCooperativeKernel(self.k["생성메가qwen"], self.메가격자, 1, 1, 256, 1, 1, 0, None, args)
        if r != 0:
            raise RuntimeError(f"생성 메가커널 실행 오류 {r}")

    def _걸음두기(self, 위치, 걸음=0):
        self.dr.올리기(self.걸음칸, np.array([위치, 걸음], np.int64))

    def _걸음띄우기(self, n):
        """생성 그래프를 n 번 잇따라 띄운다(기다리지 않는다)."""
        if self._생성그래프 is None:
            self._생성그래프만들기()
        ex = self._생성그래프[1]
        launch = self.dr.cu.cuGraphLaunch
        for _ in range(n):
            r = launch(ex, None)
            if r != 0:
                raise RuntimeError(f"생성 그래프 실행 오류 {r}")

    def 생성(self, ids, n):
        """탐욕 생성(문장 하나): 프롬프트를 한 번에 처리하고(첫 토큰까지) 나머지 n − 1 개는 생성 그래프로. 토큰 n 개."""
        p = len(ids)
        assert p + n - 1 <= self.최대길이 and n <= self.생성최대
        for a in range(0, p, self.최대행):               # 최대행보다 긴 프롬프트는 나눠 넣는다(같은 비트 — 계약)
            조각 = ids[a:a + self.최대행]
            self.토큰넣기(조각)
            self.계산(1, len(조각), a, "끝", 출력자리=self.생성칸)
        if n > 1:
            if self.메가쓰기:
                self._메가띄우기(0, p, n)
            else:
                self._걸음두기(p)
                self._걸음띄우기(n - 1)
        out = np.zeros(n, np.int64)
        self.dr.맞추기()
        return [int(t) for t in self.dr.내리기(self.생성칸, out)]

    def 이어넣기(self, 덩이, 위치):
        """덩이를 위치부터 앞 캐시에 이어 넣고 마지막 행의 탐욕 토큰을 생성칸[0] 에 — 그 토큰을 돌려준다. 덩이가 최대행보다 길면 나눠 넣는다."""
        for a in range(0, len(덩이), self.최대행):
            조각 = 덩이[a:a + self.최대행]
            self.토큰넣기(조각)
            self.계산(1, len(조각), 위치 + a, "끝", 출력자리=self.생성칸)
        self.dr.맞추기()
        return int(self.dr.내리기(self.생성칸, np.zeros(1, np.int64))[0])

    def 이어생성(self, 첫, 위치, k, 끝들=(), 묶음=16, 받기=None):
        """생성칸[0] 의 토큰(첫 — 이어넣기가 고른 것)을 위치에 두고 이어서 k 개를 생성 그래프로(마지막 것은 넣지 않는다). 토큰 k + 1 개(첫
        포함)를 돌려준다 — 끝들(끝 토큰)이 나오면 거기까지. 걸음을 1 · 2 · 4 · … · 묶음 개씩 띄우고 한 번씩 기다려 받기(새 토큰들)를 부른다
        (흘려 보이기 — 짧은 답에서 끝 토큰 뒤에 헛걸음이 적게). 끝 토큰 뒤의 헛걸음이 캐시의 뒷자리에 쓴 것은 다음 덩이가 덮는다(어텐션은
        제 위치까지만 읽는다)."""
        assert 위치 + k <= self.최대길이 and k + 1 <= self.생성최대
        if not self.메가쓰기:
            self._걸음두기(위치)
        토큰 = [첫]
        if 첫 in 끝들:
            return 토큰
        이번 = 1
        while len(토큰) < k + 1:
            n = min(이번, 묶음, k + 1 - len(토큰))
            이번 *= 2
            if self.메가쓰기:                         # 15단계: 메가커널 — 끝 토큰이 나오면 커널 안에서 멈춘다(헛걸음 없이)
                self._메가띄우기(len(토큰) - 1, 위치 + len(토큰) - 1, n + 1, 끝들)
            else:
                self._걸음띄우기(n)
            out = np.zeros(len(토큰) + n, np.int64)
            self.dr.맞추기()
            새 = [int(t) for t in self.dr.내리기(self.생성칸, out)[len(토큰):]]
            for i, t in enumerate(새):
                if t in 끝들:
                    새 = 새[:i + 1]
                    break
            토큰 += 새
            if 받기:
                받기(새)
            if 새 and 새[-1] in 끝들:
                break
        return 토큰

    def 생성로짓(self, ids, n):
        """탐욕 n 토큰과 걸음마다의 로짓 [n][어휘] (첫 걸음 = 프롬프트의 마지막 행) — 생성 그래프를 한 걸음씩(기다리며 로짓을 받는다). 시험용."""
        p = len(ids)
        for a in range(0, p, self.최대행):               # 최대행보다 긴 프롬프트는 나눠 넣는다(생성과 같이 — 같은 비트)
            조각 = ids[a:a + self.최대행]
            self.토큰넣기(조각)
            self.계산(1, len(조각), a, "끝", 출력자리=self.생성칸)
        로짓 = [self.로짓(1)[0].copy()]
        if self.메가쓰기 and n > 1:                   # 15단계: 메가커널이 걸음마다의 로짓을 기록칸에(기록 = 1)
            if self._로짓기록[1] < n - 1:
                self._로짓기록 = (self.dr.할당((n - 1) * self.V * 4), n - 1)
            self._메가띄우기(0, p, n, 기록칸=self._로짓기록[0])
            self.dr.맞추기()
            로짓 += list(self.dr.내리기(self._로짓기록[0], np.empty((n - 1, self.V), np.float32)))
        elif n > 1:
            self._걸음두기(p)
            for _ in range(n - 1):
                self._걸음띄우기(1)
                로짓.append(self.로짓(1)[0].copy())
        out = np.zeros(n, np.int64)
        self.dr.맞추기()
        return [int(t) for t in self.dr.내리기(self.생성칸, out)], np.stack(로짓)
