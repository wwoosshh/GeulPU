#!/bin/bash
# 30단계 공식 실행 — 고정한 코드(커밋)와 그 빌드로. 결과는 문서/결과/30단계/ 에(로그 등 큰 파일은 작업 폴더에).
#   bash 공식실행/공식30.sh <저장소> <작업폴더 — ASCII 경로(llama-server 가 열 모델의 하드 링크를 둔다)>
# 차례: 30단계 빌드 → 29단계 빌드(5d4d5b6 — 작업 폴더의 git worktree. 재기 도구 재기_프롬프트30 은 30단계의 것을 넣어 같은 셈으로)
# → 30a 판 · 다섯 길 · 18d → 30b 서버(28a · 28c) → 30c · 30d 29 대 30 을 세 번 번갈아 → 30e 첫 토큰(29 서버 대 30 서버 세 번)
# → 기록(llama.cpp 최신 공식 릴리스 b11567 — llama-bench pp · llama-server 첫 토큰, 형식마다 커널 시간) → 모음.
set -u
R="$1"
W="$2"
OUT="$R/문서/결과/30단계"
M7="$R/모델/qwen2.5-7b-instruct-gguf"
M14="$R/모델/qwen2.5-14b-instruct-gguf"
G05="$R/모델/qwen2.5-0.5b-instruct-gguf/qwen2.5-0.5b-instruct-q8_0.gguf"
GL="$R/../geul-lang-v2"
GC="$GL/build/self_컴파일러.exe"
PX="$GL/build/자체PTX.exe"
LL="$R/도구/llama-b11567"
LB="$LL/llama-bench.exe"
LS="$LL/llama-server.exe"
B29="$W/빌드29"
FILES=(q8_0 q4_0 q4_k_m q5_k_m q6_k)
MODS=(qwen2Q8 qwen2Q8_7b qwen2Q4_7b qwen2Q4_5120x40x8x13824x152064 qwen2K_3584x28x4x18944x152064 qwen2K_5120x40x8x13824x152064)
GP=8093
LP=8094
cd "$R"
mkdir -p "$OUT" 빌드/글 "$W" "$B29"
L="$OUT/30_기록.txt"
echo "시작 $(date '+%F %T') · 커밋 $(git rev-parse --short HEAD) · 바뀐 파일 $(git status --short | grep -v '^??' | wc -l) · 글 저장소 $(git -C "$GL" rev-parse --short HEAD) (바뀐 파일 $(git -C "$GL" status --short | grep -v '^??' | wc -l))" > "$L"
nvidia-smi --query-gpu=name,driver_version,clocks.max.sm,clocks.max.mem,memory.total --format=csv >> "$L"
"$LB" --version >> "$L" 2>&1
sha256sum "$GC" "$PX" "$LL/llama-bench.exe" "$LL/llama-server.exe" "$LL/ggml-cuda.dll" | sed "s#$GL/#../geul-lang-v2/#; s#$R/#./#" >> "$L"

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
modgen() {   # 생성기 폴더 모듈
  case "$3" in
    qwen2Q8) "$1" qwen2Q8 "$2/qwen2Q8.gl" ;;
    qwen2Q8_7b) "$1" qwen2Q8_7b "$2/qwen2Q8_7b.gl" ;;
    qwen2Q4_7b) "$1" qwen2Q4_7b "$2/qwen2Q4_7b.gl" ;;
    qwen2Q4_5120x40x8x13824x152064) "$1" qwen2큰 Q4_0 5120 40 8 13824 152064 "$2/$3.gl" ;;
    qwen2K_3584x28x4x18944x152064) "$1" qwen2큰 K 3584 28 4 18944 152064 "$2/$3.gl" ;;
    qwen2K_5120x40x8x13824x152064) "$1" qwen2큰 K 5120 40 8 13824 152064 "$2/$3.gl" ;;
  esac
}
ready() { for i in $(seq 1 600); do curl -s -m 2 "http://127.0.0.1:$1/health" 2>/dev/null | grep -q ok && return 0; sleep 1; done; return 1; }
stop_all() { taskkill //IM 서버.exe //F > /dev/null 2>&1; taskkill //IM llama-server.exe //F > /dev/null 2>&1; sleep 3; }

# ---- 30단계 빌드 ----
echo "빌드 시작 $(date '+%T')" >> "$L"
GEUL_ROOT="$GL" "$GC" 커널/커널생성.gl -o 빌드/글/커널생성.exe >> "$L" 2>&1
for t in 서버 실행기 시험_7B 시험_엔진 재기_7B 재기_프롬프트30 재기_커널30; do
  GEUL_ROOT="$GL" "$GC" "호스트/$t.gl" -o "빌드/글/$t.exe" >> "$L" 2>&1
  echo "빌드 $t 종료 $?" >> "$L"
done
for m in "${MODS[@]}"; do
  modgen 빌드/글/커널생성.exe 빌드/글 "$m" >> "$L" 2>&1
  "$PX" "빌드/글/$m.gl" -o "빌드/글/$m.ptx" > "$W/ptx_$m.log" 2>&1
  hg=$(sha256sum "빌드/글/$m.gl" | cut -c1-64)
  hp=$(sha256sum "빌드/글/$m.ptx" | cut -c1-64)
  if grep -q "^$m | .* | $hg | $hp$" 시험/모듈해시.txt; then s=같다; else s=다르다; fi
  echo "모듈 $m — PTX 종료 · 시험/모듈해시.txt 와 $s" >> "$L"
done
sha256sum 빌드/글/*.exe >> "$L"

# ---- 29단계 빌드(5d4d5b6) — 같은 컴파일러 · PTX 뒷단, 재기_프롬프트30 은 30단계의 것(엔진의 API 는 29단계와 같다) ----
rm -rf "$W/wt29"
git worktree prune
git worktree add --detach "$W/wt29" 5d4d5b6 >> "$L" 2>&1
cp 호스트/재기_프롬프트30.gl "$W/wt29/호스트/"
( cd "$W/wt29" && GEUL_ROOT="$GL" "$GC" 커널/커널생성.gl -o "$B29/커널생성.exe" ) >> "$L" 2>&1
for t in 서버 재기_7B 재기_프롬프트30; do
  ( cd "$W/wt29" && GEUL_ROOT="$GL" "$GC" "호스트/$t.gl" -o "$B29/$t.exe" ) >> "$L" 2>&1
  echo "29 빌드 $t 종료 $?" >> "$L"
done
git show 5d4d5b6:시험/모듈해시.txt > "$W/모듈해시29.txt"
for m in qwen2Q8_7b qwen2Q4_7b qwen2K_3584x28x4x18944x152064; do
  ( cd "$W/wt29" && modgen "$B29/커널생성.exe" "$B29" "$m" ) >> "$L" 2>&1
  "$PX" "$B29/$m.gl" -o "$B29/$m.ptx" > "$W/ptx29_$m.log" 2>&1
  hg=$(sha256sum "$B29/$m.gl" | cut -c1-64)
  hp=$(sha256sum "$B29/$m.ptx" | cut -c1-64)
  if grep -q "^$m | .* | $hg | $hp$" "$W/모듈해시29.txt"; then s=같다; else s=다르다; fi
  echo "29 빌드 모듈 $m — 29단계의 모듈해시와 $s" >> "$L"
done
echo "빌드 끝 $(date '+%T')" >> "$L"

# ---- 입력 ----
python -I -X utf8 시험/입력7B.py "$M7/qwen2.5-7b-instruct-q8_0.gguf" "$W/공식입력7B.bin" >> "$L" 2>&1
python -I -X utf8 시험/입력7B.py "$M7/qwen2.5-7b-instruct-q8_0.gguf" "$W/공식재기입력7B.bin" --재기 >> "$L" 2>&1
python -I -X utf8 공식실행/입력18d.py "$R" "$W/18d입력.bin" >> "$L" 2>&1
sha256sum "$W/공식입력7B.bin" "$W/공식재기입력7B.bin" "$W/18d입력.bin" | sed "s#$W/#<작업폴더>/#" >> "$L"

# ---- 30a (1) 판 ----
echo "30a(1) 시작 $(date '+%T')" >> "$L"
python -I -X utf8 시험/판23.py 빌드/글/qwen2Q4_7b.ptx "$(gguf q4_0)" "$OUT/30a_판_Q4_0.json" > "$W/30a_판_Q4_0.log" 2>&1
echo "30a(1) Q4_0 종료 $? — $(tail -1 "$W/30a_판_Q4_0.log")" >> "$L"
python -I -X utf8 시험/판23.py 빌드/글/qwen2Q8_7b.ptx "$(gguf q8_0)" "$OUT/30a_판_Q8_0.json" > "$W/30a_판_Q8_0.log" 2>&1
echo "30a(1) Q8_0 종료 $? — $(tail -1 "$W/30a_판_Q8_0.log")" >> "$L"
python -I -X utf8 시험/판26.py "$(ptx 빌드/글 q4_k_m)" "$(gguf q4_k_m)" "$(gguf q5_k_m)" "$(gguf q6_k)" "$OUT/30a_판_K.json" > "$W/30a_판_K.log" 2>&1
echo "30a(1) K 종료 $? — $(tail -1 "$W/30a_판_K.log")" >> "$L"

# ---- 30a (2) 다섯 길 요약이 앞 단계와 바이트까지 · (3) 0.5B 18d ----
run_same() {   # 이름 GGUF PTX 견줄요약
  local n="$1" G="$2" P="$3" REF="$4"
  rm -rf "$W/공식30_$n"
  mkdir -p "$W/공식30_$n"
  빌드/글/시험_7B.exe "$G" "$P" "$W/공식입력7B.bin" "$W/공식30_$n" > "$W/30a_$n.log" 2>&1
  local r=$?
  local s=다름
  cmp -s "$W/공식30_$n/요약.txt" "$REF" && s=같음
  echo "30a(2) $n 종료 $r — $(tail -1 "$W/30a_$n.log") · 견줄 요약과 $s" >> "$L"
  cp "$W/30a_$n.log" "$OUT/30a_기록_$n.txt"
}
run_same q8_0 "$(gguf q8_0)" "$(ptx 빌드/글 q8_0)" 문서/결과/23단계/23b_요약_Q8.txt
run_same q4_0 "$(gguf q4_0)" "$(ptx 빌드/글 q4_0)" 문서/결과/23단계/23b_요약_Q4.txt
run_same 14b-q4_0 "$M14/qwen2.5-14b-instruct-q4_0-pure.gguf" 빌드/글/qwen2Q4_5120x40x8x13824x152064.ptx 문서/결과/24단계/24c_요약_14b-q4_0.txt
for f in q4_k_m q5_k_m q6_k; do
  run_same "$f" "$(gguf $f)" "$(ptx 빌드/글 $f)" "문서/결과/26단계/26b_요약_$f.txt"
done
빌드/글/시험_엔진.exe "$G05" 빌드/글/qwen2Q8.ptx "$W/18d입력.bin" "$OUT/30_0.5B_18d출력.txt" > "$W/18d.log" 2>&1
if cmp -s "$OUT/30_0.5B_18d출력.txt" 문서/결과/18단계/18d_엔진_글.txt; then echo "30a(3) 0.5B 18d — 18d 기록과 바이트까지 같다" >> "$L"; else echo "30a(3) 0.5B 18d — 18d 기록과 다르다" >> "$L"; fi

# ---- 30b 서버 — 28a(7B Q4_0, 슬롯 4 · 문맥 4096) · 28c, 28단계의 28a 기록과 견주기 ----
echo "30b 시작 $(date '+%T')" >> "$L"
stop_all
python -I -X utf8 시험/서버28.py 빌드/글/서버.exe "$(gguf q4_0)" "$W/a30" --슬롯 4 --문맥 4096 --포트 $GP --일 a --시험7B 빌드/글/시험_7B.exe --ptx 빌드/글/qwen2Q4_7b.ptx \
  --출력 "$OUT/30b_28a.json" > "$W/30b_28a.log" 2>&1
echo "30b 28a 종료 $? — $(grep -E '^28a' "$W/30b_28a.log" | tr '\n' ' ')" >> "$L"
cp "$W/30b_28a.log" "$OUT/30b_28a_기록.txt"
python -I -X utf8 시험/서버28.py 빌드/글/서버.exe "$(gguf q4_0)" "$W/c30" --포트 $GP --일 c --출력 "$OUT/30b_28c.json" > "$W/30b_28c.log" 2>&1
echo "30b 28c 종료 $? — $(tail -1 "$W/30b_28c.log")" >> "$L"
cp "$W/30b_28c.log" "$OUT/30b_28c_기록.txt"
python -I -X utf8 - 문서/결과/28단계/28a_q4_0.json "$OUT/30b_28a.json" "$OUT/30b_견줌.json" >> "$L" 2>&1 <<'PYEOF'
import json, sys
옛 = json.load(open(sys.argv[1], encoding="utf-8"))["28a"]["차례"]
새 = json.load(open(sys.argv[2], encoding="utf-8"))["28a"]["차례"]
기준 = {이름: v[0] for 이름, v in 옛["가"].items()}
견준 = 다름 = 0
for 차례, 묶음 in 새.items():
    for 이름, 목록 in 묶음.items():
        for x in 목록:
            견준 += 1
            if 이름 not in 기준 or x["tokens"] != 기준[이름]["tokens"] or x["hashes"] != 기준[이름]["hashes"]:
                다름 += 1
                print(f"  다름: {이름} ({차례})")
없음 = sorted(set(기준) - set(새.get("가", {})))
결과 = {"견준": 견준, "다름": 다름, "요청": len(기준), "새 실행에 없는 요청": 없음, "통과": 다름 == 0 and 견준 > 0 and not 없음}
json.dump(결과, open(sys.argv[3], "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(f"30b 28단계 28a 기록과: 요청 {len(기준)} · 견준 {견준} · 다름 {다름} · 없는 요청 {len(없음)}")
PYEOF

# ---- 30c 프롬프트 · 30d 생성 — 29 대 30 을 세 번(홀수 번은 29 먼저, 짝수 번은 30 먼저) ----
for i in 1 2 3; do
  for f in "${FILES[@]}"; do
    if [ $((i % 2)) -eq 1 ]; then ORD="29 30"; else ORD="30 29"; fi
    for b in $ORD; do
      if [ "$b" = 29 ]; then D="$B29"; else D=빌드/글; fi
      echo "30c $b $f $i 시작 $(date '+%T')" >> "$L"
      "$D/재기_프롬프트30.exe" "$(gguf $f)" "$(ptx "$D" $f)" "$W/공식재기입력7B.bin" "$OUT/30c_${b}_${f}_$i.txt" > "$W/30c_${b}_${f}_$i.log" 2>&1
      echo "30c $b $f $i 끝 $(date '+%T') 종료 $?" >> "$L"
      "$D/재기_7B.exe" "$(gguf $f)" "$(ptx "$D" $f)" "$W/공식재기입력7B.bin" "$OUT/30d_${b}_${f}_$i.txt" > "$W/30d_${b}_${f}_$i.log" 2>&1
      echo "30d $b $f $i 끝 $(date '+%T') 종료 $?" >> "$L"
    done
  done
done

# ---- 30e 첫 토큰 — 29 서버 대 30 서버(7B Q4_0, 슬롯 4 · 문맥 4096), 막는 소켓의 클라이언트, 세 번 ----
echo "30e 시작 $(date '+%T')" >> "$L"
for i in 1 2 3; do
  if [ $((i % 2)) -eq 1 ]; then ORD="29 30"; else ORD="30 29"; fi
  for b in $ORD; do
    if [ "$b" = 29 ]; then D="$B29"; else D=빌드/글; fi
    stop_all
    "$D/서버.exe" "$(gguf q4_0)" --ptx "$(ptx "$D" q4_0)" --포트 $GP --슬롯 4 --문맥 4096 > "$W/서버_30e_${b}_$i.log" 2>&1 &
    ready $GP || echo "서버가 뜨지 않음 ($b $i)" >> "$L"
    python -I -X utf8 재기/서버재기28.py --주소 127.0.0.1:$GP --첫토큰 --막기 --되풀이 5 --출력 "$OUT/30e_${b}_$i.json" >> "$L" 2>&1
    echo "30e $b $i 종료 $?" >> "$L"
  done
done
stop_all

# ---- 기록: llama.cpp(최신 공식 릴리스 b11567) — 프롬프트(같은 GGUF) · 서버의 첫 토큰(막는 클라이언트) ----
for f in "${FILES[@]}"; do
  ( cd "$M7" && "$LB" -m "$(basename "$(gguf $f)")" -p 32,128,512,1024,2048,4096,8192 -n 0 -o md > "$OUT/30기록_라마_${f}_프롬프트.txt" 2>/dev/null )
  echo "기록 라마 프롬프트 $f 종료 $?" >> "$L"
done
WW="$(cygpath -w "$W")"
[ -f "$W/q4_0.gguf" ] || powershell -NoProfile -Command "New-Item -ItemType HardLink -Path '$WW\\q4_0.gguf' -Target '$(cygpath -w "$(gguf q4_0)")' | Out-Null"
stop_all
( cd "$W" && "$LS" -m q4_0.gguf -ngl 99 -np 4 -c 16384 --host 127.0.0.1 --port $LP > "$W/라마서버_30e.log" 2>&1 & )
ready $LP || echo "llama-server 가 뜨지 않음" >> "$L"
python -I -X utf8 재기/서버재기28.py --주소 127.0.0.1:$LP --첫토큰 --막기 --되풀이 5 --출력 "$OUT/30기록_첫토큰_라마.json" >> "$L" 2>&1
echo "기록 라마 첫 토큰 종료 $?" >> "$L"
stop_all

# ---- 기록: 형식마다 커널 시간(30단계 빌드) ----
for f in "${FILES[@]}"; do
  빌드/글/재기_커널30.exe "$(gguf $f)" "$(ptx 빌드/글 $f)" "$W/공식재기입력7B.bin" "$OUT/30기록_글_커널마다_$f.txt" > "$W/30기록_커널_$f.log" 2>&1
  echo "기록 커널마다 $f 종료 $?" >> "$L"
done

# ---- 모음 ----
python -I -X utf8 재기/모음30.py "$OUT" "$OUT/30cde_요약.json" >> "$L" 2>&1
git worktree remove --force "$W/wt29" >> "$L" 2>&1
echo "끝 $(date '+%F %T')" >> "$L"
