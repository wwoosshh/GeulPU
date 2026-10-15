#!/usr/bin/env python3
"""39b (1) — 토크나이저: 글(geul) 서버의 /tokenize · /detokenize 가 llama.cpp 와 같은가(문서/39단계.md).

  python -I 시험/토크나이저39.py 글묶음 <출력.json>
      글 묶음 2,000 줄을 짓는다 — 저장소의 한국어 · 영어 문서와 코드 줄 1,700(정한 파일에서 고른 간격으로) + 만든 줄 300(숫자 · 공백 ·
      이모지 · 섞인 글 · 특수 토큰 글 · 무작위 유니코드). 한 번 지어 시험/토크나이저39글.json 으로 둔다(문서가 바뀌어도 묶음은 그대로).

  python -I 시험/토크나이저39.py 대조 <글묶음.json> <서버 주소> <gguf> <llama-b 폴더> <출력.json> [--일꾼 8]
      줄마다: 토큰 — 서버의 POST /tokenize {"prompt": 줄, "add_special_tokens": false} 와 llama.cpp 의 llama-tokenize(같은 GGUF ·
      특수 토큰 알아봄 · --no-bos · 바이트 그대로 -bf — 읽은 바이트 수를 확인하고 아니면 다시)가 같은가.
      되돌리기 — POST /detokenize(글의 토큰): 바이트 BPE(Llama 3)는 원문과 같은가(글(geul)은 llama.cpp 의 clean_up_tokenization_spaces 를
      하지 않는다 — 잃지 않는 되돌리기). SentencePiece(Mistral)는 llama.cpp 의 llama_detokenize(C API, 어휘만 — remove_special 거짓 ·
      unparse_special 참)와 같은가 — 원문과는 두 곳에서 다를 수 있다(llama.cpp 도 같다): 특수 토큰 뒤의 글 조각 앞에 공백이 붙고
      (is_prev_special), 원문의 '▁'(U+2581)은 공백으로 돌아온다. 원문과 같은 줄 수도 적는다. 서버는 따로 띄운다(공식실행/공식39.sh).
"""
import ctypes
import json
import os
import re
import struct
import subprocess
import sys
import tempfile
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, ".."))

# ---- 글 묶음 ----
문서들 = ["README.md", "README.en.md", "연구자안내.md", "docs/research-guide.md", "문서/계약.md", "docs/contract.md"]
코드들 = ["호스트/토크나이저.gl", "호스트/서버몸.gl", "커널/커널생성.gl", "시험/참조7B.py", "앱/web/app.js"]


def _줄들(경로):
    with open(os.path.join(ROOT, 경로), encoding="utf-8") as f:
        return [l.rstrip("\r\n") for l in f.read().split("\n")]


