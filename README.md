# GeulPU — 의미를 지키는 GPU 추론 엔진

*English: [README.en.md](README.en.md) · [docs/](docs/) — the contract, research log, hidden-loss measurements, how to reproduce,
glossary, and a short brief for outside reviewers.*

**글(geul)** 언어로 쓴 GPU 커널을 글 컴파일러가 PTX 로 바꿔 NVIDIA 드라이버에 바로 올리는 언어 모델 추론 엔진이다. CUDA 툴킷 ·
cuBLAS · PyTorch 없이, 그래픽 드라이버에 들어 있는 `nvcuda.dll` 하나로 돈다.

> 적힌 대로만 잃고, 느려지지 않는다.

## 무엇이 다른가

- **정밀도를 계약으로 밝힌다.** 활성값은 32 개 블록마다 자리 둘(±2¹⁴)의 정수, KV 캐시도 자리 둘 블록 정수, 곱의 합은 정수 텐서
  코어의 정확한 합, 지수 함수는 적어 둔 다항식(적힌지수). 그래서 GPU 의 결과가 CPU 참조 구현([계약/정수계약.py](계약/정수계약.py))과
  **비트까지** 같다. 손실은 모델 파일의 형식(Q8_0 · Q4_0)과 이 계약이 밝힌 만큼뿐이다.
- **어느 길로 계산해도 같은 비트.** 프롬프트를 한 번에 넣든, 나눠 넣든, 하나씩 넣든, 대화로 이어 가든, 여러 문장을 묶든 결과가 같다.
  흔한 엔진(llama.cpp · PyTorch)은 함께 계산하는 양에 따라 결과 비트가 바뀐다. 퍼플렉시티(wikitext-2)도 llama.cpp 는 배치 설정에 따라
  15.8171 ~ 15.8200 으로 바뀌고, 글은 어느 방식으로 넣어도 마지막 비트까지 같다([20단계](문서/20단계.md)).
- **빠르다.** (RTX 4070 Ti) 채팅 모델 Qwen2.5-0.5B-Instruct(Q8_0)에서 llama.cpp 보다 프롬프트 128 ~ 8192 토큰이 0.55~0.82배 시간,
  생성 토큰당 0.63~0.65배(생성 메가커널 — 1.26 ms, 가중치를 한 번 읽는 바닥의 1.21배) — 그러면서 숨은 손실(같은 가중치의 fp64 참값 대비
  KL)이 llama.cpp 의 1/615(평가글 461 토큰) · 1/385(wikitext-2 148,920 토큰)다. 퍼플렉시티로 보면 글은 참값과 구별되지 않고(상대
  −6.6 × 10⁻⁶), llama.cpp 는 0.34% 높다 — 가중치를 Q8_0 으로 줄인 손실(0.24%)과 같은 급이라 체감할 만큼은 아니다([20단계](문서/20단계.md)).
  GPT-2 XL 프롬프트는
  llama.cpp 의 0.78~0.87배 · PyTorch f16 의 0.71~0.81배, 합성 긴 모델(위치 10만)의 덩이 넣기 23 칸 모두 llama.cpp 보다 짧다.
  숫자와 재는 법은 [문서/단계기록.md](문서/단계기록.md) · [문서/14단계.md](문서/14단계.md) · [문서/15단계.md](문서/15단계.md).

## 지금 되는 것 · 안 되는 것 (2026-10)

