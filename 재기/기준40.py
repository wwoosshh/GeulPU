#!/usr/bin/env python3
"""40g 기준 자체의 기울기 — Qwen2.5-0.5B 에서 계약(G)의 반올림이 위험한 걸음을 fp64 참값 대비 기울이는가 (문서/40단계.md '40g').

  python -I -X utf8 재기/기준40.py 로짓 --작업 W --모델폴더 M --ptx <qwen2Q8.ptx>   # GPU: 7B G 답을 0.5B 계약 엔진에 넣어 걸음마다 상위 20
  python -I -X utf8 재기/기준40.py 위험 --작업 W --모델폴더 M                      # 위험한 걸음 — 증상40.위험한걸음들_빠르게 그대로
  python -I -X utf8 재기/기준40.py 참값 --작업 W --모델폴더 M [--확인 20]           # CPU fp64: 위험한 걸음의 행에서 ln p_64 (앞 N 문항은 모든 걸음 확인)
  python -I -X utf8 재기/기준40.py 셈 --작업 W --모델폴더 M [--결과 문서/결과/40단계]  # Δ_G · 붓스트랩 · Holm · 판정

원자료는 W/기준/ 에: G05b_7b.jsonl(상위 20), 위험_05b.jsonl, 참값_05b.jsonl.
"""
import argparse
import json
import os
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, ".."))
sys.path.insert(0, HERE)
import 증상40 as Z      # noqa: E402
import 셈40 as S        # noqa: E402
import 모음40 as MO     # noqa: E402

한국어묶음 = ("자연_LCB", "자연_긴글", "방아쇠_글자", "방아쇠_언어", "방아쇠_되풀이")
상위 = 20
행묶음 = 512


def 기록(*a):
    print(time.strftime("%H:%M:%S"), *a, flush=True)


def 폴더(a):
    p = os.path.join(a.작업, "기준")
    os.makedirs(p, exist_ok=True)
    return p


def 상위20(L):
    """float32 로짓 [m][V] → (상위 번호 [m][20], float64 log-softmax 값 [m][20]) — 서버와 같이 float64 로."""
    X = L.astype(np.float64)
    mx = X.max(1, keepdims=True)
    lp = X - (mx + np.log(np.exp(X - mx).sum(1, keepdims=True)))
    idx = np.argpartition(-lp, 상위, axis=1)[:, :상위]
    val = np.take_along_axis(lp, idx, 1)
    차례 = np.argsort(-val, axis=1)
    return np.take_along_axis(idx, 차례, 1), np.take_along_axis(val, 차례, 1)


