#!/bin/bash
# 29단계 공식 실행 — 리눅스: 같은 GPU, 같은 비트. 몫이 둘이고 윈도 몫이 먼저다(입력을 만든다). 결과는 문서/결과/29단계/ 에.
#   윈도(Git Bash):  bash 공식실행/공식29.sh 윈도 <저장소> <작업폴더>
#   리눅스(WSL):     bash 공식실행/공식29.sh 리눅스 <저장소> <작업폴더>     — 같은 저장소 · 같은 작업폴더를 /mnt/c/… 로
# 윈도 몫(29e): 빌드 → 빠른점검 → 입력 → 다섯 길 요약 여섯 · 18d → 서버 28a(7B Q4_0) · 28c → 기록(재기_7B · 서버 걸음)
# 리눅스 몫(29a ~ 29d): 글 컴파일러(참조 구현 → 고정점) · PTX 뒷단 → 빌드 · 가져오기 → 빠른점검(모듈 해시) → 다섯 길 요약 여섯 · 18d
#   → 서버 28a(7B Q4_0) · 28c → 윈도의 28a 기록과 견주기 → 기록(재기_7B · 서버 걸음 · 올림 시간)
set -u
P="$1"
R="$2"
W="$3"
OUT="$R/문서/결과/29단계"
M7="$R/모델/qwen2.5-7b-instruct-gguf"
M14="$R/모델/qwen2.5-14b-instruct-gguf"
G05="$R/모델/qwen2.5-0.5b-instruct-gguf/qwen2.5-0.5b-instruct-q8_0.gguf"
GL="$R/../geul-lang-v2"
Q8="$M7/qwen2.5-7b-instruct-q8_0.gguf"
Q4="$M7/qwen2.5-7b-instruct-q4_0-pure.gguf"
QK="$M7/qwen2.5-7b-instruct-q4_k_m-req.gguf"
Q5="$M7/qwen2.5-7b-instruct-q5_k_m-req.gguf"
Q6="$M7/qwen2.5-7b-instruct-q6_k-req.gguf"
Q14="$M14/qwen2.5-14b-instruct-q4_0-pure.gguf"
GP=8094
if [ "$P" = 윈도 ]; then
  X=.exe
  PY=python
  B=빌드/글
elif [ "$P" = 리눅스 ]; then
  X=
  PY=python3
  B=빌드/글리눅스
else
  echo "몫은 윈도 또는 리눅스: $P"
  exit 3
fi
GC="$GL/build/self_컴파일러$X"
PX="$GL/build/자체PTX$X"
cd "$R"
mkdir -p "$OUT" "$W" "$B"
L="$OUT/29_기록_$P.txt"
echo "시작 $(date '+%F %T') · $P · 커밋 $(git rev-parse --short HEAD) · 바뀐 파일 $(git status --short | grep -v '^??' | wc -l) · 글 저장소 $(git -C "$GL" rev-parse --short HEAD) (바뀐 파일 $(git -C "$GL" status --short | grep -v '^??' | wc -l))" > "$L"
uname -a >> "$L"
nvidia-smi --query-gpu=name,driver_version,clocks.max.sm,clocks.max.mem,memory.total --format=csv >> "$L"

MODS=(qwen2Q8 qwen2Q8_7b qwen2Q4_7b qwen2Q4_5120x40x8x13824x152064 qwen2K_3584x28x4x18944x152064)
gen() {   # 생성기 출력폴더 모듈
  case "$3" in
    qwen2Q8) "$1" qwen2Q8 "$2/qwen2Q8.gl" ;;
    qwen2Q8_7b) "$1" qwen2Q8_7b "$2/qwen2Q8_7b.gl" ;;
    qwen2Q4_7b) "$1" qwen2Q4_7b "$2/qwen2Q4_7b.gl" ;;
    qwen2Q4_5120x40x8x13824x152064) "$1" qwen2큰 Q4_0 5120 40 8 13824 152064 "$2/$3.gl" ;;
    qwen2K_3584x28x4x18944x152064) "$1" qwen2큰 K 3584 28 4 18944 152064 "$2/$3.gl" ;;
  esac
}
stop_srv() {
  if [ "$P" = 윈도 ]; then taskkill //IM 서버.exe //F > /dev/null 2>&1; else pkill -x 서버 > /dev/null 2>&1; fi
  sleep 3
}
ready() { for i in $(seq 1 600); do curl -s -m 2 "http://127.0.0.1:$1/health" 2>/dev/null | grep -q ok && return 0; sleep 1; done; return 1; }

