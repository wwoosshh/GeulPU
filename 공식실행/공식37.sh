#!/bin/bash
# 37단계 공식 실행 — 고정한 코드(커밋)와 그 빌드로. 결과는 문서/결과/37단계/ 에(로짓 등 큰 파일은 작업 폴더에).
#   bash 공식실행/공식37.sh <저장소> <작업폴더>
# 차례: 빌드(생성기 · 시험 · 재기 도구 · 모듈 — 빠른 점검의 해시와 대조) → 37a(1) 머리 정규화 판(CUDA · Vulkan) → 37b(1) 다섯 길(세 파일, CUDA)
# → 37a(3) Vulkan(세 파일) · 37a(4) 공유32 흉내(1.7B) → 37b(2) 옛 모델 그대로(7B Q8_0 · Q4_0 · Q4_K_M 의 요약) → 37a(5) 14B 모양 합성 둘
# → 37c · 37d 속도(글과 llama.cpp 최신 공식 판을 세 번 번갈아) → 기록(커널마다 · 실행기 채팅) → 모음
# → 37a(2) · 37a(5) CPU 참조(끝에 — CPU 를 많이 써서 시간 재기와 겹치지 않게).
# 37b(3) 교차검증(R1 32 문제)은 교차검증/run.ps1 · runV.ps1 로 따로 돌린다(결과 묶음을 이 폴더에 둔다).
set -u
R="$1"
W="$2"
OUT="$R/문서/결과/37단계"
M3="$R/모델/qwen3-8b-gguf"
M17="$R/모델/qwen3-1.7b-gguf"
MS="$R/모델/합성"
M7="$R/모델/qwen2.5-7b-instruct-gguf"
GL="$R/../geul-lang-v2"
GC="$GL/build/self_컴파일러.exe"
PX="$GL/build/자체PTX.exe"
SV="$GL/build/자체SPIRV.exe"
LL="$R/도구/llama-b11635"
LB="$LL/llama-bench.exe"
B=빌드/글37
cd "$R"
mkdir -p "$OUT" "$B" "$W"
L="$OUT/37_기록.txt"
echo "시작 $(date '+%F %T') · 커밋 $(git rev-parse --short HEAD) · 바뀐 파일 $(git status --short | grep -v '^??' | wc -l) · 글 저장소 $(git -C "$GL" rev-parse --short HEAD) (바뀐 파일 $(git -C "$GL" status --short | grep -v '^??' | wc -l))" > "$L"
nvidia-smi --query-gpu=name,driver_version,clocks.max.sm,clocks.max.mem,memory.total --format=csv >> "$L"
"$LB" --version >> "$L" 2>&1
sha256sum "$GC" "$PX" "$SV" "$LB" "$LL/ggml-cuda.dll" | sed "s#$GL/#../geul-lang-v2/#; s#$R/#./#" >> "$L"

# ---- 빌드 ----
echo "빌드 시작 $(date '+%T')" >> "$L"
GEUL_ROOT="$GL" "$GC" 커널/커널생성.gl -o "$B/커널생성.exe" >> "$L" 2>&1
for t in 실행기 시험_7B 시험_7BV 재기_7B 재기_7B커널; do
  GEUL_ROOT="$GL" "$GC" "호스트/$t.gl" -o "$B/$t.exe" >> "$L" 2>&1
done
modgen() {   # 모듈 이름 → 생성기 인자
  case "$1" in
    qwen3Q8_2048x16x8x6144x151936) echo "qwen3큰 Q8_0 2048 16 8 6144 151936" ;;
    qwen3Q8_2048x16x8x6144x151936_공유32) echo "qwen3큰 Q8_0 2048 16 8 6144 151936" ;;
    qwen3Q8_4096x32x8x12288x151936) echo "qwen3큰 Q8_0 4096 32 8 12288 151936" ;;
    qwen3K_4096x32x8x12288x151936) echo "qwen3큰 K 4096 32 8 12288 151936" ;;
    qwen3Q8_5120x40x8x17408x151936) echo "qwen3큰 Q8_0 5120 40 8 17408 151936" ;;
    qwen3K_5120x40x8x17408x151936) echo "qwen3큰 K 5120 40 8 17408 151936" ;;
    qwen2Q8_7b) echo "qwen2Q8_7b" ;;
    qwen2Q4_7b) echo "qwen2Q4_7b" ;;
    qwen2K_3584x28x4x18944x152064) echo "qwen2큰 K 3584 28 4 18944 152064" ;;
  esac
}
MODS=(qwen3Q8_2048x16x8x6144x151936 qwen3Q8_4096x32x8x12288x151936 qwen3K_4096x32x8x12288x151936 qwen3Q8_2048x16x8x6144x151936_공유32
      qwen3Q8_5120x40x8x17408x151936 qwen3K_5120x40x8x17408x151936 qwen2Q8_7b qwen2Q4_7b qwen2K_3584x28x4x18944x152064)
