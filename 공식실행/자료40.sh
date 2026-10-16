#!/bin/bash
# 40단계 원자료를 Zenodo 에 올릴 묶음(zip)으로 싼다. 로그(logs/ · *.log — 기계의 경로가 든다)와 dl/ 는 뺀다.
#   bash 공식실행/자료40.sh <작업 폴더> <낼 폴더>
# zip · sha256sum 이 있어야 한다(WSL Ubuntu 에서 돌린다). 결과: 낼 폴더에 zip 다섯 · MANIFEST.sha256 · SHA256SUMS.
set -euo pipefail
W="${1:?작업 폴더}"
OUT="${2:?낼 폴더}"
mkdir -p "$OUT"
OUT="$(cd "$OUT" && pwd)"
cd "$W"

pack() {  # pack <이름> <경로…>
  local name="$1"; shift
  rm -f "$OUT/$name.zip"
  zip -q -9 -r "$OUT/$name.zip" "$@"
  echo "$(date '+%T') $name.zip  $(du -h "$OUT/$name.zip" | cut -f1)"
}

pack geulpu-s40-generation-qwen2.5-7b \
  생성/G_7b.jsonl 생성/L_7b.jsonl 생성/V_7b.jsonl 생성/V점수_7b.jsonl 생성/L1확인_7b.jsonl \
  생성/갈래_7b.jsonl 생성/오염첫_7b.jsonl 생성/오염둘_7b.jsonl \
  생성/재현G_7b.jsonl 생성/재현V_7b.jsonl 생성/재현갈래_7b.jsonl
pack geulpu-s40-generation-r1-distill-7b \
  생성/G_r1.jsonl 생성/L_r1.jsonl 생성/V_r1.jsonl 생성/V점수_r1.jsonl
pack geulpu-s40-follower 따라
pack geulpu-s40-steps-tokens 위험 토큰 토큰_옛_BOS없음
pack geulpu-s40-engine-build build

# 안에 든 모든 파일의 해시(작업 폴더 기준 상대 경로)와 묶음 자체의 해시
find 생성 따라 위험 토큰 토큰_옛_BOS없음 build -type f | LC_ALL=C sort \
  | xargs -d '\n' sha256sum > "$OUT/MANIFEST.sha256"
cd "$OUT"
sha256sum geulpu-s40-*.zip MANIFEST.sha256 > SHA256SUMS
echo "$(date '+%T') 끝 — $(wc -l < MANIFEST.sha256) 파일, zip $(ls geulpu-s40-*.zip | wc -l) 개"
ls -la "$OUT"
