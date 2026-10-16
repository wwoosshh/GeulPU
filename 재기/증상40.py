#!/usr/bin/env python3
"""40단계 판정기(문서/40단계.md '정의') — 증상(S1 ~ S6), 위험한 걸음(O · R · C), 기울기, 통계(묶음 붓스트랩 · McNemar · Holm).

모두 토큰 번호 · 토큰의 바이트 · 글로만 판정한다(엔진과 상관없다). 토큰의 바이트는 GGUF 의 어휘(바이트 BPE — GPT-2 의 바이트 ↔ 글자 표)에서.

  python -I -X utf8 재기/증상40.py --시험        (단위 시험)
"""
import math
import os
import re
import sys
import unicodedata
from difflib import SequenceMatcher

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, ".."))
sys.path.insert(0, os.path.join(ROOT, "엔진"))

LN10 = math.log(10.0)
R길이 = 8                   # R: 답 안의 앞선 8-토큰 묶음을 베끼는가
위험여유 = LN10             # 여유 m < ln 10 이면 위험한 걸음


# ---------------------------------------------------------------- 토큰의 바이트
def 바이트표(gguf_경로):
    """GGUF 어휘 → 토큰마다의 바이트(바이트 BPE). 특수 토큰(제어 · 사용자 정의)은 b'' 로 두고 따로 특수 집합에."""
    import gguf읽기 as GR
    import 토크나이저 as TK
    meta = GR.GGUF(gguf_경로).meta
    toks, 종류 = meta["tokenizer.ggml.tokens"], meta["tokenizer.ggml.token_type"]
    inv = {c: b for b, c in TK._바이트글자().items()}
    표, 특수 = [], set()
    for i, t in enumerate(toks):
        if 종류[i] in (3, 4):
            표.append(b"")
            특수.add(i)
            continue
        try:
            표.append(bytes(inv[c] for c in t))
        except KeyError:
            표.append(t.encode("utf-8"))
    return 표, 특수


# ---------------------------------------------------------------- 글자 계통
def 한글인가(cp):
    return 0xAC00 <= cp <= 0xD7A3 or 0x1100 <= cp <= 0x11FF or 0x3130 <= cp <= 0x318F or 0xA960 <= cp <= 0xA97F \
        or 0xD7B0 <= cp <= 0xD7FF


def 라틴인가(cp):
    return (0x41 <= cp <= 0x5A) or (0x61 <= cp <= 0x7A) or (0xC0 <= cp <= 0x24F and cp not in (0xD7, 0xF7)) \
        or 0x1E00 <= cp <= 0x1EFF or 0x2C60 <= cp <= 0x2C7F or 0xA720 <= cp <= 0xA7FF or 0xFF21 <= cp <= 0xFF3A \
        or 0xFF41 <= cp <= 0xFF5A


def 그리스인가(cp):
    return 0x370 <= cp <= 0x3FF or 0x1F00 <= cp <= 0x1FFF


def 다른문자인가(ch):
    """한글도 라틴도 아닌 문자(글자 — 유니코드 범주 L). 그리스 문자는 수식에서 흔해 넣지 않는다(문서 '정의' S2a)."""
    cp = ord(ch)
    if 한글인가(cp) or 라틴인가(cp) or 그리스인가(cp):
        return False
    return unicodedata.category(ch).startswith("L")


def 조각계통(b):
    """끝나지 않은 UTF-8 조각(b — 첫 바이트가 여러 바이트 글자의 머리)의 계통: '다른' · '한글' · '모름'.
    문서: UTF-8 첫 바이트 E4 ~ E9 는 한자, E3 81 ~ E3 83 은 가나. 키릴(D0 ~ D3) · 아랍(D8 ~ DB) · 데바나가리(E0 A4 · A5) · 타이(E0 B8 · B9)."""
    if not b:
        return "모름"
    c0 = b[0]
    if 0xE4 <= c0 <= 0xE9:
        return "다른"
    if 0xD0 <= c0 <= 0xD3 or 0xD8 <= c0 <= 0xDB:
        return "다른"
    if c0 == 0xE3:
        if len(b) >= 2 and 0x81 <= b[1] <= 0x83:
            return "다른"
        return "모름"
    if c0 == 0xE0:
        if len(b) >= 2 and b[1] in (0xA4, 0xA5, 0xB8, 0xB9):
            return "다른"
        return "모름"
    if c0 in (0xEB, 0xEC):
        return "한글"
    if c0 == 0xEA:
        if len(b) >= 2 and b[1] >= 0xB0:
            return "한글"
        return "모름"
    if c0 == 0xED:
        if len(b) >= 2 and b[1] <= 0x9E:
            return "한글"
        return "모름"
    return "모름"


