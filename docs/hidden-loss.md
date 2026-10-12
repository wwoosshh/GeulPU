# Hidden loss — how it is measured and what was found

*English version of the quality measurements in [`문서/14단계.md`](../문서/14단계.md), [`문서/20단계.md`](../문서/20단계.md) and
[`문서/계약손실검토.md`](../문서/계약손실검토.md) (contract-loss review). Terms follow the [glossary](glossary.md).*

## What "hidden loss" means here

A quantized model file already loses information relative to the original weights — that is the file's **format loss**, and every engine
that reads the file shares it. An engine then adds its own rounding on top: re-quantizing activations, half-precision caches, fused or
reordered arithmetic. We call that extra part the **hidden loss**, and measure it against a **ground truth**: an fp64 forward pass of the
*same* GGUF weights (each block dequantized exactly as q · d). The main metric is the mean KL divergence KL(ground truth ‖ engine) of the
next-token distribution over the whole vocabulary, averaged over all scored rows; we also report perplexity (PPL) and how often the
most likely token agrees with the ground truth.

llama.cpp is build b11496 (CUDA) throughout.

## 1. First measurement — Qwen2.5-0.5B-Instruct Q8_0, a short text (stage 14)

All rows of a 461-token evaluation text ([`시험/평가글.txt`](../시험/평가글.txt)), and 64 decoding steps for three chat prompts.

| | GeulPU | llama.cpp | GeulPU / llama.cpp |
|---|---|---|---|
| Mean KL against the ground truth (461 tokens) | 2.24 × 10⁻⁶ | 1.38 × 10⁻³ | **1/615** |
| Top token agrees with the ground truth · median relative difference of a row of logits | 99.78% · 0.071% | 97.61% · 2.2% | |
| Median relative difference per step, 64 decoding steps (three chat prompts) | 0.22% · 0.14% · 0.065% | 3.3% · 3.1% · 1.8% | 0.068 · 0.047 · 0.036 |

GeulPU chose the ground truth's token at every one of those decoding steps.

(The stage-14 document first described the text as 512 tokens; it is 461 tokens with the Qwen tokenizer — disclosed there.)

## 2. Perplexity on wikitext-2 (stage 20)

A third-party review (2026-10-10) said the 1/615 figure is correct but easy to overstate: no perplexity or benchmark difference had been
shown, and llama.cpp's extra KL might be of the same order as the Q8_0 format loss itself. Stage 20 measured exactly that, with criteria
committed before the run.

**Method** — the same as llama.cpp's `llama-perplexity`: tokenize `wiki.test.raw` of wikitext-2-raw-v1 (no BOS for Qwen2), cut it into
512-token chunks (the tail is dropped), compute each chunk from position 0, and score the second half (the logits at positions 256 … 510
predicting tokens 257 … 511 — 255 per chunk). PPL = exp(mean NLL). 584 chunks, 148,920 scored tokens. llama.cpp: `llama-perplexity -c 512`
with default settings (n_batch 2048 — four chunks per batch); for KL, the same computation through its C API. Ground truths: fp64 forward
passes of the Q8_0 weights and of the F16 weights from the same official release.

| Qwen2.5-0.5B-Instruct, wikitext-2 test | Ground truth F16 | Ground truth Q8_0 | GeulPU | llama.cpp |
|---|---|---|---|---|
| PPL | 15.725389 | 15.763774 | **15.763670** | 15.817967 (`llama-perplexity`: 15.8180 ± 0.12058) |
| Mean NLL | 2.7552765 | 2.7577145 | 2.7577079 | 2.7611465 |
| Mean NLL − ground truth Q8_0 (paired by chunk, ± standard error) | −2.44 × 10⁻³ ± 0.12 × 10⁻³ | 0 | **−6.6 × 10⁻⁶ ± 1.2 × 10⁻⁵** | +3.43 × 10⁻³ ± 0.17 × 10⁻³ |
| Mean KL(ground truth Q8_0 ‖ ·); F16 column: KL(F16 ‖ Q8_0) = format loss | 7.20 × 10⁻⁴ | 0 | **3.63 × 10⁻⁶** | 1.40 × 10⁻³ |
| Top token agrees with ground truth Q8_0 | 98.44% | 100% | **99.89%** | 97.79% |

| Criterion (pre-registered) | Result |
|---|---|
| 20a invariance — GeulPU's per-chunk NLL sums (fp64 bits) and PPL do not depend on how the text is fed: 512 rows at once (twice), four pieces of 128 rows (continuing the KV cache), one row at a time (first 64 chunks) | **Passed** — all 584 sums identical, file for file |
| 20b accuracy — PPL within 10⁻⁴ (relative) of the ground truth, and KL at most 1/100 of llama.cpp's | **Passed** — relative −6.6 × 10⁻⁶; KL **1/385** of llama.cpp's |
| 20c scale — r = llama.cpp's hidden loss / Q8_0 format loss; r < 0.1 "an order smaller", 0.1–10 "same order — the review is right", > 10 "an order larger" | **Same order — the review is right**: r = 1.40 × 10⁻³ / 7.20 × 10⁻⁴ = **1.95** (1.41 in PPL terms) |

**What this says.** GeulPU's perplexity cannot be told apart from the fp64 ground truth (the difference is within its standard error).
llama.cpp's hidden loss is real — its mean NLL is 20 standard errors above the ground truth (PPL +0.34%) — but it is of the same order as
the Q8_0 quantization of the weights (KL 1.9×, NLL 1.4×). For this model and this text, "1/615" should be read with that scale in mind.
On the longer text the KL ratio is 1/385 rather than 1/615.

