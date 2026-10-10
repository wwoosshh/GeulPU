#!/usr/bin/env python3
"""실행 파일(PE)의 가져오기 표 — DLL 마다 가져오는 함수 수. 표준 라이브러리만(18a · 22c 의 조건: kernel32 · shell32 · nvcuda 뿐인가).

  python -I 시험/가져오기표.py <실행 파일>
"""
import struct
import sys


def 가져오기(경로):
    b = open(경로, "rb").read()
    pe = struct.unpack_from("<I", b, 0x3C)[0]
    assert b[pe:pe + 4] == b"PE\0\0"
    n절 = struct.unpack_from("<H", b, pe + 6)[0]
    선택크기 = struct.unpack_from("<H", b, pe + 20)[0]
    선택 = pe + 24
    매직 = struct.unpack_from("<H", b, 선택)[0]
    자료목록 = 선택 + (112 if 매직 == 0x20B else 96)
    imp_rva = struct.unpack_from("<I", b, 자료목록 + 8)[0]
    절들 = []
    for i in range(n절):
        o = 선택 + 선택크기 + 40 * i
        vsz, va, rawsz, raw = struct.unpack_from("<IIII", b, o + 8)      # VirtualSize · VirtualAddress · SizeOfRawData · PointerToRawData
        절들.append((va, max(vsz, rawsz), raw))

    def 위치(rva):
        for va, sz, raw in 절들:
            if va <= rva < va + sz:
                return raw + rva - va
        raise ValueError(hex(rva))

    def 글(rva):
        o = 위치(rva)
        return b[o:b.index(b"\0", o)].decode("ascii")
    out = []
    o = 위치(imp_rva)
    while True:
        oft, _, _, name, ft = struct.unpack_from("<IIIII", b, o)
        if name == 0:
            break
        thunk = 위치(oft or ft)
        n = 0
        while struct.unpack_from("<Q" if 매직 == 0x20B else "<I", b, thunk)[0]:
            n += 1
            thunk += 8 if 매직 == 0x20B else 4
        out.append((글(name), n))
        o += 20
    return out


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    for dll, n in 가져오기(sys.argv[1]):
        print(f"{dll} {n}")