# ---- 29a 글 컴파일러 · PTX 뒷단 (리눅스 몫: 참조 구현에서 — 윈도 몫은 있는 것의 해시만) ----
if [ "$P" = 리눅스 ]; then
  echo "29a 글 컴파일러 시작 $(date '+%T')" >> "$L"
  ( cd "$GL" && python3 build.py selfhost 컴파일러 ) > "$W/29a_selfhost.log" 2>&1
  echo "29a selfhost 컴파일러 종료 $? — $(grep -E '바이트 비교|DT_NEEDED|고정점|명령줄' "$W/29a_selfhost.log" | tr '\n' ' ')" >> "$L"
  grep -v '^  PASS' "$W/29a_selfhost.log" > "$OUT/29a_selfhost_리눅스.txt"
  ( cd "$GL" && GEUL_ROOT=. build/self_컴파일러 research/gpu/자체PTX/PTX.gl -o build/자체PTX ) >> "$L" 2>&1
  echo "29a PTX 뒷단 종료 $?" >> "$L"
fi
sha256sum "$GC" "$PX" | sed "s#$GL/#../geul-lang-v2/#" >> "$L"

# ---- 빌드 ----
echo "빌드 시작 $(date '+%T')" >> "$L"
GEUL_ROOT="$GL" "$GC" 커널/커널생성.gl -o "$B/커널생성$X" >> "$L" 2>&1
echo "빌드 커널생성 종료 $?" >> "$L"
for t in 서버 실행기 시험_7B 시험_엔진 재기_7B; do
  GEUL_ROOT="$GL" "$GC" "호스트/$t.gl" -o "$B/$t$X" >> "$L" 2>&1
  echo "빌드 $t 종료 $?" >> "$L"
done
for m in "${MODS[@]}"; do
  gen "$B/커널생성$X" "$B" "$m" >> "$L" 2>&1
  "$PX" "$B/$m.gl" -o "$B/$m.ptx" > "$W/ptx_${P}_$m.log" 2>&1
  echo "PTX $m 종료 $?" >> "$L"
done
( cd "$B" && sha256sum qwen2*.gl qwen2*.ptx 커널생성$X 서버$X 실행기$X 시험_7B$X 시험_엔진$X 재기_7B$X ) >> "$L"
for t in 실행기 서버; do
  echo "가져오기 $t: $($PY -I -X utf8 시험/가져오기표.py "$B/$t$X" | tr '\n' ' ')" >> "$L"
done

# ---- 29b 빠른점검 (모듈 해시 — 리눅스는 계약 자체 시험(numpy)을 빼고: 윈도 몫이 돌린다) ----
CHK=""
[ "$P" = 리눅스 ] && CHK="--계약없이"
$PY -X utf8 시험/빠른점검.py --글 "$GL" --출력 "$W/점검_$P" $CHK > "$W/29b_빠른점검_$P.log" 2>&1
echo "29b 빠른점검 종료 $? — $(tail -1 "$W/29b_빠른점검_$P.log")" >> "$L"
grep -v '^    넘침' "$W/29b_빠른점검_$P.log" > "$OUT/29b_빠른점검_$P.txt"

# ---- 입력 (윈도 몫 — numpy 가 드는 파이썬. 리눅스 몫은 같은 파일을 읽는다) ----
if [ "$P" = 윈도 ]; then
  python -I -X utf8 시험/입력7B.py "$Q8" "$W/공식입력7B.bin" >> "$L" 2>&1
  python -I -X utf8 시험/입력7B.py "$Q8" "$W/공식재기입력7B.bin" --재기 >> "$L" 2>&1
  python -I -X utf8 공식실행/입력18d.py "$R" "$W/18d입력.bin" >> "$L" 2>&1
fi
sha256sum "$W/공식입력7B.bin" "$W/공식재기입력7B.bin" "$W/18d입력.bin" | sed "s#$W/#<작업폴더>/#" >> "$L"

