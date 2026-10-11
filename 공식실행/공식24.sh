#!/bin/bash
# 24단계 공식 실행 — 고정한 코드(커밋)와 그 빌드로. 결과는 문서/결과/24단계/ 에(큰 로짓 파일은 작업 폴더에).
#   bash 공식24.sh <저장소> <작업폴더>
set -u
R="$1"
W="$2"
OUT="$R/문서/결과/24단계"
M7="$R/모델/qwen2.5-7b-instruct-gguf"
G8="$M7/qwen2.5-7b-instruct-q8_0.gguf"
G4="$M7/qwen2.5-7b-instruct-q4_0-pure.gguf"
M14="$R/모델/qwen2.5-14b-instruct-gguf"
G14="$M14/qwen2.5-14b-instruct-q4_0-pure.gguf"
MS="$R/모델/합성"
G05="$R/모델/qwen2.5-0.5b-instruct-gguf/qwen2.5-0.5b-instruct-q8_0.gguf"
GC="../geul-lang-v2/build/self_컴파일러.exe"
PX="../geul-lang-v2/build/자체PTX.exe"
LB="$R/도구/llama-b11496/llama-bench.exe"
cd "$R"
mkdir -p "$OUT" 빌드/글 "$W"
L="$OUT/24_기록.txt"
echo "시작 $(date '+%F %T') · 커밋 $(git rev-parse --short HEAD) · 바뀐 파일 $(git status --short | grep -v '^??' | wc -l)" > "$L"
nvidia-smi --query-gpu=name,driver_version,clocks.max.sm,clocks.max.mem,memory.total --format=csv >> "$L"

# ---- 빌드 (글 컴파일러 · 글 PTX 뒷단) ----
echo "빌드 시작 $(date '+%T')" >> "$L"
GEUL_ROOT=../geul-lang-v2 "$GC" 커널/커널생성.gl -o 빌드/글/커널생성.exe >> "$L" 2>&1
for t in 실행기 시험_7B 시험_엔진 재기_7B 재기_7B커널; do
  GEUL_ROOT=../geul-lang-v2 "$GC" "호스트/$t.gl" -o "빌드/글/$t.exe" >> "$L" 2>&1
done
빌드/글/커널생성.exe qwen2Q8 빌드/글/qwen2Q8.gl >> "$L" 2>&1
빌드/글/커널생성.exe qwen2Q8_7b 빌드/글/qwen2Q8_7b.gl >> "$L" 2>&1
빌드/글/커널생성.exe qwen2Q4_7b 빌드/글/qwen2Q4_7b.gl >> "$L" 2>&1
# 24a — qwen2큰 길에 7B 모양
빌드/글/커널생성.exe qwen2큰 Q8_0 3584 28 4 18944 152064 "$W/24a_큰Q8_7b.gl" >> "$L" 2>&1
빌드/글/커널생성.exe qwen2큰 Q4_0 3584 28 4 18944 152064 "$W/24a_큰Q4_7b.gl" >> "$L" 2>&1
# 새 모양
for m in "Q4_0 5120 40 8 13824 qwen2Q4_5120x40x8x13824x152064" "Q4_0 5120 40 8 27648 qwen2Q4_5120x40x8x27648x152064" \
         "Q8_0 5120 40 8 27648 qwen2Q8_5120x40x8x27648x152064" "Q4_0 8192 64 8 29568 qwen2Q4_8192x64x8x29568x152064" \
         "Q8_0 8192 64 8 29568 qwen2Q8_8192x64x8x29568x152064"; do
  set -- $m
  빌드/글/커널생성.exe qwen2큰 "$1" "$2" "$3" "$4" "$5" 152064 "빌드/글/$6.gl" >> "$L" 2>&1
done
for m in qwen2Q8 qwen2Q8_7b qwen2Q4_7b qwen2Q4_5120x40x8x13824x152064 qwen2Q4_5120x40x8x27648x152064 qwen2Q8_5120x40x8x27648x152064 \
         qwen2Q4_8192x64x8x29568x152064 qwen2Q8_8192x64x8x29568x152064; do
  "$PX" "빌드/글/$m.gl" -o "빌드/글/$m.ptx" > "$W/ptx_$m.log" 2>&1
  echo "PTX $m 종료 $?" >> "$L"
