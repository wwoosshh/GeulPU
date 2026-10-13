"""31단계 확인 — 비정규수 버림 규칙 R 을 CUDA 커널에 적용하면 R1 32 문제의 출력이 바뀌는가.
   1) q8_7b.ptx 의 짧은실수 연산에 .ftz 를 붙인 사본(q8_7b_ftz.ptx)을 만든다(원본은 그대로).
   2) 기준을 만들 때와 같은 방식(32 개를 한꺼번에, 슬롯 8, 문맥 3584, 최대 3200)으로 돌려 로짓 해시를 ref_lh/expected.json 과 견준다.
   python -I ftz_r1.py <출력 폴더>"""
import hashlib
import http.client
import json
import os
import re
import subprocess
import sys
import threading
import time

P = os.path.dirname(os.path.abspath(__file__))
OUT = sys.argv[1]
GS = os.path.join(P, "server_r1.exe")
MODEL = os.path.join(P, "r1.gguf")
SRC = os.path.join(P, "q8_7b.ptx")
PTX = os.path.join(P, "q8_7b_ftz.ptx")
PORT = 18093
SLOTS = 8
CTX = 3584
MAXTOK = 3200

# 비정규수가 들어오거나 나올 수 있는 짧은실수 연산만. cvt.f32.f16(반실수 읽기 — 늘 정규수) · cvt.rn.f32.s64(정수 → 실수) · 옮기기는 그대로.
RULES = [
    (re.compile(r"\b(fma|mul|sub|add|div|sqrt)\.rn\.f32\b"), r"\1.rn.ftz.f32"),
    (re.compile(r"\b(max|min|neg|abs)\.f32\b"), r"\1.ftz.f32"),
    (re.compile(r"\bcvt\.rni\.s32\.f32\b"), "cvt.rni.ftz.s32.f32"),
    (re.compile(r"\bsetp\.(eq|ne|lt|le|gt|ge|equ|neu|ltu|leu|gtu|geu|num|nan)(\.and|\.or|\.xor)?\.f32\b"), r"setp.\1\2.ftz.f32"),
]


def make_ptx():
    src = open(SRC, encoding="ascii").read()
    out_lines, counts = [], {}
    for line in src.split("\n"):
        code, sep, comment = line.partition("//")
        for rx, rep in RULES:
            code, n = rx.subn(rep, code)
            if n:
                counts[rx.pattern] = counts.get(rx.pattern, 0) + n
        out_lines.append(code + sep + comment)
    dst = "\n".join(out_lines)
    open(PTX, "w", encoding="ascii", newline="").write(dst)
    left = sorted(set(re.findall(r"^\s+([a-z][a-z0-9_.]*\.f32[a-z0-9_.]*)", dst, re.M)))
    return counts, left, hashlib.sha256(src.encode()).hexdigest(), hashlib.sha256(dst.encode()).hexdigest()


def req(path, body=None, method="POST"):
    c = http.client.HTTPConnection("127.0.0.1", PORT, timeout=None)
    c.request(method, path, body=json.dumps(body).encode("utf-8") if body is not None else None,
              headers={"Content-Type": "application/json"})
    r = c.getresponse()
    raw = r.read()
    c.close()
    return r.status, raw


def main():
    os.makedirs(OUT, exist_ok=True)
    counts, left, h_src, h_dst = make_ptx()
    print("바꾼 수:", json.dumps(counts, ensure_ascii=False))
    print("남은 .f32 명령 형태:", left)
    print(f"원본 PTX {h_src[:16]} → .ftz 사본 {h_dst[:16]}", flush=True)
    ref = json.load(open(os.path.join(P, "ref_lh", "expected.json"), encoding="utf-8"))
    reqs = json.load(open(os.path.join(P, "ref_lh", "requests.json"), encoding="utf-8"))
    log = open(os.path.join(OUT, "server.log"), "wb")
    proc = subprocess.Popen([GS, MODEL, "--ptx", PTX, "--슬롯", str(SLOTS), "--문맥", str(CTX), "--포트", str(PORT)],
                            stdout=log, stderr=subprocess.STDOUT)
    t0 = time.time()
    while True:
        if proc.poll() is not None:
            raise RuntimeError("서버가 끝났다 — server.log 를 보라")
        try:
            if req("/health", None, "GET")[0] == 200:
                break
        except OSError:
            time.sleep(1)
    print(f"준비 {time.time() - t0:.1f} s", flush=True)
    res = {}

    def one(r):
        st, raw = req("/v1/completions", {"prompt": r["prompt_tokens"], "max_tokens": MAXTOK, "temperature": 0, "cache_prompt": False,
                                          "geulpu": {"logit_hash": True}})
        res[r["id"]] = (st, json.loads(raw))

    t1 = time.time()
    ths = [threading.Thread(target=one, args=(r,)) for r in reqs]
    for t in ths:
        t.start()
    for t in ths:
        t.join()
    print(f"생성 {time.time() - t1:.0f} s", flush=True)
    proc.terminate()
    proc.wait(30)
    want = {it["id"]: it for it in ref["items"]}
    rows, steps, same_steps, same_items = [], 0, 0, 0
    for r in reqs:
        st, d = res[r["id"]]
        assert st == 200, d
        g = d["geulpu"]
        w = want[r["id"]]
        text = d["choices"][0]["text"]
        n = min(len(g["logit_hashes"]), len(w["logit_hashes"]))
        first = next((i for i in range(n) if g["logit_hashes"][i] != w["logit_hashes"][i]), None)
        ok = g["tokens"] == w["tokens"] and g["logit_hashes"] == w["logit_hashes"] and \
            hashlib.sha256(text.encode("utf-8")).hexdigest() == w["text_sha256"]
        same_items += ok
        steps += len(w["logit_hashes"])
        same_steps += sum(a == b for a, b in zip(g["logit_hashes"], w["logit_hashes"]))
        rows.append({"id": r["id"], "걸음": len(g["logit_hashes"]), "기준걸음": len(w["logit_hashes"]), "같음": ok, "처음다른걸음": first})
    summary = {"원본PTX_sha256": h_src, "ftzPTX_sha256": h_dst, "바꾼수": counts, "남은f32형태": left,
               "문제": len(reqs), "모두같은문제": same_items, "기준걸음": steps, "같은로짓해시": same_steps, "문제별": rows}
    json.dump(summary, open(os.path.join(OUT, "ftz_대조.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"모두 같은 문제 {same_items}/{len(reqs)} · 로짓 해시 같은 걸음 {same_steps}/{steps}")
    for row in rows:
        if not row["같음"]:
            print("  다름:", row)


if __name__ == "__main__":
    main()
