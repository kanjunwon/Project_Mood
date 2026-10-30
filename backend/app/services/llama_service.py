import os
import re

MOCK_MODE = os.environ.get("MOCK_MODE", "false").lower() == "true"


# ---------- 생성 설정 (patch 12) ----------
# 서버에서 코드 수정 없이 비교할 수 있게 .env로 뺌. 값은 호출할 때마다 다시 읽음.
def _env_float(name: str, default: float) -> float:
    try:
        return float(os.environ.get(name, "").strip() or default)
    except ValueError:
        return default


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, "").strip() or default)
    except ValueError:
        return default


def get_generation_config() -> dict:
    """
    LLM_REPETITION_PENALTY (기본 1.05): 예전 1.2는 '프롬프트 전체'(예시 일기 포함 약 1,400토큰)에 감점이 걸려서
        '~했다', '~더라' 같은 자연스러운 일기 표현까지 피하게 만들었음. 일기/이미지 변환 공통.
    LLM_TOP_P (기본 0.9)
    DIARY_NO_REPEAT_NGRAM (기본 4): 같은 4토큰 묶음 반복만 막음 (반복 방지는 이걸로 대신함)
    DIARY_TEMPERATURES (기본 "0.45,0.55,0.65"): 시도별 온도. patch 12에서 0.6~0.9로 올렸더니 입력에 없는 메뉴/소품을
        지어내는 일이 늘어서(짬뽕 -> 새우튀김) patch 13에서 예전 첫 시도 값(0.45)부터 조금씩만 올리게 바꿈
    DIARY_MIN_CHARS / DIARY_MAX_CHARS (기본 60 / 350): 예전 상한 200자 때문에 일기가 짧게만 통과했음
    DIARY_BLOCK_WORDS (기본 true): 입력에 없는 식사시간대/술 종류/관계 단어를 생성 단계에서 금지
    """
    temps = []
    for part in (os.environ.get("DIARY_TEMPERATURES", "") or "0.45,0.55,0.65").split(","):
        try:
            temps.append(float(part))
        except ValueError:
            pass
    return {
        "repetition_penalty": _env_float("LLM_REPETITION_PENALTY", 1.05),
        "top_p": _env_float("LLM_TOP_P", 0.9),
        "no_repeat_ngram_size": _env_int("DIARY_NO_REPEAT_NGRAM", 4),
        "temperatures": temps or [0.45, 0.55, 0.65],
        "min_chars": _env_int("DIARY_MIN_CHARS", 60),
        "max_chars": _env_int("DIARY_MAX_CHARS", 350),
        "block_words": os.environ.get("DIARY_BLOCK_WORDS", "true").strip().lower() not in ("0", "false", "no", "off"),
    }

SYSTEM_PREAMBLE = (
    "A chat between a curious user and an artificial intelligence assistant. "
    "The assistant는 20대 대학생 본인이다. 그날 있었던 일을 그냥 편하게 적어두는 개인 일기를 쓴다.\n\n"
    "[가장 중요한 전제]\n"
    "너는 아래 다섯 가지 정보(무엇을, 이유, 누구와, 언제, 어디서) 외에는 그날 무슨 일이 "
    "있었는지 모른다.\n\n"
    "[규칙]\n"
    "1. 반말 일기체로 쓴다. '~했다', '~하더라', '~잖아', '~하나' 등 자연스러운 어미를 "
    "섞어 쓴다. 존댓말은 절대 쓰지 않는다.\n"
    "2. 담백하게 쓴다: 교훈적으로 정리하거나 요약하며 끝내지 않는다 ('~덕분에', '~을 선사했다', "
    "'~라는 걸 느꼈다', '최고의 하루였다', '완벽한 하루였다' 같은 문장으로 마무리하지 않는다). "
    "과장된 비유도 쓰지 않는다 ('마법처럼', '환상적인', '하늘을 날아갈 것 같았다', "
    "'세상을 다 가진 기분' 등). 그냥 있었던 일 적고 끝내거나 사소한 잡생각으로 "
    "끝나도 된다.\n"
    "3. 문장 길이를 들쭉날쭉하게 쓴다. 짧게 끊는 문장과 길게 이어지는 문장을 섞는다.\n"
    "4. 분량은 3~4문장, 100자 안팎으로 쓴다. 정보가 적어도 그날의 장소 분위기, 몸 상태, 사소한 "
    "잡생각 같은 일반적인 배경으로 채워서 한 문장짜리로 끝내지 않는다.\n"
    "5. 디테일을 채울 땐 위험도를 구분해서 판단해라:\n"
    "   - 괜찮음: 그 장소/상황에서 흔히 있는 배경 묘사 (예: 공원이면 사람들, 생일이면 케이크 정도의 "
    "일반적인 소품) - 이 정도는 자연스러움을 위해 살짝 곁들여도 된다.\n"
    "   - 절대 금지: 확인할 수 없는 결과나 판단(예: '시험을 잘 봤다', '다들 좋아했다'), 구체적인 "
    "대화 내용, 술, 정확한 식사 시간대(아침/점심/저녁) - 이런 건 틀렸을 때 완전히 어색해지는 "
    "내용이라 무슨 일이 있어도 지어내면 안 된다. 애매하게 돌려 말해라.\n"
    "6. '다행이다/다행히'는 한 번 이상 쓰지 않는다.\n"
    "7. 외래어 대신 순수 한국어를 쓴다.\n"
    "8. '어디서' 정보를 그대로 따른다: '친구네 집'이면 내가 친구 집에 간 것이고, '본가'면 "
    "내가 부모님 댁에 간 것이다. 절대 방향을 반대로 바꿔서 '친구가 우리 집에 왔다'처럼 "
    "쓰지 않는다.\n"
)