def _쪼개기(b):
    """바이트 → (온전한 글자들의 글, 앞에 붙은 이어짐 바이트 수, 끝에 남은 끝나지 않은 조각)."""
    i = 0
    앞이음 = 0
    while i < len(b) and 0x80 <= b[i] <= 0xBF:
        i += 1
        앞이음 += 1
    글 = []
    끝조각 = b""
    while i < len(b):
        c = b[i]
        n = 1 if c < 0x80 else 2 if 0xC0 <= c <= 0xDF else 3 if 0xE0 <= c <= 0xEF else 4 if 0xF0 <= c <= 0xF7 else 1
        if i + n > len(b):
            끝조각 = b[i:]
            break
        try:
            글.append(b[i:i + n].decode("utf-8"))
        except UnicodeDecodeError:
            글.append("\ufffd")
        i += n
    return "".join(글), 앞이음, 끝조각


def 토큰계통(b):
    """O 의 토큰 분류: '정상' · '다른' · '깨짐'(글자 경계에서 이어짐 바이트로 시작) · '모름' · '특수'(바이트 없음)."""
    if not b:
        return "특수"
    글, 앞이음, 끝조각 = _쪼개기(b)
    if 앞이음:
        return "깨짐"
    if any(다른문자인가(ch) for ch in 글):
        return "다른"
    if 끝조각:
        k = 조각계통(끝조각)
        return "다른" if k == "다른" else ("정상" if k == "한글" else "모름")
    return "정상"


def 계통표(표):
    return [토큰계통(b) for b in 표]


# ---------------------------------------------------------------- 바이트 흐름
def 글자한가운데인가(바이트들):
    """지금까지의 바이트가 한 글자의 UTF-8 을 다 채우지 않았는가(글자 한가운데)."""
    n = len(바이트들)
    for back in range(1, min(4, n) + 1):
        c = 바이트들[n - back]
        if 0x80 <= c <= 0xBF:
            continue
        need = 1 if c < 0x80 else 2 if 0xC0 <= c <= 0xDF else 3 if 0xE0 <= c <= 0xEF else 4 if 0xF0 <= c <= 0xF7 else 1
        return back < need
    return False


def 쪼개진음절수(토큰들, 표):
    """토큰 흐름에서 두 토큰 이상에 걸친 한글 음절의 수와 한글 음절의 수."""
    흐름 = bytearray()
    주인 = []
    for k, t in enumerate(토큰들):
        b = 표[t]
        흐름 += b
        주인 += [k] * len(b)
    i = n음절 = n쪼갬 = 0
    while i < len(흐름):
        c = 흐름[i]
        n = 1 if c < 0x80 else 2 if 0xC0 <= c <= 0xDF else 3 if 0xE0 <= c <= 0xEF else 4 if 0xF0 <= c <= 0xF7 else 1
        if n == 3 and i + 3 <= len(흐름):
            try:
                ch = bytes(흐름[i:i + 3]).decode("utf-8")
                if 0xAC00 <= ord(ch) <= 0xD7A3:
                    n음절 += 1
                    if 주인[i] != 주인[i + 2]:
                        n쪼갬 += 1
            except UnicodeDecodeError:
                pass
        i += n
    return n쪼갬, n음절


