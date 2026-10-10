# GeulPU — 의미를 지키는 GPU 추론 엔진

**글(geul)** 언어로 쓴 GPU 커널을 글 컴파일러가 PTX 로 바꿔 NVIDIA 드라이버에 바로 올리는 언어 모델 추론 엔진이다. CUDA 툴킷 ·
cuBLAS · PyTorch 없이, 그래픽 드라이버에 들어 있는 `nvcuda.dll` 하나로 돈다.

> 적힌 대로만 잃고, 느려지지 않는다.

## 무엇이 다른가

- **정밀도를 계약으로 밝힌다.** 활성값은 32 개 블록마다 자리 둘(±2¹⁴)의 정수, KV 캐시도 자리 둘 블록 정수, 곱의 합은 정수 텐서
  코어의 정확한 합, 지수 함수는 적어 둔 다항식(적힌지수). 그래서 GPU 의 결과가 CPU 참조 구현([계약/정수계약.py](계약/정수계약.py))과
  **비트까지** 같다. 손실은 모델 파일의 형식(Q8_0 · Q4_0)과 이 계약이 밝힌 만큼뿐이다.
- **어느 길로 계산해도 같은 비트.** 프롬프트를 한 번에 넣든, 나눠 넣든, 하나씩 넣든, 대화로 이어 가든, 여러 문장을 묶든 결과가 같다.
  흔한 엔진(llama.cpp · PyTorch)은 함께 계산하는 양에 따라 결과 비트가 바뀐다.
- **빠르다.** (RTX 4070 Ti) 채팅 모델 Qwen2.5-0.5B-Instruct(Q8_0)에서 llama.cpp 보다 프롬프트 128 ~ 8192 토큰이 0.55~0.82배 시간,
  생성 토큰당 0.80~0.87배 — 그러면서 숨은 손실(같은 가중치의 fp64 참값 대비 KL)이 llama.cpp 의 1/615 다. GPT-2 XL 프롬프트는
  llama.cpp 의 0.78~0.87배 · PyTorch f16 의 0.71~0.81배, 합성 긴 모델(위치 10만)의 덩이 넣기 23 칸 모두 llama.cpp 보다 짧다.
  숫자와 재는 법은 [문서/단계기록.md](문서/단계기록.md) · [문서/14단계.md](문서/14단계.md).

## 지금 되는 것 · 안 되는 것 (2026-10)

| | |
|---|---|
| 모델 | **Qwen2.5-0.5B-Instruct** (채팅 — Llama 계열 블록: RMSNorm · RoPE · SwiGLU · GQA) — 공식 GGUF Q8_0. GPT-2 (small 124M · XL 1.5B) — GGUF Q8_0 · Q4_0, 시험용 합성 긴 모델(위치 102400) |
| 터미널 실행기 | `python 실행.py 모델.gguf` — 채팅(ChatML), 답을 흘려 보이고, 차례마다 KV 캐시를 이어 쓴다. 탐욕(같은 대화면 같은 답) |
| 실행 환경 | Windows + NVIDIA Ampere(RTX 30) 이상 + 드라이버 (이 저장소의 숫자는 RTX 4070 Ti 에서 잰 것). 호스트는 Python 3.12 + numpy |
| 아직 없는 것 | 더 큰 Llama 계열(머리 128 · 다른 크기 — 커널이 모델의 모양으로 만들어지므로 모양마다 모듈이 필요하다), k-양자화(Q4_K_M 등), 샘플링(지금은 탐욕), Linux |

다음 단계는 생성 메가커널(생성의 바닥과의 거리 1.6배를 줄이기)과 더 많은 모델 모양이다. 호스트도 나중에 글로 옮겨 "글 실행 파일 하나 +
드라이버" 로 만드는 것이 목표다.

## 구조

