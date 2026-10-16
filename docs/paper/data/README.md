# Raw data — GeulPU stage 40: engine numerical loss and LLM failure symptoms

Data for the paper *Engine Numerical Loss Re-Rolls but Does Not Degrade: An Exact-Baseline Study of LLM Failure Symptoms*
(Sunghyeun Woo, Chungwoon University, 2026). Code, prompts, pre-registration and the analysis results live in the GeulPU
repository: https://github.com/wwoosshh/GeulPU — paper draft in `docs/paper/`, pre-registration and record (Korean) in
`문서/40단계.md`, computed results in `문서/결과/40단계/`, prompt sets in `시험/질문40/`, tools in `재기/*40.py`. This record holds
what the repository cannot: every token the three engines generated and the per-step probabilities from which every number in
the paper is computed.

DOI: [10.5281/zenodo.23417759](https://doi.org/10.5281/zenodo.23417759). Repository commit used for the analysis: `0a5ab97`.

## Archives

| Archive | Contents | Paper | Size (zip) |
|---|---|---|---|
| `geulpu-s40-generation-qwen2.5-7b.zip` | `생성/`: Qwen2.5-7B-Instruct outputs of arms G, L, V; V's scoring of G's answers; the one-slot llama-server run; forced-token continuations; contamination dialogs; determinism re-runs | §5.1–5.6 | 796 MB (2.06 GB unpacked) |
| `geulpu-s40-generation-r1-distill-7b.zip` | `생성/`: DeepSeek-R1-Distill-Qwen-7B outputs of arms G, L, V on gsm8k, and V's scoring | §5.2, 5.3 | 723 MB (1.78 GB) |
| `geulpu-s40-follower.zip` | `따라/`: llama.cpp's per-step distributions at G's prefixes (the "follower"), and its validation summary | §4.4, 5.1, 5.3 | 141 MB (165 MB) |
| `geulpu-s40-steps-tokens.zip` | `위험/`: fragile steps and the sampled steps for propagation; `토큰/`: the token ids sent to every arm; `토큰_옛_BOS없음/`: the discarded first tokenization | §4.1, 4.4, 4.5, App. B | 1.7 MB (10 MB) |
| `geulpu-s40-engine-build.zip` | `build/`: the exact GeulPU server and kernel-generator executables, generated kernel sources and PTX used in the runs | §3, App. C | 36 MB (249 MB) |
| `MANIFEST.sha256` | SHA-256 of every file inside the archives (1,981 files; paths relative to the work directory) | | 185 KB |
| `SHA256SUMS` | SHA-256 of the archives and of the manifest | | |

SHA-256 of the archives:

```
f6ae149bd759044b8baf76cceaed805f2762e6def236eff8681c96cd00070e12  geulpu-s40-generation-qwen2.5-7b.zip
b6bee150794c9b0f19f30020b6e446433a8a0e106cf328d9db140ed455c50add  geulpu-s40-generation-r1-distill-7b.zip
69e7dc5e4c4555799412e635a20dd228bf5a55dda80e320e4387a20aa92f1ba7  geulpu-s40-follower.zip
c86328bed5beadc9c33d0f3ba70ab18b5877719b2029218ece415f55db836f3b  geulpu-s40-steps-tokens.zip
0c75d19972ceb232d0b43d57b3729634c9dea7153b0cfdb9106b4d195a7abb9d  geulpu-s40-engine-build.zip
87cda2b9fabd1b407796370b16d710a20205192927e8284b1e5be0781189f7ad  MANIFEST.sha256
```

Extract all archives into one directory; together they recreate the *work directory* of the experiment (`생성/`, `따라/`, `위험/`,
`토큰/`, `토큰_옛_BOS없음/`, `build/`), which is the layout the analysis tools read. Directory and file names are Korean because the
tools are written that way; the meaning of each is given below.

## Arms and models

- **G** — GeulPU under its precision contract (exact baseline), server with 8 slots.
- **L** — llama.cpp build b11669 (Windows CUDA 13.4), `llama-server` with default settings, 8 slots.
- **V** — GeulPU with one change: linear-layer input activations rounded to one digit (module `qwen2Q8_7b_자리하나`).
- **L1** — `llama-server` with one slot and no prompt cache, used only to validate the follower.

Model files (ASCII names used by the tools; only the vocabularies are needed to re-run the analysis):

| Tool name | File | Source | SHA-256 |
|---|---|---|---|
| `qwen7b.gguf` | Qwen2.5-7B-Instruct, Q8_0 | Hugging Face `Qwen/Qwen2.5-7B-Instruct-GGUF`, `qwen2.5-7b-instruct-q8_0*.gguf`, split files merged with `llama-gguf-split --merge` | `52c5bf1406d31fd335a9d18154071c8d29d74680e13af45bb76543b4ddd5dbf1` |
| `r1.gguf` | DeepSeek-R1-Distill-Qwen-7B, Q8_0 | Hugging Face `unsloth/DeepSeek-R1-Distill-Qwen-7B-GGUF`, `DeepSeek-R1-Distill-Qwen-7B-Q8_0.gguf` | `7307bfbb539fd2e8ed636315440781fed23140dc7f911f64b33418f5b978281b` |

Model suffixes in file names: `_7b` = Qwen2.5-7B-Instruct, `_r1` = DeepSeek-R1-Distill-Qwen-7B. (`05b` = Qwen2.5-0.5B, tokenized but
not generated — dropped, Appendix B.)

## Files and record formats

All `.jsonl` files hold one JSON object per line, UTF-8. Token ids are the GGUF vocabulary ids. Prompt-set names (`묶음`):
`자연_LCB` (Language Confusion Benchmark, Korean), `자연_긴글` (long-form Korean), `자연_수학` (gsm8k), `방아쇠_글자` (rare-syllable copy
trigger), `방아쇠_언어` (mixed-script trigger), `방아쇠_되풀이` (repetition trigger). Item ids (`id`) match `시험/질문40/*.jsonl` in the
repository.

### `생성/` — generation

`G_7b.jsonl`, `L_7b.jsonl`, `V_7b.jsonl` (1,296 items each: 396 LCB + 300 long-form + 3 × 200 triggers), `G_r1.jsonl`, `L_r1.jsonl`,
`V_r1.jsonl` (600 gsm8k problems each). One record per prompt:

| Field | Meaning |
|---|---|
| `id`, `묶음` | item id and prompt set |
| `tokens` | generated token ids, in order, including the end token when the model stopped |
| `text` | the decoded answer |
| `finish` | `stop` (end token) or `length` (maximum reached) |
| `top_ids`, `top_lp` | per generated step, the 20 highest-probability token ids and their natural-log probabilities, in descending order (`top_ids[t][0]` is the chosen token under greedy decoding). **G, V**: one entry per generated step except the end-token step, so `len(top_ids) == len(tokens) − 1` when `finish == "stop"`. **L**: `llama-server`'s `completion_probabilities` as returned; the server emits no entry for a step whose token is an incomplete UTF-8 byte piece (it merges such pieces into the step that completes the character), so L has fewer entries than tokens and they are not step-aligned. The analysis does not use L's `top_ids`; L's per-step distributions are in `따라/`. |
| `prompt_n` | prompt tokens as counted by the engine; `보낸수` = tokens sent (equal in every record — the identical-input check); `최대` = maximum new tokens |
| L only: `stop_type`, `cache_n`, `셈한프롬프트` | llama-server's stop type, prompt-cache hits, prompt tokens evaluated |

`V점수_7b.jsonl` (1,294 items — two very long LCB answers failed, Appendix B), `V점수_r1.jsonl` (600): V's distribution at G's prefixes
("scoring" G's answer under V). Fields `id`, `묶음`, `top_ids`, `top_lp` with one entry per step of G's answer **including** the
end-token step (`len == len(G.tokens)`).

`L1확인_7b.jsonl` (50 items): the one-slot, cache-off `llama-server` generations used to validate the follower (§5.1). Same fields as L.

`갈래_7b.jsonl` (259: 100 O, 100 R, 59 C): forced-token continuations (propagation, §4.5). At fragile step `t` of item `문항`, the
abnormal token `b` of type `유형` (O / R / C) was appended to G's prefix and up to 256 tokens were generated by G. `id` = `문항@tO` etc.; `tokens`, `text`,
`finish`, `prompt_n` as above (no `top_*`).

`오염첫_7b.jsonl` (100): G's first answers of the contamination dialogs; `ids` = the prompt token ids. `오염둘_7b.jsonl` (400): the second
answers, four per dialog (`대화`): `종류` = `깨끗` (unchanged first answer), `다른문자` (one Chinese word inserted), `맞춤법` (one word
misspelled), `되풀이` (one sentence duplicated); `넣음` describes the injected anomaly (`자리` = position, `앞`/`뒤` = text before/after).
In 8 dialogs the `맞춤법` injection failed (Appendix B); those records equal the clean ones.

`재현G_7b.jsonl`, `재현V_7b.jsonl` (50 each): re-runs at concurrency 1 (`id`, `tokens`) — identical to the main runs (§5.1).
`재현갈래_7b.jsonl` (50): re-runs of forced continuations — identical.

### `따라/` — follower (llama.cpp at G's prefixes)

`7b/<id>.npz` (1,296) and `r1/<id>.npz` (600), NumPy archives with three arrays over the steps of G's answer (end-token step
excluded, so the length equals `len(G.top_ids)`):

| Array | Shape | Meaning |
|---|---|---|
| `lp` | (steps, 20) float32 | llama.cpp's natural-log probabilities of G's 20 top tokens at that step (same order as G's `top_ids[t]`) |
| `a1` | (steps,) int32 | llama.cpp's highest-probability token at that step |
| `a1lp` | (steps,) float32 | its log probability |

Obtained through llama.cpp's C API (build b11669): the prompt in one batch, then G's answer tokens one at a time, eight sequences
per batch. `확인_7b.json`: the validation against `L1확인_7b.jsonl` — 3,358 of 3,358 steps up to the first divergence agree.

### `위험/` — fragile steps

`7b.jsonl` (1,296), `r1.jsonl` (600): per item, `n` = number of steps examined and `걸음` = the fragile steps, each an 8-element list
`[t, 유형, a, b, 여유, bc, lpGb, lpGbc]`: step index, type (`O` other script, `R` repetition, `C` byte-split character), chosen token
`a`, abnormal candidate `b`, margin `여유` = ln p_G(a) − ln p_G(b) (< ln 10), the best *normal* alternative `bc` (control; `null` if
none in the top 20), and G's log probabilities of `b` and `bc`. Recomputable from `생성/G_*.jsonl` with `재기/셈40.py 위험`.

`갈래목록_7b.jsonl` (259): the steps sampled for propagation (seed 40; up to 100 per type — only 59 C steps existed on the copy trigger): `id`, `t`, `유형`, `a`, `b`, `여유`, `key`
(= id of the continuation in `생성/갈래_7b.jsonl`), `창` (continuation window, 256).

### `토큰/` — inputs

`7b.jsonl` (1,299: all Korean items, including the 3 overlong LCB prompts excluded from generation), `r1.jsonl` (1,200: gsm8k items
0–1199; only the first 600 were generated), `05b.jsonl` (2,499: Korean and gsm8k items tokenized for the dropped 0.5B model; unused). Fields: `id`, `묶음`, `ids` (the prompt token ids sent to every
arm — produced by llama.cpp's `/apply-template` and `/tokenize`), `최대` (maximum new tokens), `틀글끝` (the tail of the templated
prompt text, for inspection). `토큰_옛_BOS없음/`: the first tokenization of the R1 prompts, without the BOS token, discarded before any
measurement (Appendix B, item 3); kept for the record.

### `build/` — the engine as run

`서버.exe` (GeulPU server, CUDA path, Windows x86-64), `커널생성.exe` (kernel generator), the generated kernel sources `qwen2Q8_7b.gl`
(arm G and the contract) and `qwen2Q8_7b_자리하나.gl` (arm V), their PTX, and the small `*.판기억-*.txt` files recording the kernel
variants chosen on the reference GPU. `qwen2Q8.*` is the 0.5B module, unused. Hashes match the module-hash table of the repository
at the commit above and `문서/결과/40단계/40_기록.txt`.

## Recomputing the paper's numbers

1. Clone https://github.com/wwoosshh/GeulPU and check out commit `0a5ab97` (or later).
2. Extract the five archives into one directory `W`.
3. Put the two GGUF files in a directory `M` as `M/qwen7b.gguf` and `M/r1.gguf` (table above; check the SHA-256).
4. Python 3.12 with NumPy, from the repository root:

   ```
   python -I -X utf8 재기/셈40.py 모두 --작업 W --모델폴더 M --결과 OUT
   python -I -X utf8 재기/사후40.py --작업 W --모델폴더 M --결과 OUT
   ```

   The first writes `OUT/40_판정.json` (every number in §5 and Appendix B); the second `OUT/40_사후_S2엄격.json` (the strict judge,
   §5.6). Compare with `문서/결과/40단계/` in the repository. `재기/셈40.py 위험` regenerates `위험/*.jsonl` from `생성/G_*.jsonl`.
   The analysis reads only the vocabularies of the GGUF files; no GPU and no llama.cpp are needed for this step.
5. Replaying a case bit for bit (any record of G) needs the GeulPU engine and a supported GPU: the repository's documentation
   describes the server, the capsule format and the CPU reference. The follower (`재기/따라40.py`) needs llama.cpp b11669 and an
   NVIDIA GPU.

## Not included

- Server and tool logs (they contain local file-system paths). The run record with hashes and timings is in the repository:
  `문서/결과/40단계/40_기록.txt`.
- The Language Confusion Benchmark download (`test_sets.zip`): available from its source (GitHub `Cohere-Labs-Community/language-confusion`,
  commit `0cfdbb4a`); the derived prompts with their hashes are in the repository (`시험/질문40/`).
- The GGUF model files (8 GB each; sources and hashes above).

## Licenses and attribution

- This record (the author's prompts, the generated outputs and the derived tables): **CC BY 4.0**. The GeulPU executables and kernel
  sources in `build/`: MIT, as in the repository.
- The data contains outputs of Qwen2.5-7B-Instruct (Alibaba Cloud, Apache-2.0) and DeepSeek-R1-Distill-Qwen-7B (DeepSeek, MIT),
  prompt token ids derived from the Language Confusion Benchmark (Cohere, Apache-2.0; arXiv:2406.20052) and from gsm8k (OpenAI,
  MIT; arXiv:2110.14168), and continuations generated by llama.cpp (MIT).

## Citation

Woo, S. (2026). *Raw data — GeulPU stage 40: engine numerical loss and LLM failure symptoms* [Data set]. Zenodo.
https://doi.org/10.5281/zenodo.23417759
