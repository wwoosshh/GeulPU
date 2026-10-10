"""어텐션 시험 — 정수 KV 계약의 커널들을 CPU 참조(계약/정수계약.py)와 비트로 대조한다.

  커널대조 — 실제 모델 층의 q · k · v 로 KV정수로 의 캐시 바이트 · 프롬프트 어텐션(판 하나)의 출력 자리 · 정보 · 생성 판(정수조각어텐션 +
            정수조각접기)의 O/L (연구 9단계 재기10.py)
  긴대조 — 합성 긴 모델의 엔진으로 맥락 × 덩이마다 새 판(묶음 판 질의 64 · 16 + 묶음 접기, 두 층 판, 생성 판)을 새 CPU 참조(두 층 접기)와,
          판끼리(모든 머리), 위치 1024 이하면 차례 판과도 (연구 13단계 재기14.py)
"""
import time

import numpy as np

from 공통 import G, C, u64, i64, f32, 다른칸

어텐션판 = {"정수어텐션": (64, 128), "정수어텐션둘": (64, 256), "정수어텐션갈래": (16, 32 * G.갈래워프)}    # 판 → (블록의 질의 수, 스레드 수)


def 층qkv(w, ids, L, D):
    """fp64 로 층 L 까지 돌려 층 L 의 c_attn 출력 [n][3D] 을 짧은실수로 — 커널 대조의 입력(실제 모델 값의 분포; 커널과 CPU 참조가 같은 입력을
    본다). 가중치는 safetensors(글gpt2.가중치읽기)."""
    f64 = np.float64
    n = len(ids)
    NH = D // 64

    def ln(x, g, b):
        mu = x.mean(-1, keepdims=True)
        var = ((x - mu) ** 2).mean(-1, keepdims=True)
        return (x - mu) / np.sqrt(var + 1e-5) * g + b
    x = w["wte.weight"][ids].astype(f64) + w["wpe.weight"][:n].astype(f64)
    가림 = np.triu(np.full((n, n), -np.inf), 1)
    for l in range(L + 1):
        W = {k[len(f"h.{l}."):]: np.asarray(v, f64) for k, v in w.items() if k.startswith(f"h.{l}.")}
        h = ln(x, W["ln_1.weight"], W["ln_1.bias"])
        qkv = h @ W["attn.c_attn.weight"] + W["attn.c_attn.bias"]
        if l == L:
            break
        q, k, v = (t.reshape(n, NH, 64).transpose(1, 0, 2) for t in np.split(qkv, 3, axis=1))
        s = q @ k.transpose(0, 2, 1) / 8.0 + 가림
        s = np.exp(s - s.max(-1, keepdims=True))
        s /= s.sum(-1, keepdims=True)
        y = (s @ v).transpose(1, 0, 2).reshape(n, D)
        x = x + y @ W["attn.c_proj.weight"] + W["attn.c_proj.bias"]
        h = ln(x, W["ln_2.weight"], W["ln_2.bias"])
        u = h @ W["mlp.c_fc.weight"] + W["mlp.c_fc.bias"]
        u = 0.5 * u * (1 + np.tanh(np.sqrt(2 / np.pi) * (u + 0.044715 * u ** 3)))
        x = x + u @ W["mlp.c_proj.weight"] + W["mlp.c_proj.bias"]
    return qkv.astype(f32)