FEWSHOT_EXAMPLES = (
    "Human: 다음 정보를 바탕으로 감성적인 일기를 작성해라:\n\n"
    "무엇을: 늦은 밤 혼자 동네 자전거 라이딩\n"
    "이유: 하루 종일 답답했던 마음을 시원한 밤바람으로 날려버리고 싶어서\n"
    "누구와: 혼자\n"
    "언제: 밤 11시\n"
    "어디서: 동네 하천변 자전거도로\n"
    "Assistant:\n"
    "하루 종일 답답해서 그냥 자전거 끌고 나왔다. 밤이라 그런지 하천변에 사람도 별로 없고 조용했다. "
    "한 바퀴 도는데 바람이 좀 차긴 했는데 그것도 나쁘지 않았다. 중간에 벤치에 앉아서 핸드폰도 안 보고 "
    "그냥 멍하니 있다가 왔다. 집에 오니까 좀 살 것 같아서 씻고 바로 잤다.\n\n"
    "Human: 다음 정보를 바탕으로 감성적인 일기를 작성해라:\n\n"
    "무엇을: 오랜만에 친구와 전화 통화\n"
    "이유: 요즘 서로 바빠서 연락이 뜸했는데, 오랜만에 목소리 들으니 반가워서\n"
    "누구와: 친구\n"
    "언제: 저녁 9시\n"
    "어디서: 자취방 침대 위\n"
    "Assistant:\n"
    "저녁 먹고 누워있는데 갑자기 걔한테 연락이 왔다. 뭐 하냐고 물어보길래 그냥 누워있다고 했더니 "
    "지도 똑같다면서 웃었다. 별 얘기도 안 했는데 이런저런 얘기하다 보니까 한 시간 넘게 통화했다. "
    "요즘 서로 사는 게 바빠서 이런 것도 오랜만이다.\n\n"
    "Human: 다음 정보를 바탕으로 감성적인 일기를 작성해라:\n\n"
    "무엇을: 주말에 본가 방문\n"
    "이유: 자취하느라 계속 대충 먹다가, 오랜만에 부모님이 해주시는 밥 먹고 싶어서\n"
    "누구와: 가족\n"
    "언제: 토요일 낮 12시\n"
    "어디서: 본가\n"
    "Assistant:\n"
    "토요일 아침에 짐 좀 챙겨서 본가로 내려갔다. 도착하니까 엄마가 벌써 점심 준비하고 계셨다. "
    "오랜만에 집밥 먹으니까 확실히 맛이 다르긴 다르더라. 아빠랑 티비 좀 보다가 저녁까지 먹고 자취방으로 올라왔다.\n\n"
    "Human: 다음 정보를 바탕으로 감성적인 일기를 작성해라:\n\n"
    "무엇을: 친구랑 카페에서 수다\n"
    "이유: 오랜만에 만나서 반가워서\n"
    "누구와: 친구\n"
    "언제: 저녁 7시\n"
    "어디서: 동네 카페\n"
    "Assistant:\n"
    "저녁에 동네 카페에서 오랜만에 걔를 만났다. 얼굴 본 지 꽤 됐는데 만나니까 어색함 하나 없었다. "
    "몇 시간을 떠들었는지도 모르겠다. 다음에 또 이렇게 보자고 하고 헤어졌다.\n\n"
    "Human: 다음 정보를 바탕으로 감성적인 일기를 작성해라:\n\n"
    "무엇을: 친구 생일 축하\n"
    "이유: 친한 친구 생일이라 챙겨주고 싶어서\n"
    "누구와: 친구\n"
    "언제: 저녁\n"
    "어디서: 친구네 집\n"
    "Assistant:\n"
    "친구 생일이라고 해서 저녁에 걔네 집으로 갔다. 다른 애들도 몇 명 와있었다. 다 같이 앉아서 "
    "이런저런 얘기 나누다 보니 시간 가는 줄 몰랐다. 늦게까지 있다가 집으로 왔다.\n"
)

FORBIDDEN_PHRASES = (
    "도와드릴까요", "궁금하신", "다행이에요", "그러셨군요", "질문해주세요", "제가 그 자리에",
    "기억나?", "그치?", "그렇지?", "알지?", "그지?"
)

RELATION_KEYWORDS = (
    "형", "언니", "누나", "오빠", "동료", "남편", "아내", "여자친구", "남자친구",
    "선배", "후배", "교수님", "사수", "팀장", "과장", "사장"
)

IMPLIED_RELATION_TRIGGERS = {
    "상담": ["교수님"], "진로": ["교수님"], "지도교수": ["교수님"],
    "회식": ["동료", "선배", "후배", "팀장", "과장", "사장", "사수"],
    "출근": ["동료", "선배", "후배", "팀장", "과장", "사장", "사수"],
    "부서": ["동료", "선배", "후배", "팀장", "과장", "사장", "사수"],
    "회사": ["동료", "선배", "후배", "팀장", "과장", "사장", "사수"],
    "사수": ["사수", "선배"], "면접": ["면접관"],
}

ALCOHOL_KEYWORDS = ("소주", "맥주", "막걸리", "와인", "폭탄주", "술")
MEALTIME_KEYWORDS = ("아침", "점심", "저녁", "새벽")

