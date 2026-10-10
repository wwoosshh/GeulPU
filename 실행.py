#!/usr/bin/env python3
"""GeulPU 터미널 실행기 — GGUF 모델 하나를 올려 채팅한다(14단계: Qwen2.5-0.5B-Instruct Q8_0).

  python 실행.py 모델.gguf [--최대길이 8192] [--최대행 2048] [--생성 1024] [--시스템 "…"]

입력 한 줄이 사용자의 말 한 차례다. 명령: /새로 (대화를 비운다) · /끝 (나간다). 탐욕 생성 — 같은 대화면 같은 답(비트까지 같은 계약:
문서/계약.md · 문서/14단계.md). 차례마다 KV 캐시를 이어 쓴다(앞 차례를 다시 계산하지 않는다). 답 뒤에 첫 토큰까지의 시간 · 초당 토큰을 보인다.
토크나이저 · 채팅 틀은 GGUF 안의 것(tokenizer.ggml.*)을 쓴다 — 다른 파일이 필요 없다.
"""
import argparse
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "엔진"))


class 대화:
    """채팅 한 줄기의 상태 — 차례마다 덩이(사용자 말 + 틀)를 앞 캐시에 이어 넣고 답을 생성 그래프로 만든다. 마지막에 고른 토큰은 아직 캐시에
    넣지 않았다 — 다음 차례 덩이의 머리가 된다(그래서 대화 전체의 토큰열을 한 번에 넣은 탐욕과 같은 토큰이 나온다)."""

    def __init__(self, 엔진, tk, 시스템=None, 최대생성=1024):
        import 토크나이저 as TK
        self.m, self.tk = 엔진, tk
        self.시스템 = TK.기본시스템 if 시스템 is None else 시스템
        self.최대생성 = 최대생성
        self.끝 = tk.특수["<|im_end|>"]
        self.끝들 = tuple(sorted(tk.끝들))
        self.비우기()

    def 비우기(self):
        self.토큰 = []          # 대화의 모든 토큰(마지막 것은 아직 캐시 밖)
        self.위치 = 0           # 캐시에 든 토큰 수

    def 덩이(self, 말):
        """이번 차례에 넣을 토큰 — 첫 차례는 시스템 + 사용자 + 답의 머리, 그 뒤는 [앞 답의 마지막 토큰] + (끝이 아니었으면 <|im_end|>) + 줄바꿈 +
        사용자 + 답의 머리 (ChatML — Qwen2.5 의 채팅 틀과 같은 글)."""
        사용자 = f"<|im_start|>user\n{말}<|im_end|>\n<|im_start|>assistant\n"
        if not self.토큰:
            return self.tk.나누기(f"<|im_start|>system\n{self.시스템}<|im_end|>\n" + 사용자)
        앞 = self.토큰[-1]
        return [앞] + self.tk.나누기(("\n" if 앞 == self.끝 else "<|im_end|>\n") + 사용자)

    def 남은자리(self, 덩이):
        return self.m.최대길이 - self.위치 - len(덩이)

    def 묻기(self, 말, 받기=None):
        """말 한 차례 — (답 토큰, 첫 토큰까지 ms, 생성 ms). 받기(새 글) 로 흘려 보인다."""
        덩이 = self.덩이(말)
        자리 = self.남은자리(덩이)
        if 자리 < 2:
            raise OverflowError("문맥이 가득 찼다")
        self.m.dr.맞추기()
        t0 = time.perf_counter()
        첫 = self.m.이어넣기(덩이, self.위치)
        t1 = time.perf_counter()
        답글, 보인 = [첫], [""]

        def 보이기(끝=False):
            """지금까지의 답을 글로 풀어 새로 생긴 뒷부분만 받기로 — 바이트가 아직 끊긴 글자(바꿈표)는 끝이 아니면 다음에."""
            글 = self.tk.잇기([t for t in 답글 if t not in self.끝들])
            if not 끝:
                글 = 글.rstrip("�")
            if len(글) > len(보인[0]) and 글.startswith(보인[0]):
                받기(글[len(보인[0]):])
                보인[0] = 글

        def 흘리기(새):
            답글.extend(새)
            보이기()
        if 받기:
            보이기()
        답 = self.m.이어생성(첫, self.위치 + len(덩이), min(self.최대생성, 자리) - 1, 끝들=self.끝들, 받기=흘리기 if 받기 else None)
        t2 = time.perf_counter()
        if 받기:
            보이기(끝=True)
        # 캐시: 덩이 전체 + 답의 마지막 앞까지(답의 첫 토큰부터 이어생성이 넣었다)
        self.위치 += len(덩이) + len(답) - 1
        self.토큰 += (덩이[1:] if self.토큰 else 덩이) + 답
        return 답, (t1 - t0) * 1000, (t2 - t1) * 1000


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stdin.reconfigure(encoding="utf-8", errors="replace")
    p = argparse.ArgumentParser(description="GeulPU 터미널 실행기 — GGUF 를 올려 채팅")
    p.add_argument("gguf")
    p.add_argument("--최대길이", type=int, default=8192)
    p.add_argument("--최대행", type=int, default=2048)
    p.add_argument("--생성", type=int, default=1024, help="차례마다 생성할 토큰 수의 한도")
    p.add_argument("--시스템", default=None, help="시스템 말(없으면 Qwen 의 기본)")
    a = p.parse_args()
    import gguf읽기
    import 글qwen2
    import 토크나이저 as TK
    t0 = time.perf_counter()
    print("모델을 올리는 중…", flush=True)
    g = gguf읽기.GGUF(a.gguf)
    tk = TK.Qwen토크나이저(gguf=g)
    w = 글qwen2.qwen2가중치(a.gguf)
    del g
    m = 글qwen2.글Qwen2(a.gguf, 최대행=a.최대행, 최대길이=a.최대길이, 로짓행=1, 가중치=w)
    del w
    m.판미리고르기()
    print(f"올림 {time.perf_counter() - t0:.1f} 초 — {os.path.basename(a.gguf)} · 문맥 {a.최대길이}. /새로 · /끝", flush=True)
    d = 대화(m, tk, a.시스템, a.생성)
    try:
        while True:
            try:
                말 = input("\n> ")
            except EOFError:
                break
            말 = 말.strip()
            if not 말:
                continue
            if 말 in ("/끝", "/나가기", "/quit", "/exit"):
                break
            if 말 in ("/새로", "/new"):
                d.비우기()
                print("(새 대화)")
                continue
            try:
                답, 첫ms, 생성ms = d.묻기(말, 받기=lambda s: print(s, end="", flush=True))
            except OverflowError:
                print(f"(문맥 {a.최대길이} 이 가득 찼다 — /새로 로 새 대화를 시작하세요)")
                continue
            n = len(답)
            초당 = (n - 1) / (생성ms / 1000) if n > 1 and 생성ms > 0 else 0.0
            print(f"\n[첫 토큰까지 {첫ms:.1f} ms · 생성 {n} 토큰 {초당:.1f} 토큰/초 · 문맥 {d.위치 + 1}]", flush=True)
    finally:
        m.닫기()


if __name__ == "__main__":
    main()
