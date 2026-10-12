# What the compiler caught — and what it missed (stages 1–27)

*English version of [`research/gpu/컴파일러가-잡은-것.md`](https://github.com/wwoosshh/geul-lang/blob/research/gpu/research/gpu/컴파일러가-잡은-것.md)
in the geul repository. Terms follow the [glossary](glossary.md).*

The research program behind GeulPU makes a claim ("claim A"): *meaning is lost below libraries and inside compilers, so it takes a
compiler to keep it.* An outside review pointed out that the only quantitative evidence for that claim would be a list of the cases
where the geul compiler rejected a program, forced something to be written explicitly, or inserted a check that fired — and that
those cases were scattered across the stage reports where nobody could count them. This page is that list. It counts the misses too:
a list of catches alone would be advertising, not evidence.

## What was counted

- Sources: the research plan (geul repository `docs/17`), the stage reports of stages 1–13 (`research/gpu/`) and 14–27 (GeulPU
  `문서/`), and the commit history of both repositories, read on 2026-10-12. Every row cites its source.
- "The geul compiler" means both toolchains: the Python reference front end + Python PTX backend (stages 1–15) and the PTX backend
  written in geul inside the self-hosted compiler (stage 16 on).
- Categories:
  - **R** — compile-time rejection of real code in this project.
  - **E** — a rule the compiler always enforces, which makes a class of loss impossible (with its measured effect, if any).
  - **C** — a runtime check inserted by the compiler (the module's error cell) that actually fired.
  - **T** — caught only by tests, profiling or by hand; the compiler did not catch it.
  - **S** — a silent loss caused by the compiler or the language itself.
- Not counted: stage 0 (43 external bugs judged on paper), the paper test, the audits of other software stacks, driver behaviour,
  pure optimisation findings, and checks the programmer wrote in geul.

## Summary

| Category | Count | What |
|---|---|---|
| R — compile-time rejection | 9 | 4 touch meaning: the role-swap check D-30 three times (all preventive — no actually swapped argument is on record) and one backend refusal to emit different PTX. 5 are naming, syntax or tooling |
| E — enforced rules | 7 | The best-measured one is the PTX contract P1 (explicit `.rn` on float add/sub/mul): differing results 245,734 of 1,048,576 → 0; negative results of x·x − y·y 524,113 → 0 |
| C — inserted check fired | 4 | 2 on real bugs (garbage rows converted by an epilogue; garbage exponents written into the KV cache), 2 on designed tests |
| T — missed by the compiler | 27 | 13 bugs in geul code (found by bit tests 5, crash or hang 3, out of memory 1, by hand or unrecorded 4), 10 in test harnesses or measurement, 4 performance-only |
| S — the language or compiler itself | 6 | FMA fusion (P1) and address spaces (fixed); particle roles erased in the IR (still open); implicit msvcrt binding of `외부` declarations without a DLL name (still open); a user function capturing a standard-library verb call, and a literal adopting an 8-bit operand type (made errors by decision D-49) |

**How to read it.**
- Compile-time catches of real meaning bugs are few. The evidence for claim A is mostly **E** (rules that rule out a class of loss)
  and **C** (the error cell). P1 is the one E with a clear measurement.
- The planned compile-time meaning layer — axis, role and kind types, read-only roles, and the "facts license optimisations" items —
  was never built, so it rejected no real code.
- Two root causes recur among the 13 missed bugs in geul code:
  - **inner-block shadowing**, three times (stage 6, stages 9–14, stage 22) — every one silent; the language allows it;
  - **buffers whose size is not part of their type**, twice (an epilogue writing past a shared-memory array; a chunk buffer
    overflowed for 2–4-row chunks).

## Table

| # | Stage | What happened | Caught by | Cat. | Real bug? |
|---|---|---|---|---|---|
| 1 | 1 | The first PTX backend emitted `mul.f32`/`add.f32` without a rounding mode; the driver fused them into FMA: 245,734 of 1,048,576 results differed, x·x − y·y gave 1,048,342 non-zero cells (524,113 negative) | bit test vs geul on the CPU | S | yes (backend) |
| 2 | 1, 2g | PTX contract P1: `.rn` on every float add/sub/mul; fusion only through an explicit `곱해더하기` (fma). 245,734 → 0 | backend rule | E | designed |
| 3 | 1, 3 | P2: no `.approx`/`.ftz` unless the source names it; `div.rn` from the start | backend rule | E | designed |
| 4 | 1 | The IR had no address spaces: generic loads/stores, 40-byte stack (16 registers vs 12 for hand-written PTX); no wrong values | by hand | S | yes (performance) |
| 5 | 2a | Address-space rule: stacks 40 B and 88 B → 0; matmul 19.8 → 3.7 ms; bits unchanged | backend rule | E | designed |
| 6 | 1 (open) | Particle roles are erased when parameters become p0..p3 in the IR, so read-only and overlap facts never reach the backend; the read-only rejection was never built | by hand | S | yes (no wrong values) |
| 7 | 1 | D-30 required particles at the CUDA-wrapper call sites | sema (D-30) | R | no — preventive |
| 8 | 1 | Identifiers collided with keywords | parser | R | no (naming) |
| 9 | 1 | D-30 rejected a call in the cubin writer; rewritten with particles | sema (D-30) | R | no — a risk, no evidence of a swap |
| 10 | 2c | Error cell for float → int and f64 → f32 conversions fired on every designed out-of-range input; cost too small to measure | inserted check | C | designed test |
| 11 | 2e | Range analysis narrows div/rem to 32 bits only when proven; bit-identical at indices > 2³¹ | backend range proof | E | designed |
| 12 | 3 | A timing-only variant discarded its results and the driver removed the work (a wrong 27.6 TFLOPS figure) | by hand | T (measurement) | yes |
| 13 | 4 | A Python harness passed the address of a freed temporary to llama.cpp | crash | T (harness) | yes |
| 14 | 4-2 | Narrowing to float16 must be explicit; all four designed implicit narrowings are compile errors; no rejection of real code recorded | sema + backend | E | designed |
| 15 | 4-2 | float16 overflow sets error cell 4 even when one cell in 256 overflows | inserted check | C | designed test |
| 16 | 4-2 | A barrier number in a register made the cooperative megakernel hang | hang | T | yes (variant) |
| 17 | 3–5 | An epilogue wrote 64 floats past its shared-memory array; values were right by luck | by hand (bit tests could not see it) | T | yes |
| 18 | 6 | An epilogue converted garbage rows beyond the row count; the range check set the error cell | inserted check on real code | C | yes (latent) |
| 19 | 6 | An inner `M2` shadowed the outer one: 1 of 4 attention rows wrong | bit test vs another path | T | yes |
| 20 | 6 | No float tensor cores (unspecified accumulation rounding); only exact int8 MMA; malformed MMA call groups are rejected | backend design | E | designed |
| 21 | 6 | A 64-bit remainder made every tile 2× slower | timing | T (performance) | yes |
| 22 | 8 | A harness launched a kernel with the wrong grid rule (false failure) | test failure | T (harness) | yes |
| 23 | 8 | A stale global made a four-digit kernel be timed as two-digit | printed counts | T (measurement) | yes |
| 24 | 9 | A KV epilogue wrote garbage into value exponents (391 bytes) | error cell + cache-byte comparison | C (+T) | yes |
| 25 | 9 | `cp.async` waits only for the calling thread's copies; half of an attention output was wrong | bit test vs the CPU reference | T | yes |
| 26 | 9 | Range-checked conversions cost 181 vs 129 µs; replaced on hot paths by exact magic-number rounding | timing | T (performance) | no — the check's own cost |
| 27 | 9 | Negative time from an unwarmed plan; a double free in the harness | by hand | T (harness) | yes |
| 28 | 10–11 | A tile variant with 75–87.5% wrong cells was recorded as bit-identical (never shipped) | later bit test | T | yes (unshipped) |
| 29 | 11 | Another variant combination was wrong; now blocked in the generator | bit test | T | yes (unshipped) |
| 30 | 11 | The matmul test had compared only the first 6 tile shapes since stage 8 | test review | T (harness) | no — coverage gap |
| 31 | 11–12 | `ptxas` turned 64-bit division by a constant into a ~90-instruction call; the backend now lowers it with a magic multiply | Nsight / SASS | T (performance) | no |
| 32 | 12 | A comparison script read an output plane at the wrong row count | CPU-reference comparison | T (harness) | yes |
| 33 | 12 | An argument-handling bug made an empty selection run every kernel | by hand | T (harness) | yes |
| 34 | 9–13 | A chunk attention kernel overflowed its chunk buffer for 2–4-row chunks | code reading | T | yes (out-of-bounds write) |
| 35 | 9–14 | `{ 짧은실수 e = 0 }` declared a new inner `e` (shadowing): a denormal residue in every integer-KV attention kernel; invisible to bit tests | not recorded | T | yes (still in the GPT-2 modules) |
| 36 | 14 | A test compared `\r\n` with `\n` output | test failure | T (harness) | yes |
| 37 | 15 | Threads disagreed on barrier counting; the kernel hung (development) | hang | T | yes |
| 38 | 16 | The new geul PTX backend stopped at the first `sdiv` because the range proof was not ported yet — it refused instead of emitting different PTX | backend refusal | R | no — designed |
| 39 | 16 | Kernel-only sources without an entry point were rejected (fragment mode added) | front end | R | no (tooling) |
| 40 | 17 | The first build of the PTX backend in geul failed only on names | parser/sema | R | no |
| 41 | 17 | The geul backend refuses unsigned 64-bit values (its range analysis could disagree with the Python backend's) | backend design | E | designed |
| 42 | 18 | Host build errors: names colliding with language words, particle errors, braces in quotes | parser/sema | R | no |
| 43 | 18 (open) | An `외부` declaration without a DLL name silently binds to msvcrt.dll unless the compiler knows the function; the executable failed to start | load failure at run time | S | yes |
| 44 | 19 | A user function named `다듬기` captured the standard library's internal `다듬다` call (verb-form resolution, D-37); it surfaced only as an unrelated type error | coincidental type error | S | yes → error (D-49) |
| 45 | 19 | A literal adopts its operand's type, so `(문자 & 63) << 6` was computed in 8 bits and truncated (1088 → 64) | byte diff vs the Python generator | S | yes → error (D-49) |
| 46 | 19 | D-30 required particles while porting the generator | sema (D-30) | R | no — forced explicit |
| 47 | 19 | No string literals inside interpolation braces | parser | R | no |
| 48 | 20–24 | Shell scripts broke on Korean variable names three times | script errors | T (harness) | yes |
| 49 | 21 | A geul tool overflowed buffers sized for K = 3584 with K = 18944 inputs: 59% of cells differed | bit test vs the CPU reference | T | yes |
| 50 | 22 | A state buffer 4× too large (values right) | by hand | T | yes (memory) |
| 51 | 22 | Generated `b0`/`p0` shadowed loop variables of the same name: CUDA error 700 | crash in a test | T | yes |
| 52 | 23–24 | Q4_0 buffers sized like Q8_0 (1.9 GB extra on 7B); found because 14B did not fit | out of memory | T | yes (memory) |
| 53 | 25 | The first layer-split version did not wait for the last part: contexts overlapped | timing | T (performance) | yes |

Sources for every row (file and line, commit) are in the Korean version.

## What follows for the language

1. **Make the two silent failures errors** (#44, #45) — decision D-49 in the geul repository. While fixing them, a divergence between
   the two compiler implementations was found and fixed as well: the reference implementation included generic functions among
   verb-form prefix-omission candidates and the self-hosted (shipped) compiler did not, so the same program was accepted by one and
   rejected by the other.
2. **Inner-block shadowing** caused three real bugs here (#19, #35, #51). Whether to make it an error will be decided after measuring
   how much existing code it would reject.
3. **Buffers with their size in the type** (#17, #34) — the planned "v0 rule 1".
4. **`외부` declarations without a DLL name** (#43) — make an unknown function an error instead of binding it to msvcrt.