| 폴더 | 무엇 |
|---|---|
| [컴파일러/](컴파일러/) | `글ptx.py` — 글 소스 → (글 앞단: 파서 · 의미 분석) → 타입 IR → PTX. 글 앞단은 [글 참조 구현](https://github.com/wwoosshh/geul-lang)의 고정 사본(`ref/`) |
| [커널/](커널/) | `커널생성.py` — 모델의 커널 모듈(글 소스)을 만드는 생성기, `gpt2.gl` — 손으로 쓴 작은 커널들 |
| [엔진/](엔진/) | `글qwen2.py` — Qwen2 호스트(프롬프트 · 줄 길 · 생성 그래프), `글gpt2.py` — 드라이버 · 가중치 · 계획 · CUDA 그래프 · 생성 메가커널(GPT-2), `토크나이저.py` — Qwen2 BPE · 채팅 틀(GGUF 안의 것으로), `gguf읽기.py`, `커널모듈.py` — 모듈을 만들고 PTX 를 캐시 |
| [계약/](계약/) | `정수계약.py` — 계약의 CPU 참조 구현(행렬곱 · 바꾸기 · KV 캐시 · 어텐션 — 모든 비트 대조의 기준) |
| [시험/](시험/) | 비트 시험 — 판 모두 대 CPU 참조, 길끼리(한 번에 · 하나씩 · 나눠 넣기 · 대화 · 메가커널), 캐시 바이트, 긴 문맥 |
| [재기/](재기/) | 속도 견주기 — llama.cpp(b11496 CUDA) · PyTorch |
| [준비/](준비/) | 모델 파일 만들기(GPT-2 → GGUF, 합성 긴 모델) |
| [문서/](문서/) | [계약](문서/계약.md) · [단계 기록](문서/단계기록.md) · [14단계 — 첫 채팅 모델](문서/14단계.md) |
| [실행.py](실행.py) | 터미널 실행기 |

## 빠른 시작

1. **준비물**: Windows, NVIDIA 드라이버(Ampere 이상), Python 3.12, `pip install numpy`. (시험의 일부와 재기는 `torch`, 견주기는
   llama.cpp b11496 Windows CUDA 배포본을 `도구/llama-b11496/` 에.)
2. **채팅**: Hugging Face `Qwen/Qwen2.5-0.5B-Instruct-GGUF` 의 `qwen2.5-0.5b-instruct-q8_0.gguf` (676 MB)를 받아
   ```
   python 실행.py qwen2.5-0.5b-instruct-q8_0.gguf
   ```
   처음에는 커널 모듈을 만들고 컴파일한다(1 분 남짓 — `빌드/` 에 캐시). 입력 한 줄이 한 차례, `/새로` 는 새 대화, `/끝` 은 나가기.
   시험(`시험/qwen2.py`)은 이 파일을 `모델/qwen2.5-0.5b-instruct-gguf/` 에서, 토크나이저 대조 · 참값은 원본(`Qwen/Qwen2.5-0.5B-Instruct`)을
   `모델/qwen2.5-0.5b-instruct/` 에서 찾는다.
3. **GPT-2 모델**: `모델/` 에 둔다(저장소에는 없다).
   - `모델/gpt2/` — Hugging Face `openai-community/gpt2` 의 `model.safetensors` · `config.json` · `vocab.json` · `merges.txt`
     (XL 은 `openai-community/gpt2-xl` → `모델/gpt2-xl/`)
   - GGUF: `python 준비/gguf쓰기.py 모델/gpt2-f32.gguf` (XL 은 `--모델 모델/gpt2-xl`) → llama.cpp 의
     `llama-quantize 모델/gpt2-f32.gguf 모델/gpt2-q8_0.gguf q8_0` (q4_0 도 같게)
   - 합성 긴 모델(속도 · 비트 시험용): `python 준비/gguf쓰기.py 모델/gpt2-long/gpt2-long100k-f32.gguf --합성 102400` → `q8_0` 로
4. **시험**: `python 시험/모두.py 빠르게` — 있는 GPT-2 모델로 비트 시험을 모두 돌린다(마지막 줄 "모두 통과"). Qwen2 는
   `python 시험/qwen2.py 빠르게`(CPU 참조의 전체 앞으로를 돌려 몇 분 걸린다 — torch 가 필요 없다).
5. **GPT-2 생성** (파이썬에서):
   ```python
   import sys; sys.path[:0] = ["엔진", "시험"]
   import 공통 as T
   m = T.글엔진("small", "q8_0")           # 처음에는 커널 모듈을 만들고 컴파일한다(수십 초 — 빌드/ 에 캐시)
   tk = T.토크나이저("small")
   print(tk.잇기(m.생성(tk.나누기("The meaning of life is"), 32)))
   ```

## 연구 기록

이 엔진은 2026-10-08 ~ 10-10 의 연구 0~13단계에서 나왔다. 단계마다 판정 기준을 실험보다 먼저 적고, 모든 변형을 비트 대조한 뒤에
시간을 적었다. 판정 · 측정 · 실패한 시도의 전문은 글 저장소의 `research/gpu` 가지(docs/17 · research/gpu/N단계)에 있고, 요약은
[문서/단계기록.md](문서/단계기록.md). 14단계(첫 채팅 모델)부터는 이 저장소에서 한다 — [문서/14단계.md](문서/14단계.md).

## 라이선스

MIT — [LICENSE](LICENSE). 글 앞단 사본(`컴파일러/ref/`)도 같은 저자의 MIT.

---

**In short (English).** GeulPU is an LLM inference engine whose GPU kernels are written in the Korean programming language *geul* and
compiled to PTX by geul's own compiler; it runs on the NVIDIA driver alone (no CUDA toolkit, cuBLAS, or PyTorch). Precision is a
written contract (2-digit block integers for activations and the KV cache, exact integer tensor-core sums, a written exp polynomial), so
GPU results match a CPU reference bit for bit and stay identical however the input is split or batched. It runs the chat model
Qwen2.5-0.5B-Instruct (official GGUF Q8_0) with a terminal runner (`python 실행.py model.gguf`) and GPT-2 (small/XL); on an RTX 4070 Ti
it is faster than llama.cpp at every measured prompt length (0.55-0.82x time) and decode context (0.80-0.87x), while its hidden loss
against an fp64 reference with the same weights is 1/615 of llama.cpp's.