# ---- 29c 같은 비트 — 다섯 길 요약 여섯 · 0.5B 18d ----
echo "29c 시작 $(date '+%T')" >> "$L"
run_same() {   # 이름 GGUF PTX 견줄요약
  local n="$1" G="$2" PT="$3" REF="$4"
  rm -rf "$W/${P}_$n"
  mkdir -p "$W/${P}_$n"
  "$B/시험_7B$X" "$G" "$PT" "$W/공식입력7B.bin" "$W/${P}_$n" > "$W/29c_${P}_$n.log" 2>&1
  local r=$?
  local s=다름
  cmp -s "$W/${P}_$n/요약.txt" "$REF" && s=같음
  echo "29c($P) $n 종료 $r — $(tail -1 "$W/29c_${P}_$n.log") · 기록($REF)과 $s" >> "$L"
  cp "$W/29c_${P}_$n.log" "$OUT/29c_${P}_$n.txt"
}
run_same q8_0 "$Q8" "$B/qwen2Q8_7b.ptx" 문서/결과/23단계/23b_요약_Q8.txt
run_same q4_0 "$Q4" "$B/qwen2Q4_7b.ptx" 문서/결과/23단계/23b_요약_Q4.txt
run_same 14b-q4_0 "$Q14" "$B/qwen2Q4_5120x40x8x13824x152064.ptx" 문서/결과/24단계/24c_요약_14b-q4_0.txt
run_same q4_k_m "$QK" "$B/qwen2K_3584x28x4x18944x152064.ptx" 문서/결과/26단계/26b_요약_q4_k_m.txt
run_same q5_k_m "$Q5" "$B/qwen2K_3584x28x4x18944x152064.ptx" 문서/결과/26단계/26b_요약_q5_k_m.txt
run_same q6_k "$Q6" "$B/qwen2K_3584x28x4x18944x152064.ptx" 문서/결과/26단계/26b_요약_q6_k.txt
"$B/시험_엔진$X" "$G05" "$B/qwen2Q8.ptx" "$W/18d입력.bin" "$OUT/29c_${P}_0.5B_18d출력.txt" > "$W/18d_$P.log" 2>&1
if cmp -s "$OUT/29c_${P}_0.5B_18d출력.txt" 문서/결과/18단계/18d_엔진_글.txt; then
  echo "29c($P) 0.5B 18d — 18d 기록과 바이트까지 같다" >> "$L"
else
  echo "29c($P) 0.5B 18d — 18d 기록과 다르다" >> "$L"
fi

# ---- 29d 서버 — 28a(7B Q4_0, 슬롯 4 · 문맥 4096) · 28c, 윈도의 28a 기록과 견주기 ----
echo "29d 시작 $(date '+%T')" >> "$L"
stop_srv
$PY -I -X utf8 시험/서버28.py "$B/서버$X" "$Q4" "$W/a_$P" --슬롯 4 --문맥 4096 --포트 $GP --일 a --시험7B "$B/시험_7B$X" --ptx "$B/qwen2Q4_7b.ptx" \
  --출력 "$OUT/29d_28a_$P.json" > "$W/29d_28a_$P.log" 2>&1
echo "29d($P) 28a 종료 $? — $(grep -E '^28a' "$W/29d_28a_$P.log" | tr '\n' ' ')" >> "$L"
cp "$W/29d_28a_$P.log" "$OUT/29d_28a_기록_$P.txt"
$PY -I -X utf8 시험/서버28.py "$B/서버$X" "$Q4" "$W/c_$P" --포트 $GP --일 c --출력 "$OUT/29d_28c_$P.json" > "$W/29d_28c_$P.log" 2>&1
echo "29d($P) 28c 종료 $? — $(tail -1 "$W/29d_28c_$P.log")" >> "$L"
cp "$W/29d_28c_$P.log" "$OUT/29d_28c_기록_$P.txt"
$PY -I -X utf8 - 문서/결과/28단계/28a_q4_0.json "$OUT/29d_28a_$P.json" "$OUT/29d_견줌_$P.json" >> "$L" 2>&1 <<'PYEOF'
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
print(f"29d 윈도 28a 기록(28단계)과: 요청 {len(기준)} · 견준 {견준} · 다름 {다름} · 없는 요청 {len(없음)}")
PYEOF

# ---- 기록 (판정 아님): 재기_7B · 서버 걸음 · 올림 시간 ----
echo "기록 시작 $(date '+%T')" >> "$L"
stop_srv
"$B/재기_7B$X" "$Q4" "$B/qwen2Q4_7b.ptx" "$W/공식재기입력7B.bin" "$OUT/29기록_재기_${P}_q4_0.txt" > "$W/29기록_재기_$P.log" 2>&1
echo "기록 재기_7B 종료 $? — $(grep '생성 채팅' "$OUT/29기록_재기_${P}_q4_0.txt" | head -1)" >> "$L"
"$B/서버$X" "$Q4" --포트 $GP --슬롯 4 --문맥 4096 > "$W/서버_기록_$P.log" 2>&1 &
ready $GP || echo "서버가 뜨지 않음" >> "$L"
echo "올림: $(grep -o '올림 [0-9.]* 초' "$W/서버_기록_$P.log")" >> "$L"
$PY -I -X utf8 재기/서버재기28.py --주소 127.0.0.1:$GP --동시 1,4 --생성 256 --되풀이 3 --출력 "$OUT/29기록_서버_$P.json" >> "$L" 2>&1
echo "기록 서버 걸음 종료 $?" >> "$L"
$PY -I -X utf8 재기/서버재기28.py --주소 127.0.0.1:$GP --첫토큰 --되풀이 3 --출력 "$OUT/29기록_첫토큰_$P.json" >> "$L" 2>&1
stop_srv
echo "끝 $(date '+%F %T')" >> "$L"
