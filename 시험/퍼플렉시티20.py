#!/usr/bin/env python3
"""20단계 대조 도구 — 퍼플렉시티(llama-perplexity 의 방법: 512 토큰 덩이마다 위치 256 … 510 의 로짓 → 다음 토큰)를 덩이마다 셋으로:

  참값      GGUF 의 가중치를 풀어(Q8_0 의 q · d, F16 — 짧은실수로 정확) fp64 로 계산(torch, GPU) — Q8_0 과 F16 둘.
  글        파이썬 호스트(글qwen2 — 글 도구와 같은 PTX. 18d 에서 글 호스트와 비트가 같다)의 마지막 256 행 로짓(로짓 판).
  llama.cpp C API(재기/라마일꾼.py)로 llama-perplexity 와 같은 배치 — 덩이 넷을 시퀀스로 한 llama_decode(n_ctx 2048 · n_batch 2048 ·
            n_ubatch 512 · 플래시 어텐션 자동 · KV F16).

덩이마다(fp64, GPU): NLL 합, KL(참값Q8 ‖ 글 · llama.cpp), KL(참값F16 ‖ 참값Q8), 맨 위 토큰 일치. 대조: 토큰(글 · 파이썬 · llama.cpp),
llama.cpp 의 누적 PPL 이 llama-perplexity 의 출력과 같은지, 글 도구의 덩이마다 NLL 합(--기록)이 파이썬의 같은 값과 같은지,
Q8_0 이 F16 의 Q8_0 양자화인지.

  python -I 시험/퍼플렉시티20.py <wiki.test.raw — ASCII 경로> <출력.json> --글기록 <파일> --글토큰 <파일> --라마출력 <파일>
         [--덩이 N] [--통합 0|1]
"""
import argparse
import json
import math
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, ".."))
for _d in ("엔진", "계약", "커널", "시험"):
    sys.path.insert(0, os.path.join(ROOT, _d))
import gguf읽기 as GR      # noqa: E402
import 참값 as 참           # noqa: E402

Q8 = os.path.join(ROOT, "모델", "qwen2.5-0.5b-instruct-gguf", "qwen2.5-0.5b-instruct-q8_0.gguf")
F16 = os.path.join(ROOT, "모델", "qwen2.5-0.5b-instruct-gguf-f16", "qwen2.5-0.5b-instruct-fp16.gguf")
PTX = os.path.join(ROOT, "빌드", "글", "qwen2Q8.ptx")
문맥, 첫 = 512, 256
채점 = 문맥 - 1 - 첫


class 일꾼:
    """재기/라마일꾼.py — llama.cpp 를 제 프로세스에서(파이토치의 OpenMP 와 한 프로세스에 둘 수 없다). JSON 한 줄씩."""

    def __init__(self):
        self.p = subprocess.Popen([sys.executable, "-I", os.path.join(ROOT, "재기", "라마일꾼.py")], stdin=subprocess.PIPE,
                                  stdout=subprocess.PIPE, text=True, encoding="utf-8")
        self.임시 = tempfile.mkdtemp(prefix="geulpu20_")

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

    def 파일(self, 이름):
        return os.path.join(self.임시, 이름)

    def 끝(self):
        self.p.stdin.write(json.dumps({"op": "끝"}) + "\n")
        self.p.stdin.flush()
        self.p.wait(timeout=120)
        shutil.rmtree(self.임시, ignore_errors=True)