# patch 13: 입력에 없는 음식/메뉴 지어내기 검사 ("짬뽕 먹음"인데 "새우튀김도 시켰다")
# 2글자 이상만. '밥', '빵', '회', '떡'처럼 한 글자는 다른 단어 속에 너무 자주 섞여서 제외
FOOD_KEYWORDS = (
    # 중식
    "짜장면", "자장면", "짬뽕", "탕수육", "군만두", "만두", "볶음밥", "새우튀김", "깐풍기", "유린기", "양장피",
    "마라탕", "마라샹궈", "꿔바로우",
    # 한식
    "김치찌개", "된장찌개", "부대찌개", "순두부", "찌개", "전골", "국밥", "순대국", "설렁탕", "갈비탕", "삼계탕",
    "감자탕", "해장국", "비빔밥", "김밥", "삼각김밥", "떡볶이", "떡국", "순대", "튀김", "어묵", "오뎅",
    "라면", "컵라면", "냉면", "칼국수", "수제비", "국수", "불고기", "갈비", "삼겹살", "목살", "고기", "곱창", "막창",
    "족발", "보쌈", "닭갈비", "찜닭", "제육", "김치", "파전", "김치전", "계란말이", "계란찜", "도시락", "주먹밥", "새우",
    # 양식/분식/패스트푸드
    "치킨", "피자", "햄버거", "버거", "감자튀김", "파스타", "스파게티", "스테이크", "샐러드", "샌드위치", "토스트",
    "핫도그", "타코", "돈까스", "돈가스", "우동", "라멘", "초밥", "스시", "덮밥",
    # 간식/디저트/음료
    "케이크", "과자", "아이스크림", "빙수", "팝콘", "마카롱", "와플", "도넛", "쿠키", "젤리", "사탕", "초콜릿",
    "붕어빵", "호떡", "커피", "라떼", "아메리카노", "콜라", "사이다", "주스", "밀크티", "버블티", "스무디", "에이드",
)

# 입력에 이 단어가 있으면 같이 써도 자연스러운 음식 (카페 -> 커피). '중국집'은 일부러 없음:
# 짬뽕만 먹었다고 했는데 탕수육/군만두를 붙이는 게 바로 문제였던 경우라서.
FOOD_IMPLIED_BY = {
    "카페": ("커피", "라떼", "아메리카노", "케이크", "쿠키", "스무디", "에이드", "밀크티", "버블티"),
    "커피": ("라떼", "아메리카노"),
    "생일": ("케이크",),
    "영화": ("팝콘", "콜라"),
    "고깃집": ("고기", "삼겹살", "목살", "갈비"),
    "삼겹살": ("고기",),
    "분식": ("떡볶이", "김밥", "순대", "튀김", "어묵", "라면"),
    "치킨": ("콜라",),
    "피자": ("콜라",),
    "햄버거": ("감자튀김", "콜라"),
    "편의점": ("컵라면", "삼각김밥", "도시락"),
}

# 생성 단계 금지(bad_words)에서는 빼는 음식 단어: 다른 말의 일부와 토큰이 겹칠 수 있음
# ('~라면' 가정형, '그만두다', '물고기' 등). 이 단어들도 검증기에서는 계속 잡음.
_FOOD_NO_GENERATION_BLOCK = {"라면", "만두", "고기", "김치", "튀김", "새우", "국수", "갈비", "순대", "어묵", "주스"}


def food_context(context_str: str) -> str:
    """음식 검사용 문맥: 입력 + 입력에서 자연스럽게 따라오는 음식(FOOD_IMPLIED_BY)"""
    extra = [f for trigger, foods in FOOD_IMPLIED_BY.items() if trigger in context_str for f in foods]
    return context_str + " " + " ".join(extra)


def has_invented_food(text: str, context_str: str) -> str | None:
    """
    일기에 입력에 없는 음식 단어가 있으면 그 단어를 반환.
    앞 글자가 한글이면 다른 단어의 일부로 보고 건너뜀 ('그만두다'의 만두, '물고기'의 고기, '이라면'의 라면).
    """
    ctx = food_context(context_str)
    for kw in FOOD_KEYWORDS:
        if kw in ctx:
            continue
        if re.search(rf"(?<![가-힣]){kw}", text):
            return kw
    return None

# "술", "형", "과장" 같은 짧은 키워드는 무관한 흔한 단어에도 다 포함돼서 오탐지가 잦음
# (미술관, 인형, 과장해서 등) - 검사 전에 이런 단어들을 먼저 지워버리고 나서 진짜 매칭 확인
FALSE_POSITIVE_EXCLUSIONS = {
    "술": ["미술", "기술", "예술", "수술", "무술", "마술", "서술", "저술", "시술", "학술", "진술", "예술적", "미술관", "기술적"],
    "형": ["인형", "모형", "유형", "형식", "형태", "전형", "변형", "원형", "지형", "체형", "선형", "도형", "균형", "조형", "정형외과", "삼각형", "사각형"],
    "과장": ["과장해서", "과장이", "과장된", "좀 과장", "너무 과장", "과장해", "과장하면", "과장인가"],
}


def _mask_false_positives(text: str, keyword: str) -> str:
    masked = text
    for fp in FALSE_POSITIVE_EXCLUSIONS.get(keyword, []):
        masked = masked.replace(fp, "")
    return masked

CLICHE_PATTERNS = (
    "덕분에 힘", "덕분에 이겨", "앞으로 살아갈 힘", "정말 소중", "말로 표현할 수",
    "마음이 따뜻해지는 것을 느꼈다", "환상적이었다", "마법처럼", "별처럼 빛나",
    "행복이었다", "힐링이 되었다", "위로가 되었다", "선사", "느꼈다는 걸", "라는 걸 느꼈다",
    "최고의 하루", "최고의 순간", "잊지 못할", "평생 기억", "완벽한 하루",
    "날아갈 것", "날아갈 듯", "터질 것 같았다", "구름 위", "세상을 다 가진",
)

FORMAL_ENDING_PATTERN = re.compile(r'(요|습니다|ㅂ니다)[.!?]?$')

MAX_RETRIES = 3  # 전시 당일 응답 속도 고려해서 5->3으로 낮춤 (대부분 1~2번 안에 통과하는 걸 확인함)


def expand_context(context_str: str) -> str:
    extra = []
    for trigger, implied_list in IMPLIED_RELATION_TRIGGERS.items():
        if trigger in context_str:
            extra.extend(implied_list)
    return context_str + " " + " ".join(extra)