# ---------------------------------------------------------------- 로짓 (GPU, 계약 엔진)
def 명령_로짓(a):
    sys.path.insert(0, os.path.join(ROOT, "엔진"))
    import 글qwen2 as GQ
    gguf = os.path.join(a.모델폴더, MO.GGUF["05b"])
    m = GQ.글Qwen2(gguf, 최대행=행묶음, 최대문장=1, 최대길이=4096, 로짓행=행묶음, ptx경로=a.ptx)
    토 = {r["id"]: r for r in MO.jsonl읽기(os.path.join(a.작업, "토큰", "7b.jsonl"))}
    G = S.색인(os.path.join(a.작업, "생성", "G_7b.jsonl"))
    out = os.path.join(폴더(a), "G05b_7b.jsonl")
    n문항 = n걸음 = 같음 = 0
    확인됨 = None
    with open(out, "w", encoding="utf-8", newline="\n") as f:
        for k in sorted(G.keys()):
            g = G[k]
            if g["묶음"] not in 한국어묶음:
                continue
            ids, toks = 토[k]["ids"], g["tokens"]
            seq = ids + toks
            p, n = len(ids), len(toks)
            total = p - 1 + n                       # 행 r 의 로짓은 토큰 r + 1 을 고른다 — 답의 걸음 t 는 행 p − 1 + t
            assert total <= 4096, k
            번호, 값 = [], []
            for s in range(0, total, 행묶음):
                chunk = seq[s:min(s + 행묶음, total)]
                m.토큰넣기(chunk)
                m.계산(1, len(chunk), s, "전부")
                L = m.로짓(len(chunk))
                lo = max(p - 1, s)
                if lo < s + len(chunk):
                    i, v = 상위20(L[lo - s:])
                    번호.extend(i.tolist())
                    값.extend(v.tolist())
                if 확인됨 is None and s == 0 and p <= 행묶음:
                    # 확인: 생성 길의 첫 걸음 로짓(프롬프트의 마지막 행)이 한 번에 길과 비트까지 같다(계약)
                    첫행 = L[p - 1].copy()
                    _, logs = m.생성로짓(ids, 1)
                    확인됨 = bool(np.array_equal(첫행, logs[0]))
                    기록(f"확인 — 생성 길과 한 번에 길의 첫 걸음 로짓 같음: {확인됨} ({k})")
                    m.토큰넣기(chunk)                 # 생성로짓이 캐시를 덮었으니 다시 넣는다
                    m.계산(1, len(chunk), s, "전부")
            assert len(번호) == n, (k, len(번호), n)
            같음 += sum(int(번호[t][0] == toks[t]) for t in range(n))
            n걸음 += n
            n문항 += 1
            f.write(json.dumps({"id": k, "묶음": g["묶음"], "prompt_n": p, "tokens": toks, "top_ids": 번호, "top_lp": 값}, ensure_ascii=False) + "\n")
            if n문항 % 100 == 0:
                기록(f"로짓 {n문항} 문항 · {n걸음} 걸음 · 0.5B 의 1위 = 7B 의 토큰 {같음 / n걸음:.1%}")
    기록(f"로짓 끝 — {n문항} 문항 · {n걸음} 걸음 · 0.5B 의 1위 = 7B 의 토큰 {같음 / max(n걸음, 1):.1%} · 확인 {확인됨}")
    json.dump({"문항": n문항, "걸음": n걸음, "1위같음": 같음, "생성길확인": 확인됨},
              open(os.path.join(폴더(a), "로짓_요약.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)


# ---------------------------------------------------------------- 위험한 걸음
def 명령_위험(a):
    표, 특수, 계통 = S.모델표(None, a.모델폴더, "7b")        # 0.5B 와 같은 어휘
    out = os.path.join(폴더(a), "위험_05b.jsonl")
    수 = {"O": 0, "R": 0, "C": 0}
    n걸음 = 0
    with open(out, "w", encoding="utf-8", newline="\n") as f:
        for r in MO.jsonl읽기(os.path.join(폴더(a), "G05b_7b.jsonl")):
            st = Z.위험한걸음들_빠르게(r["tokens"], r["top_ids"], r["top_lp"], 표, 계통, 특수)
            for s in st:
                수[s[1]] += 1
            n걸음 += len(r["tokens"])
            f.write(json.dumps({"id": r["id"], "묶음": r["묶음"], "prompt_n": r["prompt_n"], "n": len(r["tokens"]), "걸음": st}, ensure_ascii=False) + "\n")
    기록(f"위험 05b: 걸음 {n걸음} · O {수['O']} · R {수['R']} · C {수['C']}")


# ---------------------------------------------------------------- 참값 (CPU fp64)
class 참값모델:
    """시험/참값.py qwen2_로짓과 같은 계산을 NumPy fp64 로 — 행 전부 또는 고른 행의 로짓."""

    def __init__(self, gguf):
        sys.path.insert(0, os.path.join(ROOT, "시험"))
        import 참값
        W, 설정 = 참값.qwen2_gguf(gguf)
        self.W = {}
        for k, v in W.items():
            if k == "head" and v is W["embed"]:
                self.W[k] = self.W["embed"]
            else:
                self.W[k] = np.ascontiguousarray(v, dtype=np.float64)
        self.설정 = 설정
        self.NH, self.NKV, self.NL = 설정["머리"], 설정["KV머리"], 설정["층"]
        self.D = self.W["embed"].shape[1]
        self.hd = self.D // self.NH
        self.eps = 설정["eps"]
        inv = 1.0 / (설정["theta"] ** (np.arange(0, self.hd, 2, dtype=np.float64) / self.hd))
        self.inv = inv

    def 숨은(self, ids):
        """마지막 정규화까지 한 숨은 상태 [n][D] (fp64)."""
        W, NH, NKV, hd = self.W, self.NH, self.NKV, self.hd
        ids = np.asarray(ids)
        n = len(ids)
        x = W["embed"][ids]
        ang = np.arange(n, dtype=np.float64)[:, None] * self.inv[None, :]
        cos = np.concatenate([np.cos(ang), np.cos(ang)], 1)
        sin = np.concatenate([np.sin(ang), np.sin(ang)], 1)
        mask = np.triu(np.full((n, n), -np.inf), 1)

        def rms(v, g):
            return v / np.sqrt((v * v).mean(-1, keepdims=True) + self.eps) * g

        def rope(t):                                   # [머리][n][hd]
            t1, t2 = t[..., :hd // 2], t[..., hd // 2:]
            return t * cos + np.concatenate([-t2, t1], -1) * sin
        scale = 1.0 / np.sqrt(hd)
        rep = NH // NKV
        for l in range(self.NL):
            h = rms(x, W[f"{l}.n1"])
            q = h @ W[f"{l}.wq"].T + W[f"{l}.bq"]
            k = h @ W[f"{l}.wk"].T + W[f"{l}.bk"]
            v = h @ W[f"{l}.wv"].T + W[f"{l}.bv"]
            q = rope(q.reshape(n, NH, hd).transpose(1, 0, 2))
            k = rope(k.reshape(n, NKV, hd).transpose(1, 0, 2))
            v = v.reshape(n, NKV, hd).transpose(1, 0, 2)
            y = np.empty((NH, n, hd))
            for hh in range(NH):
                kk, vv = k[hh // rep], v[hh // rep]
                s = q[hh] @ kk.T * scale + mask
                s -= s.max(1, keepdims=True)
                e = np.exp(s)
                y[hh] = (e / e.sum(1, keepdims=True)) @ vv
            x = x + y.transpose(1, 0, 2).reshape(n, self.D) @ W[f"{l}.wo"].T
            h = rms(x, W[f"{l}.n2"])
            g_, u = h @ W[f"{l}.wg"].T, h @ W[f"{l}.wu"].T
            x = x + (g_ / (1.0 + np.exp(-g_)) * u) @ W[f"{l}.wd"].T
        return rms(x, W["norm"])

    def 로짓(self, 숨은, rows):
        return 숨은[np.asarray(rows)] @ self.W["head"].T


def lsm(X):
    mx = X.max(-1, keepdims=True)
    return X - (mx + np.log(np.exp(X - mx).sum(-1, keepdims=True)))


def 명령_참값(a):
    gguf = os.path.join(a.모델폴더, MO.GGUF["05b"])
    t0 = time.time()
    M = 참값모델(gguf)
    기록(f"fp64 가중치 올림 {time.time() - t0:.0f} 초")
    토 = {r["id"]: r for r in MO.jsonl읽기(os.path.join(a.작업, "토큰", "7b.jsonl"))}
    G = {r["id"]: r for r in MO.jsonl읽기(os.path.join(폴더(a), "G05b_7b.jsonl"))}
    위험 = {r["id"]: r for r in MO.jsonl읽기(os.path.join(폴더(a), "위험_05b.jsonl"))}
    out = os.path.join(폴더(a), "참값_05b.jsonl")
    확인 = {"문항": 0, "걸음": 0, "1위같음": 0}
    n문항 = n걸음 = 0
    t0 = time.time()
    with open(out, "w", encoding="utf-8", newline="\n") as f:
        for i, k in enumerate(sorted(G.keys())):
            g, r = G[k], 위험[k]
            p = g["prompt_n"]
            if not r["걸음"] and i >= a.확인:
                continue
            seq = 토[k]["ids"] + g["tokens"]
            H = M.숨은(seq[:p - 1 + len(g["tokens"])])
            rec = {"id": k, "걸음": []}
            if i < a.확인:                              # 모든 걸음에서 fp64 의 1위 = G-0.5B 의 1위?
                rows = np.arange(p - 1, p - 1 + len(g["tokens"]))
                같 = 0
                for s in range(0, len(rows), 256):
                    am = M.로짓(H, rows[s:s + 256]).argmax(1)
                    같 += sum(int(am[j] == g["top_ids"][s + j][0]) for j in range(len(am)))
                확인["문항"] += 1
                확인["걸음"] += len(rows)
                확인["1위같음"] += 같
                rec["확인"] = {"걸음": int(len(rows)), "1위같음": int(같)}
            if r["걸음"]:
                rows = sorted({p - 1 + s[0] for s in r["걸음"]})
                lp = lsm(M.로짓(H, rows))
                자리 = {row: j for j, row in enumerate(rows)}
                for s in r["걸음"]:
                    t, 유형, aa, b, m_, bc, lpGb, lpGbc = s
                    row = lp[자리[p - 1 + t]]
                    rec["걸음"].append([t, 유형, aa, b, bc, float(row[aa]), float(row[b]), float(row[bc]) if bc is not None else None,
                                      int(row.argmax())])
                n걸음 += len(r["걸음"])
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
            n문항 += 1
            if n문항 % 50 == 0:
                기록(f"참값 {n문항} 문항 · 위험한 걸음 {n걸음} · {time.time() - t0:.0f} 초" +
                   (f" · 확인 1위 같음 {확인['1위같음'] / 확인['걸음']:.2%}" if 확인["걸음"] else ""))
    확인["비율"] = 확인["1위같음"] / 확인["걸음"] if 확인["걸음"] else None
    json.dump(확인, open(os.path.join(폴더(a), "참값_확인.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    기록(f"참값 끝 — {n문항} 문항 · 위험한 걸음 {n걸음} · {time.time() - t0:.0f} 초 · 확인 {확인}")


# ---------------------------------------------------------------- 셈
def 명령_셈(a):
    G = {r["id"]: r for r in MO.jsonl읽기(os.path.join(폴더(a), "G05b_7b.jsonl"))}
    위험 = {r["id"]: r for r in MO.jsonl읽기(os.path.join(폴더(a), "위험_05b.jsonl"))}
    참 = {r["id"]: r for r in MO.jsonl읽기(os.path.join(폴더(a), "참값_05b.jsonl"))}
    문항 = {(갈, 유형): {} for 갈 in ("G", "G대조") for 유형 in "ORC"}
    다름 = {유형: [0, 0] for 유형 in "ORC"}
    n토큰 = sum(r["n"] for r in 위험.values())
    for k, r in 위험.items():
        if k not in 참:
            continue
        g = G[k]
        참걸음 = {(s[0], s[1]): s for s in 참[k]["걸음"]}
        for s in r["걸음"]:
            t, 유형, aa, b, m_, bc, lpGb, lpGbc = s
            z = 참걸음[(t, 유형)]
            lp64a, lp64b, lp64bc, am = z[5], z[6], z[7], z[8]
            lpGa = g["top_lp"][t][0]
            d = (lpGb - lpGa) - (lp64b - lp64a)
            e = 문항[("G", 유형)].setdefault(k, [0.0, 0])
            e[0] += d
            e[1] += 1
            다름[유형][0] += 1
            다름[유형][1] += int(am != aa)
            if bc is not None and lp64bc is not None:
                dc = (lpGbc - lpGa) - (lp64bc - lp64a)
                e = 문항[("G대조", 유형)].setdefault(k, [0.0, 0])
                e[0] += dc
                e[1] += 1
    결 = {"정의": "문서/40단계.md '40g' — Δ_G = [ln p_G(b) − ln p_G(a)] − [ln p_64(b) − ln p_64(a)], Qwen2.5-0.5B Q8_0, 7B G 답 접두",
         "토큰": n토큰, "문항": len(위험)}
    ps = []
    for 유형 in "ORC":
        d = 문항[("G", 유형)]
        합, 수 = [x[0] for x in d.values()], [x[1] for x in d.values()]
        평균, 구간, p = Z.묶음붓스트랩(합, 수)
        결[f"G_{유형}"] = {"평균": 평균, "구간": 구간, "p": p, "걸음": int(sum(수)), "문항": len(수),
                         "밀도(천 토큰마다)": sum(수) / n토큰 * 1000 if n토큰 else None,
                         "fp64의 1위가 a 와 다른 걸음": 다름[유형][1]}
        ps.append(p if p is not None else 1.0)
        d = 문항[("G대조", 유형)]
        합, 수 = [x[0] for x in d.values()], [x[1] for x in d.values()]
        평균c, 구간c, pc = Z.묶음붓스트랩(합, 수) if 수 else (None, None, None)
        결[f"G대조_{유형}"] = {"평균": 평균c, "구간": 구간c, "p": pc, "걸음": int(sum(수))}
    고친 = Z.Holm(ps)
    for 유형, gp in zip("ORC", 고친):
        e = 결[f"G_{유형}"]
        e["고친p"] = gp
        e["판정"] = Z.기울기판정(e["평균"], e["구간"], gp, e["걸음"])
    for 이름 in ("로짓_요약.json", "참값_확인.json"):
        p = os.path.join(폴더(a), 이름)
        if os.path.exists(p):
            결[이름[:-5]] = json.load(open(p, encoding="utf-8"))
    out = os.path.join(a.결과, "40g_기준기울기.json")
    json.dump(결, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps(결, ensure_ascii=False, indent=1))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("명령", choices=("로짓", "위험", "참값", "셈"))
    ap.add_argument("--작업", required=True)
    ap.add_argument("--모델폴더", required=True)
    ap.add_argument("--ptx")
    ap.add_argument("--확인", type=int, default=20)
    ap.add_argument("--결과", default=os.path.join(ROOT, "문서", "결과", "40단계"))
    a = ap.parse_args()
    {"로짓": 명령_로짓, "위험": 명령_위험, "참값": 명령_참값, "셈": 명령_셈}[a.명령](a)


if __name__ == "__main__":
    main()
