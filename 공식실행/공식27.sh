#!/bin/bash
# 27단계 공식 실행 — 고정한 코드(커밋)와 그 빌드로. 결과는 문서/결과/27단계/ 에(로짓 등 큰 파일은 작업 폴더에).
#   bash 공식실행/공식27.sh <저장소> <작업폴더>
# 차례: 글 PTX 뒷단(../geul-lang-v2) 빌드 → 27단계 빌드 → 26단계 빌드(9e91abc — 작업 폴더의 git worktree) → 27a(1) 판 → 27b 그대로
# → 27c · 27d 26 대 27 을 세 번 번갈아 → 기록(llama.cpp 프롬프트 · 커널마다 · 14B) → 모음 → 27a(2) CPU 참조(끝에 — CPU 를 많이 써서).
set -u
R="$1"
W="$2"
OUT="$R/문서/결과/27단계"
M7="$R/모델/qwen2.5-7b-instruct-gguf"
M14="$R/모델/qwen2.5-14b-instruct-gguf"
G05="$R/모델/qwen2.5-0.5b-instruct-gguf/qwen2.5-0.5b-instruct-q8_0.gguf"
GL="$R/../geul-lang-v2"
GC="$GL/build/self_컴파일러.exe"
PX="$GL/build/자체PTX.exe"
LB="$R/도구/llama-b11496/llama-bench.exe"
B26="$W/빌드26"
FILES=(q8_0 q4_0 q4_k_m q5_k_m q6_k)
cd "$R"
mkdir -p "$OUT" 빌드/글 "$W" "$B26"
L="$OUT/27_기록.txt"
echo "시작 $(date '+%F %T') · 커밋 $(git rev-parse --short HEAD) · 바뀐 파일 $(git status --short | grep -v '^??' | wc -l) · 글 저장소 $(git -C "$GL" rev-parse --short HEAD) (바뀐 파일 $(git -C "$GL" status --short | grep -v '^??' | wc -l))" > "$L"
nvidia-smi --query-gpu=name,driver_version,clocks.max.sm,clocks.max.mem,memory.total --format=csv >> "$L"

gguf() {   # 형식 → 7B GGUF
  case "$1" in
    q8_0) echo "$M7/qwen2.5-7b-instruct-q8_0.gguf" ;;
    q4_0) echo "$M7/qwen2.5-7b-instruct-q4_0-pure.gguf" ;;
    *) echo "$M7/qwen2.5-7b-instruct-$1-req.gguf" ;;
  esac
}
ptx() {    # 빌드 폴더 · 형식 → 7B 모듈
  case "$2" in
    q8_0) echo "$1/qwen2Q8_7b.ptx" ;;
    q4_0) echo "$1/qwen2Q4_7b.ptx" ;;
    *) echo "$1/qwen2K_3584x28x4x18944x152064.ptx" ;;
  esac
}

# ---- 글 PTX 뒷단(내장 정수텐서곱16) ----
echo "빌드 시작 $(date '+%T')" >> "$L"
( cd "$GL" && GEUL_ROOT=. "$GC" research/gpu/자체PTX/PTX.gl -o build/자체PTX.exe ) >> "$L" 2>&1
echo "PTX 뒷단 빌드 종료 $?" >> "$L"

# ---- 27단계 빌드 ----
GEUL_ROOT="$GL" "$GC" 커널/커널생성.gl -o 빌드/글/커널생성.exe >> "$L" 2>&1
for t in 실행기 시험_7B 시험_엔진 재기_7B 재기_7B커널; do
  GEUL_ROOT="$GL" "$GC" "호스트/$t.gl" -o "빌드/글/$t.exe" >> "$L" 2>&1