**llama.cpp's perplexity depends on batch settings** (same model, text and chunks): default (-b 2048 -ub 512) 15.8180; -ub 128 15.8192;
-ub 32 15.8171; -b 512 (one chunk per batch) 15.8200. GeulPU gives 15.763669739143534 to the last bit for every way of feeding.

**Checks of the measurement itself** (all passed): GeulPU's tokenizer, the Python tokenizer and llama.cpp's C API give the same 299,078
tokens; the C-API computation reproduces all 584 running PPL values printed by `llama-perplexity` to four decimals; all 19,690,496 Q8_0
blocks equal llama.cpp's Q8_0 quantization of the F16 weights byte for byte (d = amax / 127, q = roundf(x / d)) — so the F16 vs Q8_0
difference is exactly the format loss; GeulPU's own NLL sums agree with a Python recomputation from the same logits within 1.1 × 10⁻¹⁴
(relative).

## 3. Larger models — a rounding-point simulation (contract-loss review)

Measuring 7B and 14B like stage 20 would take more than nine hours. The review asked a narrower question within two hours: **is there a
sign that the contract must change** as models grow (larger activation outliers make a block-maximum grid lose the small values in the
same block)?

**Method.** Three fp64 forward passes that differ only in where they round:

- *ground truth* — no rounding;
- *contract emulation* — inputs of the linear layers (qkv · o · gate·up · down · logits), q · k · v and the attention probabilities rounded
  to the contract's grid (per 32-value block, 2^(E − 13) with E = ⌊log₂ block max⌋, round half to even; probabilities per 32-key block
  within a 64-key chunk, as in [contract.md](contract.md) section 2.4);
- *llama.cpp emulation* — linear-layer inputs rounded to Q8_1 (block max / 127, as llama.cpp re-quantizes activations for quantized
  matmuls), q · k · v and probabilities to f16 (F16 KV cache, flash attention).

The emulation leaves out float32 roundings (residual adds, RMSNorm, RoPE, written exp), so it is first validated on 0.5B, where the real
engines were measured. Text: the same 461-token evaluation text, all rows. r = KL(truth ‖ contract) / KL(truth ‖ llama.cpp).

**Pre-registered rules.** (1) The emulation is trusted only if 0.5B gives 1/2000 ≤ r ≤ 1/200 (measured: 1/615). (2) A sign of trouble
if any of: (a) r at 7B or 14B is more than four times r at 0.5B; (b) r at 7B or 14B is above 1/30; (c) at some rounding point (kind ×
layer) of 7B or 14B the contract's relative error exceeds the llama.cpp emulation's.

| Model (weights) | KL(truth ‖ contract) | KL(truth ‖ llama.cpp) | r | Top token agrees (contract · llama.cpp) |
|---|---|---|---|---|
| 0.5B (Q8_0) | 2.25 × 10⁻⁶ (measured 2.24 × 10⁻⁶) | 1.43 × 10⁻³ (measured 1.38 × 10⁻³) | **1/637** (measured 1/615) | 1.0000 · 0.9718 |
| 7B (Q8_0) | 1.58 × 10⁻⁷ | 6.01 × 10⁻⁴ | **1/3805** | 1.0000 · 0.9783 |
| 14B (Q4_0) | 1.55 × 10⁻⁷ | 6.93 × 10⁻⁴ | **1/4467** | 1.0000 · 0.9826 |

- Rule 1: **passed** — the emulation reproduces the measured 0.5B values closely.
- (a) **no**: r falls from 1/637 to 1/3805 and 1/4467 (the contract's own loss is 15× smaller). (b) **no**.
- (c) **yes — the attention probabilities.** The contract's probability rounding (two digits per 32-key block) has a larger relative
  error than f16 in 12 of 28 layers (7B; worst ratio 1.32, layer 26) and 34 of 48 layers (14B; 1.79, layer 5). Everywhere else the contract
  is finer: linear-layer inputs about 1/80 of Q8_1's error (worst ratio 0.012–0.022), q · k · v 0.39–0.63× of f16's.

Where the contract's loss comes from (turning on one rounding point at a time; record, not a criterion):

| Model | All | Linear inputs only | q · k · v only | Probabilities only |
|---|---|---|---|---|
| 0.5B | 2.25 × 10⁻⁶ | 2.24 × 10⁻⁷ | 1.94 × 10⁻⁶ | 2.91 × 10⁻⁸ (1.3%) |
| 7B | 1.58 × 10⁻⁷ | 8.28 × 10⁻⁸ | 7.34 × 10⁻⁸ | 1.41 × 10⁻⁸ (9%) |

Large activations do appear: at the input of down (the SwiGLU output) in 7B layer 2 and 14B layer 3 the contract rounds 9% of the
values to zero (0.5B: 0.1%), because of large values in the same block — yet the error there is still 1/50 of Q8_1's.

**Conclusion.** No reason to change the contract now: at 7B and 14B its loss is about 1/4000 of the llama.cpp emulation's, and the
advantage grows with model size. The one flagged place is the attention probabilities, at about f16 level. This review used a short text;
how much that place matters with thousands of keys is the next thing to check. If it ever needs fixing, the change would be three digits
for probabilities or 16-key blocks — a contract change that must be pre-registered and re-measured.

## Limits

- Real-engine measurements of the hidden loss exist only for 0.5B (two texts). 7B and 14B are simulated.
- One text per measurement, context 512 (perplexity) or 461 tokens (KL); long-context attention probabilities are not covered.
- KL and perplexity only — no task benchmarks (MMLU etc.).
- The 14B file is a locally re-quantized Q4_0 (`--pure`).
- The ground truths and comparison tools are Python (PyTorch for fp64 on the GPU); they are used for measurement only, not by the engine.
