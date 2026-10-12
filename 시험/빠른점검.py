#!/usr/bin/env python3
"""GeulPU 빠른 점검 — GPU · 모델 파일 없이 커밋마다 도는 검사(CI: .github/workflows/ci.yml 이 이것을 부른다).
단계마다의 공식 실행(GPU 의 비트 대조 · 속도 — 공식실행/)은 그대로 두고, 그 가운데 GPU 가 들지 않는 몫을 여기로:
  1. 파이썬 문법(저장소의 .py 모두)과 셸 스크립트 문법(공식실행/*.sh — bash -n)
  2. 계약의 CPU 참조 자체 시험(시험/계약자체.py)
  3. 판(타일 모양) 표가 생성기 · 호스트 · 시험에서 같은가
  4. 글(geul) 언어 프로그램이 빌드되는가 — 커널 생성기와 호스트 프로그램 모두(글 컴파일러)
  5. 모듈(커널 소스 · PTX)을 처음부터 만들어 시험/모듈해시.txt 와 바이트까지 견준다 — 바꾸려면 --해시갱신
  6. 실행기가 가져오는 DLL 이 kernel32 · shell32 · nvcuda 뿐인가(18단계 · 22단계의 조건)

  python -X utf8 시험/빠른점검.py [--글 <글 저장소 — 기본 ../geul-lang-v2>] [--병렬 N] [--출력 <폴더 — 기본 빌드/점검>] [--해시갱신]
글 저장소에는 build/self_컴파일러.exe 와 build/자체PTX.exe 가 있어야 한다(README 의 빠른 시작 2).
마지막 줄 "빠른 점검: 모두 통과"(종료 0) 또는 "못 미침 …"(종료 1).
"""
import argparse
import ast
import hashlib
import os
import re
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path.insert(0, os.path.join(ROOT, "시험"))
import 가져오기표       # noqa: E402

실패 = []
요약 = []


def 알림(단계, 통과, 덧=""):
    줄 = f"{'통과' if 통과 else '못 미침'}  [{단계}] {덧}"
    print(줄, flush=True)
    요약.append(줄)
    if not 통과:
        실패.append(단계)


def 해시(경로):
    h = hashlib.sha256()
    with open(경로, "rb") as f:
        for 덩이 in iter(lambda: f.read(1 << 20), b""):
            h.update(덩이)
    return h.hexdigest()


def 돌리기(명령, 기록, 환경=None, 폴더=None):
    """명령을 돌려 표준 출력 · 오류를 기록 파일에 — (종료 코드, 마지막 몇 줄)."""
    with open(기록, "wb") as f:
        r = subprocess.run(명령, stdout=f, stderr=subprocess.STDOUT, env=환경, cwd=폴더, stdin=subprocess.DEVNULL)
    꼬리 = open(기록, "rb").read().decode("utf-8", "replace").strip().splitlines()[-3:]
    return r.returncode, " / ".join(꼬리)


# ---- 1. 문법 ----
def 파이썬문법():
    수, 틀림 = 0, []
    for 폴더, 아래, 파일들 in os.walk(ROOT):
        아래[:] = [d for d in 아래 if d not in (".git", "빌드", "모델", "도구", "__pycache__", "점검결과")]
        for 이름 in 파일들:
            if 이름.endswith(".py"):
                경로 = os.path.join(폴더, 이름)
                수 += 1
                try:
                    compile(open(경로, "rb").read(), 경로, "exec")
                except SyntaxError as e:
                    틀림.append(f"{os.path.relpath(경로, ROOT)}:{e.lineno} {e.msg}")
    알림("파이썬 문법", not 틀림, f"파일 {수} 개" + (f" — {틀림[:5]}" if 틀림 else ""))


def 셸문법():
    bash = "bash"
    try:
        subprocess.run([bash, "--version"], capture_output=True, check=True)
    except (OSError, subprocess.CalledProcessError):
        알림("셸 문법", True, "bash 가 없어 건너뜀")
        return
    폴더 = os.path.join(ROOT, "공식실행")
    틀림 = []
    수 = 0
    for 이름 in sorted(os.listdir(폴더)):
        if 이름.endswith(".sh"):
            수 += 1
            r = subprocess.run([bash, "-n", 이름], capture_output=True, cwd=폴더)
            if r.returncode != 0:
                틀림.append(f"{이름}: {r.stderr.decode('utf-8', 'replace').strip()[:200]}")
    알림("셸 문법", not 틀림, f"공식실행/*.sh {수} 개" + (f" — {틀림}" if 틀림 else ""))