for m in "${MODS[@]}"; do
  깃발=""
  case "$m" in *_공유32) 깃발="--공유32" ;; esac
  # shellcheck disable=SC2046
  "$B/커널생성.exe" $(modgen "$m") "$B/$m.gl" $깃발 >> "$L" 2>&1
  "$PX" "$B/$m.gl" -o "$B/$m.ptx" > "$W/ptx_$m.log" 2>&1
  echo "PTX $m 종료 $?" >> "$L"
  case "$m" in qwen3*_2048*|qwen3*_4096*)
    "$SV" "$B/$m.gl" -o "$B/$m.spvs" > "$W/spv_$m.log" 2>&1
    echo "SPIR-V $m 종료 $?" >> "$L" ;;
  esac
  줄=$(grep "^$m |" 시험/모듈해시.txt)
  if [ -n "$줄" ]; then
    gl=$(sha256sum "$B/$m.gl" | cut -c1-64)
    px=$(sha256sum "$B/$m.ptx" | cut -c1-64)
    if echo "$줄" | grep -q "$gl | $px"; then echo "모듈 $m — 소스 · PTX 가 빠른 점검의 해시와 같다" >> "$L"; else echo "모듈 $m — 빠른 점검의 해시와 다르다" >> "$L"; fi
  fi