def has_invented_word(text: str, context_str: str, keyword_list) -> str | None:
    for kw in keyword_list:
        masked_text = _mask_false_positives(text, kw)
        if kw in masked_text and kw not in context_str:
            return kw
    return None


def _split_sentences(text: str) -> list[str]:
    return [s for s in re.split(r'(?<=[.!?])\s+', text.strip()) if s.strip()]


def validate_diary(text: str, context_str: str = ""):
    text = text.strip()
    reasons = []

    if not text:
        return False, ["empty"], 0

    cfg = get_generation_config()
    length_ok = cfg["min_chars"] <= len(text) <= cfg["max_chars"]
    if not length_ok:
        reasons.append(f"길이={len(text)}자")

    sentences = _split_sentences(text)
    count_ok = 2 <= len(sentences) <= 8
    if not count_ok:
        reasons.append(f"문장수={len(sentences)}개")

    formal_ok = not any(FORMAL_ENDING_PATTERN.search(s.strip()) for s in sentences)
    if not formal_ok:
        reasons.append("해요체 섞임")

    phrase_ok = not any(p in text for p in FORBIDDEN_PHRASES)
    if not phrase_ok:
        reasons.append("금지 문구 포함")

    cliche_ok = not any(c in text for c in CLICHE_PATTERNS)
    if not cliche_ok:
        reasons.append("뻔한 마무리")

    dahaeng_ok = text.count("다행") <= 1
    if not dahaeng_ok:
        reasons.append("다행 중복")

    invented = has_invented_word(text, context_str, RELATION_KEYWORDS)
    relation_ok = invented is None
    if not relation_ok:
        reasons.append(f"관계 지어냄({invented})")

    invented_alcohol = has_invented_word(text, context_str, ALCOHOL_KEYWORDS)
    alcohol_ok = invented_alcohol is None
    if not alcohol_ok:
        reasons.append(f"술 지어냄({invented_alcohol})")

    invented_meal = has_invented_word(text, context_str, MEALTIME_KEYWORDS)
    meal_ok = invented_meal is None
    if not meal_ok:
        reasons.append(f"식사시간대 지어냄({invented_meal})")

    invented_food = has_invented_food(text, context_str)
    food_ok = invented_food is None
    if not food_ok:
        reasons.append(f"음식 지어냄({invented_food})")

    checks = [length_ok, count_ok, formal_ok, phrase_ok, cliche_ok, dahaeng_ok, relation_ok, alcohol_ok, meal_ok, food_ok]
    score = sum(checks)
    passed = all(checks)
    return passed, reasons, score


# ---------- 측정용 프롬프트 변형 (기본값 아님) ----------
# 기본(None/"base")은 위 SYSTEM_PREAMBLE/FEWSHOT_EXAMPLES 그대로. 변형은 측정용 디버그 엔드포인트에서만
# 고를 수 있고, 한 변형은 한 가지만 바꿈 (전후 비교용). 채택하면 그때 기본값으로 올림.

_RULE2_TAIL = "그냥 있었던 일 적고 끝내거나 사소한 잡생각으로 끝나도 된다.\n"
assert SYSTEM_PREAMBLE.count(_RULE2_TAIL) == 1

# "emotion_word": 규칙 2번 마지막 문장만 바꿈. 마무리 부근에 그날 기분을 평범한 단어 하나로 쓰게 허용.
# (KoBERT가 감정을 고를 단서가 일기에 없어서 확률이 갈리는 문제 대응. 교훈형/과장형 금지는 그대로)
SYSTEM_PREAMBLE_EMOTION_WORD = SYSTEM_PREAMBLE.replace(
    _RULE2_TAIL,
    "다만 마무리 부근에 그날 든 기분을 평범한 말 하나로 적는다 (예: '재밌었다', '답답했다', "
    "'뿌듯했다', '피곤했다'). 기분은 '무엇을'과 '이유'에서 짐작되는 것으로만 고르고, "
    "그 기분을 꾸미거나 교훈으로 늘이지 않는다.\n",
)

# "fewshot_no_mealtime": few-shot 예시에서 식사시간대 단어(아침/점심/저녁)만 뺌.
# 기존 예시는 일기 본문과 '언제'에 저녁/아침/점심을 쓰는데, 앱이 보내는 '언제'는 "오후 7시" 형식이라
# 모델이 예시를 따라 '저녁'을 쓰면 '식사시간대 지어냄'으로 검증에서 떨어짐 (3번 예시는 원문 그대로도 불합격).
_FEWSHOT_MEALTIME_FIXES = [
    ("언제: 저녁 9시\n", "언제: 오후 9시\n"),
    ("저녁 먹고 누워있는데", "밥 먹고 누워있는데"),
    ("토요일 아침에 짐 좀 챙겨서", "토요일에 짐 좀 챙겨서"),
    ("엄마가 벌써 점심 준비하고 계셨다", "엄마가 벌써 밥 준비하고 계셨다"),
    ("티비 좀 보다가 저녁까지 먹고", "티비 좀 보다가 밥 한 끼 더 먹고"),
    ("언제: 저녁 7시\n", "언제: 오후 7시\n"),
    ("저녁에 동네 카페에서", "동네 카페에서"),
    ("언제: 저녁\n", "언제: 오후 7시\n"),
    ("친구 생일이라고 해서 저녁에 걔네 집으로", "친구 생일이라고 해서 걔네 집으로"),
]
FEWSHOT_EXAMPLES_NO_MEALTIME = FEWSHOT_EXAMPLES
for _old, _new in _FEWSHOT_MEALTIME_FIXES:
    assert FEWSHOT_EXAMPLES_NO_MEALTIME.count(_old) == 1, _old
    FEWSHOT_EXAMPLES_NO_MEALTIME = FEWSHOT_EXAMPLES_NO_MEALTIME.replace(_old, _new)

