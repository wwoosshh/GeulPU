"""시험의 GPU 드라이버 — 보통은 CUDA(엔진/글gpt2.py 의 드라이버). 환경 변수 GEULPU_VULKAN 이 있으면 그 이름이 든 Vulkan 장치에서
글(geul) 컴파일러의 SPIR-V 뒷단이 낸 커널(.spvs — 시험에 PTX 대신 준다)을 돌린다(31단계 — 탐침/vulkan/vk뒷단.py 의 CUDA 흉내)."""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, ".."))


def 드라이버():
    v = os.environ.get("GEULPU_VULKAN")
    if not v:
        sys.path.insert(0, os.path.join(ROOT, "엔진"))
        import 글gpt2 as G
        return G.드라이버()
    sys.path.insert(0, os.path.join(ROOT, "탐침", "vulkan"))
    import vk뒷단 as VB
    return VB.쿠다흉내드라이버(v)


def 한도넘음(dr, 이름):
    """Vulkan 장치에서 그 커널을 돌릴 수 없으면 까닭(글), 아니면 None — 공유 메모리가 장치 한도를 넘거나 뒷단이 뺀 커널.
    CUDA 드라이버는 늘 None. 시험은 이 커널을 조용히 빼지 않고 결과에 '장치 한도' 로 적는다(31단계 31g)."""
    if not hasattr(dr, "커널들"):
        return None
    try:
        e = dr.함수(None, 이름)
    except KeyError:
        return "SPIR-V 뒷단이 뺀 커널"
    b = dr.커널들[e][1]
    if b > dr.공유한도:
        return f"공유 메모리 {b} 바이트 > 장치 한도 {dr.공유한도}"
    return None
