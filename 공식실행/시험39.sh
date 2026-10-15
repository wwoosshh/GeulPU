#!/bin/bash
# 39단계 비트 시험 · 대조(문서/39단계.md) — 고정한 코드(커밋)와 그 빌드로. 사전 등록대로 2 ~ 3 시간짜리 공식 속도 측정은 하지 않는다(속도는
# 기록 한 번). 결과는 문서/결과/39단계/ 에(로짓 등 큰 파일은 작업 폴더에).
#   bash 공식실행/시험39.sh <저장소> <작업폴더> <모델폴더> <llama.cpp 판 폴더> [단계 …]
#   단계(없으면 모두, 이 차례로): 빌드 로프 끝에서끝 공유32 합성 그대로 독립 토크나이저 틀 속도 참조 합성참조
# 모델폴더: bartowski 의 GGUF 다섯(Meta-Llama-3.1-8B-Instruct-Q4_K_M · Q8_0, Llama-3.2-3B-Instruct-Q8_0, Mistral-7B-Instruct-v0.3-Q4_K_M · Q8_0)
#   과 합성/ (준비/합성qwen2.py · llama-quantize 로 — 단계 '합성' 이 없으면 만든다). 옛 모델(Qwen)은 저장소의 모델/ 에서.
# 서버(토크나이저 · 틀)는 포트 18391 에 띄웠다 끈다. jinja2 는 WSL 의 Ubuntu-24.04 파이썬(3.1.2)으로 그린다.
set -u
R="$1"; W="$2"; M="$3"; LL="$4"; shift 4
STEPS=("$@")
[ ${#STEPS[@]} -eq 0 ] && STEPS=(빌드 로프 끝에서끝 공유32 합성 그대로 독립 토크나이저 틀 속도 참조 합성참조)
OUT="$R/문서/결과/39단계"
GL="$R/../geul-lang-v2"
GC="$GL/build/self_컴파일러.exe"
PX="$GL/build/자체PTX.exe"
SV="$GL/build/자체SPIRV.exe"
LT="$LL/llama-tokenize.exe"
LB="$LL/llama-bench.exe"
B="$W/build"
MS="$M/합성"
OLD=3f0bff0                    # 39단계 직전(코드는 38단계 그대로) — 그대로(39c (2))의 견줄 판
cd "$R" || exit 1
mkdir -p "$OUT" "$B" "$W" "$MS"
L="$OUT/39_기록.txt"
기록() { echo "$*" >> "$L"; }
[ -f "$L" ] || 기록 "시작 $(date '+%F %T') · 커밋 $(git rev-parse --short HEAD) · 바뀐 파일 $(git status --short | grep -v '^??' | wc -l) · 글 저장소 $(git -C "$GL" rev-parse --short HEAD) (바뀐 파일 $(git -C "$GL" status --short | grep -v '^??' | wc -l))"
기록 "== 단계 ${STEPS[*]} — $(date '+%F %T') · 커밋 $(git rev-parse --short HEAD) · 바뀐 파일 $(git status --short | grep -v '^??' | wc -l)"

F31Q4="$M/Meta-Llama-3.1-8B-Instruct-Q4_K_M.gguf"; F31Q8="$M/Meta-Llama-3.1-8B-Instruct-Q8_0.gguf"; F32Q8="$M/Llama-3.2-3B-Instruct-Q8_0.gguf"
FMQ4="$M/Mistral-7B-Instruct-v0.3-Q4_K_M.gguf"; FMQ8="$M/Mistral-7B-Instruct-v0.3-Q8_0.gguf"
파일() { case "$1" in 31q4) echo "$F31Q4" ;; 31q8) echo "$F31Q8" ;; 32q8) echo "$F32Q8" ;; mq4) echo "$FMQ4" ;; mq8) echo "$FMQ8" ;; esac; }
모듈() { case "$1" in 31q4) echo llamaK_4096x32x8x14336x128256 ;; 31q8) echo llamaQ8_4096x32x8x14336x128256 ;; 32q8) echo llamaQ8_3072x24x8x8192x128256 ;;
                      mq4) echo llamaK_4096x32x8x14336x32768 ;; mq8) echo llamaQ8_4096x32x8x14336x32768 ;; esac; }
