#!/bin/bash
# 22a · 22b 공식 실행 — 고정한 코드(커밋 d98c6dd)와 그 빌드로. 결과는 문서/결과/22단계/ 에(큰 로짓 파일은 작업 폴더에).
#   bash 공식22ab.sh <저장소> <작업폴더>
set -u
R="$1"
W="$2"
OUT="$R/문서/결과/22단계"
G7="$R/모델/qwen2.5-7b-instruct-gguf/qwen2.5-7b-instruct-q8_0.gguf"
G05="$R/모델/qwen2.5-0.5b-instruct-gguf/qwen2.5-0.5b-instruct-q8_0.gguf"
cd "$R"
L="$OUT/22ab_기록.txt"
echo "시작 $(date '+%F %T') · 커밋 $(git rev-parse --short HEAD)" > "$L"
sha256sum 빌드/글/qwen2Q8.gl 빌드/글/qwen2Q8.ptx 빌드/글/qwen2Q8_7b.gl 빌드/글/qwen2Q8_7b.ptx 빌드/글/실행기.exe 빌드/글/시험_7B.exe >> "$L"
echo "22a(1) 머리 128 커널 시작 $(date '+%T')" >> "$L"
python -I -X utf8 시험/머리128.py 빌드/글/qwen2Q8_7b.ptx "$G7" "$OUT/22a_머리128커널.json" > "$W/22a_머리128.log" 2>&1
echo "22a(1) 머리 128 커널 끝 $(date '+%T') 종료 $? — $(tail -1 "$W/22a_머리128.log")" >> "$L"
echo "22a(1) 줄 판 시작 $(date '+%T')" >> "$L"
python -I -X utf8 시험/줄128.py 빌드/글/qwen2Q8_7b.ptx "$G7" "$OUT/22a_줄판.json" > "$W/22a_줄판.log" 2>&1
echo "22a(1) 줄 판 끝 $(date '+%T') 종료 $? — $(tail -1 "$W/22a_줄판.log")" >> "$L"
echo "22b 길 시작 $(date '+%T')" >> "$L"
python -I -X utf8 시험/입력7B.py "$G7" "$W/공식입력7B.bin" >> "$L" 2>&1
mkdir -p "$W/공식7B"
빌드/글/시험_7B.exe "$G7" 빌드/글/qwen2Q8_7b.ptx "$W/공식입력7B.bin" "$W/공식7B" > "$W/22b.log" 2>&1
echo "22b 길 끝 $(date '+%T') 종료 $? — $(tail -1 "$W/22b.log")" >> "$L"
cp "$W/공식7B/요약.txt" "$OUT/22b_요약.txt"
cp "$W/22b.log" "$OUT/22b_기록.txt"
echo "22a(2) 끝에서 끝 시작 $(date '+%T')" >> "$L"
python -I -X utf8 시험/참조7B.py "$G7" "$W/공식7B" "$OUT/22a_끝에서끝.json" > "$W/22a_끝에서끝.log" 2>&1
echo "22a(2) 끝에서 끝 끝 $(date '+%T') 종료 $? — $(tail -1 "$W/22a_끝에서끝.log")" >> "$L"
echo "0.5B 회귀(18d) 시작 $(date '+%T')" >> "$L"
python -I -X utf8 "$W/입력18d.py" "$R" "$W/18d입력.bin" >> "$L" 2>&1
빌드/글/시험_엔진.exe "$G05" 빌드/글/qwen2Q8.ptx "$W/18d입력.bin" "$OUT/22_0.5B_18d출력.txt" > "$W/18d.log" 2>&1
if cmp -s "$OUT/22_0.5B_18d출력.txt" 문서/결과/18단계/18d_엔진_글.txt; then 회귀="18d 기록과 바이트까지 같다"; else 회귀="18d 기록과 다르다"; fi
echo "0.5B 회귀(18d) 끝 $(date '+%T') — $회귀" >> "$L"
echo "끝 $(date '+%F %T')" >> "$L"
