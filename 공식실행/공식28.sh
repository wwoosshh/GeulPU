#!/bin/bash
# 28단계 공식 실행 — 고정한 코드(커밋)와 그 빌드로. 결과는 문서/결과/28단계/ 에(로짓 등 큰 파일은 작업 폴더에).
#   bash 공식실행/공식28.sh <저장소> <작업폴더 — ASCII 경로(llama-server 가 열 모델의 하드 링크를 둔다)>
# 차례: 28단계 빌드 → 27단계 빌드(b54a732 — 작업 폴더의 git worktree) → 28e(1) 모듈의 앞부분 → 입력 → 28e(2) 다섯 길 요약 · 18d
# → 28d 속도(엔진 재기_7B, 글 서버 슬롯 4 · 8, llama-server 슬롯 4 · 8 — 같은 하네스) → 기록(첫 토큰 · 다른 모델의 처리량)
# → 28a 네 모델 → 28c → 28b (2) 분포 · (3) 기록 · (1) 대조 · 뽑기 시간(끝에 — CPU 를 많이 써서) → 모음.
set -u
R="$1"
W="$2"
OUT="$R/문서/결과/28단계"
M7="$R/모델/qwen2.5-7b-instruct-gguf"
M14="$R/모델/qwen2.5-14b-instruct-gguf"
G05="$R/모델/qwen2.5-0.5b-instruct-gguf/qwen2.5-0.5b-instruct-q8_0.gguf"
GL="$R/../geul-lang-v2"
GC="$GL/build/self_컴파일러.exe"
PX="$GL/build/자체PTX.exe"
LS="$R/도구/llama-b11496/llama-server.exe"
B27="$W/build27"
GP=8094
LP=8095
cd "$R"
mkdir -p "$OUT" 빌드/글 "$W" "$B27"
L="$OUT/28_기록.txt"
echo "시작 $(date '+%F %T') · 커밋 $(git rev-parse --short HEAD) · 바뀐 파일 $(git status --short | grep -v '^??' | wc -l) · 글 저장소 $(git -C "$GL" rev-parse --short HEAD) (바뀐 파일 $(git -C "$GL" status --short | grep -v '^??' | wc -l))" > "$L"
nvidia-smi --query-gpu=name,driver_version,clocks.max.sm,clocks.max.mem,memory.total --format=csv >> "$L"

Q8="$M7/qwen2.5-7b-instruct-q8_0.gguf"
Q4="$M7/qwen2.5-7b-instruct-q4_0-pure.gguf"
QK="$M7/qwen2.5-7b-instruct-q4_k_m-req.gguf"
Q14="$M14/qwen2.5-14b-instruct-q4_0-pure.gguf"
MODS=(qwen2Q8 qwen2Q8_7b qwen2Q4_7b qwen2Q4_5120x40x8x13824x152064 qwen2K_3584x28x4x18944x152064 qwen2K_5120x40x8x13824x152064)
gen() {   # 생성기 출력폴더 모듈
  case "$3" in
    qwen2Q8) "$1" qwen2Q8 "$2/qwen2Q8.gl" ;;
    qwen2Q8_7b) "$1" qwen2Q8_7b "$2/qwen2Q8_7b.gl" ;;
    qwen2Q4_7b) "$1" qwen2Q4_7b "$2/qwen2Q4_7b.gl" ;;
    qwen2Q4_5120x40x8x13824x152064) "$1" qwen2큰 Q4_0 5120 40 8 13824 152064 "$2/$3.gl" ;;
    qwen2K_3584x28x4x18944x152064) "$1" qwen2큰 K 3584 28 4 18944 152064 "$2/$3.gl" ;;
    qwen2K_5120x40x8x13824x152064) "$1" qwen2큰 K 5120 40 8 13824 152064 "$2/$3.gl" ;;
  esac
}

# ---- 28단계 빌드 ----
echo "빌드 시작 $(date '+%T')" >> "$L"
GEUL_ROOT="$GL" "$GC" 커널/커널생성.gl -o 빌드/글/커널생성.exe >> "$L" 2>&1
for t in 서버 실행기 시험_7B 시험_엔진 시험_표 시험_뽑기 재기_7B; do
  GEUL_ROOT="$GL" "$GC" "호스트/$t.gl" -o "빌드/글/$t.exe" >> "$L" 2>&1
  echo "빌드 $t 종료 $?" >> "$L"