입력() { case "$1" in mq4|mq8) echo "$W/입력M.bin" ;; *) echo "$W/입력L3.bin" ;; esac; }
FIVE=(31q4 31q8 32q8 mq4 mq8)
같은가() {   # 폴더 둘 — 경우 0 … 2 의 로짓 · 토큰 파일과 요약
  local a="$1" b="$2" i
  for i in 0 1 2; do
    cmp -s "$a/경우${i}_로짓.bin" "$b/경우${i}_로짓.bin" || { echo 다름; return; }
    cmp -s "$a/경우${i}_토큰.bin" "$b/경우${i}_토큰.bin" || { echo 다름; return; }
  done
  cmp -s "$a/요약.txt" "$b/요약.txt" && echo "같음(로짓 · 토큰 · 요약)" || echo "로짓 · 토큰 같음, 요약 다름"
}
모듈만들기() {   # 이름 생성기인자… [--공유32]
  local m="$1"; shift
  "$B/커널생성.exe" "$@" > "$W/gen_$m.log" 2>&1
}
서버띄우기() {   # gguf 모듈경로 → 전역 SP(프로세스)
  "$B/서버.exe" "$1" --ptx "$2" --포트 18391 --슬롯 1 --문맥 2048 --이름 시험39 > "$W/서버_$(basename "$1").log" 2>&1 &
  SP=$!
  for _ in $(seq 1 120); do curl -s -m 2 http://127.0.0.1:18391/health > /dev/null 2>&1 && return 0; sleep 2; done
  기록 "서버가 뜨지 않았다: $1"; return 1
}
서버끄기() { kill "$SP" 2> /dev/null; wait "$SP" 2> /dev/null; sleep 3; }

for STEP in "${STEPS[@]}"; do
case "$STEP" in
빌드)
  기록 "빌드 시작 $(date '+%T')"
  nvidia-smi --query-gpu=name,driver_version,clocks.max.sm,clocks.max.mem,memory.total --format=csv >> "$L"
  "$LB" --version >> "$L" 2>&1
  sha256sum "$GC" "$PX" "$SV" "$LT" "$LB" "$LL/llama.dll" "$LL/ggml-cuda.dll" | sed "s#$GL/#../geul-lang-v2/#; s#$R/#./#; s#$LL/#llama.cpp/#" >> "$L"
  GEUL_ROOT="$GL" "$GC" 커널/커널생성.gl -o "$B/커널생성.exe" >> "$L" 2>&1
  for t in 시험_7B 시험_7BV 시험_로프 재기_7B 실행기 서버; do
    GEUL_ROOT="$GL" "$GC" "호스트/$t.gl" -o "$B/$t.exe" >> "$L" 2>&1 || 기록 "빌드 실패 $t"
  done
  # 모듈: 다섯 파일(PTX · SPIR-V), 3B 공유32(SPIR-V), 합성 70B 모양 둘(PTX)
  while read -r m ARGS; do
    [ -z "$m" ] && continue
    FLAG=""; case "$m" in *_공유32) FLAG="--공유32" ;; esac
    # shellcheck disable=SC2086
    "$B/커널생성.exe" $ARGS "$B/$m.gl" $FLAG > "$W/gen_$m.log" 2>&1
    "$PX" "$B/$m.gl" -o "$B/$m.ptx" > "$W/ptx_$m.log" 2>&1; 기록 "PTX $m 종료 $?"
    case "$m" in *8192x64*) ;; *) "$SV" "$B/$m.gl" -o "$B/$m.spvs" > "$W/spv_$m.log" 2>&1; 기록 "SPIR-V $m 종료 $?" ;; esac
    ROW=$(grep "^$m |" 시험/모듈해시.txt)
    if [ -n "$ROW" ]; then
      h="$(sha256sum "$B/$m.gl" | cut -c1-64) | $(sha256sum "$B/$m.ptx" | cut -c1-64) | $(sha256sum "$B/$m.spvs" | cut -c1-64)"
      if echo "$ROW" | grep -q "$h"; then 기록 "모듈 $m — 소스 · PTX · SPIR-V 가 빠른 점검의 해시와 같다"; else 기록 "모듈 $m — 빠른 점검의 해시와 다르다"; fi
    fi
  done <<'LIST'
