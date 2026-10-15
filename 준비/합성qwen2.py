#!/usr/bin/env python3
"""24단계 — 실제 모양 · 층을 줄인 합성 Qwen2 GGUF (이 PC 에 들지 않는 32B · 72B 의 모양을 시험하려고).

  python -I 준비/합성qwen2.py <바탕 GGUF(7B — 메타데이터 · 토크나이저)> <출력.gguf> --모양 14B|32B|72B --층 4 --형식 Q4_0|Q8_0 [--씨앗 24]

- 메타데이터는 바탕 파일의 것을 바이트 그대로 옮기고, 모양 열쇠(qwen2.block_count · embedding_length · feed_forward_length ·
  attention.head_count · attention.head_count_kv)와 general.name · general.file_type 만 바꾼다. 토크나이저(낱말 152064)는 7B 와 같다.
- 텐서는 llama.cpp 의 qwen2 가 읽는 이름 · 모양 그대로: token_embd · output_norm · output, 층마다 attn_norm · attn_q/k/v(weight · bias) ·
  attn_output · ffn_norm · ffn_gate · ffn_up · ffn_down. 가중치는 형식의 블록을 바로 무작위로(씨앗은 텐서 이름마다 — 다시 만들면 같은 파일):
  Q4_0 은 니블 0 … 15 고르게 · 척도 d = 0.0043 · (0.5 … 1.5), Q8_0 은 −127 … 127 고르게 · d = 0.00027 · (0.5 … 1.5) — 값의 표준편차 약 0.02.
  RMS 감마는 1 + N(0, 0.1), 치우침은 N(0, 0.02) (F32).
값은 학습한 모델이 아니다 — 모양 · 비트 · 길 · 속도(층마다)를 보는 데만 쓴다.
37단계 — 바탕이 Qwen3(구조 qwen3)면 열쇠의 앞머리가 qwen3. 이고, 층마다 치우침 대신 attn_q_norm · attn_k_norm(F32 128 칸 — 감마와 같은
1 + N(0, 0.1))을 둔다. 모양 qwen3-14B = Qwen3-14B(5120 · 40 / 8 · 17408). Qwen2 바탕의 파일은 바이트까지 그대로다.
39단계 — 바탕이 llama(Llama 3.1 · 3.2 · Mistral)면 열쇠의 앞머리가 llama. 이고, 층에 치우침 · q · k 정규화가 없다. 바탕에 rope_freqs.weight
(RoPE 늘이기 인자 — F32 64 칸)가 있으면 그 값을 바이트 그대로 옮긴다(모양이 바뀌어도 머리 크기 128 · 늘이기 설정이 같다). 모양 llama-70B =
Llama-3.1-70B(8192 · 64 / 8 · 28672). Q4_K_M 은 이 파일을 llama-quantize(--allow-requantize)로 만든다. Qwen2 · Qwen3 바탕의 파일은 그대로다.
"""
import hashlib
import os
import struct
import sys

import numpy as np

모양들 = {"14B": (5120, 40, 8, 13824), "32B": (5120, 40, 8, 27648), "72B": (8192, 64, 8, 29568),
         "qwen3-14B": (5120, 40, 8, 17408), "llama-70B": (8192, 64, 8, 28672)}
F32, Q4_0, Q8_0 = 0, 2, 8
파일형식 = {"Q4_0": 2, "Q8_0": 7}                                  # llama.cpp 의 LLAMA_FTYPE_MOSTLY_*
정렬 = 32


def 문자열(s):
    b = s.encode("utf-8")
    return struct.pack("<Q", len(b)) + b


def 값건너기(b, o, t):
    고정 = {0: 1, 1: 1, 2: 2, 3: 2, 4: 4, 5: 4, 6: 4, 7: 1, 10: 8, 11: 8, 12: 8}
    if t in 고정:
        return o + 고정[t]
    if t == 8:
        return o + 8 + struct.unpack_from("<Q", b, o)[0]
    if t == 9:
        et, n = struct.unpack_from("<IQ", b, o)
        o += 12
        if et in 고정:
            return o + 고정[et] * n
        for _ in range(n):
            o = 값건너기(b, o, et)
        return o
    raise ValueError(f"GGUF 값 타입 {t}")


