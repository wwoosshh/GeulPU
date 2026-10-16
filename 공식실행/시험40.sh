#!/bin/bash
# 40단계 측정(문서/40단계.md) — 손실이 증상을 만드는가. 고정한 코드(커밋)와 그 빌드로. 결과의 요약은 문서/결과/40단계/ 에,
# 생성 기록 · 로짓 같은 큰 파일은 작업 폴더에.
#   bash 공식실행/시험40.sh <저장소> <작업폴더> <ASCII 모델폴더> <llama.cpp 판 폴더> [단계 …]
#   단계(없으면 모두, 이 차례로): 빌드 토큰 G7 GR1 오염 V7 VR1 L7 LR1 따라7 따라R1 확인L 셈1 갈래 셈
#   (0.5B 의 G05 · L05 · 따라05 는 기본에서 뺐다 — GeulPU 서버는 머리 128 의 Qwen2 만 받는다. 결과의 '사전 등록과 다른 점')
# ASCII 모델폴더: llama.cpp 가 한글 경로를 열지 못해 GGUF 를 ASCII 이름으로 둔다(같은 디스크면 하드 링크) —
#   qwen7b.gguf(Qwen2.5-7B-Instruct Q8_0) · r1.gguf(DeepSeek-R1-Distill-Qwen-7B Q8_0) · qwen05b.gguf(Qwen2.5-0.5B-Instruct Q8_0).
# GPU 일은 하나씩 차례로 한다. 서버는 포트 18401(GeulPU) · 18402(llama.cpp 생성) · 18403(llama.cpp 토큰 — CPU)에 띄웠다 끈다.
set -u
R="$1"; W="$2"; M="$3"; LL="$4"; shift 4
STEPS=("$@")
[ ${#STEPS[@]} -eq 0 ] && STEPS=(빌드 토큰 G7 GR1 오염 V7 VR1 L7 LR1 따라7 따라R1 확인L 셈1 갈래 셈)
OUT="$R/문서/결과/40단계"
GL="$R/../geul-lang-v2"
GC="$GL/build/self_컴파일러.exe"
PX="$GL/build/자체PTX.exe"
B="$W/build"
PY="python -I -X utf8"
cd "$R" || exit 1
mkdir -p "$OUT" "$B" "$W"
L="$OUT/40_기록.txt"
기록() { echo "$*" >> "$L"; }
[ -f "$L" ] || 기록 "시작 $(date '+%F %T') · 커밋 $(git rev-parse --short HEAD) · 바뀐 파일 $(git status --short | grep -v '^??' | wc -l) · 글 저장소 $(git -C "$GL" rev-parse --short HEAD) (바뀐 파일 $(git -C "$GL" status --short | grep -v '^??' | wc -l))"
기록 "== 단계 ${STEPS[*]} — $(date '+%F %T') · 커밋 $(git rev-parse --short HEAD) · 바뀐 파일 $(git status --short | grep -v '^??' | wc -l)"

모음() { $PY 재기/모음40.py "$@" --작업 "$W" --모델폴더 "$M" --llama "$LL" --빌드 "$B" >> "$W/모음.log" 2>&1; local r=$?; 기록 "모음 $* — 종료 $r $(date '+%T')"; return $r; }
따라() { $PY 재기/따라40.py "$@" --작업 "$W" --모델폴더 "$M" --llama "$LL" >> "$W/따라.log" 2>&1; local r=$?; 기록 "따라 $* — 종료 $r $(date '+%T')"; return $r; }

for STEP in "${STEPS[@]}"; do
case "$STEP" in
빌드)
  기록 "빌드 시작 $(date '+%T')"
  nvidia-smi --query-gpu=name,driver_version,clocks.max.sm,clocks.max.mem,memory.total --format=csv >> "$L"
  "$LL/llama-server.exe" --version >> "$L" 2>&1
  sha256sum "$GC" "$PX" "$LL/llama-server.exe" "$LL/llama.dll" "$LL/ggml-cuda.dll" "$M/qwen7b.gguf" "$M/r1.gguf" "$M/qwen05b.gguf" \
    | sed "s#$GL/#../geul-lang-v2/#; s#$R/#./#; s#$LL/#llama.cpp/#; s#$M/#모델/#" >> "$L"
  GEUL_ROOT="$GL" "$GC" 커널/커널생성.gl -o "$B/커널생성.exe" >> "$L" 2>&1 || 기록 "빌드 실패 커널생성"
  GEUL_ROOT="$GL" "$GC" 호스트/서버.gl -o "$B/서버.exe" >> "$L" 2>&1 || 기록 "빌드 실패 서버"
  sha256sum "$B/커널생성.exe" "$B/서버.exe" | sed "s#$B/#빌드/#" >> "$L"
  while read -r m ARGS; do
    [ -z "$m" ] && continue
    FLAG=""; case "$m" in *_자리하나) FLAG="--자리하나" ;; esac
    # shellcheck disable=SC2086
    "$B/커널생성.exe" $ARGS "$B/$m.gl" $FLAG > "$W/gen_$m.log" 2>&1
    "$PX" "$B/$m.gl" -o "$B/$m.ptx" > "$W/ptx_$m.log" 2>&1; 기록 "PTX $m 종료 $?"
    ROW=$(grep "^$m |" 시험/모듈해시.txt)
    h="$(sha256sum "$B/$m.gl" | cut -c1-64) | $(sha256sum "$B/$m.ptx" | cut -c1-64)"
    if echo "$ROW" | grep -q "$h"; then 기록 "모듈 $m — 소스 · PTX 가 모듈해시와 같다"; else 기록 "모듈 $m — 모듈해시와 다르다 ($h)"; fi
  done <<'EOF'
qwen2Q8 qwen2Q8
qwen2Q8_7b qwen2Q8_7b
qwen2Q8_7b_자리하나 qwen2Q8_7b
EOF
  기록 "빌드 끝 $(date '+%T')"
  ;;
토큰) 모음 토큰 --모델 7b; 모음 토큰 --모델 r1; 모음 토큰 --모델 05b ;;
G7)  모음 생성 --갈래 G --모델 7b ;;
GR1) 모음 생성 --갈래 G --모델 r1 ;;
G05) 모음 생성 --갈래 G --모델 05b ;;
오염) 모음 오염 --모델 7b ;;
V7)  모음 생성 --갈래 V --모델 7b; 모음 점수 --갈래 V --모델 7b ;;
VR1) 모음 생성 --갈래 V --모델 r1; 모음 점수 --갈래 V --모델 r1 ;;
L7)  모음 생성 --갈래 L --모델 7b ;;
LR1) 모음 생성 --갈래 L --모델 r1 ;;
L05) 모음 생성 --갈래 L --모델 05b ;;
따라7)  따라 --모델 7b ;;
따라R1) 따라 --모델 r1 ;;
따라05) 따라 --모델 05b ;;
확인L) 모음 확인L --모델 7b; 따라 --모델 7b --확인 ;;
셈1)  $PY 재기/셈40.py 위험 --작업 "$W" --모델폴더 "$M" >> "$W/셈.log" 2>&1; 기록 "셈1 — 종료 $? $(date '+%T')" ;;
갈래) 모음 갈래 --모델 7b ;;
셈)   $PY 재기/셈40.py 모두 --작업 "$W" --모델폴더 "$M" --결과 "$OUT" >> "$W/셈.log" 2>&1; 기록 "셈 — 종료 $? $(date '+%T')" ;;
*) 기록 "모르는 단계 $STEP" ;;
esac
done
기록 "== 끝 $(date '+%F %T')"