llamaK_4096x32x8x14336x128256 llama큰 K 4096 32 8 14336 128256
llamaQ8_4096x32x8x14336x128256 llama큰 Q8_0 4096 32 8 14336 128256
llamaQ8_3072x24x8x8192x128256 llama큰 Q8_0 3072 24 8 8192 128256
llamaK_4096x32x8x14336x32768 llama큰 K 4096 32 8 14336 32768
llamaQ8_4096x32x8x14336x32768 llama큰 Q8_0 4096 32 8 14336 32768
llamaQ8_3072x24x8x8192x128256_공유32 llama큰 Q8_0 3072 24 8 8192 128256
llamaQ8_8192x64x8x28672x128256 llama큰 Q8_0 8192 64 8 28672 128256
llamaK_8192x64x8x28672x128256 llama큰 K 8192 64 8 28672 128256
LIST
  sha256sum "$B"/*.exe | sed "s#$W/#작업/#" >> "$L"
  # 입력 — 채팅 틀은 서버와 같은 글, 토큰은 llama.cpp 의 llama-tokenize
  python -I -X utf8 시험/입력7B.py "$F31Q4" "$W/입력L3.bin" --라마토큰 "$LT" >> "$L" 2>&1
  python -I -X utf8 시험/입력7B.py "$FMQ4" "$W/입력M.bin" --라마토큰 "$LT" >> "$L" 2>&1
  python -I -X utf8 시험/입력7B.py "$F31Q4" "$W/재기입력L3.bin" --재기 --라마토큰 "$LT" >> "$L" 2>&1
  기록 "빌드 끝 $(date '+%T')"
  ;;
로프)   # 39a (1) — 셋(θ 500000 · 3.1 의 인자, θ 500000 · 3.2 의 인자, θ 10⁶ · 인자 없음) × 위치 0 … 131,071
  python -I -X utf8 시험/로프39.py "$B/시험_로프.exe" "$OUT/39a_로프.json" "$F31Q4" "$F32Q8" "$FMQ4" --길이 131072 > "$W/39a_로프.log" 2>&1
  기록 "39a(1) 종료 $? — $(tail -1 "$W/39a_로프.log")"
  ;;
끝에서끝)   # 39c (1) 다섯 길 · 39a (3) Vulkan(로짓은 39a (2) 의 입력)
  for f in "${FIVE[@]}"; do
    rm -rf "$W/시험39_$f" "$W/시험39V_$f"; mkdir -p "$W/시험39_$f" "$W/시험39V_$f"
    "$B/시험_7B.exe" "$(파일 $f)" "$B/$(모듈 $f).ptx" "$(입력 $f)" "$W/시험39_$f" > "$W/39c_$f.log" 2>&1
    기록 "39c(1) $f 종료 $? — $(tail -1 "$W/39c_$f.log")"
    cp "$W/시험39_$f/요약.txt" "$OUT/39c_요약_$f.txt"; cp "$W/39c_$f.log" "$OUT/39c_기록_$f.txt"
    GEULPU_VULKAN=RTX "$B/시험_7BV.exe" "$(파일 $f)" "$B/$(모듈 $f).spvs" "$(입력 $f)" "$W/시험39V_$f" > "$W/39aV_$f.log" 2>&1
    기록 "39a(3) Vulkan $f 종료 $? — $(tail -1 "$W/39aV_$f.log") · CUDA 와 $(같은가 "$W/시험39_$f" "$W/시험39V_$f")"
    cp "$W/39aV_$f.log" "$OUT/39a_Vulkan_기록_$f.txt"
  done
  ;;
공유32)   # 39a (4) — 3B Q8_0 의 공유32 모듈(AMD 한도 흉내)
  rm -rf "$W/시험39A_32q8"; mkdir -p "$W/시험39A_32q8"
  GEULPU_VULKAN=RTX GEULPU_VULKAN_SHARED=32768 GEULPU_VULKAN_PUSH=128 GEULPU_VULKAN_ALLOC=2147483648 \
    "$B/시험_7BV.exe" "$F32Q8" "$B/llamaQ8_3072x24x8x8192x128256_공유32.spvs" "$W/입력L3.bin" "$W/시험39A_32q8" > "$W/39aA_32q8.log" 2>&1
  기록 "39a(4) 공유32 흉내 32q8 종료 $? — $(tail -1 "$W/39aA_32q8.log") · CUDA 와 $(같은가 "$W/시험39_32q8" "$W/시험39A_32q8")"
  cp "$W/39aA_32q8.log" "$OUT/39a_공유32_기록_32q8.txt"
  ;;
합성)   # 39a (5) — Llama-3.1-70B 모양(층 넷) Q8_0 · 그것을 llama-quantize 로 Q4_K_M
  [ -f "$MS/llama-synth-70b-l4-q8_0.gguf" ] || python -I -X utf8 준비/합성qwen2.py "$F31Q8" "$MS/llama-synth-70b-l4-q8_0.gguf" --모양 llama-70B --층 4 --형식 Q8_0 --씨앗 39 >> "$L" 2>&1
  [ -f "$MS/llama-synth-70b-l4-q4_k_m.gguf" ] || "$LL/llama-quantize.exe" --allow-requantize "$MS/llama-synth-70b-l4-q8_0.gguf" "$MS/llama-synth-70b-l4-q4_k_m.gguf" Q4_K_M > "$W/양자화.log" 2>&1
  sha256sum "$MS"/llama-synth-70b-l4-*.gguf | sed "s#$M/#모델/#" >> "$L"
  python -I -X utf8 시험/입력7B.py "$MS/llama-synth-70b-l4-q8_0.gguf" "$W/입력무작위L.bin" --무작위 39 --라마토큰 "$LT" >> "$L" 2>&1
  for s in q8_0 q4_k_m; do
    m=llamaQ8_8192x64x8x28672x128256; [ "$s" = q4_k_m ] && m=llamaK_8192x64x8x28672x128256
    rm -rf "$W/시험39_s70_$s"; mkdir -p "$W/시험39_s70_$s"
    "$B/시험_7B.exe" "$MS/llama-synth-70b-l4-$s.gguf" "$B/$m.ptx" "$W/입력무작위L.bin" "$W/시험39_s70_$s" > "$W/39a5_$s.log" 2>&1
    기록 "39a(5) 합성 70B $s 종료 $? — $(tail -1 "$W/39a5_$s.log")"
    cp "$W/시험39_s70_$s/요약.txt" "$OUT/39a_합성70B_요약_$s.txt"
  done
  ;;
그대로)   # 39c (2) — Qwen2.5-7B Q8_0 · Q4_0 · Q4_K_M 은 23b · 26b 기록과, Qwen3 셋은 39단계 직전 커밋(38단계 코드)의 빌드와 요약이 같은가
  python -I -X utf8 시험/입력7B.py 모델/qwen2.5-7b-instruct-gguf/qwen2.5-7b-instruct-q4_0-pure.gguf "$W/입력7B.bin" >> "$L" 2>&1
  python -I -X utf8 시험/입력7B.py 모델/qwen3-1.7b-gguf/Qwen3-1.7B-Q8_0.gguf "$W/입력Q3.bin" >> "$L" 2>&1
  [ -d "$W/옛판" ] || git worktree add --detach "$W/옛판" "$OLD" >> "$L" 2>&1
  for t in 시험_7B; do GEUL_ROOT="$GL" "$GC" "$W/옛판/호스트/$t.gl" -o "$B/옛_$t.exe" >> "$L" 2>&1; done
  GEUL_ROOT="$GL" "$GC" "$W/옛판/커널/커널생성.gl" -o "$B/옛_커널생성.exe" >> "$L" 2>&1
  while read -r m ARGS; do
    [ -z "$m" ] && continue
    # shellcheck disable=SC2086
    "$B/커널생성.exe" $ARGS "$B/$m.gl" > /dev/null 2>&1; "$PX" "$B/$m.gl" -o "$B/$m.ptx" > /dev/null 2>&1
    # shellcheck disable=SC2086
    "$B/옛_커널생성.exe" $ARGS "$B/옛_$m.gl" > /dev/null 2>&1
    cmp -s "$B/$m.gl" "$B/옛_$m.gl" && 기록 "그대로: 모듈 $m 소스가 옛 생성기와 같다" || 기록 "그대로: 모듈 $m 소스가 옛 생성기와 다르다"
  done <<'LIST'
qwen2Q8_7b qwen2Q8_7b
qwen2Q4_7b qwen2Q4_7b
qwen2K_3584x28x4x18944x152064 qwen2큰 K 3584 28 4 18944 152064
qwen3Q8_2048x16x8x6144x151936 qwen3큰 Q8_0 2048 16 8 6144 151936
qwen3Q8_4096x32x8x12288x151936 qwen3큰 Q8_0 4096 32 8 12288 151936
qwen3K_4096x32x8x12288x151936 qwen3큰 K 4096 32 8 12288 151936
LIST
  run_same() {   # 이름 GGUF 모듈 입력 견줄요약(없으면 옛 빌드로 만든다)
    rm -rf "$W/시험39_$1" "$W/옛39_$1"; mkdir -p "$W/시험39_$1" "$W/옛39_$1"
    "$B/시험_7B.exe" "$2" "$B/$3.ptx" "$4" "$W/시험39_$1" > "$W/39c2_$1.log" 2>&1
    local r=$? s=다름 ref="$5"
    if [ -z "$ref" ]; then
      "$B/옛_시험_7B.exe" "$2" "$B/$3.ptx" "$4" "$W/옛39_$1" > "$W/39c2옛_$1.log" 2>&1
      ref="$W/옛39_$1/요약.txt"
    fi
    cmp -s "$W/시험39_$1/요약.txt" "$ref" && s=같음
    기록 "39c(2) $1 종료 $r — $(tail -1 "$W/39c2_$1.log") · 견줄 요약($(basename "$(dirname "$ref")")/$(basename "$ref"))과 $s"
    cp "$W/시험39_$1/요약.txt" "$OUT/39c_그대로_요약_$1.txt"
  }
  run_same 7b-q8_0 모델/qwen2.5-7b-instruct-gguf/qwen2.5-7b-instruct-q8_0.gguf qwen2Q8_7b "$W/입력7B.bin" 문서/결과/23단계/23b_요약_Q8.txt
  run_same 7b-q4_0 모델/qwen2.5-7b-instruct-gguf/qwen2.5-7b-instruct-q4_0-pure.gguf qwen2Q4_7b "$W/입력7B.bin" 문서/결과/23단계/23b_요약_Q4.txt
  run_same 7b-q4_k_m 모델/qwen2.5-7b-instruct-gguf/qwen2.5-7b-instruct-q4_k_m-req.gguf qwen2K_3584x28x4x18944x152064 "$W/입력7B.bin" 문서/결과/26단계/26b_요약_q4_k_m.txt
  run_same q3-1.7b-q8_0 모델/qwen3-1.7b-gguf/Qwen3-1.7B-Q8_0.gguf qwen3Q8_2048x16x8x6144x151936 "$W/입력Q3.bin" ""
  run_same q3-8b-q8_0 모델/qwen3-8b-gguf/Qwen3-8B-Q8_0.gguf qwen3Q8_4096x32x8x12288x151936 "$W/입력Q3.bin" ""
  run_same q3-8b-q4_k_m 모델/qwen3-8b-gguf/Qwen3-8B-Q4_K_M.gguf qwen3K_4096x32x8x12288x151936 "$W/입력Q3.bin" ""
  ;;
독립)   # 39a (6) — llama.cpp(같은 GGUF · 기본 설정)의 모든 행 로짓과 KL · 1위
  for f in 31q8 mq8; do
    D="$W/독립39_$f"; rm -rf "$D"; mkdir -p "$D/글"
    python -I -X utf8 시험/독립39.py 입력 "$(파일 $f)" "$LL" "$D" >> "$L" 2>&1
    "$B/시험_7B.exe" "$(파일 $f)" "$B/$(모듈 $f).ptx" "$D/입력.bin" "$D/글" > "$D/글.log" 2>&1
    기록 "39a(6) $f 글 종료 $? — $(tail -1 "$D/글.log")"
    python -I -X utf8 시험/독립39.py 라마 "$(파일 $f)" "$LL" "$D" > "$D/라마.log" 2>&1
    기록 "39a(6) $f llama.cpp 종료 $? — $(grep -c '^라마' "$D/라마.log") 경우"
    python -I -X utf8 시험/독립39.py 견주기 "$D" "$D/글" "$OUT/39a_독립_$f.json" > "$D/견주기.log" 2>&1
    기록 "39a(6) $f — $(cat "$D/견주기.log" | tr '\n' ' ')"
    # 라마{i}.npy(각 1 GB 남짓)는 작업 폴더에 남긴다
  done
  ;;
토크나이저)   # 39b (1) — 글 묶음 2,000 줄 · 서버의 /tokenize · /detokenize 와 llama-tokenize
  for f in 31q4 32q8 mq4; do
    서버띄우기 "$(파일 $f)" "$B/$(모듈 $f).ptx" || continue
    python -I -X utf8 시험/토크나이저39.py 대조 시험/토크나이저39글.json http://127.0.0.1:18391 "$(파일 $f)" "$LL" "$OUT/39b_토크나이저_$f.json" --일꾼 8 > "$W/39b1_$f.log" 2>&1
    기록 "39b(1) $f — $(tail -1 "$W/39b1_$f.log")"
    서버끄기
  done
  ;;
틀)   # 39b (2) · (3) — 대화 열둘(jinja2 — WSL) · 끝 토큰
  for f in 31q4 32q8 mq4; do
    python -I -X utf8 시험/틀39.py 준비 "$(파일 $f)" "$W/틀준비_$f.json" >> "$L" 2>&1
    wp=$(echo "$W" | sed -E 's#^/([a-zA-Z])/#/mnt/\1/#; s#^([A-Za-z]):/#/mnt/\L\1/#')
    wr=$(echo "$R" | sed -E 's#^/([a-zA-Z])/#/mnt/\1/#; s#^([A-Za-z]):/#/mnt/\L\1/#')
    MSYS_NO_PATHCONV=1 wsl -d Ubuntu-24.04 -- python3 "$wr/시험/틀39.py" 그리기 "$wp/틀준비_$f.json" "$wp/틀그림_$f.json" >> "$L" 2>&1
    서버띄우기 "$(파일 $f)" "$B/$(모듈 $f).ptx" || continue
    python -I -X utf8 시험/틀39.py 대조 "$W/틀그림_$f.json" http://127.0.0.1:18391 "$(파일 $f)" "$LL" "$OUT/39b_틀_$f.json" > "$W/39b2_$f.log" 2>&1
    기록 "39b(2)(3) $f — $(tail -1 "$W/39b2_$f.log")"
    서버끄기
  done
  ;;
속도)   # 기록(판정 아님) — Llama-3.1-8B Q8_0 · Q4_K_M, 글(재기_7B) 과 llama.cpp(llama-bench) 를 번갈아 한 번
  for f in 31q8 31q4; do
    기록 "속도 글 $f 시작 $(date '+%T')"
    "$B/재기_7B.exe" "$(파일 $f)" "$B/$(모듈 $f).ptx" "$W/재기입력L3.bin" "$OUT/39속도_글_$f.txt" > "$W/39속도_글_$f.log" 2>&1
    기록 "속도 글 $f 끝 $(date '+%T') 종료 $?"
    ( cd "$M" && "$LB" -m "$(basename "$(파일 $f)")" -p 2048,8192 -n 0 -o md > "$OUT/39속도_라마_${f}_프롬프트.txt" 2> /dev/null
      "$LB" -m "$(basename "$(파일 $f)")" -p 0 -n 128 -d 0,2048,8192 -o md > "$OUT/39속도_라마_${f}_생성.txt" 2> /dev/null )
    기록 "속도 라마 $f 끝 $(date '+%T') 종료 $?"
  done
  ;;
참조)   # 39a (2) — 다섯 파일의 CPU 참조 전체 앞으로(파일마다 수십 분 — 끝에)
  for f in "${FIVE[@]}"; do
    기록 "39a(2) $f 시작 $(date '+%T')"
    python -I -X utf8 시험/참조7B.py "$(파일 $f)" "$W/시험39_$f" "$OUT/39a_끝에서끝_$f.json" > "$W/39a_끝에서끝_$f.log" 2>&1
    기록 "39a(2) $f 끝 $(date '+%T') 종료 $? — $(tail -1 "$W/39a_끝에서끝_$f.log")"
  done
  ;;
합성참조)   # 39a (5) — 합성 70B 모양 둘의 CPU 참조(단계 '합성' 뒤에)
  for s in q8_0 q4_k_m; do
    python -I -X utf8 시험/참조7B.py "$MS/llama-synth-70b-l4-$s.gguf" "$W/시험39_s70_$s" "$OUT/39a_합성70B_$s.json" > "$W/39a5_참조_$s.log" 2>&1
    기록 "39a(5) 합성 70B $s CPU 참조 종료 $? — $(tail -1 "$W/39a5_참조_$s.log")"
  done
  ;;
*) 기록 "모르는 단계 $STEP" ;;
esac
done
기록 "끝 $(date '+%F %T')"
