#!/usr/bin/env python3
"""계약 손실 검토(문서/계약손실검토.md) — 반올림 자리만 흉내 낸 fp64 앞으로 셋: 참값 · 계약 흉내 · llama.cpp 흉내.

같은 가중치(파일의 q · d 를 fp64 로 — 정확)와 같은 토큰(시험/평가글.txt)으로 층마다 세 길을 함께 돌리고, 모든 행의 다음 토큰 분포의 KL 과
반올림 자리마다의 상대 오차를 낸다. 반올림 자리:
  계약   — 선형의 입력 · q · k · v: 32 칸 블록마다 E = ⌊log₂ 최댓값⌋, 눈금 2^(E − 13), 가까운 짝수(문서/계약.md 1절 · 2절).
           어텐션: 64 키 조각마다 e_t = exp(s_t − 조각 최댓값), 값 블록 b 의 지수를 합친 e′_t = e_t · 2^(E_v,t,b) 를 키 32 개 블록마다 같은 눈금으로,
           o = Σ_조각 exp(m_조각 − M) Σ_t Q(e′)_t · n_v,t,b · 2⁻¹³ / Σ_조각 exp(m_조각 − M) Σ_t e_t (2절 4 · 3절 — 짧은실수 반올림은 빼고).
  llama  — 선형의 입력: Q8_1(블록 최댓값 / 127 눈금, 척도 d 는 반실수), q · k · v · 확률 P = exp(s − 행 최댓값): f16.
그 밖의 연산은 모두 fp64 다(흉내 — 비트까지의 계약이 아니다).

  python -I 재기/계약손실검토.py <출력.json> <gguf …>
"""
import json
import os
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, ".."))
for _d in ("엔진", "계약", "시험"):
    sys.path.insert(0, os.path.join(ROOT, _d))
import gguf읽기 as GR          # noqa: E402
import 토크나이저 as TK        # noqa: E402

f64 = np.float64


