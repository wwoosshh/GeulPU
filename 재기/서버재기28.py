"""OpenAI 꼴 서버(/v1/chat/completions, 흘려보내기)에 동시 요청 K 개를 보내 토큰이 오는 시각을 잰다 — 표준 라이브러리만.

    python -I 재기/서버재기28.py --주소 127.0.0.1:8091 --동시 1,2,4 --생성 256 [--되풀이 3] [--출력 결과.json]
    python -I 재기/서버재기28.py --주소 … --첫토큰 [--막기] [--출력 결과.json]      (긴 대화(약 2,000 토큰)의 첫 토큰까지 — 캐시 끔 · 같은 프롬프트 · 다음 차례)

--막기(30단계): 첫 토큰을 막는 소켓(timeout 없음)으로 잰다. timeout 을 둔 소켓은 윈도에서 connect 가 select 로 기다려 요청의 절반쯤에서
10 ~ 25 ms 가 붙었다(30단계 진단 — 서버와 상관없는 클라이언트 쪽의 흔들림).

요청마다 다른 프롬프트(이야기 주제), 탐욕(temperature 0), ignore_eos(끝 토큰을 무시 — llama.cpp 의 덧붙임)로 생성 수를 같게.
동시 K 의 '모두 도는 구간'(가장 늦게 첫 토큰을 받은 때 ~ 가장 먼저 끝난 때)에 받은 토큰 수 / 구간 길이 = 합 처리량(토큰/초),
스트림마다 토큰 사이 간격의 가운데 값 = 걸음 시간.
"""
import argparse, http.client, json, statistics, sys, threading, time, io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

주제 = ["a lighthouse keeper who finds a map", "a robot learning to paint", "two rival chefs in a small town",
      "a lost cat crossing a city", "an astronaut stranded on the moon", "a librarian who can read minds",
      "a child who builds a boat", "a detective in a city of glass"]


def 요청하나(주소, 몸, 결과, i, 시작신호):
    host, port = 주소.split(":")
    c = http.client.HTTPConnection(host, int(port), timeout=600)
    본문 = json.dumps(몸).encode("utf-8")
    시작신호.wait()
    t0 = time.perf_counter()
    c.request("POST", "/v1/chat/completions", body=본문, headers={"Content-Type": "application/json"})
    r = c.getresponse()
    시각 = []
    마지막 = None
    글 = []
    버퍼 = b""
    while True:
        조각 = r.read1(65536) if hasattr(r, "read1") else r.read(1)
        if not 조각:
            break
        버퍼 += 조각
        while b"\n\n" in 버퍼:
            사건, 버퍼 = 버퍼.split(b"\n\n", 1)
            for 줄 in 사건.split(b"\n"):
                if not 줄.startswith(b"data:"):
                    continue
                자료 = 줄[5:].strip()
                if 자료 == b"[DONE]":
                    continue
                d = json.loads(자료)
                마지막 = d
                ch = d.get("choices") or []
                if ch and ch[0].get("delta", {}).get("content"):
                    시각.append(time.perf_counter())
                    글.append(ch[0]["delta"]["content"])
    결과[i] = {"t0": t0, "시각": 시각, "마지막": 마지막, "글": "".join(글), "상태": r.status}
    c.close()


def 한번(주소, K, 생성, 모델):
    결과 = [None] * K
    신호 = threading.Event()
    실들 = []
    for i in range(K):
        몸 = {"model": 모델, "stream": True, "temperature": 0, "max_tokens": 생성, "ignore_eos": True,
             "messages": [{"role": "user", "content": f"Write a long story about {주제[i % len(주제)]}."}]}
        t = threading.Thread(target=요청하나, args=(주소, 몸, 결과, i, 신호))
        t.start()
        실들.append(t)
    time.sleep(0.2)
    신호.set()
    for t in 실들:
        t.join()
    첫들 = [r["시각"][0] for r in 결과 if r["시각"]]
    끝들 = [r["시각"][-1] for r in 결과 if r["시각"]]
    a, b = max(첫들), min(끝들)
    받음 = sum(sum(1 for x in r["시각"] if a < x <= b) for r in 결과)
    간격 = []
    for r in 결과:
        s = r["시각"]
        간격 += [s[j + 1] - s[j] for j in range(16, len(s) - 16)]
    return {"K": K, "합처리량": 받음 / (b - a) if b > a else None, "걸음ms": statistics.median(간격) * 1000 if 간격 else None,
            "토큰수": [len(r["시각"]) for r in 결과], "첫토큰ms": [(r["시각"][0] - r["t0"]) * 1000 for r in 결과 if r["시각"]],
            "라마시간": [(r["마지막"] or {}).get("timings") for r in 결과], "글머리": [r["글"][:80] for r in 결과]}