# ---- 2. 계약 자체 시험 ----
def 계약자체(출력):
    t0 = time.time()
    rc, 꼬리 = 돌리기([sys.executable, "-I", "-X", "utf8", os.path.join(ROOT, "시험", "계약자체.py")], os.path.join(출력, "계약자체.txt"))
    알림("계약 자체 시험", rc == 0, f"{꼬리} ({time.time() - t0:.1f} 초)")


# ---- 3. 판 표 ----
def 판표들():
    """(이름, WM, WN, MT, NT) 의 차례 목록을 곳마다."""
    표 = {}
    s = open(os.path.join(ROOT, "커널", "생성타일.gl"), encoding="utf-8").read()
    표["커널/생성타일.gl"] = [(m[1], *map(int, m[2:6])) for m in re.findall(r'판하나\((\d+), "([^"]+)", (\d+), (\d+), (\d+), (\d+), \d+, \d+\)', s)]
    s = open(os.path.join(ROOT, "호스트", "엔진.gl"), encoding="utf-8").read()
    표["호스트/엔진.gl"] = [(m[1], *map(int, m[2:6])) for m in re.findall(r'판하나\((\d+), "([^"]+)", (\d+), (\d+), (\d+), (\d+)\)\.', s)]
    for 파일, 이름 in (("판23.py", "판들"), ("판26.py", "_판표")):
        트리 = ast.parse(open(os.path.join(ROOT, "시험", 파일), encoding="utf-8").read())
        for 노드 in 트리.body:
            if isinstance(노드, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 이름 for t in 노드.targets):
                표[f"시험/{파일}"] = [tuple(x) for x in ast.literal_eval(노드.value)]
    return 표


def 판표():
    표 = 판표들()
    기준 = 표["커널/생성타일.gl"]
    다름 = [곳 for 곳, 값 in 표.items() if 값 != 기준]
    알림("판 표", bool(기준) and not 다름 and len(표) == 4, f"{len(기준)} 판 · 곳 {len(표)}" + (f" — 생성기와 다른 곳 {다름}" if 다름 else ""))


# ---- 4 · 5 · 6. 빌드 · 모듈 · 가져오기 표 ----
def 호스트프로그램들():
    """호스트/ 에서 시작하기 가 있는 것(프로그램)."""
    폴더 = os.path.join(ROOT, "호스트")
    return sorted(이름[:-3] for 이름 in os.listdir(폴더) if 이름.endswith(".gl") and "시작하기]는" in open(os.path.join(폴더, 이름), encoding="utf-8").read())


def 빌드(글, 출력, 병렬):
    컴파일러 = os.path.join(글, "build", "self_컴파일러.exe")
    환경 = dict(os.environ, GEUL_ROOT=글)
    일들 = [("커널생성", os.path.join(ROOT, "커널", "커널생성.gl"))] + [(p, os.path.join(ROOT, "호스트", p + ".gl")) for p in 호스트프로그램들()]

    def 하나(일):
        이름, 소스 = 일
        exe = os.path.join(출력, 이름 + ".exe")
        if os.path.exists(exe):
            os.remove(exe)
        rc, 꼬리 = 돌리기([컴파일러, 소스, "-o", exe], os.path.join(출력, f"빌드_{이름}.txt"), 환경)
        return 이름, rc == 0 and os.path.exists(exe), 꼬리
    t0 = time.time()
    with ThreadPoolExecutor(병렬) as ex:
        결과 = list(ex.map(하나, 일들))
    틀림 = [f"{이름}: {꼬리}" for 이름, 된, 꼬리 in 결과 if not 된]
    알림("글 빌드", not 틀림, f"생성기 + 호스트 프로그램 {len(일들) - 1} 개 ({time.time() - t0:.1f} 초)" + (f" — {틀림}" if 틀림 else ""))
    return not 틀림


def 모듈표읽기():
    줄들 = []
    for 줄 in open(os.path.join(ROOT, "시험", "모듈해시.txt"), encoding="utf-8"):
        if 줄.strip() and not 줄.startswith("#"):
            이름, 인자, gl, ptx = [x.strip() for x in 줄.split("|")]
            줄들.append((이름, 인자.split(), gl, ptx))
    return 줄들


