"""
app/services/image_prompt_template.py
LLM 호출 없이 사전 매핑만으로 이미지 프롬프트를 만드는 변환기 (IMAGE_PROMPT_MODE=template일 때 사용).

LLM 방식(image_prompt_service.py)이 A6000 기준 약 93초 걸려서 Cloudflare 100초 제한에 걸리는 문제의 대안.
시스템 프롬프트의 규칙은 그대로 지킴:
  - 인원수는 성별+정확한 숫자로, 프롬프트 맨 앞에 배치 ("1girl, solo" / "2girls, 1boy" ...)
  - 커플은 "1girl, young adult woman, 1boy, young adult man, couple"
  - 최대 6명, 사람 많은 장소는 전경 최대 3명 + 배경은 흐린 실루엣/보케만
  - 부모님은 "mature female, mother" / "mature male, father"
  - 감정별 표정/조명 태그, 4명 이상이면 화풍 강조 태그
  - 마지막은 "gamjeong style", negative는 v3 고정값(인원 초과 방지 항목 포함)

[반영되는 정보]
  - 함께한 사람(who): 앱 선택지 14개 전부 + 자주 나오는 자유입력 단어(친구들, 동기, 할머니, 선배 등)
  - 사용자 성별: 계정 설정 gender("남성"/"여성"). 없으면 LLM 예시와 같은 1girl 기본
  - 감정: KoBERT 24종 전부 -> 표정/조명 태그
  - 장소(where): 자주 나오는 장소 사전. where에서 못 찾으면 일기 본문에서 한 번 더 찾고, 그래도 없으면 생략
  - 시간대(when): 앱이 보내는 "8월 24일 월요일 오후 2시 30분" 형식 + 아침/점심/저녁/밤/새벽 단어
  - 행동/소품: 일기 본문에 나오는 자주 쓰는 행동 단어(공부, 커피, 산책, 영화, 노래, 케이크 등) 최대 3개
  - 아바타(안경/앞머리/머리길이/머리색): 여기서 안 함. sd3_service._avatar_tags()가 llm/template
    두 모드 모두에 똑같이 뒤에 붙여줌 (이미 결정론적 매핑 테이블이 있어서 중복 구현 안 함)

[빠지는 정보 - 템플릿의 한계]
  - 사전에 없는 장소/행동/사람은 그냥 빠짐 (예: "셀프 세차장", "고압수 세차" 같은 구체적인 장면)
  - 일기 속 구체적인 소품, 자세, 구도, 사람 사이의 상호작용(같이 앉아있음, 안고 있음 등)
  - "친구"처럼 인원이 불명확한 경우 문맥 추정 불가 -> 고정 규칙(1명, 본문에 '친구들' 있으면 2명)
  - 자녀/형제처럼 성별이 불명확한 사람은 고정값으로 처리 (아래 사전 주석 참고)
  - 같은 입력이면 항상 같은 프롬프트 (seed만 바뀌므로 구도 다양성은 seed에 의존)
"""
import re

from app.services.image_prompt_service import FALLBACK_NEGATIVE

MAX_PEOPLE = 6
MAX_FOREGROUND_IN_CROWD = 3

STYLE_TAGS = "flat color, cel shading, line art, illustration"
CROWD_TAGS = "foreground, blurred crowd silhouettes in background, out of focus background, bokeh"

