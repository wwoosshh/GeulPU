#!/bin/bash
# 23단계 공식 실행 — 고정한 코드(커밋)와 그 빌드로. 결과는 문서/결과/23단계/ 에(큰 로짓 파일은 작업 폴더에).
#   bash 공식23.sh <저장소> <작업폴더>
set -u
R="$1"
W="$2"
OUT="$R/문서/결과/23단계"
MD="$R/모델/qwen2.5-7b-instruct-gguf"
G8="$MD/qwen2.5-7b-instruct-q8_0.gguf"
G4="$MD/qwen2.5-7b-instruct-q4_0-pure.gguf"
G05="$R/모델/qwen2.5-0.5b-instruct-gguf/qwen2.5-0.5b-instruct-q8_0.gguf"
GC="../geul-lang-v2/build/self_컴파일러.exe"
PX="../geul-lang-v2/build/자체PTX.exe"
LB="$R/도구/llama-b11496/llama-bench.exe"
cd "$R"
mkdir -p "$OUT" 빌드/글 "$W"
L="$OUT/23_기록.txt"
echo "시작 $(date '+%F %T') · 커밋 $(git rev-parse --short HEAD) · 바뀐 파일 $(git status --short | grep -v '^??' | wc -l)" > "$L"
nvidia-smi --query-gpu=name,driver_version,clocks.max.sm,clocks.max.mem --format=csv >> "$L"

# ---- 빌드 (글 컴파일러 · 글 PTX 뒷단) ----
echo "빌드 시작 $(date '+%T')" >> "$L"
GEUL_ROOT=../geul-lang-v2 "$GC" 커널/커널생성.gl -o 빌드/글/커널생성.exe >> "$L" 2>&1
for t in 실행기 시험_7B 시험_엔진 재기_7B 재기_7B커널; do
  GEUL_ROOT=../geul-lang-v2 "$GC" "호스트/$t.gl" -o "빌드/글/$t.exe" >> "$L" 2>&1
done
for m in qwen2Q8 qwen2Q8_7b qwen2Q4_7b; do
  빌드/글/커널생성.exe "$m" "빌드/글/$m.gl" >> "$L" 2>&1
  "$PX" "빌드/글/$m.gl" -o "빌드/글/$m.ptx" > "$W/ptx_$m.log" 2>&1
  echo "PTX $m 종료 $?" >> "$L"
done
sha256sum 빌드/글/qwen2Q8.gl 빌드/글/qwen2Q8.ptx 빌드/글/qwen2Q8_7b.gl 빌드/글/qwen2Q8_7b.ptx 빌드/글/qwen2Q4_7b.gl 빌드/글/qwen2Q4_7b.ptx \
  빌드/글/커널생성.exe 빌드/글/실행기.exe 빌드/글/시험_7B.exe 빌드/글/시험_엔진.exe 빌드/글/재기_7B.exe 빌드/글/재기_7B커널.exe >> "$L"
wc -l -c 빌드/글/qwen2Q8_7b.gl 빌드/글/qwen2Q4_7b.gl >> "$L"
echo "빌드 끝 $(date '+%T')" >> "$L"

# ---- 23b (3) 0.5B 소스 해시 (19단계 · 22단계와 같아야 한다) ----
H05=$(sha256sum 빌드/글/qwen2Q8.gl | cut -c1-64)
if [ "$H05" = "0f3153c8901003883ae299287848ebd67a2f8e4d27d94a7ceb37902b37d7f3cd" ]; then echo "23b(3) 0.5B 소스 해시 같음 ($H05)" >> "$L"; else echo "23b(3) 0.5B 소스 해시 다름 ($H05)" >> "$L"; fi

# ---- 23a (1) 커널 비트 ----
for f in Q4 Q8; do
  if [ "$f" = "Q4" ]; then G="$G4"; P=빌드/글/qwen2Q4_7b.ptx; else G="$G8"; P=빌드/글/qwen2Q8_7b.ptx; fi
  echo "23a(1) 판23 $f 시작 $(date '+%T')" >> "$L"
  python -I -X utf8 시험/판23.py "$P" "$G" "$OUT/23a_판_$f.json" > "$W/23a_판_$f.log" 2>&1
  echo "23a(1) 판23 $f 끝 $(date '+%T') 종료 $? — $(tail -1 "$W/23a_판_$f.log")" >> "$L"
done
echo "23a(1) 머리128 시작 $(date '+%T')" >> "$L"
python -I -X utf8 시험/머리128.py 빌드/글/qwen2Q4_7b.ptx "$G8" "$OUT/23a_머리128.json" > "$W/23a_머리128.log" 2>&1
echo "23a(1) 머리128 끝 $(date '+%T') 종료 $? — $(tail -1 "$W/23a_머리128.log")" >> "$L"

