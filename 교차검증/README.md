# 교차 검증 — 다른 PC 에서도 같은 출력이 나오는가

GeulPU 는 계산을 정확한 정수 계약으로 해서, 같은 입력이면 어디서 어떻게 계산해도 같은 비트를 낸다고 주장한다. 이 폴더는 그 주장을
**다른 PC** 에서 확인하는 실험 묶음이다.

## 실험
- 모델: DeepSeek-R1-Distill-Qwen-7B Q8_0 — Hugging Face `unsloth/DeepSeek-R1-Distill-Qwen-7B-GGUF` 의
  `DeepSeek-R1-Distill-Qwen-7B-Q8_0.gguf` (8,098,524,896 바이트, SHA-256 `7307bfbb539fd2e8ed636315440781fed23140dc7f911f64b33418f5b978281b`)
- 문제: 정답을 코드로 계산한 수학 문제 32 개(`requests.json` — 씨앗 31 로 만든 합성 문제, 표준 벤치마크가 아니다)
- 생성: 탐욕(temperature 0), 답 길이 상한 3200 토큰. 프롬프트는 모든 PC 에 같은 토큰열(BOS + llama-server 의 대화 틀)
- 판정(실행 전에 적음): 다른 PC 의 출력 글이 32 문제 모두 기준(`expected.json`)과 같으면 통과. 하나라도 다르면 그 GPU · 드라이버와
  처음 갈린 자리를 그대로 기록한다.

## 기준 PC 에서 본 것 (2026-10-13, RTX 4070 Ti — 한 PC 안에서 함께 도는 요청 수 1 · 8)

| | llama.cpp b11567 | GeulPU |
|---|---|---|
| 두 조건의 출력 글이 같은 문제 | 0 / 32 | 32 / 32 |
| 최종 답이 바뀐 문제 | 6 | 0 |
| 정답 수 (함께 1 / 함께 8) | 19 / 16 | 20 / 20 |

같은 모델 · 같은 토큰 · 탐욕 생성인데, llama.cpp 는 함께 도는 요청 수만 바꿔도 모든 문제의 풀이가 갈렸다. 다른 GPU 에서도 GeulPU 가
같은지가 이 묶음으로 보려는 것이다.

## 다른 PC 에서 돌리는 법
1. [릴리스 crosscheck-r1-v1](https://github.com/wwoosshh/GeulPU/releases/tag/crosscheck-r1-v1) 에서 `geulpu-crosscheck-r1-v1.zip` 을 받는다.
2. zip 을 오른쪽 클릭 → 속성 → '차단 해제' 체크 → 확인. 압축을 푼다.
3. `run.bat` 을 더블클릭한다. 환경 검사 → 모델 받기(8.1 GB, 이미 있으면 폴더에 넣어 두면 건너뜀) → 생성 → 비교 → `result-….zip`.
4. `result-….zip` 을 보낸다.

필요: 윈도 10/11 64 비트, NVIDIA RTX 30 시리즈 이상(VRAM 12 GB 이상 권장 — 10 GB 는 슬롯을 줄여 느리게), 디스크 여유 9 GB.

## 환경 검사 (실행할 때마다 먼저)
운영체제(판 · 빌드), 모든 GPU 의 이름 · 연산 능력 · VRAM · 드라이버와 그 방식(WDDM/TCC) · VBIOS · PCIe · 최대 클럭 · 전력 한도,
nvcuda.dll 판 · CUDA 판, CPU · RAM, 디스크 여유, 하드웨어 가속 GPU 일정, 전원 계획, 묶음 파일이 원본과 같은가(SHA-256)를 보고
`environment.json` 에 남긴다. 실패가 있으면 생성하지 않고 환경 기록만 묶어 멈춘다. 사용자 이름 · 컴퓨터 이름 · GPU 고유번호는
넣지 않고, 서버 기록의 폴더 경로는 지운다.

## 묶음의 내용
- `run.ps1` · `run.bat` — 위 순서 전부. 서버는 127.0.0.1 에서만 열린다.
- `server_r1.exe` — 이 저장소 31a3b1b 의 `호스트/서버.gl` 에 [`토크나이저_R1.diff`](토크나이저_R1.diff) 만 더해 빌드한 것. 이 모델의
  `tokenizer.ggml.pre`(`deepseek-r1-qwen` — 바이트 BPE 의 앞자르기는 qwen2 와 같다)를 받고, 끝 토큰을 `<｜end▁of▁sentence｜>` 로 둔다.
  계산(커널)은 그대로다.
- `q8_7b.ptx` — 31a3b1b 의 7B Q8_0 모듈(`시험/모듈해시.txt` 의 `qwen2Q8_7b` 와 같은 해시 `a26545fb…`).
- `requests.json` · `expected.json` — 문제와 기준 출력. 실행할 때 걸음마다의 로짓 해시(`logit_hash`)도 받아 결과에 남긴다.