# KoBERT 24종 -> 표정/분위기 태그 (긍정: smile/blush/warm lighting 계열, 부정: frown/dim lighting 계열)
EMOTION_TAGS = {
    # 긍정 - 상승형
    "행복한": "smile, blush, happy, warm lighting",
    "기쁜": "smile, open mouth, happy, warm lighting",
    "기대되는": "smile, blush, sparkling eyes, anticipation, warm lighting",
    "설레는": "shy smile, blush, soft warm lighting",
    # 긍정 - 활동형
    "신나는": "smile, open mouth, excited expression, energetic, warm lighting",
    "열정적인": "determined smile, fired up, clenched hand, warm lighting",
    "즐거운": "laughing, smile, warm lighting",
    # 긍정 - 해소형
    "상쾌한": "smile, refreshed, gentle breeze, bright lighting",
    "뿌듯한": "proud smile, satisfied expression, warm lighting",
    "후련한": "relieved expression, smile, closed eyes, warm lighting",
    # 긍정 - 안정형
    "감사한": "gentle smile, grateful expression, blush, warm lighting",
    "편안한": "relaxed, gentle smile, calm atmosphere, soft warm lighting",
    # 부정 - 경계형
    "우울한": "sad, downcast eyes, gloomy atmosphere, dim lighting",
    "실망한": "disappointed, frown, looking down, dim lighting",
    "후회되는": "regretful expression, frown, looking down, dim lighting",
    "슬픈": "sad, teary eyes, frown, dim lighting",
    # 부정 - 침체형
    "두려운": "scared, worried expression, dim lighting",
    "불안한": "anxious, worried expression, nervous, dim lighting",
    "막막한": "troubled expression, frown, blank stare, dim lighting",
    # 부정 - 소모형
    "피곤한": "tired expression, sleepy, slouching, dim lighting",
    "외로운": "lonely, melancholic expression, dim lighting",
    "지루한": "bored, half-closed eyes, head rest, dim lighting",
    # 부정 - 폭발형
    "화나는": "angry, frown, clenched teeth, dim lighting",
    "짜증나는": "annoyed, frown, pout, dim lighting",
}
NEUTRAL_EMOTION_TAGS = "calm expression, soft lighting"

# 함께한 사람 사전: 키워드 -> [(역할, 성별, 태그), ...]
#   성별: "f" / "m" / "same"(사용자와 같은 성별) / "opposite"(반대 성별) / None(사람 아님: 동물)
#   역할: 같은 역할은 한 번만 들어감 (가족+엄마 -> 엄마 1명). "friend*"는 누적.
# 앱 선택지(DiaryWhoScreen.kt): 가족, 남매, 친구, 남성친구, 여성친구, 연인, 반려동물, 강아지, 고양이, 자녀, 엄마, 아빠, 형제, 혼자
WHO_DICT = {
    "혼자": [],
    "가족": [("mother", "f", "mature female, mother"), ("father", "m", "mature male, father")],
    "엄마": [("mother", "f", "mature female, mother")],
    "어머니": [("mother", "f", "mature female, mother")],
    "아빠": [("father", "m", "mature male, father")],
    "아버지": [("father", "m", "mature male, father")],
    "부모님": [("mother", "f", "mature female, mother"), ("father", "m", "mature male, father")],
    "남매": [("sibling", "opposite", "siblings")],
    "형제": [("sibling", "same", "siblings")],  # 형제/자매 성별을 알 수 없어서 사용자와 같은 성별로 고정
    "자매": [("sibling", "f", "sisters")],
    "언니": [("sibling", "f", "sisters")],
    "누나": [("sibling", "f", "siblings")],
    "오빠": [("sibling", "m", "siblings")],
    "형": [("sibling", "m", "brothers")],
    "동생": [("younger_sibling", "same", "siblings")],
    "자녀": [("child", "f", "child")],  # 자녀 성별을 알 수 없어서 1girl+child로 고정
    "아이": [("child", "f", "child")],
    "딸": [("child", "f", "child, daughter")],
    "아들": [("child", "m", "child, son")],
    "할머니": [("grandmother", "f", "elderly woman, grandmother")],
    "할아버지": [("grandfather", "m", "elderly man, grandfather")],
    "친구": [("friend1", "same", "friends")],
    "친구들": [("friend1", "same", "friends"), ("friend2", "opposite", "friends")],
    "동기": [("friend1", "same", "friends"), ("friend2", "opposite", "friends")],
    "동아리": [("friend1", "same", "friends"), ("friend2", "opposite", "friends")],
    "여성친구": [("friend_f", "f", "friends")],
    "여자사람친구": [("friend_f", "f", "friends")],
    "남성친구": [("friend_m", "m", "friends")],
    "남자사람친구": [("friend_m", "m", "friends")],
    "연인": [("partner", "opposite", "couple")],
    "여자친구": [("partner", "f", "couple")],
    "남자친구": [("partner", "m", "couple")],
    "애인": [("partner", "opposite", "couple")],
    "동료": [("coworker", "same", "coworkers, office")],
    "선배": [("senior", "same", "")],
    "후배": [("junior", "same", "")],
    "교수님": [("professor", "m", "professor")],
    "선생님": [("teacher", "f", "teacher")],
    "반려동물": [("pet", None, "pet")],
    "강아지": [("dog", None, "dog")],
    "고양이": [("cat", None, "cat")],
}