done
빌드/글/커널생성.exe qwen2Q8 빌드/글/qwen2Q8.gl >> "$L" 2>&1
빌드/글/커널생성.exe qwen2Q8_7b 빌드/글/qwen2Q8_7b.gl >> "$L" 2>&1
빌드/글/커널생성.exe qwen2Q4_7b 빌드/글/qwen2Q4_7b.gl >> "$L" 2>&1
빌드/글/커널생성.exe qwen2큰 Q4_0 5120 40 8 13824 152064 빌드/글/qwen2Q4_5120x40x8x13824x152064.gl >> "$L" 2>&1
빌드/글/커널생성.exe qwen2큰 K 3584 28 4 18944 152064 빌드/글/qwen2K_3584x28x4x18944x152064.gl >> "$L" 2>&1
빌드/글/커널생성.exe qwen2큰 K 5120 40 8 13824 152064 빌드/글/qwen2K_5120x40x8x13824x152064.gl >> "$L" 2>&1
for m in qwen2Q8 qwen2Q8_7b qwen2Q4_7b qwen2Q4_5120x40x8x13824x152064 qwen2K_3584x28x4x18944x152064 qwen2K_5120x40x8x13824x152064; do
  "$PX" "빌드/글/$m.gl" -o "빌드/글/$m.ptx" > "$W/ptx_$m.log" 2>&1
  echo "PTX $m 종료 $?" >> "$L"
done
for m in qwen2Q8 qwen2Q8_7b; do       # 27b — 바꾸지 않은 모듈은 24단계와 바이트까지
  for e in gl ptx; do
    h=$(sha256sum "빌드/글/$m.$e" | cut -c1-64)
    if grep -q "^$h \*빌드/글/$m.$e" 문서/결과/24단계/24_기록.txt; then echo "모듈 $m.$e — 24단계와 바이트까지 같다" >> "$L"; else echo "모듈 $m.$e — 24단계와 다르다" >> "$L"; fi
  done
done
sha256sum 빌드/글/qwen2Q4_*.gl 빌드/글/qwen2Q4_*.ptx 빌드/글/qwen2K_*.gl 빌드/글/qwen2K_*.ptx 빌드/글/커널생성.exe 빌드/글/실행기.exe 빌드/글/시험_7B.exe 빌드/글/재기_7B.exe 빌드/글/재기_7B커널.exe "$PX" >> "$L"

# ---- 26단계 빌드(9e91abc) — 같은 PTX 뒷단으로(바꾸지 않은 소스는 같은 PTX 를 낸다 — 26단계 기록의 해시와 견준다) ----
rm -rf "$W/wt26"
git worktree prune
git worktree add --detach "$W/wt26" 9e91abc >> "$L" 2>&1
( cd "$W/wt26" && GEUL_ROOT="$GL" "$GC" 커널/커널생성.gl -o "$B26/커널생성.exe" && GEUL_ROOT="$GL" "$GC" 호스트/재기_7B.gl -o "$B26/재기_7B.exe" ) >> "$L" 2>&1
"$B26/커널생성.exe" qwen2Q8_7b "$B26/qwen2Q8_7b.gl" >> "$L" 2>&1
"$B26/커널생성.exe" qwen2Q4_7b "$B26/qwen2Q4_7b.gl" >> "$L" 2>&1
"$B26/커널생성.exe" qwen2큰 K 3584 28 4 18944 152064 "$B26/qwen2K_3584x28x4x18944x152064.gl" >> "$L" 2>&1
"$B26/커널생성.exe" qwen2큰 Q4_0 5120 40 8 13824 152064 "$B26/qwen2Q4_5120x40x8x13824x152064.gl" >> "$L" 2>&1
"$B26/커널생성.exe" qwen2큰 K 5120 40 8 13824 152064 "$B26/qwen2K_5120x40x8x13824x152064.gl" >> "$L" 2>&1
for m in qwen2Q8_7b qwen2Q4_7b qwen2K_3584x28x4x18944x152064 qwen2Q4_5120x40x8x13824x152064 qwen2K_5120x40x8x13824x152064; do
  "$PX" "$B26/$m.gl" -o "$B26/$m.ptx" > "$W/ptx26_$m.log" 2>&1
  h=$(sha256sum "$B26/$m.ptx" | cut -c1-64)
  if grep -q "^$h " 문서/결과/26단계/26_기록.txt 문서/결과/24단계/24_기록.txt; then s=같다; else s=다르다; fi
  echo "26 빌드 PTX $m — 앞 단계 기록의 해시와 $s" >> "$L"