# ---- 23b (1) · (2) 다섯 길 ----
python -I -X utf8 시험/입력7B.py "$G8" "$W/공식입력7B.bin" >> "$L" 2>&1
for f in Q4 Q8; do
  if [ "$f" = "Q4" ]; then G="$G4"; P=빌드/글/qwen2Q4_7b.ptx; else G="$G8"; P=빌드/글/qwen2Q8_7b.ptx; fi
  rm -rf "$W/공식7B_$f"
  mkdir -p "$W/공식7B_$f"
  echo "23b 길 $f 시작 $(date '+%T')" >> "$L"
  빌드/글/시험_7B.exe "$G" "$P" "$W/공식입력7B.bin" "$W/공식7B_$f" > "$W/23b_$f.log" 2>&1
  echo "23b 길 $f 끝 $(date '+%T') 종료 $? — $(tail -1 "$W/23b_$f.log")" >> "$L"
  cp "$W/공식7B_$f/요약.txt" "$OUT/23b_요약_$f.txt"
  cp "$W/23b_$f.log" "$OUT/23b_기록_$f.txt"
done
if cmp -s "$OUT/23b_요약_Q8.txt" 문서/결과/22단계/22b_요약.txt; then echo "23b(2) Q8_0 요약 — 22b_요약과 바이트까지 같다" >> "$L"; else echo "23b(2) Q8_0 요약 — 22b_요약과 다르다" >> "$L"; fi

# ---- 23a (2) Q4_0 끝에서 끝 (CPU 참조) ----
echo "23a(2) 끝에서 끝 시작 $(date '+%T')" >> "$L"
python -I -X utf8 시험/참조7B.py "$G4" "$W/공식7B_Q4" "$OUT/23a_끝에서끝_Q4.json" > "$W/23a_끝에서끝.log" 2>&1
echo "23a(2) 끝에서 끝 끝 $(date '+%T') 종료 $? — $(tail -1 "$W/23a_끝에서끝.log")" >> "$L"

# ---- 23b (3) 0.5B 18d 출력 ----
echo "0.5B 회귀(18d) 시작 $(date '+%T')" >> "$L"
python -I -X utf8 "$W/입력18d.py" "$R" "$W/18d입력.bin" >> "$L" 2>&1
빌드/글/시험_엔진.exe "$G05" 빌드/글/qwen2Q8.ptx "$W/18d입력.bin" "$OUT/23_0.5B_18d출력.txt" > "$W/18d.log" 2>&1
if cmp -s "$OUT/23_0.5B_18d출력.txt" 문서/결과/18단계/18d_엔진_글.txt; then echo "23b(3) 0.5B 18d — 18d 기록과 바이트까지 같다" >> "$L"; else echo "23b(3) 0.5B 18d — 18d 기록과 다르다" >> "$L"; fi

# ---- 23c · 23d 속도: 글과 llama.cpp(llama-bench, 같은 GGUF, 기본 설정)를 번갈아 세 번씩 ----
python -I -X utf8 시험/입력7B.py "$G8" "$W/공식재기입력7B.bin" --재기 >> "$L" 2>&1
for i in 1 2 3; do
  for f in Q8_0 Q4_0; do
    if [ "$f" = "Q4_0" ]; then G="$G4"; P=빌드/글/qwen2Q4_7b.ptx; GN=qwen2.5-7b-instruct-q4_0-pure.gguf; else G="$G8"; P=빌드/글/qwen2Q8_7b.ptx; GN=qwen2.5-7b-instruct-q8_0.gguf; fi
    echo "글 $f $i 시작 $(date '+%T')" >> "$L"
    빌드/글/재기_7B.exe "$G" "$P" "$W/공식재기입력7B.bin" "$OUT/23c_글_${f}_$i.txt" >> "$L" 2>&1
    echo "글 $f $i 끝 $(date '+%T') 종료 $?" >> "$L"
    echo "라마 $f $i 시작 $(date '+%T')" >> "$L"
    # llama.cpp 는 한글 경로를 열지 못한다 — 모델 폴더에서 파일 이름(ASCII)으로
    ( cd "$MD" && "$LB" -m "$GN" -p 2048,8192 -n 0 -o md > "$OUT/23c_라마_${f}_프롬프트_$i.txt" 2>/dev/null
      "$LB" -m "$GN" -p 0 -n 128 -d 0,2048,8192 -o md > "$OUT/23c_라마_${f}_생성_$i.txt" 2>/dev/null )
    echo "라마 $f $i 끝 $(date '+%T') 종료 $?" >> "$L"
  done
done
for f in Q8_0 Q4_0; do
  if [ "$f" = "Q4_0" ]; then G="$G4"; P=빌드/글/qwen2Q4_7b.ptx; else G="$G8"; P=빌드/글/qwen2Q8_7b.ptx; fi
  echo "커널마다 $f 시작 $(date '+%T')" >> "$L"
  빌드/글/재기_7B커널.exe "$G" "$P" "$W/공식재기입력7B.bin" "$OUT/23c_글_커널마다_$f.txt" >> "$L" 2>&1
done
python -I -X utf8 재기/모음23.py "$OUT" "$OUT/23cd_요약.json" >> "$L" 2>&1
echo "끝 $(date '+%F %T')" >> "$L"
