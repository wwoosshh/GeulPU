#!/usr/bin/env python3
"""40단계 수집(문서/40단계.md '무엇으로 재나') — 토큰 번호 만들기 · 갈래마다 생성 · V 의 점수 매기기 · 오염 대화 · 갈래(번짐) · L 확인.

  python -I -X utf8 재기/모음40.py <명령> --모델 7b|r1|05b [--갈래 G|V|L] --작업 W --모델폴더 M --llama LL --빌드 B

명령:
  토큰   — llama.cpp(CPU 로 띄운 llama-server)의 /apply-template · /tokenize 로 질문을 토큰 번호로(모든 갈래가 같은 번호를 받는다)
  생성   — 갈래 G(GeulPU 계약) · V(한 자리 모듈) · L(llama-server, 기본 설정 -np 8)로 탐욕 생성, 걸음마다 상위 20
  점수   — V 가 G 의 답을 점수 매긴다(echo — 상위 20)
  오염   — 오염 대화: 첫 답(G) → 비정상 넣기(넷) → 둘째 답(G)
  확인L  — 40a (5): 자연 묶음에서 50 문항(씨앗 40)을 llama-server -np 1 로 생성(따라40.py --확인 이 견준다)
  갈래   — 40e (1): 위험한 걸음(셈40.py 위험)에서 b 를 넣고 이어 쓰기(G)
기록은 W/토큰 · W/생성 아래 JSONL(문항마다 한 줄) — 다시 부르면 이미 있는 문항은 건너뛴다.
"""
import argparse
import json
import os
import random
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, ".."))
sys.path.insert(0, HERE)
질문폴더 = os.path.join(ROOT, "시험", "질문40")
GGUF = {"7b": "qwen7b.gguf", "r1": "r1.gguf", "05b": "qwen05b.gguf"}
모듈 = {("G", "7b"): "qwen2Q8_7b", ("G", "r1"): "qwen2Q8_7b", ("G", "05b"): "qwen2Q8",
        ("V", "7b"): "qwen2Q8_7b_자리하나", ("V", "r1"): "qwen2Q8_7b_자리하나"}
문맥 = 4096                 # 줄마다(38c 에서 두 엔진 모두 슬롯 8 · 4096 으로 돌렸다)
슬롯 = 8
최소새토큰 = 256            # 프롬프트가 길어 새 토큰을 이만큼도 못 내면 뺀다(기록) — 모든 갈래에 같게


def 최대(r):
    """문맥 안에서 낼 수 있는 새 토큰 수(모든 갈래에 같게). 최소새토큰보다 작으면 None(뺌)."""
    m = min(r["최대"], 문맥 - len(r["ids"]))
    return m if m >= 최소새토큰 else None
포트 = {"G": 18401, "V": 18401, "L": 18402, "토큰": 18403, "L1": 18404}
씨앗 = 40


def 기록(*a):
    print(time.strftime("%H:%M:%S"), *a, flush=True)