done
echo "빌드 끝 $(date '+%T')" >> "$L"

# ---- 입력 ----
python -I -X utf8 시험/입력7B.py "$M7/qwen2.5-7b-instruct-q8_0.gguf" "$W/공식입력7B.bin" >> "$L" 2>&1
python -I -X utf8 시험/입력7B.py "$M7/qwen2.5-7b-instruct-q8_0.gguf" "$W/공식재기입력7B.bin" --재기 >> "$L" 2>&1
python -I -X utf8 공식실행/입력18d.py "$R" "$W/18d입력.bin" >> "$L" 2>&1

# ---- 27a (1) 판 ----
echo "27a(1) 시작 $(date '+%T')" >> "$L"
python -I -X utf8 시험/판23.py 빌드/글/qwen2Q4_7b.ptx "$(gguf q4_0)" "$OUT/27a_판_Q4_0.json" > "$W/27a_판_Q4_0.log" 2>&1
echo "27a(1) Q4_0 종료 $? — $(tail -1 "$W/27a_판_Q4_0.log")" >> "$L"
python -I -X utf8 시험/판26.py "$(ptx 빌드/글 q4_k_m)" "$(gguf q4_k_m)" "$(gguf q5_k_m)" "$(gguf q6_k)" "$OUT/27a_판_K.json" > "$W/27a_판_K.log" 2>&1
echo "27a(1) K 종료 $? — $(tail -1 "$W/27a_판_K.log")" >> "$L"

# ---- 27b 그대로 — 다섯 길 요약이 앞 단계와 바이트까지 ----
run_same() {   # 이름 GGUF PTX 견줄요약
  local n="$1" G="$2" P="$3" REF="$4"
  rm -rf "$W/공식27_$n"
  mkdir -p "$W/공식27_$n"
  빌드/글/시험_7B.exe "$G" "$P" "$W/공식입력7B.bin" "$W/공식27_$n" > "$W/27b_$n.log" 2>&1
  local r=$?
  local s=다름
  cmp -s "$W/공식27_$n/요약.txt" "$REF" && s=같음
  echo "27b $n 종료 $r — $(tail -1 "$W/27b_$n.log") · 견줄 요약과 $s" >> "$L"
  cp "$W/27b_$n.log" "$OUT/27b_기록_$n.txt"
}
run_same q8_0 "$(gguf q8_0)" "$(ptx 빌드/글 q8_0)" 문서/결과/23단계/23b_요약_Q8.txt
run_same q4_0 "$(gguf q4_0)" "$(ptx 빌드/글 q4_0)" 문서/결과/23단계/23b_요약_Q4.txt
run_same 14b-q4_0 "$M14/qwen2.5-14b-instruct-q4_0-pure.gguf" 빌드/글/qwen2Q4_5120x40x8x13824x152064.ptx 문서/결과/24단계/24c_요약_14b-q4_0.txt
for f in q4_k_m q5_k_m q6_k; do
  run_same "$f" "$(gguf $f)" "$(ptx 빌드/글 $f)" "문서/결과/26단계/26b_요약_$f.txt"
done
빌드/글/시험_엔진.exe "$G05" 빌드/글/qwen2Q8.ptx "$W/18d입력.bin" "$OUT/27_0.5B_18d출력.txt" > "$W/18d.log" 2>&1
if cmp -s "$OUT/27_0.5B_18d출력.txt" 문서/결과/18단계/18d_엔진_글.txt; then echo "27b 0.5B 18d — 18d 기록과 바이트까지 같다" >> "$L"; else echo "27b 0.5B 18d — 18d 기록과 다르다" >> "$L"; fi

