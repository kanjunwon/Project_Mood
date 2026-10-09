"""
app/services/cast.py
그림에 "누가 몇 명 나오는지"를 앱 입력(Who)과 계정 성별로 서버가 직접 정한다.

배경: 이미지 프롬프트 변환 LLM한테 인원/성별을 맡기면 "친구 3명"인데 1명이나 4명이 나오고,
남성 계정인데 여자가 섞이는 문제가 반복됐다 (2026-10 통합 테스트). SDXL은 프롬프트의 인원수를 잘 안 따르기 때문에,
인원/성별 태그는 코드가 확정하고 LLM은 장소/행동/분위기 태그만 맡긴다.

규칙 (재유 확정, 2026-10-09):
- "나"는 항상 그림에 포함된다. 성별은 계정 성별(남성/여성).
- 남성친구 -> 남자 1명 추가 / 여성친구 -> 여자 1명 추가 / 친구 -> 나와 같은 성별 1명 추가
- 직접 입력에 "N명"이 있으면 N명이 친구로 추가된다 (나 제외). 예) 남성 계정 + 남성친구 + "3명" -> 나 포함 남자 4명
- 엄마(mature female, mother) / 아빠(mature male, father) / 형제(남자) / 남매(나와 반대 성별) 각각 1명
- 혼자 -> 나 1명만
- 한 장면 최대 4명 (SDXL은 4명을 넘으면 구도가 급격히 불안정). 넘으면 앞에서부터 4명만 그린다.
- 판단할 수 없는 경우(가족/연인/자녀/직접 입력한 사람 설명/계정 성별 없음 등)는 None을 돌려주고,
  호출한 쪽(sd3_service)이 예전처럼 LLM이 만든 인원 태그를 쓴다.
"""
import re
from dataclasses import dataclass, field

MAX_FOREGROUND = 4

_COUNT = re.compile(r"(\d+|한|두|세|네|다섯|여섯)\s*명")
_KOR_NUM = {"한": 1, "두": 2, "세": 3, "네": 4, "다섯": 5, "여섯": 6}

# 칩 -> (친구 성별: None이면 나와 같은 성별)
_FRIEND_CHIPS = {"친구": None, "남성친구": "male", "여성친구": "female"}
_PARENT_CHIPS = {
    "엄마": ("female", ["mature female", "mother"]),
    "아빠": ("male", ["mature male", "father"]),
}
_IGNORED_CHIPS = {"반려동물", "강아지", "고양이"}      # 사람 수에 영향 없음 (동물은 LLM 태그가 담당)
_UNRESOLVABLE_CHIPS = {"가족", "연인", "자녀"}         # 몇 명/무슨 성별인지 알 수 없음 -> LLM에 맡김

# 단독(1인)일 때 쓰는 보정 문구. sd3_service의 기존 1인 보정(apply_gender/ensure_solo_person)과 같은 값.
_MALE_SOLO_TAGS = ["(1boy:1.3)", "(male focus:1.2)", "solo"]
_FEMALE_SOLO_TAGS = ["1girl", "solo"]
_MALE_SOLO_NEGATIVE = "(1girl:1.3), (girl:1.2), (female:1.2), feminine, multiple girls, multiple boys, 2boys, 3boys, group"
_FEMALE_SOLO_NEGATIVE = "multiple girls, multiple boys, 2girls, 3girls, group"
# 그룹은 반대 성별만 막는다. (같은 성별의 다른 인원수 태그를 negative에 넣으면 positive와 충돌해서 그림이 뭉개짐 - F 실험)
_MALE_GROUP_NEGATIVE = "girl, 1girl, 2girls, 3girls"
_FEMALE_GROUP_NEGATIVE = "boy, 1boy, 2boys, 3boys"


def normalize_gender(gender) -> str | None:
    """DB의 users.gender 텍스트("남성"/"여성"/...) -> "male" | "female" | None"""
    if not gender:
        return None
    s = str(gender).strip().lower()
    if "여" in s or s.startswith("f") or "woman" in s or "girl" in s:
        return "female"
    if "남" in s or s.startswith("m") or "man" in s or "boy" in s:
        return "male"
    return None


@dataclass
class Cast:
    boys: int
    girls: int
    solo: bool
    tags: list = field(default_factory=list)   # positive 맨 앞에 넣을 인원/성별 태그
    negative: str = ""                           # negative에 덧붙일 문구
    trimmed: bool = False                        # 4명 초과라 줄였는지
    summary: str = ""                            # 로그용

    @property
    def total(self) -> int:
        return self.boys + self.girls


