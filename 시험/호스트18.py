#!/usr/bin/env python3
"""18단계 시험의 파이썬 쪽(정답지) — 파이썬 호스트(엔진/글qwen2.py)가 GPU 에 올린 것 · 낸 결과를 글 호스트(호스트/*.gl)와 같은 꼴로 적는다.
견주는 도구일 뿐 — 글 실행기가 도는 데에는 들지 않는다(문서/18단계.md 밝혀 둘 것 3).

  python 시험/호스트18.py 준비            18b — 올린 버퍼마다 SHA-256 (장치에서 내려받아)
"""
import hashlib
import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import numpy as np                 # noqa: E402

import qwen2공통 as Q              # noqa: E402


def 장치해시(m, 주소, 길이):
    h = hashlib.sha256()
    덩이 = 64 << 20
    o = 0
    while o < 길이:
        n = min(덩이, 길이 - o)
        h.update(m.dr.내리기(주소 + o, np.empty(n, np.uint8)).tobytes())
        o += n
    return h.hexdigest()


def 준비(최대길이=16384):
    m = Q.엔진(최대행=64, 최대길이=최대길이, 로짓행=1)
    NL, D, QKV = m.NL, m.D, m.QKV
    한층 = lambda 이름: m.층[1][이름][0] - m.층[0][이름][0]
    for 이름 in ("qkv", "o", "gu", "down"):
        print(이름, 장치해시(m, m.층[0][이름][0], NL * 한층(이름)))
    print("qkv치우침", 장치해시(m, m.층[0]["qkv치우침"], NL * QKV * 4))
    print("n1", 장치해시(m, m.층[0]["n1"], NL * D * 4))
    print("n2", 장치해시(m, m.층[0]["n2"], NL * D * 4))
    V = m.V
    낱말 = D * V + D // 32 * ((V + 63) // 64 * 64) * 2
    print("낱말", 장치해시(m, m.낱말[0], 낱말))
    print("머리", 장치해시(m, m.머리[0], 낱말))
    print("출력정규", 장치해시(m, m.norm, D * 4))
    print("코사인", 장치해시(m, m.코사인, 최대길이 * 32 * 4))
    print("사인", 장치해시(m, m.사인, 최대길이 * 32 * 4))
    m.닫기()


def 시험글들():
    """18c 의 글들 — 시험 질문의 채팅 틀, 평가글, 유니코드 시험글(통째 · 줄마다), 실행기의 둘째 차례 덩이 꼴."""
    import 토크나이저 as TK
    out = [TK.채팅틀([{"role": "user", "content": q}]) for q in Q.질문들]
    out.append(open(os.path.join(HERE, "평가글.txt"), "rb").read().decode("utf-8"))
    시험 = open(os.path.join(HERE, "토크나이저시험글.txt"), "rb").read().decode("utf-8")
    out.append(시험)
    out += 시험.split("\n")
    for q in Q.질문들:
        out.append(f"\n<|im_start|>user\n{q}<|im_end|>\n<|im_start|>assistant\n")
        out.append(f"<|im_end|>\n<|im_start|>user\n{q}<|im_end|>\n<|im_start|>assistant\n")
    return out


def 토크나이저(입력, 출력):
    """18c — 글들을 입력 파일(글 쪽이 읽는 꼴)로 쓰고, 파이썬 토크나이저의 결과를 출력에(글 쪽과 같은 꼴)."""
    import 토크나이저 as TK
    tk = TK.Qwen토크나이저(gguf=Q.GGUF)
    글들 = 시험글들()
    with open(입력, "wb") as f:
        for t in 글들:
            b = t.encode("utf-8")
            f.write(len(b).to_bytes(8, "little") + b)
    줄 = []
    for t in 글들:
        ids = tk.나누기(t)
        줄.append("T" + "".join(f" {i}" for i in ids))
        줄.append("D " + tk.잇기(ids).encode("utf-8").hex())
        for k in range(1, min(len(ids), 48) + 1):
            줄.append(f"P {k} " + tk.잇기(ids[:k]).encode("utf-8").hex())
    open(출력, "w", encoding="utf-8", newline="\n").write("\n".join(줄) + "\n")
    print(f"글 {len(글들)} 개, 토큰 {sum(len(tk.나누기(t)) for t in 글들)} 개")