# "app_style" (patch 12 기본값): 실제 앱 입력처럼 짧은 답변을 자연스럽게 풀어 쓰는 예시 + 마무리 기분 한 마디.
# - 예전 예시는 '이유'가 긴 문장이라, 실제 사용자가 "아쉽다"처럼 짧게 쓰면 답변을 거의 그대로 옮겨 적었음
# - '언제'도 앱이 실제로 보내는 "10월 25일 토요일 오후 2시" 형식으로 맞춤
# - 마무리에 평범한 기분 한 마디 -> KoBERT가 감정을 고를 단서가 생김 (emotion_word 변형과 같은 규칙)
_RULE4 = ("4. 분량은 3~4문장, 100자 안팎으로 쓴다. 정보가 적어도 그날의 장소 분위기, 몸 상태, 사소한 "
          "잡생각 같은 일반적인 배경으로 채워서 한 문장짜리로 끝내지 않는다.\n")
assert SYSTEM_PREAMBLE_EMOTION_WORD.count(_RULE4) == 1
# patch 13: patch 12의 "4~5문장, 130~200자"는 짧은 답변으로 분량을 채우려다 메뉴/소품을 지어내게 만들어서
# 3~4문장으로 되돌리고, 모자란 분량은 '새 사건' 대신 기분/몸 상태/분위기로만 채우게 함.
# 규칙 5의 '괜찮음' 예시(생일이면 케이크 같은 소품)도 음식/물건을 덧붙여도 된다는 신호라서 app_style에서는 바꿈.
_RULE5_OK = ("   - 괜찮음: 그 장소/상황에서 흔히 있는 배경 묘사 (예: 공원이면 사람들, 생일이면 케이크 정도의 "
             "일반적인 소품) - 이 정도는 자연스러움을 위해 살짝 곁들여도 된다.\n")
_RULE5_BAN = "   - 절대 금지: 확인할 수 없는 결과나 판단(예: '시험을 잘 봤다', '다들 좋아했다'), 구체적인 "
assert SYSTEM_PREAMBLE_EMOTION_WORD.count(_RULE5_OK) == 1 and SYSTEM_PREAMBLE_EMOTION_WORD.count(_RULE5_BAN) == 1
SYSTEM_PREAMBLE_APP = (
    SYSTEM_PREAMBLE_EMOTION_WORD
    .replace(
        _RULE4,
        "4. 분량은 3~4문장, 90~150자 정도로 쓴다 (답변이 길 때만 5문장까지). 답변 문장을 그대로 옮겨 적지 말고 "
        "내 말로 바꿔 쓴다. 분량이 모자라면 새로운 일이나 물건을 만들지 말고 그때의 기분, 몸 상태, "
        "장소 분위기로 채운다.\n",
    )
    .replace(
        _RULE5_OK,
        "   - 괜찮음: 그 장소의 분위기나 풍경 묘사 (예: 공원이면 오가는 사람들, 날씨, 바람) - 살짝 곁들이는 정도만.\n",
    )
    .replace(
        _RULE5_BAN,
        "   - 절대 금지: 답변에 없는 음식·메뉴·음료·물건 (예: 한 가지 메뉴만 먹었다고 했으면 다른 메뉴를 "
        "덧붙이지 않는다), " + _RULE5_BAN[len("   - 절대 금지: "):],
    )
)

_APP_HUMAN = "Human: 다음 정보를 바탕으로 감성적인 일기를 작성해라:\n\n"
FEWSHOT_APP_STYLE = (
    # patch 13: 예시 일기에도 입력에 없는 소품/음식(케이크, 과자, 물 한 잔, 사진)이 들어가 있어서 모델이 그대로 따라 했음
    # -> 덧붙이는 내용은 기분/몸 상태/분위기만. 음식 예시(짜장면)를 넣어 "그 메뉴만" 쓰는 모습을 보여줌.
    _APP_HUMAN +
    "무엇을: 늦게까지 과제\n이유: 마감이 내일이라 급해서\n누구와: 혼자\n"
    "언제: 10월 21일 화요일 오후 11시\n어디서: 자취방\n"
    "Assistant:\n"
    "마감이 내일이라 결국 자취방에서 늦게까지 과제를 붙잡고 있었다. 처음엔 금방 끝날 줄 알았는데 생각보다 손볼 게 많았다. "
    "겨우 마무리하고 나니까 어깨가 뻐근하고 눈도 침침했다. 솔직히 좀 피곤했다.\n\n" +
    _APP_HUMAN +
    "무엇을: 정보처리기사 실기 시험\n이유: 아쉽다\n누구와: 혼자\n"
    "언제: 10월 25일 토요일 오후 2시\n어디서: 시험장\n"
    "Assistant:\n"
    "오늘 정보처리기사 실기 시험을 보러 시험장에 다녀왔다. 나름 준비한다고 했는데 막상 자리에 앉으니까 긴장이 많이 됐다. "
    "끝나고 나오는 길에도 문제들이 자꾸 머릿속에 맴돌았다. 마음이 좀 아쉽다.\n\n" +
    _APP_HUMAN +
    "무엇을: 짜장면 먹음\n이유: 오랜만에 먹으니까 맛있어서\n누구와: 혼자\n"
    "언제: 10월 14일 화요일 오후 1시\n어디서: 집\n"
    "Assistant:\n"
    "오늘은 집에서 짜장면을 먹었다. 오랜만에 먹어서 그런지 한 입 먹자마자 맛있다는 말이 절로 나왔다. "
    "혼자 조용히 먹으니까 오히려 맛에 더 집중이 됐다. 배가 든든하니 기분이 좋았다.\n\n" +
    _APP_HUMAN +
    "무엇을: 친구랑 한강 산책\n이유: 날씨가 좋아서\n누구와: 친구\n"
    "언제: 10월 18일 토요일 오후 4시\n어디서: 한강공원\n"
    "Assistant:\n"
    "날씨가 좋아서 친구랑 한강에 나갔다. 바람이 선선해서 걷기 딱 좋았다. "
    "강을 따라 천천히 걸으면서 이런저런 얘기를 나눴다. 오랜만에 기분이 상쾌했다.\n\n" +
    _APP_HUMAN +
    "무엇을: 엄마랑 장보기\n이유: 오랜만에 같이 시간을 보내서 좋았다\n누구와: 엄마\n"
    "언제: 10월 12일 일요일 오전 11시\n어디서: 동네 마트\n"
    "Assistant:\n"
    "오랜만에 엄마랑 동네 마트에 장을 보러 갔다. 엄마는 카트를 밀면서 이것저것 꼼꼼하게 고르셨다. "
    "별거 아닌데 둘이 같이 돌아다니는 시간이 괜히 좋았다. 마음이 편안했다.\n"
)