def _고르기(줄들, n):
    """빈 줄 · 겹친 줄을 뺀 뒤 고른 간격으로 n 개."""
    본, 있음 = [], set()
    for l in 줄들:
        if l.strip() and l not in 있음:
            있음.add(l)
            본.append(l)
    if len(본) <= n:
        return 본
    return [본[i * len(본) // n] for i in range(n)]


def _만든줄():
    import numpy as np
    r = np.random.default_rng(39)
    숫자 = ["0", "7", "42", "123", "1234", "12345", "123456", "1234567", "12345678901234567890", "3.14159", "-42", "+7", "1e-10", "6.02e23",
           "1,234,567", "1.234.567,89", "0x1F", "0b1010", "007", "2026-10-16", "12:34:56", "v0.5.0", "192.168.0.1", "010-1234-5678",
           "₩1,000", "$3.50", "50%", "1/2", "3×4=12", "２０２６", "١٢٣٤", "०१२३", "①②③", "½ ¾ ⅓", "Ⅻ ⅳ", "〇一二三", "𝟏𝟐𝟑", "99.9%",
           "a1b22c333d4444", "x=1234567;y=89"]
    공백 = ["", " ", "  ", "   ", "\t", " \t ", "\t\t", "a  b", "a   b", "a    b", "  앞 공백", "뒤 공백  ", " 앞뒤 ", "\n", "\n\n", "\n\n\n",
           "a\nb", "a\r\nb", "\r", "\r\n", "x \n y", "  \n  ", "a\n\n\nb", "\u00a0nbsp\u00a0", "\u3000전각 공백\u3000", "\u2003em\u2002en",
           "zero\u200bwidth", "a\u2028b\u2029c", "\x0bvt\x0cff", "a\x1cb\x1fc", "tab\tin\tline", "끝에 줄바꿈\n", "\n앞에 줄바꿈",
           " \n", "\n ", "공백 \t\n 섞임", "  \r\n  ", "x\u0085y", "\u205f수학 공백", "\u1680ogham"]
    이모지 = ["😀", "👍🏽", "👨‍👩‍👧‍👦", "🇰🇷🇺🇸🇯🇵", "❤️", "🏳️‍🌈", "emoji 😀 in text", "안녕 👋 반가워", "🤖🧠💡", "1️⃣2️⃣3️⃣",
            "☕️ coffee", "🚀🚀🚀", "👩🏻‍💻 개발자", "🙂🙃", "✨ 새 기능 ✨", "⚠️ 주의", "✅ ❌", "🔥", "😂🤣", "🇺🇳",
            "👨‍❤️‍👨", "🧑‍🔬 연구", "📊 그래프", "🎉 축하", "😀😀😀😀😀😀😀😀", "a😀b😀c", "😀\n😀", " 😀 ", "🫠", "🪐"]
    섞인 = ["café naïve résumé", "cafe\u0301 nai\u0308ve", "한국어와 English 섞기", "日本語のテキスト", "中文文本测试", "Русский текст",
           "Ελληνικά", "العربية نص", "עברית", "हिन्दी पाठ", "ภาษาไทย", "Tiếng Việt có dấu", "Türkçe ğüşıöç", "Ünïcödé Ⓐⓑⓒ",
           "\u1100\u1161\u11a8 첫가끝", "한\u0300글", "Ǆ ǅ ǆ", "ﬁ ﬂ ﬀ", "Ａｂｃ 全角", "ｱｲｳ 반각", "ⓐⓑⓒ", "x² + y² = z²",
           "∀x ∈ ℝ: x² ≥ 0", "f(x) → ∞", "α β γ δ", "naïve × ÷", "© ® ™", "«quotes» „German“ ‚x‘", "‘single’ “double”",
           "…ellipsis… — em-dash – en-dash", "don't I'LL we've they're it's He'D 'S 'Re", "rock'n'roll", "o'clock", "'s alone",
           "Mixed 한글123English!", "URL https://example.com/a?b=1&c=2#x", "path C:\\Users\\name\\file.txt", "email a.b@example.co.kr",
           "<html><body>태그</body></html>", "{\"json\": [1, 2, 3]}", "def f(x):\n    return x ** 2  # 제곱", "SELECT * FROM t WHERE x > 1;",
           "$$\\frac{a}{b}$$", "a_b-c.d/e", "camelCaseWord snake_case_word", "ALLCAPS WORDS", "MiXeD CaSe",
           "!!!...???", "(괄호) [대괄호] {중괄호}", "@#$%^&*", "~`|\\", "—––", "。、「」", "，。！？", "‼⁉", "¿Qué? ¡Sí!",
           "Ⅰ Ⅱ Ⅲ", "㈜ ㉿", "𝓗𝓮𝓵𝓵𝓸", "Z̤͔ͧ̑a̴lgo", "a\u0301\u0302\u0303", "한국어 문장입니다. 마침표로 끝납니다.", "물음표로 끝나요?"]
    특수 = ["<|begin_of_text|>", "<|end_of_text|>", "<|eot_id|>", "<|eom_id|>", "<|start_header_id|>user<|end_header_id|>",
           "<|reserved_special_token_5|>", "<|python_tag|>", "<|finetune_right_pad_id|>", "<|eot_id", "|eot_id|>", "<|EOT_ID|>", "< |eot_id|>",
           "a<|eot_id|>b", "<|eot_id|><|eot_id|>", " <|eot_id|> ", "끝<|eot_id|>\n다음", "<s>", "</s>", "<unk>", "<s>x</s>", "<s><s>",
           " <s> ", "[INST]", "[/INST]", "[INST] hi [/INST]", "[INST][/INST]", "a [INST] b [/INST] c", "[TOOL_CALLS]", "[AVAILABLE_TOOLS]",
           "[control_8]", "<0x41>", "<0xFF>", "▁", "▁▁", "▁word", "<|im_start|>user\nhi<|im_end|>", "<|endoftext|>", "<think></think>",
           "[INST", "INST]", "<s", "/s>", "<|begin_of_text|>Hello", "Hello<|end_of_text|>", "<|start_header_id|>", "<|end_header_id|>\n\n",
           "<|begin_of_text|><|start_header_id|>system<|end_header_id|>\n\n<|eot_id|>", "<s>[INST] 질문 [/INST]답</s>", "[/INST]  공백",
           "\n[INST]\n", "\t</s>\t", "<|eot_id|>😀<|eom_id|>", "[INST]한글[/INST]", "x</s>y</s>z", "<<SYS>>\n시스템\n<</SYS>>", "<|eot_id|>\n"]
    무작위 = []
    구간 = [(0x20, 0x7f), (0xa0, 0x250), (0x370, 0x530), (0x600, 0x700), (0x900, 0x980), (0xe00, 0xe80), (0x1100, 0x1200),
           (0x2000, 0x2070), (0x2190, 0x2300), (0x3040, 0x3100), (0x4e00, 0x4f00), (0xac00, 0xd7a4), (0xff00, 0xffef), (0x1f300, 0x1f650)]
    while len(무작위) < 300 - len(숫자) - len(공백) - len(이모지) - len(섞인) - len(특수):
        n = int(r.integers(1, 40))
        글 = []
        for _ in range(n):
            a, b = 구간[int(r.integers(0, len(구간)))]
            c = int(r.integers(a, b))
            if 0xd800 <= c <= 0xdfff:
                continue
            글.append(chr(c))
            if r.random() < 0.15:
                글.append(" ")
        무작위.append("".join(글))
    return [("숫자", x) for x in 숫자] + [("공백", x) for x in 공백] + [("이모지", x) for x in 이모지] + [("섞인 글", x) for x in 섞인] + \
        [("특수 토큰 글", x) for x in 특수] + [("무작위", x) for x in 무작위]


def 글묶음(출력):
    줄 = []
    for p in 문서들:
        줄 += [("문서 " + p, l) for l in _고르기(_줄들(p), 150)]
    for p in 코드들:
        줄 += [("코드 " + p, l) for l in _고르기(_줄들(p), 160)]
    만든 = _만든줄()
    assert len(만든) == 300, len(만든)
    줄 += 만든
    assert len(줄) == 1700 + 300, len(줄)
    for 종류, l in 줄:
        assert "\x00" not in l and not any(0xd800 <= ord(c) <= 0xdfff for c in l), (종류, l)
    with open(출력, "w", encoding="utf-8") as f:
        json.dump({"설명": "39b(1) 글 묶음 — 저장소의 문서 · 코드 줄 1,700 + 만든 줄 300(시험/토크나이저39.py 글묶음)",
                   "줄": [{"종류": k, "글": l} for k, l in 줄]}, f, ensure_ascii=False, indent=0)
    print("글 묶음", len(줄), "줄 →", 출력)


# ---- 대조 ----
def _요청(주소, 길, 몸):
    req = urllib.request.Request(주소 + 길, data=json.dumps(몸, ensure_ascii=False).encode("utf-8"),
                                 headers={"Content-Type": "application/json; charset=utf-8"})
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.loads(r.read().decode("utf-8"))


def _라마토큰(도구, gguf, 글, 폴더, i):
    """llama-tokenize 한 번 — 나란히 돌리면 드물게 파일을 빈 것으로 읽는다(받은 바이트 수가 stderr 의 'Read N bytes' 에 있다): 수가 다르면
    다시(다섯 번까지)."""
    b = 글.encode("utf-8")
    p = os.path.join(폴더, f"line{i}.txt")             # llama.cpp 는 한글 경로를 열지 못한다 — 작업 폴더는 ASCII
    오류 = ""
    for 번 in range(5):
        with open(p, "wb") as f:
            f.write(b)
        r = subprocess.run([도구, "-m", gguf, "-bf", p, "--ids", "--log-disable", "--no-escape", "--no-bos"],
                           capture_output=True, text=True, encoding="utf-8", errors="replace")
        os.remove(p)
        읽음 = re.search(r"Read (\d+) bytes from binary file", r.stderr)
        t = r.stdout.strip()
        if r.returncode == 0 and 읽음 and int(읽음.group(1)) == len(b) and t:
            return json.loads(t.splitlines()[-1]), ("" if 번 == 0 else f"다시 {번}")
        오류 = f"종료 {r.returncode} · 읽음 {읽음.group(1) if 읽음 else '?'} / {len(b)} · {r.stderr[-200:]}"
        time.sleep(0.2)
    return None, 오류


class 라마어휘:
    """llama.cpp 의 C API(어휘만 — vocab_only)로 llama_detokenize. 재기/라마.py 의 DLL 부르기를 쓴다(GEULPU_LLAMA = 판 폴더)."""

    def __init__(self, 판폴더, gguf):
        os.environ["GEULPU_LLAMA"] = 판폴더
        sys.path.insert(0, os.path.join(ROOT, "재기"))
        import 라마 as LM                      # noqa: E402
        L, _ = LM._불러오기(True)
        c_p = ctypes.c_void_p
        L.llama_model_default_params.restype = c_p
        L.llama_model_default_params.argtypes = [c_p]
        L.llama_model_load_from_file.restype = c_p
        L.llama_model_load_from_file.argtypes = [ctypes.c_char_p, c_p]
        L.llama_model_get_vocab.restype = c_p
        L.llama_model_get_vocab.argtypes = [c_p]
        L.llama_detokenize.restype = ctypes.c_int32
        L.llama_detokenize.argtypes = [c_p, ctypes.POINTER(ctypes.c_int32), ctypes.c_int32, ctypes.c_char_p, ctypes.c_int32,
                                       ctypes.c_bool, ctypes.c_bool]
        mp = ctypes.create_string_buffer(256)
        L.llama_model_default_params(mp)
        # b11669 의 llama_model_params: … kv_overrides 64, 참거짓 여섯 72 … 77(vocab_only · check_tensors · use_extra_bufts · …)
        assert mp.raw[72:78] == bytes([0, 0, 1, 0, 0, 0]), f"llama_model_params 의 참거짓 칸이 예상과 다르다: {mp.raw[64:80].hex()}"
        struct.pack_into("<B", mp, 72, 1)
        self.L = L
        self.model = L.llama_model_load_from_file(gguf.encode("utf-8"), mp)
        assert self.model, "llama.cpp 가 어휘를 읽지 못했다"
        self.vocab = L.llama_model_get_vocab(self.model)

    def 되돌리기(self, ids):
        a = (ctypes.c_int32 * max(1, len(ids)))(*ids)
        n = 4096 + 32 * len(ids)
        buf = ctypes.create_string_buffer(n)
        k = self.L.llama_detokenize(self.vocab, a, len(ids), buf, n, False, True)
        assert k >= 0, k
        return buf.raw[:k].decode("utf-8", errors="replace")


def 대조(묶음경로, 주소, gguf, 판폴더, 출력, 일꾼):
    줄들 = json.load(open(묶음경로, encoding="utf-8"))["줄"]
    도구 = os.path.join(판폴더, "llama-tokenize.exe")
    정보 = json.loads(urllib.request.urlopen(주소 + "/tokenizer_info", timeout=30).read().decode("utf-8"))
    t0 = time.time()
    글토큰, 글되돌림 = [], []
    for x in 줄들:
        글토큰.append(_요청(주소, "/tokenize", {"prompt": x["글"], "add_special_tokens": False})["tokens"])
    for ids in 글토큰:
        글되돌림.append(_요청(주소, "/detokenize", {"tokens": ids})["prompt"])
    t1 = time.time()
    with tempfile.TemporaryDirectory(prefix="tok39_", dir=os.environ.get("TOK39_TMP")) as 폴더:
        with ThreadPoolExecutor(일꾼) as ex:
            라마 = list(ex.map(lambda ix: _라마토큰(도구, gguf, ix[1]["글"], 폴더, ix[0]), enumerate(줄들)))
    t2 = time.time()
    sys.path.insert(0, os.path.join(ROOT, "엔진"))
    import gguf읽기 as GR                               # noqa: E402
    g = GR.GGUF(gguf)
    SP = g.meta["tokenizer.ggml.model"] == "llama"      # SentencePiece(Mistral)
    종류 = g.meta["tokenizer.ggml.token_type"]
    어휘 = 라마어휘(판폴더, gguf) if SP else None
    결과, 다른토큰, 다른되돌림, 실패, 다시 = [], 0, 0, 0, 0
    원문같음, 특수줄, 막대줄 = 0, 0, 0
    for i, x in enumerate(줄들):
        l, 오류 = 라마[i]
        if 오류.startswith("다시"):
            다시 += 1
        같은토큰 = l == 글토큰[i]
        특수든 = any(종류[t] in (2, 3, 4) for t in 글토큰[i])      # 글의 토큰에 특수(모름 · 제어 · 사용자 정의) 토큰이 있다
        기준 = x["글"]
        기준꼴 = "원문"
        if SP:
            기준 = 어휘.되돌리기(글토큰[i])
            기준꼴 = "llama_detokenize"
            특수줄 += 특수든
            막대줄 += "\u2581" in x["글"]
        같은되돌림 = 글되돌림[i] == 기준
        원문같음 += 글되돌림[i] == x["글"]
        if l is None:
            실패 += 1
        if not 같은토큰:
            다른토큰 += 1
        if not 같은되돌림:
            다른되돌림 += 1
        한 = {"번호": i, "종류": x["종류"], "같은 토큰": 같은토큰, "같은 되돌림": 같은되돌림, "되돌림 기준": 기준꼴, "토큰 수": len(글토큰[i]),
             "원문과 같음": 글되돌림[i] == x["글"]}
        if 오류:
            한["llama-tokenize"] = 오류
        if not 같은토큰 or not 같은되돌림:
            한.update({"글": x["글"], "llama.cpp": l, "글(geul)": 글토큰[i], "되돌림": 글되돌림[i], "기준": 기준, "오류": 오류})
        결과.append(한)
    요약 = {"gguf": os.path.basename(gguf), "줄": len(줄들), "다른 토큰 줄": 다른토큰, "다른 되돌림 줄": 다른되돌림, "llama-tokenize 실패": 실패,
          "llama-tokenize 다시 읽은 줄": 다시, "토큰 합": sum(len(t) for t in 글토큰), "SentencePiece": SP,
          "되돌리기 기준": "llama_detokenize" if SP else "원문", "되돌리기가 원문과 같은 줄": 원문같음,
          "특수 토큰이 든 줄(SentencePiece)": 특수줄 if SP else None, "원문에 '▁' 가 든 줄(SentencePiece)": 막대줄 if SP else None,
          "글 초": round(t1 - t0, 1), "llama.cpp 초": round(t2 - t1, 1), "llama.cpp 판": os.path.basename(판폴더.rstrip("/\\"))}
    with open(출력, "w", encoding="utf-8") as f:
        json.dump({"요약": 요약, "줄": 결과}, f, ensure_ascii=False, indent=1)
    print(json.dumps(요약, ensure_ascii=False))
    print("39b(1)", os.path.basename(gguf), "— 토큰", "모두 같음" if 다른토큰 == 0 and 실패 == 0 else f"다른 줄 {다른토큰} · 실패 {실패}",
          "· 되돌리기", "모두 같음" if 다른되돌림 == 0 else f"다른 줄 {다른되돌림}")


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    if sys.argv[1] == "글묶음":
        글묶음(sys.argv[2])
    elif sys.argv[1] == "대조":
        일꾼 = int(sys.argv[sys.argv.index("--일꾼") + 1]) if "--일꾼" in sys.argv else 8
        a = [x for x in sys.argv[2:] if not x.startswith("--")]
        if "--일꾼" in sys.argv:
            a.remove(str(일꾼))
        대조(a[0], a[1], a[2], a[3], a[4], 일꾼)
    else:
        print(__doc__)


if __name__ == "__main__":
    main()