# ---------------------------------------------------------------- HTTP · 서버
def 보내기(포, 길, 몸, 기다림=3600):
    q = urllib.request.Request(f"http://127.0.0.1:{포}{길}", data=json.dumps(몸).encode(), headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(q, timeout=기다림) as r:
        return json.loads(r.read().decode("utf-8"))


def 살았나(포):
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{포}/health", timeout=3) as r:
            return r.status == 200
    except Exception:
        return False


class 서버:
    def __init__(self, 명령, 포, 로그):
        self.포 = 포
        self.f = open(로그, "ab")
        기록("서버 띄움:", " ".join(os.path.basename(x) if os.sep in x or "/" in x else x for x in 명령))
        self.p = subprocess.Popen(명령, stdout=self.f, stderr=subprocess.STDOUT)
        t0 = time.time()
        while not 살았나(포):
            if self.p.poll() is not None:
                raise RuntimeError(f"서버가 끝났다(종료 {self.p.returncode}) — {로그}")
            if time.time() - t0 > 900:
                raise RuntimeError("서버가 15 분 안에 뜨지 않았다")
            time.sleep(2)
        기록(f"서버 뜸 ({time.time() - t0:.0f} 초)")

    def 끄기(self):
        self.p.terminate()
        try:
            self.p.wait(30)
        except subprocess.TimeoutExpired:
            self.p.kill()
            self.p.wait(30)
        self.f.close()
        time.sleep(3)


def 지울서버(a, 갈래, 모델):
    g = os.path.join(a.모델폴더, GGUF[모델])
    로그 = os.path.join(a.작업, "logs", f"서버_{갈래}_{모델}.log")
    os.makedirs(os.path.dirname(로그), exist_ok=True)
    if 갈래 in ("G", "V"):
        ptx = os.path.join(a.빌드, 모듈[(갈래, 모델)] + ".ptx")
        return 서버([os.path.join(a.빌드, "서버.exe"), g, "--ptx", ptx, "--포트", str(포트[갈래]), "--슬롯", str(슬롯), "--문맥", str(문맥),
                   "--이름", f"geulpu40{갈래}"], 포트[갈래], 로그)
    if 갈래 == "L":
        return 서버([os.path.join(a.llama, "llama-server.exe"), "-m", g, "-ngl", "99", "-c", str(문맥 * 슬롯), "-np", str(슬롯),
                   "--host", "127.0.0.1", "--port", str(포트["L"]), "--no-webui"], 포트["L"], 로그)
    if 갈래 == "L1":
        return 서버([os.path.join(a.llama, "llama-server.exe"), "-m", g, "-ngl", "99", "-c", str(문맥), "-np", "1",
                   "--host", "127.0.0.1", "--port", str(포트["L1"]), "--no-webui"], 포트["L1"], 로그)
    if 갈래 == "토큰":
        return 서버([os.path.join(a.llama, "llama-server.exe"), "-m", g, "-ngl", "0", "-c", "8192", "-np", "1", "--jinja",
                   "--host", "127.0.0.1", "--port", str(포트["토큰"]), "--no-webui"], 포트["토큰"], 로그)
    raise ValueError(갈래)


# ---------------------------------------------------------------- 질문 · 토큰
def 질문들(모델):
    out = []
    for f in sorted(os.listdir(질문폴더)):
        if not f.endswith(".jsonl") or f.startswith("오염") or f == "자연_수학_더.jsonl":
            continue
        for l in open(os.path.join(질문폴더, f), encoding="utf-8"):
            r = json.loads(l)
            if 모델 in r["모델"]:
                out.append(r)
    return out


def 토큰화(포, messages):
    """llama-server 의 채팅과 같게: 틀을 그리고 add_special 참으로 토큰화(GGUF 가 BOS 를 붙이라면 붙는다 — R1)."""
    t = 보내기(포, "/apply-template", {"messages": messages})["prompt"]
    ids = 보내기(포, "/tokenize", {"content": t, "add_special": True, "parse_special": True})["tokens"]
    return t, ids


def jsonl읽기(p):
    if not os.path.exists(p):
        return {}
    out = {}
    for l in open(p, encoding="utf-8"):
        if l.strip():
            r = json.loads(l)
            out[r["id"]] = r
    return out


class 쓰개:
    def __init__(self, p):
        os.makedirs(os.path.dirname(p), exist_ok=True)
        self.f = open(p, "a", encoding="utf-8", newline="\n")
        self.lock = threading.Lock()

    def 쓰기(self, r):
        with self.lock:
            self.f.write(json.dumps(r, ensure_ascii=False) + "\n")
            self.f.flush()

    def 닫기(self):
        self.f.close()


def 명령_토큰(a):
    rows = 질문들(a.모델)
    if a.모델 in ("r1", "05b"):                        # 수학의 다음 600 문항도 토큰으로 만들어 둔다(생성은 --더 일 때만)
        rows += [json.loads(l) for l in open(os.path.join(질문폴더, "자연_수학_더.jsonl"), encoding="utf-8")
                 if a.모델 in json.loads(l)["모델"]]
    p = os.path.join(a.작업, "토큰", f"{a.모델}.jsonl")
    있음 = jsonl읽기(p)
    s = 지울서버(a, "토큰", a.모델)
    w = 쓰개(p)
    try:
        for i, r in enumerate(rows):
            if r["id"] in 있음:
                continue
            t, ids = 토큰화(포트["토큰"], r["messages"])
            w.쓰기({"id": r["id"], "묶음": r["묶음"], "ids": ids, "최대": r["최대"], "틀글끝": t[-80:]})
            if i % 200 == 0:
                기록(f"토큰 {a.모델} {i}/{len(rows)} — 길이 {len(ids)}")
    finally:
        w.닫기()
        s.끄기()
    기록(f"토큰 {a.모델} 끝 — {len(jsonl읽기(p))} 문항")


# ---------------------------------------------------------------- 생성
def G요청(포, ids, 최대):
    r = 보내기(포, "/v1/completions", {"prompt": ids, "max_tokens": 최대, "temperature": 0.0, "logprobs": 20, "seed": 씨앗,
                                     "geulpu": {"prompt_tokens": True}})
    g, c = r["geulpu"], r["choices"][0]
    return {"tokens": g["tokens"], "text": c["text"], "finish": c["finish_reason"], "top_ids": g["top_ids"],
            "top_lp": g["top_logprobs"], "prompt_n": len(g["prompt_tokens"])}


def L요청(포, ids, 최대, 캐시=True):
    r = 보내기(포, "/completion", {"prompt": ids, "n_predict": 최대, "temperature": 0.0, "n_probs": 20, "return_tokens": True,
                                 "cache_prompt": 캐시, "seed": 씨앗, "repeat_penalty": 1.0, "presence_penalty": 0.0,
                                 "frequency_penalty": 0.0, "dry_multiplier": 0.0})
    cp = r.get("completion_probabilities") or []
    top_ids = [[t["id"] for t in e["top_logprobs"]] for e in cp]
    top_lp = [[t["logprob"] for t in e["top_logprobs"]] for e in cp]
    끝 = "length" if r.get("stop_type") == "limit" or (r.get("stopped_limit") is True) else "stop"
    tm = r.get("timings") or {}
    return {"tokens": r.get("tokens", []), "text": r["content"], "finish": 끝, "top_ids": top_ids, "top_lp": top_lp,
            "prompt_n": r.get("tokens_evaluated"), "stop_type": r.get("stop_type"), "cache_n": tm.get("cache_n"),
            "셈한프롬프트": tm.get("prompt_n")}


def 명령_생성(a):
    토 = [r for r in jsonl읽기(os.path.join(a.작업, "토큰", f"{a.모델}.jsonl")).values()]
    if a.갈래 in ("V", "L"):                      # V · L 의 생성은 자연 묶음(H1 · H2) — L 은 방아쇠 묶음도(보조 궤적)
        토 = [r for r in 토 if r["묶음"].startswith("자연") or (a.갈래 == "L" and r["묶음"].startswith("방아쇠"))]
    더 = [r for r in 토 if r["id"] >= "gsm_0600" and r["id"].startswith("gsm_")]
    if 더 and not a.더:
        토 = [r for r in 토 if r not in 더]           # 수학의 다음 600 은 판정 규칙(b + c < 40)이 부를 때만
    p = os.path.join(a.작업, "생성", f"{a.갈래}_{a.모델}.jsonl")
    있음 = jsonl읽기(p)
    뺌 = [r["id"] for r in 토 if 최대(r) is None]
    if 뺌:
        기록(f"문맥 {문맥} 에 새 토큰 {최소새토큰} 개도 못 내는 프롬프트 — 뺌: {뺌}")
    할 = [r for r in 토 if r["id"] not in 있음 and 최대(r) is not None]
    기록(f"생성 {a.갈래} {a.모델}: {len(할)} 문항 (이미 {len(있음)})")
    if not 할:
        return
    s = 지울서버(a, a.갈래, a.모델)
    w = 쓰개(p)
    포 = 포트[a.갈래]
    t0 = time.time()
    n = [0, 0]

    def 하나(r):
        try:
            m = 최대(r)
            x = G요청(포, r["ids"], m) if a.갈래 in ("G", "V") else L요청(포, r["ids"], m)
            x.update({"id": r["id"], "묶음": r["묶음"], "보낸수": len(r["ids"]), "최대": m})
            w.쓰기(x)
            n[0] += 1
            n[1] += len(x["tokens"])
            if n[0] % 50 == 0:
                기록(f"  {n[0]}/{len(할)} · 토큰 {n[1]} · {n[1] / (time.time() - t0):.0f} 토큰/초")
        except Exception as e:
            기록("실패", r["id"], repr(e)[:300])
    try:
        with ThreadPoolExecutor(슬롯) as ex:
            list(ex.map(하나, 할))
    finally:
        w.닫기()
        s.끄기()
    기록(f"생성 {a.갈래} {a.모델} 끝 — {len(jsonl읽기(p))} 문항 · {time.time() - t0:.0f} 초")


def 명령_점수(a):
    """V 가 G 의 답(토큰 — 끝 토큰 포함)을 점수 매긴다: echo, 상위 20. 걸음 t 의 분포 = prompt_top_ids[P + t]."""
    G = jsonl읽기(os.path.join(a.작업, "생성", f"G_{a.모델}.jsonl"))
    토 = jsonl읽기(os.path.join(a.작업, "토큰", f"{a.모델}.jsonl"))
    p = os.path.join(a.작업, "생성", f"{a.갈래}점수_{a.모델}.jsonl")
    있음 = jsonl읽기(p)
    할 = [g for k, g in G.items() if k not in 있음]
    기록(f"점수 {a.갈래} {a.모델}: {len(할)} 문항")
    if not 할:
        return
    s = 지울서버(a, a.갈래, a.모델)
    w = 쓰개(p)
    포 = 포트[a.갈래]

    def 하나(g):
        try:
            P = 토[g["id"]]["ids"]
            r = 보내기(포, "/v1/completions", {"prompt": P + g["tokens"], "echo": True, "max_tokens": 0, "logprobs": 20,
                                           "temperature": 0.0, "geulpu": {"echo_from": len(P)}})
            q = r["geulpu"]
            w.쓰기({"id": g["id"], "묶음": g["묶음"], "top_ids": q["prompt_top_ids"][len(P):],
                   "top_lp": q["prompt_top_logprobs"][len(P):]})
        except Exception as e:
            기록("실패", g["id"], repr(e)[:300])
    try:
        with ThreadPoolExecutor(4) as ex:
            list(ex.map(하나, 할))
    finally:
        w.닫기()
        s.끄기()
    기록(f"점수 {a.갈래} {a.모델} 끝 — {len(jsonl읽기(p))} 문항")


# ---------------------------------------------------------------- 오염 대화
def 명령_오염(a):
    import 질문40 as Q
    rows = [json.loads(l) for l in open(os.path.join(질문폴더, "오염.jsonl"), encoding="utf-8")]
    p1 = os.path.join(a.작업, "생성", "오염첫_7b.jsonl")
    p2 = os.path.join(a.작업, "생성", "오염둘_7b.jsonl")
    tk = 지울서버(a, "토큰", "7b")
    s = 지울서버(a, "G", "7b")
    try:
        있음 = jsonl읽기(p1)
        w = 쓰개(p1)

        def 첫(r):
            try:
                _, ids = 토큰화(포트["토큰"], [{"role": "user", "content": r["q1"]}])
                x = G요청(포트["G"], ids, r["최대1"])
                x.update({"id": r["id"], "ids": ids})
                w.쓰기(x)
            except Exception as e:
                기록("실패 첫", r["id"], repr(e)[:300])
        with ThreadPoolExecutor(슬롯) as ex:
            list(ex.map(첫, [r for r in rows if r["id"] not in 있음]))
        w.닫기()
        A1 = jsonl읽기(p1)
        있음 = jsonl읽기(p2)
        w = 쓰개(p2)
        일 = []
        for i, r in enumerate(rows):
            for 종류 in ("깨끗", "다른문자", "맞춤법", "되풀이"):
                k = f"{r['id']}_{종류}"
                if k not in 있음 and r["id"] in A1:
                    일.append((i, r, 종류, k))

        def 둘(x):
            i, r, 종류, k = x
            try:
                답 = A1[r["id"]]["text"]
                if 답.endswith("<|im_end|>"):
                    답 = 답[:-len("<|im_end|>")]
                바뀐, 무엇 = Q.오염넣기(답, 종류, i)
                msgs = [{"role": "user", "content": r["q1"]}, {"role": "assistant", "content": 바뀐}, {"role": "user", "content": r["q2"]}]
                _, ids = 토큰화(포트["토큰"], msgs)
                y = G요청(포트["G"], ids, r["최대2"])
                y.update({"id": k, "대화": r["id"], "종류": 종류, "넣음": 무엇, "보낸수": len(ids)})
                w.쓰기(y)
            except Exception as e:
                기록("실패 둘", k, repr(e)[:300])
        with ThreadPoolExecutor(슬롯) as ex:
            list(ex.map(둘, 일))
        w.닫기()
    finally:
        s.끄기()
        tk.끄기()
    기록(f"오염 끝 — 첫 {len(jsonl읽기(p1))} · 둘 {len(jsonl읽기(p2))}")


# ---------------------------------------------------------------- 40a (5) · 40e
def 확인문항(작업, 모델):
    토 = [r for r in jsonl읽기(os.path.join(작업, "토큰", f"{모델}.jsonl")).values()
         if r["묶음"].startswith("자연") and 최대(r) is not None and not (r["id"].startswith("gsm_") and r["id"] >= "gsm_0600")]
    토.sort(key=lambda r: r["id"])
    rng = random.Random(씨앗)
    return rng.sample(토, 50)


def 명령_확인L(a):
    p = os.path.join(a.작업, "생성", f"L1확인_{a.모델}.jsonl")
    있음 = jsonl읽기(p)
    할 = [r for r in 확인문항(a.작업, a.모델) if r["id"] not in 있음]
    if not 할:
        return
    s = 지울서버(a, "L1", a.모델)
    w = 쓰개(p)
    try:
        for r in 할:                                  # 하나씩(동시 1)
            m = 최대(r)
            x = L요청(포트["L1"], r["ids"], m, 캐시=False)
            x.update({"id": r["id"], "묶음": r["묶음"], "보낸수": len(r["ids"]), "최대": m})
            w.쓰기(x)
    finally:
        w.닫기()
        s.끄기()
    기록(f"확인L 끝 — {len(jsonl읽기(p))} 문항")


def 명령_갈래(a):
    """셈40.py 위험 이 고른 갈래 목록(W/위험/갈래목록_7b.jsonl — 문항 · 걸음 · 유형 · b)으로 G 에서 이어 쓰기."""
    목록 = [json.loads(l) for l in open(os.path.join(a.작업, "위험", f"갈래목록_{a.모델}.jsonl"), encoding="utf-8")]
    토 = jsonl읽기(os.path.join(a.작업, "토큰", f"{a.모델}.jsonl"))
    G = jsonl읽기(os.path.join(a.작업, "생성", f"G_{a.모델}.jsonl"))
    p = os.path.join(a.작업, "생성", f"갈래_{a.모델}.jsonl")
    있음 = jsonl읽기(p)
    할 = [x for x in 목록 if x["key"] not in 있음]
    if not 할:
        return
    s = 지울서버(a, "G", a.모델)
    w = 쓰개(p)

    def 하나(x):
        try:
            P = 토[x["id"]]["ids"]
            앞 = G[x["id"]]["tokens"][:x["t"]]
            창 = min(x["창"], 문맥 - len(P) - len(앞) - 1)
            y = G요청(포트["G"], P + 앞 + [x["b"]], 창)
            y.update({"id": x["key"], "문항": x["id"], "t": x["t"], "유형": x["유형"], "b": x["b"]})
            del y["top_ids"], y["top_lp"]
            w.쓰기(y)
        except Exception as e:
            기록("실패 갈래", x["key"], repr(e)[:300])
    try:
        with ThreadPoolExecutor(슬롯) as ex:
            list(ex.map(하나, 할))
    finally:
        w.닫기()
        s.끄기()
    기록(f"갈래 끝 — {len(jsonl읽기(p))}")


def 명령_재현(a):
    """40a (3): G · V 를 문항 50 개(씨앗 40 — 확인문항과 같은 고르기)로 동시 요청 1 에서 다시, 그리고 갈래 50 개를 다시(G)."""
    for 갈래 in ("G", "V"):
        p = os.path.join(a.작업, "생성", f"재현{갈래}_{a.모델}.jsonl")
        있음 = jsonl읽기(p)
        할 = [r for r in 확인문항(a.작업, a.모델) if r["id"] not in 있음]
        if not 할:
            continue
        s = 지울서버(a, 갈래, a.모델)
        w = 쓰개(p)
        try:
            for r in 할:
                x = G요청(포트[갈래], r["ids"], 최대(r))
                w.쓰기({"id": r["id"], "tokens": x["tokens"]})
        finally:
            w.닫기()
            s.끄기()
    목 = os.path.join(a.작업, "위험", f"갈래목록_{a.모델}.jsonl")
    if os.path.exists(목):
        목록 = [json.loads(l) for l in open(목, encoding="utf-8")][:50]
        p = os.path.join(a.작업, "생성", f"재현갈래_{a.모델}.jsonl")
        있음 = jsonl읽기(p)
        할 = [x for x in 목록 if x["key"] not in 있음]
        if 할:
            토 = jsonl읽기(os.path.join(a.작업, "토큰", f"{a.모델}.jsonl"))
            G = jsonl읽기(os.path.join(a.작업, "생성", f"G_{a.모델}.jsonl"))
            s = 지울서버(a, "G", a.모델)
            w = 쓰개(p)
            try:
                for x in 할:
                    P = 토[x["id"]]["ids"]
                    앞 = G[x["id"]]["tokens"][:x["t"]]
                    창 = min(x["창"], 문맥 - len(P) - len(앞) - 1)
                    y = G요청(포트["G"], P + 앞 + [x["b"]], 창)
                    w.쓰기({"id": x["key"], "tokens": y["tokens"]})
            finally:
                w.닫기()
                s.끄기()
    기록("재현 끝")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("명령")
    ap.add_argument("--모델", required=True)
    ap.add_argument("--갈래", default="G")
    ap.add_argument("--작업", required=True)
    ap.add_argument("--모델폴더", required=True)
    ap.add_argument("--llama", required=True)
    ap.add_argument("--빌드", required=True)
    ap.add_argument("--더", action="store_true", help="수학의 다음 600 문항도")
    a = ap.parse_args()
    {"토큰": 명령_토큰, "생성": 명령_생성, "점수": 명령_점수, "오염": 명령_오염, "확인L": 명령_확인L, "갈래": 명령_갈래,
     "재현": 명령_재현}[a.명령](a)


if __name__ == "__main__":
    main()
