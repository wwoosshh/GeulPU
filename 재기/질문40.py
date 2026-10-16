#!/usr/bin/env python3
"""40단계 질문 묶음 짓기(문서/40단계.md '질문 묶음') — 측정 전에 커밋한다. 씨앗 40.

  python -I -X utf8 재기/질문40.py <LCB test_sets.zip> <LCB LICENSE> <gsm8k-test.arrow> <Qwen2.5 GGUF(토크나이저)>

시험/질문40/ 에: 자연_LCB · 자연_긴글 · 자연_수학 · 자연_수학_더 · 방아쇠_글자 · 방아쇠_언어 · 방아쇠_되풀이 · 오염 (.jsonl),
출처.md, LICENSE-LCB.txt. 오염 대화의 비정상 넣기(오염넣기)도 여기 — 수집 도구가 첫 답에 쓴다.
"""
import csv
import hashlib
import io
import json
import os
import random
import re
import struct
import sys
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, ".."))
sys.path.insert(0, os.path.join(ROOT, "엔진"))
sys.path.insert(0, HERE)
OUT = os.path.join(ROOT, "시험", "질문40")
씨앗 = 40


# ---------------------------------------------------------------- 조사
def 받침(낱말):
    for ch in reversed(낱말.strip().rstrip("'\"’”")):
        cp = ord(ch)
        if 0xAC00 <= cp <= 0xD7A3:
            return (cp - 0xAC00) % 28
        if ch.isalnum():
            return 1
    return 0


def 을를(w):
    return w + ("을" if 받침(w) else "를")


def 은는(w):
    return w + ("은" if 받침(w) else "는")


def 이가(w):
    return w + ("이" if 받침(w) else "가")


def 과와(w):
    return w + ("과" if 받침(w) else "와")


def 으로로(w):
    b = 받침(w)
    return w + ("으로" if b and b != 8 else "로")


def 따옴(w, 조사함수):
    """'낱말'+조사 — 조사는 따옴표 앞 낱말의 받침으로."""
    return 조사함수(w).replace(w, "'" + w + "'", 1)


# ---------------------------------------------------------------- gsm8k (Arrow IPC 흐름 — 작은 읽개)
def _u16(b, o): return struct.unpack_from("<H", b, o)[0]
def _i32(b, o): return struct.unpack_from("<i", b, o)[0]
def _u32(b, o): return struct.unpack_from("<I", b, o)[0]
def _i64(b, o): return struct.unpack_from("<q", b, o)[0]


def _자리(fb, 표, i):
    """flatbuffer 표(위치)의 i 번째 필드의 절대 위치(없으면 None)."""
    vt = 표 - _i32(fb, 표)
    vs = _u16(fb, vt)
    o = 4 + 2 * i
    if o >= vs:
        return None
    off = _u16(fb, vt + o)
    return 표 + off if off else None


def 화살읽기(경로, 열수=2):
    """HF datasets 의 .arrow(IPC 흐름) — 문자열 열들만. 돌려줌: [[열0 값…], [열1 값…]]."""
    d = open(경로, "rb").read()
    pos = 0
    열 = [[] for _ in range(열수)]
    while pos + 8 <= len(d):
        if _i32(d, pos) == -1:
            pos += 4
        mlen = _i32(d, pos)
        pos += 4
        if mlen == 0:
            break
        fb = d[pos:pos + mlen]
        root = _u32(fb, 0)
        종류 = fb[_자리(fb, root, 1)] if _자리(fb, root, 1) is not None else 0
        hp = _자리(fb, root, 2)
        bl = _i64(fb, _자리(fb, root, 3)) if _자리(fb, root, 3) is not None else 0
        몸 = d[pos + mlen:pos + mlen + bl]
        if 종류 == 3:                                   # RecordBatch
            rb = hp + _u32(fb, hp)
            n = _i64(fb, _자리(fb, rb, 0))
            bp = _자리(fb, rb, 2)
            bv = bp + _u32(fb, bp)
            nb = _u32(fb, bv)
            bufs = [(_i64(fb, bv + 4 + 16 * k), _i64(fb, bv + 4 + 16 * k + 8)) for k in range(nb)]
            assert nb == 3 * 열수, f"버퍼 {nb} — 문자열 열 {열수} 개가 아니다"
            for c in range(열수):
                (oo, ol), (do, dl) = bufs[3 * c + 1], bufs[3 * c + 2]
                offs = struct.unpack_from(f"<{n + 1}i", 몸, oo)
                data = 몸[do:do + dl]
                열[c] += [data[offs[i]:offs[i + 1]].decode("utf-8") for i in range(n)]
        pos += mlen + bl
    return 열