# 일기 본문에 이 단어가 있으면 "친구"를 1명 -> 2명으로 늘림
FRIENDS_GROUP_HINTS = ("친구들", "다 같이", "다같이", "애들", "동기들")

# 장소 사전: 키워드 -> 태그. 긴 키워드부터 매칭 (예: "친구네 집"이 "집"보다 먼저)
PLACE_DICT = {
    "자취방": "small apartment room, indoors",
    "친구네 집": "friend's house, living room, indoors",
    "친구 집": "friend's house, living room, indoors",
    "본가": "family home, living room, indoors",
    "할머니댁": "grandmother's house, traditional korean house, indoors",
    "할머니 댁": "grandmother's house, traditional korean house, indoors",
    "집": "home, living room, indoors",
    "방": "bedroom, indoors",
    "학교": "school, campus",
    "캠퍼스": "university campus",
    "강의실": "classroom, lecture hall, indoors",
    "교실": "classroom, indoors",
    "도서관": "library, bookshelves, indoors",
    "카페": "cafe, coffee shop, indoors",
    "식당": "restaurant, indoors",
    "음식점": "restaurant, indoors",
    "공원": "park, trees, outdoors",
    "한강": "han river park, riverside, outdoors",
    "하천": "riverside path, outdoors",
    "바다": "beach, ocean, outdoors",
    "해변": "beach, ocean, outdoors",
    "산": "mountain trail, nature, outdoors",
    "노래방": "karaoke room, colorful lighting, indoors",
    "영화관": "movie theater, indoors",
    "회사": "office, indoors",
    "사무실": "office, indoors",
    "헬스장": "gym, indoors",
    "체육관": "gym, indoors",
    "운동장": "sports field, outdoors",
    "백화점": "shopping mall, indoors",
    "쇼핑몰": "shopping mall, indoors",
    "마트": "supermarket, indoors",
    "편의점": "convenience store, indoors",
    "병원": "hospital, indoors",
    "지하철": "subway train, indoors",
    "버스": "bus interior",
    "기차": "train interior",
    "공항": "airport, indoors",
    "놀이공원": "amusement park, outdoors",
    "워터파크": "water park, outdoors",
    "축제": "festival, outdoors",
    "콘서트": "concert venue, stage lights",
    "공연장": "concert venue, stage lights",
    "야구장": "baseball stadium, outdoors",
    "경기장": "stadium, outdoors",
    "박람회": "exhibition hall, indoors",
    "미술관": "art museum, gallery, indoors",
    "박물관": "museum, indoors",
    "시장": "traditional market, outdoors",
    "길거리": "street, outdoors",
    "거리": "street, outdoors",
}
# 배경에 사람이 많은 장소 (시스템 프롬프트 규칙 4)
CROWDED_PLACES = ("놀이공원", "워터파크", "축제", "콘서트", "공연장", "야구장", "경기장", "박람회", "시장")