# ---- 27c · 27d — 26 대 27 을 세 번(홀수 번은 26 먼저, 짝수 번은 27 먼저) ----
for i in 1 2 3; do
  for f in "${FILES[@]}"; do
    if [ $((i % 2)) -eq 1 ]; then ORD="26 27"; else ORD="27 26"; fi
    for b in $ORD; do
      if [ "$b" = 26 ]; then X="$B26/재기_7B.exe"; P="$(ptx "$B26" $f)"; else X=빌드/글/재기_7B.exe; P="$(ptx 빌드/글 $f)"; fi
      echo "27c $b $f $i 시작 $(date '+%T')" >> "$L"
      "$X" "$(gguf $f)" "$P" "$W/공식재기입력7B.bin" "$OUT/27c_${b}_${f}_$i.txt" > "$W/27c_${b}_${f}_$i.log" 2>&1
      echo "27c $b $f $i 끝 $(date '+%T') 종료 $?" >> "$L"
    done
  done
done

# ---- 기록: llama.cpp 프롬프트(같은 GGUF) · 형식마다 커널 시간(27) · 14B Q4_0 · Q4_K_M(26 · 27 한 번씩) ----
for f in "${FILES[@]}"; do
  ( cd "$M7" && "$LB" -m "$(basename "$(gguf $f)")" -p 2048,8192 -n 0 -o md > "$OUT/27기록_라마_${f}_프롬프트.txt" 2>/dev/null )
  echo "기록 라마 $f 종료 $?" >> "$L"
  빌드/글/재기_7B커널.exe "$(gguf $f)" "$(ptx 빌드/글 $f)" "$W/공식재기입력7B.bin" "$OUT/27기록_글_커널마다_$f.txt" > "$W/27기록_커널_$f.log" 2>&1
  echo "기록 커널마다 $f 종료 $?" >> "$L"
done
for b in 26 27; do
  if [ "$b" = 26 ]; then X="$B26/재기_7B.exe"; D="$B26"; else X=빌드/글/재기_7B.exe; D=빌드/글; fi
  "$X" "$M14/qwen2.5-14b-instruct-q4_0-pure.gguf" "$D/qwen2Q4_5120x40x8x13824x152064.ptx" "$W/공식재기입력7B.bin" "$OUT/27기록_${b}_14b-q4_0.txt" > "$W/27기록_${b}_14b-q4_0.log" 2>&1
  echo "기록 14B Q4_0 $b 종료 $?" >> "$L"
  "$X" "$M14/qwen2.5-14b-instruct-q4_k_m-req.gguf" "$D/qwen2K_5120x40x8x13824x152064.ptx" "$W/공식재기입력7B.bin" "$OUT/27기록_${b}_14b-q4_k_m.txt" > "$W/27기록_${b}_14b-q4_k_m.log" 2>&1
  echo "기록 14B Q4_K_M $b 종료 $?" >> "$L"
done
python -I -X utf8 재기/모음27.py "$OUT" "$OUT/27cd_요약.json" >> "$L" 2>&1

# ---- 기록: 실행기 채팅(7B Q4_K_M) ----
printf '대한민국의 수도는 어디야? 한 문장으로.\nWhat is 17 times 23? Answer briefly.\n/끝\n' > "$W/채팅입력27.txt"
빌드/글/실행기.exe "$(gguf q4_k_m)" --생성 64 < "$W/채팅입력27.txt" > "$OUT/27_채팅_7b-q4_k_m.txt" 2>&1
echo "기록 채팅 종료 $?" >> "$L"

# ---- 27a (2) 끝에서 끝 — CPU 참조의 전체 앞으로 ----
for f in q4_0 q4_k_m q6_k; do
  echo "27a(2) $f 시작 $(date '+%T')" >> "$L"
  python -I -X utf8 시험/참조7B.py "$(gguf $f)" "$W/공식27_$f" "$OUT/27a_끝에서끝_$f.json" > "$W/27a_끝에서끝_$f.log" 2>&1
  echo "27a(2) $f 끝 $(date '+%T') 종료 $? — $(tail -1 "$W/27a_끝에서끝_$f.log")" >> "$L"
done
git worktree remove --force "$W/wt26" >> "$L" 2>&1
echo "끝 $(date '+%F %T')" >> "$L"