# ---------------------------------------------------------------- 낱말 목록
주제들 = """봄철 등산|김장 문화|지하철 출퇴근|반려견 산책|커피의 역사|한글의 창제|장마철 건강 관리|도시 텃밭|전통 시장|독서 모임|
자전거 여행|제주도 바다|겨울 캠핑|라면 끓이기|초등학교 운동회|할머니의 부엌|첫 월급|이사하는 날|동네 도서관|밤하늘의 별자리|
태풍 대비|김치찌개|한옥 마을|고양이 키우기|스마트폰 사용 습관|재활용 분리배출|수능 시험|군대 생활|결혼식 풍경|명절 귀성길|
비 오는 날의 산책|동해 일출|가을 단풍 구경|겨울 스키장|시골 장날|바둑 두기|피아노 연습|마라톤 완주|아파트 층간소음|편의점 야간 근무|
택배 기사의 하루|미세먼지|전기차|인공지능 비서|온라인 수업|재택근무|중고 거래|동네 빵집|떡볶이|한강 공원|
북한산 둘레길|경주 여행|부산 국제시장|강릉 커피거리|전주 비빔밥|판소리|탈춤|사물놀이|서예|도자기 만들기|
봄나물 캐기|여름 장마|추석 송편|설날 떡국|동지 팥죽|정월 대보름|단오 그네뛰기|한복 입기|국악 공연|민속 박물관|
지리산 종주|설악산 단풍|남해 다랭이논|순천만 갈대밭|안동 하회마을|수원 화성|창덕궁 후원|종묘 제례|훈민정음 해례본|조선왕조실록|
동의보감|거북선|측우기|해시계|첨성대|석굴암|팔만대장경|고려청자|백자 달항아리|김홍도의 풍속화|
신윤복의 미인도|정약용의 목민심서|세종대왕의 업적|이순신 장군|안중근 의사|유관순 열사|김구 선생|장영실|허준|신사임당"""
주제들 = [s.strip() for s in 주제들.replace("\n", "").split("|")]

