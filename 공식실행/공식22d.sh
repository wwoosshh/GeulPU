#!/bin/bash
# 22d — 글(재기_7B) 과 llama.cpp(llama-bench, 같은 GGUF, 기본 설정)를 번갈아 세 번씩. 결과는 문서/결과/22단계/ 에.
#   bash 공식22d.sh <저장소> <재기입력.bin>
set -u
R="$1"
IN="$2"
OUT="$R/문서/결과/22단계"
G7="$R/모델/qwen2.5-7b-instruct-gguf/qwen2.5-7b-instruct-q8_0.gguf"
LB="$R/도구/llama-b11496/llama-bench.exe"
cd "$R"
echo "시작 $(date '+%F %T')" > "$OUT/22d_기록.txt"
nvidia-smi --query-gpu=name,driver_version,clocks.max.sm,clocks.max.mem --format=csv >> "$OUT/22d_기록.txt"
for i in 1 2 3; do
  echo "글 $i 시작 $(date '+%T')" >> "$OUT/22d_기록.txt"
  빌드/글/재기_7B.exe "$G7" 빌드/글/qwen2Q8_7b.ptx "$IN" "$OUT/22d_글_$i.txt" >> "$OUT/22d_기록.txt" 2>&1
  echo "글 $i 끝 $(date '+%T') 종료 $?" >> "$OUT/22d_기록.txt"
  echo "라마 $i 시작 $(date '+%T')" >> "$OUT/22d_기록.txt"
  # llama.cpp 는 한글 경로를 열지 못한다 — 모델 폴더에서 파일 이름(ASCII)으로
  ( cd "$R/모델/qwen2.5-7b-instruct-gguf" && "$LB" -m qwen2.5-7b-instruct-q8_0.gguf -p 2048,8192 -n 0 -o md > "$OUT/22d_라마_프롬프트_$i.txt" 2>/dev/null
    "$LB" -m qwen2.5-7b-instruct-q8_0.gguf -p 0 -n 128 -d 0,2048,8192 -o md > "$OUT/22d_라마_생성_$i.txt" 2>/dev/null )
  echo "라마 $i 끝 $(date '+%T') 종료 $?" >> "$OUT/22d_기록.txt"
done
echo "커널마다 시작 $(date '+%T')" >> "$OUT/22d_기록.txt"
빌드/글/재기_7B커널.exe "$G7" 빌드/글/qwen2Q8_7b.ptx "$IN" "$OUT/22d_글_커널마다.txt" >> "$OUT/22d_기록.txt" 2>&1
echo "끝 $(date '+%F %T')" >> "$OUT/22d_기록.txt"
