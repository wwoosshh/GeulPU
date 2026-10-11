#!/bin/bash
# 26단계 공식 실행 — 고정한 코드(커밋)와 그 빌드로. 결과는 문서/결과/26단계/ 에(로짓 등 큰 파일은 작업 폴더에).
#   bash 공식실행/공식26.sh <저장소> <작업폴더>
# 차례: 빌드 → 26a(1) 판 → 26b 길 · 그대로 · 두 조각 → 26c · 26d 속도(번갈아 세 번) → 기록 커널마다 · 14B Q4_K_M → 모음 → 실행기 채팅 기록
# → 26a(2) CPU 참조(끝에 — CPU 를 많이 써서 시간 재기와 겹치지 않게).
set -u
R="$1"
W="$2"
OUT="$R/문서/결과/26단계"
M7="$R/모델/qwen2.5-7b-instruct-gguf"
G8="$M7/qwen2.5-7b-instruct-q8_0.gguf"
G4="$M7/qwen2.5-7b-instruct-q4_0-pure.gguf"
M14="$R/모델/qwen2.5-14b-instruct-gguf"
G14="$M14/qwen2.5-14b-instruct-q4_0-pure.gguf"
G14K="$M14/qwen2.5-14b-instruct-q4_k_m-req.gguf"
G05="$R/모델/qwen2.5-0.5b-instruct-gguf/qwen2.5-0.5b-instruct-q8_0.gguf"
GC="../geul-lang-v2/build/self_컴파일러.exe"
PX="../geul-lang-v2/build/자체PTX.exe"
LB="$R/도구/llama-b11496/llama-bench.exe"
LQ="$R/도구/llama-b11496/llama-quantize.exe"
PK7=빌드/글/qwen2K_3584x28x4x18944x152064.ptx
PK14=빌드/글/qwen2K_5120x40x8x13824x152064.ptx
P14=빌드/글/qwen2Q4_5120x40x8x13824x152064.ptx
FILES=(q4_k_m q5_k_m q6_k)
cd "$R"
mkdir -p "$OUT" 빌드/글 "$W"
L="$OUT/26_기록.txt"
echo "시작 $(date '+%F %T') · 커밋 $(git rev-parse --short HEAD) · 바뀐 파일 $(git status --short | grep -v '^??' | wc -l)" > "$L"
nvidia-smi --query-gpu=name,driver_version,clocks.max.sm,clocks.max.mem,memory.total --format=csv >> "$L"

# ---- 빌드 — 고전 모듈은 24단계와 바이트까지 같은지 본다 ----
echo "빌드 시작 $(date '+%T')" >> "$L"
GEUL_ROOT=../geul-lang-v2 "$GC" 커널/커널생성.gl -o 빌드/글/커널생성.exe >> "$L" 2>&1
for t in 실행기 시험_7B 시험_엔진 재기_7B 재기_7B커널; do
  GEUL_ROOT=../geul-lang-v2 "$GC" "호스트/$t.gl" -o "빌드/글/$t.exe" >> "$L" 2>&1
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
for m in qwen2Q8 qwen2Q8_7b qwen2Q4_7b qwen2Q4_5120x40x8x13824x152064; do
  for e in gl ptx; do
    h=$(sha256sum "빌드/글/$m.$e" | cut -c1-64)
    if grep -q "^$h \*빌드/글/$m.$e" 문서/결과/24단계/24_기록.txt; then echo "모듈 $m.$e — 24단계와 바이트까지 같다" >> "$L"; else echo "모듈 $m.$e — 24단계와 다르다" >> "$L"; fi
  done
done
sha256sum 빌드/글/qwen2K_*.gl 빌드/글/qwen2K_*.ptx 빌드/글/커널생성.exe 빌드/글/실행기.exe 빌드/글/시험_7B.exe 빌드/글/시험_엔진.exe 빌드/글/재기_7B.exe 빌드/글/재기_7B커널.exe >> "$L"
echo "빌드 끝 $(date '+%T')" >> "$L"

# ---- 입력 ----
python -I -X utf8 시험/입력7B.py "$G8" "$W/공식입력7B.bin" >> "$L" 2>&1
python -I -X utf8 시험/입력7B.py "$G8" "$W/공식재기입력7B.bin" --재기 >> "$L" 2>&1
python -I -X utf8 공식실행/입력18d.py "$R" "$W/18d입력.bin" >> "$L" 2>&1