소리말 = """꾀죄죄 쭈뼛쭈뼛 삐죽빼죽 오돌토돌 꼬깃꼬깃 쪼글쪼글 쫀득쫀득 뾰족뾰족 왁자지껄 옹알옹알 쫑알쫑알 꿈지럭꿈지럭 꼼지락꼼지락
엉금엉금 깡충깡충 껑충껑충 폴짝폴짝 살랑살랑 너울너울 출렁출렁 와르르 후드득 토독토독 콸콸 쨍그랑 딸그락 덜그럭 뽀드득 뿌드득 쩝쩝
후루룩 홀짝홀짝 꿀꺽꿀꺽 오물오물 냠냠 딸꾹딸꾹 쿨럭쿨럭 깔깔 낄낄 키득키득 히죽히죽 싱글벙글 찡긋 갸우뚱 끄덕끄덕 움찔 흠칫 화들짝
털썩 풀썩 철퍼덕 첨벙첨벙 퐁당퐁당 찰방찰방 휘청휘청 비척비척 터벅터벅 뚜벅뚜벅 성큼성큼 아장아장 사뿐사뿐 엉거주춤 꾸벅꾸벅 끔뻑끔뻑
말똥말똥 초롱초롱 번뜩 섬뜩 오싹 으슬으슬 부들부들 오들오들 바들바들 욱신욱신 지끈지끈 뜨끈뜨끈 삐걱삐걱 덜컹덜컹 부릉부릉 뻐끔뻐끔
쌔근쌔근 칭얼칭얼 쫄랑쫄랑 촐랑촐랑 꼴깍 꿀렁꿀렁 뭉게뭉게 몽글몽글 보슬보슬 추적추적 주룩주룩 철썩철썩 휘잉 쌩쌩 씽씽 윙윙 왱왱
웽웽 꽥꽥 삐약삐약 꼬꼬댁 짹짹 뻐꾹뻐꾹 부엉부엉 개굴개굴 맴맴 찌르르 귀뚤귀뚤""".split()
물건들 = """똬리 쐐기 꽹과리 괭이 호미 쇠스랑 도리깨 맷돌 절구 디딜방아 물레방아 멍석 덕석 가마니 삼태기 소쿠리 조리 함지박 뚝배기 옹기
장독 시루 화로 풍로 구들장 굴뚝 뒤주 반닫이 궤짝 고리짝 경대 등잔 호롱 초롱 탕건 망건 두루마기 마고자 배자 댕기 비녀 노리개 족두리
꽃신 짚신 미투리 나막신 버선 대님 토시 벙거지 패랭이 삿갓 도롱이 지게 바지게 쟁기 써레 곰방메 꼴망태 새끼줄 짚단 볏짚 골무 바늘쌈
실꾸리 물레 베틀""".split()
생물들 = """꿩 뜸부기 뻐꾸기 꾀꼬리 딱따구리 쇠똥구리 땅강아지 귀뚜라미 베짱이 여치 쓰르라미 반딧불이 소금쟁이 물방개 송사리 미꾸라지
쏘가리 꺽지 퉁가리 동자개 가물치 꼴뚜기 쭈꾸미 뽈락 쥐치 꽁치 넙치 도다리 쑥부쟁이 엉겅퀴 씀바귀 고들빼기 꽈리 앵두 오디 머루 다래
으름 개암 도토리 상수리 솔방울 괭이밥 쐐기풀 쇠비름 꿀풀 뚱딴지""".split()
성들 = "곽 탁 편 뇌 섭 궉 견 묵 빙 옹 십 엽 팽 봉 용".split()
이름들 = """뙤순 쫑희 꽹이 뾰롱 쀼리 쑥이 뙈미 쫀이 꿩이 똘이 뺑덕 쌕이 뚱이 쎄미 쒸리 똠이 꽉이 땡이 삑이 쫑이 뿌니 꾀돌 쭈니 뽀미
쪼롱 뚜리 까미 꼬미 뭉치""".split()
장소들 = """뒤뜰 툇마루 장독대 부뚜막 뙈기밭 개울가 고갯마루 솔숲 대숲 텃밭 우물가 정자 나루터 섬돌 곳간 다랭이논 물레방앗간 징검다리
돌담길 싸리문""".split()


def 글자글들(rng, 표, 수, 토크나이저):
    """방아쇠 · 글자의 글: 80 ~ 200 자, 그 모델(Qwen2.5) 어휘에서 두 토큰 이상에 걸쳐 나오는 음절이 여섯 개 이상."""
    import 증상40 as Z
    틀 = [
        lambda: f"{은는(rng.choice(성들) + rng.choice(이름들))} {을를(rng.choice(물건들))} 챙겨 {으로로(rng.choice(장소들))} {rng.choice(소리말)} 걸어갔다.",
        lambda: f"{rng.choice(장소들)}에서 {rng.choice(소리말)} 소리가 나자 {은는(rng.choice(성들) + rng.choice(이름들))} {rng.choice(소리말)} 고개를 들었다.",
        lambda: f"{이가(rng.choice(생물들))} {rng.choice(소리말)} 울던 날, {은는(rng.choice(성들) + rng.choice(이름들))} {rng.choice(물건들)} 옆에 앉아 있었다.",
        lambda: f"{rng.choice(성들) + rng.choice(이름들)}의 {rng.choice(물건들)}에는 {rng.choice(생물들)} 그림이 새겨져 있었다.",
        lambda: f"바람이 불자 {rng.choice(장소들)}의 {이가(rng.choice(물건들))} {rng.choice(소리말)} 흔들렸다.",
        lambda: f"{은는(rng.choice(성들) + rng.choice(이름들))} {을를(rng.choice(생물들))} 보며 {rng.choice(소리말)} 웃었다.",
        lambda: f"{rng.choice(장소들)}에 둔 {rng.choice(물건들)}에서 {rng.choice(소리말)} 소리가 났다.",
        lambda: f"할머니는 {과와(rng.choice(물건들))} {을를(rng.choice(물건들))} {rng.choice(성들) + rng.choice(이름들)}에게 건네주었다.",
        lambda: f"{rng.choice(소리말)} 내리는 비를 맞으며 {은는(rng.choice(성들) + rng.choice(이름들))} {을를(rng.choice(장소들))} 지났다.",
        lambda: f"{rng.choice(생물들)} 한 마리가 {rng.choice(장소들)}에서 {rng.choice(소리말)} 움직였다.",
    ]
    out, 본 = [], set()
    시도 = 0
    while len(out) < 수:
        시도 += 1
        assert 시도 < 100000, "글자 글을 다 짓지 못했다"
        문장 = []
        while len(" ".join(문장)) < 80:
            문장.append(rng.choice(틀)())
        글 = " ".join(문장)
        if not 80 <= len(글) <= 200 or 글 in 본:
            continue
        쪼갬, 음절 = Z.쪼개진음절수(토크나이저.나누기(글), 표)
        if 쪼갬 < 6:
            continue
        본.add(글)
        out.append((글, 쪼갬, 음절))
    return out