PROMPT_VARIANTS = {
    "base": (SYSTEM_PREAMBLE, FEWSHOT_EXAMPLES),
    "emotion_word": (SYSTEM_PREAMBLE_EMOTION_WORD, FEWSHOT_EXAMPLES),
    "fewshot_no_mealtime": (SYSTEM_PREAMBLE, FEWSHOT_EXAMPLES_NO_MEALTIME),
    "app_style": (SYSTEM_PREAMBLE_APP, FEWSHOT_APP_STYLE),
}

# 마지막 지시문 (변형별). app_style은 분량/풀어쓰기 지시가 다름.
_FINAL_INSTRUCTION = (
    "(정보에 없는 음식/음료/시간/대화내용/결과 판단은 절대 지어내지 말 것. "
    "아침/점심/저녁/새벽 같은 시간대 단어도 쓰지 말 것. '술'은 입력에 적힌 그대로 '술'이라고만 쓰고 "
    "맥주/소주 같은 구체적인 종류는 쓰지 말 것. 입력의 '무엇을'과 '이유'를 반드시 반영할 것. 3~4문장으로 쓸 것)"
)
_FINAL_INSTRUCTION_APP = (
    "(정보에 없는 음식/메뉴/음료/물건/대화내용/결과 판단은 절대 지어내지 말 것. 아침/점심/저녁/새벽 같은 시간대 단어는 "
    "쓰지 말 것. '술'은 입력에 적힌 그대로 '술'이라고만 쓸 것. '무엇을'과 '이유'를 내 말로 풀어서 3~4문장으로 쓰고, "
    "마지막에 그날 기분을 평범한 말 하나로 적을 것)"
)

# 2026-10 실기기 테스트: 기본(base) few-shot이 '저녁/아침/점심'을 쓰는 예시라 모델이 "오늘 아침 일찍…"으로 시작
# -> 식사시간대 검증에서 3/3 불합격 -> 입력 그대로 이어붙인 안전 템플릿이 출력됨 (patch 10에서 fewshot_no_mealtime 채택).
# patch 12: 짧은 답변을 풀어 쓰는 app_style을 기본으로. .env DIARY_PROMPT_VARIANT로 예전 변형으로 되돌릴 수 있음.
DEFAULT_VARIANT = "app_style"


def default_variant() -> str:
    v = (os.environ.get("DIARY_PROMPT_VARIANT", "") or DEFAULT_VARIANT).strip()
    return v if v in PROMPT_VARIANTS else DEFAULT_VARIANT


def build_prompt(actual_user_content: str, variant: str | None = None) -> str:
    variant = variant or default_variant()
    if variant not in PROMPT_VARIANTS:
        raise ValueError(f"알 수 없는 프롬프트 변형: {variant} (가능: {', '.join(PROMPT_VARIANTS)})")
    preamble, fewshot = PROMPT_VARIANTS[variant]
    instruction = _FINAL_INSTRUCTION_APP if variant == "app_style" else _FINAL_INSTRUCTION
    return (
        f"{preamble}\n"
        f"{fewshot}\n"
        f"Human: 다음 정보를 바탕으로 감성적인 일기를 작성해라 {instruction}:\n\n"
        f"{actual_user_content}\n"
        f"Assistant:\n"
    )


