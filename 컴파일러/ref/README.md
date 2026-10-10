# 글 앞단 (고정 사본)

`geul/` 은 [글 참조 구현](https://github.com/wwoosshh/geul-lang)의 `ref/geul` 패키지 사본이다 — 렉서 · 파서 · 의미 분석 · 낮추기와
연구 옵션(`research.py` — `반실수` 등). `글ptx.py` 가 글 소스를 읽어 타입이 붙은 IR 까지 만드는 데 쓴다(뒤의 PTX 생성은 `글ptx.py`).

- 출처: wwoosshh/geul-lang, 가지 `research/gpu`, `ref/geul` 의 마지막 변경 커밋 f74d4b6 (2026-10-09). 2세대 글(1.2.x)의 참조 구현에
  연구 옵션을 더한 판.
- 라이선스: MIT (같은 저자 — 저장소의 [LICENSE](../../LICENSE)).
- 이 사본을 바꾸면 `엔진/커널모듈.py` 의 PTX 캐시 열쇠가 바뀌어 모듈을 다시 컴파일한다. 글 언어 쪽이 바뀌면 사본을 맞추고 시험을 다시 돌린다.
