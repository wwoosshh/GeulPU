# Research log — how GeulPU came about (stages 0–37, 2026-10-08 to 10-15)

*English summary of [`문서/단계기록.md`](../문서/단계기록.md). Stage reports (Korean) are in [`문서/`](../문서/); stages 0–13 are in the
`research/gpu` branch of the geul repository ([docs/17](https://github.com/wwoosshh/geul-lang/blob/research/gpu/docs/17-연구-의미를-지키는-GPU-컴파일러.md),
[research/gpu/](https://github.com/wwoosshh/geul-lang/tree/research/gpu/research/gpu)).*

**Method.** Every stage writes its pass/fail criteria first and commits them before any measurement. Every kernel variant is compared
bit for bit against the CPU reference before it is timed. Failures and missed criteria are recorded as they happened. All numbers are
from one RTX 4070 Ti (12 GB) on Windows 11; llama.cpp is build b11496 (CUDA) through stage 29 and the latest official release at measurement time from stage 30 (b11567; b11609 Vulkan for stage 31i). Speed ratios r are time(GeulPU) / time(llama.cpp) on the
same GGUF file: r < 1 means GeulPU is faster.

## Stages

| Stage | What | Result |
|---|---|---|
| 0 | Classify 43 public real-world bugs by a fixed rule: what meaning was lost, and where | Bugs that geul's grammar would block: 28% (criterion 50% — missed). Losses inside compilers: 23% → "the compiler must keep meaning" comes first |
| 1 | Probe: geul source → typed IR → PTX, run through the driver by a host written in geul | Passed. PTX contract found: without an explicit rounding mode the driver fuses multiply+add into FMA and values change (245,734 of 1,048,576) → `.rn` everywhere |
| 2 | Address spaces, registers, shared-memory tiles, range checks (error cell) | Matmul 19.8 → 0.48 ms; row-invariant, bits unchanged |
| 3 | GPT-2 small in geul kernels — identical bits on every path; a generation megakernel | Decode 1.19 ms/token (PyTorch CUDA graph 1.54); 0 differing elements across paths (PyTorch: 74–96% differ) |
| 4 | Compare with llama.cpp and Hugging Face (speed, meaning, stability); declared precision: half-precision KV | Decode ahead, prompt 4–9% behind. llama.cpp changes 99.96% of output elements depending on how input is fed — GeulPU 0 |
| 5 | Quantized GGUF (F16 · Q8_0 · Q4_0) used as is — only the format's declared loss | KL vs the original model = the format's own loss (llama.cpp loses 1.6–505× the format's loss); decode ahead |
| 6 | Integer tensor cores — the integer block contract (four digits) | Prompts also ahead of llama.cpp on small; error 1/100 of llama.cpp's |
| 7 | GPT-2 XL (1.5B) | Decode and accuracy ahead; prompts 1.2–1.7× slower (four digits = four times the tensor work) |
| 8 | Two-digit contract (activations ±2¹⁴) — "loses only what is written, and is not slower" | Prompts 1.3–1.5× faster (all small cases ahead; XL 4–22% short) |
| 9 | Integer KV contract — attention on integer tensor cores with written exp, up to 130K positions | KV loss smaller than half-precision KV; long-context (synthetic 100K) prompts ahead |
| 10 | Tile and attention variants from first principles | All equal or slower — the limit of working without a profiler |
| 11 | Where Nsight Compute pointed: ldmatrix, π-ordered B operands, scale prefetch | XL prompts ahead of llama.cpp (0.86–0.95×) and PyTorch f16 (0.79–0.91×) for the first time |
| 12 | Overlap · attention · sustained use: split kernels for short chunks, constant-division lowering, per-head folding blocks in the megakernel, early garbage collection | Ahead of llama.cpp in every segment and window of a growing 100K-context conversation and a 2-minute XL run |
| 13 | Two-level fold (group = 1024 positions) — groups spread across blocks | All 23 long-context chunked-feeding cells ahead (0.68–0.91×; context 98K, chunk 16: 14.30 → 9.53 ms); real GPT-2 outputs bit-identical to stage 12. 13d (no regression) missed by about 1% in three cells |
| 14 | First chat model: Qwen2.5-0.5B-Instruct (Q8_0) — RMSNorm · RoPE · SwiGLU · GQA in the contract, a terminal runner | All rows of logits bit-identical to the CPU reference (beyond position 1024 too). Hidden loss (KL) 1/615 of llama.cpp's; prompts 0.55–0.82×, decode 0.80–0.87× — all five criteria passed |
| 15 | Generation megakernel: a whole token in one cooperative launch (GQA group attention, split two-level fold, waiting blocks warm L2 by real reads of the weights) | Decode 1.255 · 1.336 · 1.507 ms/token (chat prompt · context 1024 · 8192): 0.75–0.79× of stage 14, 0.63–0.65× of llama.cpp, 1.21× the floor. Logits and cache bit-identical to the decode graph at every step — all four criteria passed |
| 16 | PTX from geul's own compiler — stages 1–15 used a Python toolchain (reference front end + `글ptx.py`); a PTX backend written in geul inside the self-hosted compiler | The four stage-1 probe kernels: PTX byte-identical to the Python backend, 0 wrong values on the GPU — from geul source to GPU execution without Python. Real kernels stopped at the range-proof rule |
| 17 | Model kernels through the geul compiler — all remaining rules ported (range proofs, constant division, vectorized loads, tensor cores, async copies, half precision) | All 23 engine modules (GPT-2 ×22 + the 52 MB Qwen2 megakernel module) byte-identical to the Python backend on the first run; every stage-15 bit test passes with that PTX; compiling is 2.7× faster (149.5 vs 399.7 s) — all four criteria passed |
| 18 | The host in geul — GGUF loading, weight layout, RoPE tables (double-precision arithmetic), tokenizer (Unicode 15.0 tables · NFC · BPE), engine (kernel selection · graphs · megakernel), chat runner | The 266 KB runner imports only kernel32 · shell32 · nvcuda.dll and chats on a PATH without Python. Uploads, tokens, per-step logits, KV cache and conversations byte-identical to the Python host; speed 0.991–1.003× — all five criteria passed |
| 19 | The kernel generator in geul — the Qwen2 path of `커널생성.py` (2,395 lines, 72 functions) | The geul generator's `qwen2Q8.gl` is byte-identical to the Python version (107,417 lines, 6.8 MB); build → generate → PTX → chat from scratch with only the geul compiler + nvcuda.dll; generation 39 ms (Python 90 ms) — all three criteria passed |
| 20 | Quality: hidden loss seen as perplexity (a third-party review said "1/615 is easy to overstate") — wikitext-2 | 20a passed: the NLL sum of 584 chunks is bit-identical for every feeding mode (llama.cpp: PPL 15.8171–15.8200 depending on batch settings). 20b passed: PPL 15.763670 vs fp64 15.763774 (relative −6.6 × 10⁻⁶), KL 1/385. 20c "same order — the review is right": llama.cpp's hidden loss (KL 1.40 × 10⁻³, PPL +0.34%) is 1.95× the Q8_0 format loss (KL 7.20 × 10⁻⁴, PPL +0.24%) |
| 21 | 7B matmuls — does the two-digit contract's doubled tensor work show? Real Qwen2.5-7B Q8_0 layer-0 weights, GeulPU tiles vs llama.cpp's MMQ | 21a passed: 11 tile shapes agree with each other and the CPU reference (K up to 18944). 21b "it shows, but not 2×": 2048 rows 10.32 vs 8.63 ms (r 1.20), 8192 rows 63.2 vs 35.6 ms (r 1.77); GeulPU multiplies twice but uses 55–58% of int8 peak (llama.cpp 33–35%) |
| 22 | The whole 7B in geul — head-128 attention, a 7B module, prompts in 1024-row chunks, a CUDA graph per decoded token | 22a passed: new kernels and end-to-end (26,155,008 logits) 0 differences. 22b passed: five paths identical (2100 tokens too). 22c passed: 7B chat from one runner without Python. 22d: prompts r 1.14 · 1.30, decode r 1.054–1.070 ("slower" — the short-context cell missed 1.05 by 0.004) |
| 23 | 4-bit (Q4_0) in the contract, and the fixed cost of 7B decoding — new decode kernels with the same formulas and order | 23a/23b passed (106 kernel cases, end-to-end, five paths; Q8_0 byte-identical to stage 22). 23c passed: all six decode cells "same" — Q8_0 r 0.980–0.990, Q4_0 r 0.970–0.985 (1.11 · 1.16× the floor; llama.cpp 1.13–1.19×). 23d: Q4_0 prompts r 1.23 · 1.38. L2 prefetching was tried and removed |
| 24 | Model shapes from the GGUF config — `qwen2큰 <format> <width> <heads> <KV> <FFN> <vocab>`; real 14B; 32B · 72B shapes as 4-layer synthetic models | 24a–24d passed: modules unchanged, five models bit-exact, 14B decode r 0.982–0.994, prompts 1.22 · 1.34. A bug sizing Q4_0 buffers as Q8_0 was fixed |
| 25 | Layer split across GPUs — parts with their own CUDA contexts (emulated on one GPU), async hand-off, memory budget | 25a passed: 16 split runs byte-identical to one part. 25b passed. **25c not passed**: 7B two parts 1.0285 · 1.0285 · 1.0249 (within 1.03), but 14B two parts did not fit at context 8192 on 12 GB, so that cell was not measured. A shared context costs only 1.002–1.003× |
| Review | Contract-loss review — does a larger model show a sign that the contract must change? fp64 forward passes simulating only the rounding points (ground truth · contract · llama.cpp-like) | The simulation matches the measured 0.5B (1/637 vs 1/615). 7B · 14B: 1/3805 · 1/4467 — the contract's advantage grows with size. One pre-registered rule fired: attention probabilities (two digits per 32-key block) are at f16 level and worse than f16 in 12/28 (7B) · 34/48 (14B) layers, contributing 9% of the contract's KL at 7B. No contract change; long-context probabilities to be checked |
| 26 | k-quants (Q4_K · Q5_K · Q6_K) in the contract — the file's integers and scales as stored, per-tensor formats, a `qwen2K_{shape}` module | 26a passed: 243 kernel cases and three files end-to-end (26.16 M logits each) 0 differences. 26b passed. 26c passed: nine decode cells r 0.977–1.009 (1.13–1.17× the floor). 26d (record): prompts Q4_K_M 1.46 · 1.58, Q5_K_M 1.51 · 1.62, Q6_K 2.06 · 2.12. 14B Q4_K_M decode 1.009 · 1.012 |
| 27 | Prompt tiles: fill the tensor pipe (values unchanged). Nsight: tiles kept the tensor pipe 54–58% busy with 14–17 instructions per integer MMA, MMAs bunched by ptxas | 27a–27d passed. Q6_K: one m16n8k16 integer MMA per 16-value sub-block (new `정수텐서곱16` intrinsic in the geul PTX backend) with signed 4(q − 32) operands from a pre-arranged high-bit layout; a magic-number accumulator for Q4_0 · Q4_K; hoisted prefetch addressing in k-quant tiles. 349 kernel cases and three files end-to-end (26,155,008 logits each) 0 differences; five paths unchanged. Prompt time vs the stage-26 build (2048 · 8192): Q6_K 0.698 · 0.731, Q4_K_M 0.859 · 0.881, Q5_K_M 0.905 · 0.919, Q4_0 0.915 · 0.933, Q8_0 1.000 · 1.001; decode 0.991–1.003. Prompts vs llama.cpp: 1.13–1.30× (Q4_0 · Q8_0), 1.25–1.56× (k-quants). A chat record failed once: since stage 26 a worker thread built kernel names through the standard library's single formatting buffer while the main thread used it — fixed after the run |
| 28 | Server: an OpenAI-compatible HTTP API written in the geul language (Winsock, JSON, SSE), slots with continuous batching and prompt caching, a sampling contract (float64, a written exp, SplitMix64), and three "table" decode kernels that read each sequence's position and KV slot from a device table | 28a–28e passed. Over four models (7B Q4_0 · Q8_0 · Q4_K_M · 14B Q4_0), twelve requests sent alone, all at once, in reverse with random gaps and in duplicate gave identical tokens and per-step logit hashes; prompt-cache reuse equals no cache; 128 logit rows equal the one-shot engine path. The diagnosis found llama-server's greedy answer changing in 11 of 12 cases with concurrent requests. 24,000 sampler cases and 1,708 served sampling steps match the Python contract. One stream is 1.013× the engine alone; aggregate throughput 2.79× with four streams and 4.73× with eight. Versus llama-server: one stream 0.96×, four streams 1.20× and eight 1.25× the step time (record — no multi-row decode kernel yet) |
| 29 | Linux: same GPU, same bits. The geul compiler gained a Linux x86-64 target (geul D-50: ELF, System V for C calls, libc); GeulPU's OS layer (CUDA declarations → libcuda.so.1, file mapping → mmap, threads → pthread, sockets → BSD + poll) moved into files with a `호스트/리눅스/` counterpart, picked by the compiler's per-target include rule. Tested under WSL2 Ubuntu 24.04 on the same RTX 4070 Ti | 29a–29e passed. On Linux the reference implementation built the self-hosted compiler (149 ELF byte comparisons, fixpoint), which built the PTX backend, the kernel generator and the host programs; they import only libc.so.6 and libcuda.so.1. The six kernel modules made on Linux are byte-identical to the Windows ones. The six five-path summaries (7B Q8_0 · Q4_0 · Q4_K_M · Q5_K_M · Q6_K, 14B Q4_0) and the 0.5B 18d output are byte-identical to the Windows records; the Linux server passes the 13 API checks and its 28a tokens and per-step logit hashes equal the stage-28 Windows record (60 compared, 0 different). Windows is unchanged. Speed is within ~0.5% across the two systems (a 128-token prompt is 1.05× under WSL — record) |
| 30 | Prompt and first token: lighter tile-kernel loops (block scales copied asynchronously as halves, running pointers, the main loop unrolled by the stage count), deeper pipelines for the small tiles (2 → 5 · 6 · 8 stages), the server feeds a short cached remainder (≤ 4 rows) through the decode step, and a BPE piece cache in the tokenizer — values unchanged | 30a, 30b, 30d, 30e passed; 30c missed 3 of 25 cells. All kernels, the six five-path summaries and 18d are bit-identical to earlier records; the server's 28a matches the stage-28 record. 7B Q4_0 prompts of 32 · 128 · 512 · 2048 · 8192 tokens take 0.770 · 0.951 · 0.972 · 0.976 · 0.982× the stage-29 time; Q8_0 2048 · 8192 only 0.995 · 0.994 (criterion 0.99) and Q6_K at 32 tokens 0.958 (criterion 0.92) missed. Decoding is unchanged. The cached-prompt first token went from 28.8 to 13.8 ms (llama-server 13.0). Against the latest llama.cpp release (b11567) 7B Q4_0 prompts take 0.85× (32 tokens) to 1.27× (8192). The README's "not slower" was withdrawn: at equal optimization two-digit activations double the prompt matmul's integer tensor work |
| Cross-check | Does another PC give the same output? (DeepSeek-R1-Distill-Qwen-7B Q8_0, 32 math problems, greedy). One script (`교차검증/run.bat`) checks the environment, builds from source (each step's hash checked against the reference), generates and compares ([교차검증](../교차검증/)) | Same PC (1 vs 8 concurrent requests): llama.cpp b11567 gave identical outputs on 0/32 problems and changed 6 answers (accuracy 59.4% vs 50.0%); GeulPU 32/32. Other PC (RTX 5070, Blackwell, driver 596.21, Ryzen 5 7500F) vs reference (RTX 4070 Ti, Ada, 616.56, i7-14700K): all six build hashes identical, outputs 32/32 identical, tokens and per-step logit hashes identical for all 82,673 steps — pass. RTX 3080 Ti (Ampere, 616.92, i9-11900K) identical too — pass (three NVIDIA generations). Not yet: llama.cpp across machines, comparison with the CPU reference, non-NVIDIA GPUs |
| 31 (only 31j open) | Vulkan path — GeulPU on AMD GPUs. Two probes measured Vulkan's arithmetic rules and the contract's float32 rule became R (subnormal flush); then a SPIR-V backend in the geul compiler (same IR, same kernel sources as the PTX backend) and a Vulkan layer for the geul host (the CUDA driver API's names and signatures implemented over vulkan-1.dll) ([31단계](../문서/31단계.md)) | Probes: integer sums and fma are bit-identical to the CPU reference on NVIDIA and Intel Vulkan, only subnormals differ (31a missed, 31b passed); one rule R explains all four flushing paths (31d); Vulkan's division and square root are not correctly rounded (31e) — contract switched to R, outputs unchanged. 31f: values pass, NaN bit patterns do not. 31g passed — every kernel compiles to SPIR-V (only the cooperative-launch decode megakernel is left out); on NVIDIA all 282 · 243 · 480-case plate tests and the attention test match the CPU reference, on Intel (32 KB shared memory) every kernel that fits matches and the rest are logged as device limits; three NVIDIA driver issues (Aliased views, OpSRem, 64-bit division) are avoided in the backend. 31h passed — the geul host without nvcuda.dll reproduces the CUDA records byte for byte: 0.5B 18d and the six five-path summaries (7B Q8_0 · Q4_0 · Q4_K_M · Q5_K_M · Q6_K, 14B Q4_0) on NVIDIA, 0.5B 18d on Intel (a 32 KB module variant); long submissions hit the Windows GPU timeout (TDR), so the layer submits in pieces. 31i missed — against llama.cpp b11609 Vulkan, prompts take 4.4–6.1× (the backend emulates the integer MMA without tensor cores) and decode 1.09–1.24×. 31j (AMD) needs a card |
| 32 (in progress) | Fitting the device — GeulPU measures and chooses on the machine it runs on, to reach that machine's floor: self-diagnosis (floors, each kernel's distance to them, the plates the engine measured, the two builds alternated), a line-tile kernel for up to eight rows (the integer MMA operands swapped so nothing is padded; five variants, chosen by measurement on the device) and a per-device plate cache ([32단계](../문서/32단계.md)) | RTX 4070 Ti: read bandwidth 477.7 GB/s (94.8% of spec), integer tensor 317.5 TOPS. At eight rows the stage-31 plates spend 59–101 SM cycles of issue and 60 of tensor work per KB of weights; the devices with fewer cycles per KB (4070 Ti 318, RTX 5070 184, RTX 3080 Ti 150 at spec bandwidth and boost clock) were further from their floors in the same order. The line tile needs 39–43 and 15. Bits: 282 kernel cases (normal and extreme), the six five-path summaries, 0.5B 18d and R1's 82,673 steps unchanged (32a). 32b passed: alternated with the stage-31 build, every ratio is ≤ 1.01 — server decode step at position 2048, Q8_0, eight slots 0.942 (1.16 → 1.10× the floor) and four slots 0.844 (1.28 → 1.08×); with the line tile for Q4_0 as well, Q4_0 eight slots 0.788 (1.48 → 1.16×) and four slots 0.745; with line tiles for the three k-quant formats, Q4_K_M 0.720 · 0.675 and Q6_K 0.760 · 0.728; prompts and single-row decode 0.998–1.007. The cache cuts server load from 5.5 to 3.5 s. Pending: diagnosis and alternation on friends' PCs (32c, 32d) |

## What remains (after stage 31 — closed except 31j, 2026-10-14)

- 31j: the same checks (31f · 31g · 31h) on an AMD card.
- Vulkan speed (31i missed): prompts need the integer MMA mapped to cooperative matrices; decode first needs a lighter Vulkan layer (no
  barrier after every dispatch, fewer submissions, no re-recording of the decode graph). The measurement method changes too: one prompt per
  context, then many timed decode steps (the current method subtracts two runs that both contain the 8192-token prompt, which failed on Vulkan).
- Stage 33 (the price of the contract at equal optimization) was pre-registered and its one-digit variant built and verified, then stopped
  before timing: the same price had already been measured on 2026-10-13 in the same engine (two digits → one: prompts 1.26–1.38×, a lower
  bound; decode about 1.0×), and a price measured on an engine that has not reached its hardware floor says little.
- **Stage 34 — Vulkan speed**: the integer tensor op is emulated with subgroup shuffles and integer dot products; per-kernel timing
  showed the matrix products 4.6–10.9× and attention 7.2× slower than CUDA, everything else close. The SPIR-V backend gained
  cooperative-matrix instructions (16×16×32 integer products on tiles in shared memory, split per device shape — AMD's 16×16×16 too), and
  `커널생성 --협력` emits tile kernels with the same names, parameters and epilogues that use them. Attention's three products and the
  decode line kernels followed. On NVIDIA the "lane" kernels (`--레인 16x16`) read results straight from the cooperative-matrix
  components instead of a shared-memory round trip; the component order is implementation-defined, so such modules carry a check
  kernel that the engine runs at load and refuses on mismatch. Bit-exact throughout (plate tests 0 differences, head-128 attention 0,
  five paths byte-identical to the CUDA records). Further fixes: 64-bit division by an unproven divisor (a kernel parameter) was a
  64-step long-division loop in the SPIR-V backend — now a runtime check takes a 32-bit division when both values fit (RoPEKV went
  from 3× CUDA to equal); barriers between dispatches are compute-to-compute instead of all-commands (decode about 4% faster); "batch"
  tile kernels load S K-blocks at once and then multiply them (Vulkan has no async copy), used where every thread loads at least one
  B column; the backend no longer re-flushes subnormals for max/compare/negate inputs that are already flushed (results of arithmetic,
  max, int→float, flushed-only locals) — prompt attention −10%, checked bit-for-bit against the always-flush backend on NVIDIA and
  Intel. Measured alternately in one session, 7B on Vulkan takes 1.19–1.27× the CUDA path's prompt time (stage 31: 4.3–5.5×) and
  1.00–1.06× its decode time (stage 31: 1.09–1.27×; short-context decode varies about 3% between runs) — a record, not yet the verdict. Re-running the stage-31 model tests exposed a
  fixed 512-launch plan limit (14B with many split tiles) — now sized by layer count — and the cross-check's build hashes, stale since
  stage 33, were renewed after the R1 run matched all 82,673 logit hashes.
  An AMD cross-check (`교차검증/runV.bat` — a Vulkan device check, then one run each with the cooperative-matrix and the basic module)
  matches R1 32/32 · 82,673 steps of the CUDA reference with both modules on this PC's Vulkan. The first AMD report (RX 9060 XT) hit
  32 KB of shared memory and a 2 GiB single allocation, so a "shared32" kernel set (decode line kernels and attention within 32 KB — the
  same arithmetic) and per-layer weight allocation were added (the AMD-limit emulation matches 23b's five paths). On a friend's RX 9060 XT
  both modules (16×16×16 cooperative, basic) then matched R1 32/32 · 82,673 steps of the NVIDIA CUDA reference — the same bits on another
  vendor's GPU. Its speed is 3.3–3.7× the reference PC's Vulkan (attention, eight-row matrix products).
- Stage 32 waits for the diagnosis and alternation runs on friends' PCs (32c, 32d).
- **Stage 35 — AMD speed** (shared32 attention on cooperative matrices, line tiles fitted to 32 KB): 35a passed; 35b (AMD emulation on
  this PC) cut an eight-slot decode step from 44.3 to 22.2 ms; 35c waits for a friend's `speedV.bat` run ([35단계](../문서/35단계.md)).
- **Stage 36 — the GeulPU app.** 0.2.0: a manager written in geul (`GeulPU.exe`) with a web UI — model download (WinHTTP, resume,
  SHA-256) and adding GGUF files, chat (Qwen2.5, R1), self-diagnosis, speed and cross-check runs with result zips, versioning
  (`앱/판.gl`, `바뀐것.md`, an update notice) and a release CI (tag → draft release). The released server, generator and backends are
  byte-identical to the cross-check reference build. 0.3.0: redesigned on the x.ai design system through rounds of review by independent
  agents; the six other catalog files were downloaded through the app and all seven run on CUDA ([36단계](../문서/36단계.md)).
- **Stage 37 — Qwen3, the second model family.** Verification is per architecture · shape · format rather than per model (large shapes
  on synthetic models). Per-head Q/K RMSNorm became contract §4.6 and one kernel appended to the module (`머리정규화128` — every earlier
  kernel byte-identical); host, server (Qwen3 chat template, thinking on/off, `geulpu.special` to emit `<think>` tokens as text) and app
  accept qwen3. 37a passed: the norm kernel and three files end to end (Qwen3-1.7B Q8_0, 8B Q8_0, 8B Q4_K_M) show 0 differing logits
  against the CPU reference; Vulkan and the shared32 emulation are byte-identical to CUDA; two synthetic 14B-shape models also match.
  37b passed: five paths, the nine old modules and the 7B records unchanged, R1 cross-check CUDA 32/32 and Vulkan quick check — the build
  hashes in `expected.json` were renewed. 37c (decode speed ≤ 1.05× llama.cpp) was not measured officially: a one-run preview against
  b11567 gave r 0.982–1.007 (Q8_0) and 1.037–1.055 (Q4_K_M), and by the user's decision speed becomes its own stage. Bit tests ran on
  the same code before the commit, without an official run. App 0.4.0: Qwen3, a model finder that browses every Hugging Face GGUF repo
  sorted by trending, downloads, likes or recency (runnable models only by default, with a detail pane), and install/usage guides in
  Korean and English ([37단계](../문서/37단계.md)).

## What remains (after stage 30)

- 7B Q4_0 prompts take 0.85× (32 tokens) to 1.27× (8192) the time of the latest llama.cpp release (b11567). At equal optimization the
  contract's two-digit activations double the prompt matmul's integer tensor work, so most of the remaining gap above 128 tokens is the
  price of the precision the contract keeps, not an engineering shortfall; the README's "not slower" was withdrawn.
- Next, stage 31 measures what determinism itself costs: a one-digit activation contract (llama.cpp-level precision) plus the same kernels
  with each constraint (bit-equality with the CPU reference, determinism) switched on and off. Then a comparison with vLLM's batch-invariant
  and SGLang's deterministic modes, multi-stream decoding, and MoE.
- Left from stage 30: an attention rewrite (31% of an 8192-token prompt), unsigned Q4_0 nibbles with a per-block activation sum, and the
  Q8_0 tiles (long prompts only 0.995×).

## What remains (after stage 29)

- A GPU run on native Linux (a real Linux machine with the NVIDIA driver) — this PC only has WSL2. ARM64 and macOS have no geul target.
- Linux distributables (geul 1.4.0, a GeulPU Linux build bundle) — after the user's approval.
- The cached first token jitters on Windows only (28.7–53.3 ms; ~29 ms on Linux) — the server loop's wait is looked at in stage 30.
- Next: stage 30 prompts (first token, long-context attention, instruction count in the matmul tiles), stage 31 the step time of
  concurrent streams, then MoE.

## What remains (after stage 28)

- **Prompt speed.** The two-digit contract does twice the integer tensor work of 8-bit activations; the remaining gap is in the tile
  kernels' epilogue cost and MMA scheduling. CPU-only SASS analysis (the CI's ptxas step) shows the head-128 prompt attention kernel spills
  1,092 bytes per thread — the next lever for long prompts. Precomputing per-row activation sums would remove the Q4_K · Q5_K
  T-sum MMAs (an upper-bound experiment: 3–5%).
- **Decode** is at parity with llama.cpp and 1.11–1.17× the bandwidth floor; the remaining distance is in small matmuls, per-layer small
  kernels and attention at 8192.
- **Server throughput with several streams.** Four and eight concurrent streams take 1.20× and 1.25× llama-server's step time on 7B Q4_0:
  the decode GEMVs for 2–4 rows reuse an older kernel and k-quants fall back to tile kernels. A multi-row version of the async-copy row
  kernel is stage 29.
- **Formats and models**: Q2_K · Q3_K · IQ · Q5_0 (needed for real 72B k-quant files), official k-quant files, MoE.
- **Linux**: a Linux x86-64 target for the geul compiler (ELF, System V calls to libc, a Linux standard-library layer) is in progress;
  GeulPU's host layer (file mapping, threads, sockets, libcuda.so.1) comes after it.
- **Reproduction** on other GPUs; real multi-GPU layer split; measuring the contract's loss with the real engine on 7B+.