def _generate_once(
    prompt_str: str,
    temperature: float,
    max_new_tokens: int = 220,
    do_sample: bool = True,
    extra_stop_strings: list | None = None,
    stats: dict | None = None,
    no_repeat_ngram_size: int = 0,
    bad_words: list | None = None,
) -> str:
    """
    do_sample/extra_stop_strings/stats는 이미지 프롬프트 변환 측정용으로 추가한 옵션.
    stats에 dict를 넘기면 입력/생성 토큰 수, 소요시간, 잘리기 전 raw 출력을 채워줌.
    no_repeat_ngram_size / bad_words는 일기 생성에서만 넘김 (patch 12).
    repetition_penalty / top_p는 get_generation_config() 값 (일기·이미지 변환 공통).
    """
    import time
    import torch
    from app.models.llama_loader import get_model_and_tokenizer

    model, tokenizer = get_model_and_tokenizer()
    input_ids = tokenizer(prompt_str, return_tensors="pt")["input_ids"].to(model.device)

    cfg = get_generation_config()
    gen_kwargs = dict(
        input_ids=input_ids,
        max_new_tokens=max_new_tokens,
        do_sample=do_sample,
        # transformers의 반복 감점은 새로 쓴 글자뿐 아니라 '프롬프트 전체'에 걸림.
        # 1.2면 예시 일기에 나온 자연스러운 표현까지 감점돼서 어색해졌음 -> 아주 약하게(1.05)
        repetition_penalty=cfg["repetition_penalty"],
        # EEVE의 config.json에 "use_cache": false 가 들어있어서, 명시하지 않으면 KV 캐시가 꺼진 채로
        # 토큰마다 입력 전체를 다시 계산함 (1.8 tok/s -> 켜면 약 18 tok/s). 반드시 True로 고정.
        use_cache=True,
        eos_token_id=tokenizer.eos_token_id,
        tokenizer=tokenizer,
        stop_strings=["\nHuman:", "Human:", "무엇을:"] + list(extra_stop_strings or []),
    )
    if do_sample:
        gen_kwargs["temperature"] = temperature
        gen_kwargs["top_p"] = cfg["top_p"]
    if no_repeat_ngram_size:
        gen_kwargs["no_repeat_ngram_size"] = no_repeat_ngram_size  # 같은 n토큰 묶음이 두 번 나오지 않게
    bad_ids = _bad_words_ids(tokenizer, bad_words or [])
    if bad_ids:
        gen_kwargs["bad_words_ids"] = bad_ids  # 이 토큰 열은 아예 생성하지 못함

    start = time.time()
    with torch.no_grad():
        outputs = model.generate(**gen_kwargs)
    elapsed = time.time() - start

    new_tokens = outputs[0][input_ids.shape[-1]:]
    generated_text = tokenizer.decode(new_tokens, skip_special_tokens=True)

    if stats is not None:
        stats["input_tokens"] = int(input_ids.shape[-1])
        stats["output_tokens"] = int(new_tokens.shape[-1])
        stats["max_new_tokens"] = max_new_tokens
        stats["hit_max_new_tokens"] = int(new_tokens.shape[-1]) >= max_new_tokens
        stats["elapsed_sec"] = round(elapsed, 2)
        stats["tokens_per_sec"] = round(int(new_tokens.shape[-1]) / elapsed, 2) if elapsed > 0 else None
        stats["raw_full"] = generated_text  # "Human:" 기준으로 자르기 전 전문

    return generated_text.split("Human:")[0].strip()


# patch 13: "점심"만 금지해도 실제 생성에선 "점심으로"가 다른 토큰 조합으로 쪼개져서 못 막은 경우가 있었음
# (2026-10-30 로그: '어제 점심으로…'). 조사가 붙은 흔한 형태도 같이 금지 목록에 넣음.
_JOSA = ("에", "은", "는", "이", "을", "도", "만", "으로", "까지", "부터", "때", "쯤", "엔", "이랑")
_JOSA_WORDS = set(MEALTIME_KEYWORDS) | {"소주", "맥주", "막걸리", "와인", "폭탄주"}


def _bad_words_ids(tokenizer, words: list) -> list:
    """
    금지할 단어 -> 토큰 id 열 목록 (generate의 bad_words_ids 형식).
    같은 단어도 앞에 공백이 있을 때/없을 때 토큰이 달라서 둘 다 넣음.
    SentencePiece 계열은 공백이 '▁' 토큰으로 따로 붙는 경우가 있어서, 공백만 있는 맨 앞 토큰을 뗀 것도 넣음.
    식사시간대/술 단어는 조사가 붙은 형태("점심으로")도 넣음 (_JOSA_WORDS).
    """
    out = set()
    for w in words:
        forms = [w] + ([w + j for j in _JOSA] if w in _JOSA_WORDS else [])
        for variant in [f for form in forms for f in (form, " " + form)]:
            ids = tokenizer(variant, add_special_tokens=False)["input_ids"]
            if not ids:
                continue
            out.add(tuple(ids))
            if len(ids) > 1 and not tokenizer.decode(ids[:1]).strip():
                out.add(tuple(ids[1:]))
    return [list(t) for t in out]


# 생성 단계에서 막을 단어 (검증기에서 걸리는 단어 중, 다른 단어 속에 잘 섞이지 않는 2글자 이상만)
# '술', '형'처럼 한 글자는 '미술', '인형' 같은 정상 단어까지 막을 수 있어서 제외 (검증기가 계속 잡음)
_BLOCK_CANDIDATES = (
    tuple(MEALTIME_KEYWORDS)
    + ("소주", "맥주", "막걸리", "와인", "폭탄주")
    + tuple(k for k in RELATION_KEYWORDS if len(k) >= 2)
)
_FOOD_BLOCK_CANDIDATES = tuple(f for f in FOOD_KEYWORDS if f not in _FOOD_NO_GENERATION_BLOCK)


def words_to_block(context_str: str) -> list[str]:
    """입력(context)에 없는 금지 후보만 골라서 반환 (입력에 '선배'가 있으면 '선배'는 써도 됨)"""
    ctx_food = food_context(context_str)
    return ([w for w in _BLOCK_CANDIDATES if w not in context_str]
            + [f for f in _FOOD_BLOCK_CANDIDATES if f not in ctx_food])


def _drop_invented_sentences(text: str, context_str: str) -> str:
    """입력에 없는 식사시간대/술/관계/음식 단어가 들어간 문장만 빼고 나머지를 이어 붙임"""
    keep = []
    for sent in _split_sentences(text):
        if (has_invented_word(sent, context_str, MEALTIME_KEYWORDS)
                or has_invented_word(sent, context_str, ALCOHOL_KEYWORDS)
                or has_invented_word(sent, context_str, RELATION_KEYWORDS)
                or has_invented_food(sent, context_str)):
            continue
        keep.append(sent.strip())
    return " ".join(keep)


def _mock_generate(what: str) -> str:
    return f"오늘은 {what} 관련된 하루였다. 이건 목(mock) 응답이라 실제 생성된 건 아니다. 그래도 API 흐름 테스트용으로는 충분하다."