def 엔진경우들(tk):
    """18d 의 경우 — 15단계 시험(시험/메가15.py)과 같다: 채팅 질문 셋의 채팅 틀, 문장 1 을 되풀이한 문맥 1024 · 2100 · 8192, 걸음 64."""
    import 공통 as T
    import 토크나이저 as TK
    out = [tk.나누기(TK.채팅틀([{"role": "user", "content": q}])) for q in Q.질문들]
    for n in (1024, 2100, 8192):
        out.append((tk.나누기(T.문장들[1]) * 400)[:n])
    return out


def 엔진(입력, 출력, 최대행=2048, 최대길이=16384, 로짓행=64, 걸음=64, 최대생성=64):
    """18d — 경우마다 걸음마다의 로짓 · 토큰 · 생성 뒤의 KV 캐시(버퍼 전체)의 SHA-256, 그리고 실행기의 세 차례 대화(실행.py 의 대화)."""
    import 토크나이저 as TK
    import qwen2 as S
    sys.path.insert(0, Q.ROOT)
    import 실행
    tk = TK.Qwen토크나이저(gguf=Q.GGUF)
    경우들 = 엔진경우들(tk)
    with open(입력, "wb") as f:
        w = lambda v: f.write(int(v).to_bytes(8, "little", signed=True))
        w(최대행), w(최대길이), w(로짓행), w(len(경우들))
        for ids in 경우들:
            w(len(ids)), w(걸음)
            for t in ids:
                w(t)
        w(len(Q.질문들))
        for q in Q.질문들:
            b = q.encode("utf-8")
            w(len(b))
            f.write(b)
        w(최대생성)
    m = Q.엔진(최대행=최대행, 최대길이=최대길이, 로짓행=로짓행)
    NL = m.NL
    kv, ek = m.kc[1] - m.kc[0], m.ke[1] - m.ke[0]

    def 캐시():
        return (f" kc {장치해시(m, m.kc바탕, NL * kv)} vc {장치해시(m, m.vc바탕, NL * kv)} ke {장치해시(m, m.ke바탕, NL * ek)}"
                f" ve {장치해시(m, m.ve바탕, NL * ek)}")
    줄 = []
    for i, ids in enumerate(경우들):
        S.캐시비우기(m)
        toks, 로짓 = m.생성로짓(ids, 걸음)
        줄.append(f"경우 {i} 토큰" + "".join(f" {t}" for t in toks))
        줄.append(f"경우 {i} 로짓 {hashlib.sha256(np.ascontiguousarray(로짓, np.float32).tobytes()).hexdigest()}")
        줄.append(f"경우 {i} 캐시" + 캐시())
        print(f"경우 {i}: 프롬프트 {len(ids)} · 걸음 {걸음}", flush=True)
    d = 실행.대화(m, tk, 최대생성=최대생성)
    d.비우기()
    S.캐시비우기(m)
    for j, q in enumerate(Q.질문들):
        답 = d.묻기(q)[0]
        줄.append(f"대화 {j} 답" + "".join(f" {t}" for t in 답))
        줄.append(f"대화 {j} 글 " + tk.잇기(답).encode("utf-8").hex())
    줄.append(f"대화 위치 {d.위치} 토큰" + "".join(f" {t}" for t in d.토큰))
    줄.append("대화 캐시" + 캐시())
    줄.append(f"오류칸 {m.오류칸()}")
    open(출력, "w", encoding="utf-8", newline="\n").write("\n".join(줄) + "\n")
    m.닫기()


def 재기입력(입력):
    """18e 의 입력 — 재기15 와 같은 토큰열: 채팅 질문(셋째)의 채팅 틀, 문장 1 의 되풀이 8192."""
    import 공통 as T
    tk = Q.토크나이저()
    긴 = (tk.나누기(T.문장들[1]) * 400)[:8192]
    채팅 = Q.채팅(tk, Q.질문들[2])
    with open(입력, "wb") as f:
        for ids in (채팅, 긴):
            f.write(len(ids).to_bytes(8, "little"))
            for t in ids:
                f.write(int(t).to_bytes(8, "little", signed=True))