| | |
|---|---|
| 모델 | **Qwen2.5-0.5B-Instruct** · **Qwen2.5-7B-Instruct** · **Qwen2.5-14B-Instruct** (채팅 — Llama 계열 블록: RMSNorm · RoPE · SwiGLU · GQA, 머리 크기 64 · 128) — GGUF Q8_0 · Q4_0 · **k-양자화(Q4_K · Q5_K · Q6_K — 텐서마다 형식이 다른 Q4_K_M · Q5_K_M · Q6_K 섞음 그대로, 26단계 — 이 PC 에서 다시 양자화한 파일로 시험)**. k-양자화도 CPU 참조와 비트까지 같고, 7B 생성은 llama.cpp 의 0.977 ~ 1.009배 시간(아홉 칸) — 14B Q4_K_M 생성 1.009 · 1.012배([26단계](문서/26단계.md)). 27단계에서 프롬프트의 타일 판을 고쳐(값은 비트까지 그대로) 7B 프롬프트가 llama.cpp 의 1.25 · 1.39배(Q4_K_M) · 1.37 · 1.49배(Q5_K_M) · 1.45 · 1.56배(Q6_K) · 1.13 · 1.29배(Q4_0) · 1.14 · 1.30배(Q8_0)다(2048 · 8192, [27단계](문서/27단계.md)). 24단계부터 머리 크기 128 의 Qwen2 는 모양(너비 · 머리 · KV 머리 · 확장폭 · 낱말)을 GGUF 의 설정에서 받는다 — 14B 는 실제로(llama.cpp 대비 생성 0.982 · 0.986 · 0.994배, 프롬프트 1.22 · 1.34배), 이 PC 에 들지 않는 32B · 72B 모양은 층을 줄인 합성 모델로 비트까지 시험했다([24단계](문서/24단계.md)). 7B 는 22단계부터, Q4_0 은 23단계부터: CPU 참조와 비트까지 같고, llama.cpp(같은 GGUF) 대비 생성 0.97 ~ 0.99배 시간(Q8_0 0.980 ~ 0.990 · Q4_0 0.970 ~ 0.985 — 문맥 짧을 때 · 2048 · 8192), 프롬프트는 23단계에 1.15 · 1.30배(Q8_0) · 1.23 · 1.38배(Q4_0, 2048 · 8192)였다 ([22단계](문서/22단계.md) · [23단계](문서/23단계.md)). GPT-2 (small 124M · XL 1.5B) — GGUF Q8_0 · Q4_0, 시험용 합성 긴 모델(위치 102400) |
| 터미널 실행기 | `빌드/글/실행기.exe 모델.gguf` — 글(geul) 언어 프로그램(18단계). 채팅(ChatML), 답을 흘려 보이고, 차례마다 KV 캐시를 이어 쓴다. 탐욕(같은 대화면 같은 답). 프롬프트까지 약 0.3 초(일꾼 스레드로 겹쳐 올린다 — 파이썬판은 2.9 초). 파이썬판 `python 실행.py 모델.gguf` 도 같은 답 |
| 실행 환경 | Windows + NVIDIA Ampere(RTX 30) 이상 + 드라이버 (이 저장소의 숫자는 RTX 4070 Ti 에서 잰 것). 실행기는 글 실행 파일 하나 + nvcuda.dll — 파이썬이 들지 않는다. 빌드(생성기 → 커널 소스 → PTX → 실행기)도 글 컴파일러만으로(19단계). 시험 · 재기 · 파이썬 연구 엔진(GPT-2)은 Python 3.12 + numpy |
| 층 나누기 | 25단계 — 한 GPU 에 들지 않는 모델을 층으로 나눠 여러 GPU 에(`--나누기 P` · `--장치 a,b,…` · `--예산 GB`). 이 PC 에는 GPU 가 한 장이라 한 장 안의 여러 쿠다 문맥으로 흉내 냈다: 나눠 돌린 길 16 개가 한 조각과 바이트까지 같고, 7B 두 조각의 생성은 한 조각의 1.025 ~ 1.029 배(조각마다 문맥 — 그 차이의 대부분은 한 GPU 에서 문맥을 오가는 흉내의 값) · 1.002 ~ 1.003 배(문맥 하나). 14B 두 조각은 12 GB 한 장에 문맥 8192 로 들지 않아 그 칸을 재지 못했다 — 판정 25c 는 통과하지 못함([25단계](문서/25단계.md)) |
| 아직 없는 것 | 실제 여러 GPU 에서의 층 나누기(이 PC 에서는 흉내뿐), 계약의 손실을 7B 이상의 실제 엔진 출력으로 fp64 참값과 견주기(실제로 잰 것은 0.5B — 7B · 14B 는 반올림 자리만 흉내 낸 fp64 계산으로 검토했다: llama.cpp 식의 1/3805 · 1/4467, [계약손실검토](문서/계약손실검토.md)), k-양자화의 Q2_K · Q3_K · IQ 계열 · Q5_0(실제 72B 의 k-양자화 파일은 ffn_down 이 Q5_0 · Q8_0 이라 아직 돌지 않는다), MoE, 샘플링(지금은 탐욕), 서버 기능, Linux, 다른 GPU 에서의 재현 |