def _split_who(who) -> list[str]:
    if isinstance(who, str):
        items = re.split(r"[,/]", who)
    else:
        items = [str(x) for x in (who or [])]
    return [i.strip() for i in items if i and i.strip()]


def _parse_count(item: str) -> int | None:
    m = _COUNT.search(item)
    if not m:
        return None
    raw = m.group(1)
    return int(raw) if raw.isdigit() else _KOR_NUM[raw]


def _count_tags(boys: int, girls: int) -> list[str]:
    if girls == 0:
        return ["1boy", "solo"] if boys == 1 else [f"({boys}boys:1.2)", "male focus"]
    if boys == 0:
        return ["1girl", "solo"] if girls == 1 else [f"({girls}girls:1.2)", "female focus"]
    g = f"{girls}girl" + ("s" if girls > 1 else "")
    b = f"{boys}boy" + ("s" if boys > 1 else "")
    return [g, b]


def build_cast(who, gender) -> Cast | None:
    me = normalize_gender(gender)
    if me is None:
        return None
    items = _split_who(who)
    if not items:
        return None

    opposite = "female" if me == "male" else "male"
    others: list[str] = []
    count_n = 0
    has_count = False
    for it in items:
        n = _parse_count(it)
        if n is not None:
            has_count = True
            count_n += n
        else:
            others.append(it)

    people: list[str] = []          # 나를 제외한 인원의 성별
    role_tags: list[str] = []
    friend_genders: list[str] = []
    for it in others:
        if it == "혼자" or it in _IGNORED_CHIPS:
            continue
        if it in _UNRESOLVABLE_CHIPS:
            return None
        if it in _FRIEND_CHIPS:
            friend_genders.append(_FRIEND_CHIPS[it] or me)
        elif it in _PARENT_CHIPS:
            g, tags = _PARENT_CHIPS[it]
            people.append(g)
            role_tags += tags
        elif it == "형제":
            people.append("male")
        elif it == "남매":
            people.append(opposite)
        else:
            return None  # 사람을 직접 설명한 입력("회사 동료" 등) -> 판단 불가

    if has_count:
        if len(set(friend_genders)) > 1:
            return None  # 남성친구+여성친구 + "3명": 성별 비율을 알 수 없음
        friend_gender = friend_genders[0] if friend_genders else me  # 숫자만 입력하면 친구로 본다
        people += [friend_gender] * count_n
    else:
        people += friend_genders

    members = [me] + people
    trimmed = len(members) > MAX_FOREGROUND
    members = members[:MAX_FOREGROUND]
    boys = members.count("male")
    girls = members.count("female")
    solo = len(members) == 1

    if solo:
        tags = list(_MALE_SOLO_TAGS if me == "male" else _FEMALE_SOLO_TAGS)
        negative = _MALE_SOLO_NEGATIVE if me == "male" else _FEMALE_SOLO_NEGATIVE
    else:
        tags = _count_tags(boys, girls)
        if girls == 0:
            negative = _MALE_GROUP_NEGATIVE
        elif boys == 0:
            negative = _FEMALE_GROUP_NEGATIVE
        else:
            negative = ""
    tags += role_tags
    if trimmed:
        tags.append("out of focus background")

    summary = f"나 포함 {len(members)}명 (남 {boys}, 여 {girls})" + (f", {len(people) + 1}명 중 4명만 그림" if trimmed else "")
    return Cast(boys=boys, girls=girls, solo=solo, tags=tags, negative=negative, trimmed=trimmed, summary=summary)


# LLM이 만든 인원/성별/관계 태그. cast가 확정되면 이것들은 지우고 cast의 태그로 대체한다.
_PERSON_COUNT_TAG = re.compile(r"^\(?\s*\d+\s*(girls?|boys?|women|woman|men|man)\s*(:\s*[\d.]+)?\)?$", re.IGNORECASE)
_PERSON_WORD_TAGS = {
    "solo", "alone", "couple", "group", "multiple girls", "multiple boys", "male focus", "female focus",
    "girl", "boy", "woman", "man", "women", "men", "female", "male",
    "young adult woman", "young adult man", "middle aged woman", "middle aged man",
    "mature female", "mature male", "mother", "father", "mom", "dad", "brother", "brothers", "sister", "sisters",
    "boyfriend", "girlfriend", "family",
}


def strip_person_tags(positive: str) -> str:
    out = []
    for tag in (t.strip() for t in positive.split(",")):
        if not tag:
            continue
        low = tag.lower()
        if _PERSON_COUNT_TAG.match(low) or low in _PERSON_WORD_TAGS:
            continue
        out.append(tag)
    return ", ".join(out)
