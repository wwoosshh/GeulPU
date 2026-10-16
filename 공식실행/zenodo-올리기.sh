#!/bin/bash
# Zenodo 초안(draft)에 파일을 명령줄로 올린다 — 브라우저 업로드가 끊길 때 쓴다. Git Bash · WSL 어디서나 된다(curl · python 필요).
#
#   export ZENODO_TOKEN=<개인 토큰>          # read -s -p "token: " ZENODO_TOKEN; echo; export ZENODO_TOKEN  (기록에 남지 않게)
#   bash 공식실행/zenodo-올리기.sh <기록 번호> <파일 폴더> [파일…]
#
# 기록 번호: 초안 주소 zenodo.org/uploads/<번호> 의 번호(예약한 DOI 10.5281/zenodo.<번호> 와 같다).
# 토큰: zenodo.org → 계정 → Applications → Personal access tokens → New token, 범위(scope) deposit:write.
# 파일을 적지 않으면 폴더의 geulpu-s40-*.zip · MANIFEST.sha256 · SHA256SUMS · README.md 를 올린다.
# 이미 Zenodo 에 같은 이름 · 크기 · md5 로 있는 파일은 건너뛴다. 변수 이름은 ASCII(Git Bash 는 한글 변수 이름을 못 받는다). 끊기면(502 등) 8 번까지 점점 길게 기다리며 다시 시도한다(10 초 → 2 분).
# 길: 옛 deposit API(bucket 에 PUT)를 먼저 쓰고, 그 길이 막혀 있으면(404 · 410) 새 records API(files 등록 → content PUT → commit)로.
set -uo pipefail
: "${ZENODO_TOKEN:?ZENODO_TOKEN 환경 변수에 토큰을 넣어라}"
REC="${1:?기록 번호}"
DIR="${2:?파일 폴더}"
shift 2
API="https://zenodo.org/api"
AUTH="Authorization: Bearer $ZENODO_TOKEN"
TRIES=8

# 돌아가는 파이썬 — Windows 의 python3 는 스토어 안내 껍데기일 수 있다
PY=""
for p in python python3; do
  if "$p" -c "import json" >/dev/null 2>&1; then PY="$p"; break; fi
done
[ -n "$PY" ] || { echo "python 이 없다" >&2; exit 1; }
TMP="$(mktemp)"
trap 'rm -f "$TMP"' EXIT

json() { "$PY" -c "import sys, json; d = json.load(open(sys.argv[1], encoding='utf-8')); $1" "$TMP" "${@:2}"; }
md5() { "$PY" -c "import sys, hashlib; h = hashlib.md5(); f = open(sys.argv[1], 'rb')
for b in iter(lambda: f.read(1 << 24), b''): h.update(b)
print(h.hexdigest())" "$1"; }

# ── 초안 정보 ──
code="$(curl -sS -o "$TMP" -w '%{http_code}' -H "$AUTH" "$API/deposit/depositions/$REC")"
LEGACY=0; BUCKET=""; FILES=""
if [ "$code" = "200" ]; then
  BUCKET="$(json 'print(d["links"]["bucket"])')" && LEGACY=1
  echo "옛 deposit API — bucket: $BUCKET"
elif [ "$code" = "401" ] || [ "$code" = "403" ]; then
  echo "HTTP $code — 토큰이 틀렸거나 범위(deposit:write)가 모자란다: $(head -c 300 "$TMP")" >&2; exit 1
else
  echo "옛 deposit API 는 HTTP $code — 새 records API 로 간다"
  code="$(curl -sS -o "$TMP" -w '%{http_code}' -H "$AUTH" "$API/records/$REC/draft")"
  [ "$code" = "200" ] || { echo "초안 정보를 못 읽었다 — HTTP $code: $(head -c 300 "$TMP")" >&2; exit 1; }
  FILES="$(json 'print(d["links"]["files"])')"
  echo "새 records API — files: $FILES"
fi

# Zenodo 에 있는 파일 목록 → "이름 크기 md5" 줄들
목록() {
  if [ $LEGACY = 1 ]; then
    curl -sS -o "$TMP" -H "$AUTH" "$API/deposit/depositions/$REC/files" && \
      json 'print("\n".join("%s %d %s" % (x["filename"], int(x["filesize"]), x["checksum"].replace("md5:", "")) for x in d))'
  else
    curl -sS -o "$TMP" -H "$AUTH" "$FILES" && \
      json 'print("\n".join("%s %s %s" % (x["key"], int(x["size"]) if x.get("size") is not None else "?", str(x.get("checksum", "")).replace("md5:", "")) for x in d["entries"]))'
  fi
}

if [ $# -eq 0 ]; then
  set -- "$DIR"/geulpu-s40-*.zip "$DIR/MANIFEST.sha256" "$DIR/SHA256SUMS" "$DIR/README.md"
else
  set -- "${@/#/$DIR/}"
fi

올리기_옛() {  # 파일 → bucket/이름 (덮어씀)
  curl --fail --progress-bar -H "$AUTH" --upload-file "$1" "$BUCKET/$2" -o /dev/null
}

올리기_새() {  # 이름 등록(있으면 지우고) → content PUT → commit
  local f="$1" name="$2" enc
  enc="$("$PY" -c "import sys, urllib.parse; print(urllib.parse.quote(sys.argv[1]))" "$name")"
  curl -sS -o /dev/null -X DELETE -H "$AUTH" "$FILES/$enc" || true
  curl -sS -o "$TMP" -w '%{http_code}' -X POST -H "$AUTH" -H "Content-Type: application/json" \
       -d "[{\"key\": \"$name\"}]" "$FILES" | grep -qE '^20[01]$' || { echo "등록 실패: $(head -c 300 "$TMP")" >&2; return 1; }
  curl --fail --progress-bar -H "$AUTH" -H "Content-Type: application/octet-stream" \
       --upload-file "$f" "$FILES/$enc/content" -o /dev/null || return 1
  curl --fail -sS -o /dev/null -X POST -H "$AUTH" "$FILES/$enc/commit"
}

fail=0
HAVE="$(목록 | tr -d '\r')"
for f in "$@"; do
  name="$(basename "$f")"
  size="$(stat -c %s "$f" 2>/dev/null || wc -c < "$f")"
  sum="$(md5 "$f")"
  if grep -qF "$name $size $sum" <<<"$HAVE"; then
    echo "건너뜀(이미 같음): $name"
    continue
  fi
  ok=0
  wait=10
  for try in $(seq 1 $TRIES); do
    echo "== $name ($(du -h "$f" | cut -f1)) — 시도 $try/$TRIES"
    if { [ $LEGACY = 1 ] && 올리기_옛 "$f" "$name"; } || { [ $LEGACY = 0 ] && 올리기_새 "$f" "$name"; }; then
      ok=1; break
    fi
    echo "   끊김 — $wait 초 뒤 다시"
    sleep "$wait"
    wait=$(( wait * 2 > 120 ? 120 : wait * 2 ))
  done
  if [ $ok = 1 ]; then echo "올림: $name"; else echo "실패: $name" >&2; fail=1; fi
done

echo "== Zenodo 에 있는 파일(이름 · 크기 · md5):"
목록
echo "docs/paper/data/zenodo.md 의 md5 표와 견주면 된다."
exit $fail