다음은 MoE · 서버 기능, 프롬프트의 남은 거리(특히 k-양자화의 타일 판 — Q6_K 는 정수 텐서 일이 두 배), 생성의 바닥까지 남은 거리다. 공식 실행 스크립트(빌드부터 판정의 값까지)는
[공식실행/](공식실행/)에 있다. **실행에는 파이썬이 들지 않는다**(18단계): 채팅 실행기는 글(geul) 언어 프로그램(`호스트/*.gl`)을
글의 자체 호스팅 컴파일러로 빌드한 실행 파일 하나이고, 가져오는 DLL 은 `kernel32` · `shell32`(글 런타임)과 `nvcuda.dll` 뿐이다. GPU 커널의 PTX 는
글로 쓴 PTX 뒷단이 만든다(17단계). 파이썬 호스트(`엔진/` · `실행.py`)와 견줘 GPU 에 올리는 것 · 토큰 · 걸음마다 로짓 · KV 캐시 · 대화가 바이트까지
같고 속도도 같다([문서/18단계.md](문서/18단계.md)). **빌드에도 파이썬이 들지 않는다**(19단계): 커널 소스(글)를 만드는 생성기도 글 언어
([커널/커널생성.gl](커널/커널생성.gl))로 옮겼다. 파이썬 생성기와 바이트까지 같은 소스를 0.04 초에 낸다(파이썬판은 0.09 초) — Qwen2 채팅은
빌드부터 실행까지 글 컴파일러와 nvcuda.dll 만으로 된다([문서/19단계.md](문서/19단계.md)). 남은 파이썬은 대조 · 시험 · 재기 도구와 GPT-2 연구 엔진이다.

## 구조

