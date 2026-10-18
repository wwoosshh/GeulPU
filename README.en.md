# GeulPU — local AI chat on your own graphics card

*한국어: [README.md](README.md). The code and most stage reports are written in Korean — see the [glossary](docs/glossary.md) for the
terms; English documents live in [docs/](docs/).*

> In [stage 40](문서/40단계.md) (2026-10-16) we measured whether computational loss causes LLM failure symptoms (repetition loops,
> unrelated-language output, broken spelling, wrong answers). Engine-level loss (llama.cpp, Q8_0) changes almost every answer but does not
> increase the symptoms. This research stops here ([research log](docs/research-log.md)). The app guide below still applies. Paper draft (English and Korean, with
> PDFs): [docs/paper/](docs/paper/) · raw data (1.7 GB): [release s40-data](https://github.com/wwoosshh/GeulPU/releases/tag/s40-data).

GeulPU is a Windows app that runs language models such as Qwen3, Qwen2.5, DeepSeek-R1, Llama 3 and Mistral **on your own GPU**. There is no installer:
unzip it, run `GeulPU.exe`, and a chat page opens in your browser. Models are downloaded from Hugging Face inside the app, and your
conversations never leave the PC.

The engine is written in **geul (글)**, a Korean programming language — from the GPU kernels to the inference server and the app. It
runs on the graphics driver alone, without the CUDA toolkit, Python or PyTorch, and its precision is a written contract, so its
results are **bit-identical** to a CPU reference implementation ([What is different](#what-is-different)). So scoring the same text
again gives the same probabilities on any PC or GPU, and the **research panel** lets you inspect every token's probability, branch
with one token changed, compare against another model or prompt, and check someone else's result to the bit
([research panel](#5-research-panel--per-token-probabilities--intervene--compare--reproduce)).

> It loses only what is written down — and it shows what losing less costs.

**[⬇ Download the latest version — Windows 64-bit, zip of about 1.4 MB](https://github.com/wwoosshh/GeulPU/releases/latest)**

[Install](#install) · [First steps](#first-steps) · [Supported models](#supported-models) · [How it runs](#how-it-runs) ·
[Troubleshooting](#troubleshooting) · [Update and uninstall](#update-and-uninstall) · [What is different](#what-is-different) ·
[Development and research](#development-and-research)

## Install

### Requirements

| | |
|---|---|
| OS | Windows 10 or 11 (64-bit) |
| GPU | NVIDIA RTX 30 series or newer runs on CUDA; other GPUs (AMD Radeon, …) run on Vulkan 1.3 |
| Graphics memory | From 6 GB (small models). 7B / 8B need 8 GB (Q4_K_M) or 12 GB (Q8_0); 14B needs 12 GB or more ([table below](#which-model-fits-your-pc)) |
| Disk | About 5 MB for the app plus 2–9 GB per model |
| Internet | Only to find and download models and to check for new versions |

Keep the graphics driver up to date. NVIDIA cards older than the RTX 30 series (RTX 20, GTX 16 and earlier) cannot use the CUDA path
(compute capability below 8.0); the app then checks by itself whether they can run on Vulkan. On AMD, a Radeon RX 9060 XT has been
verified.

### 1. Download

Get **`GeulPU-<version>-windows-x64.zip`** from the [releases page](https://github.com/wwoosshh/GeulPU/releases/latest). It is small
because it contains no model — you download models inside the app.

To check that the file arrived intact (optional), compare it with `SHA256SUMS.txt` on the same page. In PowerShell:

```powershell
Get-FileHash .\GeulPU-0.5.0-windows-x64.zip
```

### 2. Unzip

Right-click the zip, choose **Extract All…**, and pick any folder (for example `C:\GeulPU`). Do not run `GeulPU.exe` from inside the
opened zip — extract it first.

### 3. Run

Double-click `GeulPU.exe`.

1. If **"Windows protected your PC"** appears, click **More info → Run anyway**. The executable is not code-signed; release zips are
   built from this repository's source by GitHub Actions ([How it runs](#how-it-runs)).
2. A black console window opens. That window *is* GeulPU — **closing it quits the app.**
3. Your browser opens `http://127.0.0.1:44544`. If it does not, type that address into the address bar.

## First steps

The app speaks English unless your browser prefers Korean — switch any time in **Settings → Language** (Auto · 한국어 · English).
The icons in the left bar are, from the top, **Chat · Models · Benchmark · Hardware**, with **Settings** at the bottom.

With no model installed, the app first shows this screen. **Download the recommended model** fetches a model chosen for your graphics
memory right away; **Browse models** opens Find models, described below.

![First screen — first, you need a model](docs/img/first-run-en.png)

### 1. Get a model — Models → Find models

- Hugging Face's GGUF models are listed by **Trending**. Switch to Popular, Likes or Recently updated, or type part of a name (for
  example `qwen3`, `coder`, `14b`) into the box at the top to narrow the list.
- By default only **models GeulPU can run** are shown. **Also show models that don't run** shows everything, with the ones that don't
  run dimmed and the reason given. **Fits this PC** keeps only models that fit your graphics memory.
- New to this? Switch on **Verified by GeulPU**: only repositories with files GeulPU has run itself remain (picture below); see
  [which model fits your PC](#which-model-fits-your-pc).

![Find models — the list on the left, details of the selected model on the right](docs/img/find-models-en.png)

- Click a model to see its description, downloads, license and **file list** on the right. The file that suits this PC best is marked
  **Recommended for this PC**, files GeulPU has run are marked **Verified to run**, and files that are tight or too large for your
  graphics memory say so. Click **Download** on the file you want.

![File list — "Recommended for this PC" and "Verified to run" marks with download buttons](docs/img/model-files-en.png)

- Before downloading, the app reads only the beginning of the file to check that it will run; interrupted downloads resume; finished
  files are verified with SHA-256. Downloads in progress appear under **My models** and in the status bar at the bottom, where you can
  pause or resume them.
- GGUF files you already have can be added with **Add a GGUF file** at the top; they stay where they are.

### 2. Chat

- Pick a model with the model button at the top and send a message (**Enter** sends, **Shift+Enter** adds a line).
- **The first time**, GeulPU builds the kernels for your GPU and model (about 10 seconds on a fast CPU, 1–3 minutes on a slow one) and
  loads the model into graphics memory (about 20 seconds for 7B). Later only the loading happens.
- **Reasoning models** (Qwen3, DeepSeek-R1) think before answering. The thinking is folded as "Thought for N s"; click it to expand.
  Token count and speed (tokens/s) appear under the answer.

![Chat — Qwen3-8B Q4_K_M with its thinking folded and the speed under the answer](docs/img/chat-en.png)

- **To turn Qwen3's thinking off**: **Generation settings** (the slider icon at the top right) → switch off **Thinking**. It then
  answers directly.
- Generation settings also hold the temperature (0 gives the same answer to the same question every time), the maximum answer length
  and a system prompt, saved in this browser.

![Generation settings — temperature, max answer length, thinking switch, system prompt](docs/img/generation-settings-en.png)
- You can regenerate an answer or edit and resend your message; earlier answers stay as versions you can flip through (‹ 1 / 2 ›).
  Code, tables and math (LaTeX) are rendered.
- Conversations are stored only in this browser.

### 3. Benchmark (optional)

- **Hardware diagnosis**: measures memory bandwidth and tensor-core throughput and shows how close each kernel comes to the hardware's
  limit.
- **Speed test**: prompt processing (512 and 2048 tokens) and generation speed in tokens per second.
- **Reproducibility check**: solves 32 math problems with DeepSeek-R1-Distill-Qwen-7B Q8_0 and compares the output with the reference
  PC bit for bit (the quick check uses 2 problems and 64 tokens).
- Results can be exported as a zip (user paths are removed). The raw tool output and the result files themselves stay in Korean.

### 4. Settings

GPU backend (Auto · CUDA · Vulkan), Vulkan device, concurrent chats (how many chats can answer at once, 1–8) and context length per
chat, model folder, language, new-version notice. Changes are saved immediately.

### 5. Research panel — per-token probabilities · intervene · compare · reproduce

GeulPU's arithmetic is fixed by a written contract, so scoring the same text again gives **bit-identical** probabilities to those at
generation time — whatever the number of concurrent requests, the cache, the GPU or the backend (CUDA · Vulkan). The difference
between two runs therefore comes only from what you changed. Open the panel with the flask button at the top of the chat, or the
flask under an answer (answers received in this version onward — research records stay in this browser).

**New to it? Start with the [research panel guide](docs/research-guide.md)** — seven experiments (where the model hesitated, branching,
comparing two answers, the effect of quantization, the effect of one word, scoring text, reproduction capsules) with screenshots, how to
read the numbers, and API examples.

- **Observe** — the answer as tokens: each token's probability, rank, top-10 alternatives, entropy and the gap between the top two
  (margin). Close calls (margin < δ — places where a slightly different computation or setting could pick another token) and steps
  where sampling picked a token that wasn't ranked first are marked.
- **Intervene** — pick an alternative token at any step and **branch here**: generation continues with the same settings, the same
  seed and the same per-step random numbers, so the chosen token is the only change. You can also regenerate with only the
  temperature, seed or max length changed. New answers stay as versions.
- **Compare** — the first diverging step of two answers (versions or branches). For an edited question, score the same answer tokens
  under the other prompt and see the per-token difference; score the same text with another model (e.g. Q8_0 ↔ Q4_K_M of the same
  model) to see the effect of the quantization alone.
- **Score** — paste text and get each token's log-probability and the perplexity.
- **Reproduce** — fingerprints (SHA-256 — the recipe is in [contract](docs/contract.md) §5.2), re-run without the cache and check, export a **reproduction capsule** (request, result,
  log-probabilities and logit hashes in one JSON file) and load one to check it, hashes of the engine binaries and kernels.
- **Export** — every value shown as JSON or CSV, and Python code that fetches the same values.

Probabilities are the model's distribution (temperature 1), not the distribution filtered by the sampling temperature, top-k or
top-p. The panel computes only when you look, so chat speed is unchanged.

![Research panel — Observe: pick a step in the token strip to see its top-10 alternatives and numbers](docs/img/research-observe-en.png)

![Research panel — Compare: the same answer scored again with the same model's Q4_K_M file — the effect of the quantization alone, token by token](docs/img/research-compare-en.png)

A capsule can be checked without a GPU, too — clone the repository (`pip install numpy`) and run
`python -I 도구/캡슐확인.py <capsule.json> <model.gguf>`. The contract's CPU reference implementation recomputes the tokens, logit hashes
and log-probabilities (a few minutes for 7B).

### Use it from other programs (OpenAI-compatible API)

While a model is loaded in the app (sending one chat message loads it), use `http://127.0.0.1:44544/v1` as an OpenAI-compatible base
URL. Any `model` name works — the loaded model answers. The response's `model` echoes the name you sent, so check `/v1/models` to see
which model answered.

Paste this into a PowerShell window (it reads the response as UTF-8 so non-English text is not garbled; to save it as a `.ps1` file,
use "UTF-8 with BOM"):

```powershell
$body = @{ messages = @(@{ role = 'user'; content = 'Hello' }) } | ConvertTo-Json -Depth 4
$r = Invoke-WebRequest -Uri http://127.0.0.1:44544/v1/chat/completions -Method Post -ContentType 'application/json; charset=utf-8' -Body ([Text.Encoding]::UTF8.GetBytes($body)) -UseBasicParsing
([Text.Encoding]::UTF8.GetString($r.RawContentStream.ToArray()) | ConvertFrom-Json).choices[0].message.content
```

```python
from openai import OpenAI   # pip install openai
client = OpenAI(base_url="http://127.0.0.1:44544/v1", api_key="geulpu")   # any key
r = client.chat.completions.create(model="geulpu", messages=[{"role": "user", "content": "Hello"}])
print(r.choices[0].message.content)
```

- To turn Qwen3's thinking off, add `"chat_template_kwargs": {"enable_thinking": false}` to the request (`extra_body=` in Python).
- By default the thinking of Qwen3 and DeepSeek-R1 comes in front of the answer without tags. Add `"geulpu": {"special": true}` to
  receive `<think>` and `</think>` as text, so you can separate the thinking from the answer.
- Only this PC can connect, and there is no authentication. Requests that other websites send through your browser are refused.
- `/v1/chat/completions` uses the Qwen2.5, Qwen3, Llama 3 (3.1 · 3.2) and Mistral (v0.3) chat templates. For DeepSeek-R1, put R1's
  template into `/v1/completions` yourself for now.
- The Llama 3 template puts a date in the system header. So that the same question does not become a different prompt every day, it is
  fixed to `26 Jul 2024`; change it with `"chat_template_kwargs": {"date_string": "16 Oct 2026"}` in the request. Mistral's template has
  no system role, so a system message is put in front of the first question as `{system}\n\n` (the same form as llama.cpp).
- For Llama 3 and Mistral a BOS token is prepended to text prompts (the text of `/v1/completions` and the `prompt` of `/tokenize`), as
  llama.cpp and vLLM do — `/tokenize` leaves it out with `"add_special_tokens": false`. Prompts given as token ids are used as they are.

**Log-probabilities · scoring · tokenization (for research)** — every value in the research panel is also available from the API.
Contract 5.2 ([contract](docs/contract.md)) defines the values, so they are bit-identical on any PC or GPU.

- `/v1/chat/completions`: `"logprobs": true, "top_logprobs": 5` (0–20), in the OpenAI shape (`token` · `logprob` · `bytes` ·
  `top_logprobs`).
- `/v1/completions`: `"logprobs": 5`, `"echo": true` (log-probabilities of the prompt tokens too), `"max_tokens": 0` (score only, no
  generation). `prompt` is text or an array of token ids.
- The `"geulpu"` extension: `"logit_hash": true` (a 64-bit hash of each step's logit row), `"prompt_tokens": true` (the prompt tokens
  after the chat template), `"echo_from": n` (echo log-probabilities from the token at index n on — 0-based; earlier ones are null), and `entropy` · `top_ids` · `top_logprobs`
  (aligned with the ids) · `seed` in the response.
- `/tokenize` · `/detokenize` · `/tokenizer_info` — in the same shape as vLLM.
- In `geulpu`, `tokens` and `logit_hashes` include the step that sampled the stop token (EOS), while the log-probability arrays
  (`logprobs`, `entropy`, `top_ids`, `top_logprobs`) cover only the answer's tokens, as in OpenAI — one shorter when the answer ends with
  EOS (score `tokens` with echo to get the EOS step's probability). Despite its name, `first_token_ms` is in µs (kept for compatibility).
- Asking for log-probabilities during generation adds about 2% per token (7B · 8B — the computation hides behind the next step's GPU
  work). Without them, speed is unchanged.

```python
# Log-probability of each token of a text (scoring) — the first token has no context, so it is null
r = client.completions.create(model="geulpu", prompt="The capital of France is Paris.", echo=True, max_tokens=0, logprobs=5)
print(list(zip(r.choices[0].logprobs.tokens, r.choices[0].logprobs.token_logprobs)))
```

**lm-evaluation-harness** — it connects as `local-completions`. It uses the server's tokenizer (`tokenizer_backend=remote`), so no
Hugging Face tokenizer is downloaded. Per-item results are bit-identical whatever `num_concurrent`, the number of concurrent chats or
CUDA ↔ Vulkan ([stage 38](문서/38단계.md)). Raise the number of concurrent chats in **Settings** (up to 8).

```bash
pip install "lm-eval[api]"
lm_eval --model local-completions --tasks arc_easy,gsm8k --model_args model=geulpu,base_url=http://127.0.0.1:44544/v1/completions,tokenizer_backend=remote,tokenized_requests=True,num_concurrent=8
```

## Supported models

GeulPU takes a single GGUF file (merge split files with llama.cpp's `llama-gguf-split --merge`).

| Architecture | Models | Sizes |
|---|---|---|
| qwen2 | Qwen2.5-Instruct · Qwen2.5-Coder · DeepSeek-R1-Distill-Qwen and their fine-tunes | 1.5B and up (head size 128) — 7B and 14B run on this project's PC |
| qwen3 | Qwen3 and its fine-tunes | 1.7B · 8B · 14B |
| llama | Llama 3.1 · 3.2 Instruct, Mistral 7B Instruct v0.3, and their fine-tunes that use the same chat templates | 3B · 7B · 8B — 70B checked as a shape with a synthetic model |

- **Formats**: Q8_0 · Q4_K_M · Q5_K_M · Q6_K, and Q4_0 files whose tensors are all Q4_0.
- **Licenses** differ by model. In the app's list, Llama 3.1 · 3.2 use Meta's community licenses (usage conditions and an Acceptable
  Use Policy — services with more than 700 million monthly users need permission from Meta), the Mistral 7B v0.3, Qwen2.5 and Qwen3 files
  are Apache 2.0, and DeepSeek-R1-Distill is MIT (also shown in the app's model descriptions).
- **Not yet**: other architectures (Gemma, Phi, …), models whose query width differs from the hidden size (Qwen3 0.6B · 4B · 32B,
  Mistral NeMo), small models with head size 64 (Qwen2.5-0.5B, Llama 3.2 1B), MoE (Mixtral, Qwen3-30B-A3B, …), llama-architecture
  fine-tunes with other chat templates (ChatML, …), image input, Q2_K · Q3_K · IQ · Q5_0 · F16 · BF16. Find models hides such files by
  default.
- **Depending on the GPU**: k-quants (Q4_K_M, …) run on CUDA and on Vulkan GPUs with at least 48 KB of shared memory. With AMD's
  Windows driver (32 KB of shared memory) only Q8_0 (and Q4_0) files run for now.

### Which model fits your PC

Files GeulPU has run itself (**Verified by GeulPU** in the app). Sizes use 1024-based units, as Windows Explorer does.

| Graphics memory | Suggested files |
|---|---|
| 6 GB | Qwen3-1.7B Q8_0 (1.7 GB) · Llama-3.2-3B-Instruct Q8_0 (3.2 GB) |
| 8 GB | Qwen3-8B Q4_K_M (4.7 GB) · Qwen2.5-7B-Instruct Q4_K_M (4.4 GB) · DeepSeek-R1-Distill-Qwen-7B Q4_K_M (4.4 GB) · Llama-3.1-8B-Instruct Q4_K_M (4.6 GB) · Mistral-7B-Instruct-v0.3 Q4_K_M (4.1 GB) |
| 12 GB | Qwen3-8B Q8_0 (8.1 GB) · Qwen2.5-7B-Instruct Q8_0 · Qwen2.5-Coder-7B-Instruct Q8_0 · DeepSeek-R1-Distill-Qwen-7B Q8_0 (7.5 GB) · Llama-3.1-8B-Instruct Q8_0 (8.0 GB) · Mistral-7B-Instruct-v0.3 Q8_0 (7.2 GB) — 14B Q4_K_M also runs with a reduced context |
| 16 GB or more | Qwen2.5-14B-Instruct Q4_K_M · DeepSeek-R1-Distill-Qwen-14B Q4_K_M (8.4 GB) |

Qwen3-14B Q4_K_M has only been checked bit for bit on a synthetic model of the same shape and has not been run yet. The app tells you
for every file whether it fits your graphics memory.

## How it runs

```mermaid
flowchart LR
    B["Browser<br/>127.0.0.1:44544"] -- "UI · /api · /v1" --> M["GeulPU.exe<br/>manager"]
    M -- "first use of a model" --> G["kernel-gen.exe<br/>ptx-backend.exe · spirv-backend.exe"]
    G -- "kernels for this GPU" --> K[("module folder")]
    M -- "starts it, forwards /v1" --> S["server-cuda.exe<br/>server-vulkan.exe"]
    K --> S
    S -- "nvcuda.dll · vulkan-1.dll" --> GPU[("GPU")]
```

1. The **manager** (`GeulPU.exe`) serves the UI on `127.0.0.1:44544` and opens your browser. It listens only inside this PC; if it is
   already running on that port, it just opens the page. 44544 is the code point of '글' (U+AE00).
2. It first checks the GPU — CUDA (`nvcuda.dll`) on an NVIDIA RTX 30 or newer, otherwise Vulkan (`vulkan-1.dll`). You can change this
   in Settings.
3. The first time a model is used, it **builds kernels**: the kernel generator (`kernel-gen.exe`) writes GPU kernel source in geul for
   the model's architecture, shape and format, and the geul compiler's backends (`ptx-backend.exe`, `spirv-backend.exe`) turn it into
   PTX (NVIDIA) or SPIR-V (Vulkan) in the data folder — once per app version.
4. The **inference server** (`server-cuda.exe` or `server-vulkan.exe`) loads the GGUF into graphics memory and runs those kernels
   directly through the graphics driver. No CUDA toolkit, runtime or Python is needed.
5. Chat goes browser → manager → inference server (an OpenAI-style API), and the answer streams back token by token.
6. Closing the console window stops the manager together with every process under it (server, tools).

The manager, the inference server, the kernel generator and the backends are all written in geul; they import only Windows DLLs (the
manager: kernel32, ws2_32, shell32, winhttp, bcrypt, advapi32) and the graphics driver's DLL.

**Inside the zip**

| File | What it does |
|---|---|
| `GeulPU.exe` | The manager — UI, model download and verification, starting the server and tools |
| `bin\server-cuda.exe` · `bin\server-vulkan.exe` | Inference server (OpenAI-style HTTP API) |
| `bin\kernel-gen.exe` | Kernel generator — kernel source (geul) for a model's shape |
| `bin\ptx-backend.exe` · `bin\spirv-backend.exe` | The geul compiler's backends — kernels to PTX and SPIR-V |
| `bin\device-*.exe` · `bin\diag-*.exe` · `kernels\` | GPU detection and hardware diagnosis |
| `web\` | The UI (HTML, CSS, JavaScript) |
| `data\` | Catalog of downloadable models · reproducibility-check reference |
| `version.json` | Version, commit and the SHA-256 of every file |

**Data folder** — `%USERPROFILE%\GeulPU` (kept across versions)

| | |
|---|---|
| `모델\` (models) | Downloaded models (GGUF) |
| `모듈\<version>\` (modules) | Kernels built for this GPU |
| `결과\` (results) | Benchmark results |
| `기록\` (logs) | Server and job logs — look here when something goes wrong |
| `설정.json` · `모델목록.json` · `허깅목록.json` | Settings · your model list · files picked on Hugging Face |

To move the data folder, set the environment variable `GEULPU_HOME` or run `GeulPU.exe --자료 <folder>`. Other options:
`--포트 <number>` (another port) and `--열지않음` (do not open the browser).

**Network and privacy**

- The manager and the inference server listen only on `127.0.0.1` — other devices cannot connect.
- The internet is used for three things only: Find models (the page reads the Hugging Face API directly), downloading models
  (huggingface.co) and the new-version check (GitHub — switch off **New-version notice** in Settings).
- No usage statistics are sent. Conversations stay in your browser's storage.
- There is no installer, and nothing is written to the registry.

**Build and trust**: release zips are built from this repository's source by GitHub Actions when a tag is pushed (`앱/꾸리기.ps1` — it
builds the geul compiler to its self-hosting fixed point, then the backends, servers, tools and the manager). The server, generator and
backends are packaged only after their bytes are checked against the build hashes of the reproducibility reference
(`교차검증/expected.json`).

## Troubleshooting

| Symptom | What to do |
|---|---|
| The browser does not open | Type `http://127.0.0.1:44544` into the address bar. |
| "Windows protected your PC" | **More info → Run anyway** (the executable is not code-signed). |
| Antivirus blocks it | Add an exception for the extracted GeulPU folder. The source and the build process are public in this repository. |
| Port 44544 is taken by another program | Start it on another port, e.g. `GeulPU.exe --포트 44600`. |
| "No usable GPU" | Update the graphics driver, then **Hardware → Check again**. |
| "Not supported on this GPU" · "Not enough VRAM" | Choose a smaller file (Q4_K_M) or a smaller model. A shorter context per chat or fewer concurrent chats in Settings also use less memory. |
| The first message takes long | The first time builds kernels (1–3 minutes). After that, only loading the model (tens of seconds). |
| A download stopped | **Resume download** under My models or in the status bar — it continues where it stopped. |
| Part of the screen is in Korean | Messages from the engine are translated when they are shown; raw logs, tool output and result files stay in Korean. Paths such as `%USERPROFILE%\GeulPU\모델\` are real folder names. |
| Anything else | Open an [issue](https://github.com/wwoosshh/GeulPU/issues) and attach the logs from `%USERPROFILE%\GeulPU\기록\`. |

## Update and uninstall

- **New version**: the app tells you when GitHub has a new release. Quit the app, unzip the new zip and run its `GeulPU.exe`. Models,
  settings and results stay in the data folder, so nothing is downloaded again (the kernels are rebuilt once for the new version).
  Changes are listed in [바뀐것.md](바뀐것.md) (Korean).
- **Uninstall**: quit the app and delete the GeulPU folder. To delete the downloaded models as well, also delete
  `%USERPROFILE%\GeulPU`.

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
  outputs all changed with the number of concurrent requests on one PC ([교차검증](교차검증/)). Evaluation tools too: lm-evaluation-harness
  per-item results (arc_easy 500, gsm8k 100) were identical across num_concurrent 1 ↔ 8 and CUDA ↔ Vulkan (with the same setup,
  llama.cpp b11643 changed the generated text of 41 of 100 gsm8k items between 1 and 8 concurrent requests — [stage 38](문서/38단계.md)).
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
  - Stage 34, Vulkan speed — the emulated integer tensor op became cooperative-matrix tensor-core work in the tile kernels,
    attention and the decode line kernels; the SPIR-V backend's division and subnormal flushing (no re-flush of values already flushed), the
    Vulkan layer's barriers and the tile kernels' loading were fixed. All bit-exact (CPU reference, CUDA records byte for byte). Measured alternately in one session, 7B on Vulkan takes 1.19–1.27×
    the CUDA path's prompt time (stage 31: 4.3–5.5×) and 1.00–1.06× its decode time (stage 31: 1.09–1.27×; short-context decode varies
    about 3% between runs); prompt tile kernels and short prompts (128 rows: 1.39–1.47×) remain ([stage 34](문서/34단계.md), Korean). Stage 31 (Vulkan): the geul host runs on vulkan-1.dll alone and reproduces the CUDA records byte for byte on NVIDIA and on Intel
    integrated graphics; on a friend's AMD Radeon RX 9060 XT (RDNA4) the 7B R1 run matched the NVIDIA CUDA reference in all 82,673 steps
    (stage 34). Stage 32 (self-tuning to the device's floor) waits for runs on
    friends' PCs. See the [research log](docs/research-log.md).
  - Now: stage 37, Qwen3 — a one-run preview of Qwen3-8B decoding took 0.982–1.007× llama.cpp's time (b11567) for Q8_0 and 1.037–1.055×
    for Q4_K_M; the pre-registered speed criterion (37c, ≤ 1.05×) was not measured officially ([stage 37](문서/37단계.md), Korean).
- **Larger models keep the advantage.** A simulation that reproduces only the rounding points (validated against the measured 0.5B value:
  1/637 simulated vs 1/615 measured) gives a hidden loss of 1/3805 (7B Q8_0) and 1/4467 (14B Q4_0) of a llama.cpp-like pipeline.

## Development and research

The rest is for building the engine from source or reading the research record. To use the app, [Install](#install) is all you need.

### Status (2026-10)

| | |
|---|---|
| Models | **Llama-3.1-8B · Llama-3.2-3B · Mistral-7B v0.3** (stage 39 — architecture `llama`: q · k row restore and RoPE scaling factors as contract §4.7; five files bit-identical to the CPU reference, mean KL ≤ 4 × 10⁻⁴ against llama.cpp on every token of the same texts; the 70B shape tested on synthetic models) · **Qwen3-1.7B / 8B / 14B** (stage 37 — per-head Q/K RMSNorm as contract §4.6 and one appended kernel, bit-identical to the CPU reference; the 14B shape tested on synthetic models) · **Qwen2.5-0.5B / 7B / 14B-Instruct** · DeepSeek-R1-Distill-Qwen (chat; Llama-family blocks — RMSNorm · RoPE · SwiGLU · GQA; head sizes 64 and 128). Head-128 Qwen2 shapes are read from the GGUF config; 32B and 72B shapes were bit-tested on 4-layer synthetic models. GPT-2 small and XL (research engine). |
| App | Stages 36–39 — `GeulPU.exe` (a manager written in geul) and a web UI: find models (browse every Hugging Face GGUF repo, sorted), download, add and verify them; chat (Qwen2.5's ChatML, Qwen3's template with thinking on/off, R1's, Llama 3's and Mistral's templates); self-diagnosis, speed and cross-check runs; result zips; a new-version notice; a **research panel** (stage 38 — per-token probabilities, branching, comparison, scoring and reproduction capsules; log-probabilities as contract §5.2) and an English UI. The release zip (1.4 MB) is built from source by CI when a tag is pushed (as a draft; a person publishes it). Windows x64 only — see [Install](#install). |
| Weight formats | GGUF **Q8_0 · Q4_0 · Q4_K · Q5_K · Q6_K**, including per-tensor mixes as in Q4_K_M · Q5_K_M (stage 26 — tested with files re-quantized on this PC from Q8_0; official Qwen files are not yet tested). |
| Runner | `빌드/글/실행기.exe model.gguf` (`실행기` = runner) — a geul program: chat (Qwen's ChatML and the Qwen3, Llama 3 and Mistral templates), streamed output, KV cache reused across turns, greedy decoding (the same conversation gives the same answer). About 0.3 s until the prompt runs. |
| Server | `빌드/글/서버.exe model.gguf` (`서버` = server) — a geul program (stage 28): an OpenAI-compatible HTTP API (chat · completions · SSE streaming) with slots, continuous batching, prompt caching and a sampling contract (the same seed gives the same tokens). A request returns the same bits whatever else runs with it — zero differences over four models × twelve requests × four schedules, while llama-server's greedy answer changed in 11 of 12 cases depending on the concurrent requests. Head-128 Qwen2 (7B · 14B). 7B Q4_0 aggregate throughput: 302 tokens/s with four streams and 508 with eight (llama-server 360 · 632 — a multi-row decode kernel is next); one stream is 4% faster than llama-server. A cached prompt's first token takes 13.8 ms (llama-server 13.0 ms; stage 30 feeds the last rows through the decode step). See [`문서/28단계.md`](문서/28단계.md) · [`문서/30단계.md`](문서/30단계.md) |
| Environment | Windows or Linux x86-64 (glibc) + NVIDIA Ampere (RTX 30) or newer + driver. Linux was tested under WSL2 Ubuntu 24.04 in stage 29 — the same bits as Windows on the same GPU, speed within ~0.5% ([`문서/29단계.md`](문서/29단계.md)). On Linux the programs import only libc.so.6 and libcuda.so.1. All numbers here are from one RTX 4070 Ti (12 GB). Building (generator → kernel source → PTX → runner) needs only the geul compiler. Tests and benchmarks need Python 3.12 + numpy. **Vulkan (stage 31):** Vulkan builds of the geul host (`시험_엔진V` · `시험_7BV` · `재기_7BV` — they import kernel32, shell32 and vulkan-1.dll; kernels come from the geul compiler's SPIR-V backend) reproduce the CUDA records byte for byte on NVIDIA (0.5B, 7B in five formats, 14B) and Intel integrated graphics (0.5B). Speed is not there yet — stage 34 replaced the emulated integer MMA with cooperative-matrix tensor-core work (`--협력` modules) and fixed the backend and the Vulkan layer: 7B prompts take 1.15–1.41× llama.cpp Vulkan's time (stage 31: 4.4–6.1×), decode 1.00–1.04× (stage 31: 1.09–1.24×) — a record, not yet a verdict. No Vulkan build of the runner or the server yet. |
| Layer split | Stage 25 — split layers across GPUs (`--나누기 P` parts, `--장치 a,b,…` devices, `--예산 GB` budget). Emulated on one GPU with one CUDA context per part: 16 split runs are bit-identical to the single-part run; decoding with two parts takes 1.025–1.029× (mostly the emulation's context switching; 1.002–1.003× with a shared context). 14B in two parts did not fit at context 8192 on 12 GB, so that pre-registered cell was not measured (criterion 25c not passed). |
| Not yet | Real multi-GPU runs; measuring the contract's loss with the real engine on 7B+ (done for 0.5B; simulated for 7B · 14B); Q2_K · Q3_K · IQ formats · Q5_0 (real 72B k-quant files use Q5_0 · Q8_0 for ffn_down); MoE; a GPU run on native Linux (tested under WSL2 only); running on Apple GPUs (three NVIDIA generations and an AMD Radeon RX 9060 XT (RDNA4, Vulkan) match bit for bit — [교차검증](교차검증/); AMD speed (RX 9060 XT generation is about 3× slower than an RTX 4070 Ti, mostly attention); Intel integrated graphics matches through Vulkan for 0.5B — stage 31); k-quants on 32 KB shared-memory devices (AMD on Windows); models whose query width differs from the hidden size (Qwen3-0.6B · 4B · 32B, Mistral NeMo); small head-64 llama models (Llama-3.2-1B); other architectures (Gemma, Phi, …). |

### Repository layout

| Folder | What |
|---|---|
| [`커널/`](커널/) (kernels) | `커널생성.gl` + `생성*.gl` — the kernel generator written in geul; it emits geul kernel source for every module. `커널생성.py` — the legacy Python generator (GPT-2, reference). |
| [`호스트/`](호스트/) (host) | geul programs: `실행기.gl` (runner), `엔진.gl` (engine: kernel selection, CUDA graphs, decoding), `가중치*.gl` (GGUF weight layout), `로프.gl` (RoPE tables in double-precision arithmetic), `토크나이저.gl` (Unicode 15.0 tables, NFC, BPE), `조각.gl` (layer split), tests and benchmarks. |
| [`계약/`](계약/) (contract) | `정수계약.py` — the CPU reference implementation of the contract; every bit comparison is against it. `로그확률.py` — log-probabilities (contract §5.2) in Python. |
| [`도구/캡슐확인.py`](도구/캡슐확인.py) (tools) | Checks a research-panel reproduction capsule without a GPU, on the CPU reference (the rest of `도구/` is downloaded external tools, not in the repository). |
| [`시험/`](시험/) (tests) | Bit tests (every kernel vs the CPU reference, paths vs each other, end-to-end), the quick check (`빠른점검.py`). |
| [`재기/`](재기/) (benchmarks) | Speed comparisons with llama.cpp (the latest official release at measurement time — b11496 through stage 29, b11567 from stage 30; CUDA) and PyTorch; result collectors. |
| [`공식실행/`](공식실행/) (official runs) | The scripts that produced each stage's verdicts, kept as they were run. |
| [`문서/`](문서/) (documents) | Korean stage reports and the contract. English: [`docs/`](docs/). |
| [`엔진/`](엔진/) · [`컴파일러/`](컴파일러/) | Legacy Python host and Python PTX backend, kept for comparison. |

### Build from source

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

### Checks

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

### Research log

The engine came out of a research program started on 2026-10-08: stages 0–13 in the `research/gpu` branch of the geul repository, stage
14 onward here. Every stage commits its pass/fail criteria before measuring, compares every variant bit for bit before timing it, and
keeps failures and missed criteria. English summary: [docs/research-log.md](docs/research-log.md). Korean stage reports:
[`문서/`](문서/). A short technical brief for outside reviewers: [docs/brief.md](docs/brief.md). What the geul compiler caught and
missed over stages 1–27, counted case by case: [docs/compiler-catches.md](docs/compiler-catches.md).

## License

MIT — [LICENSE](LICENSE). The copy of the geul front end (`컴파일러/ref/`) is MIT by the same author.
