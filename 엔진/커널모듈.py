"""커널 모듈(커널모듈.py) — 글 소스(.gl)를 만들고 PTX 로 바꿔 빌드/ 에 둔다. 내용의 해시로 캐시한다: 같은 생성기 · 같은 모듈 → 같은 .gl,
같은 .gl · 같은 컴파일러(글ptx.py 와 글 앞단) → 같은 PTX. 값과는 상관없다(같은 소스에서 같은 PTX 가 나온다 — 캐시는 시간만 줄인다).

  gpt2.gl            — 손으로 쓴 GPT-2 small 의 작은 커널들(커널/gpt2.gl)
  gpt2XL.gl          — 커널생성.gpt2_source("XL")
  커널프롬.gl         — 커널생성.프롬소스() (프롬프트 메가커널 — 짧은실수 KV 판의 실험)
  qwen2Q8.gl         — 커널생성.qwen2_source() (14단계 — Qwen2: RMSNorm · RoPE · SwiGLU · GQA)
  그 밖               — 커널생성.source(*커널생성.모듈들[이름])
"""
import hashlib
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, ".."))
커널폴더 = os.path.join(ROOT, "커널")
컴파일러 = os.path.join(ROOT, "컴파일러", "글ptx.py")
빌드 = os.path.join(ROOT, "빌드")
sys.path.insert(0, 커널폴더)
import 커널생성 as K       # noqa: E402

_컴파일러해시 = None


def _해시(*조각들):
    h = hashlib.sha256()
    for c in 조각들:
        h.update(c if isinstance(c, bytes) else str(c).encode("utf-8"))
        h.update(b"\0")
    return h.hexdigest()[:16]


def 컴파일러해시():
    """글ptx.py 와 글 앞단(컴파일러/ref/geul/*.py)의 바이트 — PTX 캐시의 열쇠에 든다."""
    global _컴파일러해시
    if _컴파일러해시 is None:
        조각 = [open(컴파일러, "rb").read()]
        앞단 = os.path.join(ROOT, "컴파일러", "ref", "geul")
        for f in sorted(os.listdir(앞단)):
            if f.endswith(".py"):
                조각 += [f.encode("utf-8"), open(os.path.join(앞단, f), "rb").read()]
        _컴파일러해시 = _해시(*조각)
    return _컴파일러해시


def _쓰기(경로, 내용):
    os.makedirs(os.path.dirname(경로), exist_ok=True)
    임시 = 경로 + f".{os.getpid()}.임시"
    with open(임시, "wb") as f:
        f.write(내용)
    os.replace(임시, 경로)                     # 같은 열쇠의 파일은 내용이 같다 — 여럿이 함께 써도 된다


def 소스(이름):
    """모듈 이름(예: 커널Q8정수KV.gl) → .gl 경로. 만든 소스는 빌드/커널/ 에 (생성기 · 실험 변형 · 모듈마다의 열쇠)."""
    if 이름 == "gpt2.gl":
        return os.path.join(커널폴더, "gpt2.gl")
    생성기 = open(os.path.join(커널폴더, "커널생성.py"), "rb").read()
    열쇠 = _해시(생성기, 이름, repr(sorted(K.어텐션변형)))
    경로 = os.path.join(빌드, "커널", f"{os.path.splitext(이름)[0]}-{열쇠}.gl")
    if not os.path.exists(경로):
        if 이름 == "gpt2XL.gl":
            글 = K.gpt2_source("XL")
        elif 이름 == "커널프롬.gl":
            글 = K.프롬소스()
        elif 이름 == "qwen2Q8.gl":                  # 14단계 — Qwen2(Llama 계열 블록)
            글 = K.qwen2_source()
        else:
            글 = K.source(*K.모듈들[이름])
        _쓰기(경로, 글.encode("utf-8"))
    return 경로


def ptx(이름):
    """모듈 이름 → PTX 경로(없으면 글ptx.py 로 만든다)."""
    gl = 소스(이름)
    열쇠 = _해시(open(gl, "rb").read(), 컴파일러해시())
    경로 = os.path.join(빌드, "ptx", f"{os.path.splitext(이름)[0]}-{열쇠}.ptx")
    if not os.path.exists(경로):
        임시 = 경로 + f".{os.getpid()}.임시.ptx"
        os.makedirs(os.path.dirname(경로), exist_ok=True)
        r = subprocess.run([sys.executable, 컴파일러, gl, "-o", 임시], capture_output=True)
        if r.returncode != 0:
            raise RuntimeError(f"{이름} 컴파일 실패:\n" + r.stderr.decode("utf-8", "replace")[-3000:])
        os.replace(임시, 경로)
    return 경로
