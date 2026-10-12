# GeulPU — bit-reproducible LLM inference under a written precision contract

*A short technical brief for reviewers, maintainers of inference engines, and GPU tool vendors. Repository:
<https://github.com/wwoosshh/GeulPU> (MIT). All measurements are from a single RTX 4070 Ti (12 GB, Windows 11); independent reproduction
is welcome — see [reproduce.md](reproduce.md).*

## Summary

- **Problem.** LLM inference engines usually let the hardware and the batching decide rounding order, so results change with batch
  composition and with how the input is fed, and they add "hidden" precision loss beyond the model file's own quantization (e.g. by
  re-quantizing activations to 8 bits).
- **Approach.** GeulPU fixes every rounding point in a written contract: activations are per-32-value-block integers stored as two
  balanced base-256 digits (2⁻¹⁴ of the block maximum), dot products are exact integer tensor-core sums, accumulation follows one fixed
  fma chain, exp is a written polynomial, and PTX uses explicit rounding so nothing is fused behind the source's back.
  ([contract.md](contract.md))
- **Result.** GPU output is bit-identical to a CPU reference implementation on every execution path (all at once, in pieces, token by
  token, as a conversation, batched, layer-split), on Qwen2.5 0.5B / 7B / 14B with Q8_0, Q4_0 and k-quant GGUF files.
- **Cost.** Decoding is at parity with llama.cpp. Prompt processing is slower (1.15–2.12× llama.cpp's time at stage 26), mainly because two
  digits mean twice the integer tensor work of 8-bit activations; the gap is being narrowed stage by stage.
- **Toolchain.** The kernels, the host and the kernel generator are written in geul (a Korean programming language) and compiled by its
  self-hosted compiler, which also emits the PTX. The chat runner imports only `kernel32`, `shell32` and `nvcuda.dll` — no CUDA toolkit,
  cuBLAS or PyTorch.

## Evidence

| Claim | Evidence (stage) |
|---|---|
| Bit-identical to the CPU reference | every kernel variant on real weights (e.g. 243 k-quant cases); all rows of logits of full forward passes (26.2 M values per 7B file) — 0 differing values (14, 22–26) |
| Path invariance | logits and KV cache identical across five paths (decode graph, all at once, in four pieces, one row at a time, again) and across layer splits into 2–4 parts (22–26, 25) |
| Perplexity does not depend on how text is fed | wikitext-2: GeulPU's NLL sum is bit-identical for 512-row, 128-row and 1-row feeding; llama.cpp's perplexity ranges 15.8171–15.8200 with batch settings (20) |
| Less hidden loss | Qwen2.5-0.5B Q8_0: KL against an fp64 forward pass of the same weights is 1/615 of llama.cpp's; perplexity within −6.6 × 10⁻⁶ (relative) of fp64, llama.cpp +0.34% (14, 20). A rounding-point simulation (validated on 0.5B: 1/637 vs measured 1/615) gives 1/3805 (7B) and 1/4467 (14B) (review) |
| Speed | 0.5B: prompts 0.55–0.82×, decode 0.63–0.65× of llama.cpp's time (14, 15). 7B / 14B decode 0.970–1.012× (23, 24, 26). Prompts 1.15–1.38× (Q8_0 · Q4_0) and 1.46–2.12× (k-quants) at stage 26 |
| Reproducible builds | CI on a clean GitHub runner rebuilds the compiler, the PTX backend and six kernel modules byte-identically to the local build used for the measurements |

## Limits we know about

- One GPU model (RTX 4070 Ti), one machine, Windows only. Multi-GPU layer split was only emulated on one GPU.
- Qwen2 family only; greedy decoding only; no MoE; Q2_K · Q3_K · IQ formats not supported.
- The contract's loss was measured with the real engine only on 0.5B; for 7B · 14B it was simulated.
- The review of the contract found one place at roughly float16 precision: attention probabilities (two digits per 32-key block).
- k-quant files used for timing were re-quantized locally from Q8_0 with llama.cpp's standard mixes; official files are not yet tested.

## Questions and proposals

These are drafts for discussion; nothing has been submitted.

**For inference-engine maintainers (llama.cpp / ggml and others)**

1. *Batch- and split-invariance as an option.* Our numbers suggest the cost is small for decoding (parity) and moderate for prompts. Would
   an opt-in deterministic mode with a written accumulation order be of interest? We can share the contract and the CPU reference.
2. *Measuring hidden loss.* Comparing against an fp64 forward pass of the same quantized weights separates an engine's own loss from the
   file's quantization loss (stage 20 method). We would welcome an independent check of our measurement of llama.cpp.

**For NVIDIA (compiler and tools)**

1. *Scheduling of integer MMA with per-block epilogues.* Our prompt tile kernels (sm_89, `mma.sync.aligned.m16n8k32.row.col.s32.s8.s8.s32`)
   issue 14–17 instructions per MMA in the main loop; about half of them are a per-element, per-32-value-block epilogue (combine the
   two digit sums, int → float, scale, fma). Nsight Compute 2026.3 on real 7B weights shows the tensor pipe 54–58% busy and "math pipe
   throttle" as the largest stall: `ptxas` places the MMAs in tight bursts (eight close together, then about 40 other instructions), so
   the tensor pipe alternates between saturated and idle and both the issue slots and the tensor pipe stay around 60%. Is there a
   recommended way to make the scheduler interleave MMAs with independent epilogue work, or published guidance for this pattern?
2. *Exact wider-integer products.* Exact two-digit activations need two int8 MMAs per product (for Q4_0 · Q4_K we already chain the
   two through the accumulator, so the second adds no epilogue work). Is there a recommended way to obtain exact 16-bit × 8-bit integer
   products on current tensor cores with less than twice the int8 work?
3. *Non-ASCII paths on Windows.* (a) On a GitHub-hosted Windows runner (English locale), `ptxas` from the `nvidia-cuda-nvcc-cu12`
   12.9.86 wheel fails with `Input file '…\????\qwen2Q8.ptx' could not be opened` when the path contains Korean folder names — the name
   appears to pass through the ANSI code page. (b) Nsight Compute 2026.3.1.2 (zip redistributable) fails at startup on Korean-locale
   Windows 11 (ANSI code page 949) when its own install path contains Korean characters ("No mapping for the Unicode character exists in
   the target multi-byte code page"). We work around both with ASCII paths; both could be filed as bug reports with minimal examples.

## How to check our claims

- The contract and its CPU reference: [contract.md](contract.md), [`계약/정수계약.py`](../계약/정수계약.py).
- How the hidden loss was measured (method, checks of the measurement, the 7B · 14B simulation): [hidden-loss.md](hidden-loss.md).
- GPU-free CI on every push: builds everything from source and checks module bytes and SASS register spills
  ([reproduce.md](reproduce.md)).
- GPU tests and benchmarks, with the exact scripts used for each stage's verdict: [reproduce.md](reproduce.md), `공식실행/`.
- English summary of all stages with failures and missed criteria: [research-log.md](research-log.md).