def 재기(입력, 출력):
    """18e 의 파이썬 쪽 — 재기_엔진.gl 과 같은 방법(재기15 의 '글 메가커널' 칸): 데우기 한 번, 일곱 번의 중앙값 세 묶음."""
    import time
    import 글qwen2
    raw = open(입력, "rb").read()
    o = 0
    seqs = []
    for _ in range(2):
        n = int.from_bytes(raw[o:o + 8], "little")
        o += 8
        seqs.append([int.from_bytes(raw[o + 8 * i:o + 8 * i + 8], "little", signed=True) for i in range(n)])
        o += 8 * n
    채팅, 긴 = seqs
    t0 = time.perf_counter()
    m = 글qwen2.글Qwen2(Q.GGUF, 최대행=8192, 최대길이=16384, 로짓행=64)
    m.판미리고르기()
    올림 = (time.perf_counter() - t0) * 1000

    def 잰(ids, n):
        m.dr.맞추기()
        s = time.perf_counter()
        m.생성(ids, n)
        m.dr.맞추기()
        return (time.perf_counter() - s) * 1000

    def 세묶음(ids, n):
        return float(np.median([np.median([잰(ids, n) for _ in range(7)]) for _ in range(3)]))
    줄 = [f"올림 {올림:.1f}"]
    for 이름, ids in (("채팅 질문", 채팅), ("문맥 1024", 긴[:1024]), ("문맥 8192", 긴[:8192])):
        잰(ids, 65)
        t1, t65 = 세묶음(ids, 1), 세묶음(ids, 65)
        줄.append(f"생성 {이름} {(t65 - t1) / 64:.4f}")
        print(줄[-1], flush=True)
    for n in (128, 2048, 8192):
        잰(긴[:n], 1)
        줄.append(f"프롬프트 {n} {세묶음(긴[:n], 1):.4f}")
        print(줄[-1], flush=True)
    줄.append(f"오류칸 {m.오류칸()}")
    open(출력, "w", encoding="utf-8", newline="\n").write("\n".join(줄) + "\n")
    m.닫기()


def 재기모음(폴더, 출력):
    """18e — 프로세스마다의 결과(파이썬1~3.txt · 글1~3.txt)에서 칸마다 세 프로세스의 중앙값, 글 / 파이썬 비, 판정(1.02 배 이하)."""
    import json

    def 읽기(p):
        d = {}
        for l in open(p, encoding="utf-8"):
            k, v = l.rsplit(" ", 1)
            d[k] = float(v)
        return d
    P = [읽기(os.path.join(폴더, f"파이썬{r}.txt")) for r in (1, 2, 3)]
    G = [읽기(os.path.join(폴더, f"글{r}.txt")) for r in (1, 2, 3)]
    칸들 = ["생성 채팅 질문", "생성 문맥 1024", "생성 문맥 8192", "프롬프트 128", "프롬프트 2048", "프롬프트 8192"]
    res = {"칸": {}, "올림 ms": {"파이썬": [p["올림"] for p in P], "글": [g["올림"] for g in G]},
           "오류칸": {"파이썬": [p["오류칸"] for p in P], "글": [g["오류칸"] for g in G]}}
    통과 = True
    for k in 칸들:
        p, g = [x[k] for x in P], [x[k] for x in G]
        mp, mg = float(np.median(p)), float(np.median(g))
        비 = mg / mp
        통과 &= 비 <= 1.02
        res["칸"][k] = {"파이썬 (프로세스 셋)": p, "글 (프로세스 셋)": g, "파이썬 중앙값": round(mp, 4), "글 중앙값": round(mg, 4), "비 (글 / 파이썬)": round(비, 4)}
        print(f"{k}: 파이썬 {mp:.4f} · 글 {mg:.4f} — 비 {비:.4f}")
    res["18e"] = "통과" if 통과 else "기준 미달"
    print("18e:", res["18e"])
    json.dump(res, open(출력, "w", encoding="utf-8"), ensure_ascii=False, indent=1)


def PTX경로():
    sys.path.insert(0, os.path.join(Q.ROOT, "엔진"))
    import 커널모듈
    print(커널모듈.ptx("qwen2Q8.gl"))


if __name__ == "__main__":
    {"준비": 준비, "토크나이저": 토크나이저, "엔진": 엔진, "PTX경로": PTX경로, "재기입력": 재기입력, "재기": 재기, "재기모음": 재기모음}[sys.argv[1]](*sys.argv[2:])
