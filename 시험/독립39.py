#!/usr/bin/env python3
"""39a (6) — 독립 대조(계약 밖의 기준): 글(geul) 엔진의 모든 행 로짓을 llama.cpp(측정 날 최신 공식 판 · 같은 GGUF · 기본 설정)의 로짓과
견준다. CPU 참조와 엔진은 같은 사람이 짓는다 — q · k 줄 되돌리기나 RoPE 늘이기 인자를 둘이 함께 잘못 읽으면 39a (2) 는 같다고 나온다.
llama.cpp 는 따로 지은 구현이라 그런 잘못이 있으면 여기서 크게 벌어진다(문서/39단계.md).

  python -I 시험/독립39.py 입력 <gguf> <llama-b 폴더> <작업폴더> [<글1> <글2>]
      글 둘(기본: 빌드/wikitext-2-풀기/wiki.test.raw 의 앞 · 연구자안내.md)을 llama.cpp 의 llama_tokenize(BOS 는 모델대로 · 특수 토큰은
      풀지 않음 — llama-perplexity 와 같다)로 나눠 앞 2,048 토큰씩 → 작업폴더/토큰.json, 작업폴더/입력.bin(호스트/시험_7B.gl 의 입력 —
      최대길이 2048 · 로짓행 1024(엔진의 최대행) · 글마다 경우 둘: (프롬프트 1024, 걸음 1, 잡기시작 0) → 행 0 … 1023 이 경우{2k}_로짓.bin,
      (프롬프트 2048, 걸음 1, 잡기시작 1024) → 행 1024 … 2047 이 경우{2k+1}_뒤로짓.bin — 앞 행은 모두 같은 앞 토큰을 본다).
  python -I 시험/독립39.py 라마 <gguf> <llama-b 폴더> <작업폴더>
      llama.cpp C API(재기/라마.py): n_ctx 2048 · n_batch 2048 · n_ubatch 512 · 플래시 어텐션 자동 · KV F16 · 모든 층 GPU(llama-cli ·
      llama-server 의 기본 배치와 같다). 경우마다 캐시를 비우고 한 llama_decode 로 모든 행의 로짓 → 작업폴더/라마{i}.npy
  python -I 시험/독립39.py 견주기 <작업폴더> <시험_7B 출력폴더> <결과.json>
      행마다(실수 64 비트): KL(llama.cpp ‖ 글) = Σ p_라마 (log p_라마 − log p_글), 1위 토큰이 같은가. 판정(사전 등록): 경우마다
      1위 같음 ≥ 98 % · 평균 KL ≤ 1e-2.
"""
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, ".."))
길이 = 2048


def _어휘(판폴더, gguf):
    sys.path.insert(0, HERE)
    import 토크나이저39 as T39            # noqa: E402 — 어휘만 올린 llama.cpp(vocab_only)
    return T39.라마어휘(판폴더, gguf)


def 입력(gguf, 판폴더, 작업, 글들):
    import ctypes
    os.makedirs(작업, exist_ok=True)
    어휘 = _어휘(판폴더, gguf)
    L = 어휘.L
    L.llama_tokenize.restype = ctypes.c_int32
    L.llama_tokenize.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_int32, ctypes.POINTER(ctypes.c_int32), ctypes.c_int32,
                                 ctypes.c_bool, ctypes.c_bool]
    토큰들 = []
    for p in 글들:
        b = open(p, "rb").read()[:200000]
        buf = (ctypes.c_int32 * (len(b) + 16))()
        n = L.llama_tokenize(어휘.vocab, b, len(b), buf, len(b) + 16, True, False)
        assert n >= 길이, (p, n)
        토큰들.append([int(x) for x in buf[:길이]])
    with open(os.path.join(작업, "토큰.json"), "w", encoding="utf-8") as f:
        json.dump({"gguf": os.path.basename(gguf), "글": [os.path.relpath(p, ROOT) if p.startswith(ROOT) else os.path.basename(p) for p in 글들],
                   "토큰": 토큰들}, f)
    반 = 길이 // 2
    with open(os.path.join(작업, "입력.bin"), "wb") as f:
        w = lambda v: f.write(int(v).to_bytes(8, "little", signed=True))
        w(길이), w(반), w(2 * len(토큰들))
        for ids in 토큰들:
            for p, 잡기 in ((반, 0), (길이, 반)):
                w(p), w(1), w(잡기)
                for t in ids[:p]:
                    w(t)
    print("입력: 경우", len(토큰들), "· 토큰", 길이, "씩 · 첫 토큰", [t[:4] for t in 토큰들])


