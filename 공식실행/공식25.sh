#!/bin/bash
# 25단계 공식 실행 — 고정한 코드(커밋)와 그 빌드로. 결과는 문서/결과/25단계/ 에(로짓 파일은 작업 폴더에).
#   bash 공식25.sh <저장소> <작업폴더>
set -u
R="$1"
W="$2"
OUT="$R/문서/결과/25단계"
M7="$R/모델/qwen2.5-7b-instruct-gguf"
G8="$M7/qwen2.5-7b-instruct-q8_0.gguf"
G4="$M7/qwen2.5-7b-instruct-q4_0-pure.gguf"
G14="$R/모델/qwen2.5-14b-instruct-gguf/qwen2.5-14b-instruct-q4_0-pure.gguf"
G72="$R/모델/합성/qwen2-synth-72b-l4-q4_0.gguf"
P8=빌드/글/qwen2Q8_7b.ptx
P4=빌드/글/qwen2Q4_7b.ptx
P14=빌드/글/qwen2Q4_5120x40x8x13824x152064.ptx
P72=빌드/글/qwen2Q4_8192x64x8x29568x152064.ptx
GC="../geul-lang-v2/build/self_컴파일러.exe"
PX="../geul-lang-v2/build/자체PTX.exe"
cd "$R"
mkdir -p "$OUT" 빌드/글 "$W"
L="$OUT/25_기록.txt"
echo "시작 $(date '+%F %T') · 커밋 $(git rev-parse --short HEAD) · 바뀐 파일 $(git status --short | grep -v '^??' | wc -l)" > "$L"
nvidia-smi --query-gpu=name,driver_version,clocks.max.sm,clocks.max.mem,memory.total --format=csv >> "$L"

# ---- 빌드 (글 컴파일러 · 글 PTX 뒷단) — 커널 생성기는 24단계와 같다: 모듈이 24단계의 바이트와 같은지 본다 ----
echo "빌드 시작 $(date '+%T')" >> "$L"
GEUL_ROOT=../geul-lang-v2 "$GC" 커널/커널생성.gl -o 빌드/글/커널생성.exe >> "$L" 2>&1
for t in 실행기 시험_7B 재기_7B; do
  GEUL_ROOT=../geul-lang-v2 "$GC" "호스트/$t.gl" -o "빌드/글/$t.exe" >> "$L" 2>&1
done
빌드/글/커널생성.exe qwen2Q8_7b 빌드/글/qwen2Q8_7b.gl >> "$L" 2>&1
빌드/글/커널생성.exe qwen2Q4_7b 빌드/글/qwen2Q4_7b.gl >> "$L" 2>&1
빌드/글/커널생성.exe qwen2큰 Q4_0 5120 40 8 13824 152064 빌드/글/qwen2Q4_5120x40x8x13824x152064.gl >> "$L" 2>&1
빌드/글/커널생성.exe qwen2큰 Q4_0 8192 64 8 29568 152064 빌드/글/qwen2Q4_8192x64x8x29568x152064.gl >> "$L" 2>&1
for m in qwen2Q8_7b qwen2Q4_7b qwen2Q4_5120x40x8x13824x152064 qwen2Q4_8192x64x8x29568x152064; do
  "$PX" "빌드/글/$m.gl" -o "빌드/글/$m.ptx" > "$W/ptx_$m.log" 2>&1
  echo "PTX $m 종료 $?" >> "$L"
  for e in gl ptx; do
    h=$(sha256sum "빌드/글/$m.$e" | cut -c1-64)
    if grep -q "^$h \*빌드/글/$m.$e" 문서/결과/24단계/24_기록.txt; then echo "모듈 $m.$e — 24단계와 바이트까지 같다" >> "$L"; else echo "모듈 $m.$e — 24단계와 다르다" >> "$L"; fi
  done
done
sha256sum 빌드/글/qwen2Q8_7b.* 빌드/글/qwen2Q4_7b.* 빌드/글/qwen2Q4_5120x40x8x13824x152064.* 빌드/글/qwen2Q4_8192x64x8x29568x152064.* \
  빌드/글/커널생성.exe 빌드/글/실행기.exe 빌드/글/시험_7B.exe 빌드/글/재기_7B.exe >> "$L"
echo "빌드 끝 $(date '+%T')" >> "$L"

# ---- 입력 ----
python -I -X utf8 시험/입력7B.py "$G8" "$W/공식입력7B.bin" >> "$L" 2>&1
python -I -X utf8 시험/입력7B.py "$G8" "$W/공식무작위입력.bin" --무작위 24 >> "$L" 2>&1
python -I -X utf8 시험/입력7B.py "$G8" "$W/공식재기입력7B.bin" --재기 >> "$L" 2>&1

