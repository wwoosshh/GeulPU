#!/usr/bin/env python3
"""39b (2) · (3) — 채팅 틀 · 끝 토큰(문서/39단계.md).

  python -I 시험/틀39.py 준비 <gguf> <준비.json>
      GGUF 의 chat_template · bos_token · eos_token 과 대화 열둘(시스템 있음 · 없음, 한 차례 · 여러 차례, 앞뒤 공백 · 유니코드 공백).
      Mistral 틀에는 system 이 없어 맨 앞 system 말을 첫 user 말 앞에 '{system}\\n\\n' 으로 붙인 대화로 그린다(사용자 결정 — 서버와 같다).
  python3 시험/틀39.py 그리기 <준비.json> <그린.json>          (jinja2 가 있는 파이썬 — 이 PC 는 WSL 의 Ubuntu)
      Hugging Face transformers 의 apply_chat_template 과 같은 환경으로 그린다: ImmutableSandboxedEnvironment(trim_blocks · lstrip_blocks ·
      loopcontrols), raise_exception · strftime_now · tojson, render(messages, tools=None, documents=None, add_generation_prompt=True,
      bos_token, eos_token, date_string). 날짜는 서버의 기본 '26 Jul 2024'(대화 하나는 '16 Oct 2026' 을 chat_template_kwargs 로).
  python -I 시험/틀39.py 대조 <그린.json> <서버 주소> <gguf> <llama-b 폴더> <출력.json>
      (2) 대화마다 서버의 POST /tokenize {"messages", "chat_template_kwargs"} 가 그린 글의 llama.cpp 토큰(llama-tokenize — 특수 토큰
      알아봄 · --no-bos: 그린 글에 BOS 가 든다)과 같은가.
      (3) 끝 토큰: /tokenizer_info 의 eog_token_ids 가 llama.cpp 의 llama_vocab_is_eog(어휘 전부 — C API, 어휘만)와 같은 모음인가, 그리고
      채팅 셋의 생성(탐욕 · 최대 256 토큰)이 끝 토큰에서 멈추는가(finish_reason stop — 멈춤 글은 주지 않는다).
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, ".."))
날짜 = "26 Jul 2024"

대화들 = [
    ([{"role": "user", "content": "What is the capital of France?"}], None),
    ([{"role": "system", "content": "You are a concise assistant."}, {"role": "user", "content": "Name three primary colors."}], None),
    ([{"role": "user", "content": "Hi! My name is Mina."}, {"role": "assistant", "content": "Hello Mina! How can I help you today?"},
      {"role": "user", "content": "What is my name?"}], None),
    ([{"role": "system", "content": "Answer in Korean."}, {"role": "user", "content": "What is 2+2?"}, {"role": "assistant", "content": "4입니다."},
      {"role": "user", "content": "And 3+3?"}], None),
    ([{"role": "user", "content": "   leading and trailing spaces   "}], None),
    ([{"role": "system", "content": "  \n spaced system \n  "}, {"role": "user", "content": "\tTabbed question?\n"}], None),
    ([{"role": "user", "content": "안녕하세요? 오늘 날씨 어때요?"}], None),
    ([{"role": "user", "content": "Line one\nLine two\n\nLine four"}], None),
    ([{"role": "user", "content": "x"}, {"role": "assistant", "content": "  answer with spaces  "}, {"role": "user", "content": "y"}], None),
    ([{"role": "user", "content": "첫 질문 😀"}, {"role": "assistant", "content": "첫 답 👍"}, {"role": "user", "content": "Second, in English."},
      {"role": "assistant", "content": "Sure — here it is."}, {"role": "user", "content": "마지막: 1+1=?"}], None),
    ([{"role": "user", "content": " NBSP and ideographic space　"}], None),
    ([{"role": "system", "content": "Today is special."}, {"role": "user", "content": "What is today's date?"}], "16 Oct 2026"),
]
질문셋 = ["What is the capital of France? Answer in one word.", "대한민국의 수도는 어디야? 한 단어로 답해.", "Say hello in three languages."]


def 준비(gguf, 출력):
    sys.path.insert(0, os.path.join(ROOT, "엔진"))
    import gguf읽기 as GR                    # noqa: E402
    g = GR.GGUF(gguf)
    m = g.meta
    toks = m["tokenizer.ggml.tokens"]
    SP = m["tokenizer.ggml.model"] == "llama"
    out = []
    for i, (msgs, d) in enumerate(대화들):
        그릴 = msgs
        if SP and msgs[0]["role"] == "system":            # Mistral — '{system}\n\n' + 첫 user
            그릴 = [{"role": "user", "content": msgs[0]["content"] + "\n\n" + msgs[1]["content"]}] + msgs[2:]
        out.append({"번호": i, "messages": msgs, "그릴 messages": 그릴, "date_string": d or 날짜, "kwargs": ({"date_string": d} if d else None)})
    with open(출력, "w", encoding="utf-8") as f:
        json.dump({"gguf": os.path.basename(gguf), "chat_template": m["tokenizer.chat_template"],
                   "bos_token": toks[m["tokenizer.ggml.bos_token_id"]], "eos_token": toks[m["tokenizer.ggml.eos_token_id"]],
                   "SentencePiece": SP, "대화": out}, f, ensure_ascii=False, indent=1)
    print("준비", len(out), "대화 →", 출력)


def 그리기(준비경로, 출력):
    import datetime
    import jinja2
    import jinja2.ext
    import jinja2.sandbox
    j = json.load(open(준비경로, encoding="utf-8"))

    def raise_exception(message):
        raise jinja2.exceptions.TemplateError(message)

    def tojson(x, ensure_ascii=False, indent=None, separators=None, sort_keys=False):
        return json.dumps(x, ensure_ascii=ensure_ascii, indent=indent, separators=separators, sort_keys=sort_keys)

    def strftime_now(format):
        return datetime.datetime.now().strftime(format)

    env = jinja2.sandbox.ImmutableSandboxedEnvironment(trim_blocks=True, lstrip_blocks=True, extensions=[jinja2.ext.loopcontrols])
    env.filters["tojson"] = tojson
    env.globals["raise_exception"] = raise_exception
    env.globals["strftime_now"] = strftime_now
    틀 = env.from_string(j["chat_template"])
    for c in j["대화"]:
        c["그린 글"] = 틀.render(messages=c["그릴 messages"], tools=None, documents=None, add_generation_prompt=True,
                             bos_token=j["bos_token"], eos_token=j["eos_token"], date_string=c["date_string"])
    j["jinja2"] = jinja2.__version__
    with open(출력, "w", encoding="utf-8") as f:
        json.dump(j, f, ensure_ascii=False, indent=1)
    print("그림", len(j["대화"]), "대화 · jinja2", jinja2.__version__, "→", 출력)


def 대조(그린경로, 주소, gguf, 판폴더, 출력):
    import subprocess
    import tempfile
    import urllib.error
    import urllib.request
    sys.path.insert(0, HERE)
    import 토크나이저39 as T39                # noqa: E402 — _라마토큰 · 라마어휘

    def 요청(길, 몸):
        req = urllib.request.Request(주소 + 길, data=json.dumps(몸, ensure_ascii=False).encode("utf-8"),
                                     headers={"Content-Type": "application/json; charset=utf-8"})
        try:
            with urllib.request.urlopen(req, timeout=600) as r:
                return json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            return {"오류": e.code, "몸": e.read().decode("utf-8", "replace")}

    j = json.load(open(그린경로, encoding="utf-8"))
    도구 = os.path.join(판폴더, "llama-tokenize.exe")
    결과, 다름 = [], 0
    with tempfile.TemporaryDirectory(prefix="tmpl39_") as 폴더:
        for c in j["대화"]:
            l, 오류 = T39._라마토큰(도구, gguf, c["그린 글"], 폴더, c["번호"])
            몸 = {"messages": c["messages"]}
            if c["kwargs"]:
                몸["chat_template_kwargs"] = c["kwargs"]
            r = 요청("/tokenize", 몸)
            g = r.get("tokens")
            같음 = l is not None and l == g
            다름 += not 같음
            한 = {"번호": c["번호"], "같음": 같음, "토큰 수": len(g) if g else None}
            if not 같음:
                한.update({"그린 글": c["그린 글"], "llama.cpp": l, "글(geul)": g, "서버": r if g is None else None, "오류": 오류})
            결과.append(한)
    # (3) 끝 토큰 — 모음 · 생성
    정보 = json.loads(urllib.request.urlopen(주소 + "/tokenizer_info", timeout=30).read().decode("utf-8"))
    어휘 = T39.라마어휘(판폴더, gguf)
    import ctypes
    L = 어휘.L
    L.llama_vocab_is_eog.restype = ctypes.c_bool
    L.llama_vocab_is_eog.argtypes = [ctypes.c_void_p, ctypes.c_int32]
    L.llama_vocab_n_tokens.restype = ctypes.c_int32
    L.llama_vocab_n_tokens.argtypes = [ctypes.c_void_p]
    n = L.llama_vocab_n_tokens(어휘.vocab)
    라마끝 = sorted(t for t in range(n) if L.llama_vocab_is_eog(어휘.vocab, t))
    글끝 = sorted(정보["eog_token_ids"])
    생성 = []
    for q in 질문셋:
        r = 요청("/v1/chat/completions", {"messages": [{"role": "user", "content": q}], "max_tokens": 256, "temperature": 0,
                                         "geulpu": {"prompt_tokens": True}})
        ch = (r.get("choices") or [{}])[0]
        생성.append({"질문": q, "finish_reason": ch.get("finish_reason"), "답": (ch.get("message") or {}).get("content"),
                   "생성 토큰": (r.get("usage") or {}).get("completion_tokens"), "오류": r.get("오류")})
    멈춤 = all(x["finish_reason"] == "stop" for x in 생성)
    요약 = {"gguf": os.path.basename(gguf), "jinja2": j.get("jinja2"), "대화": len(결과), "다른 대화": 다름,
          "끝 토큰(글)": 글끝, "끝 토큰(llama.cpp llama_vocab_is_eog)": 라마끝, "끝 토큰 모음 같음": 글끝 == 라마끝,
          "생성이 끝 토큰에서 멈춤": 멈춤, "llama.cpp 판": os.path.basename(판폴더.rstrip("/\\"))}
    with open(출력, "w", encoding="utf-8") as f:
        json.dump({"요약": 요약, "대화": 결과, "생성": 생성}, f, ensure_ascii=False, indent=1)
    print(json.dumps(요약, ensure_ascii=False))
    print("39b(2)", os.path.basename(gguf), "— 틀", "모두 같음" if 다름 == 0 else f"다른 대화 {다름}",
          "· 39b(3) 끝 토큰", "같음" if 글끝 == 라마끝 else "다름", "· 멈춤", "모두" if 멈춤 else "아님")


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    op = sys.argv[1]
    if op == "준비":
        준비(sys.argv[2], sys.argv[3])
    elif op == "그리기":
        그리기(sys.argv[2], sys.argv[3])
    elif op == "대조":
        대조(*sys.argv[2:7])
    else:
        print(__doc__)


if __name__ == "__main__":
    main()
