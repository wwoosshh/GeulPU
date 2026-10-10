"""속도 견주기의 엔진들 — 모두 같은 일(프롬프트 처리 + 첫 토큰, 탐욕 생성, 대화)을 한다.

  글엔진 — GeulPU (이 프로세스)
  라마엔진 — llama.cpp b11496 CUDA 를 제 프로세스(라마일꾼.py)에서 C API 로 — PyTorch(인텔 OpenMP)와 llama.cpp 의 CPU 백엔드(LLVM OpenMP)는
            한 프로세스에 함께 올 수 없다. 시간은 일꾼 안에서 잰다(프로세스 사이를 오가는 값은 llama.cpp 를 쓰는 사람이 치르지 않는다)
  참고선 — PyTorch f16(cuBLAS 행렬곱 + f16 SDPA, CUDA 그래프)의 프롬프트 — 의미를 지키지 않는 빠른 길의 참고선(torch 가 있을 때만)
(연구 4단계 재기4.py · 11단계 재기12.py 에서 옮김)
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import traceback

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, ".."))
sys.path.insert(0, os.path.join(ROOT, "시험"))
import 공통 as T           # noqa: E402

G = T.G


class 글엔진:
    이름 = "글"

    def __init__(self, w, 이름=None, **kw):
        self.m = G.글GPT2(w, **kw)
        if 이름:
            self.이름 = 이름

    def _잰다(self, f):
        self.m.dr.맞추기()
        s = time.perf_counter()
        f()
        self.m.dr.맞추기()
        return (time.perf_counter() - s) * 1000

    def 프롬프트(self, ids):
        self.m.생성(ids, 1)

    def 생성(self, ids, n):
        return self.m.생성(ids, n)

    def 잰_프롬프트(self, ids):
        return self._잰다(lambda: self.프롬프트(ids))

    def 잰_생성(self, ids, n):
        return self._잰다(lambda: self.생성(ids, n))

    def 대화(self, 덩이들, n, 처음=True):
        """차례마다 덩이를 앞 캐시에 이어 넣고(이어넣기) n 토큰 탐욕 생성(이어생성 — 마지막 토큰은 다음 덩이의 머리). 차례마다 (넣기 ms,
        생성 ms, 위치, 끝토큰) — 넣기는 첫 토큰까지, 생성은 나머지 n − 1 개."""
        m = self.m
        if 처음:
            self.위치 = 0
        out = []
        for 덩이 in 덩이들:
            m.dr.맞추기()
            t0 = time.perf_counter()
            첫 = m.이어넣기(덩이, self.위치)
            t1 = time.perf_counter()
            self.위치 += len(덩이)
            toks = m.이어생성(첫, self.위치, n - 1) if n > 1 else [첫]
            t2 = time.perf_counter()
            self.위치 += n - 1
            out.append({"넣기 ms": (t1 - t0) * 1000, "생성 ms": (t2 - t1) * 1000, "위치": self.위치, "끝토큰": toks[-1]})
        return out

    def 닫기(self):
        self.m.닫기()


class 일꾼:
    """라마일꾼.py — llama.cpp 를 제 프로세스에서. JSON 한 줄씩 묻고 답한다."""

    def __init__(self):
        self.p = subprocess.Popen([sys.executable, "-I", os.path.join(HERE, "라마일꾼.py")], stdin=subprocess.PIPE,
                                  stdout=subprocess.PIPE, text=True, encoding="utf-8")
        self.임시 = tempfile.mkdtemp(prefix="geulpu_")
        self.번호 = 0

    def 부르기(self, op, **kw):
        self.p.stdin.write(json.dumps({"op": op, **kw}, ensure_ascii=False) + "\n")
        self.p.stdin.flush()
        line = self.p.stdout.readline()
        if not line:
            raise RuntimeError("llama.cpp 일꾼이 멈췄다")
        r = json.loads(line)
        if not r.pop("ok"):
            raise RuntimeError(r["오류"])
        return r

    def 파일(self):
        self.번호 += 1
        return os.path.join(self.임시, f"{self.번호}.npy")

    def 끝(self):
        self.p.stdin.write(json.dumps({"op": "끝"}) + "\n")
        self.p.stdin.flush()
        self.p.wait(timeout=120)
        shutil.rmtree(self.임시, ignore_errors=True)


class 라마엔진:
    _수 = 0

    def __init__(self, 일, 이름, gguf, kv형식=1, n_ctx=1024, n_batch=1024, n_ubatch=512, n_seq_max=1, flash=-1):
        라마엔진._수 += 1
        self.일, self.이름, self.키 = 일, 이름, f"e{라마엔진._수}"
        self.문맥 = 일.부르기("열기", 키=self.키, gguf=gguf, kv형식=kv형식, n_ctx=n_ctx, n_batch=n_batch, n_ubatch=n_ubatch,
                            n_seq_max=n_seq_max, 모델원=None, flash=flash)["문맥"]

    def 잰_프롬프트(self, ids):
        return self.일.부르기("프롬프트", 키=self.키, ids=ids)["ms"]

    def 프롬프트(self, ids):
        self.잰_프롬프트(ids)

    def 잰_생성(self, ids, n):
        return self.일.부르기("생성", 키=self.키, ids=ids, n=n)["ms"]

    def 생성(self, ids, n):
        return self.일.부르기("생성", 키=self.키, ids=ids, n=n)["토큰"]

    def 대화(self, 덩이들, n, 처음=True):
        return self.일.부르기("대화", 키=self.키, 덩이들=덩이들, n=n, 처음=처음)["차례"]

    def _읽기(self, f):
        x = np.load(f)
        os.remove(f)
        return x

    def 생성로짓(self, ids, n):
        """탐욕 n 토큰과 걸음마다의 로짓 [n][어휘] (첫 걸음 = 프롬프트의 마지막 행)."""
        f = self.일.파일()
        toks = self.일.부르기("생성", 키=self.키, ids=ids, n=n, 파일=f)["토큰"]
        return toks, self._읽기(f)

    def 로짓들(self, seqs, 방식="한번에", 조각=64):
        """토큰열의 모든 행 로짓 [행][어휘]."""
        f = self.일.파일()
        self.일.부르기("로짓들", 키=self.키, seqs=seqs, 방식=방식, 조각=조각, 파일=f)
        return self._읽기(f)

    def 닫기(self):
        self.일.부르기("닫기", 키=self.키)


def 번갈아(엔진들, 잰일, 번, 기록):
    """엔진을 번갈아 번 번 — 엔진마다 중앙값 ms. 실패한 엔진은 기록에 적고 빼낸다."""
    t = {e.이름: [] for e in 엔진들}
    for _ in range(번):
        for e in list(엔진들):
            try:
                t[e.이름].append(잰일(e))
            except Exception as ex:
                기록[e.이름] = f"실패: {type(ex).__name__}: {str(ex)[:300]}"
                traceback.print_exc()
                엔진들.remove(e)
                t.pop(e.이름, None)
    return {k: round(float(np.median(v)), 4) for k, v in t.items() if v}


def 데우기(엔진들, 일, 기록):
    for e in list(엔진들):
        try:
            일(e)
        except Exception as ex:
            기록[e.이름] = f"실패: {type(ex).__name__}: {str(ex)[:300]}"
            traceback.print_exc()
            엔진들.remove(e)


def 세묶음(엔진들, 잰일, 실패):
    """번갈아 7번(중앙값)을 세 묶음 — 엔진마다 세 중앙값의 중앙값."""
    묶음 = [번갈아(엔진들, 잰일, 7, 실패) for _ in range(3)]
    return {k: round(float(np.median([m[k] for m in 묶음])), 4) for k in 묶음[0]}, 묶음


def 참고선(크기, ns):
    """PyTorch f16(cuBLAS 행렬곱 + f16 SDPA, CUDA 그래프) 프롬프트 처리 + 마지막 로짓 — 의미는 지키지 않는 빠른 길의 참고선(ms)."""
    import gc
    import torch
    import torch.nn.functional as F
    w = G.가중치읽기(os.path.join(T.모델폴더(크기), "model.safetensors"))
    D = w["wpe.weight"].shape[1]
    NH, NL = D // 64, sum(1 for k in w if k.startswith("h.") and k.endswith(".ln_1.weight"))
    t = lambda a, dt=torch.float32: torch.from_numpy(np.ascontiguousarray(a)).to("cuda", dt)
    층 = []
    for l in range(NL):
        p = f"h.{l}."
        d = {"g1": t(w[p + "ln_1.weight"]), "b1": t(w[p + "ln_1.bias"]), "g2": t(w[p + "ln_2.weight"]), "b2": t(w[p + "ln_2.bias"])}
        for a, h in (("qkv", "attn.c_attn"), ("o", "attn.c_proj"), ("fc", "mlp.c_fc"), ("pr", "mlp.c_proj")):
            d[a + "h"], d[a + "b"] = t(w[p + h + ".weight"], torch.float16), t(w[p + h + ".bias"])
        층.append(d)
    wte_h, wpe_h = t(w["wte.weight"], torch.float16), t(w["wpe.weight"], torch.float16)
    lnf_g, lnf_b = t(w["ln_f.weight"]), t(w["ln_f.bias"])
    del w
    ids = torch.randint(0, 50257, (1024,), device="cuda")

    @torch.no_grad()
    def 앞으로(ids):
        n = len(ids)
        x = (wte_h[ids] + wpe_h[:n]).float()
        for d in 층:
            h = F.layer_norm(x, (D,), d["g1"], d["b1"], 1e-5)
            qkv = (h.half() @ d["qkvh"]).float() + d["qkvb"]
            q, k, v = (a.view(n, NH, 64).transpose(0, 1).half() for a in qkv.split(D, dim=1))
            y = F.scaled_dot_product_attention(q, k, v, is_causal=True).transpose(0, 1).reshape(n, D)
            x = x + (y @ d["oh"]).float() + d["ob"]
            h = F.layer_norm(x, (D,), d["g2"], d["b2"], 1e-5)
            f = F.gelu((h.half() @ d["fch"]).float() + d["fcb"], approximate="tanh")
            x = x + (f.half() @ d["prh"]).float() + d["prb"]
        h = F.layer_norm(x[-1:], (D,), lnf_g, lnf_b, 1e-5)
        return (h.half() @ wte_h.T).argmax()
    out = {}
    for n in ns:
        x_ids = ids[:n]
        s = torch.cuda.Stream()
        s.wait_stream(torch.cuda.current_stream())
        with torch.cuda.stream(s):
            for _ in range(3):
                앞으로(x_ids)
        torch.cuda.current_stream().wait_stream(s)
        g = torch.cuda.CUDAGraph()
        with torch.cuda.graph(g):
            앞으로(x_ids)
        for _ in range(5):
            g.replay()
        torch.cuda.synchronize()
        ts = []
        for _ in range(7):
            torch.cuda.synchronize()
            t0 = time.perf_counter()
            g.replay()
            torch.cuda.synchronize()
            ts.append((time.perf_counter() - t0) * 1000)
        out[str(n)] = round(float(np.median(ts)), 2)
        del g
    del 층, wte_h, wpe_h
    gc.collect()
    torch.cuda.empty_cache()
    return out