# ---- 25a 비트: 다섯 길의 요약을 한 조각(이 실행)과 앞 단계의 요약에 견준다 ----
# 이름|GGUF|PTX|입력|인자|앞 단계 요약
RUNS=( "7b-q8_p1|$G8|$P8|공식입력7B.bin||문서/결과/23단계/23b_요약_Q8.txt"
       "7b-q8_p2|$G8|$P8|공식입력7B.bin|--나누기 2|문서/결과/23단계/23b_요약_Q8.txt"
       "7b-q8_p3|$G8|$P8|공식입력7B.bin|--나누기 3|문서/결과/23단계/23b_요약_Q8.txt"
       "7b-q8_p4|$G8|$P8|공식입력7B.bin|--나누기 4|문서/결과/23단계/23b_요약_Q8.txt"
       "7b-q4_p1|$G4|$P4|공식입력7B.bin||문서/결과/23단계/23b_요약_Q4.txt"
       "7b-q4_p2|$G4|$P4|공식입력7B.bin|--나누기 2|문서/결과/23단계/23b_요약_Q4.txt"
       "7b-q4_p3|$G4|$P4|공식입력7B.bin|--나누기 3|문서/결과/23단계/23b_요약_Q4.txt"
       "7b-q4_p4|$G4|$P4|공식입력7B.bin|--나누기 4|문서/결과/23단계/23b_요약_Q4.txt"
       "7b-q4_p2하나|$G4|$P4|공식입력7B.bin|--나누기 2 --문맥 하나|문서/결과/23단계/23b_요약_Q4.txt"
       "7b-q4_p2피어|$G4|$P4|공식입력7B.bin|--나누기 2 --넘김 피어|문서/결과/23단계/23b_요약_Q4.txt"
       "14b-q4_p1|$G14|$P14|공식입력7B.bin||문서/결과/24단계/24c_요약_14b-q4_0.txt"
       "14b-q4_p2|$G14|$P14|공식입력7B.bin|--나누기 2|문서/결과/24단계/24c_요약_14b-q4_0.txt"
       "14b-q4_p3|$G14|$P14|공식입력7B.bin|--나누기 3|문서/결과/24단계/24c_요약_14b-q4_0.txt"
       "72b-q4_p1|$G72|$P72|공식무작위입력.bin||문서/결과/24단계/24c_요약_72b-l4-q4_0.txt"
       "72b-q4_p2|$G72|$P72|공식무작위입력.bin|--나누기 2|문서/결과/24단계/24c_요약_72b-l4-q4_0.txt"
       "72b-q4_p4|$G72|$P72|공식무작위입력.bin|--나누기 4|문서/결과/24단계/24c_요약_72b-l4-q4_0.txt" )
run_a() {   # 이름 GGUF PTX 입력 인자 앞요약 [판정줄 머리]
  local n="$1" G="$2" P="$3" IN="$4" A="$5" REF="$6" T="${7:-25a}"
  rm -rf "$W/공식25_$n"
  mkdir -p "$W/공식25_$n"
  echo "$T $n 시작 $(date '+%T')" >> "$L"
  # shellcheck disable=SC2086
  빌드/글/시험_7B.exe "$G" "$P" "$W/$IN" "$W/공식25_$n" $A > "$W/25a_$n.log" 2>&1
  local r=$?
  [ -f "$W/공식25_$n/요약.txt" ] && cp "$W/공식25_$n/요약.txt" "$OUT/${T}_요약_$n.txt"
  cp "$W/25a_$n.log" "$OUT/${T}_기록_$n.txt"
  local b="${n%_*}_p1"
  local s1=다름 s2=다름
  cmp -s "$W/공식25_$n/요약.txt" "$W/공식25_$b/요약.txt" && s1=같음
  cmp -s "$W/공식25_$n/요약.txt" "$REF" && s2=같음
  echo "$T $n 끝 $(date '+%T') 종료 $r — $(tail -1 "$W/25a_$n.log") · 한 조각(이 실행)과 $s1 · 앞 단계 요약과 $s2" >> "$L"
}
for x in "${RUNS[@]}"; do
  IFS='|' read -r n G P IN A REF <<< "$x"
  run_a "$n" "$G" "$P" "$IN" "$A" "$REF"
done