def 모듈(글, 출력, 병렬, 갱신):
    생성기 = os.path.join(출력, "커널생성.exe")
    뒷단 = os.path.join(글, "build", "자체PTX.exe")
    표 = 모듈표읽기()

    def 하나(항목):
        이름, 인자, _, _ = 항목
        gl = os.path.join(출력, 이름 + ".gl")
        ptx = os.path.join(출력, 이름 + ".ptx")
        for x in (gl, ptx):
            if os.path.exists(x):
                os.remove(x)
        t0 = time.time()
        rc, 꼬리 = 돌리기([생성기] + 인자 + [gl], os.path.join(출력, f"생성_{이름}.txt"))
        if rc != 0 or not os.path.exists(gl):
            return 이름, None, None, f"생성 실패: {꼬리}", 0.0
        rc, 꼬리 = 돌리기([뒷단, gl, "-o", ptx], os.path.join(출력, f"PTX_{이름}.txt"))
        if rc != 0 or not os.path.exists(ptx):
            return 이름, 해시(gl), None, f"PTX 실패(종료 {rc}): {꼬리[-300:]}", time.time() - t0
        return 이름, 해시(gl), 해시(ptx), "", time.time() - t0
    with ThreadPoolExecutor(병렬) as ex:
        결과 = list(ex.map(하나, 표))
    새줄 = []
    for (이름, 인자, 옛gl, 옛ptx), (_, gl, ptx, 오류, 초) in zip(표, 결과):
        새줄.append(f"{이름} | {' '.join(인자)} | {gl or '?'} | {ptx or '?'}")
        if 오류:
            알림(f"모듈 {이름}", False, 오류)
        elif 갱신:
            알림(f"모듈 {이름}", True, f"해시를 새로 적음 ({초:.0f} 초)")
        else:
            같음 = gl == 옛gl and ptx == 옛ptx
            덧 = f"소스 {'같음' if gl == 옛gl else '다름'} · PTX {'같음' if ptx == 옛ptx else '다름'} ({초:.0f} 초)"
            if not 같음:
                덧 += f" — 새 해시 {gl} | {ptx} (일부러 바꿨다면 --해시갱신)"
            알림(f"모듈 {이름}", 같음, 덧)
    머리 = [줄 for 줄 in open(os.path.join(ROOT, "시험", "모듈해시.txt"), encoding="utf-8") if 줄.startswith("#")]
    내용 = "".join(머리) + "\n".join(새줄) + "\n"
    open(os.path.join(출력, "모듈해시.txt"), "w", encoding="utf-8", newline="\n").write(내용)
    if 갱신 and all(not r[3] for r in 결과):
        open(os.path.join(ROOT, "시험", "모듈해시.txt"), "w", encoding="utf-8", newline="\n").write(내용)
        print("시험/모듈해시.txt 를 새 해시로 고쳤다", flush=True)


def 가져오기검사(출력):
    exe = os.path.join(출력, "실행기.exe")
    if not os.path.exists(exe):
        알림("실행기의 가져오기 표", False, "실행기.exe 가 없다(빌드 실패)")
        return
    dll들 = sorted({d.lower() for d, _ in 가져오기표.가져오기(exe)})
    알림("실행기의 가져오기 표", set(dll들) <= {"kernel32.dll", "shell32.dll", "nvcuda.dll"}, f"{dll들}")


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    p = argparse.ArgumentParser()
    p.add_argument("--글", default=os.path.normpath(os.path.join(ROOT, "..", "geul-lang-v2")))
    p.add_argument("--병렬", type=int, default=max(1, min(8, os.cpu_count() or 1)))
    p.add_argument("--출력", default=os.path.join(ROOT, "빌드", "점검"))
    p.add_argument("--해시갱신", action="store_true")
    a = p.parse_args()
    글 = os.path.abspath(a.글)
    출력 = os.path.abspath(a.출력)
    os.makedirs(출력, exist_ok=True)
    t0 = time.time()
    파이썬문법()
    셸문법()
    계약자체(출력)
    판표()
    도구 = [os.path.join(글, "build", x) for x in ("self_컴파일러.exe", "자체PTX.exe")]
    없는것 = [x for x in 도구 if not os.path.exists(x)]
    if 없는것:
        알림("글 도구", False, f"없다: {없는것} — README 의 빠른 시작 2")
    else:
        print("글 도구: " + " · ".join(f"{os.path.basename(x)} {해시(x)[:16]}" for x in 도구), flush=True)
        if 빌드(글, 출력, a.병렬):
            모듈(글, 출력, a.병렬, a.해시갱신)
            가져오기검사(출력)
    open(os.path.join(출력, "요약.txt"), "w", encoding="utf-8").write("\n".join(요약) + "\n")
    print(f"빠른 점검: {'모두 통과' if not 실패 else '못 미침 ' + str(실패)} ({time.time() - t0:.0f} 초)", flush=True)
    return 0 if not 실패 else 1


if __name__ == "__main__":
    sys.exit(main())
