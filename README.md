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
- **빠르다.** (RTX 4070 Ti) GPT-2 XL 프롬프트가 llama.cpp 의 0.78~0.87배, PyTorch f16 의 0.71~0.81배 시간; 생성 토큰당 llama.cpp 의
  0.54~0.93배(문맥 1024 안 — small 은 절반 남짓); 합성 긴 모델(위치 10만)에서 덩이 넣기 23 칸 모두 llama.cpp 보다 짧다(0.68~0.91배).
  문맥 10만 가까이의 생성은 llama.cpp 와 1% 안팎이다. 숫자와 재는 법은 [문서/단계기록.md](문서/단계기록.md).

## 지금 되는 것 · 안 되는 것 (2026-10)

| | |
|---|---|
| 모델 | GPT-2 (small 124M · XL 1.5B) — GGUF Q8_0 · Q4_0, 그리고 시험용 합성 긴 모델(위치 102400) |
| 실행 환경 | Windows + NVIDIA Ampere(RTX 30) 이상 + 드라이버 (이 저장소의 숫자는 RTX 4070 Ti 에서 잰 것). 호스트는 Python 3.12 + numpy |
| 아직 없는 것 | 채팅 모델(Llama 계열 — RoPE · RMSNorm · SwiGLU · GQA), k-양자화(Q4_K_M 등), 샘플링(지금은 탐욕), 터미널 실행기, Linux |

다음 단계는 Llama 계열의 첫 채팅 모델과 터미널 실행기다. 호스트도 나중에 글로 옮겨 "글 실행 파일 하나 + 드라이버" 로 만드는 것이 목표다.

## 구조

| 폴더 | 무엇 |
|---|---|
| [컴파일러/](컴파일러/) | `글ptx.py` — 글 소스 → (글 앞단: 파서 · 의미 분석) → 타입 IR → PTX. 글 앞단은 [글 참조 구현](https://github.com/wwoosshh/geul-lang)의 고정 사본(`ref/`) |
| [커널/](커널/) | `커널생성.py` — 모델의 커널 모듈(글 소스)을 만드는 생성기, `gpt2.gl` — 손으로 쓴 작은 커널들 |
| [엔진/](엔진/) | `글gpt2.py` — 드라이버 · 가중치 · 계획 · CUDA 그래프 · 생성 메가커널을 부르는 호스트, `gguf읽기.py`, `커널모듈.py` — 모듈을 만들고 PTX 를 캐시 |
| [계약/](계약/) | `정수계약.py` — 계약의 CPU 참조 구현(행렬곱 · 바꾸기 · KV 캐시 · 어텐션 — 모든 비트 대조의 기준) |
| [시험/](시험/) | 비트 시험 — 판 모두 대 CPU 참조, 길끼리(한 번에 · 하나씩 · 나눠 넣기 · 대화 · 메가커널), 캐시 바이트, 긴 문맥 |
| [재기/](재기/) | 속도 견주기 — llama.cpp(b11496 CUDA) · PyTorch |
| [준비/](준비/) | 모델 파일 만들기(GPT-2 → GGUF, 합성 긴 모델) |
| [문서/](문서/) | [계약](문서/계약.md) · [단계 기록](문서/단계기록.md) |

## 빠른 시작

1. **준비물**: Windows, NVIDIA 드라이버(Ampere 이상), Python 3.12, `pip install numpy`. (시험의 일부와 재기는 `torch`, 견주기는
   llama.cpp b11496 Windows CUDA 배포본을 `도구/llama-b11496/` 에.)
2. **모델**: `모델/` 에 둔다(저장소에는 없다).
   - `모델/gpt2/` — Hugging Face `openai-community/gpt2` 의 `model.safetensors` · `config.json` · `vocab.json` · `merges.txt`
     (XL 은 `openai-community/gpt2-xl` → `모델/gpt2-xl/`)
   - GGUF: `python 준비/gguf쓰기.py 모델/gpt2-f32.gguf` (XL 은 `--모델 모델/gpt2-xl`) → llama.cpp 의
     `llama-quantize 모델/gpt2-f32.gguf 모델/gpt2-q8_0.gguf q8_0` (q4_0 도 같게)
   - 합성 긴 모델(속도 · 비트 시험용): `python 준비/gguf쓰기.py 모델/gpt2-long/gpt2-long100k-f32.gguf --합성 102400` → `q8_0` 로
3. **시험**: `python 시험/모두.py 빠르게` — 있는 모델로 비트 시험을 모두 돌린다(마지막 줄 "모두 통과").
4. **생성** (지금은 파이썬에서):
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
[문서/단계기록.md](문서/단계기록.md).

## 라이선스

MIT — [LICENSE](LICENSE). 글 앞단 사본(`컴파일러/ref/`)도 같은 저자의 MIT.

---

**In short (English).** GeulPU is an LLM inference engine whose GPU kernels are written in the Korean programming language *geul* and
compiled to PTX by geul's own compiler; it runs on the NVIDIA driver alone (no CUDA toolkit, cuBLAS, or PyTorch). Precision is a
written contract (2-digit block integers for activations and the KV cache, exact integer tensor-core sums, a written exp polynomial), so
GPU results match a CPU reference bit for bit and stay identical however the input is split or batched. Today it runs GPT-2
(small/XL, GGUF Q8_0/Q4_0) faster than llama.cpp on an RTX 4070 Ti; Llama-family chat models and a terminal runner are next.