한자들 = """溫故知新 以心傳心 臥薪嘗膽 守株待兎 塞翁之馬 漁父之利 苦盡甘來 自業自得 結者解之 他山之石 切磋琢磨 磨斧作針 螢雪之功 鷄口牛後
杞人之憂 矛盾 蛇足 推敲 完璧 登龍門 背水陣 四面楚歌 破竹之勢 朝三暮四 刻舟求劍 北京 上海 西安 杭州 成都 蘇州 洛陽 南京 孔子 老子 孟子
諸葛亮 曹操 李白 杜甫 東京 京都 大阪 奈良 侘び寂び 生き甲斐 木漏れ日 物の哀れ 一期一会 改善""".split()
언어틀 = [
    lambda x: f"'{x}' — 이 말의 뜻과 유래를 한국어로 자세히 설명해 줘.",
    lambda x: f"{x}에 얽힌 이야기를 한국어로 세 문단 정도로 들려줘.",
    lambda x: f"'{x}' — 한국어로 어떻게 읽는지, 요즘 어떤 때 쓰면 좋은지 예문 세 개와 함께 한국어로 알려 줘.",
    lambda x: f"'{x}' — 비슷한 뜻의 우리말 표현 다섯 가지를 찾아 견주어 설명해 줘. 답은 한국어로 써 줘.",
]

되풀이낱말 = "사랑해 고마워 안녕하세요 바나나 하늘 행복 감사합니다 미안해 괜찮아 좋아요 고양이 커피 봄비 별빛 파도 메아리 동그라미 무지개 다람쥐 해바라기".split()
되풀이문장 = ["오늘도 좋은 하루 보내세요.", "나는 매일 아침 일찍 일어난다.", "바다는 넓고 하늘은 푸르다.", "작은 것부터 차근차근 해 보자.",
          "고양이가 창가에서 졸고 있다.", "비가 오면 우산을 챙기자.", "책을 읽으면 마음이 편해진다.", "우리는 함께 길을 걸었다.",
          "따뜻한 차 한 잔이 생각난다.", "별이 빛나는 밤이었다."]
무늬들 = ["가나 가나다 가나다라", "하나 둘 셋 / 하나 둘 셋 넷", "ㄱㄴㄷ ㄱㄴㄷㄹ", "봄 여름 가을 겨울", "도레미 도레미파", "월 화 수 목 금",
        "가위 바위 보", "동 서 남 북", "1 2 3 / 1 2 3 4", "아야어여오요우유으이"]