# 행동/소품 사전: 일기 본문에서 찾음. 위에서부터 우선, 최대 3개
ACTIVITY_DICT = [
    ("공부", "studying, desk, notebook"),
    ("과제", "studying, laptop, desk"),
    ("시험", "studying, desk, notebook"),
    ("케이크", "birthday cake, candles"),
    ("생일", "birthday cake, celebration"),
    ("커피", "coffee cup"),
    ("노래", "singing, holding microphone"),
    ("영화", "watching movie"),
    ("자전거", "riding bicycle"),
    ("산책", "walking"),
    ("운동", "exercising, sportswear"),
    ("요리", "cooking, kitchen"),
    ("통화", "talking on phone, holding phone"),
    ("전화", "talking on phone, holding phone"),
    ("게임", "playing video games"),
    ("책", "reading book"),
    ("쇼핑", "shopping bags"),
    ("사진", "taking photo, camera"),
    ("여행", "travel, backpack"),
    ("밥", "eating, food on table"),
    ("먹", "eating, food on table"),
    ("수다", "chatting, sitting at table"),
    ("누워", "lying on bed"),
    ("잤다", "sleeping, bed"),
]
MAX_ACTIVITY_TAGS = 3


def _split_who(who) -> list[str]:
    # 앱은 who를 "친구,엄마"처럼 쉼표로 이어붙인 문자열 하나로 보냄. 리스트로 오는 경우도 처리.
    items = who if isinstance(who, list) else [who or ""]
    tokens = []
    for item in items:
        tokens.extend(t.strip() for t in str(item).split(","))
    return [t for t in tokens if t]


def _match_who_token(token: str) -> list | None:
    if token in WHO_DICT:
        return WHO_DICT[token]
    # 자유입력("엄마랑 아빠", "회사 동료들")은 사전 키워드가 들어있는지 긴 것부터 찾음
    remaining = token
    found = []
    for key in sorted(WHO_DICT, key=len, reverse=True):
        if key in remaining:
            found.extend(WHO_DICT[key])
            remaining = remaining.replace(key, " ")
    return found or None


def _resolve_gender(g: str, user_gender: str) -> str:
    if g == "same":
        return user_gender
    if g == "opposite":
        return "m" if user_gender == "f" else "f"
    return g


def _count_tag(n: int, gender: str) -> str:
    word = "girl" if gender == "f" else "boy"
    return f"{n}{word}" if n == 1 else f"{n}{word}s"


def _find_place(where: str, diary_text: str) -> tuple[str | None, str | None]:
    keys = sorted(PLACE_DICT, key=len, reverse=True)
    for key in keys:
        if key in (where or ""):
            return key, PLACE_DICT[key]
    # 본문에서 찾을 땐 한 글자 키워드(집/방/산)는 제외: "산책", "방금", "집중" 같은 오탐이 너무 많음
    for key in keys:
        if len(key) >= 2 and key in (diary_text or ""):
            return key, PLACE_DICT[key]
    return None, None


def _time_tags(when: str) -> str | None:
    text = when or ""
    m = re.search(r"(오전|오후)\s*(\d{1,2})\s*시", text)
    if m:
        hour = int(m.group(2)) % 12 + (12 if m.group(1) == "오후" else 0)
    else:
        m = re.search(r"(\d{1,2})\s*시", text)
        hour = int(m.group(1)) if m else None
        if hour is not None and any(w in text for w in ("저녁", "밤")) and hour < 12:
            hour += 12

    if hour is None:
        for word, tags in (("새벽", "night, dark sky"), ("아침", "morning, sunlight"),
                           ("점심", "daytime"), ("낮", "daytime"), ("오후", "afternoon"),
                           ("저녁", "evening, sunset"), ("밤", "night")):
            if word in text:
                return tags
        return None
    if 5 <= hour < 11:
        return "morning, sunlight"
    if 11 <= hour < 16:
        return "daytime"
    if 16 <= hour < 19:
        return "evening, sunset"
    return "night"