def _repair_meal_words(text: str, context_str: str) -> str:
    """
    검증에서 '식사시간대 지어냄'만 걸린 후보를 버리지 않고 고친다.
    입력(context)에 없는 아침/점심/저녁/새벽 단어를 "오늘"로 바꿈 ("오늘 아침 일찍 일어나서" -> "오늘 일어나서").
    고친 뒤에도 validate_diary를 다시 통과해야만 채택된다 (호출하는 쪽에서 재검증).
    """
    out = text
    for kw in MEALTIME_KEYWORDS:
        if kw in context_str or kw not in out:
            continue
        # "새벽까지 있었다" -> "늦게까지 있었다" (먼저 처리 안 하면 "오늘 까지"로 깨짐)
        out = re.sub(rf"(?:오늘\s*)?{kw}(?:\s*(?:일찍|늦게))?\s*까지", "늦게까지", out)
        out = re.sub(rf"(?:오늘\s*)?{kw}(?:\s*(?:일찍|늦게))?(?:에는|에도|에|엔|부터|은|는)?\s*", "오늘 ", out)
    out = re.sub(r"(?:오늘\s*){2,}", "오늘 ", out)
    return out.strip()


def _safe_fallback_diary(what: str, why: str, who_str: str, when: str, where: str) -> str:
    return f"오늘은 {where}에서 {what}. {why}. 그런 하루였다."


def generate_diary_text(what: str, why: str, who, when: str, where: str, timings: dict | None = None,
                        prompt_variant: str | None = None):
    # timings에 dict를 넘기면 생성/검증 시간과 시도 횟수를 채워줌 (측정용, 리턴값은 그대로)
    # prompt_variant: 측정용 프롬프트 변형 (PROMPT_VARIANTS). None이면 기본 프롬프트 = 기존 동작
    import time
    who_str = ", ".join(who) if isinstance(who, list) else who

    if MOCK_MODE:
        return _mock_generate(what), False

    actual_user_content = f"무엇을: {what}\n이유: {why}\n누구와: {who_str}\n언제: {when}\n어디서: {where}"
    prompt_str = build_prompt(actual_user_content, variant=prompt_variant)
    context_str = expand_context(f"{who_str} {what} {why} {when} {where}")

    clean_diary = ""
    best_candidate = ""
    best_score = -1
    passed = False

    gen_sec = 0.0
    validate_sec = 0.0
    attempts = 0
    attempt_details = []  # 시도별 측정값 (불합격 사유 집계/지어내기 집계용)
    cfg = get_generation_config()
    block = words_to_block(context_str) if cfg["block_words"] else []
    for attempt in range(1, MAX_RETRIES + 1):
        attempts = attempt
        # 재시도할수록 온도를 올림 (예전처럼 내리면 세 번 다 거의 같은 문장이 나왔음)
        temp = cfg["temperatures"][min(attempt - 1, len(cfg["temperatures"]) - 1)]
        stats = {}
        t0 = time.time()
        candidate = _generate_once(prompt_str, temperature=temp, stats=stats,
                                   no_repeat_ngram_size=cfg["no_repeat_ngram_size"], bad_words=block)
        t1 = time.time()
        is_ok, reasons, score = validate_diary(candidate, context_str=context_str)
        t2 = time.time()
        gen_sec += t1 - t0
        validate_sec += t2 - t1
        print(f"  [TIMING] 일기 생성 {attempt}번째 시도: 생성 {t1 - t0:.1f}초 "
              f"(입력 {stats.get('input_tokens')}토큰, 생성 {stats.get('output_tokens')}토큰, "
              f"{stats.get('tokens_per_sec')}tok/s), 검증 {(t2 - t1) * 1000:.1f}ms")
        attempt_details.append({
            "attempt": attempt, "temperature": temp, "passed": is_ok, "reasons": reasons, "score": score,
            "gen_sec": round(t1 - t0, 2), "input_tokens": stats.get("input_tokens"),
            "output_tokens": stats.get("output_tokens"), "tokens_per_sec": stats.get("tokens_per_sec"),
            "hit_max_new_tokens": stats.get("hit_max_new_tokens"), "text": candidate,
        })

        if score > best_score:
            best_score = score
            best_candidate = candidate

        if is_ok:
            clean_diary = candidate
            passed = True
            print(f"  {attempt}번째 시도에서 통과")
            break
        else:
            print(f"  {attempt}번째 시도 불합격 ({', '.join(reasons)}): {candidate[:60]}...")

    repaired = False
    if not passed:
        # 후보를 점수 높은 순으로 고쳐보고, 재검증을 통과하는 첫 후보를 쓴다 (입력 복붙 템플릿보다 훨씬 자연스러움)
        # 1) 식사시간대 단어를 고쳐보고 2) 그래도 안 되면 문제 문장만 빼 봄 (둘 다 재검증 통과해야 채택)
        for d in sorted(attempt_details, key=lambda d: d["score"], reverse=True):
            for how, fixed in (("식사시간대 단어 수정", _repair_meal_words(d["text"], context_str)),
                               ("문제 문장 제거", _drop_invented_sentences(d["text"], context_str))):
                if fixed and fixed != d["text"].strip() and validate_diary(fixed, context_str=context_str)[0]:
                    clean_diary, passed, repaired = fixed, True, True
                    print(f"  {how} 후 채택: {fixed[:60]}...")
                    break
            if passed:
                break

    if not passed:
        print(f"  경고: {MAX_RETRIES}번 다 실패, 안전 템플릿으로 대체함 (최선 후보 점수 {best_score}/9)")
        clean_diary = _safe_fallback_diary(what, why, who_str, when, where)

    if timings is not None:
        timings["diary_attempts"] = attempts
        timings["diary_llm_sec"] = round(gen_sec, 2)
        timings["diary_validate_sec"] = round(validate_sec, 4)
        timings["diary_attempt_details"] = attempt_details
        timings["diary_fallback"] = not passed
        timings["prompt_variant"] = prompt_variant or default_variant()
        timings["diary_blocked_words"] = block
        timings["diary_repaired"] = repaired

    return clean_diary, not passed