class 참값엔진:
    """시험/참값.qwen2_로짓 과 같은 식(fp64 — RMSNorm · RoPE NeoX · GQA 원인 어텐션 · SwiGLU)인데, 가중치를 GPU 에 짧은실수로 두고
    (Q8_0 · F16 의 값은 짧은실수로 정확) 쓸 때 fp64 로 넓힌다. 덩이(512 토큰)의 위치 첫 … 문맥 − 2 행의 로그 확률(fp64)을 낸다."""

    def __init__(self, path, 장치="cuda"):
        import torch
        W, 설정 = 참.qwen2_gguf(path)
        같은것 = {}
        self.W = {}
        for k, v in W.items():
            if id(v) not in 같은것:
                같은것[id(v)] = torch.from_numpy(np.ascontiguousarray(v, dtype=np.float32)).to(장치)
            self.W[k] = 같은것[id(v)]
        self.설정, self.장치 = 설정, 장치
        self.D = self.W["embed"].shape[1]
        self.V = self.W["head"].shape[0]
        self.NH, self.NKV = 설정["머리"], 설정["KV머리"]
        self.hd = self.D // self.NH
        hd = self.hd
        inv = 1.0 / (설정["theta"] ** (torch.arange(0, hd, 2, dtype=torch.float64, device=장치) / hd))
        ang = torch.arange(문맥, dtype=torch.float64, device=장치)[:, None] * inv[None, :]
        self.cos = torch.cat([ang.cos(), ang.cos()], 1)
        self.sin = torch.cat([ang.sin(), ang.sin()], 1)
        self.가림 = torch.full((문맥, 문맥), float("-inf"), dtype=torch.float64, device=장치).triu(1)

    def 로그확률(self, ids):
        import torch
        W, 설정, hd, NH, NKV, D = self.W, self.설정, self.hd, self.NH, self.NKV, self.D
        T = lambda a: a.double()
        with torch.no_grad():
            n = len(ids)
            assert n == 문맥
            x = T(W["embed"][torch.as_tensor(np.asarray(ids, dtype=np.int64), device=self.장치)])

            def rms(v, g):
                return v / torch.sqrt((v * v).mean(-1, keepdim=True) + 설정["eps"]) * T(g)

            def rope(t):
                t1, t2 = t[..., :hd // 2], t[..., hd // 2:]
                return t * self.cos + torch.cat([-t2, t1], -1) * self.sin
            for l in range(설정["층"]):
                h = rms(x, W[f"{l}.n1"])
                q = h @ T(W[f"{l}.wq"]).T + T(W[f"{l}.bq"])
                k = h @ T(W[f"{l}.wk"]).T + T(W[f"{l}.bk"])
                v = h @ T(W[f"{l}.wv"]).T + T(W[f"{l}.bv"])
                q = rope(q.view(n, NH, hd).transpose(0, 1))
                k = rope(k.view(n, NKV, hd).transpose(0, 1)).repeat_interleave(NH // NKV, 0)
                v = v.view(n, NKV, hd).transpose(0, 1).repeat_interleave(NH // NKV, 0)
                s = q @ k.transpose(1, 2) / (hd ** 0.5) + self.가림
                y = (torch.softmax(s, -1) @ v).transpose(0, 1).reshape(n, D)
                x = x + y @ T(W[f"{l}.wo"]).T
                h = rms(x, W[f"{l}.n2"])
                g_, u = h @ T(W[f"{l}.wg"]).T, h @ T(W[f"{l}.wu"]).T
                x = x + (g_ * torch.sigmoid(g_) * u) @ T(W[f"{l}.wd"]).T
            x = rms(x[첫:문맥 - 1], W["norm"])
            로짓 = torch.empty((채점, self.V), dtype=torch.float64, device=self.장치)
            for a in range(0, self.V, 32768):
                로짓[:, a:a + 32768] = x @ T(W["head"][a:a + 32768]).T
            return torch.log_softmax(로짓, -1)


def 체크포인트(q8path, f16path):
    """Q8_0 GGUF 가 F16 GGUF 의 가중치를 llama.cpp 의 Q8_0 양자화(quantize_row_q8_0_ref: d = amax/127, q = roundf(x · (1/d)), d 는 f16)로
    만든 것인가 — 텐서마다 블록(32 값)이 바이트까지 같은 수. F32 텐서(정규화 · 치우침)는 바이트 그대로 같은가."""
    a, b = GR.GGUF(q8path), GR.GGUF(f16path)
    out = {"F32 텐서": 0, "F32 같음": 0, "Q8 블록": 0, "Q8 같은 블록": 0, "다른 텐서": [], "형식": {}}
    assert set(a.tensors) == set(b.tensors), "텐서 이름이 다르다"
    for name in sorted(a.tensors):
        ta, da, ra = a.원(name)
        tb, db, rb = b.원(name)
        out["형식"][f"{GR.이름.get(ta)}←{GR.이름.get(tb)}"] = out["형식"].get(f"{GR.이름.get(ta)}←{GR.이름.get(tb)}", 0) + 1
        assert da == db, name
        if ta == GR.F32 and tb == GR.F32:
            out["F32 텐서"] += 1
            out["F32 같음"] += int(np.array_equal(ra, rb))
            continue
        if ta == GR.Q8_0 and tb in (GR.F16, GR.F32):
            w = (rb.view(np.float16) if tb == GR.F16 else rb.view(np.float32)).astype(np.float32).reshape(-1, 32)
            amax = np.abs(w).max(1)
            d = (amax / np.float32(127)).astype(np.float32)
            idd = np.where(d != 0, np.float32(1) / np.where(d != 0, d, np.float32(1)), np.float32(0)).astype(np.float32)
            x0 = (w * idd[:, None]).astype(np.float32)
            q = (np.sign(x0) * np.floor(np.abs(x0) + np.float32(0.5))).astype(np.int8)       # roundf — 반은 0 에서 먼 쪽
            d16 = d.astype(np.float16)
            bl = ra.reshape(-1, 34)
            dq = bl[:, :2].copy().view(np.float16).reshape(-1)
            qq = bl[:, 2:].view(np.int8)
            같 = (dq.view(np.uint16) == d16.view(np.uint16)) & np.all(qq == q, 1)
            out["Q8 블록"] += int(같.size)
            out["Q8 같은 블록"] += int(같.sum())
            if not 같.all():
                out["다른 텐서"].append([name, int((~같).sum()), int(같.size)])
            continue
        out["다른 텐서"].append([name, "형식", GR.이름.get(ta), GR.이름.get(tb)])
    return out


def 라마출력값(path):
    """llama-perplexity 의 표준 출력에서 [i]값 — 덩이마다의 누적 PPL(소수 넷째 자리)과 Final estimate."""
    s = open(path, encoding="utf-8", errors="replace").read()
    vals = [float(v) for _, v in re.findall(r"\[(\d+)\]([0-9.]+),", s)]
    return vals


def 글기록값(path):
    """글 도구의 기록: '덩이 i <16진> <값>' 줄."""
    out = {}
    for line in open(path, encoding="utf-8"):
        p = line.split()
        if len(p) == 4 and p[0] == "덩이":
            out[int(p[1])] = (p[2], float(p[3]))
    return out


def main():
    import torch
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("글")
    ap.add_argument("출력")
    ap.add_argument("--글기록", required=True)
    ap.add_argument("--글토큰", required=True)
    ap.add_argument("--라마출력", required=True)
    ap.add_argument("--덩이", type=int, default=-1)
    ap.add_argument("--통합", type=int, default=0)
    a = ap.parse_args()
    시작 = time.time()
    결과 = {"시작": time.strftime("%Y-%m-%d %H:%M:%S"), "글": a.글, "통합KV": bool(a.통합)}

    # ── 대조: 같은 체크포인트 ──
    결과["체크포인트"] = 체크포인트(Q8, F16)
    print("체크포인트:", json.dumps({k: v for k, v in 결과["체크포인트"].items() if k != "다른 텐서"}, ensure_ascii=False),
          "다른 텐서", len(결과["체크포인트"]["다른 텐서"]), flush=True)

    # ── 대조: 토큰 ──
    import 토크나이저 as TK
    text = open(a.글, "rb").read().decode("utf-8")
    ids_py = np.asarray(TK.Qwen토크나이저(gguf=Q8).나누기(text), dtype=np.int64)
    ids_글 = np.fromfile(a.글토큰, dtype=np.int64)
    l = 일꾼()
    l.부르기("열기", 키="q8", gguf=Q8, kv형식=1, n_ctx=4 * 문맥, n_batch=4 * 문맥, n_ubatch=512, n_seq_max=4, flash=-1,
           통합=bool(a.통합))
    f = l.파일("토큰.npy")
    l.부르기("토큰", 키="q8", 글=a.글, 파일=f)
    ids_라 = np.load(f).astype(np.int64)
    결과["토큰"] = {"파이썬": int(len(ids_py)), "글": int(len(ids_글)), "llama.cpp": int(len(ids_라)),
                  "글=파이썬": bool(np.array_equal(ids_글, ids_py)), "글=llama.cpp": bool(np.array_equal(ids_글, ids_라))}
    print("토큰:", 결과["토큰"], flush=True)
    ids = ids_글
    덩이수 = len(ids) // 문맥
    if a.덩이 >= 0:
        덩이수 = min(덩이수, a.덩이)
    덩이수 -= 덩이수 % 4                                   # llama-perplexity 의 배치(덩이 넷)와 맞춘다 (584 = 4 × 146)

    # ── 엔진들 ──
    import 글qwen2
    g = 글qwen2.글Qwen2(Q8, 최대행=문맥, 최대문장=1, 최대길이=문맥, 로짓행=문맥 - 첫, ptx경로=PTX)
    refQ = 참값엔진(Q8)
    refF = 참값엔진(F16)
    V = refQ.V
    assert V == g.V == refF.V

    덩 = {k: [] for k in ("nll참Q8", "nll참F16", "nll글", "nll라마", "kl글", "kl라마", "kl형식", "맞음글", "맞음라마", "맞음형식")}
    for c0 in range(0, 덩이수, 4):
        묶 = [ids[(c0 + s) * 문맥:(c0 + s + 1) * 문맥] for s in range(4)]
        f = l.파일("배치.npy")
        l.부르기("퍼플배치", 키="q8", seqs=[x.tolist() for x in 묶], 첫=첫, 파일=f)
        라 = np.load(f)                                       # [4][255][V] f32
        for s in range(4):
            c = c0 + s
            덩ids = 묶[s]
            t = torch.as_tensor(덩ids[첫 + 1:문맥], device="cuda")
            g.토큰넣기(덩ids)
            g.계산(1, 문맥, 0, 로짓=문맥 - 첫)
            글로짓 = g.로짓(문맥 - 첫)[:채점]
            with torch.no_grad():
                lq = refQ.로그확률(덩ids)
                lf = refF.로그확률(덩ids)
                lg = torch.log_softmax(torch.from_numpy(글로짓).to("cuda").double(), -1)
                ll = torch.log_softmax(torch.from_numpy(라[s]).to("cuda").double(), -1)
                pq = lq.exp()
                pf = lf.exp()
                덩["nll참Q8"].append(float(-lq.gather(1, t[:, None]).sum()))
                덩["nll참F16"].append(float(-lf.gather(1, t[:, None]).sum()))
                덩["nll글"].append(float(-lg.gather(1, t[:, None]).sum()))
                덩["nll라마"].append(float(-ll.gather(1, t[:, None]).sum()))
                덩["kl글"].append(float((pq * (lq - lg)).sum()))
                덩["kl라마"].append(float((pq * (lq - ll)).sum()))
                덩["kl형식"].append(float((pf * (lf - lq)).sum()))
                aq = lq.argmax(1)
                덩["맞음글"].append(int((lg.argmax(1) == aq).sum()))
                덩["맞음라마"].append(int((ll.argmax(1) == aq).sum()))
                덩["맞음형식"].append(int((lf.argmax(1) == aq).sum()))
                del lq, lf, lg, ll, pq, pf
        if (c0 // 4) % 10 == 0 or c0 + 4 >= 덩이수:
            n = len(덩["nll글"]) * 채점
            print(f"덩이 {c0 + 4}/{덩이수} · {time.time() - 시작:.0f} 초 · PPL 참Q8 {math.exp(sum(덩['nll참Q8']) / n):.6f} "
                  f"글 {math.exp(sum(덩['nll글']) / n):.6f} 라마 {math.exp(sum(덩['nll라마']) / n):.6f} · KL 글 "
                  f"{sum(덩['kl글']) / n:.3e} 라마 {sum(덩['kl라마']) / n:.3e} 형식 {sum(덩['kl형식']) / n:.3e}", flush=True)
    l.끝()

    n = 덩이수 * 채점
    합 = {k: math.fsum(v) for k, v in 덩.items()}
    결과["덩이"] = 덩이수
    결과["채점 토큰"] = n
    결과["PPL"] = {"참값Q8": math.exp(합["nll참Q8"] / n), "참값F16": math.exp(합["nll참F16"] / n),
                  "글": math.exp(합["nll글"] / n), "llama.cpp": math.exp(합["nll라마"] / n)}
    결과["평균 NLL"] = {"참값Q8": 합["nll참Q8"] / n, "참값F16": 합["nll참F16"] / n, "글": 합["nll글"] / n, "llama.cpp": 합["nll라마"] / n}
    결과["평균 KL"] = {"참값Q8‖글": 합["kl글"] / n, "참값Q8‖llama.cpp": 합["kl라마"] / n, "참값F16‖참값Q8": 합["kl형식"] / n}
    결과["맨 위 일치"] = {"글": 합["맞음글"] / n, "llama.cpp": 합["맞음라마"] / n, "참값F16": 합["맞음형식"] / n}
    # 대조: llama.cpp 의 누적 PPL(C API) 이 llama-perplexity 의 출력과
    라값 = 라마출력값(a.라마출력)
    누 = np.cumsum(덩["nll라마"])
    우리 = [float(f"{math.exp(누[i] / ((i + 1) * 채점)):.4f}") for i in range(덩이수)]
    다른 = [i + 1 for i in range(min(덩이수, len(라값))) if abs(우리[i] - 라값[i]) > 5e-5]
    결과["llama-perplexity 대조"] = {"덩이": min(덩이수, len(라값)), "다른 덩이 수": len(다른), "다른 덩이(앞 20)": 다른[:20],
                                   "llama-perplexity 마지막": 라값[min(덩이수, len(라값)) - 1] if 라값 else None, "C API 마지막": 우리[-1]}
    # 대조: 글 도구의 덩이마다 NLL 합
    글값 = 글기록값(a.글기록)
    상대 = [abs(글값[i][1] - 덩["nll글"][i]) / abs(덩["nll글"][i]) for i in range(덩이수) if i in 글값]
    결과["글 도구 대조"] = {"덩이": len(상대), "가장 큰 상대 차": max(상대) if 상대 else None}
    결과["덩이마다"] = 덩
    결과["시간 (초)"] = time.time() - 시작
    json.dump(결과, open(a.출력, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    요약 = {k: v for k, v in 결과.items() if k != "덩이마다"}
    print(json.dumps(요약, ensure_ascii=False, indent=1), flush=True)


if __name__ == "__main__":
    main()
