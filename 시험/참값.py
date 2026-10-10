"""참값 — 실수(fp64)로 계산한 모델의 로짓. 정확도 판정의 기준(원래 모델 · 양자화 모델의 참값)이다. torch(GPU, fp64)로 계산한다.

  qwen2_원래(폴더)    — Hugging Face 원본(safetensors, bf16 → 정확히 fp64)
  qwen2_gguf(경로)    — GGUF 의 가중치를 풀어(Q8_0: q · d — 정확히) fp64 로; 로짓은 output.weight (llama.cpp 와 같은 텐서)
  qwen2_로짓(W, ids)  — 로짓 [n][어휘] fp64: RMSNorm · RoPE(NeoX — 반쪽 돌리기) · GQA 원인 어텐션 · SwiGLU, 모두 fp64
"""
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, ".."))
sys.path.insert(0, os.path.join(ROOT, "엔진"))
import gguf읽기 as GR       # noqa: E402


def _safetensors(path):
    """{이름: float32 배열} — F32 · BF16 · F16 (BF16 은 비트를 옮겨 정확히)."""
    with open(path, "rb") as f:
        n = int.from_bytes(f.read(8), "little")
        head = json.loads(f.read(n))
        raw = f.read()
    out = {}
    for name, info in head.items():
        if name == "__metadata__":
            continue
        b, e = info["data_offsets"]
        if info["dtype"] == "BF16":
            u = np.frombuffer(raw, dtype=np.uint16, count=(e - b) // 2, offset=b)
            a = (u.astype(np.uint32) << 16).view(np.float32)
        elif info["dtype"] == "F16":
            a = np.frombuffer(raw, dtype=np.float16, count=(e - b) // 2, offset=b).astype(np.float32)
        elif info["dtype"] == "F32":
            a = np.frombuffer(raw, dtype=np.float32, count=(e - b) // 4, offset=b)
        else:
            raise ValueError(f"{name}: {info['dtype']}")
        out[name] = a.reshape(info["shape"])
    return out


def qwen2_원래(폴더):
    """원본 가중치 → 공통 이름(층 l: wq bq wk bk wv bv wo · n1 n2 · wg wu wd, embed, norm, head) — 선형은 [출력][입력]."""
    cfg = json.load(open(os.path.join(폴더, "config.json"), encoding="utf-8"))
    w = _safetensors(os.path.join(폴더, "model.safetensors"))
    W = {"embed": w["model.embed_tokens.weight"], "norm": w["model.norm.weight"]}
    W["head"] = w.get("lm_head.weight", W["embed"])            # tie_word_embeddings
    for l in range(cfg["num_hidden_layers"]):
        p = f"model.layers.{l}."
        for a, b in (("wq", "self_attn.q_proj.weight"), ("bq", "self_attn.q_proj.bias"), ("wk", "self_attn.k_proj.weight"),
                     ("bk", "self_attn.k_proj.bias"), ("wv", "self_attn.v_proj.weight"), ("bv", "self_attn.v_proj.bias"),
                     ("wo", "self_attn.o_proj.weight"), ("n1", "input_layernorm.weight"), ("n2", "post_attention_layernorm.weight"),
                     ("wg", "mlp.gate_proj.weight"), ("wu", "mlp.up_proj.weight"), ("wd", "mlp.down_proj.weight")):
            W[f"{l}.{a}"] = w[p + b]
    설정 = {"층": cfg["num_hidden_layers"], "머리": cfg["num_attention_heads"], "KV머리": cfg["num_key_value_heads"],
           "theta": cfg["rope_theta"], "eps": cfg["rms_norm_eps"]}
    return W, 설정


def qwen2_gguf(path):
    """GGUF(qwen2) 의 가중치를 풀어(짧은실수 — q · d 는 정확) 같은 이름으로. 로짓은 output.weight(있으면) — llama.cpp 가 쓰는 텐서."""
    g = GR.GGUF(path)
    m = g.meta
    W = {"embed": g.풀기("token_embd.weight"), "norm": g.풀기("output_norm.weight")}
    W["head"] = g.풀기("output.weight") if "output.weight" in g.tensors else W["embed"]
    for l in range(m["qwen2.block_count"]):
        p = f"blk.{l}."
        for a, b in (("wq", "attn_q.weight"), ("bq", "attn_q.bias"), ("wk", "attn_k.weight"), ("bk", "attn_k.bias"),
                     ("wv", "attn_v.weight"), ("bv", "attn_v.bias"), ("wo", "attn_output.weight"), ("n1", "attn_norm.weight"),
                     ("n2", "ffn_norm.weight"), ("wg", "ffn_gate.weight"), ("wu", "ffn_up.weight"), ("wd", "ffn_down.weight")):
            W[f"{l}.{a}"] = g.풀기(p + b)                         # GGUF 의 [ne1][ne0] = [출력][입력]
    설정 = {"층": m["qwen2.block_count"], "머리": m["qwen2.attention.head_count"], "KV머리": m["qwen2.attention.head_count_kv"],
           "theta": float(m["qwen2.rope.freq_base"]), "eps": float(m["qwen2.attention.layer_norm_rms_epsilon"])}
    return W, 설정


def qwen2_로짓(W, 설정, ids, 장치="cuda"):
    """fp64 로짓 [n][어휘] (numpy). W 는 qwen2_원래 · qwen2_gguf 의 결과."""
    import torch
    with torch.no_grad():
        T = lambda a: torch.from_numpy(np.ascontiguousarray(a)).to(장치, torch.float64)
        n = len(ids)
        NH, NKV = 설정["머리"], 설정["KV머리"]
        x = T(W["embed"][np.asarray(ids)])
        D = x.shape[1]
        hd = D // NH
        inv = 1.0 / (설정["theta"] ** (torch.arange(0, hd, 2, dtype=torch.float64, device=장치) / hd))
        ang = torch.arange(n, dtype=torch.float64, device=장치)[:, None] * inv[None, :]
        cos, sin = torch.cat([ang.cos(), ang.cos()], 1), torch.cat([ang.sin(), ang.sin()], 1)       # [n][hd]

        def rms(v, g):
            return v / torch.sqrt((v * v).mean(-1, keepdim=True) + 설정["eps"]) * T(g)

        def rope(t):                                                                            # [헤드][n][hd]
            t1, t2 = t[..., :hd // 2], t[..., hd // 2:]
            return t * cos + torch.cat([-t2, t1], -1) * sin
        가림 = torch.full((n, n), float("-inf"), dtype=torch.float64, device=장치).triu(1)
        for l in range(설정["층"]):
            h = rms(x, W[f"{l}.n1"])
            q = h @ T(W[f"{l}.wq"]).T + T(W[f"{l}.bq"])
            k = h @ T(W[f"{l}.wk"]).T + T(W[f"{l}.bk"])
            v = h @ T(W[f"{l}.wv"]).T + T(W[f"{l}.bv"])
            q = rope(q.view(n, NH, hd).transpose(0, 1))
            k = rope(k.view(n, NKV, hd).transpose(0, 1)).repeat_interleave(NH // NKV, 0)
            v = v.view(n, NKV, hd).transpose(0, 1).repeat_interleave(NH // NKV, 0)
            s = q @ k.transpose(1, 2) / (hd ** 0.5) + 가림
            y = (torch.softmax(s, -1) @ v).transpose(0, 1).reshape(n, D)
            x = x + y @ T(W[f"{l}.wo"]).T
            h = rms(x, W[f"{l}.n2"])
            g_, u = h @ T(W[f"{l}.wg"]).T, h @ T(W[f"{l}.wu"]).T
            x = x + (g_ * torch.sigmoid(g_) * u) @ T(W[f"{l}.wd"]).T
        x = rms(x, W["norm"])
        return (x @ T(W["head"]).T).cpu().numpy()
