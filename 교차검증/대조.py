"""친구 PC 의 교차 검증 결과(result-….zip 또는 그 폴더)를 이 PC 의 기준과 대조한다 — 친구 쪽 요약을 믿지 않고 응답 파일에서 다시 잰다.
   python -X utf8 -I 대조.py <result zip 또는 폴더> [기준 폴더(기본: 이 파일이 있는 교차검증 폴더)]
   zip 은 옆에 같은 이름의 폴더로 푼다. 대조결과.md 를 결과 폴더에 쓴다. 걸음마다의 로짓 해시는
   결과/기준-RTX4070Ti-20261013/로짓해시.json(기준 PC 가 같은 조건 — 슬롯 8, 32 개를 한꺼번에 — 으로 낸 것)과 견준다."""
import json
import os
import re
import sys
import zipfile

P = os.path.dirname(os.path.abspath(__file__))
REF = P
BUILD_NAMES = {"글 컴파일러": "self_compiler", "PTX 뒷단": "ptx_backend", "서버 (R1)": "server_r1", "커널 생성기": "generator",
               "7B 모듈 소스": "module_source", "7B 모듈 PTX": "module_ptx"}


def load(path):
    return json.load(open(path, encoding="utf-8-sig"))


def boxed(text):
    if not text:
        return None
    i = text.rfind("\\boxed{")
    if i < 0:
        return None
    j, d = i + 7, 1
    while j < len(text) and d:
        d += {"{": 1, "}": -1}.get(text[j], 0)
        j += 1
    s = re.sub(r"\\[,!; ]|\\text\{[^}]*\}|[\s$,]", "", text[i + 7:j - 1])
    m = re.search(r"-?\d+", s)
    return int(m.group()) if m else None


def open_result(src):
    if os.path.isdir(src):
        return src
    dest = os.path.splitext(os.path.abspath(src))[0]
    os.makedirs(dest, exist_ok=True)
    root = os.path.realpath(dest)
    with zipfile.ZipFile(src) as z:
        for m in z.infolist():
            t = os.path.realpath(os.path.join(dest, m.filename))
            if not (t == root or t.startswith(root + os.sep)):
                raise SystemExit("zip 안의 경로가 이상하다: " + m.filename)
        z.extractall(dest)
    return dest