def _activity_tags(diary_text: str) -> list[str]:
    tags = []
    remaining = diary_text or ""
    for key, tag in ACTIVITY_DICT:
        if key in remaining:
            # 찾은 단어는 지워서 겹치는 짧은 키워드가 다시 안 걸리게 함 ("산책"을 찾은 뒤 "책"이 또 걸리는 문제)
            remaining = remaining.replace(key, " ")
            if tag not in tags:
                tags.append(tag)
        if len(tags) >= MAX_ACTIVITY_TAGS:
            break
    return tags


def build_template_prompt(diary_text: str, who, emotion: str, where: str, when: str,
                          gender: str | None = None) -> dict:
    user_gender = "m" if (gender or "").strip() in ("남성", "남자", "male", "m") else "f"

    # 1) 사람: 사용자 본인 + 사전에서 찾은 동행자 (같은 역할은 1번만)
    companions = []  # (role, gender, tag)
    animal_tags = []
    seen_roles = set()
    tokens = _split_who(who)
    for token in tokens:
        entries = _match_who_token(token) or []
        for role, g, tag in entries:
            if role in seen_roles:
                continue
            seen_roles.add(role)
            if g is None:
                animal_tags.append(tag)
            else:
                companions.append((role, _resolve_gender(g, user_gender), tag))

    has_friend = any(role == "friend1" for role, _, _ in companions)
    if has_friend and "friend2" not in seen_roles and any(h in (diary_text or "") for h in FRIENDS_GROUP_HINTS):
        companions.append(("friend2", "m" if user_gender == "f" else "f", "friends"))

    place_key, place_tag = _find_place(where, diary_text)
    crowded = place_key in CROWDED_PLACES

    max_people = MAX_FOREGROUND_IN_CROWD if crowded else MAX_PEOPLE
    companions = companions[: max_people - 1]  # 본인 1명 자리 남기고 자름 (뒤에 들어온 사람부터 빠짐)

    girls = (1 if user_gender == "f" else 0) + sum(1 for _, g, _ in companions if g == "f")
    boys = (1 if user_gender == "m" else 0) + sum(1 for _, g, _ in companions if g == "m")
    total = girls + boys
    roles = {role for role, _, _ in companions}

    tags = []
    is_couple = roles == {"partner"}
    if is_couple and girls == 1 and boys == 1:
        tags.append("1girl, young adult woman, 1boy, young adult man, couple")
    else:
        # 인원 태그는 맨 앞 (규칙 3)
        if girls:
            tags.append(_count_tag(girls, "f"))
        if boys:
            tags.append(_count_tag(boys, "m"))
        if total == 1:
            tags.append("solo")
        user_desc = "young adult woman" if user_gender == "f" else "young adult man"
        # 부모님/조부모/아이와 같이 있으면 본인 나이대를 명시해야 엄마+아들처럼 오인 안 됨
        if total == 1 or roles & {"mother", "father", "grandmother", "grandfather", "child", "professor", "teacher"}:
            tags.append(user_desc)
        else:
            tags.append("young adults")
        for _, _, tag in companions:
            if tag and tag not in tags:
                tags.append(tag)

    tags.extend(animal_tags)

    # 2) 감정
    tags.append(EMOTION_TAGS.get(emotion, NEUTRAL_EMOTION_TAGS))

    # 3) 행동/소품, 장소, 시간대
    tags.extend(_activity_tags(diary_text))
    if place_tag:
        tags.append(place_tag)
    time_tag = _time_tags(when)
    if time_tag:
        tags.append(time_tag)

    # 4) 군중 장소 / 화풍 강조
    if crowded:
        tags.append(CROWD_TAGS)
    if total >= 4:
        tags.append(STYLE_TAGS)

    tags.append("gamjeong style")
    # 사전끼리 겹치는 태그 제거 (예: "케이크"와 "생일"이 둘 다 birthday cake)
    unique = list(dict.fromkeys(t.strip() for group in tags for t in group.split(",") if t.strip()))
    return {"positive": ", ".join(unique), "negative": FALLBACK_NEGATIVE}