# ---- 26a (1) 판 — 세 파일 · 형식 셋 · 타일 판 11 × 끝손질 셋 · 줄 판 · 로짓 · 임베딩 ----
echo "26a(1) 시작 $(date '+%T')" >> "$L"
python -I -X utf8 시험/판26.py "$PK7" "$M7/qwen2.5-7b-instruct-q4_k_m-req.gguf" "$M7/qwen2.5-7b-instruct-q5_k_m-req.gguf" \
  "$M7/qwen2.5-7b-instruct-q6_k-req.gguf" "$OUT/26a_판.json" > "$W/26a_판.log" 2>&1
echo "26a(1) 끝 $(date '+%T') 종료 $? — $(tail -1 "$W/26a_판.log")" >> "$L"

# ---- 26b (1) 다섯 길 (로짓은 26a (2) 의 입력) ----
for f in "${FILES[@]}"; do
  rm -rf "$W/공식26_$f"
  mkdir -p "$W/공식26_$f"
  echo "26b(1) $f 시작 $(date '+%T')" >> "$L"
  빌드/글/시험_7B.exe "$M7/qwen2.5-7b-instruct-$f-req.gguf" "$PK7" "$W/공식입력7B.bin" "$W/공식26_$f" > "$W/26b_$f.log" 2>&1
  echo "26b(1) $f 끝 $(date '+%T') 종료 $? — $(tail -1 "$W/26b_$f.log")" >> "$L"
  cp "$W/공식26_$f/요약.txt" "$OUT/26b_요약_$f.txt"
  cp "$W/26b_$f.log" "$OUT/26b_기록_$f.txt"
done

# ---- 26b (2) 그대로 · (3) 두 조각 ----
run_same() {   # 이름 GGUF PTX 인자 견줄요약
  local n="$1" G="$2" P="$3" A="$4" REF="$5"
  rm -rf "$W/공식26_$n"
  mkdir -p "$W/공식26_$n"
  # shellcheck disable=SC2086
  빌드/글/시험_7B.exe "$G" "$P" "$W/공식입력7B.bin" "$W/공식26_$n" $A > "$W/26b_$n.log" 2>&1
  local r=$?
  local s=다름
  cmp -s "$W/공식26_$n/요약.txt" "$REF" && s=같음
  echo "26b $n 종료 $r — $(tail -1 "$W/26b_$n.log") · 견줄 요약과 $s" >> "$L"
  cp "$W/26b_$n.log" "$OUT/26b_기록_$n.txt"
}
run_same 7b-q8_0 "$G8" 빌드/글/qwen2Q8_7b.ptx "" 문서/결과/23단계/23b_요약_Q8.txt
run_same 7b-q4_0 "$G4" 빌드/글/qwen2Q4_7b.ptx "" 문서/결과/23단계/23b_요약_Q4.txt
run_same 14b-q4_0 "$G14" "$P14" "" 문서/결과/24단계/24c_요약_14b-q4_0.txt
run_same 7b-q4_0_p2 "$G4" 빌드/글/qwen2Q4_7b.ptx "--나누기 2" 문서/결과/25단계/25a_요약_7b-q4_p2.txt
run_same q4_k_m_p2 "$M7/qwen2.5-7b-instruct-q4_k_m-req.gguf" "$PK7" "--나누기 2" "$W/공식26_q4_k_m/요약.txt"
빌드/글/시험_엔진.exe "$G05" 빌드/글/qwen2Q8.ptx "$W/18d입력.bin" "$OUT/26_0.5B_18d출력.txt" > "$W/18d.log" 2>&1
if cmp -s "$OUT/26_0.5B_18d출력.txt" 문서/결과/18단계/18d_엔진_글.txt; then echo "26b 0.5B 18d — 18d 기록과 바이트까지 같다" >> "$L"; else echo "26b 0.5B 18d — 18d 기록과 다르다" >> "$L"; fi

