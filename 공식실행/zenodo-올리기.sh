#!/bin/bash
# Zenodo 초안(draft)에 파일을 명령줄로 올린다 — 브라우저 업로드가 끊길 때 쓴다. Git Bash · WSL 어디서나 된다(curl 필요).
#
#   ZENODO_TOKEN=<개인 토큰> bash 공식실행/zenodo-올리기.sh <기록 번호> <파일 폴더> [파일…]
#
# 기록 번호: 초안 주소 zenodo.org/uploads/<번호> 의 번호(예약한 DOI 10.5281/zenodo.<번호> 와 같다).
# 토큰: zenodo.org → 계정 → Applications → Personal access tokens → New token, 범위(scope) deposit:write.
# 파일을 적지 않으면 폴더의 geulpu-s40-*.zip · MANIFEST.sha256 · SHA256SUMS · README.md 를 올린다.
# 같은 이름이 이미 있으면 덮어쓴다. 실패한 파일은 3 번까지 다시 시도한다. 토큰은 환경 변수로만 받는다.
set -uo pipefail
: "${ZENODO_TOKEN:?ZENODO_TOKEN 환경 변수에 토큰을 넣어라}"
REC="${1:?기록 번호}"
DIR="${2:?파일 폴더}"
shift 2
API="https://zenodo.org/api"
AUTH="Authorization: Bearer $ZENODO_TOKEN"
PY="$(command -v python3 || command -v python)"

# 옛 deposit API 의 bucket 주소 — 새 화면에서 만든 초안에도 쓸 수 있다.
BUCKET="$(curl -sS -H "$AUTH" "$API/deposit/depositions/$REC" | "$PY" -c 'import sys, json; d = json.load(sys.stdin); print(d["links"]["bucket"])')" || {
  echo "초안 정보를 못 읽었다 — 번호 · 토큰 범위(deposit:write)를 확인" >&2; exit 1; }
echo "bucket: $BUCKET"

if [ $# -eq 0 ]; then
  set -- "$DIR"/geulpu-s40-*.zip "$DIR/MANIFEST.sha256" "$DIR/SHA256SUMS" "$DIR/README.md"
else
  set -- "${@/#/$DIR/}"
fi

fail=0
for f in "$@"; do
  name="$(basename "$f")"
  ok=0
  for try in 1 2 3; do
    echo "== $name ($(du -h "$f" | cut -f1)) — 시도 $try"
    if curl --fail --progress-bar -H "$AUTH" --upload-file "$f" "$BUCKET/$name" -o /dev/null; then
      ok=1; break
    fi
    sleep 5
  done
  if [ $ok = 1 ]; then echo "올림: $name"; else echo "실패: $name" >&2; fail=1; fi
done

echo "== Zenodo 에 있는 파일(이름 · 크기 · md5):"
curl -sS -H "$AUTH" "$API/deposit/depositions/$REC/files" | "$PY" -c '
import sys, json
for f in json.load(sys.stdin):
    print(f"{f[\"filename\"]}  {f[\"filesize\"]}  {f[\"checksum\"]}")'
echo "로컬 MD5SUMS 와 견주면 된다: md5sum -c MD5SUMS 는 로컬 확인, 위 목록은 Zenodo 쪽 값."
exit $fail