done
sha256sum "$B"/*.exe | sed "s#$R/#./#" >> "$L"
echo "빌드 끝 $(date '+%T')" >> "$L"

# ---- 입력 ----
python -I -X utf8 시험/입력7B.py "$M17/Qwen3-1.7B-Q8_0.gguf" "$W/입력Q3.bin" >> "$L" 2>&1
python -I -X utf8 시험/입력7B.py "$M17/Qwen3-1.7B-Q8_0.gguf" "$W/재기입력Q3.bin" --재기 >> "$L" 2>&1
python -I -X utf8 시험/입력7B.py "$M17/Qwen3-1.7B-Q8_0.gguf" "$W/입력무작위.bin" --무작위 24 >> "$L" 2>&1
python -I -X utf8 시험/입력7B.py "$M7/qwen2.5-7b-instruct-q4_0-pure.gguf" "$W/입력7B.bin" >> "$L" 2>&1

# ---- 37a (1) 머리 정규화 판 — 8B 의 층마다 무게 · 행 1 · 4 · 64 · 2048 ----
python -I -X utf8 시험/머리정규화37.py "$B/qwen3Q8_4096x32x8x12288x151936.ptx" "$M3/Qwen3-8B-Q4_K_M.gguf" "$OUT/37a_정규화_CUDA.json" > "$W/37a_정규화_CUDA.log" 2>&1
echo "37a(1) CUDA 종료 $? — $(tail -1 "$W/37a_정규화_CUDA.log")" >> "$L"
GEULPU_VULKAN=RTX python -I -X utf8 시험/머리정규화37.py "$B/qwen3Q8_4096x32x8x12288x151936.spvs" "$M3/Qwen3-8B-Q4_K_M.gguf" "$OUT/37a_정규화_Vulkan.json" > "$W/37a_정규화_Vulkan.log" 2>&1
echo "37a(1) Vulkan 종료 $? — $(tail -1 "$W/37a_정규화_Vulkan.log")" >> "$L"

# ---- 37b (1) 다섯 길(CUDA — 로짓은 37a (2) 의 입력) · 37a (3) Vulkan · 37a (4) 공유32 흉내 ----
gguf3() { case "$1" in 17q8) echo "$M17/Qwen3-1.7B-Q8_0.gguf" ;; 8q8) echo "$M3/Qwen3-8B-Q8_0.gguf" ;; 8k) echo "$M3/Qwen3-8B-Q4_K_M.gguf" ;; esac; }
mod3() { case "$1" in 17q8) echo qwen3Q8_2048x16x8x6144x151936 ;; 8q8) echo qwen3Q8_4096x32x8x12288x151936 ;; 8k) echo qwen3K_4096x32x8x12288x151936 ;; esac; }
같은가() {   # 폴더 둘 — 경우 0 … 2 의 로짓 · 토큰 파일과 요약
  local a="$1" b="$2" i
  for i in 0 1 2; do
    cmp -s "$a/경우${i}_로짓.bin" "$b/경우${i}_로짓.bin" || { echo 다름; return; }
    cmp -s "$a/경우${i}_토큰.bin" "$b/경우${i}_토큰.bin" || { echo 다름; return; }
  done
  cmp -s "$a/요약.txt" "$b/요약.txt" && echo "같음(로짓 · 토큰 · 요약)" || echo "로짓 · 토큰 같음, 요약 다름"
}
for f in 17q8 8q8 8k; do
  rm -rf "$W/공식37_$f" "$W/공식37V_$f"
  mkdir -p "$W/공식37_$f" "$W/공식37V_$f"
  "$B/시험_7B.exe" "$(gguf3 $f)" "$B/$(mod3 $f).ptx" "$W/입력Q3.bin" "$W/공식37_$f" > "$W/37b_$f.log" 2>&1
  echo "37b(1) $f 종료 $? — $(tail -1 "$W/37b_$f.log")" >> "$L"
  cp "$W/공식37_$f/요약.txt" "$OUT/37b_요약_$f.txt"
  cp "$W/37b_$f.log" "$OUT/37b_기록_$f.txt"
  GEULPU_VULKAN=RTX "$B/시험_7BV.exe" "$(gguf3 $f)" "$B/$(mod3 $f).spvs" "$W/입력Q3.bin" "$W/공식37V_$f" > "$W/37aV_$f.log" 2>&1
  echo "37a(3) Vulkan $f 종료 $? — $(tail -1 "$W/37aV_$f.log") · CUDA 와 $(같은가 "$W/공식37_$f" "$W/공식37V_$f")" >> "$L"
  cp "$W/37aV_$f.log" "$OUT/37a_Vulkan_기록_$f.txt"
done
rm -rf "$W/공식37A_17q8"
mkdir -p "$W/공식37A_17q8"
GEULPU_VULKAN=RTX GEULPU_VULKAN_SHARED=32768 GEULPU_VULKAN_PUSH=128 GEULPU_VULKAN_ALLOC=2147483648 \
  "$B/시험_7BV.exe" "$M17/Qwen3-1.7B-Q8_0.gguf" "$B/qwen3Q8_2048x16x8x6144x151936_공유32.spvs" "$W/입력Q3.bin" "$W/공식37A_17q8" > "$W/37aA_17q8.log" 2>&1
echo "37a(4) 공유32 흉내 17q8 종료 $? — $(tail -1 "$W/37aA_17q8.log") · CUDA 와 $(같은가 "$W/공식37_17q8" "$W/공식37A_17q8")" >> "$L"
cp "$W/37aA_17q8.log" "$OUT/37a_공유32_기록_17q8.txt"

# ---- 37b (2) 옛 모델 그대로 — 7B 의 요약이 23b · 26b 기록과 바이트까지 ----
run_same() {   # 이름 GGUF PTX 견줄요약
  rm -rf "$W/공식37_$1"
  mkdir -p "$W/공식37_$1"
  "$B/시험_7B.exe" "$2" "$3" "$W/입력7B.bin" "$W/공식37_$1" > "$W/37b_$1.log" 2>&1
  local r=$? s=다름
  cmp -s "$W/공식37_$1/요약.txt" "$4" && s=같음
  echo "37b(2) $1 종료 $r — $(tail -1 "$W/37b_$1.log") · 견줄 요약과 $s" >> "$L"
}
run_same 7b-q8_0 "$M7/qwen2.5-7b-instruct-q8_0.gguf" "$B/qwen2Q8_7b.ptx" 문서/결과/23단계/23b_요약_Q8.txt
run_same 7b-q4_0 "$M7/qwen2.5-7b-instruct-q4_0-pure.gguf" "$B/qwen2Q4_7b.ptx" 문서/결과/23단계/23b_요약_Q4.txt
run_same 7b-q4_k_m "$M7/qwen2.5-7b-instruct-q4_k_m-req.gguf" "$B/qwen2K_3584x28x4x18944x152064.ptx" 문서/결과/26단계/26b_요약_q4_k_m.txt

# ---- 37a (5) 14B 모양 합성 둘(층 넷) — 엔진 쪽(CPU 참조는 끝에) ----
for s in q8_0 q4_k_m; do
  m=qwen3Q8_5120x40x8x17408x151936
  [ "$s" = q4_k_m ] && m=qwen3K_5120x40x8x17408x151936
  rm -rf "$W/공식37_s14_$s"
  mkdir -p "$W/공식37_s14_$s"
  "$B/시험_7B.exe" "$MS/qwen3-synth-14b-l4-$s.gguf" "$B/$m.ptx" "$W/입력무작위.bin" "$W/공식37_s14_$s" > "$W/37a5_$s.log" 2>&1
  echo "37a(5) 합성 14B $s 종료 $? — $(tail -1 "$W/37a5_$s.log")" >> "$L"
  cp "$W/공식37_s14_$s/요약.txt" "$OUT/37a_합성14B_요약_$s.txt"
done

# ---- 37c · 37d 속도 — 글과 llama.cpp 를 세 번 번갈아 ----
for i in 1 2 3; do
  for f in q8_0 q4_k_m; do
    G="$M3/Qwen3-8B-Q8_0.gguf"; P="$B/qwen3Q8_4096x32x8x12288x151936.ptx"; N=Qwen3-8B-Q8_0.gguf
    [ "$f" = q4_k_m ] && { G="$M3/Qwen3-8B-Q4_K_M.gguf"; P="$B/qwen3K_4096x32x8x12288x151936.ptx"; N=Qwen3-8B-Q4_K_M.gguf; }
    echo "37c 글 $f $i 시작 $(date '+%T')" >> "$L"
    "$B/재기_7B.exe" "$G" "$P" "$W/재기입력Q3.bin" "$OUT/37c_글_${f}_$i.txt" > "$W/37c_글_${f}_$i.log" 2>&1
    echo "37c 글 $f $i 끝 $(date '+%T') 종료 $?" >> "$L"
    ( cd "$M3" && "$LB" -m "$N" -p 2048,8192 -n 0 -o md > "$OUT/37c_라마_${f}_프롬프트_$i.txt" 2>/dev/null
      "$LB" -m "$N" -p 0 -n 128 -d 0,2048,8192 -o md > "$OUT/37c_라마_${f}_생성_$i.txt" 2>/dev/null )
    echo "37c 라마 $f $i 끝 $(date '+%T') 종료 $?" >> "$L"
  done
done

# ---- 기록: 커널마다의 시간(이벤트 사이에 띄움 하나씩 — 37c 의 시간이 아니다 · q·k 정규화를 따로) ----
for f in q8_0 q4_k_m; do
  G="$M3/Qwen3-8B-Q8_0.gguf"; P="$B/qwen3Q8_4096x32x8x12288x151936.ptx"
  [ "$f" = q4_k_m ] && { G="$M3/Qwen3-8B-Q4_K_M.gguf"; P="$B/qwen3K_4096x32x8x12288x151936.ptx"; }
  "$B/재기_7B커널.exe" "$G" "$P" "$W/재기입력Q3.bin" "$OUT/37기록_글_커널마다_$f.txt" > "$W/37기록_커널_$f.log" 2>&1
  echo "기록 커널마다 $f 종료 $?" >> "$L"
done
python -I -X utf8 재기/모음37.py "$OUT" "$OUT/37cd_요약.json" "$M3" >> "$L" 2>&1

# ---- 기록: 실행기 채팅(8B Q4_K_M — 생각 켬이 기본) ----
printf '대한민국의 수도는 어디야? 한 문장으로.\nWhat is 17 times 23? Answer briefly.\n/끝\n' > "$W/채팅입력37.txt"
"$B/실행기.exe" "$M3/Qwen3-8B-Q4_K_M.gguf" --ptx "$B/qwen3K_4096x32x8x12288x151936.ptx" --생성 256 < "$W/채팅입력37.txt" > "$OUT/37_채팅_8b-q4_k_m.txt" 2>&1
echo "기록 채팅 종료 $?" >> "$L"

# ---- 37a (2) · (5) 끝에서 끝 — CPU 참조의 전체 앞으로(파일마다 수십 분) ----
for f in 17q8 8q8 8k; do
  echo "37a(2) $f 시작 $(date '+%T')" >> "$L"
  python -I -X utf8 시험/참조7B.py "$(gguf3 $f)" "$W/공식37_$f" "$OUT/37a_끝에서끝_$f.json" > "$W/37a_끝에서끝_$f.log" 2>&1
  echo "37a(2) $f 끝 $(date '+%T') 종료 $? — $(tail -1 "$W/37a_끝에서끝_$f.log")" >> "$L"
done
for s in q8_0 q4_k_m; do
  python -I -X utf8 시험/참조7B.py "$MS/qwen3-synth-14b-l4-$s.gguf" "$W/공식37_s14_$s" "$OUT/37a_합성14B_$s.json" > "$W/37a5_참조_$s.log" 2>&1
  echo "37a(5) 합성 14B $s CPU 참조 종료 $? — $(tail -1 "$W/37a5_참조_$s.log")" >> "$L"
done
echo "끝 $(date '+%F %T')" >> "$L"