# ---------------------------------------------------------------- 증상
def S1_끝없는반복(토큰들, 길이한도에닿음, p최대=512):
    """끝이 같은 토큰 묶음(길이 p)의 되풀이로 max(3p, 64) 토큰 이상 — 가장 작은 p. (p, 길이) 또는 None."""
    if not 길이한도에닿음:
        return None
    t = 토큰들
    n = len(t)
    for p in range(1, min(p최대, n // 3) + 1):
        L = p
        i = n - p - 1
        while i >= 0 and t[i] == t[i + p]:
            L += 1
            i -= 1
        if L >= max(3 * p, 64):
            return (p, L)
    return None


_코드블록 = re.compile(r"```.*?(```|$)", re.S)
_인라인코드 = re.compile(r"`[^`\n]*`")


def 코드빼기(글):
    return _인라인코드.sub(" ", _코드블록.sub(" ", 글))


def S2_다른문자(답, 질문):
    """(S2a, S2b, 자세히). S2a: 질문에 없는 다른 문자가 두 자 이상 이어진 곳. S2b: 글자 가운데 한글이 50 % 미만."""
    글 = 코드빼기(답)
    질문글자 = set(질문)
    a = False
    처음 = None
    줄 = 0
    for i, ch in enumerate(글):
        if 다른문자인가(ch) and ch not in 질문글자:
            줄 += 1
            if 줄 >= 2 and not a:
                a = True
                처음 = 글[max(0, i - 12):i + 4]
        else:
            줄 = 0
    한 = sum(1 for ch in 글 if 한글인가(ord(ch)))
    글자 = sum(1 for ch in 글 if unicodedata.category(ch).startswith("L"))
    b = 글자 > 0 and 한 / 글자 < 0.5
    return a, b, {"처음": 처음, "한글": 한, "글자": 글자}


def _boxed들(글):
    out = []
    i = 0
    while True:
        j = 글.find("\\boxed{", i)
        if j < 0:
            return out
        k = j + len("\\boxed{")
        d = 1
        while k < len(글) and d:
            if 글[k] == "{":
                d += 1
            elif 글[k] == "}":
                d -= 1
            k += 1
        out.append(글[j + len("\\boxed{"):k - 1] if d == 0 else 글[j + len("\\boxed{"):])
        i = k


_수 = re.compile(r"-?\d+(?:\.\d+)?")


def 수로(s):
    s = s.replace(",", "").replace("$", "").replace("\\%", "").replace("%", "").replace("\\!", "")
    s = re.sub(r"\\text\{[^}]*\}", "", s)
    s = re.sub(r"\\(?:dfrac|frac)\{(-?\d+)\}\{(\d+)\}", lambda m: str(int(m.group(1)) / int(m.group(2))), s)
    m = _수.findall(s)
    return float(m[-1]) if m else None


def 정답수(gsm8k_답):
    return float(gsm8k_답.split("####")[-1].strip().replace(",", ""))


def S3_S4(답, 길이한도에닿음, 정답, 마지막수로=False):
    """(S3 끝내지 못함, S4 틀린 답, 고른 수)."""
    bx = _boxed들(답)
    s3 = 길이한도에닿음 and not bx
    수 = 수로(bx[-1]) if bx else None
    if 수 is None and 마지막수로 and not bx:
        m = _수.findall(답.replace(",", ""))
        수 = float(m[-1]) if m else None
    s4 = s3 or 수 is None or abs(수 - 정답) > 1e-6
    return s3, s4, 수


def S6_맞춤법(답, 원문):
    """(S6, 옮김 여부, 자세히). 옮겨 쓴 부분(원문과 가장 닮은 곳)이 원문과 한 글자라도 다르면 S6. 원문과 닮은 글자가 반이 안 되면
    '옮기지 않음'(S6 아님). 깨진 글자(U+FFFD)가 있으면 S6."""
    src = 원문.strip().strip("\"'“”‘’")
    if "\ufffd" in 답:
        return True, True, {"까닭": "깨진 글자"}
    if src in 답:
        return False, True, {"까닭": "같음"}
    sm = SequenceMatcher(None, src, 답, autojunk=False)
    같은글자 = sum(bl.size for bl in sm.get_matching_blocks())
    if 같은글자 < 0.5 * len(src):
        return False, False, {"까닭": "옮기지 않음", "같은글자": 같은글자}
    return True, True, {"까닭": "다름", "같은글자": 같은글자, "원문": len(src)}


def S5_깨짐(토큰들, 답, 끝남):
    """빈 답 · 3 토큰 안에 끝 · 잘린 UTF-8 로 끝."""
    if not 답.strip():
        return True
    if 끝남 and len(토큰들) <= 3:
        return True
    return 답.endswith("\ufffd")


# ---------------------------------------------------------------- 위험한 걸음
def 위험한걸음들(답토큰, 상위번호, 상위값, 표, 계통, 특수, 유형들=("O", "R", "C")):
    """G 의 답(토큰 번호 — 끝 토큰 포함)과 걸음마다의 상위 20(번호 · 로그확률)에서 위험한 걸음을 찾는다.
    돌려줌: [(걸음 t, 유형, a, b, 여유 m, 대조 b′ 또는 None)] — a 는 G 의 1위(= 고른 토큰), b 는 그 유형의 비정상 토큰 가운데 가장 높은 것."""
    out = []
    바이트 = bytearray()
    n = min(len(답토큰), len(상위번호))         # GeulPU 의 tokens 는 끝 토큰을 담고 상위 목록은 그 걸음을 담지 않는다
    for t in range(n):
        ids, lps = 상위번호[t], 상위값[t]
        a = 답토큰[t]
        if not ids or ids[0] != a:            # 탐욕이면 고른 토큰 = 1위(같은 값이면 작은 번호) — 아니면 건너뜀(기록)
            바이트 += 표[a]
            continue
        la = lps[0]
        한가운데 = 글자한가운데인가(바이트)
        if "C" in 유형들 and 한가운데:
            # 남은 실제 바이트(G 가 쓴 것)와 맞는 후보는 정상(같은 글자의 다른 쪼갬), 아니면 비정상(다른 글자 · 깨짐)
            남은 = bytes(b"".join(표[x] for x in 답토큰[t:t + 4]))
            b = bc = None
            for j in range(1, len(ids)):
                x = ids[j]
                xb = 표[x]
                맞음 = bool(xb) and 남은[:len(xb)] == xb
                if 맞음 and bc is None:
                    bc = j
                if not 맞음 and b is None:
                    b = j
            if b is not None and la - lps[b] < 위험여유:
                out.append((t, "C", a, ids[b], la - lps[b], ids[bc] if bc is not None else None,
                            lps[b], lps[bc] if bc is not None else None))
        if not 한가운데:
            if "O" in 유형들 and 계통[a] == "정상":
                b = bc = None
                for j in range(1, len(ids)):
                    k = 계통[ids[j]]
                    if k == "다른" and b is None:
                        b = j
                    if k == "정상" and bc is None:
                        bc = j
                if b is not None and la - lps[b] < 위험여유:
                    out.append((t, "O", a, ids[b], la - lps[b], ids[bc] if bc is not None else None,
                                lps[b], lps[bc] if bc is not None else None))
            if "R" in 유형들 and t >= R길이 - 1:
                앞 = 답토큰[t - (R길이 - 1):t]
                if 앞 and not any(x in 특수 for x in 앞):
                    본 = _묶음들(답토큰[:t], R길이)
                    def 베낌(x):
                        return tuple(앞) + (x,) in 본
                    if not 베낌(a):
                        b = bc = None
                        for j in range(1, len(ids)):
                            if 베낌(ids[j]):
                                if b is None:
                                    b = j
                            elif bc is None:
                                bc = j
                        if b is not None and la - lps[b] < 위험여유:
                            out.append((t, "R", a, ids[b], la - lps[b], ids[bc] if bc is not None else None,
                                        lps[b], lps[bc] if bc is not None else None))
        바이트 += 표[a]
    return out


def _묶음들(토큰, k):
    """토큰 안의 모든 k-묶음의 집합(느린 판 — 시험에서 빠른 판과 견준다)."""
    s = set()
    for i in range(len(토큰) - k + 1):
        s.add(tuple(토큰[i:i + k]))
    return s


class 묶음집합:
    """답 하나를 앞에서부터 훑을 때 쓰는 8-묶음 집합(걸음마다 하나씩 더한다)."""
    def __init__(self, k=R길이):
        self.k = k
        self.s = set()
        self.t = []

    def 더하기(self, x):
        self.t.append(x)
        if len(self.t) >= self.k:
            self.s.add(tuple(self.t[-self.k:]))


def 위험한걸음들_빠르게(답토큰, 상위번호, 상위값, 표, 계통, 특수, 유형들=("O", "R", "C")):
    """위험한걸음들 과 같은 결과 — R 의 8-묶음 집합을 걸음마다 하나씩 더해 간다(긴 답에서 빠르게)."""
    out = []
    바이트 = bytearray()
    묶 = 묶음집합(R길이)
    n = min(len(답토큰), len(상위번호))
    for t in range(n):
        ids, lps = 상위번호[t], 상위값[t]
        a = 답토큰[t]
        if ids and ids[0] == a:
            la = lps[0]
            한가운데 = 글자한가운데인가(바이트)
            if "C" in 유형들 and 한가운데:
                남은 = bytes(b"".join(표[x] for x in 답토큰[t:t + 4]))
                b = bc = None
                for j in range(1, len(ids)):
                    xb = 표[ids[j]]
                    맞음 = bool(xb) and 남은[:len(xb)] == xb
                    if 맞음 and bc is None:
                        bc = j
                    if not 맞음 and b is None:
                        b = j
                if b is not None and la - lps[b] < 위험여유:
                    out.append((t, "C", a, ids[b], la - lps[b], ids[bc] if bc is not None else None,
                                lps[b], lps[bc] if bc is not None else None))
            if not 한가운데:
                if "O" in 유형들 and 계통[a] == "정상":
                    b = bc = None
                    for j in range(1, len(ids)):
                        k = 계통[ids[j]]
                        if k == "다른" and b is None:
                            b = j
                        if k == "정상" and bc is None:
                            bc = j
                    if b is not None and la - lps[b] < 위험여유:
                        out.append((t, "O", a, ids[b], la - lps[b], ids[bc] if bc is not None else None,
                                    lps[b], lps[bc] if bc is not None else None))
                if "R" in 유형들 and t >= R길이 - 1:
                    앞 = tuple(답토큰[t - (R길이 - 1):t])
                    if not any(x in 특수 for x in 앞):
                        if 앞 + (a,) not in 묶.s:
                            b = bc = None
                            for j in range(1, len(ids)):
                                if 앞 + (ids[j],) in 묶.s:
                                    if b is None:
                                        b = j
                                elif bc is None:
                                    bc = j
                            if b is not None and la - lps[b] < 위험여유:
                                out.append((t, "R", a, ids[b], la - lps[b], ids[bc] if bc is not None else None,
                                            lps[b], lps[bc] if bc is not None else None))
        바이트 += 표[a]
        묶.더하기(a)
    return out


def 기울기(lpX_a, lpX_b, lpG_a, lpG_b):
    """Δ = [ln p_X(b) − ln p_X(a)] − [ln p_G(b) − ln p_G(a)]. 하나라도 없으면 None."""
    if None in (lpX_a, lpX_b, lpG_a, lpG_b):
        return None
    return (lpX_b - lpX_a) - (lpG_b - lpG_a)


# ---------------------------------------------------------------- 통계
def 묶음붓스트랩(문항합, 문항수, 번=10000, 씨앗=40):
    """문항마다 (Δ 의 합, 걸음 수) — 문항을 되뽑아 평균 Δ(= Σ합 / Σ수). (평균, 95 % 구간, 양쪽 p)."""
    합 = np.asarray(문항합, np.float64)
    수 = np.asarray(문항수, np.float64)
    P = len(합)
    if P == 0 or 수.sum() == 0:
        return None, (None, None), None
    평균 = 합.sum() / 수.sum()
    rng = np.random.default_rng(씨앗)
    뽑 = rng.integers(0, P, size=(번, P))
    s, c = 합[뽑].sum(1), 수[뽑].sum(1)
    c[c == 0] = np.nan
    m = s / c
    m = m[~np.isnan(m)]
    lo, hi = np.percentile(m, [2.5, 97.5])
    p = min(1.0, 2 * min((m <= 0).mean(), (m >= 0).mean()))
    p = max(p, 1.0 / len(m))
    return float(평균), (float(lo), float(hi)), float(p)


def McNemar(b, c):
    """정확 검정(양쪽): b + c 번 가운데 작은 쪽이 그만큼 이하로 나올 확률 × 2."""
    n = b + c
    if n == 0:
        return 1.0
    k = min(b, c)
    s = sum(math.comb(n, i) for i in range(k + 1))
    return min(1.0, 2 * s / 2 ** n)


def Holm(ps):
    """고친 p(Holm — 차례대로 큰 쪽으로 올린 값)."""
    m = len(ps)
    차례 = sorted(range(m), key=lambda i: ps[i])
    out = [None] * m
    앞 = 0.0
    for r, i in enumerate(차례):
        v = min(1.0, (m - r) * ps[i])
        앞 = max(앞, v)
        out[i] = 앞
    return out


def 기울기판정(평균, 구간, 고친p, n걸음, 최소=200, 같음띠=0.05):
    if 평균 is None or n걸음 < 최소:
        return "판단 보류"
    if 고친p < 0.05:
        return "나쁜 쪽으로 기운다" if 평균 > 0 else "좋은 쪽으로 기운다"
    if -같음띠 <= 구간[0] and 구간[1] <= 같음띠:
        return "기울지 않는다"
    return "판단 보류"


def 궤적판정(b, c, 고친p, 최소=40):
    if b + c < 최소:
        return "판단 보류"
    if 고친p < 0.05:
        return "늘린다" if b > c else "줄인다"
    return "흔들지만 늘리지 않는다"


# ---------------------------------------------------------------- 단위 시험
def _시험():
    n = 0

    def 맞다(x, 말):
        nonlocal n
        n += 1
        assert x, 말

    # S1
    t = [1, 2, 3] + [7, 8] * 40
    맞다(S1_끝없는반복(t, True) == (2, 80), "S1 p=2")
    맞다(S1_끝없는반복(t, False) is None, "S1 길이 한도 아니면 없음")
    맞다(S1_끝없는반복([5] * 63 + [6], True) is None, "S1 끝이 다르면 없음")
    맞다(S1_끝없는반복([4] + [5] * 64, True) == (1, 64), "S1 p=1 64")
    맞다(S1_끝없는반복([4] + [5] * 63, True) is None, "S1 p=1 63 은 모자람")
    긴 = list(range(100)) * 3
    맞다(S1_끝없는반복(긴, True) == (100, 300), "S1 p=100")
    # S2
    a, b, _ = S2_다른문자("이것은 一期一會 라는 말입니다.", "")
    맞다(a and not b, "S2a 한자 넷")
    a, b, _ = S2_다른문자("이것은 一期一會 라는 말입니다.", "'一期一會'의 뜻")
    맞다(not a, "S2a 질문에 있는 글자는 세지 않음")
    a, b, _ = S2_다른문자("한자 漢 하나만.", "")
    맞다(not a, "S2a 한 자는 아님")
    a, b, _ = S2_다른문자("```\n中文 代码\n```\n한국어 답", "")
    맞다(not a, "S2a 코드 블록 빼기")
    a, b, _ = S2_다른문자("This is all English with one 한 word.", "")
    맞다(b, "S2b 한글 50 % 미만")
    a, b, _ = S2_다른문자("α 와 β 의 합은 π 이다", "")
    맞다(not a and not b, "그리스 문자는 다른 문자 아님")
    a, b, _ = S2_다른문자("Привет 친구", "")
    맞다(a, "S2a 키릴")
    # S3 · S4
    s3, s4, x = S3_S4("so the answer is \\boxed{1,234}.", False, 1234.0)
    맞다(not s3 and not s4 and x == 1234.0, "boxed 쉼표")
    s3, s4, x = S3_S4("… \\boxed{\\$18}", False, 18.0)
    맞다(not s4, "boxed 달러")
    s3, s4, x = S3_S4("thinking … no box", True, 5.0)
    맞다(s3 and s4, "S3 은 S4")
    s3, s4, x = S3_S4("\\boxed{3} then \\boxed{4}", False, 4.0)
    맞다(not s4, "마지막 boxed")
    s3, s4, x = S3_S4("the answer is 42", False, 42.0, 마지막수로=True)
    맞다(not s4, "0.5B — 마지막 수")
    s3, s4, x = S3_S4("\\boxed{\\frac{1}{2}}", False, 0.5)
    맞다(not s4, "frac")
    맞다(정답수("blah\n#### 1,080") == 1080.0, "gsm8k 정답")
    # S6
    원 = "곽뙤순은 똬리를 이고 뙈기밭으로 엉금엉금 걸어갔다."
    s6, 옮김, _ = S6_맞춤법("네, 그대로 옮겨 쓰겠습니다:\n\n" + 원, 원)
    맞다(not s6 and 옮김, "S6 같음")
    s6, 옮김, _ = S6_맞춤법(원.replace("뙈기밭", "뙤기밭"), 원)
    맞다(s6 and 옮김, "S6 한 글자 다름")
    s6, 옮김, _ = S6_맞춤법("죄송하지만 이해하지 못했습니다.", 원)
    맞다(not s6 and not 옮김, "S6 옮기지 않음")
    s6, 옮김, _ = S6_맞춤법(원[:5] + "\ufffd" + 원[6:], 원)
    맞다(s6, "S6 깨진 글자")
    # S5
    맞다(S5_깨짐([1, 2], "  ", True), "S5 빈 답")
    맞다(not S5_깨짐([1, 2, 3, 4], "답", True), "S5 아님")
    # 글자 한가운데
    가 = "가".encode("utf-8")
    맞다(not 글자한가운데인가(bytearray(가)), "온전한 글자")
    맞다(글자한가운데인가(bytearray(가[:2])), "두 바이트 — 한가운데")
    맞다(글자한가운데인가(bytearray(b"a" + 가[:1])), "머리 바이트만")
    맞다(not 글자한가운데인가(bytearray(b"abc")), "ASCII")
    # 토큰 계통
    맞다(토큰계통("안녕".encode()) == "정상", "한글 정상")
    맞다(토큰계통("中".encode()) == "다른", "한자 다른")
    맞다(토큰계통("中".encode()[:2]) == "다른", "한자 조각(E4)")
    맞다(토큰계통("가".encode()[:1]) == "모름", "EA 하나만 — 모름(이 · 한글 둘 다 가능)")
    맞다(토큰계통("가".encode()[:2]) == "정상", "한글 조각 EA B0")
    맞다(토큰계통("나".encode()[:1]) == "정상", "한글 조각 EB")
    맞다(토큰계통("가".encode()[1:]) == "깨짐", "이어짐 바이트로 시작")
    맞다(토큰계통(b" the") == "정상", "라틴")
    맞다(토큰계통("の".encode()) == "다른", "가나")
    맞다(토큰계통("の".encode()[:2]) == "다른", "가나 조각 E3 81")
    맞다(토큰계통("、".encode()) == "정상", "CJK 문장부호는 글자 아님")
    맞다(토큰계통(b"") == "특수", "특수")
    # 위험한 걸음 — 작은 어휘로
    표 = [b"", "가".encode(), "中".encode(), "나".encode(), b"x", b"y", "가".encode()[:2], "가".encode()[2:], "각".encode()[2:]]
    특수 = {0}
    계통 = 계통표(표)
    # O: 1위 '가'(1), 2위 '中'(2) 여유 0.5
    r = 위험한걸음들_빠르게([1], [[1, 2, 3]], [[-0.5, -1.0, -3.0]], 표, 계통, 특수)
    맞다(r and r[0][1] == "O" and r[0][3] == 2 and abs(r[0][4] - 0.5) < 1e-12 and r[0][5] == 3, "O 걸음")
    r = 위험한걸음들_빠르게([1], [[1, 2, 3]], [[-0.1, -3.0, -3.5]], 표, 계통, 특수)
    맞다(not r, "여유 2.9 > ln10 — 위험하지 않음")
    # C: '가' 를 조각 6(앞 두 바이트) + 7(끝 바이트)로 — 둘째 걸음에서 8(다른 끝 바이트 → '각')이 2위
    r = 위험한걸음들_빠르게([6, 7], [[6, 1], [7, 8, 4]], [[-0.2, -2.0], [-0.3, -0.9, -4.0]], 표, 계통, 특수)
    맞다(any(x[1] == "C" and x[0] == 1 and x[3] == 8 for x in r), "C 걸음")
    # R: 8-묶음 베낌
    t = [4, 5, 4, 5, 4, 5, 4, 5, 4, 5, 4, 5, 4, 5, 4, 5, 4]
    상번 = [[x, 3] for x in t]
    상값 = [[-0.1, -0.5] for _ in t]
    r = 위험한걸음들_빠르게(t, 상번, 상값, 표, 계통, 특수, 유형들=("R",))
    맞다(not r, "1위가 베끼면 R 아님(이미 되풀이 중)")
    t2 = [4, 5, 3, 1, 4, 5, 3, 1, 4, 5, 3, 1, 4, 5, 3, 3]
    상번 = [[x, 3] for x in t2]
    상번[15] = [3, 1]
    상값 = [[-0.1, -0.5] for _ in t2]
    r = 위험한걸음들_빠르게(t2, 상번, 상값, 표, 계통, 특수, 유형들=("R",))
    맞다(any(x[1] == "R" and x[0] == 15 and x[3] == 1 for x in r), "R 걸음 — 2위가 앞선 8-묶음을 베낌")
    # 느린 판과 같다
    rng = np.random.default_rng(1)
    for _ in range(30):
        nn = int(rng.integers(5, 60))
        tt = [int(x) for x in rng.integers(1, 9, size=nn)]
        sb = [[tt[i]] + [int(x) for x in rng.permutation([y for y in range(1, 9) if y != tt[i]])[:4]] for i in range(nn)]
        sv = [sorted([float(-x) for x in rng.random(5) * 3], reverse=True) for _ in range(nn)]
        맞다(위험한걸음들(tt, sb, sv, 표, 계통, 특수) == 위험한걸음들_빠르게(tt, sb, sv, 표, 계통, 특수), "빠른 판 = 느린 판")
    # 기울기
    맞다(abs(기울기(-1.0, -1.2, -0.5, -0.9) - 0.2) < 1e-12, "Δ")
    맞다(기울기(None, -1, -1, -1) is None, "Δ 없음")
    # 통계
    맞다(abs(McNemar(10, 2) - 0.0386) < 1e-3, "McNemar 10:2")
    맞다(McNemar(5, 5) == 1.0, "McNemar 같음")
    맞다(McNemar(0, 0) == 1.0, "McNemar 0")
    h = Holm([0.01, 0.04, 0.03])
    맞다(abs(h[0] - 0.03) < 1e-12 and abs(h[2] - 0.06) < 1e-12 and abs(h[1] - 0.06) < 1e-12, "Holm")
    평균, 구간, p = 묶음붓스트랩([1.0, 2.0, 3.0, 2.0] * 50, [10] * 200, 번=2000)
    맞다(abs(평균 - 0.2) < 1e-12 and 구간[0] > 0 and p < 0.01, "붓스트랩 — 양수")
    평균, 구간, p = 묶음붓스트랩([1.0, -1.0] * 100, [10] * 200, 번=2000)
    맞다(abs(평균) < 1e-12 and p > 0.5, "붓스트랩 — 0")
    맞다(기울기판정(0.1, (0.05, 0.15), 0.001, 500) == "나쁜 쪽으로 기운다", "판정 나쁨")
    맞다(기울기판정(0.001, (-0.01, 0.012), 0.6, 500) == "기울지 않는다", "판정 기울지 않음")
    맞다(기울기판정(0.001, (-0.1, 0.12), 0.6, 500) == "판단 보류", "판정 보류(넓음)")
    맞다(기울기판정(0.3, (0.1, 0.5), 0.001, 100) == "판단 보류", "판정 보류(적음)")
    맞다(궤적판정(30, 10, 0.002) == "늘린다", "궤적 늘림")
    맞다(궤적판정(22, 20, 0.88) == "흔들지만 늘리지 않는다", "궤적 흔들림")
    맞다(궤적판정(10, 5, 0.3) == "판단 보류", "궤적 보류")
    # 쪼개진 음절 수
    표2 = ["가".encode()[:2], "가".encode()[2:], "나".encode()]
    맞다(쪼개진음절수([0, 1, 2], 표2) == (1, 2), "쪼개진 음절")
    print(f"단위 시험 {n} 개 통과")


if __name__ == "__main__":
    if "--시험" in sys.argv:
        _시험()