# ---- 25b 예산: 조각 하나에 6 GB 면 알리고 멈춘다 · 두 조각이면 예산으로 나눈다 ----
rm -rf "$W/공식25_14b-q4_예산1"
mkdir -p "$W/공식25_14b-q4_예산1"
빌드/글/시험_7B.exe "$G14" "$P14" "$W/공식입력7B.bin" "$W/공식25_14b-q4_예산1" --예산 6 > "$W/25b_예산1.log" 2>&1
echo "25b 14b-q4 --예산 6 (조각 하나): 종료 $? — $(tail -1 "$W/25b_예산1.log")" >> "$L"
cp "$W/25b_예산1.log" "$OUT/25b_기록_예산6_조각하나.txt"
run_a "14b-q4_예산2" "$G14" "$P14" 공식입력7B.bin "--나누기 2 --예산 6" 문서/결과/24단계/24c_요약_14b-q4_0.txt 25b

# ---- 기록: 실행기 채팅 — 7B Q4_0 한 조각 · 두 조각의 답 ----
printf '대한민국의 수도는 어디야? 한 문장으로.\nWhat is 17 times 23? Answer briefly.\n/끝\n' > "$W/채팅입력25.txt"
빌드/글/실행기.exe "$G4" --생성 64 < "$W/채팅입력25.txt" > "$OUT/25_채팅_7b-q4_한조각.txt" 2>&1
빌드/글/실행기.exe "$G4" --생성 64 --나누기 2 < "$W/채팅입력25.txt" > "$OUT/25_채팅_7b-q4_두조각.txt" 2>&1
if diff <(grep -v '^올림\|^\[첫\|^조각\|^넘김\|^모델' "$OUT/25_채팅_7b-q4_한조각.txt") <(grep -v '^올림\|^\[첫\|^조각\|^넘김\|^모델' "$OUT/25_채팅_7b-q4_두조각.txt") > /dev/null; then
  echo "기록 실행기 채팅 7B Q4_0 — 한 조각 · 두 조각의 답이 같다" >> "$L"
else
  echo "기록 실행기 채팅 7B Q4_0 — 한 조각 · 두 조각의 답이 다르다" >> "$L"
fi

# ---- 25c 속도: 모델마다 한 조각 · 두 조각 · 두 조각(문맥 하나)을 번갈아 세 번, 그다음 셋 · 넷을 한 번씩 ----
run_c() {   # 모델 판 GGUF PTX 인자 번
  local m="$1" c="$2" G="$3" P="$4" A="$5" i="$6"
  echo "25c $m $c $i 시작 $(date '+%T')" >> "$L"
  # shellcheck disable=SC2086
  빌드/글/재기_7B.exe "$G" "$P" "$W/공식재기입력7B.bin" "$OUT/25c_글_${m}_${c}_$i.txt" $A > "$W/25c_${m}_${c}_$i.log" 2>&1
  echo "25c $m $c $i 끝 $(date '+%T') 종료 $?" >> "$L"
}
for i in 1 2 3; do
  run_c 7b-q4 p1 "$G4" "$P4" "" "$i"
  run_c 7b-q4 p2 "$G4" "$P4" "--나누기 2" "$i"
  run_c 7b-q4 p2하나 "$G4" "$P4" "--나누기 2 --문맥 하나" "$i"
done
run_c 7b-q4 p3 "$G4" "$P4" "--나누기 3" 1
run_c 7b-q4 p4 "$G4" "$P4" "--나누기 4" 1
for i in 1 2 3; do
  run_c 14b-q4 p1 "$G14" "$P14" "" "$i"
  run_c 14b-q4 p2 "$G14" "$P14" "--나누기 2" "$i"
  run_c 14b-q4 p2하나 "$G14" "$P14" "--나누기 2 --문맥 하나" "$i"
done
run_c 14b-q4 p3 "$G14" "$P14" "--나누기 3" 1
for f in "$W"/25c_*.log; do echo "== $(basename "$f")"; grep '^조각\|^넘김\|오류\|넘는다' "$f"; done > "$OUT/25c_조각기록.txt"
python -I -X utf8 재기/모음25.py "$OUT" "$OUT/25c_요약.json" >> "$L" 2>&1

# ---- 기록: 넘김 방법 · 문맥 바꾸기의 값(탐침) ----
python -I -X utf8 재기/넘김재기25.py > "$OUT/25_넘김재기.txt" 2>&1
python -I -X utf8 재기/문맥바꾸기25.py > "$OUT/25_문맥바꾸기.txt" 2>&1
echo "끝 $(date '+%F %T')" >> "$L"
