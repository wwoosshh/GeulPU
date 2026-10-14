# GeulPU — a GPU inference engine that keeps meaning

*English README. The Korean original is [README.md](README.md); English documents live in [docs/](docs/). The code and most stage
reports are written in Korean — see the [glossary](docs/glossary.md) for the terms.*

GeulPU is a large-language-model inference engine whose GPU kernels are written in **geul (글)** — a Korean programming language —
and compiled to PTX by geul's own self-hosted compiler, then loaded straight into the NVIDIA driver. It runs without the CUDA toolkit,
cuBLAS or PyTorch: the chat runner is a single executable that imports only `kernel32`, `shell32` and `nvcuda.dll`.

> It loses only what is written down — and it shows what losing less costs.

## Use the app (0.2.0 — stage 36)

No git, Python, build or scripts:

1. Download `GeulPU-<version>-windows-x64.zip` from [Releases](https://github.com/wwoosshh/GeulPU/releases) and unzip it anywhere.
2. Run `GeulPU.exe`; your browser opens `http://127.0.0.1:44544` (local only; closing the console window stops GeulPU).
   The executable is unsigned — if "Windows protected your PC" appears, choose *More info* → *Run anyway*.
3. **Models** — download from the list (file, source and size are shown before anything is fetched; resumable; SHA-256 verified)
   or add a GGUF you already have.
4. **Chat** — pick a model per conversation and talk (streaming, stop). The first run builds kernels for your GPU (seconds).
5. **Bench & verify** — self-diagnosis, speed (prompt and generation tokens/s) and the cross-check (32 R1 problems compared bit for bit
   with the reference PC). Results download as a zip.

NVIDIA RTX 30 and newer run on CUDA, other GPUs (AMD, …) on Vulkan (switchable in Settings). Models, kernels and results live in
`%USERPROFILE%\GeulPU` and survive upgrades. Other programs can use `http://127.0.0.1:44544/v1` (OpenAI-compatible). The manager
(`GeulPU.exe`) is written in geul too and imports only Windows DLLs (kernel32, ws2_32, shell32, winhttp, bcrypt, advapi32). Releases are
built from source by CI when a tag is pushed; their server, generator and backends are byte-identical to the cross-check reference build
(checked by `앱/꾸리기.ps1`). Changes: [바뀐것.md](바뀐것.md) (Korean); how it was built: [stage 36](문서/36단계.md) (Korean).

## What is different

- **Precision is a written contract.** Activations are integers per 32-value block (two balanced base-256 digits, ±2¹⁴ of the block
  maximum), the KV cache is block integers too, products are summed exactly on integer tensor cores, and exp is a written polynomial.
  Every rounding point is fixed in the source, so the GPU result is **bit-identical** to the CPU reference implementation
  ([`계약/정수계약.py`](계약/정수계약.py)). The only losses are the model file's own quantization and the roundings the contract writes
  down — see [docs/contract.md](docs/contract.md).
- **The same bits whichever way it computes.** Feeding a prompt at once, in pieces, one token at a time, as a continuing conversation,
  or batched with other sentences gives identical results. Common engines change output bits with the amount of work computed
  together: llama.cpp's wikitext-2 perplexity varies from 15.8171 to 15.8200 with batch settings, while GeulPU gives the same value to
  the last bit for every way of feeding the text (stage 20). Across GPUs too: an RTX 3080 Ti (Ampere), an RTX 4070 Ti (Ada) and an RTX 5070
  (Blackwell) gave bit-identical outputs and per-step logits (82,673 steps) on 32 math problems with DeepSeek-R1-Distill-Qwen-7B, while llama.cpp's
  outputs all changed with the number of concurrent requests on one PC ([교차검증](교차검증/)).
- **A small hidden loss — measured on 0.5B.** Qwen2.5-0.5B-Instruct (Q8_0): the hidden loss (KL against an fp64 forward pass of the same
  weights) is 1/615 of llama.cpp's (a 461-token evaluation text) and 1/385 (wikitext-2, 148,920 tokens); its perplexity is
  indistinguishable from fp64 (relative −6.6 × 10⁻⁶), while llama.cpp's is 0.34% higher — the same order as the Q8_0 weight quantization
  itself (0.24%). How this was measured: [docs/hidden-loss.md](docs/hidden-loss.md). 7B and 14B were not measured with the real engine
  (see the simulation below).
- **Speed — decoding at parity; compute-bound prompts pay for the extra precision.** On one RTX 4070 Ti:
  - Qwen2.5-7B / 14B (Q8_0 · Q4_0 · k-quants) decode at parity with llama.cpp (0.970–1.012× its time), 1.11–1.17× the bandwidth floor
    (llama.cpp: 1.13–1.19×). Decoding is bound by reading the weights, so the extra arithmetic hides behind it.
  - Prompts are faster only when short: 7B Q4_0 takes 0.85× (32 tokens), 1.03× (128), 1.11× (2048) and 1.27× (8192) the time of the latest
    official llama.cpp release (b11567, same GGUF), Q8_0 0.85–1.30× and k-quants 0.95–1.56× (same run, stage 30). At equal optimization the two-digit activations double
    the integer tensor-core work of llama.cpp's 8-bit activations, and the attention's exact sums and written exp add more; the ratio grows
    with length because of the attention.
  - The 0.5B results (prompts of 128–8192 tokens at 0.55–0.82× llama.cpp's time, decoding at 0.63–0.65× with a generation megakernel)
    and GPT-2 XL (prompts at 0.78–0.87×) come from kernel engineering — fusion and a megakernel — not from the contract being free.
  - The old motto's "it is not slower" was withdrawn in stage 30. The price at equal optimization was measured on 2026-10-13 by switching
    constraints off in the same engine (in a scratch folder; the raw data is not in this repository). Two activation digits → one in the
    tile kernels: 7B Q4_0 prompts of 512 / 2048 / 8192 tokens took 1.38 / 1.35 / 1.26× (a lower bound: epilogues and the attention's q
    keep two digits). Written exponent → approximate exponent: almost free. Decode: about 1.0× (weight reads dominate). Determinism alone
    could not be isolated. Stage 33 (a formal re-measurement) was stopped for that reason.
  - Now: stage 34, Vulkan speed — the emulated integer tensor op became cooperative-matrix tensor-core work in the tile kernels,
    attention and the decode line kernels; the SPIR-V backend's division and subnormal flushing (no re-flush of values already flushed), the
    Vulkan layer's barriers and the tile kernels' loading were fixed. All bit-exact (CPU reference, CUDA records byte for byte). Measured alternately in one session, 7B on Vulkan takes 1.19–1.27×
    the CUDA path's prompt time (stage 31: 4.3–5.5×) and 1.00–1.06× its decode time (stage 31: 1.09–1.27×; short-context decode varies
    about 3% between runs); prompt tile kernels and short prompts (128 rows: 1.39–1.47×) remain ([stage 34](문서/34단계.md), Korean). Stage 31 (Vulkan): the geul host runs on vulkan-1.dll alone and reproduces the CUDA records byte for byte on NVIDIA and on Intel
    integrated graphics; on a friend's AMD Radeon RX 9060 XT (RDNA4) the 7B R1 run matched the NVIDIA CUDA reference in all 82,673 steps
    (stage 34). Stage 32 (self-tuning to the device's floor) waits for runs on
    friends' PCs. See the [research log](docs/research-log.md).
- **Larger models keep the advantage.** A simulation that reproduces only the rounding points (validated against the measured 0.5B value:
  1/637 simulated vs 1/615 measured) gives a hidden loss of 1/3805 (7B Q8_0) and 1/4467 (14B Q4_0) of a llama.cpp-like pipeline.

## Status (2026-10)

| | |
|---|---|
| Models | **Qwen2.5-0.5B / 7B / 14B-Instruct** (chat; Llama-family blocks — RMSNorm · RoPE · SwiGLU · GQA; head sizes 64 and 128). Head-128 Qwen2 shapes are read from the GGUF config; 32B and 72B shapes were bit-tested on 4-layer synthetic models. GPT-2 small and XL (research engine). |
| Weight formats | GGUF **Q8_0 · Q4_0 · Q4_K · Q5_K · Q6_K**, including per-tensor mixes as in Q4_K_M · Q5_K_M (stage 26 — tested with files re-quantized on this PC from Q8_0; official Qwen files are not yet tested). |
| Runner | `빌드/글/실행기.exe model.gguf` (`실행기` = runner) — a geul program: ChatML chat, streamed output, KV cache reused across turns, greedy decoding (the same conversation gives the same answer). About 0.3 s until the prompt runs. |
| Server | `빌드/글/서버.exe model.gguf` (`서버` = server) — a geul program (stage 28): an OpenAI-compatible HTTP API (chat · completions · SSE streaming) with slots, continuous batching, prompt caching and a sampling contract (the same seed gives the same tokens). A request returns the same bits whatever else runs with it — zero differences over four models × twelve requests × four schedules, while llama-server's greedy answer changed in 11 of 12 cases depending on the concurrent requests. Head-128 Qwen2 (7B · 14B). 7B Q4_0 aggregate throughput: 302 tokens/s with four streams and 508 with eight (llama-server 360 · 632 — a multi-row decode kernel is next); one stream is 4% faster than llama-server. A cached prompt's first token takes 13.8 ms (llama-server 13.0 ms; stage 30 feeds the last rows through the decode step). See [`문서/28단계.md`](문서/28단계.md) · [`문서/30단계.md`](문서/30단계.md) |
| Environment | Windows or Linux x86-64 (glibc) + NVIDIA Ampere (RTX 30) or newer + driver. Linux was tested under WSL2 Ubuntu 24.04 in stage 29 — the same bits as Windows on the same GPU, speed within ~0.5% ([`문서/29단계.md`](문서/29단계.md)). On Linux the programs import only libc.so.6 and libcuda.so.1. All numbers here are from one RTX 4070 Ti (12 GB). Building (generator → kernel source → PTX → runner) needs only the geul compiler. Tests and benchmarks need Python 3.12 + numpy. **Vulkan (stage 31):** Vulkan builds of the geul host (`시험_엔진V` · `시험_7BV` · `재기_7BV` — they import kernel32, shell32 and vulkan-1.dll; kernels come from the geul compiler's SPIR-V backend) reproduce the CUDA records byte for byte on NVIDIA (0.5B, 7B in five formats, 14B) and Intel integrated graphics (0.5B). Speed is not there yet — stage 34 replaced the emulated integer MMA with cooperative-matrix tensor-core work (`--협력` modules) and fixed the backend and the Vulkan layer: 7B prompts take 1.15–1.41× llama.cpp Vulkan's time (stage 31: 4.4–6.1×), decode 1.00–1.04× (stage 31: 1.09–1.24×) — a record, not yet a verdict. No Vulkan build of the runner or the server yet. |
| Layer split | Stage 25 — split layers across GPUs (`--나누기 P` parts, `--장치 a,b,…` devices, `--예산 GB` budget). Emulated on one GPU with one CUDA context per part: 16 split runs are bit-identical to the single-part run; decoding with two parts takes 1.025–1.029× (mostly the emulation's context switching; 1.002–1.003× with a shared context). 14B in two parts did not fit at context 8192 on 12 GB, so that pre-registered cell was not measured (criterion 25c not passed). |
| Not yet | Real multi-GPU runs; measuring the contract's loss with the real engine on 7B+ (done for 0.5B; simulated for 7B · 14B); Q2_K · Q3_K · IQ formats · Q5_0 (real 72B k-quant files use Q5_0 · Q8_0 for ffn_down); MoE; a GPU run on native Linux (tested under WSL2 only); running on Apple GPUs (three NVIDIA generations and an AMD Radeon RX 9060 XT (RDNA4, Vulkan) match bit for bit — [교차검증](교차검증/); AMD speed (RX 9060 XT generation is about 3× slower than an RTX 4070 Ti, mostly attention); Intel integrated graphics matches through Vulkan for 0.5B — stage 31). |

## Repository layout

| Folder | What |
|---|---|
| [`커널/`](커널/) (kernels) | `커널생성.gl` + `생성*.gl` — the kernel generator written in geul; it emits geul kernel source for every module. `커널생성.py` — the legacy Python generator (GPT-2, reference). |
| [`호스트/`](호스트/) (host) | geul programs: `실행기.gl` (runner), `엔진.gl` (engine: kernel selection, CUDA graphs, decoding), `가중치*.gl` (GGUF weight layout), `로프.gl` (RoPE tables in double-precision arithmetic), `토크나이저.gl` (Unicode 15.0 tables, NFC, BPE), `조각.gl` (layer split), tests and benchmarks. |
| [`계약/`](계약/) (contract) | `정수계약.py` — the CPU reference implementation of the contract; every bit comparison is against it. |
| [`시험/`](시험/) (tests) | Bit tests (every kernel vs the CPU reference, paths vs each other, end-to-end), the quick check (`빠른점검.py`). |
| [`재기/`](재기/) (benchmarks) | Speed comparisons with llama.cpp (the latest official release at measurement time — b11496 through stage 29, b11567 from stage 30; CUDA) and PyTorch; result collectors. |
| [`공식실행/`](공식실행/) (official runs) | The scripts that produced each stage's verdicts, kept as they were run. |
| [`문서/`](문서/) (documents) | Korean stage reports and the contract. English: [`docs/`](docs/). |
| [`엔진/`](엔진/) · [`컴파일러/`](컴파일러/) | Legacy Python host and Python PTX backend, kept for comparison. |

## Quick start

1. **Requirements**: Windows or Linux x86-64 (glibc — see 7 below) and an NVIDIA driver (Ampere or newer). For chat, this and the geul compiler are enough. Tests and benchmarks
   also need Python 3.12 and `pip install -r requirements.txt`.
2. **geul compiler and PTX backend**: clone the `research/gpu` branch of the geul repository next to this one as `../geul-lang-v2` (the
   exact commit used is in [`시험/글저장소커밋.txt`](시험/글저장소커밋.txt)) and build the self-hosted compiler and the PTX backend:
   ```
   git clone -b research/gpu https://github.com/wwoosshh/geul-lang ../geul-lang-v2
   cd ../geul-lang-v2
   python build.py selfhost 컴파일러
   GEUL_ROOT=. build/self_컴파일러.exe research/gpu/자체PTX/PTX.gl -o build/자체PTX.exe
   ```
   (`python build.py selfhost 컴파일러` builds the compiler with the Python reference implementation and checks the self-hosting fixpoint;
   `python ref/geulc.py self/컴파일러.gl -o build/self_컴파일러.exe` only builds it. The released `geulc.exe` of geul 1.2.1 produces
   byte-identical executables and needs no Python.)
3. **Chat**: download `qwen2.5-0.5b-instruct-q8_0.gguf` (676 MB) from Hugging Face `Qwen/Qwen2.5-0.5B-Instruct-GGUF`. Build the generator and
   the runner, generate the kernel module, compile it to PTX next to the runner, and chat:
   ```
   mkdir -p 빌드/글
   GEUL_ROOT=../geul-lang-v2 ../geul-lang-v2/build/self_컴파일러.exe 커널/커널생성.gl -o 빌드/글/커널생성.exe
   GEUL_ROOT=../geul-lang-v2 ../geul-lang-v2/build/self_컴파일러.exe 호스트/실행기.gl -o 빌드/글/실행기.exe
   빌드/글/커널생성.exe qwen2Q8 빌드/글/qwen2Q8.gl
   ../geul-lang-v2/build/자체PTX.exe 빌드/글/qwen2Q8.gl -o 빌드/글/qwen2Q8.ptx
   빌드/글/실행기.exe qwen2.5-0.5b-instruct-q8_0.gguf
   ```
   One line of input is one turn; `/새로` starts a new conversation and `/끝` quits.
4. **Larger models** need their module. The runner reads the GGUF config and looks for the module named after the shape; if it is missing
   it prints the command. Examples:
   ```
   빌드/글/커널생성.exe qwen2Q8_7b 빌드/글/qwen2Q8_7b.gl                                   # 7B Q8_0
   빌드/글/커널생성.exe qwen2Q4_7b 빌드/글/qwen2Q4_7b.gl                                   # 7B Q4_0 (all tensors Q4_0: llama-quantize --pure)
   빌드/글/커널생성.exe qwen2큰 Q4_0 5120 40 8 13824 152064 빌드/글/qwen2Q4_5120x40x8x13824x152064.gl   # 14B Q4_0
   빌드/글/커널생성.exe qwen2큰 K 3584 28 4 18944 152064 빌드/글/qwen2K_3584x28x4x18944x152064.gl      # 7B k-quants
   ```
   then compile each `.gl` with `자체PTX.exe` as above. `qwen2큰 <format> <width> <heads> <KV heads> <FFN width> <vocab>` covers head-128
   Qwen2 shapes; format `K` builds one module holding the Q4_K · Q5_K · Q6_K kernels.
5. **Multiple GPUs** (layer split): `빌드/글/실행기.exe model.gguf --장치 0,1` (one part per device), `--예산 GB` to fill devices up to a
   memory budget, `--나누기 P` to emulate P parts on one GPU. Only the one-GPU emulation has been tested.
6. **Server** (stage 28, head-128 Qwen2: 7B · 14B): a program written in the geul language that serves an OpenAI-compatible HTTP API. It
   imports only the runner's three DLLs plus Windows sockets (`ws2_32.dll`). It serves several requests at once (continuous batching over
   slots), and a request returns the same bits whatever else runs with it. It uses the same modules as the runner; from stage 28 the
   head-128 modules contain the server's table kernels, so rebuild modules made by earlier stages.
   ```
   GEUL_ROOT=../geul-lang-v2 ../geul-lang-v2/build/self_컴파일러.exe 호스트/서버.gl -o 빌드/글/서버.exe
   빌드/글/서버.exe qwen2.5-7b-instruct-q4_0-pure.gguf --슬롯 4 --문맥 4096 --포트 8080
   ```
   - Endpoints: `GET /health`, `GET /v1/models`, `POST /v1/chat/completions`, `POST /v1/completions` (`"stream": true` streams SSE).
   - Fields: OpenAI's `messages`, `prompt` (text or token ids), `max_tokens`, `temperature`, `top_p`, `seed`, `stop`,
     `stream_options.include_usage`, plus llama.cpp's `top_k`, `min_p`, `ignore_eos`, `cache_prompt`.
   - Sampling follows [the contract](docs/contract.md), section 5. The same seed gives the same tokens, and a request without a seed can
     be replayed from `geulpu.seed` in the response.
   - Clients that speak the OpenAI API connect with base URL `http://127.0.0.1:8080/v1`. Only the Python standard library and curl were
     tested as clients.
   - The server listens on 127.0.0.1 by default and has no authentication.
7. **Linux** (stage 29 — x86-64 · glibc, tested under WSL2 Ubuntu 24.04): build the same sources with the geul compiler's Linux target —
   the executables are extension-less ELF files importing only `libc.so.6` and `libcuda.so.1`, and the kernel modules (source and PTX) are
   byte-identical to the ones made on Windows.
   ```
   cd ../geul-lang-v2 && python3 build.py selfhost 컴파일러          # on Linux the compiler itself is an ELF (build/self_컴파일러)
   GEUL_ROOT=. build/self_컴파일러 research/gpu/자체PTX/PTX.gl -o build/자체PTX
   cd ../GeulPU && mkdir -p 빌드/글리눅스
   GEUL_ROOT=../geul-lang-v2 ../geul-lang-v2/build/self_컴파일러 커널/커널생성.gl -o 빌드/글리눅스/커널생성
   GEUL_ROOT=../geul-lang-v2 ../geul-lang-v2/build/self_컴파일러 호스트/실행기.gl -o 빌드/글리눅스/실행기
   빌드/글리눅스/커널생성 qwen2Q8 빌드/글리눅스/qwen2Q8.gl
   ../geul-lang-v2/build/자체PTX 빌드/글리눅스/qwen2Q8.gl -o 빌드/글리눅스/qwen2Q8.ptx
   빌드/글리눅스/실행기 qwen2.5-0.5b-instruct-q8_0.gguf
   ```
   The server is the same (`호스트/서버.gl`). Under WSL2 the Windows driver provides `/usr/lib/wsl/lib/libcuda.so.1`. Linux binaries can
   also be built on Windows with the compiler's `--대상 리눅스` (the bytes equal those built on Linux). A GPU run on native Linux has not
   been done yet.

## Checks

[![Quick check](https://github.com/wwoosshh/GeulPU/actions/workflows/ci.yml/badge.svg)](https://github.com/wwoosshh/GeulPU/actions/workflows/ci.yml)

- **Quick check on every push** — GitHub Actions, a Windows runner and (from stage 29) an Ubuntu runner, no GPU and no model files, about 5 minutes
  ([`시험/빠른점검.py`](시험/빠른점검.py); the same command runs locally). The geul compiler is a CPU program, so everything up to PTX can be
  produced without a GPU: the check builds the geul compiler and PTX backend at the pinned geul commit, builds the generator and all 15
  host programs, regenerates six kernel modules from scratch and compares source and PTX byte for byte with
  [`시험/모듈해시.txt`](시험/모듈해시.txt), assembles every module to SASS for sm_89 with NVIDIA `ptxas` (a checker only — the engine does
  not use it) and fails on new or larger register spills ([`시험/SASS넘침.txt`](시험/SASS넘침.txt)), runs the contract's CPU self-tests
  (fma against exact rational arithmetic, slow vs BLAS references, an independent per-value dequantizer), checks that the tile tables agree
  across generator, host and tests, and that the runner imports only `kernel32`, `shell32` and `nvcuda`. The first CI run reproduced the
  local compiler, PTX backend and all module bytes exactly. Details: [docs/reproduce.md](docs/reproduce.md).
- **Official runs per stage** — GPU (`공식실행/`): kernel, path and end-to-end bit comparisons and speed. Criteria are written and
  committed before the results.

## Research log

The engine came out of a research program started on 2026-10-08: stages 0–13 in the `research/gpu` branch of the geul repository, stage
14 onward here. Every stage commits its pass/fail criteria before measuring, compares every variant bit for bit before timing it, and
keeps failures and missed criteria. English summary: [docs/research-log.md](docs/research-log.md). Korean stage reports:
[`문서/`](문서/). A short technical brief for outside reviewers: [docs/brief.md](docs/brief.md). What the geul compiler caught and
missed over stages 1–27, counted case by case: [docs/compiler-catches.md](docs/compiler-catches.md).

## License

MIT — [LICENSE](LICENSE). The copy of the geul front end (`컴파일러/ref/`) is MIT by the same author.