# ---- 26c · 26d 속도 — 글과 llama.cpp 를 세 번 번갈아 ----
for i in 1 2 3; do
  for f in "${FILES[@]}"; do
    echo "26c 글 $f $i 시작 $(date '+%T')" >> "$L"
    빌드/글/재기_7B.exe "$M7/qwen2.5-7b-instruct-$f-req.gguf" "$PK7" "$W/공식재기입력7B.bin" "$OUT/26c_글_${f}_$i.txt" > "$W/26c_글_${f}_$i.log" 2>&1
    echo "26c 글 $f $i 끝 $(date '+%T') 종료 $?" >> "$L"
    ( cd "$M7" && "$LB" -m "qwen2.5-7b-instruct-$f-req.gguf" -p 2048,8192 -n 0 -o md > "$OUT/26c_라마_${f}_프롬프트_$i.txt" 2>/dev/null
      "$LB" -m "qwen2.5-7b-instruct-$f-req.gguf" -p 0 -n 128 -d 0,2048,8192 -o md > "$OUT/26c_라마_${f}_생성_$i.txt" 2>/dev/null )
    echo "26c 라마 $f $i 끝 $(date '+%T') 종료 $?" >> "$L"
  done
done

# ---- 기록: 형식마다 커널 시간(이벤트 사이에 띄움 하나씩 — 26c 의 시간이 아니다) ----
for f in "${FILES[@]}"; do
  빌드/글/재기_7B커널.exe "$M7/qwen2.5-7b-instruct-$f-req.gguf" "$PK7" "$W/공식재기입력7B.bin" "$OUT/26기록_글_커널마다_$f.txt" > "$W/26기록_커널_$f.log" 2>&1
  echo "기록 커널마다 $f 종료 $?" >> "$L"
done

# ---- 기록: 14B Q4_K_M (가진 14B Q4_0 에서 다시 양자화 — 섞음은 llama.cpp 그대로) ----
if [ ! -f "$G14K" ]; then
  ( cd "$M14" && "$LQ" --allow-requantize qwen2.5-14b-instruct-q4_0-pure.gguf qwen2.5-14b-instruct-q4_k_m-req.gguf Q4_K_M 8 > "$W/양자화_14b.log" 2>&1 )
  echo "기록 14B Q4_K_M 만들기 종료 $?" >> "$L"
fi
빌드/글/재기_7B.exe "$G14K" "$PK14" "$W/공식재기입력7B.bin" "$OUT/26기록_글_14b-q4_k_m.txt" > "$W/26기록_14b.log" 2>&1
echo "기록 14B 글 종료 $?" >> "$L"
( cd "$M14" && "$LB" -m qwen2.5-14b-instruct-q4_k_m-req.gguf -p 2048,8192 -n 0 -o md > "$OUT/26기록_라마_14b-q4_k_m_프롬프트.txt" 2>/dev/null
  "$LB" -m qwen2.5-14b-instruct-q4_k_m-req.gguf -p 0 -n 128 -d 0,2048,8192 -o md > "$OUT/26기록_라마_14b-q4_k_m_생성.txt" 2>/dev/null )
echo "기록 14B 라마 종료 $?" >> "$L"
python -I -X utf8 재기/모음26.py "$OUT" "$OUT/26cd_요약.json" "$M7" "$G14K" >> "$L" 2>&1

# ---- 기록: 실행기 채팅(7B Q4_K_M) ----
printf '대한민국의 수도는 어디야? 한 문장으로.\nWhat is 17 times 23? Answer briefly.\n/끝\n' > "$W/채팅입력26.txt"
빌드/글/실행기.exe "$M7/qwen2.5-7b-instruct-q4_k_m-req.gguf" --생성 64 < "$W/채팅입력26.txt" > "$OUT/26_채팅_7b-q4_k_m.txt" 2>&1
echo "기록 채팅 종료 $?" >> "$L"

# ---- 26a (2) 끝에서 끝 — CPU 참조의 전체 앞으로(파일마다 수십 분) ----
for f in "${FILES[@]}"; do
  echo "26a(2) $f 시작 $(date '+%T')" >> "$L"
  python -I -X utf8 시험/참조7B.py "$M7/qwen2.5-7b-instruct-$f-req.gguf" "$W/공식26_$f" "$OUT/26a_끝에서끝_$f.json" > "$W/26a_끝에서끝_$f.log" 2>&1
  echo "26a(2) $f 끝 $(date '+%T') 종료 $? — $(tail -1 "$W/26a_끝에서끝_$f.log")" >> "$L"
done
echo "끝 $(date '+%F %T')" >> "$L"
