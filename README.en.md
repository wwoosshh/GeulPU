# GeulPU — a GPU inference engine that keeps meaning

*English README. The Korean original is [README.md](README.md); English documents live in [docs/](docs/). The code and most stage
reports are written in Korean — see the [glossary](docs/glossary.md) for the terms.*

GeulPU is a large-language-model inference engine whose GPU kernels are written in **geul (글)** — a Korean programming language —
and compiled to PTX by geul's own self-hosted compiler, then loaded straight into the NVIDIA driver. It runs without the CUDA toolkit,
cuBLAS or PyTorch: the chat runner is a single executable that imports only `kernel32`, `shell32` and `nvcuda.dll`.

> It loses only what is written down, and it is not slower.

## What is different

- **Precision is a written contract.** Activations are integers per 32-value block (two balanced base-256 digits, ±2¹⁴ of the block
  maximum), the KV cache is block integers too, products are summed exactly on integer tensor cores, and exp is a written polynomial.
  Every rounding point is fixed in the source, so the GPU result is **bit-identical** to the CPU reference implementation
  ([`계약/정수계약.py`](계약/정수계약.py)). The only losses are the model file's own quantization and the roundings the contract writes
  down — see [docs/contract.md](docs/contract.md).
- **The same bits whichever way it computes.** Feeding a prompt at once, in pieces, one token at a time, as a continuing conversation,
  or batched with other sentences gives identical results. Common engines change output bits with the amount of work computed
  together: llama.cpp's wikitext-2 perplexity varies from 15.8171 to 15.8200 with batch settings, while GeulPU gives the same value to
  the last bit for every way of feeding the text (stage 20).
- **Fast where it matters most, and honest about where it is not.** On one RTX 4070 Ti:
  - Qwen2.5-0.5B-Instruct (Q8_0): prompts of 128–8192 tokens take 0.55–0.82× llama.cpp's time; decoding takes 0.63–0.65× (a generation
    megakernel — 1.26 ms/token, 1.21× the floor of reading the weights once). Its hidden loss (KL against an fp64 forward pass of the same
    weights) is 1/615 of llama.cpp's (a 461-token evaluation text) and 1/385 (wikitext-2, 148,920 tokens); its perplexity is
    indistinguishable from fp64 (relative −6.6 × 10⁻⁶), while llama.cpp's is 0.34% higher — the same order as the Q8_0 weight quantization
    itself (0.24%).
  - Qwen2.5-7B / 14B (Q8_0 · Q4_0 · k-quants): decoding is at parity with llama.cpp (0.970–1.012× its time), 1.11–1.17× the bandwidth
    floor (llama.cpp: 1.13–1.19×). Prompts are slower: 1.15–1.38× for Q8_0 · Q4_0 and 1.46–2.12× for k-quants as of stage 26. The two-digit activations
    double the integer tensor-core work of 8-bit activations; stage 27 (in progress) narrows the gap — see the
    [research log](docs/research-log.md).
- **Larger models keep the advantage.** A simulation that reproduces only the rounding points (validated against the measured 0.5B value:
  1/637 simulated vs 1/615 measured) gives a hidden loss of 1/3805 (7B Q8_0) and 1/4467 (14B Q4_0) of a llama.cpp-like pipeline.

## Status (2026-10)

| | |
|---|---|
| Models | **Qwen2.5-0.5B / 7B / 14B-Instruct** (chat; Llama-family blocks — RMSNorm · RoPE · SwiGLU · GQA; head sizes 64 and 128). Head-128 Qwen2 shapes are read from the GGUF config; 32B and 72B shapes were bit-tested on 4-layer synthetic models. GPT-2 small and XL (research engine). |
| Weight formats | GGUF **Q8_0 · Q4_0 · Q4_K · Q5_K · Q6_K**, including per-tensor mixes as in Q4_K_M · Q5_K_M (stage 26 — tested with files re-quantized on this PC from Q8_0; official Qwen files are not yet tested). |
| Runner | `빌드/글/실행기.exe model.gguf` (`실행기` = runner) — a geul program: ChatML chat, streamed output, KV cache reused across turns, greedy decoding (the same conversation gives the same answer). About 0.3 s until the prompt runs. |
| Environment | Windows + NVIDIA Ampere (RTX 30) or newer + driver. All numbers here are from one RTX 4070 Ti (12 GB). Building (generator → kernel source → PTX → runner) needs only the geul compiler. Tests and benchmarks need Python 3.12 + numpy. |
| Layer split | Stage 25 — split layers across GPUs (`--나누기 P` parts, `--장치 a,b,…` devices, `--예산 GB` budget). Emulated on one GPU with one CUDA context per part: 16 split runs are bit-identical to the single-part run; decoding with two parts takes 1.025–1.029× (mostly the emulation's context switching; 1.002–1.003× with a shared context). 14B in two parts did not fit at context 8192 on 12 GB, so that pre-registered cell was not measured (criterion 25c not passed). |
| Not yet | Real multi-GPU runs; measuring the contract's loss with the real engine on 7B+ (done for 0.5B; simulated for 7B · 14B); Q2_K · Q3_K · IQ formats · Q5_0 (real 72B k-quant files use Q5_0 · Q8_0 for ffn_down); MoE; sampling (greedy only); server features; Linux; reproduction on another GPU. |

## Repository layout

| Folder | What |
|---|---|
| [`커널/`](커널/) (kernels) | `커널생성.gl` + `생성*.gl` — the kernel generator written in geul; it emits geul kernel source for every module. `커널생성.py` — the legacy Python generator (GPT-2, reference). |
| [`호스트/`](호스트/) (host) | geul programs: `실행기.gl` (runner), `엔진.gl` (engine: kernel selection, CUDA graphs, decoding), `가중치*.gl` (GGUF weight layout), `로프.gl` (RoPE tables in double-precision arithmetic), `토크나이저.gl` (Unicode 15.0 tables, NFC, BPE), `조각.gl` (layer split), tests and benchmarks. |
| [`계약/`](계약/) (contract) | `정수계약.py` — the CPU reference implementation of the contract; every bit comparison is against it. |
| [`시험/`](시험/) (tests) | Bit tests (every kernel vs the CPU reference, paths vs each other, end-to-end), the quick check (`빠른점검.py`). |
| [`재기/`](재기/) (benchmarks) | Speed comparisons with llama.cpp (b11496 CUDA) and PyTorch; result collectors. |
| [`공식실행/`](공식실행/) (official runs) | The scripts that produced each stage's verdicts, kept as they were run. |
| [`문서/`](문서/) (documents) | Korean stage reports and the contract. English: [`docs/`](docs/). |
| [`엔진/`](엔진/) · [`컴파일러/`](컴파일러/) | Legacy Python host and Python PTX backend, kept for comparison. |

## Quick start

1. **Requirements**: Windows and an NVIDIA driver (Ampere or newer). For chat, this and the geul compiler are enough. Tests and benchmarks
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

## Checks

[![Quick check](https://github.com/wwoosshh/GeulPU/actions/workflows/ci.yml/badge.svg)](https://github.com/wwoosshh/GeulPU/actions/workflows/ci.yml)

- **Quick check on every push** — GitHub Actions, Windows runner, no GPU and no model files, about 5 minutes
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
[`문서/`](문서/). A short technical brief for outside reviewers: [docs/brief.md](docs/brief.md).

## License

MIT — [LICENSE](LICENSE). The copy of the geul front end (`컴파일러/ref/`) is MIT by the same author.
