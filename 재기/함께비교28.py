"""같은 탐욕 요청을 혼자 · 다른 요청과 함께 보내 답이 같은지 — OpenAI 꼴 서버(흘려보내지 않음). 표준 라이브러리만.
    python -I 재기/함께비교28.py --주소 127.0.0.1:8091 [--생성 256]
"""
import argparse, http.client, json, sys, threading, io, hashlib

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
주제 = ["a lighthouse keeper who finds a map", "a robot learning to paint", "two rival chefs in a small town",
      "a lost cat crossing a city", "an astronaut stranded on the moon", "a librarian who can read minds",
      "a child who builds a boat", "a detective in a city of glass"]


def 묻기(주소, 글, 생성):
    host, port = 주소.split(":")
    c = http.client.HTTPConnection(host, int(port), timeout=600)
    몸 = {"model": "m", "temperature": 0, "max_tokens": 생성, "ignore_eos": True, "cache_prompt": False,
         "messages": [{"role": "user", "content": 글}]}
    c.request("POST", "/v1/chat/completions", body=json.dumps(몸).encode("utf-8"), headers={"Content-Type": "application/json"})
    d = json.loads(c.getresponse().read())
    c.close()
    return d["choices"][0]["message"]["content"]


def 함께(주소, 글들, 생성):
    out = [None] * len(글들)
    def 일(i):
        out[i] = 묻기(주소, 글들[i], 생성)
    ts = [threading.Thread(target=일, args=(i,)) for i in range(len(글들))]
    for t in ts:
        t.start()
    for t in ts:
        t.join()
    return out


def 첫다름(a, b):
    for i, (x, y) in enumerate(zip(a, b)):
        if x != y:
            return i
    return None if len(a) == len(b) else min(len(a), len(b))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--주소", default="127.0.0.1:8091")
    ap.add_argument("--생성", type=int, default=256)
    a = ap.parse_args()
    결과 = {}
    for k in range(4):
        X = f"Write a long story about {주제[k]}."
        혼자 = [묻기(a.주소, X, a.생성) for _ in range(2)]
        둘 = 함께(a.주소, [X, f"Write a long story about {주제[4]}."], a.생성)[0]
        넷 = 함께(a.주소, [X] + [f"Write a long story about {주제[j]}." for j in (5, 6, 7)], a.생성)[0]
        넷뒤 = 함께(a.주소, [f"Write a long story about {주제[j]}." for j in (5, 6, 7)] + [X], a.생성)[3]
        h = lambda s: hashlib.sha256(s.encode("utf-8")).hexdigest()[:12]
        줄 = {"혼자1": h(혼자[0]), "혼자2": h(혼자[1]), "둘": h(둘), "넷": h(넷), "넷뒤": h(넷뒤),
             "첫다름_둘": 첫다름(혼자[0], 둘), "첫다름_넷": 첫다름(혼자[0], 넷), "첫다름_넷뒤": 첫다름(혼자[0], 넷뒤)}
        결과[k] = 줄
        print(k, 줄, flush=True)


if __name__ == "__main__":
    main()