def 메타읽기(경로):
    """[(열쇠, 타입, 값 바이트)] — 바탕 파일의 메타데이터를 바이트 그대로."""
    with open(경로, "rb") as f:
        b = f.read(96 * 1024 * 1024)
    assert b[:4] == b"GGUF" and struct.unpack_from("<I", b, 4)[0] == 3
    _, nkv = struct.unpack_from("<QQ", b, 8)
    o = 24
    out = []
    for _ in range(nkv):
        n = struct.unpack_from("<Q", b, o)[0]
        k = b[o + 8:o + 8 + n].decode("utf-8")
        o += 8 + n
        t = struct.unpack_from("<I", b, o)[0]
        e = 값건너기(b, o + 4, t)
        out.append((k, t, b[o + 4:e]))
        o = e
    return out


def 씨앗(이름, 기본):
    return int.from_bytes(hashlib.sha256(f"{기본}:{이름}".encode()).digest()[:8], "little")


def 블록들(형식, n블록, r):
    """무작위 블록 n 개의 바이트."""
    if 형식 == "Q4_0":
        d = (0.0043 * r.uniform(0.5, 1.5, n블록)).astype(np.float16)
        qs = r.integers(0, 256, (n블록, 16), dtype=np.uint8)
        out = np.empty((n블록, 18), np.uint8)
        out[:, :2] = d.view(np.uint8).reshape(n블록, 2)
        out[:, 2:] = qs
        return out
    d = (0.00027 * r.uniform(0.5, 1.5, n블록)).astype(np.float16)
    qs = r.integers(-127, 128, (n블록, 32), dtype=np.int16).astype(np.int8)
    out = np.empty((n블록, 34), np.uint8)
    out[:, :2] = d.view(np.uint8).reshape(n블록, 2)
    out[:, 2:] = qs.view(np.uint8)
    return out


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    바탕, 출력 = sys.argv[1:3]
    인자 = dict(zip(sys.argv[3::2], sys.argv[4::2]))
    모양 = 인자.get("--모양", "72B")
    층 = int(인자.get("--층", "4"))
    형식 = 인자.get("--형식", "Q4_0")
    기본씨앗 = int(인자.get("--씨앗", "24"))
    D, NH, NKV, F = 모양들[모양]
    HD = 128
    KVD = NKV * HD
    메타 = 메타읽기(바탕)
    구조 = next((raw[8:].decode("utf-8") for k, t, raw in 메타 if k == "general.architecture"), "qwen2")
    assert 구조 in ("qwen2", "qwen3", "llama"), 구조
    qwen3 = 구조 == "qwen3"
    llama = 구조 == "llama"                                  # 39단계
    앞 = 구조 + "."
    이름글 = f"합성 Qwen3 {모양} 모양 · 층 {층} · {형식} (37단계)" if qwen3 else f"합성 Qwen2 {모양} 모양 · 층 {층} · {형식} (24단계)"
    if llama:
        이름글 = f"합성 Llama {모양} 모양 · 층 {층} · {형식} (39단계)"
    로프인자 = None
    if llama:                                                # 바탕의 rope_freqs.weight (있으면) — 바이트 그대로
        sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "엔진"))
        import gguf읽기 as GR                                # noqa: E402
        g0 = GR.GGUF(바탕)
        if "rope_freqs.weight" in g0.tensors:
            로프인자 = np.ascontiguousarray(g0.풀기("rope_freqs.weight"), np.float32)
            assert 로프인자.shape == (64,), 로프인자.shape
    V = None
    바꿈 = {앞 + "block_count": (4, struct.pack("<I", 층)), 앞 + "embedding_length": (4, struct.pack("<I", D)),
          앞 + "feed_forward_length": (4, struct.pack("<I", F)), 앞 + "attention.head_count": (4, struct.pack("<I", NH)),
          앞 + "attention.head_count_kv": (4, struct.pack("<I", NKV)),
          "general.name": (8, 문자열(이름글)),
          "general.file_type": (4, struct.pack("<I", 파일형식[형식]))}
    kv = []
    for k, t, raw in 메타:
        if k == "tokenizer.ggml.tokens":
            V = struct.unpack_from("<Q", raw, 4)[0]
        if k in 바꿈:
            t2, raw2 = 바꿈.pop(k)
            assert t2 == t, (k, t, t2)
            raw = raw2
        kv.append((k, t, raw))
    for k, (t, raw) in 바꿈.items():                     # 바탕에 없던 열쇠
        kv.append((k, t, raw))
    assert V is not None
    # 텐서 — (이름, 타입, ne0, ne1) 차례
    텐서 = [("token_embd.weight", 형식, D, V)]
    if 로프인자 is not None:
        텐서 += [("rope_freqs.weight", "F32", 64, 1)]
    for l in range(층):
        p = f"blk.{l}."
        if llama:                                            # 39단계 — 치우침 · q · k 정규화 없음
            텐서 += [(p + "attn_norm.weight", "F32", D, 1), (p + "attn_q.weight", 형식, D, D), (p + "attn_k.weight", 형식, D, KVD),
                   (p + "attn_v.weight", 형식, D, KVD), (p + "attn_output.weight", 형식, D, D), (p + "ffn_norm.weight", "F32", D, 1),
                   (p + "ffn_gate.weight", 형식, D, F), (p + "ffn_up.weight", 형식, D, F), (p + "ffn_down.weight", 형식, F, D)]
            continue
        if qwen3:                                            # 37단계 — 치우침 없음, 머리마다 q · k 정규화의 무게
            텐서 += [(p + "attn_norm.weight", "F32", D, 1), (p + "attn_q.weight", 형식, D, D), (p + "attn_q_norm.weight", "F32", HD, 1),
                   (p + "attn_k.weight", 형식, D, KVD), (p + "attn_k_norm.weight", "F32", HD, 1), (p + "attn_v.weight", 형식, D, KVD),
                   (p + "attn_output.weight", 형식, D, D), (p + "ffn_norm.weight", "F32", D, 1),
                   (p + "ffn_gate.weight", 형식, D, F), (p + "ffn_up.weight", 형식, D, F), (p + "ffn_down.weight", 형식, F, D)]
            continue
        텐서 += [(p + "attn_norm.weight", "F32", D, 1), (p + "attn_q.weight", 형식, D, D), (p + "attn_q.bias", "F32", D, 1),
               (p + "attn_k.weight", 형식, D, KVD), (p + "attn_k.bias", "F32", KVD, 1), (p + "attn_v.weight", 형식, D, KVD),
               (p + "attn_v.bias", "F32", KVD, 1), (p + "attn_output.weight", 형식, D, D), (p + "ffn_norm.weight", "F32", D, 1),
               (p + "ffn_gate.weight", 형식, D, F), (p + "ffn_up.weight", 형식, D, F), (p + "ffn_down.weight", 형식, F, D)]
    텐서 += [("output_norm.weight", "F32", D, 1), ("output.weight", 형식, D, V)]
    블록바이트 = {"Q4_0": 18, "Q8_0": 34}

    def 바이트수(t, ne0, ne1):
        return ne0 * ne1 * 4 if t == "F32" else ne0 // 32 * ne1 * 블록바이트[t]

    머리 = bytearray(b"GGUF" + struct.pack("<IQQ", 3, len(텐서), len(kv)))
    for k, t, raw in kv:
        머리 += 문자열(k) + struct.pack("<I", t) + raw
    off = 0
    for 이름, t, ne0, ne1 in 텐서:
        tt = {"F32": F32, "Q4_0": Q4_0, "Q8_0": Q8_0}[t]
        if ne1 == 1:
            머리 += 문자열(이름) + struct.pack("<I", 1) + struct.pack("<Q", ne0) + struct.pack("<IQ", tt, off)
        else:
            머리 += 문자열(이름) + struct.pack("<I", 2) + struct.pack("<QQ", ne0, ne1) + struct.pack("<IQ", tt, off)
        off += (바이트수(t, ne0, ne1) + 정렬 - 1) // 정렬 * 정렬
    머리 += b"\0" * ((-len(머리)) % 정렬)
    with open(출력, "wb") as f:
        f.write(머리)
        for 이름, t, ne0, ne1 in 텐서:
            r = np.random.default_rng(씨앗(이름, 기본씨앗))
            n = 바이트수(t, ne0, ne1)
            if t == "F32" and 이름 == "rope_freqs.weight":
                f.write(로프인자.tobytes())
            elif t == "F32":
                if 이름.endswith("norm.weight"):
                    x = (1.0 + 0.1 * r.standard_normal(ne0)).astype(np.float32)
                else:
                    x = (0.02 * r.standard_normal(ne0)).astype(np.float32)
                f.write(x.tobytes())
            else:
                행블록 = ne0 // 32
                쓴 = 0
                for 시작 in range(0, ne1, 4096):                   # 행 4096 개씩(메모리)
                    끝 = min(ne1, 시작 + 4096)
                    b = 블록들(t, (끝 - 시작) * 행블록, r)
                    f.write(b.tobytes())
                    쓴 += b.size
                assert 쓴 == n
            f.write(b"\0" * ((-n) % 정렬))
    print(f"{출력}: {모양} 모양(너비 {D} · 머리 {NH} · KV {NKV} · 확장폭 {F} · 낱말 {V}) · 층 {층} · {형식} · 텐서 {len(텐서)} · 메타 {len(kv)}")


if __name__ == "__main__":
    main()