def main():
    d = open_result(sys.argv[1])
    ref = sys.argv[2] if len(sys.argv) > 2 else REF
    exp = load(os.path.join(ref, "expected.json"))
    reqs = {r["id"]: r for r in load(os.path.join(ref, "requests.json"))}
    env = load(os.path.join(d, "environment.json")) if os.path.exists(os.path.join(d, "environment.json")) else {}
    summ = load(os.path.join(d, "summary.json")) if os.path.exists(os.path.join(d, "summary.json")) else {}
    out = []

    def w(s=""):
        print(s)
        out.append(s)

    w("# 교차 검증 대조")
    w()
    w("## 친구 PC 의 환경")
    for g in env.get("gpus") or []:
        w(f"- GPU {g.get('index')}: {g.get('name')} · compute {g.get('compute_cap')} · VRAM {g.get('memory.total')} MiB · 드라이버 "
          f"{g.get('driver_version')} ({g.get('driver_model.current')}) · VBIOS {g.get('vbios_version')} · PCIe "
          f"{g.get('pcie.link.gen.max')}x{g.get('pcie.link.width.max')}")
    o = env.get("os") or {}
    cpu = env.get("cpu") or {}
    w(f"- CUDA {env.get('cuda_driver_version')} · nvcuda.dll {env.get('nvcuda_dll')}")
    w(f"- {o.get('caption')} {o.get('display_version')} (빌드 {o.get('build')}) · {cpu.get('name')} · RAM {env.get('ram_gb')} GB")
    w(f"- 하드웨어 가속 GPU 일정 {env.get('hardware_gpu_scheduling')} · 전원 계획 {env.get('power_plan')} · GeulPU 커밋 "
      f"{(env.get('geulpu_commit') or '')[:12]} · 글 커밋 {(env.get('geul_commit') or '')[:12]}")
    ref_env = exp.get("reference", {})
    w(f"- 기준 PC: {ref_env.get('gpu')} · 드라이버 {ref_env.get('driver')}")
    bad = [c for c in env.get("checks") or [] if c.get("state") in ("경고", "실패")]
    if bad:
        w("- 경고 · 실패:")
        for c in bad:
            w(f"  - [{c.get('state')}] {c.get('name')}: {c.get('detail')}")
    w()

    w("## 빌드 (기준 PC 의 해시와)")
    build = summ.get("build") or env.get("build") or {}
    want = exp.get("build", {})
    build_ok = True
    if not build:
        w("- 빌드 기록 없음")
        build_ok = False
    for name, key in BUILD_NAMES.items():
        if name in build:
            same = build[name] == want.get(key)
            build_ok &= same
            w(f"- {name}: {'같음' if same else '다름'} ({build[name][:12]})")
        elif build:
            w(f"- {name}: 기록 없음")
            build_ok = False
    w()

    w("## 출력 (응답 파일에서 다시 잼)")
    run = summ.get("run") or {}
    w(f"- 슬롯 {run.get('slots')} · 생성 {run.get('generate_minutes')} 분")
    lhf = os.path.join(ref, "결과", "기준-RTX4070Ti-20261013", "로짓해시.json")   # 기준 PC 의 걸음마다 로짓 해시(같은 조건으로 낸 것)
    lhref = {it["id"]: it for it in load(lhf)["items"]} if os.path.exists(lhf) else {}
    same_n = ans_same = acc_f = acc_r = steps_ok = lh_same = 0
    steps_total = 0
    lh_diffs = []
    diffs, missing = [], []
    for it in exp["items"]:
        i = it["id"]
        f = os.path.join(d, "responses", "%02d.json" % i)
        if not os.path.exists(f):
            missing.append(i)
            continue
        r = load(f)
        text = r["choices"][0]["text"]
        n = r.get("usage", {}).get("completion_tokens")
        g = r.get("geulpu") or {}
        toks, lh = g.get("tokens"), g.get("logit_hashes")
        if toks is not None and lh is not None and len(toks) == len(lh) and len(toks) in (n, n + 1):   # 끝 토큰(EOS)까지 담기면 n + 1
            steps_ok += 1
        if lhref and toks is not None and lh is not None:
            rt, rl = lhref[i]["tokens"], lhref[i]["logit_hashes"]
            if toks == rt and lh == rl:
                lh_same += 1
                steps_total += len(lh)
            else:
                s = next((q for q in range(min(len(lh), len(rl))) if lh[q] != rl[q] or toks[q] != rt[q]), min(len(lh), len(rl)))
                lh_diffs.append((i, s, len(lh), len(rl)))
        xf, xr, truth = boxed(text), boxed(it["text"]), reqs[i]["answer"]
        acc_f += xf == truth
        acc_r += xr == truth
        ans_same += xf == xr
        if text == it["text"]:
            same_n += 1
        else:
            k = next((q for q in range(min(len(text), len(it["text"]))) if text[q] != it["text"][q]), min(len(text), len(it["text"])))
            diffs.append((i, k, n, it["n"], repr(it["text"][max(0, k - 40):k + 40]), repr(text[max(0, k - 40):k + 40])))
    total = len(exp["items"])
    w(f"- 출력 글이 기준과 같은 문제: **{same_n} / {total}**" + (f" (응답 없음 {missing})" if missing else ""))
    w(f"- 최종 답이 같은 문제: {ans_same} / {total - len(missing)} · 정답 수 친구 {acc_f} · 기준 {acc_r}")
    w(f"- 걸음마다의 로짓 해시가 생성 토큰 수만큼 있는 문제: {steps_ok} / {total - len(missing)}")
    if lhref:
        w(f"- 토큰 열과 걸음마다의 로짓 해시(어휘 152,064 개 전체의 비트)가 기준과 모두 같은 문제: **{lh_same} / {total - len(missing)}**"
          f" (같은 걸음 {steps_total:,} 개)")
        for i, s, a, b in lh_diffs:
            w(f"  - 문제 {i}: {s} 번째 걸음에서 로짓 해시가 갈림 (걸음 수 친구 {a} · 기준 {b})")
    else:
        w("- 기준 PC 의 로짓 해시가 없어 걸음마다의 비교는 하지 않았다")
    if summ:
        w(f"- 친구 PC 스크립트의 판정: {summ.get('same')} / {summ.get('total')}"
          + ("" if summ.get("same") == same_n else " — 다시 잰 값과 다르다!"))
    for i, k, n, rn, a, b in diffs:
        w(f"- 문제 {i}: {k} 번째 글자에서 갈림 (생성 {n} · 기준 {rn} 토큰)")
        w(f"  - 기준: {a}")
        w(f"  - 친구: {b}")
    w()
    if missing or not build:
        verdict = "판정 못 함 — 결과가 다 오지 않았다"
    elif same_n == total:
        verdict = "통과 — 32 문제 모두 출력 글이 기준 PC 와 같다"
        if lhref and lh_same == total:
            verdict += f", 매 걸음의 로짓(어휘 전체)까지 비트가 같다 ({steps_total:,} 걸음)"
        elif lhref:
            verdict += f" — 다만 로짓 해시는 {total - lh_same} 문제에서 다르다(위 참고)"
        verdict += "" if build_ok else " (빌드 해시 중 다른 것이 있다 — 위 참고)"
    else:
        verdict = f"못 미침 — {total - same_n} 문제가 다르다" + (" (빌드는 기준과 같다 — GPU · 드라이버 쪽 차이)" if build_ok else " (빌드도 다르다)")
    w("## 판정")
    w("- " + verdict)
    open(os.path.join(d, "대조결과.md"), "w", encoding="utf-8").write("\n".join(out) + "\n")
    print("\n대조결과.md →", os.path.join(d, "대조결과.md"))


if __name__ == "__main__":
    main()
