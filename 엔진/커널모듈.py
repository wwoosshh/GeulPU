"""커널 모듈(커널모듈.py) — 글 소스(.gl)를 만들고 PTX 로 바꿔 빌드/ 에 둔다. 내용의 해시로 캐시한다: 같은 생성기 · 같은 모듈 → 같은 .gl,
같은 .gl · 같은 컴파일러 → 같은 PTX. 값과는 상관없다(같은 소스에서 같은 PTX 가 나온다 — 캐시는 시간만 줄인다).

PTX 는 글 컴파일러가 만든다(17단계): 자체 호스팅 컴파일러(geul-lang-v2 self/*.gl)의 앞단과 글로 쓴 PTX 뒷단(geul-lang-v2
research/gpu/자체PTX/PTX.gl)을 그 컴파일러로 빌드한 자체PTX.exe. 캐시의 열쇠는 .gl 과 그 실행 파일의 바이트다. 1~16단계의 파이썬판
(컴파일러/글ptx.py + 참조 구현 앞단의 사본)은 대조용으로 남긴다 — 환경변수 GEULPU_PTX=파이썬 이면 파이썬판으로 만들고, =대조 면 둘 다
돌려 바이트가 다르면 멈춘다. 뒷단의 자리는 환경변수 GEULPU_글뒷단(기본: 이 저장소 옆의 geul-lang-v2/build/자체PTX.exe).

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
컴파일러 = os.path.join(ROOT, "컴파일러", "글ptx.py")           # 파이썬판 — 대조용
글뒷단 = os.environ.get("GEULPU_글뒷단") or os.path.normpath(os.path.join(ROOT, "..", "geul-lang-v2", "build", "자체PTX.exe"))
빌드 = os.path.join(ROOT, "빌드")
sys.path.insert(0, 커널폴더)
import 커널생성 as K       # noqa: E402

_컴파일러해시 = None
_글뒷단해시 = None


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


def 글뒷단해시():
    """글 PTX 뒷단(자체PTX.exe — 자체 호스팅 앞단과 글로 쓴 뒷단이 다 들었다)의 바이트 — PTX 캐시의 열쇠에 든다."""
    global _글뒷단해시
    if _글뒷단해시 is None:
        if not os.path.exists(글뒷단):
            raise RuntimeError(f"글 PTX 뒷단이 없다: {글뒷단}\n  geul-lang-v2 에서: GEUL_ROOT=$PWD ./build/self_컴파일러.exe "
                               "research/gpu/자체PTX/PTX.gl -o build/자체PTX.exe")
        _글뒷단해시 = _해시(b"geul-ptx-backend", open(글뒷단, "rb").read())
    return _글뒷단해시


def 방식():
    """PTX 를 만드는 쪽: 글(기본) · 파이썬 · 대조(둘 다 — 바이트가 같아야 한다)."""
    m = os.environ.get("GEULPU_PTX", "글")
    if m not in ("글", "파이썬", "대조"):
        raise RuntimeError(f"GEULPU_PTX 는 글 · 파이썬 · 대조 중 하나: {m}")
    return m


def _파이썬판(이름, gl, 출력):
    r = subprocess.run([sys.executable, 컴파일러, gl, "-o", 출력], capture_output=True)
    if r.returncode != 0:
        raise RuntimeError(f"{이름} 컴파일 실패(파이썬판):\n" + r.stderr.decode("utf-8", "replace")[-3000:])


def _글판(이름, gl, 출력):
    env = dict(os.environ, GEUL_ROOT=os.path.dirname(os.path.dirname(글뒷단)))
    r = subprocess.run([글뒷단, gl, "-o", 출력], capture_output=True, stdin=subprocess.DEVNULL, env=env)
    if r.returncode != 0:
        raise RuntimeError(f"{이름} 컴파일 실패(글 뒷단):\n" + r.stderr.decode("utf-8", "replace")[-3000:])


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
    """모듈 이름 → PTX 경로(없으면 글 뒷단으로 만든다 — 방식() 참고)."""
    gl = 소스(이름)
    m = 방식()
    열쇠 = _해시(open(gl, "rb").read(), 컴파일러해시() if m == "파이썬" else 글뒷단해시())
    경로 = os.path.join(빌드, "ptx", f"{os.path.splitext(이름)[0]}-{열쇠}.ptx")
    if not os.path.exists(경로):
        임시 = 경로 + f".{os.getpid()}.임시.ptx"
        os.makedirs(os.path.dirname(경로), exist_ok=True)
        if m == "파이썬":
            _파이썬판(이름, gl, 임시)
        else:
            _글판(이름, gl, 임시)
            if m == "대조":
                임시2 = 경로 + f".{os.getpid()}.파이썬.ptx"
                _파이썬판(이름, gl, 임시2)
                같음 = open(임시, "rb").read() == open(임시2, "rb").read()
                os.remove(임시2)
                if not 같음:
                    os.remove(임시)
                    raise RuntimeError(f"{이름}: 글 뒷단과 파이썬판의 PTX 가 다르다")
        os.replace(임시, 경로)
    return 경로