done
sha256sum 빌드/글/*.gl 빌드/글/*.ptx "$W/24a_큰Q8_7b.gl" "$W/24a_큰Q4_7b.gl" 빌드/글/커널생성.exe 빌드/글/실행기.exe 빌드/글/시험_7B.exe \
  빌드/글/시험_엔진.exe 빌드/글/재기_7B.exe 빌드/글/재기_7B커널.exe | sed "s#$W/##" >> "$L"
echo "빌드 끝 $(date '+%T')" >> "$L"

# ---- 24a 바이트 ----
h() { sha256sum "$1" | cut -c1-64; }
[ "$(h 빌드/글/qwen2Q8.gl)" = "0f3153c8901003883ae299287848ebd67a2f8e4d27d94a7ceb37902b37d7f3cd" ] && echo "24a 0.5B 같음" >> "$L" || echo "24a 0.5B 다름" >> "$L"
for a in "빌드/글/qwen2Q8_7b.gl 1c7da2143ca400cfe2fc90f520094610ba2891216ab7f106d28057dc65dcd40e" "$W/24a_큰Q8_7b.gl 1c7da2143ca400cfe2fc90f520094610ba2891216ab7f106d28057dc65dcd40e" \
         "빌드/글/qwen2Q4_7b.gl 853497d4152c41d1b014f434ec248d89ed08c0f7cf3dbcf0976528395b1fc9c5" "$W/24a_큰Q4_7b.gl 853497d4152c41d1b014f434ec248d89ed08c0f7cf3dbcf0976528395b1fc9c5"; do
  set -- $a
  [ "$(h "$1")" = "$2" ] && echo "24a $(basename "$1") 같음" >> "$L" || echo "24a $(basename "$1") 다름" >> "$L"
done

# 새 모델 표: 이름 GGUF 모듈 입력종류
MODELS=( "14b-q4_0|$G14|qwen2Q4_5120x40x8x13824x152064|채팅"
     "32b-l4-q4_0|$MS/qwen2-synth-32b-l4-q4_0.gguf|qwen2Q4_5120x40x8x27648x152064|무작위"
     "32b-l4-q8_0|$MS/qwen2-synth-32b-l4-q8_0.gguf|qwen2Q8_5120x40x8x27648x152064|무작위"
     "72b-l4-q4_0|$MS/qwen2-synth-72b-l4-q4_0.gguf|qwen2Q4_8192x64x8x29568x152064|무작위"
     "72b-l4-q8_0|$MS/qwen2-synth-72b-l4-q8_0.gguf|qwen2Q8_8192x64x8x29568x152064|무작위" )
python -I -X utf8 시험/입력7B.py "$G8" "$W/공식입력7B.bin" >> "$L" 2>&1
python -I -X utf8 시험/입력7B.py "$G8" "$W/공식무작위입력.bin" --무작위 24 >> "$L" 2>&1

# ---- 24b (1) 커널 비트 ----
for x in "${MODELS[@]}"; do
  IFS='|' read -r n G P k <<< "$x"
  echo "24b(1) 판 $n 시작 $(date '+%T')" >> "$L"
  python -I -X utf8 시험/판23.py "빌드/글/$P.ptx" "$G" "$OUT/24b_판_$n.json" > "$W/24b_판_$n.log" 2>&1
  echo "24b(1) 판 $n 끝 $(date '+%T') 종료 $? — $(tail -1 "$W/24b_판_$n.log")" >> "$L"
  echo "24b(1) 머리128 $n 시작 $(date '+%T')" >> "$L"
  python -I -X utf8 시험/머리128.py "빌드/글/$P.ptx" "$G" "$OUT/24b_머리128_$n.json" > "$W/24b_머리128_$n.log" 2>&1
  echo "24b(1) 머리128 $n 끝 $(date '+%T') 종료 $? — $(tail -1 "$W/24b_머리128_$n.log")" >> "$L"
done

# ---- 24c 다섯 길 · 24b (2) 끝에서 끝 ----
for x in "${MODELS[@]}"; do
  IFS='|' read -r n G P k <<< "$x"
  IN="$W/공식입력7B.bin"; [ "$k" = "무작위" ] && IN="$W/공식무작위입력.bin"
  rm -rf "$W/공식24_$n"
  mkdir -p "$W/공식24_$n"
  echo "24c 길 $n 시작 $(date '+%T')" >> "$L"
  빌드/글/시험_7B.exe "$G" "빌드/글/$P.ptx" "$IN" "$W/공식24_$n" > "$W/24c_$n.log" 2>&1
  echo "24c 길 $n 끝 $(date '+%T') 종료 $? — $(tail -1 "$W/24c_$n.log")" >> "$L"
  cp "$W/공식24_$n/요약.txt" "$OUT/24c_요약_$n.txt"
  cp "$W/24c_$n.log" "$OUT/24c_기록_$n.txt"
  echo "24b(2) 끝에서 끝 $n 시작 $(date '+%T')" >> "$L"
  python -I -X utf8 시험/참조7B.py "$G" "$W/공식24_$n" "$OUT/24b_끝에서끝_$n.json" > "$W/24b_끝에서끝_$n.log" 2>&1
  echo "24b(2) 끝에서 끝 $n 끝 $(date '+%T') 종료 $? — $(tail -1 "$W/24b_끝에서끝_$n.log")" >> "$L"
done

# ---- 그대로(회귀): 7B Q8_0 · Q4_0 다섯 길, 0.5B 18d ----
for f in Q8 Q4; do
  if [ "$f" = "Q4" ]; then G="$G4"; P=빌드/글/qwen2Q4_7b.ptx; else G="$G8"; P=빌드/글/qwen2Q8_7b.ptx; fi
  rm -rf "$W/공식24_7b_$f"
  mkdir -p "$W/공식24_7b_$f"
  빌드/글/시험_7B.exe "$G" "$P" "$W/공식입력7B.bin" "$W/공식24_7b_$f" > "$W/24_7b_$f.log" 2>&1
  if cmp -s "$W/공식24_7b_$f/요약.txt" "문서/결과/23단계/23b_요약_$f.txt"; then echo "회귀 7B $f — 23b 요약과 바이트까지 같다" >> "$L"; else echo "회귀 7B $f — 23b 요약과 다르다" >> "$L"; fi
done
python -I -X utf8 "$W/입력18d.py" "$R" "$W/18d입력.bin" >> "$L" 2>&1
빌드/글/시험_엔진.exe "$G05" 빌드/글/qwen2Q8.ptx "$W/18d입력.bin" "$OUT/24_0.5B_18d출력.txt" > "$W/18d.log" 2>&1
if cmp -s "$OUT/24_0.5B_18d출력.txt" 문서/결과/18단계/18d_엔진_글.txt; then echo "회귀 0.5B 18d — 18d 기록과 바이트까지 같다" >> "$L"; else echo "회귀 0.5B 18d — 18d 기록과 다르다" >> "$L"; fi

# ---- 24d 속도: 14B Q4_0 — 글과 llama.cpp 를 번갈아 세 번 ----
python -I -X utf8 시험/입력7B.py "$G8" "$W/공식재기입력7B.bin" --재기 >> "$L" 2>&1
P14=빌드/글/qwen2Q4_5120x40x8x13824x152064.ptx
( for t in $(seq 1 80); do nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits; sleep 3; done ) > "$W/24_14b_메모리.txt" 2>/dev/null &
for i in 1 2 3; do
  echo "글 14b $i 시작 $(date '+%T')" >> "$L"
  빌드/글/재기_7B.exe "$G14" "$P14" "$W/공식재기입력7B.bin" "$OUT/24d_글_14b_$i.txt" >> "$L" 2>&1
  echo "글 14b $i 끝 $(date '+%T') 종료 $?" >> "$L"
  echo "라마 14b $i 시작 $(date '+%T')" >> "$L"
  ( cd "$M14" && "$LB" -m qwen2.5-14b-instruct-q4_0-pure.gguf -p 2048,8192 -n 0 -o md > "$OUT/24d_라마_14b_프롬프트_$i.txt" 2>/dev/null
    "$LB" -m qwen2.5-14b-instruct-q4_0-pure.gguf -p 0 -n 128 -d 0,2048,8192 -o md > "$OUT/24d_라마_14b_생성_$i.txt" 2>/dev/null )
  echo "라마 14b $i 끝 $(date '+%T') 종료 $?" >> "$L"
done
echo "커널마다 14b 시작 $(date '+%T')" >> "$L"
빌드/글/재기_7B커널.exe "$G14" "$P14" "$W/공식재기입력7B.bin" "$OUT/24d_글_커널마다_14b.txt" >> "$L" 2>&1
# ---- 기록: 합성 모델(층 넷) 한 번씩 ----
for x in "${MODELS[@]:1}"; do
  IFS='|' read -r n G P k <<< "$x"
  echo "기록 글 $n 시작 $(date '+%T')" >> "$L"
  빌드/글/재기_7B.exe "$G" "빌드/글/$P.ptx" "$W/공식재기입력7B.bin" "$OUT/24기록_글_$n.txt" >> "$L" 2>&1
  GN=$(basename "$G")
  ( cd "$MS" && "$LB" -m "$GN" -p 2048,8192 -n 0 -o md > "$OUT/24기록_라마_${n}_프롬프트.txt" 2>/dev/null
    "$LB" -m "$GN" -p 0 -n 128 -d 0,2048,8192 -o md > "$OUT/24기록_라마_${n}_생성.txt" 2>/dev/null )
  echo "기록 $n 끝 $(date '+%T')" >> "$L"
done
echo "기록 14B 의 장치 메모리(재기 첫 4 분, MiB) 가장 큰 값: $(sort -n "$W/24_14b_메모리.txt" | tail -1)" >> "$L"
python -I -X utf8 재기/모음24.py "$OUT" "$OUT/24d_요약.json" >> "$L" 2>&1
powershell -NoProfile -ExecutionPolicy Bypass -File "$W/공식24채팅.ps1" "$(cygpath -w "$R")" "$(cygpath -w "$OUT")" >> "$L" 2>&1
echo "끝 $(date '+%F %T')" >> "$L"
