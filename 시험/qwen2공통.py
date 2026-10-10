"""14단계 시험의 공통 — Qwen2.5-0.5B-Instruct(Q8_0 GGUF)의 경로, 엔진 만들기, CPU 참조(계약/정수계약.qwen2_앞으로)의 가중치."""
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, ".."))
for d in ("엔진", "계약", "커널"):
    sys.path.insert(0, os.path.join(ROOT, d))
import gguf읽기 as GR          # noqa: E402
import 정수계약 as C            # noqa: E402

모델 = os.environ.get("GEULPU_MODELS", os.path.join(ROOT, "모델"))
폴더 = os.path.join(모델, "qwen2.5-0.5b-instruct")
GGUF = os.path.join(모델, "qwen2.5-0.5b-instruct-gguf", "qwen2.5-0.5b-instruct-q8_0.gguf")
질문들 = ["What is the capital of France? Answer in one word.", "대한민국의 수도는 어디야? 한 단어로 답해.",
         "Write a short poem about the sea."]


def 있나():
    return os.path.exists(GGUF) and os.path.exists(os.path.join(폴더, "tokenizer.json"))


def 토크나이저():
    import 토크나이저 as TK
    return TK.Qwen토크나이저(폴더)


def 채팅(tk, 질문):
    import 토크나이저 as TK
    return tk.나누기(TK.채팅틀([{"role": "user", "content": 질문}]))


def 엔진(**kw):
    import 글qwen2
    return 글qwen2.글Qwen2(GGUF, **kw)


def _q8(g, name):
    """GGUF Q8_0 텐서 → (q [N][K] int8, d [N][K/32] 짧은실수)."""
    t, dims, raw = g.원(name)
    assert t == GR.Q8_0
    K, N = dims
    bl = raw.reshape(N, K // 32, 34)
    d = np.ascontiguousarray(bl[:, :, :2]).view(np.float16).reshape(N, K // 32).astype(np.float32)
    q = np.ascontiguousarray(bl[:, :, 2:]).view(np.int8).reshape(N, K)
    return q, d


def 참조가중치(path=GGUF):
    """정수계약.qwen2_앞으로 의 가중치(같은 GGUF 의 정수와 척도 그대로) — (W, 설정)."""
    g = GR.GGUF(path)
    m = g.meta
    설정 = {"층": m["qwen2.block_count"], "머리": m["qwen2.attention.head_count"], "KV머리": m["qwen2.attention.head_count_kv"],
           "theta": float(m["qwen2.rope.freq_base"]), "eps": float(m["qwen2.attention.layer_norm_rms_epsilon"])}
    eq, ed = _q8(g, "token_embd.weight")
    W = {"embed": (eq, ed), "norm": g.풀기("output_norm.weight")}
    hq, hd = _q8(g, "output.weight") if "output.weight" in g.tensors else (eq, ed)
    W["head"] = (hq.T, np.ascontiguousarray(hd.T))
    for l in range(설정["층"]):
        p = f"blk.{l}."
        for a, b in (("wq", "attn_q"), ("wk", "attn_k"), ("wv", "attn_v"), ("wo", "attn_output"), ("wg", "ffn_gate"),
                     ("wu", "ffn_up"), ("wd", "ffn_down")):
            q, d = _q8(g, p + b + ".weight")
            W[f"{l}.{a}"] = (q.T, np.ascontiguousarray(d.T))
        for a, b in (("bq", "attn_q.bias"), ("bk", "attn_k.bias"), ("bv", "attn_v.bias"), ("n1", "attn_norm.weight"),
                     ("n2", "ffn_norm.weight")):
            W[f"{l}.{a}"] = g.풀기(p + b)
    return W, 설정


def 참조로짓(W, 설정, ids, 최대길이=None, 첫위치=0, 캐시=None):
    """CPU 참조의 로짓 [n][어휘] — 엔진과 같은 RoPE 표(정수계약.rope표)."""
    n = 첫위치 + len(ids)
    cos, sin = C.rope표(최대길이 or max(64, n), 설정["theta"])
    return C.qwen2_앞으로(W, 설정, ids, cos, sin, 첫위치=첫위치, 캐시=캐시)


def 같은비트(a, b):
    a, b = np.asarray(a, np.float32), np.asarray(b, np.float32)
    return a.shape == b.shape and np.array_equal(a.view(np.int32), b.view(np.int32))


def 다른칸(a, b):
    a, b = np.asarray(a, np.float32), np.asarray(b, np.float32)
    return int((a.view(np.int32) != b.view(np.int32)).sum())
