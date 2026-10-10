"""Qwen2 토크나이저(엔진/토크나이저.py)가 Hugging Face tokenizers(tokenizer.json — 같은 모델 폴더)와 같은 토큰 · 같은 글을 내는가.
transformers 가 있어야 한다(시험만). 인자: 모델 폴더(기본 모델/qwen2.5-0.5b-instruct) [무작위 수]"""
import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.stderr.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, ".."))
sys.path.insert(0, os.path.join(ROOT, "엔진"))
import numpy as np                 # noqa: E402
import 토크나이저 as TK            # noqa: E402

폴더 = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "모델", "qwen2.5-0.5b-instruct")
무작위수 = int(sys.argv[2]) if len(sys.argv) > 2 else 3000
from transformers import AutoTokenizer      # noqa: E402
hf = AutoTokenizer.from_pretrained(폴더)
글 = TK.Qwen토크나이저(폴더)

예 = [open(os.path.join(HERE, "평가글.txt"), encoding="utf-8").read(),
     "안녕하세요! 오늘은 2026년 10월 10일입니다. GPU 계산에서 의미를 잃지 않는 컴파일러를 만들고 있어요.",
     "def f(x):\n    return x ** 2  # 제곱\n\n\nfor i in range(10):\n\tprint(f(i))\r\n",
     "1234567890 3.14159 -42 1e-10 ½ ① Ⅻ ٣ 〇",
     "  leading and trailing  \n\n  \n   ", "a  b   c    d\n\ne", " \n hello", "\t\tx", "x 　 y", "a\x1cb\x1fc",
     "<|im_start|>system\nYou are Qwen.<|im_end|>\n<|im_start|>user\n안녕<|im_end|>\n<|im_start|>assistant\n",
     "don't I'LL we've they're it's He'D 'S 'Re",
     "😀👍🏽 🇰🇷 नमस्ते مرحبا 你好世界 こんにちは Ünïcödé café naïve",
     "é é́ 각 (NFC 대상)", "!!!...??\n\n", "(hello) [world] {x}", "https://example.com/a?b=1&c=2"]
rng = np.random.default_rng(14)
범위 = [(0x20, 0x7f), (0xa0, 0x250), (0x370, 0x400), (0x400, 0x500), (0x600, 0x700), (0x900, 0x980), (0x3040, 0x3100), (0x4e00, 0x4f00),
        (0xac00, 0xad00), (0x1100, 0x1200), (0x2000, 0x2070), (0x1f300, 0x1f650), (0x9, 0xe), (0x300, 0x370)]
for _ in range(무작위수):
    n = int(rng.integers(1, 40))
    s = []
    for _ in range(n):
        a, b = 범위[int(rng.integers(0, len(범위)))]
        s.append(chr(int(rng.integers(a, b))))
    예.append("".join(s))
틀림 = 0
for s in 예:
    a = 글.나누기(s)
    b = hf.encode(s, add_special_tokens=False)
    if a != b:
        틀림 += 1
        if 틀림 <= 5:
            print("다름:", repr(s[:80]), "\n  글", a[:30], "\n  HF", b[:30])
    elif 글.잇기(a) != hf.decode(b, skip_special_tokens=False, clean_up_tokenization_spaces=False):
        틀림 += 1
        if 틀림 <= 5:
            print("잇기 다름:", repr(s[:80]))
채팅 = TK.채팅틀([{"role": "user", "content": "안녕? 너는 누구야?"}])
hf채팅 = hf.apply_chat_template([{"role": "user", "content": "안녕? 너는 누구야?"}], tokenize=False, add_generation_prompt=True)
print("채팅 틀 같음:", 채팅 == hf채팅)
print(f"{len(예)} 가지 중 다른 것 {틀림}", "— 모두 같다" if 틀림 == 0 and 채팅 == hf채팅 else "")
sys.exit(0 if 틀림 == 0 and 채팅 == hf채팅 else 1)