def 라마(gguf, 판폴더, 작업):
    os.environ["GEULPU_LLAMA"] = 판폴더
    sys.path.insert(0, os.path.join(ROOT, "재기"))
    import 라마 as LM                     # noqa: E402
    토큰들 = json.load(open(os.path.join(작업, "토큰.json"), encoding="utf-8"))["토큰"]
    lm = LM.라마(gguf, n_ctx=길이, n_batch=길이, n_ubatch=512, n_seq_max=1, flash=-1, kv형식=1)
    print("llama.cpp 문맥:", " | ".join(l.strip() for l in lm.문맥로그.splitlines() if any(x in l for x in ("flash", "Flash", "n_ctx", "n_ubatch", "CUDA"))))
    for i, ids in enumerate(토큰들):
        lm.지우기()
        lm.넣기(ids, list(range(len(ids))), [0] * len(ids), [1] * len(ids))
        x = lm.모든로짓(len(ids))
        np.save(os.path.join(작업, f"라마{i}.npy"), x)
        print("라마", i, x.shape, "1위(앞 8 행)", x[:8].argmax(1).tolist())
    lm.닫기()


def _로그소프트맥스(x):
    x = x.astype(np.float64)
    m = x.max(1, keepdims=True)
    return x - m - np.log(np.exp(x - m).sum(1, keepdims=True))


def 견주기(작업, 글폴더, 출력):
    토큰들 = json.load(open(os.path.join(작업, "토큰.json"), encoding="utf-8"))
    결과 = {"gguf": 토큰들["gguf"], "글": 토큰들["글"], "경우": []}
    통과 = True
    for i, ids in enumerate(토큰들["토큰"]):
        S = np.fromfile(os.path.join(글폴더, f"경우{2 * i}_토큰.bin"), dtype=np.int64)
        assert S.tolist() == ids[:len(S)], f"글 {i}: 글 도구의 토큰열이 입력과 다르다"
        라 = np.load(os.path.join(작업, f"라마{i}.npy"), mmap_mode="r")
        V = 라.shape[1]
        앞 = np.fromfile(os.path.join(글폴더, f"경우{2 * i}_로짓.bin"), dtype=np.float32).reshape(-1, V)
        뒤 = np.fromfile(os.path.join(글폴더, f"경우{2 * i + 1}_뒤로짓.bin"), dtype=np.float32).reshape(-1, V)
        글 = np.concatenate([앞, 뒤], 0)
        assert 글.shape == 라.shape, (글.shape, 라.shape)
        kl = np.zeros(len(ids))
        같음 = np.zeros(len(ids), bool)
        for a in range(0, len(ids), 128):
            b = min(len(ids), a + 128)
            lp, lg = _로그소프트맥스(np.asarray(라[a:b])), _로그소프트맥스(np.asarray(글[a:b]))
            kl[a:b] = (np.exp(lp) * (lp - lg)).sum(1)
            같음[a:b] = np.asarray(라[a:b]).argmax(1) == np.asarray(글[a:b]).argmax(1)
        한 = {"경우": i, "행": len(ids), "1위 같음 비율": float(같음.mean()), "평균 KL": float(kl.mean()), "KL 최대": float(kl.max()),
             "KL 최대 행": int(kl.argmax()), "KL 중앙값": float(np.median(kl)), "1위 다른 행": np.flatnonzero(~같음).tolist()[:50],
             "판정": bool(같음.mean() >= 0.98 and kl.mean() <= 1e-2)}
        통과 &= 한["판정"]
        결과["경우"].append(한)
        print(f"경우 {i}: 1위 같음 {한['1위 같음 비율'] * 100:.2f} % · 평균 KL {한['평균 KL']:.3e} · 최대 KL {한['KL 최대']:.3e} — "
              f"{'통과' if 한['판정'] else '실패'}")
    결과["통과"] = 통과
    with open(출력, "w", encoding="utf-8") as f:
        json.dump(결과, f, ensure_ascii=False, indent=1)
    print("39a(6)", 결과["gguf"], "— 통과" if 통과 else "— 실패")


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    op = sys.argv[1]
    if op == "입력":
        글들 = sys.argv[5:7] if len(sys.argv) > 6 else [os.path.join(ROOT, "빌드", "wikitext-2-풀기", "wiki.test.raw"),
                                                       os.path.join(ROOT, "연구자안내.md")]
        입력(sys.argv[2], sys.argv[3], sys.argv[4], 글들)
    elif op == "라마":
        라마(sys.argv[2], sys.argv[3], sys.argv[4])
    elif op == "견주기":
        견주기(sys.argv[2], sys.argv[3], sys.argv[4])
    else:
        print(__doc__)


if __name__ == "__main__":
    main()