def 커널대조(m, 입력, 최대길이, 참조머리=None, 커널="정수어텐션"):
    """엔진 m 의 어텐션 커널을 입력 [n][3D](짧은실수 q · k · v)에 — KV정수로 의 캐시 바이트 · 프롬프트 어텐션(mma)의 출력 자리 · 정보 ·
    생성 판(dp4a — n ≤ 4096)의 O/L 을 CPU 참조와 비트 대조. 참조머리: CPU 참조를 할 머리들(없으면 모두)."""
    dr, D, NH = m.dr, m.D, m.NH
    n = 입력.shape[0]
    정보폭 = (n + 63) // 64 * 64

    def up(a):
        p = dr.할당(a.nbytes)
        dr.올리기(p, a)
        return p

    def zero(nb):
        p = dr.할당(nb)
        dr.확인(dr.cu.cuMemsetD8_v2(u64(p), 0, G.ctypes.c_size_t(nb)))
        return p

    def down(p, shape, dt):
        return dr.내리기(p, np.empty(shape, dt)).copy()

    def run(x):
        r = dr.cu.cuLaunchKernel(x.fn, x.grid[0], x.grid[1], 1, x.block[0], x.block[1], 1, 0, None, x.args, None)
        assert r == 0, r
    g입력 = up(입력)
    자릿값q, 정보q = zero(2 * n * D), zero(D // 32 * 정보폭 * 4)
    키칸, 값칸 = zero(NH * 2 * 최대길이 * 64), zero(NH * 최대길이 * 128)
    키지수, 값지수 = zero(NH * 최대길이 * 2), zero(NH * 최대길이 * 2)
    자릿값, 정보 = zero(2 * n * D), zero(D // 32 * 정보폭 * 4)
    생성판 = n <= 4096
    조각칸, 출력 = (zero(n * NH * (최대길이 // 64) * 68 * 4), zero(n * D * 4)) if 생성판 else (0, 0)
    k = m.k
    KV = [u64(키칸), u64(값칸), u64(키지수), u64(값지수)]
    run(G._띄움(k["KV정수로"], ((3 * D // 32 + 31) // 32, n), (256, 1), [u64(g입력), u64(자릿값q), u64(정보q)] + KV + [i64(n), i64(n), i64(0), i64(최대길이)]))
    Q, 스 = 어텐션판[커널]
    run(G._띄움(k[커널], (NH, (n + Q - 1) // Q), (스, 1), [u64(자릿값q), u64(정보q)] + KV + [u64(정보), u64(자릿값), i64(n), i64(n), i64(0), i64(최대길이)]))
    if 생성판:
        run(G._띄움(k["정수조각어텐션"], (((n - 1) // 64 + 1 + 7) // 8, n * NH), (256, 1), [u64(자릿값q), u64(정보q)] + KV + [u64(조각칸), i64(n), i64(n), i64(0), i64(최대길이)]))
        run(G._띄움(k["정수조각접기"], (n * NH, 1), (256, 1), [u64(조각칸), u64(출력), i64(n), i64(n), i64(0), i64(최대길이)]))
    dr.맞추기()
    q, kk, v = 입력[:, :D], 입력[:, D:2 * D], 입력[:, 2 * D:]
    out = {}
    Dq, Eq = C.자리로(q, 2)
    out["q 자리 다른 칸"] = int((down(자릿값q, (2, n, D), np.int8) != C.낱말차례(Dq.reshape(2, n, D // 32, 32)).reshape(2, n, D).astype(np.int8)).sum())
    out["q 정보 다른 칸"] = int((down(정보q, (D // 32, 정보폭), np.int32)[:, :n] != (((137 + Eq.T) << 23) + 0x400000).astype(np.int32)).sum())
    gk, gke = down(키칸, (NH, 2, 최대길이, 64), np.int8), down(키지수, (NH, 최대길이, 2), np.uint8)
    gv, gve = down(값칸, (NH, 최대길이 // 32, 2, 64, 32), np.int8), down(값지수, (NH, 최대길이, 2), np.uint8)
    dk = dv = dke = dve = 0
    for h in range(NH):
        kc, ke = C.키캐시(kk[:, 64 * h:64 * h + 64], 최대길이)
        vc, ve = C.값캐시(v[:, 64 * h:64 * h + 64], 최대길이)
        dk += int((gk[h] != kc).sum()); dke += int((gke[h] != ke).sum()); dv += int((gv[h] != vc).sum()); dve += int((gve[h] != ve).sum())
    out.update({"키 캐시 다른 바이트": dk, "키 지수 다른 바이트": dke, "값 캐시 다른 바이트": dv, "값 지수 다른 바이트": dve})
    머리들 = list(range(NH)) if 참조머리 is None else list(참조머리)
    t0 = time.time()
    ref = np.zeros((n, D), f32)
    for h in 머리들:
        ref[:, 64 * h:64 * h + 64] = C.어텐션(q[:, 64 * h:64 * h + 64], kk[:, 64 * h:64 * h + 64], v[:, 64 * h:64 * h + 64])
    out["CPU 참조 초"] = round(time.time() - t0, 1)
    Do, Eo = C.자리로(ref, 2)
    ga = down(자릿값, (2, n, D), np.int8)
    rb = C.낱말차례(Do.reshape(2, n, D // 32, 32)).reshape(2, n, D).astype(np.int8)
    cols = np.zeros(D, bool)
    for h in 머리들:
        cols[64 * h:64 * h + 64] = True
    out["프롬프트 어텐션 출력 자리 다른 칸"] = int((ga[:, :, cols] != rb[:, :, cols]).sum())
    gi = down(정보, (D // 32, 정보폭), np.int32)[:, :n]
    bl = np.zeros(D // 32, bool)
    for h in 머리들:
        bl[2 * h:2 * h + 2] = True
    out["프롬프트 어텐션 출력 정보 다른 칸"] = int((gi[bl] != (((137 + Eo.T) << 23) + 0x400000).astype(np.int32)[bl]).sum())
    if 생성판:
        go = down(출력, (n, D), f32)
        out["생성 판 O/L 다른 칸"] = 다른칸(go[:, cols], ref[:, cols])
    out["칸 수"] = int(n * 64 * len(머리들))
    out["오류 칸"] = m.오류칸()
    out["통과"] = all(v == 0 for kk_, v in out.items() if "다른" in kk_) and out["오류 칸"] == 0
    return out


def 긴대조(m, rng, 맥락들, 덩이들, 참조머리=(0, 7), 알림=print):
    """합성 긴 모델의 엔진 m(최대길이 > 1024)의 커널로, 무작위 q · k · v 로 캐시를 위치 0 … C+M−1 까지 채우고(KV정수로) 덩이 M 행(위치 C …)의
    어텐션을 새 판 모두로: (1) 새 판끼리(모든 머리 — 출력 자리 · 정보), (2) 머리 둘의 CPU 참조(정수계약.어텐션 — 두 층)와, 생성 판(정수조각어텐션
    + 정수조각접기 — 행 64 개씩)의 O/L 도, (3) C + M ≤ 1024 면 차례 판(정수어텐션 — 한 층, 묶음 하나라 같아야)과."""
    dr, D, NH, 최대길이 = m.dr, m.D, m.NH, m.최대길이
    cu = dr.cu
    k = m.k

    def zero(nb):
        p = dr.할당(nb)
        dr.확인(cu.cuMemsetD8_v2(u64(p), 0, G.ctypes.c_size_t(nb)))
        return p

    def run(x):
        r = cu.cuLaunchKernel(x.fn, x.grid[0], x.grid[1], 1, x.block[0], x.block[1], 1, 0, None, x.args, None)
        assert r == 0, r
    최대행 = max(맥락들) + max(덩이들)
    입력 = (rng.standard_normal((최대행, 3 * D)) * rng.uniform(0.3, 3.0, (최대행, 1))).astype(f32)
    g입력 = dr.할당(입력.nbytes)
    dr.올리기(g입력, 입력)
    KV = [u64(m.kc[0]), u64(m.vc[0]), u64(m.ke[0]), u64(m.ve[0])]
    덩큰 = 16384
    자q큰, 정q큰 = zero(2 * 덩큰 * D), zero(D // 32 * 덩큰 * 4)

    def kv정수로(a, n, 자q, 정q):
        run(G._띄움(k["KV정수로"], ((3 * D // 32 + 31) // 32, n), (256, 1),
                    [u64(g입력 + a * 3 * D * 4), u64(자q), u64(정q)] + KV + [i64(n), i64(n), i64(a), i64(최대길이)]))
    for a in range(0, 최대행, 덩큰):
        kv정수로(a, min(덩큰, 최대행 - a), 자q큰, 정q큰)
    dr.맞추기()
    M최대 = max(덩이들)
    폭 = (M최대 + 63) // 64 * 64
    자q, 정q = zero(2 * M최대 * D), zero(D // 32 * 폭 * 4)
    출 = {nm: (zero(2 * M최대 * D), zero(D // 32 * 폭 * 4)) for nm in ("묶음64", "묶음16", "두층", "차례")}
    조각칸, 출력 = zero(64 * NH * (최대길이 // 64) * 68 * 4), zero(64 * D * 4)

    def 띄움들(판, C0, M):
        자, 정 = 출[판]
        G묶 = (C0 + M - 1) // 1024 + 1
        접기 = G._띄움(k["정수묶음접기"], (NH, M), (64, 1), [u64(m.묶음칸), u64(정), u64(자), i64(M), i64(M), i64(C0), i64(최대길이)])
        if 판 == "묶음64":
            return [G._띄움(k["정수어텐션묶음"], ((M + 63) // 64 * NH * G묶, 1), (128, 1),
                            [u64(자q), u64(정q)] + KV + [u64(m.묶음칸), i64(M), i64(M), i64(C0), i64(최대길이)]), 접기]
        if 판 == "묶음16":
            return [G._띄움(k["정수어텐션갈래묶음"], ((M + 15) // 16 * NH * G묶, 1), (256, 1),
                            [u64(자q), u64(정q)] + KV + [u64(m.묶음칸), i64(M), i64(M), i64(C0), i64(최대길이)]), 접기]
        if 판 == "두층":
            return [G._띄움(k["정수어텐션두층"], (NH, (M + 63) // 64), (128, 1),
                            [u64(자q), u64(정q)] + KV + [u64(m.묶음칸), u64(정), u64(자), i64(M), i64(M), i64(C0), i64(최대길이)])]
        return [G._띄움(k["정수어텐션"], (NH, (M + 63) // 64), (128, 1),
                        [u64(자q), u64(정q)] + KV + [u64(정), u64(자), i64(M), i64(M), i64(C0), i64(최대길이)])]
    out = {"새 판끼리 (모든 머리)": {}, "CPU 참조 (머리 둘)": {}, "차례 판과 (위치 1024 이하)": {}}
    for C0 in 맥락들:
        for M in 덩이들:
            if C0 + M > 최대길이:
                continue
            kv정수로(C0, M, 자q, 정q)
            판들 = ["묶음64", "묶음16", "두층"] + (["차례"] if C0 + M <= 1024 else [])
            for 판 in 판들:
                dr.확인(cu.cuMemsetD8_v2(u64(출[판][0]), 0x5A, G.ctypes.c_size_t(2 * M최대 * D)))
                dr.확인(cu.cuMemsetD8_v2(u64(출[판][1]), 0x5A, G.ctypes.c_size_t(D // 32 * 폭 * 4)))
                for x in 띄움들(판, C0, M):
                    run(x)
            dr.맞추기()
            정보폭 = (M + 63) // 64 * 64
            o = {판: (dr.내리기(출[판][0], np.empty(2 * M * D, np.int8)).reshape(2, M, D),
                     dr.내리기(출[판][1], np.empty(D // 32 * 정보폭, np.int32)).reshape(D // 32, 정보폭)[:, :M]) for 판 in 판들}
            칸 = f"맥락 {C0} 덩이 {M}"
            out["새 판끼리 (모든 머리)"][칸] = {f"묶음64 대 {판}": [int((o["묶음64"][0] != o[판][0]).sum()), int((o["묶음64"][1] != o[판][1]).sum())]
                                          for 판 in ("묶음16", "두층")}
            if "차례" in o:
                out["차례 판과 (위치 1024 이하)"][칸] = [int((o["묶음64"][0] != o["차례"][0]).sum()), int((o["묶음64"][1] != o["차례"][1]).sum())]
            q_, kk_, v_ = 입력[:C0 + M, :D], 입력[:C0 + M, D:2 * D], 입력[:C0 + M, 2 * D:]
            ref = np.zeros((M, D), f32)
            t0 = time.time()
            for h in 참조머리:
                sl = slice(64 * h, 64 * h + 64)
                ref[:, sl] = C.어텐션(q_[:, sl], kk_[:, sl], v_[:, sl], 첫행=C0)
            초 = round(time.time() - t0, 1)
            Do, Eo = C.자리로(ref, 2)
            rb = C.낱말차례(Do.reshape(2, M, D // 32, 32)).reshape(2, M, D).astype(np.int8)
            ri = ((((137 + Eo.T) << 23) + 0x400000).astype(np.int32))
            cols = np.zeros(D, bool)
            bl = np.zeros(D // 32, bool)
            for h in 참조머리:
                cols[64 * h:64 * h + 64] = True
                bl[2 * h:2 * h + 2] = True
            r = {판: [int((o[판][0][:, :, cols] != rb[:, :, cols]).sum()), int((o[판][1][bl] != ri[bl]).sum())] for 판 in ("묶음64", "묶음16", "두층")}
            go = np.zeros((M, D), f32)
            for a in range(0, M, 64):                     # 생성 판 — 행 64 개씩(그 행들의 q 를 다시 만들어 — 캐시는 같은 값으로 다시 쓴다)
                n = min(64, M - a)
                kv정수로(C0 + a, n, 자q, 정q)
                run(G._띄움(k["정수조각어텐션"], (((C0 + a + n - 1) // 64 + 1 + 7) // 8, n * NH), (256, 1),
                            [u64(자q), u64(정q)] + KV + [u64(조각칸), i64(n), i64(n), i64(C0 + a), i64(최대길이)]))
                run(G._띄움(k["정수조각접기"], (n * NH, 1), (256, 1), [u64(조각칸), u64(출력), i64(n), i64(n), i64(C0 + a), i64(최대길이)]))
                dr.맞추기()
                go[a:a + n] = dr.내리기(출력, np.empty(64 * D, f32)).reshape(64, D)[:n]
            r["생성 판 O/L"] = int((go[:, cols].view(np.int32) != ref[:, cols].view(np.int32)).sum())
            r["CPU 참조 초"] = 초
            out["CPU 참조 (머리 둘)"][칸] = r
            if 알림:
                알림(f"  긴 문맥 {칸}: 판끼리 {out['새 판끼리 (모든 머리)'][칸]} · CPU 참조 {r}")
    out["오류 칸"] = m.오류칸()
    out["통과"] = (all(x == 0 for v in out["새 판끼리 (모든 머리)"].values() for p in v.values() for x in p) and
                 all(x == 0 for v in out["차례 판과 (위치 1024 이하)"].values() for x in v) and
                 all((x == 0 if not isinstance(x, list) else all(y == 0 for y in x))
                     for v in out["CPU 참조 (머리 둘)"].values() for kk, x in v.items() if kk != "CPU 참조 초") and out["오류 칸"] == 0)
    return out