# ---- 반올림 자리 ----
def 계약자리(x, 축=-1):
    """32 칸 블록(축을 따라)마다 2^(E − 13) 눈금, 가까운 짝수."""
    x = np.moveaxis(np.asarray(x, f64), 축, -1)
    s = x.shape
    xb = x.reshape(s[:-1] + (s[-1] // 32, 32))
    m = np.abs(xb).max(-1, keepdims=True)
    E = np.where(m > 0, np.clip(np.floor(np.log2(np.where(m > 0, m, 1.0))), -98, 100), -98)
    눈 = np.ldexp(1.0, (E - 13).astype(np.int64))
    q = (np.rint(xb / 눈) * 눈).reshape(s)
    return np.moveaxis(q, -1, 축)


def 계약지수(x, 축=-1):
    """블록마다 E (값 블록의 지수 — 확률에 합친다)."""
    x = np.moveaxis(np.asarray(x, f64), 축, -1)
    s = x.shape
    m = np.abs(x.reshape(s[:-1] + (s[-1] // 32, 32))).max(-1)
    return np.where(m > 0, np.clip(np.floor(np.log2(np.where(m > 0, m, 1.0))), -98, 100), -98)


def Q8_1(x):
    """llama.cpp 의 활성값 양자화: 32 칸 블록마다 d = 최댓값 / 127 (반실수로), q = 반올림(x / d)."""
    x = np.asarray(x, f64)
    s = x.shape
    xb = x.reshape(s[:-1] + (s[-1] // 32, 32))
    d = (np.abs(xb).max(-1, keepdims=True) / 127.0).astype(np.float16).astype(f64)
    q = np.where(d > 0, np.round(xb / np.where(d > 0, d, 1.0)), 0.0)
    return (q * d).reshape(s)


def f16(x):
    return np.asarray(x, f64).astype(np.float16).astype(f64)


def 상대(a, b):
    """‖a − b‖ / ‖b‖."""
    n = np.linalg.norm(b)
    return float(np.linalg.norm(a - b) / n) if n > 0 else 0.0


def 버림비율(xq, x):
    """0 이 아니던 값 중 0 이 된 비율."""
    nz = x != 0
    return float(np.count_nonzero(nz & (xq == 0)) / max(1, np.count_nonzero(nz)))


# ---- 가중치 ----
def 풀기(g, name):
    """GGUF Q8_0 · Q4_0 텐서 → fp64 [N][K] (q · d 정확)."""
    t, dims, raw = g.원(name)
    K, N = dims
    if t == GR.Q8_0:
        bl = np.asarray(raw).reshape(N, K // 32, 34)
        d = np.ascontiguousarray(bl[:, :, :2]).view(np.float16)[:, :, 0].astype(f64)
        q = np.ascontiguousarray(bl[:, :, 2:]).view(np.int8).astype(f64)
        return (q * d[:, :, None]).reshape(N, K)
    if t == GR.Q4_0:
        bl = np.asarray(raw).reshape(N, K // 32, 18)
        d = np.ascontiguousarray(bl[:, :, :2]).view(np.float16)[:, :, 0].astype(f64)
        qs = bl[:, :, 2:]
        q = np.concatenate([qs & 15, qs >> 4], 2).astype(f64) - 8.0
        return (q * d[:, :, None]).reshape(N, K)
    if t in (GR.F32, GR.F16):
        return g.풀기(name).astype(f64)
    raise ValueError(f"{name}: 형식 {t}")


def 행풀기(g, name, rows):
    """낱말표의 행들만(토큰) — fp64 [len(rows)][K]."""
    t, dims, raw = g.원(name)
    K, N = dims
    bb = {GR.Q8_0: 34, GR.Q4_0: 18}[t]
    bl = np.asarray(raw).reshape(N, K // 32, bb)[rows]
    d = np.ascontiguousarray(bl[:, :, :2]).view(np.float16)[:, :, 0].astype(f64)
    if t == GR.Q8_0:
        q = np.ascontiguousarray(bl[:, :, 2:]).view(np.int8).astype(f64)
    else:
        qs = bl[:, :, 2:]
        q = np.concatenate([qs & 15, qs >> 4], 2).astype(f64) - 8.0
    return (q * d[:, :, None]).reshape(len(rows), K)


# ---- 블록 ----
def rms(x, w, eps):
    return x / np.sqrt((x * x).mean(-1, keepdims=True) + eps) * w


def rope(x, 위치, base, hd):
    """NeoX — 반쪽 돌리기. x [n][머리][hd]."""
    i = np.arange(hd // 2, dtype=f64)
    θ = base ** (-2.0 * i / hd)
    각 = 위치[:, None].astype(f64) * θ[None, :]
    c, s = np.cos(각)[:, None, :], np.sin(각)[:, None, :]
    a, b = x[..., :hd // 2], x[..., hd // 2:]
    return np.concatenate([a * c - b * s, b * c + a * s], -1)


def 계약확률(s, vv, 통계=None):
    """계약의 어텐션 한 머리 — s [n][n] (가린 칸 −inf), vv [n][hd] (계약 눈금). 64 키 조각마다 e = exp(s − 조각 최댓값), 값 블록 b 마다
    e′ = e · 2^E_v 를 키 32 개 블록마다 계약 눈금으로, 조각들을 정확히 접는다. 통계가 있으면 e′ 반올림의 상대 오차를 담는다."""
    n, hd = vv.shape
    nb = hd // 32
    np64 = (n + 63) // 64 * 64
    sp = np.full((n, np64), -np.inf)
    sp[:, :n] = s
    sseg = sp.reshape(n, np64 // 64, 64)
    mseg = sseg.max(2)                                                      # [n][조각]
    유효 = np.isfinite(mseg)
    mz = np.where(유효, mseg, 0.0)
    e = np.where(np.isfinite(sseg), np.exp(np.where(np.isfinite(sseg), sseg, 0.0) - mz[:, :, None]), 0.0)
    lseg = e.sum(2)
    vp = np.zeros((np64, hd))
    vp[:n] = vv
    Ev = 계약지수(vp, 1)                                                     # [키][nb]
    nv = vp / np.ldexp(1.0, np.repeat(Ev, 32, 1).astype(np.int64))           # v = n_v · 2^(E_v − 13) → n_v · 2⁻¹³
    oseg = np.zeros((n, np64 // 64, hd))
    for b in range(nb):
        ep = e * np.ldexp(1.0, Ev[:, b].astype(np.int64)).reshape(1, np64 // 64, 64)
        epq = 계약자리(ep.reshape(n, np64), 1).reshape(n, np64 // 64, 64)
        if 통계 is not None:
            통계["P_계약"].append(상대(epq, ep))
        nvb = nv[:, 32 * b:32 * b + 32].reshape(np64 // 64, 64, 32)
        oseg[:, :, 32 * b:32 * b + 32] = np.einsum("nsk,skd->nsd", epq, nvb)
    M = np.where(유효, mseg, -np.inf).max(1, keepdims=True)
    w = np.where(유효, np.exp(np.where(유효, mz - M, 0.0)), 0.0)            # [n][조각]
    return (w[:, :, None] * oseg).sum(1) / (w * lseg).sum(1, keepdims=True)


def 어텐션(q, k, v, 길, 통계):
    """q [n][NH][hd], k · v [n][NKV][hd] — 원인 가림. 길: 참 · 계약 · 라마. 통계(참 길만): 확률 반올림의 상대 오차(계약 · f16)."""
    n, NH, hd = q.shape
    NKV = k.shape[1]
    G = NH // NKV
    out = np.empty((n, NH, hd), f64)
    가림 = np.triu(np.ones((n, n), bool), 1)
    for h in range(NH):
        kv = h // G
        s = (q[:, h, :] @ k[:, kv, :].T) / np.sqrt(hd)
        s = np.where(가림, -np.inf, s)
        vv = v[:, kv, :]
        if 길 == "계약":
            out[:, h, :] = 계약확률(s, vv)
            continue
        m = s.max(1, keepdims=True)
        P = np.exp(s - m)
        l = P.sum(1, keepdims=True)
        if 길 == "라마":
            out[:, h, :] = (f16(P) @ vv) / l
            continue
        out[:, h, :] = (P @ vv) / l
        if 통계 is not None:
            통계["P_라마"].append(상대(f16(P), P))
            계약확률(s, 계약자리(vv), 통계)                                 # 같은 점수 · 값(계약 눈금)에서 확률 반올림의 오차만
    return out.reshape(n, NH * hd)


def 활(x, 길):
    if 길 in ("계약", "계약활성"):
        return 계약자리(x)
    if 길 == "라마":
        return Q8_1(x)
    return x


def 자리통계(통계, 이름, x):
    통계[이름 + "_계약"].append(상대(계약자리(x), x))
    통계[이름 + "_라마"].append(상대(Q8_1(x), x))
    통계[이름 + "_버림"].append(버림비율(계약자리(x), x))


def 모델(gguf, ids, 분해=False):
    g = GR.GGUF(gguf)
    m = g.meta
    NL, NH, NKV = m["qwen2.block_count"], m["qwen2.attention.head_count"], m["qwen2.attention.head_count_kv"]
    eps = float(m["qwen2.attention.layer_norm_rms_epsilon"])
    base = float(m["qwen2.rope.freq_base"])
    n = len(ids)
    위치 = np.arange(n)
    h0 = 행풀기(g, "token_embd.weight", np.asarray(ids))
    D = h0.shape[1]
    hd = D // NH
    길들 = ("참", "계약", "라마") + (("계약활성", "계약KV", "계약확률") if 분해 else ())
    H = {p: h0.copy() for p in 길들}
    통계 = {k: [] for k in ("qkv_계약", "qkv_라마", "qkv_버림", "o_계약", "o_라마", "o_버림", "gu_계약", "gu_라마", "gu_버림",
                           "down_계약", "down_라마", "down_버림", "로짓_계약", "로짓_라마", "로짓_버림",
                           "q_계약", "q_f16", "k_계약", "k_f16", "v_계약", "v_f16", "q_버림", "k_버림", "v_버림",
                           "P_계약", "P_라마")}
    t0 = time.time()
    for l in range(NL):
        p = f"blk.{l}."
        Wq, Wk, Wv = 풀기(g, p + "attn_q.weight"), 풀기(g, p + "attn_k.weight"), 풀기(g, p + "attn_v.weight")
        bq, bk, bv = (g.풀기(p + f"attn_{a}.bias").astype(f64) for a in ("q", "k", "v"))
        Wo = 풀기(g, p + "attn_output.weight")
        n1, n2 = g.풀기(p + "attn_norm.weight").astype(f64), g.풀기(p + "ffn_norm.weight").astype(f64)
        Wg, Wu, Wd = 풀기(g, p + "ffn_gate.weight"), 풀기(g, p + "ffn_up.weight"), 풀기(g, p + "ffn_down.weight")
        for 길 in 길들:
            st = 통계 if 길 == "참" else None
            h = H[길]
            x = rms(h, n1, eps)
            if st is not None:
                자리통계(st, "qkv", x)
            xi = 활(x, 길)
            q = (xi @ Wq.T + bq).reshape(n, NH, hd)
            k = (xi @ Wk.T + bk).reshape(n, NKV, hd)
            v = (xi @ Wv.T + bv).reshape(n, NKV, hd)
            q, k = rope(q, 위치, base, hd), rope(k, 위치, base, hd)
            if st is not None:
                for nm, a in (("q", q), ("k", k), ("v", v)):
                    st[nm + "_계약"].append(상대(계약자리(a), a))
                    st[nm + "_f16"].append(상대(f16(a), a))
                    st[nm + "_버림"].append(버림비율(계약자리(a), a))
            if 길 in ("계약", "계약KV"):
                q, k, v = 계약자리(q), 계약자리(k), 계약자리(v)
            elif 길 == "라마":
                q, k, v = f16(q), f16(k), f16(v)
            a = 어텐션(q, k, v, {"계약확률": "계약", "계약활성": "참", "계약KV": "참"}.get(길, 길), st)
            if st is not None:
                자리통계(st, "o", a)
            h = h + 활(a, 길) @ Wo.T
            x = rms(h, n2, eps)
            if st is not None:
                자리통계(st, "gu", x)
            xi = 활(x, 길)
            gg, uu = xi @ Wg.T, xi @ Wu.T
            f = gg / (1.0 + np.exp(-gg)) * uu
            if st is not None:
                자리통계(st, "down", f)
            h = h + 활(f, 길) @ Wd.T
            H[길] = h
        del Wq, Wk, Wv, Wo, Wg, Wu, Wd
        print(f"  층 {l}: {time.time() - t0:.0f} 초", flush=True)
    nf = g.풀기("output_norm.weight").astype(f64)
    머리 = "output.weight" if "output.weight" in g.tensors else "token_embd.weight"
    t, dims, _ = g.원(머리)
    V = dims[1]
    X = {}
    for 길 in 길들:
        x = rms(H[길], nf, eps)
        if 길 == "참":
            자리통계(통계, "로짓", x)
        X[길] = 활(x, 길)
    로짓 = {p: np.empty((n, V)) for p in 길들}
    덩이 = 16384
    for r0 in range(0, V, 덩이):
        r1 = min(V, r0 + 덩이)
        W = 행풀기(g, 머리, np.arange(r0, r1))
        for 길 in 길들:
            로짓[길][:, r0:r1] = X[길] @ W.T
    def 로그확률(z):
        z = z - z.max(1, keepdims=True)
        return z - np.log(np.exp(z).sum(1, keepdims=True))
    lp = {p: 로그확률(로짓[p]) for p in 길들}
    pr = np.exp(lp["참"])
    결과 = {"모델": os.path.basename(gguf), "토큰": n, "층": NL, "너비": D, "머리 크기": hd}
    for 길 in 길들[1:]:
        kl = (pr * (lp["참"] - lp[길])).sum(1)
        결과[f"KL_{길}"] = float(kl.mean())
        결과[f"고른 토큰 일치_{길}"] = float((lp[길].argmax(1) == lp["참"].argmax(1)).mean())
    결과["r"] = 결과["KL_계약"] / 결과["KL_라마"]
    # 반올림 자리마다: 층마다 값(층 차례), 계약 / 라마(또는 f16)의 비가 가장 큰 층
    자리 = {}
    for 이름, 짝 in (("qkv", "라마"), ("o", "라마"), ("gu", "라마"), ("down", "라마"), ("로짓", "라마"),
                    ("q", "f16"), ("k", "f16"), ("v", "f16"), ("P", "라마")):
        c = np.asarray(통계[f"{이름}_계약"])
        o = np.asarray(통계[f"{이름}_{짝}"])
        if 이름 == "P":                          # 머리 · 값 블록마다의 값을 층마다 모은다
            c = c.reshape(NL, -1).max(1)
            o = o.reshape(NL, -1).max(1)
        비 = c / np.where(o > 0, o, np.inf)
        한 = {"계약 (층마다)": [float(x) for x in c], f"{짝} (층마다)": [float(x) for x in o],
             "계약 / 견줌 가장 큰 비": float(비.max()), "그 층": int(비.argmax())}
        if f"{이름}_버림" in 통계:
            b = np.asarray(통계[f"{이름}_버림"])
            한["계약이 0 으로 만든 비율 (가장 큰 층)"] = float(b.max())
        자리[이름] = 한
    결과["반올림 자리"] = 자리
    결과["초"] = round(time.time() - t0, 1)
    return 결과


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    출력 = sys.argv[1]
    파일들 = [a for a in sys.argv[2:] if not a.startswith("--")]
    tk = TK.Qwen토크나이저(gguf=파일들[0])
    ids = tk.나누기(open(os.path.join(ROOT, "시험", "평가글.txt"), encoding="utf-8").read())[:1024]
    print("토큰", len(ids), flush=True)
    결과 = []
    for f in 파일들:
        print("모델", os.path.basename(f), flush=True)
        r = 모델(f, ids, "--분해" in sys.argv)
        결과.append(r)
        print(f"  KL 계약 {r['KL_계약']:.3e} · 라마 {r['KL_라마']:.3e} · r = 1/{1 / r['r']:.0f} · 고른 토큰 일치 {r['고른 토큰 일치_계약']:.4f} / "
              f"{r['고른 토큰 일치_라마']:.4f}", flush=True)
        for 길 in ("계약활성", "계약KV", "계약확률"):
            if f"KL_{길}" in r:
                print(f"  (분해) KL {길} {r[f'KL_{길}']:.3e}", flush=True)
        for 이름, 한 in r["반올림 자리"].items():
            print(f"  {이름}: 계약/견줌 가장 큰 비 {한['계약 / 견줌 가장 큰 비']:.3f} (층 {한['그 층']})"
                  + (f" · 0 으로 만든 비율 {한['계약이 0 으로 만든 비율 (가장 큰 층)']:.2e}" if "계약이 0 으로 만든 비율 (가장 큰 층)" in 한 else ""), flush=True)
        json.dump(결과, open(출력, "w", encoding="utf-8"), ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