막기 = False          # 30단계 — --막기: 첫 토큰을 막는 소켓으로


def 첫토큰하나(주소, 몸):
    host, port = 주소.split(":")
    c = http.client.HTTPConnection(host, int(port), timeout=None if 막기 else 600)
    t0 = time.perf_counter()
    c.request("POST", "/v1/chat/completions", body=json.dumps(dict(몸, stream=True)).encode("utf-8"), headers={"Content-Type": "application/json"})
    r = c.getresponse()
    버퍼 = b""
    첫 = None
    while 첫 is None:
        조각 = r.read1(65536)
        if not 조각:
            break
        버퍼 += 조각
        for 사건 in 버퍼.split(b"\n\n"):
            if 사건.startswith(b"data: {") and b'"content":"' in 사건 and b'"content":""' not in 사건:
                첫 = time.perf_counter() - t0
                break
    r.read()
    c.close()
    return 첫 * 1000.0 if 첫 is not None else None


def 첫토큰재기(주소, 되풀이):
    """긴 대화 — 문장 140 개(약 2,000 토큰)의 사용자 말 + 답 + 새 질문. 캐시 끔 · 같은 프롬프트(캐시 씀) · 다음 차례(앞 차례까지 캐시)"""
    긴글 = " ".join(f"Sentence {i}: the river carries stones and stories down to the sea." for i in range(140))
    앞 = [{"role": "user", "content": "Read this text carefully.\n" + 긴글}, {"role": "assistant", "content": "I have read it."}]
    몸 = {"messages": 앞 + [{"role": "user", "content": "What does the river carry?"}], "temperature": 0, "max_tokens": 4}
    다음 = {"messages": 앞 + [{"role": "user", "content": "What does the river carry?"}, {"role": "assistant", "content": "Stones and stories."},
                            {"role": "user", "content": "Where does it go?"}], "temperature": 0, "max_tokens": 4}
    결과 = {"캐시끔": [], "같은프롬프트": [], "다음차례": []}
    for _ in range(되풀이):
        결과["캐시끔"].append(첫토큰하나(주소, dict(몸, cache_prompt=False)))
        결과["같은프롬프트"].append(첫토큰하나(주소, 몸))
        첫토큰하나(주소, dict(몸, cache_prompt=False))
        결과["다음차례"].append(첫토큰하나(주소, 다음))
    for k, v in 결과.items():
        print(f"첫 토큰 {k}: {[round(x, 1) for x in v]} ms (가운데 {statistics.median(v):.1f})", flush=True)
    return 결과


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--주소", default="127.0.0.1:8091")
    ap.add_argument("--동시", default="1,2,4")
    ap.add_argument("--생성", type=int, default=256)
    ap.add_argument("--되풀이", type=int, default=3)
    ap.add_argument("--모델", default="m")
    ap.add_argument("--출력")
    ap.add_argument("--첫토큰", action="store_true")
    ap.add_argument("--막기", action="store_true")
    a = ap.parse_args()
    global 막기
    막기 = a.막기
    if a.첫토큰:
        첫토큰하나(a.주소, {"messages": [{"role": "user", "content": "Hi"}], "temperature": 0, "max_tokens": 4})      # 데우기
        r = 첫토큰재기(a.주소, a.되풀이)
        if a.출력:
            json.dump(r, open(a.출력, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        return
    모두 = []
    한번(a.주소, 1, 32, a.모델)       # 데우기
    for 바퀴 in range(a.되풀이):
        for K in [int(x) for x in a.동시.split(",")]:
            r = 한번(a.주소, K, a.생성, a.모델)
            r["바퀴"] = 바퀴
            모두.append(r)
            print(f"바퀴 {바퀴} 동시 {K}: 합 {r['합처리량']:.1f} 토큰/초 · 걸음 {r['걸음ms']:.3f} ms · 토큰 {r['토큰수']} · 첫 토큰 {[round(x) for x in r['첫토큰ms']]} ms", flush=True)
    if a.출력:
        json.dump(모두, open(a.출력, "w", encoding="utf-8"), ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