def 되풀이질문들(rng, 수):
    """모든 조합(276 가지)을 지어 씨앗으로 섞고 앞에서 수 개."""
    모두 = []
    모두 += [f"{따옴(w, 을를)} {n}번 이어서 써 줘. 다른 말은 쓰지 마." for w in 되풀이낱말 for n in (30, 50, 100, 150, 200)]
    모두 += [f"다음 문장을 {n}번 그대로 되풀이해 써 줘: {s}" for s in 되풀이문장 for n in (10, 20, 30, 40, 50)]
    모두 += [f"1부터 {n}까지 숫자를 한글로(일, 이, 삼, …) 차례로 써 줘." for n in (100, 150, 200, 300, 400, 500)]
    모두 += [f"다음 무늬를 계속 이어서 {n}줄 써 줘:\n{p}" for p in 무늬들 for n in (20, 30, 50, 80)]
    모두 += [f"{따옴(w, 으로로)} 시작하는 문장을 {n}개 써 줘. 모든 문장은 {따옴(w, 으로로)} 시작해야 해." for w in 되풀이낱말 for n in (20, 30, 40, 50)]
    assert len(모두) == len(set(모두)) == 276, len(모두)
    rng.shuffle(모두)
    return 모두[:수]


긴글틀 = [
    ("설명", lambda w: f"'{w}'에 대해 자세히 설명하는 글을 2,000자 이상 써 줘."),
    ("이야기", lambda w: f"{따옴(w, 을를)} 소재로 한 이야기를 2,000자 이상 지어 줘."),
    ("목록", lambda w: f"{따옴(w, 과와)} 관련해 알아 두면 좋은 점을 번호를 붙여 20가지 이상 쓰고, 항목마다 두세 문장으로 설명해 줘. 모두 합쳐 2,000자 이상으로."),
    ("편지", lambda w: f"'{w}'에 얽힌 추억을 담아 오랜 친구에게 보내는 편지를 2,000자 이상 써 줘."),
    ("견줌", lambda w: f"'{w}'의 옛날과 요즘을 견주는 글을 2,000자 이상 써 줘."),
]
수학지시 = "Please reason step by step, and put your final answer within \\boxed{}."
옮김지시 = "다음 글을 한 글자도 바꾸지 말고 그대로 옮겨 써."
오염둘째 = "고마워. 이어서 다음 글을 한 글자도 바꾸지 말고 그대로 옮겨 쓴 뒤, 그 뜻을 한 문장으로 설명해 줘."
오염한자 = ["因此", "然而", "所以", "但是", "其实"]


# ---------------------------------------------------------------- 오염 넣기(첫 답에 비정상 하나)
_문장끝 = re.compile(r"(?<=[.!?。])\s+|\n+")