| 폴더 | 무엇 |
|---|---|
| [컴파일러/](컴파일러/) | 파이썬판 `글ptx.py`(1~16단계의 PTX 를 냈다 — 이제 대조용) — 글 소스 → (글 앞단: 파서 · 의미 분석) → 타입 IR → PTX. 글 앞단은 [글 참조 구현](https://github.com/wwoosshh/geul-lang)의 고정 사본(`ref/`). 엔진이 쓰는 PTX 는 글로 쓴 뒷단(글 저장소 [research/gpu/자체PTX/](https://github.com/wwoosshh/geul-lang/tree/research/gpu/research/gpu/자체PTX))이 만든다 |
| [커널/](커널/) | `커널생성.gl` · `생성*.gl` — Qwen2 커널 모듈(글 소스)을 만드는 글 언어 생성기(19단계 — 파이썬판과 바이트까지 같다), `커널생성.py` — 파이썬 생성기(GPT-2 모듈 · 파이썬 엔진 · 정답지), `gpt2.gl` — 손으로 쓴 작은 커널들 |
| [엔진/](엔진/) | `글qwen2.py` — Qwen2 호스트(프롬프트 · 줄 길 · 생성 메가커널 · 대조용 생성 그래프), `글gpt2.py` — 드라이버 · 가중치 · 계획 · CUDA 그래프 · 생성 메가커널(GPT-2), `토크나이저.py` — Qwen2 BPE · 채팅 틀(GGUF 안의 것으로), `gguf읽기.py`, `커널모듈.py` — 모듈을 만들고 PTX 를 캐시 |
| [계약/](계약/) | `정수계약.py` — 계약의 CPU 참조 구현(행렬곱 · 바꾸기 · KV 캐시 · 어텐션 — 모든 비트 대조의 기준) |
| [시험/](시험/) | 비트 시험 — 판 모두 대 CPU 참조, 길끼리(한 번에 · 하나씩 · 나눠 넣기 · 대화 · 메가커널), 캐시 바이트, 긴 문맥 |
| [재기/](재기/) | 속도 견주기 — llama.cpp(b11496 CUDA) · PyTorch |
| [준비/](준비/) | 모델 파일 만들기(GPT-2 → GGUF, 합성 긴 모델) |
| [문서/](문서/) | [계약](문서/계약.md) · [단계 기록](문서/단계기록.md) · [14단계 — 첫 채팅 모델](문서/14단계.md) |
| [호스트/](호스트/) | 글(geul) 언어 호스트 — `실행기.gl`(터미널 실행기), `엔진.gl` · `가중치.gl` · `로프.gl` · `토크나이저.gl` · `gguf.gl` · `쿠다.gl` · `일꾼.gl`(겹친 올림), 시험 · 재기의 글 쪽 |
| [실행.py](실행.py) | 파이썬 터미널 실행기(대조용 — 글 실행기와 같은 답) |

## 빠른 시작

1. **준비물**: Windows, NVIDIA 드라이버(Ampere 이상). 채팅만 하려면 이것과 글 컴파일러로 충분하다. 시험 · 재기 · GPT-2 는 Python 3.12 와
   `pip install numpy` 가 더 든다(시험의 일부와 재기는 `torch`, 견주기는 llama.cpp b11496 Windows CUDA 배포본을 `도구/llama-b11496/` 에).
2. **글 컴파일러와 PTX 뒷단**: 글 저장소의 `research/gpu` 가지를 이 저장소 옆 `../geul-lang-v2` 에 받는다(PTX 뒷단의 소스). 컴파일러는 둘 중
   하나를 쓴다.
   - 자체 호스팅 컴파일러를 소스에서 만든다(아래 `python build.py selfhost 컴파일러` — 1세대는 파이썬 참조 구현이 만들고 고정점을 확인한다).
   - 글 배포판([Releases](https://github.com/wwoosshh/geul-lang/releases) — 1.2.1)의 `geulc.exe`(자기 컴파일한 실행 파일)를 쓴다. 이때는 파이썬이
     들지 않는다. 아래의 `build/self_컴파일러.exe` 자리에 `geulc.exe` 를 쓰면 되고, 만든 실행 파일은 바이트까지 같다(이 PC 의 1.2.1 배포 폴더로
     확인 — 19단계).

   PTX 뒷단을 다른 자리에 두면 파이썬 엔진이 찾도록 환경변수 `GEULPU_글뒷단` 에 실행 파일의 경로를 준다.
   ```
   git clone -b research/gpu https://github.com/wwoosshh/geul-lang ../geul-lang-v2
   cd ../geul-lang-v2
   python build.py selfhost 컴파일러
   GEUL_ROOT=. build/self_컴파일러.exe research/gpu/자체PTX/PTX.gl -o build/자체PTX.exe
   ```
3. **채팅**: Hugging Face `Qwen/Qwen2.5-0.5B-Instruct-GGUF` 의 `qwen2.5-0.5b-instruct-q8_0.gguf` (676 MB)를 받는다. 글 언어의 커널 생성기와
   실행기를 빌드하고, 생성기가 낸 커널 소스를 PTX 뒷단으로 PTX 로 바꿔 실행기 옆에 둔다. 생성은 0.04 초, PTX 는 약 26 초가 걸린다.
   ```
   mkdir -p 빌드/글
   GEUL_ROOT=../geul-lang-v2 ../geul-lang-v2/build/self_컴파일러.exe 커널/커널생성.gl -o 빌드/글/커널생성.exe
   GEUL_ROOT=../geul-lang-v2 ../geul-lang-v2/build/self_컴파일러.exe 호스트/실행기.gl -o 빌드/글/실행기.exe
   빌드/글/커널생성.exe qwen2Q8 빌드/글/qwen2Q8.gl
   ../geul-lang-v2/build/자체PTX.exe 빌드/글/qwen2Q8.gl -o 빌드/글/qwen2Q8.ptx
   빌드/글/실행기.exe qwen2.5-0.5b-instruct-q8_0.gguf
   ```
   7B(Hugging Face `Qwen/Qwen2.5-7B-Instruct-GGUF` 의 `qwen2.5-7b-instruct-q8_0*.gguf` — 나뉜 파일은 llama.cpp 의 `llama-gguf-split --merge` 로
   하나로)는 7B 모듈을 더 만든다. 실행기가 GGUF 의 설정을 읽고 옆의 PTX 를 고른다(22단계).
   ```
   빌드/글/커널생성.exe qwen2Q8_7b 빌드/글/qwen2Q8_7b.gl
   ../geul-lang-v2/build/자체PTX.exe 빌드/글/qwen2Q8_7b.gl -o 빌드/글/qwen2Q8_7b.ptx
   빌드/글/실행기.exe qwen2.5-7b-instruct-q8_0.gguf
   ```
   7B Q4_0(23단계 — 모든 텐서가 Q4_0 인 GGUF: 공식 q4_0 은 출력이 Q6_K 라, Q8_0 에서 llama.cpp 의
   `llama-quantize --allow-requantize --pure 7b-q8_0.gguf 7b-q4_0-pure.gguf Q4_0` 으로 만든다)은 Q4_0 모듈을 더 만든다.
   ```
   빌드/글/커널생성.exe qwen2Q4_7b 빌드/글/qwen2Q4_7b.gl
   ../geul-lang-v2/build/자체PTX.exe 빌드/글/qwen2Q4_7b.gl -o 빌드/글/qwen2Q4_7b.ptx
   빌드/글/실행기.exe qwen2.5-7b-instruct-q4_0-pure.gguf
   ```
   다른 모양(24단계 — 머리 크기 128 의 Qwen2: 14B 등)은 `qwen2큰` 에 모양을 주어 만든다. 실행기는 GGUF 의 모양에서 모듈 이름
   `qwen2{Q8|Q4}_{너비}x{머리}x{KV 머리}x{확장폭}x{낱말}.ptx` 를 찾고, 없으면 이 명령을 알린다. 14B Q4_0:
   ```
   빌드/글/커널생성.exe qwen2큰 Q4_0 5120 40 8 13824 152064 빌드/글/qwen2Q4_5120x40x8x13824x152064.gl
   ../geul-lang-v2/build/자체PTX.exe 빌드/글/qwen2Q4_5120x40x8x13824x152064.gl -o 빌드/글/qwen2Q4_5120x40x8x13824x152064.ptx
   빌드/글/실행기.exe qwen2.5-14b-instruct-q4_0-pure.gguf
   ```
   k-양자화(26단계 — Q4_K_M · Q5_K_M · Q6_K 등, 행렬마다 Q4_K · Q5_K · Q6_K 의 아무 섞음)는 형식 자리에 `K` 를 준 모듈 하나가 세 형식의 판을
   모두 담는다(모듈 이름 `qwen2K_{모양}.ptx`). 시험한 파일은 이 PC 에서 7B Q8_0 을 다시 양자화해 만든 것이다
   (`llama-quantize --allow-requantize 7b-q8_0.gguf 7b-q4_k_m-req.gguf Q4_K_M` — 섞는 규칙은 공식 파일과 같고, 공식 파일은 아직 돌려 보지 않았다). 7B:
   ```
   빌드/글/커널생성.exe qwen2큰 K 3584 28 4 18944 152064 빌드/글/qwen2K_3584x28x4x18944x152064.gl
   ../geul-lang-v2/build/자체PTX.exe 빌드/글/qwen2K_3584x28x4x18944x152064.gl -o 빌드/글/qwen2K_3584x28x4x18944x152064.ptx
   빌드/글/실행기.exe qwen2.5-7b-instruct-q4_k_m-req.gguf
   ```
   여러 GPU 에 층을 나눠 싣기(25단계): `빌드/글/실행기.exe 모델.gguf --장치 0,1` (장치마다 조각 하나), 장치마다 쓸 메모리를 정하면 `--예산 GB`
   (나누는 자리를 예산 안에서 앞부터), 한 GPU 에서 흉내는 `--나누기 P`. 이 PC 에서는 한 장 안의 흉내만 시험했다.
   입력 한 줄이 한 차례, `/새로` 는 새 대화, `/끝` 은 나가기. 파이썬 실행기(`python 실행.py 모델.gguf` — 0.5B 만)도 같은 답을 낸다.
   시험(`시험/qwen2.py`)은 이 파일을 `모델/qwen2.5-0.5b-instruct-gguf/` 에서, 토크나이저 대조 · 참값은 원본(`Qwen/Qwen2.5-0.5B-Instruct`)을
   `모델/qwen2.5-0.5b-instruct/` 에서 찾는다.
4. **GPT-2 모델**: `모델/` 에 둔다(저장소에는 없다).
   - `모델/gpt2/` — Hugging Face `openai-community/gpt2` 의 `model.safetensors` · `config.json` · `vocab.json` · `merges.txt`
     (XL 은 `openai-community/gpt2-xl` → `모델/gpt2-xl/`)
   - GGUF: `python 준비/gguf쓰기.py 모델/gpt2-f32.gguf` (XL 은 `--모델 모델/gpt2-xl`) → llama.cpp 의
     `llama-quantize 모델/gpt2-f32.gguf 모델/gpt2-q8_0.gguf q8_0` (q4_0 도 같게)
   - 합성 긴 모델(속도 · 비트 시험용): `python 준비/gguf쓰기.py 모델/gpt2-long/gpt2-long100k-f32.gguf --합성 102400` → `q8_0` 로
5. **시험**: `python 시험/모두.py 빠르게` — 있는 GPT-2 모델로 비트 시험을 모두 돌린다(마지막 줄 "모두 통과"). Qwen2 는
   `python 시험/qwen2.py 빠르게`(CPU 참조의 전체 앞으로를 돌려 몇 분 걸린다 — torch 가 필요 없다).
6. **GPT-2 생성** (파이썬에서):
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
[문서/단계기록.md](문서/단계기록.md). 14단계(첫 채팅 모델)부터는 이 저장소에서 한다 — [14단계](문서/14단계.md) ·
[15단계 — 생성 메가커널](문서/15단계.md) · [16단계 — 자체 컴파일러 PTX 탐침](문서/16단계.md) · [17단계 — 모델 커널을 글 컴파일러로](문서/17단계.md) ·
[18단계 — 호스트를 글로](문서/18단계.md) · [19단계 — 커널 생성기를 글로](문서/19단계.md) · [20단계 — 퍼플렉시티로 본 숨은 손실](문서/20단계.md) ·
[21단계 — 7B 의 행렬곱](문서/21단계.md) · [22단계 — 7B 전체](문서/22단계.md) · [23단계 — 4비트(Q4_0)](문서/23단계.md) ·
[24단계 — 설정에서 모양](문서/24단계.md) · [25단계 — 층 나누기](문서/25단계.md) · [계약 손실 검토](문서/계약손실검토.md) ·
[26단계 — k-양자화](문서/26단계.md).

## 점검 — 커밋마다의 빠른 점검(CI)과 단계마다의 공식 실행

[![빠른 점검](https://github.com/wwoosshh/GeulPU/actions/workflows/ci.yml/badge.svg)](https://github.com/wwoosshh/GeulPU/actions/workflows/ci.yml)

- **빠른 점검**(커밋마다, GPU · 모델 파일 없이 — GitHub Actions 의 Windows 러너, 5분 안팎, [시험/빠른점검.py](시험/빠른점검.py)). 글 컴파일러는
  CPU 프로그램이라 커널 소스 → PTX 까지는 GPU 없이 만든다: 글 저장소의 고정 커밋([시험/글저장소커밋.txt](시험/글저장소커밋.txt))에서 글 컴파일러와
  PTX 뒷단을 빌드하고, 생성기와 호스트 프로그램 모두를 빌드하고, 모듈 여섯(0.5B · 7B Q8_0 · Q4_0 · 14B Q4_0 · 7B · 14B k-양자화)을 처음부터
  만들어 소스와 PTX 를 [시험/모듈해시.txt](시험/모듈해시.txt) 와 바이트까지 견준다(커널이 뜻하지 않게 바뀌면 걸린다 — 일부러 바꾼 커밋은
  `--해시갱신`). NVIDIA ptxas(검사에만 — 엔진은 쓰지 않는다)로 SASS(sm_89)까지 만들어 커널마다 레지스터 · 넘침(spill)을 적는다. 그 밖에 계약의
  CPU 참조 자체 시험(정확한 유리수 셈 · 느린 참조 대 블라스 · 날 블록에서 값 하나씩 — [시험/계약자체.py](시험/계약자체.py)), 판 표가
  생성기 · 호스트 · 시험에서 같은가, 실행기의 가져오기 표(kernel32 · shell32 · nvcuda 뿐), 파이썬 · 셸 문법. 이 PC 에서도 같은 것을 돈다:
  `python -X utf8 시험/빠른점검.py`.
- **공식 실행**(단계마다, GPU — [공식실행/](공식실행/)): 판 · 다섯 길 · CPU 참조의 끝에서 끝 비트 대조와 속도. 판정 기준은 결과보다 먼저 적는다.

## 라이선스

MIT — [LICENSE](LICENSE). 글 앞단 사본(`컴파일러/ref/`)도 같은 저자의 MIT.

---

**In short (English).** GeulPU is an LLM inference engine whose GPU kernels are written in the Korean programming language *geul* and
compiled to PTX by geul's own backend; the host (GGUF loading, weight layout, RoPE tables, tokenizer, CUDA graphs, terminal runner) and the
kernel-source generator are geul too, so the chat runner is a single executable that imports only kernel32, shell32 and nvcuda.dll (Python
remains for the CPU reference, tests and benchmarks). Precision is a written contract — activations and the KV cache are 2-digit block
integers (2^-14 of the block maximum, 128x finer than llama.cpp's 8-bit activations), sums are exact integer tensor-core sums, exp is a
written polynomial — so GPU results match a CPU reference bit for bit and stay identical however the input is split or batched (batch- and
split-invariant). On an RTX 4070 Ti: Qwen2.5-0.5B-Instruct Q8_0 is faster than llama.cpp b11496 at every prompt length (0.55-0.82x time) and
decode context (0.63-0.65x), with a hidden loss against an fp64 reference of the same weights 1/615 of llama.cpp's (perplexity
indistinguishable from fp64; llama.cpp +0.34%). Qwen2.5-7B-Instruct (Q8_0, Q4_0) and 14B (Q4_0) run bit-exact to the CPU reference: decode
0.97-0.99x llama.cpp's time, prompt 1.15-1.38x (stages 22-24); shapes are read from the GGUF config (32B/72B tested on 4-layer synthetic
models). Stage 25 adds layer splitting across GPUs (`--장치 0,1`), emulated on one GPU with one CUDA context per part: 16 split runs are
bit-identical to the single-part run; 7B decode with two parts takes 1.025-1.029x the single-part time (mostly the one-GPU context-switch
cost of the emulation; 1.002-1.003x with a shared context), and 14B with two parts did not fit at context 8192 on 12 GB, so that cell of the
pre-registered speed check was not measured. A contract-loss review simulated only the rounding points in an fp64 forward pass: at 7B and
14B the contract's loss is 1/3805 and 1/4467 of a llama.cpp-like pipeline, with attention probabilities the one place at f16 level.
Stage 26 adds k-quants (Q4_K, Q5_K, Q6_K, with a per-tensor format mix as in Q4_K_M/Q5_K_M/Q6_K files, requantized on this PC): kernels and
end-to-end logits are bit-exact to the CPU reference, 7B decode takes 0.977-1.009x llama.cpp's time in all nine cells. Stage 27 reworked
the prompt tile kernels without changing a bit (one m16n8k16 integer MMA per Q6_K sub-block, a magic-number accumulator for Q4_0/Q4_K, hoisted
prefetch addressing): 7B prompts now take 1.13-1.30x (Q4_0, Q8_0) and 1.25-1.56x (k-quants) llama.cpp's time. Not yet: real multi-GPU runs, measuring
the contract's loss with the real engine on 7B+ weights (done for 0.5B), Q2_K/Q3_K/IQ/Q5_0, MoE, sampling (greedy only), server features,
Linux, and reproduction on another GPU.
Every stage pre-registers its criteria before measuring and keeps failures (see 문서/단계기록.md; English: [docs/research-log.md](docs/research-log.md));
run scripts are in 공식실행/. Full English README: [README.en.md](README.en.md); contract, reproduction guide, glossary and a brief for
reviewers: [docs/](docs/).