done
for m in "${MODS[@]}"; do
  gen 빌드/글/커널생성.exe 빌드/글 "$m" >> "$L" 2>&1
  "$PX" "빌드/글/$m.gl" -o "빌드/글/$m.ptx" > "$W/ptx_$m.log" 2>&1
  echo "PTX $m 종료 $?" >> "$L"
done
sha256sum 빌드/글/qwen2*.gl 빌드/글/qwen2*.ptx 빌드/글/*.exe "$PX" >> "$L"

# ---- 27단계 빌드(b54a732) — 같은 PTX 뒷단으로 ----
rm -rf "$W/wt27"
git worktree prune
git worktree add --detach "$W/wt27" b54a732 >> "$L" 2>&1
( cd "$W/wt27" && GEUL_ROOT="$GL" "$GC" 커널/커널생성.gl -o "$B27/커널생성.exe" ) >> "$L" 2>&1
for m in "${MODS[@]}"; do
  gen "$B27/커널생성.exe" "$B27" "$m" >> "$L" 2>&1
  "$PX" "$B27/$m.gl" -o "$B27/$m.ptx" > "$W/ptx27_$m.log" 2>&1
done
# 28e (1) — 27단계 모듈(소스 · PTX)이 28단계 모듈의 앞부분과 바이트까지 같은가(0.5B 는 통째로)
python -I -X utf8 - "$B27" 빌드/글 "$OUT/28e_모듈.json" "${MODS[@]}" >> "$L" 2>&1 <<'PYEOF'
import json, sys
옛, 새, 출력 = sys.argv[1:4]
결과 = {}
for m in sys.argv[4:]:
    for e in ("gl", "ptx"):
        a = open(f"{옛}/{m}.{e}", "rb").read()
        b = open(f"{새}/{m}.{e}", "rb").read()
        if m == "qwen2Q8":
            맞음 = a == b
        else:
            맞음 = b.startswith(a) and len(b) > len(a)
        결과[f"{m}.{e}"] = {"27": len(a), "28": len(b), "같음": 맞음}
        print(f"28e(1) {m}.{e}: 27단계 {len(a)} 바이트 · 28단계 {len(b)} 바이트 · {'앞부분이 같다' if 맞음 else '다르다'}")
결과["통과"] = all(v["같음"] for v in 결과.values())
json.dump(결과, open(출력, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
PYEOF
echo "빌드 끝 $(date '+%T')" >> "$L"

# ---- 입력 ----
python -I -X utf8 시험/입력7B.py "$Q8" "$W/공식입력7B.bin" >> "$L" 2>&1
python -I -X utf8 시험/입력7B.py "$Q8" "$W/공식재기입력7B.bin" --재기 >> "$L" 2>&1
python -I -X utf8 공식실행/입력18d.py "$R" "$W/18d입력.bin" >> "$L" 2>&1

# ---- 28e (2) 그대로 — 다섯 길 요약이 앞 단계와 바이트까지 ----
run_same() {   # 이름 GGUF PTX 견줄요약
  local n="$1" G="$2" P="$3" REF="$4"
  rm -rf "$W/공식28_$n"
  mkdir -p "$W/공식28_$n"
  빌드/글/시험_7B.exe "$G" "$P" "$W/공식입력7B.bin" "$W/공식28_$n" > "$W/28e_$n.log" 2>&1
  local r=$?
  local s=다름
  cmp -s "$W/공식28_$n/요약.txt" "$REF" && s=같음
  echo "28e(2) $n 종료 $r — $(tail -1 "$W/28e_$n.log") · 견줄 요약과 $s" >> "$L"
  cp "$W/28e_$n.log" "$OUT/28e_기록_$n.txt"
}
run_same q8_0 "$Q8" 빌드/글/qwen2Q8_7b.ptx 문서/결과/23단계/23b_요약_Q8.txt
run_same q4_0 "$Q4" 빌드/글/qwen2Q4_7b.ptx 문서/결과/23단계/23b_요약_Q4.txt
run_same 14b-q4_0 "$Q14" 빌드/글/qwen2Q4_5120x40x8x13824x152064.ptx 문서/결과/24단계/24c_요약_14b-q4_0.txt
run_same q4_k_m "$QK" 빌드/글/qwen2K_3584x28x4x18944x152064.ptx 문서/결과/26단계/26b_요약_q4_k_m.txt
빌드/글/시험_엔진.exe "$G05" 빌드/글/qwen2Q8.ptx "$W/18d입력.bin" "$OUT/28_0.5B_18d출력.txt" > "$W/18d.log" 2>&1
if cmp -s "$OUT/28_0.5B_18d출력.txt" 문서/결과/18단계/18d_엔진_글.txt; then echo "28e(2) 0.5B 18d — 18d 기록과 바이트까지 같다" >> "$L"; else echo "28e(2) 0.5B 18d — 18d 기록과 다르다" >> "$L"; fi

# ---- 서버 띄우기 · 끄기 ----
WW="$(cygpath -w "$W")"
link() {   # GGUF 이름 → 작업 폴더의 ASCII 하드 링크(llama-server 는 한글 경로를 열지 못한다)
  [ -f "$W/$2" ] || powershell -NoProfile -Command "New-Item -ItemType HardLink -Path '$WW\\$2' -Target '$(cygpath -w "$1")' | Out-Null"
}
ready() { for i in $(seq 1 600); do curl -s -m 2 "http://127.0.0.1:$1/health" 2>/dev/null | grep -q ok && return 0; sleep 1; done; return 1; }
stop_all() { taskkill //IM 서버.exe //F > /dev/null 2>&1; taskkill //IM llama-server.exe //F > /dev/null 2>&1; sleep 3; }
glsrv() {   # GGUF PTX 슬롯 문맥 로그
  stop_all
  빌드/글/서버.exe "$1" --ptx "$2" --포트 $GP --슬롯 "$3" --문맥 "$4" > "$5" 2>&1 &
  ready $GP || echo "글 서버가 뜨지 않음 ($1)" >> "$L"
}
lmsrv() {   # 하드링크이름 슬롯 전체문맥 로그
  stop_all
  ( cd "$W" && "$LS" -m "$1" -ngl 99 -np "$2" -c "$3" --host 127.0.0.1 --port $LP > "$4" 2>&1 & )
  ready $LP || echo "llama-server 가 뜨지 않음 ($1)" >> "$L"
}
measure() {   # 포트 동시 출력
  python -I -X utf8 재기/서버재기28.py --주소 127.0.0.1:$1 --동시 "$2" --생성 256 --되풀이 3 --출력 "$3" >> "$L" 2>&1
  echo "재기 $3 종료 $?" >> "$L"
}
link "$Q4" q4_0.gguf
link "$Q8" q8_0.gguf
link "$QK" q4_k_m.gguf
link "$Q14" q14_q4_0.gguf

# ---- 28d 속도 (7B Q4_0) ----
echo "28d 시작 $(date '+%T')" >> "$L"
stop_all
빌드/글/재기_7B.exe "$Q4" 빌드/글/qwen2Q4_7b.ptx "$W/공식재기입력7B.bin" "$OUT/28d_엔진_q4_0.txt" > "$W/28d_엔진.log" 2>&1
echo "28d 엔진 종료 $? — $(grep '생성 채팅' "$OUT/28d_엔진_q4_0.txt")" >> "$L"
glsrv "$Q4" 빌드/글/qwen2Q4_7b.ptx 4 4096 "$W/서버_28d_4.log"
measure $GP 1,2,4 "$OUT/28d_글_슬롯4.json"
python -I -X utf8 재기/서버재기28.py --주소 127.0.0.1:$GP --첫토큰 --되풀이 3 --출력 "$OUT/28기록_첫토큰_글.json" >> "$L" 2>&1
lmsrv q4_0.gguf 4 16384 "$W/라마_28d_4.log"
measure $LP 1,2,4 "$OUT/28d_라마_슬롯4.json"
python -I -X utf8 재기/서버재기28.py --주소 127.0.0.1:$LP --첫토큰 --되풀이 3 --출력 "$OUT/28기록_첫토큰_라마.json" >> "$L" 2>&1
glsrv "$Q4" 빌드/글/qwen2Q4_7b.ptx 8 4096 "$W/서버_28d_8.log"
measure $GP 1,2,4,8 "$OUT/28d_글_슬롯8.json"
lmsrv q4_0.gguf 8 32768 "$W/라마_28d_8.log"
measure $LP 1,2,4,8 "$OUT/28d_라마_슬롯8.json"
# ---- 기록: 다른 모델의 처리량 (글 · llama-server) ----
glsrv "$Q8" 빌드/글/qwen2Q8_7b.ptx 4 4096 "$W/서버_기록_q8.log"
measure $GP 1,2,4 "$OUT/28기록_처리량_글_q8_0.json"
lmsrv q8_0.gguf 4 16384 "$W/라마_기록_q8.log"
measure $LP 1,2,4 "$OUT/28기록_처리량_라마_q8_0.json"
glsrv "$QK" 빌드/글/qwen2K_3584x28x4x18944x152064.ptx 4 4096 "$W/서버_기록_k.log"
measure $GP 1,2,4 "$OUT/28기록_처리량_글_q4_k_m.json"
lmsrv q4_k_m.gguf 4 16384 "$W/라마_기록_k.log"
measure $LP 1,2,4 "$OUT/28기록_처리량_라마_q4_k_m.json"
glsrv "$Q14" 빌드/글/qwen2Q4_5120x40x8x13824x152064.ptx 2 2048 "$W/서버_기록_14.log"
measure $GP 1,2 "$OUT/28기록_처리량_글_14b-q4_0.json"
lmsrv q14_q4_0.gguf 2 4096 "$W/라마_기록_14.log"
measure $LP 1,2 "$OUT/28기록_처리량_라마_14b-q4_0.json"
stop_all
echo "28d 끝 $(date '+%T')" >> "$L"

# ---- 28a 네 모델 ----
run_a() {   # 이름 GGUF PTX 슬롯 문맥
  echo "28a $1 시작 $(date '+%T')" >> "$L"
  python -I -X utf8 시험/서버28.py 빌드/글/서버.exe "$2" "$W/a_$1" --슬롯 "$4" --문맥 "$5" --포트 $GP --일 a --시험7B 빌드/글/시험_7B.exe --ptx "$3" \
    --출력 "$OUT/28a_$1.json" > "$W/28a_$1.log" 2>&1
  echo "28a $1 끝 $(date '+%T') 종료 $? — $(grep -E '^28a' "$W/28a_$1.log" | tr '\n' ' ')" >> "$L"
  cp "$W/28a_$1.log" "$OUT/28a_기록_$1.txt"
}
run_a q4_0 "$Q4" 빌드/글/qwen2Q4_7b.ptx 4 4096
run_a q8_0 "$Q8" 빌드/글/qwen2Q8_7b.ptx 4 4096
run_a q4_k_m "$QK" 빌드/글/qwen2K_3584x28x4x18944x152064.ptx 4 4096
run_a 14b-q4_0 "$Q14" 빌드/글/qwen2Q4_5120x40x8x13824x152064.ptx 2 2048

# ---- 28c ----
python -I -X utf8 시험/서버28.py 빌드/글/서버.exe "$Q4" "$W/c" --포트 $GP --일 c --출력 "$OUT/28c.json" > "$W/28c.log" 2>&1
echo "28c 종료 $? — $(tail -1 "$W/28c.log")" >> "$L"
cp "$W/28c.log" "$OUT/28c_기록.txt"
stop_all

# ---- 28b ----
python -I -X utf8 시험/뽑기.py 분포 빌드/글/시험_뽑기.exe --횟수 1000000 --출력 "$OUT/28b_분포.json" > "$W/28b_분포.log" 2>&1
echo "28b(2) 종료 $? — $(tr '\n' ' ' < "$W/28b_분포.log")" >> "$L"
python -I -X utf8 시험/뽑기.py 기록 --결과 "$OUT/28a_q4_0.json" "$OUT/28a_q8_0.json" "$OUT/28a_q4_k_m.json" "$OUT/28a_14b-q4_0.json" \
  --출력 "$OUT/28b_기록.json" > "$W/28b_기록.log" 2>&1
echo "28b(3) 종료 $? — $(tail -1 "$W/28b_기록.log")" >> "$L"
REALS=()
for n in q4_0 q8_0 q4_k_m 14b-q4_0; do
  for x in S1 S2 S3 S4 S5 R1 R2; do REALS+=("$W/a_$n/기록28/rec_${x}_로짓.bin"); done
done
python -I -X utf8 시험/뽑기.py 대조 빌드/글/시험_뽑기.exe --합성 1000 --실제 "${REALS[@]}" --실제행 1000 --출력 "$OUT/28b_대조.json" > "$W/28b_대조.log" 2>&1
echo "28b(1) 종료 $? — $(tail -1 "$W/28b_대조.log")" >> "$L"
python -I -X utf8 시험/뽑기.py 시간 빌드/글/시험_뽑기.exe --실제 "$W/a_q4_0/기록28/rec_S1_로짓.bin" "$W/a_q4_0/기록28/rec_S3_로짓.bin" > "$OUT/28기록_뽑기시간.txt" 2>&1

# ---- 모음 ----
python -I -X utf8 재기/모음28.py "$OUT" "$OUT/28d_요약.json" >> "$L" 2>&1
git worktree remove --force "$W/wt27" >> "$L" 2>&1
echo "끝 $(date '+%F %T')" >> "$L"