def 오염넣기(답, 종류, 번호):
    """첫 답(답)의 가운데 문장에 비정상 하나. 종류: '깨끗' · '다른문자' · '맞춤법' · '되풀이'. 돌려줌: (바꾼 답, 기록)."""
    if 종류 == "깨끗":
        return 답, {"종류": 종류}
    조각 = [(m.start(), m.end()) for m in _문장끝.finditer(답)]
    경계 = [0] + [e for _, e in 조각] + [len(답)]
    문장들 = [(경계[i], (조각[i][0] if i < len(조각) else len(답))) for i in range(len(경계) - 1)]
    문장들 = [(s, e) for s, e in 문장들 if 답[s:e].strip()]
    if not 문장들:
        return 답, {"종류": 종류, "못함": "문장 없음"}
    s, e = 문장들[len(문장들) // 2]
    if 종류 == "다른문자":
        w = 오염한자[번호 % len(오염한자)]
        return 답[:s] + w + " " + 답[s:], {"종류": 종류, "자리": s, "넣음": w}
    if 종류 == "되풀이":
        문 = 답[s:e]
        return 답[:e] + " " + 문 + 답[e:], {"종류": 종류, "자리": e, "넣음": 문}
    if 종류 == "맞춤법":
        한 = [i for i in range(s, e) if 0xAC00 <= ord(답[i]) <= 0xD7A3]
        if len(한) < 3:
            return 답, {"종류": 종류, "못함": "한글이 모자람"}
        i = 한[2]
        cp = ord(답[i]) - 0xAC00
        b = cp % 28
        새 = chr(0xAC00 + cp - b + (4 if b == 0 else 0))
        return 답[:i] + 새 + 답[i + 1:], {"종류": 종류, "자리": i, "앞": 답[i], "뒤": 새}
    raise ValueError(종류)


# ---------------------------------------------------------------- 짓기
def 쓰기(이름, 줄들):
    p = os.path.join(OUT, 이름)
    with open(p, "w", encoding="utf-8", newline="\n") as f:
        for r in 줄들:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


def main():
    lcb_zip, lcb_lic, gsm_arrow, qwen_gguf = sys.argv[1:5]
    import 토크나이저 as TK
    import 증상40 as Z
    os.makedirs(OUT, exist_ok=True)
    해시 = {}

    # 자연 · LCB 한국어
    z = zipfile.ZipFile(lcb_zip)
    lcb = []
    for 원천 in ("monolingual/native", "crosslingual/okapi", "crosslingual/sharegpt", "crosslingual/complex_prompts"):
        rows = list(csv.DictReader(io.StringIO(z.read(f"test_sets/{원천}/ko.csv").decode("utf-8"))))
        for i, r in enumerate(rows):
            lcb.append({"id": f"lcb_{원천.split('/')[1]}_{i:03d}", "묶음": "자연_LCB", "messages": [{"role": "user", "content": r["prompt"]}],
                        "최대": 1024, "질문": r["prompt"], "모델": ["7b", "05b"]})
    해시["자연_LCB.jsonl"] = 쓰기("자연_LCB.jsonl", lcb)

    # 자연 · 긴 글
    긴 = []
    for i, w in enumerate(주제들[:60]):
        for 꼴, 틀 in 긴글틀:
            q = 틀(w)
            긴.append({"id": f"긴글_{i:02d}_{꼴}", "묶음": "자연_긴글", "messages": [{"role": "user", "content": q}], "최대": 2048,
                      "질문": q, "모델": ["7b", "05b"]})
    해시["자연_긴글.jsonl"] = 쓰기("자연_긴글.jsonl", 긴)

    # 자연 · 수학
    문, 답 = 화살읽기(gsm_arrow, 2)
    assert len(문) == 1319, len(문)
    수학 = [{"id": f"gsm_{i:04d}", "묶음": "자연_수학", "messages": [{"role": "user", "content": 문[i] + "\n" + 수학지시}], "최대": 3200,
           "질문": 문[i], "정답": Z.정답수(답[i]), "모델": ["r1", "05b"]} for i in range(1200)]
    해시["자연_수학.jsonl"] = 쓰기("자연_수학.jsonl", 수학[:600])
    해시["자연_수학_더.jsonl"] = 쓰기("자연_수학_더.jsonl", 수학[600:])

    # 방아쇠 · 글자 (+ 오염 둘째 말의 글)
    tk = TK.Qwen토크나이저(gguf=qwen_gguf)
    표, _ = Z.바이트표(qwen_gguf)
    rng = random.Random(씨앗)
    글들 = 글자글들(rng, 표, 300, tk)
    글자 = [{"id": f"글자_{i:03d}", "묶음": "방아쇠_글자", "messages": [{"role": "user", "content": 옮김지시 + "\n\n" + g}], "최대": 512,
           "질문": 옮김지시 + "\n\n" + g, "원문": g, "쪼갠음절": 쪼, "음절": 음, "모델": ["7b", "05b"]} for i, (g, 쪼, 음) in enumerate(글들[:200])]
    해시["방아쇠_글자.jsonl"] = 쓰기("방아쇠_글자.jsonl", 글자)

    # 방아쇠 · 언어
    언어 = []
    for i, x in enumerate(한자들):
        for j, 틀 in enumerate(언어틀):
            q = 틀(x)
            언어.append({"id": f"언어_{i:02d}_{j}", "묶음": "방아쇠_언어", "messages": [{"role": "user", "content": q}], "최대": 1024,
                       "질문": q, "모델": ["7b", "05b"]})
    assert len(언어) == 200, len(언어)
    해시["방아쇠_언어.jsonl"] = 쓰기("방아쇠_언어.jsonl", 언어)

    # 방아쇠 · 되풀이
    rng = random.Random(씨앗 + 1)
    되 = [{"id": f"되풀이_{i:03d}", "묶음": "방아쇠_되풀이", "messages": [{"role": "user", "content": q}], "최대": 2048, "질문": q,
          "모델": ["7b", "05b"]} for i, q in enumerate(되풀이질문들(rng, 200))]
    해시["방아쇠_되풀이.jsonl"] = 쓰기("방아쇠_되풀이.jsonl", 되)

    # 오염 대화
    오 = []
    for i, w in enumerate(주제들):
        g, 쪼, 음 = 글들[200 + i]
        오.append({"id": f"오염_{i:03d}", "묶음": "오염", "q1": f"'{w}'에 대해 다섯 문장으로 설명해 줘.", "q2": 오염둘째 + "\n\n" + g,
                  "원문": g, "최대1": 512, "최대2": 1024, "모델": ["7b"]})
    assert len(오) == 100
    해시["오염.jsonl"] = 쓰기("오염.jsonl", 오)

    # 출처 · 라이선스
    with open(os.path.join(OUT, "LICENSE-LCB.txt"), "w", encoding="utf-8", newline="\n") as f:
        f.write(open(lcb_lic, encoding="utf-8").read())
    zh = hashlib.sha256(open(lcb_zip, "rb").read()).hexdigest()
    gh = hashlib.sha256(open(gsm_arrow, "rb").read()).hexdigest()
    쪼갬평균 = sum(r["쪼갠음절"] for r in 글자) / len(글자)
    with open(os.path.join(OUT, "출처.md"), "w", encoding="utf-8", newline="\n") as f:
        f.write(f"""# 40단계 질문 묶음 — 출처 · 라이선스 · 해시

`재기/질문40.py` 가 지었다(씨앗 {씨앗}). 측정 전에 커밋한다([문서/40단계.md](../../문서/40단계.md) '질문 묶음').

| 파일 | 수 | 원천 |
|---|---|---|
| 자연_LCB.jsonl | {len(lcb)} | Language Confusion Benchmark(arXiv 2406.20052) 의 한국어 — `test_sets/monolingual/native/ko.csv` · `crosslingual/{{okapi,sharegpt,complex_prompts}}/ko.csv`. Apache-2.0([LICENSE-LCB.txt](LICENSE-LCB.txt)), GitHub `Cohere-Labs-Community/language-confusion` 커밋 0cfdbb4a64502648938c456b2fa9689968f22298, test_sets.zip SHA-256 {zh} |
| 자연_긴글.jsonl | {len(긴)} | 새로 씀 — 주제 60 × 꼴 5(설명 · 이야기 · 목록 · 편지 · 견줌) |
| 자연_수학.jsonl · 자연_수학_더.jsonl | 600 · 600 | gsm8k test(Cobbe et al. 2021, MIT — `openai/gsm8k` main) 의 앞 1,200 문항, 끝에 "{수학지시}". Hugging Face datasets 캐시의 gsm8k-test.arrow SHA-256 {gh} |
| 방아쇠_글자.jsonl | {len(글자)} | 새로 씀 — 이름 · 소리말 · 옛 물건 · 생물 낱말을 틀 문장 열에 넣은 80 ~ 200 자의 글, Qwen2.5 어휘에서 두 토큰 이상에 걸치는 음절 6 개 이상(평균 {쪼갬평균:.1f} 개) |
| 방아쇠_언어.jsonl | {len(언어)} | 새로 씀 — 한자말 · 중국 · 일본의 이름 · 말 50 개 × 틀 넷 |
| 방아쇠_되풀이.jsonl | {len(되)} | 새로 씀 — 낱말 · 문장 되풀이, 한글로 수 세기, 무늬 이어 쓰기, 같은 말로 시작하는 문장 |
| 오염.jsonl | {len(오)} | 새로 씀 — 첫 말 '주제 100 개를 다섯 문장으로', 둘째 말 '그대로 옮겨 쓰고 뜻을 한 문장으로'(글자 묶음과 같은 방식의 다른 글 100 개) |

파일의 SHA-256:

""")
        for k, v in 해시.items():
            f.write(f"- `{k}` — {v}\n")
    for k, v in 해시.items():
        print(k, v)
    print("글자 글의 쪼갠 음절 평균", round(쪼갬평균, 2), "· 길이", min(len(r["원문"]) for r in 글자), "~", max(len(r["원문"]) for r in 글자))


if __name__ == "__main__":
    main()
