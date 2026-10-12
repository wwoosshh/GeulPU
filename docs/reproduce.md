# Reproducing GeulPU's results

*How to rebuild everything from source, run the GPU-free quick check, and re-run the GPU bit tests and benchmarks. Korean details are in
[`공식실행/README.md`](../공식실행/README.md) and the stage reports in [`문서/`](../문서/).*

## 1. Toolchain

- Windows 10/11 x64. (Everything is built by the geul compiler, which emits Windows PE executables directly.)
- The geul repository's `research/gpu` branch next to this repository as `../geul-lang-v2`, at the commit in
  [`시험/글저장소커밋.txt`](../시험/글저장소커밋.txt). Build its self-hosted compiler and the PTX backend:
  ```
  cd ../geul-lang-v2
  python ref/geulc.py self/컴파일러.gl -o build/self_컴파일러.exe        # or: python build.py selfhost 컴파일러 (also checks the fixpoint)
  GEUL_ROOT=. build/self_컴파일러.exe research/gpu/자체PTX/PTX.gl -o build/자체PTX.exe
  ```
  At commit 906b8cc these are byte-identical everywhere we have built them (SHA-256 `bd8f3381…` and `7181aead…`).
- Python 3.12 and `pip install -r requirements.txt` (numpy) for tests and benchmarks. Run Python with `-X utf8`.
- Paths: the repository uses Korean folder names. NVIDIA `ptxas` cannot open a path with characters outside the system's ANSI code page
  (Korean on an English-locale Windows), so the quick check copies PTX to an ASCII temporary folder before calling it. Nsight Compute
  fails to start when installed under a path with Korean characters, even on Korean-locale Windows — run it from an ASCII install path.

## 2. Quick check — no GPU, no model files (about 5 minutes)

```
python -X utf8 시험/빠른점검.py [--글 ../geul-lang-v2] [--ptxas <ptxas.exe>] [--병렬 N]
```

This is exactly what CI runs on every push ([`.github/workflows/ci.yml`](../.github/workflows/ci.yml); `ptxas` comes from the PyPI
package `nvidia-cuda-nvcc-cu12==12.9.86` and is used only as a checker). It verifies:

| Step | What |
|---|---|
| Syntax | every Python file compiles; every official-run shell script passes `bash -n` |
| Contract self-test | [`시험/계약자체.py`](../시험/계약자체.py): `fma32` against exact rational rounding (4,000 cases incl. near-cancellation); slow vs fast vs BLAS references for Q8_0 · Q4_0; slow vs BLAS for Q4_K · Q5_K · Q6_K on synthetic GGUF blocks; the k-quant embedding against an independent per-value dequantizer written like llama.cpp's `dequantize_row_q*_K` |
| Tile tables | the 11 tile shapes agree across the generator, the engine and the tests |
| Build | the kernel generator and all 15 host programs build with the geul compiler |
| Modules | six modules (0.5B · 7B Q8_0 · 7B Q4_0 · 14B Q4_0 · 7B and 14B k-quants) are regenerated from scratch; source and PTX must match [`시험/모듈해시.txt`](../시험/모듈해시.txt) byte for byte |
| SASS | `ptxas -arch=sm_89 -v` on every module; a kernel that newly spills registers, or spills more than [`시험/SASS넘침.txt`](../시험/SASS넘침.txt) allows, fails the check |
| Imports | the runner imports only `kernel32`, `shell32` and `nvcuda` |

When a commit changes kernels on purpose, update the baselines in the same commit: `--해시갱신` rewrites the module hashes and
`--넘침갱신` the spill list (or copy them from the CI run's `check-result` artifact).

## 3. Model files

| File | How |
|---|---|
| `모델/qwen2.5-0.5b-instruct-gguf/qwen2.5-0.5b-instruct-q8_0.gguf` | Hugging Face `Qwen/Qwen2.5-0.5B-Instruct-GGUF` |
| `모델/qwen2.5-7b-instruct-gguf/qwen2.5-7b-instruct-q8_0.gguf` | `Qwen/Qwen2.5-7B-Instruct-GGUF` q8_0 (split files merged with `llama-gguf-split --merge`) |
| `…/qwen2.5-7b-instruct-q4_0-pure.gguf` | `llama-quantize --allow-requantize --pure <7b-q8_0> <out> Q4_0` (all tensors Q4_0) |
| `…/qwen2.5-7b-instruct-{q4_k_m,q5_k_m,q6_k}-req.gguf` | `llama-quantize --allow-requantize <7b-q8_0> <out> Q4_K_M` (and Q5_K_M, Q6_K) — llama.cpp's standard per-tensor mixes |
| `모델/qwen2.5-14b-instruct-gguf/qwen2.5-14b-instruct-q4_0-pure.gguf` | `Qwen/Qwen2.5-14B-Instruct-GGUF` q4_0, merged, then `--pure` Q4_0 |
| `…/qwen2.5-14b-instruct-q4_k_m-req.gguf` | `llama-quantize --allow-requantize <14b-q4_0-pure> <out> Q4_K_M` (speed records only) |

llama.cpp for comparisons: release b11496, Windows CUDA build, in `도구/llama-b11496/`.

## 4. GPU bit tests

Build the modules (see the README's quick start), then:

```
python -I -X utf8 시험/판23.py 빌드/글/qwen2Q4_7b.ptx <7b-q4_0-pure.gguf> out.json            # every Q4_0 kernel vs the CPU reference
python -I -X utf8 시험/판26.py 빌드/글/qwen2K_3584x28x4x18944x152064.ptx <q4_k_m> <q5_k_m> <q6_k> out.json   # every k-quant kernel
python -I -X utf8 시험/입력7B.py <7b-q8_0.gguf> 입력7B.bin                                    # chat prompts + a 2100-token text
빌드/글/시험_7B.exe <model.gguf> <module.ptx> 입력7B.bin <out folder>                          # five paths: logits + KV cache must agree
python -I -X utf8 시험/참조7B.py <model.gguf> <out folder> ref.json                            # every row of logits vs the CPU forward pass
```

`시험_7B` writes `요약.txt` (logit hashes, tokens, KV hashes); comparing it with the stage's committed summary in `문서/결과/<stage>/`
checks that nothing changed. The CPU forward pass takes 20–25 minutes per 7B file.

## 5. Benchmarks

```
python -I -X utf8 시험/입력7B.py <7b-q8_0.gguf> 재기입력.bin --재기
빌드/글/재기_7B.exe <model.gguf> <module.ptx> 재기입력.bin out.txt         # decode ms/token (short · 2048 · 8192), prompt ms (128 · 2048 · 8192)
llama-bench -m <model.gguf> -p 2048,8192 -n 0 -o md
llama-bench -m <model.gguf> -p 0 -n 128 -d 0,2048,8192 -o md
```

`재기_7B` reports, per cell, the median of three medians of seven runs (after one warm-up). Each stage's official script runs GeulPU and
llama.cpp alternately three times; the collectors in `재기/모음2X.py` take the median of the three runs and compute the ratios. Never run
two GPU timings at once.

## 6. Official runs

`bash 공식실행/공식2X.sh <absolute repo path> <work folder>` re-runs a stage exactly as it was judged: it builds from the committed
code, runs the bit tests and benchmarks, and writes the results to `문서/결과/<stage>/`. Stage 27's script also builds the stage-26 commit
in a git worktree and alternates the two builds in the same session.
