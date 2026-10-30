"""
app/services/danbooru_tags.py
이미지 프롬프트 태그를 Danbooru 태그 기준으로 정리 (patch 13)

왜 필요한가:
  Illustrious XL은 Danbooru 태그로 학습된 모델이라, 사전에 없는 영어 표현이나 게시물이 아주 적은 태그는
  거의 반영이 안 되거나 엉뚱하게 그려짐. 2026-10-30 헬스장 그림 로그 예:
    - "weight bench"  -> Danbooru 게시물 34건 (모델이 거의 모름 -> 벤치/바벨이 뒤엉킨 그림)
    - "dumbbells"     -> 태그 아님 (정식 태그는 단수형 "dumbbell", 1,893건)
    - "working out"   -> "exercising"의 별칭 (같은 뜻이 두 번 들어감)
    - "warm lighting", "excited expression", "grill house" -> 태그 아님
  태그가 아닌 단어도 토큰은 그대로 차지해서, 프롬프트가 75토큰을 넘어 두 덩어리로 잘리는 원인이 됐음.

하는 일 (filter_tags):
  1) PHRASE_MAP: 우리 사전/LLM이 자주 쓰는 표현을 Danbooru 태그로 바꿈 ("food on table" -> "food, table")
  2) 별칭/복수형을 정식 태그로 ("working out" -> "exercising", "dumbbells" -> "dumbbell")
  3) 게시물 수가 IMAGE_TAG_MIN_POSTS(기본 100) 미만이거나 사전에 없는 태그는 버림
  4) KEEP_TAGS는 Danbooru 태그가 아니어도 그대로 둠 (팀이 테스트해서 넣은 태그, 코드가 인원 판단에 쓰는 태그)
  5) 정리 후 중복 제거, 가중치 "(태그:1.2)"는 유지

데이터: app/data/danbooru_tags.tsv
  a1111-sd-webui-tagcomplete의 tags/danbooru.csv 중 일반(0)/메타(5) 분류, 게시물 100건 이상만 추림
  형식: 태그<TAB>게시물수<TAB>별칭(쉼표 구분)

.env
  IMAGE_TAG_FILTER (기본 true): false면 이 정리를 건너뜀 (patch 12 이전과 같은 태그)
  IMAGE_TAG_MIN_POSTS (기본 100): 이 수보다 게시물이 적은 태그는 버림
"""
import os
import re
from functools import lru_cache

_DATA_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "danbooru_tags.tsv")

# Danbooru 태그는 아니지만 일부러 남기는 태그
KEEP_TAGS = {
    # LoRA 트리거 / 화풍 보조 (다인원 그림에서 화풍 유지에 효과 있었음)
    "gamjeong style", "illustration", "cel shading",
    # sd3_service.sanitize_image_tags가 일부러 바꿔 넣는 태그 (patch 9~10 테스트로 정함)
    "karaoke room", "colorful lighting",
    # 인원/관계 판단 코드(ensure_male_group 등)가 읽는 태그
    "mother", "father", "grandmother", "grandfather", "daughter", "son",
    "young adult woman", "young adult man", "young adults", "elderly woman", "elderly man", "coworkers",
}

# 표현 -> Danbooru 태그 목록 (빈 목록 = 대체할 태그가 없어서 버림)
PHRASE_MAP = {
    # 조명/분위기 (Danbooru 태그 아님. 화풍 쪽 warm colors가 이미 있어서 버림)
    "warm lighting": [], "soft warm lighting": [], "bright lighting": [], "soft lighting": [],
    "calm atmosphere": [], "gloomy atmosphere": ["shaded face"],
    # 표정
    "excited expression": ["excited"], "energetic": [], "anticipation": [], "fired up": [],
    "determined smile": ["determined", "smile"], "shy smile": ["shy", "smile"], "refreshed": [],
    "gentle breeze": ["wind"], "proud smile": ["smile"], "satisfied expression": ["light smile"],
    "relieved expression": ["light smile"], "gentle smile": ["light smile"], "grateful expression": ["light smile"],
    "regretful expression": ["sad"], "teary eyes": ["tears"], "worried expression": ["worried"], "anxious": [],
    "troubled expression": ["worried"], "blank stare": ["empty eyes"], "tired expression": ["half-closed eyes"],
    "melancholic expression": ["sad"], "calm expression": ["closed mouth"],
    # 시간
    "daytime": ["day"], "afternoon": ["day"], "dark sky": ["night sky"],
    # 장소
    "home": [], "small apartment room": ["bedroom"], "friend's house": ["house"], "family home": ["house"],
    "grandmother's house": ["house"], "traditional korean house": ["east asian architecture"],
    "campus": ["school"], "university campus": ["school"], "lecture hall": ["classroom"],
    "han river park": ["river", "park"], "riverside": ["river"], "riverside path": ["river", "path"],
    "riverside park": ["river", "park"], "mountain trail": ["mountain", "path"], "sports field": ["field"],
    "shopping mall": ["mall"], "subway train": ["train interior"], "water park": ["pool"],
    "concert venue": ["concert"], "exhibition hall": [], "art museum": ["museum"], "gallery": ["museum"],
    "traditional market": ["market"], "grill house": ["restaurant", "grill"], "korean bbq": ["yakiniku"],
    "barbecue restaurant": ["restaurant", "grill"], "chinese restaurant": ["restaurant", "chinese food"],
    "exam hall": ["classroom"], "grocery shelves": ["shelf"],
    # 행동/소품
    "watching movie": [], "reading book": ["reading", "holding book"], "taking photo": ["taking picture"],
    "food on table": ["food", "table"], "chatting": ["talking"], "sitting at table": ["sitting", "table"],
    "lying on bed": ["lying", "on bed"], "travel": [], "eating and drinking": ["eating", "drinking"],
    "grilled pork belly": ["meat", "grill"], "pork belly": ["meat"], "korean food": ["food"],
    "coffee cup": ["coffee", "cup"], "taking exam": ["writing"], "test paper": ["paper"],
    # 군중 장소용 (image_prompt_template.CROWD_TAGS)
    "blurred crowd silhouettes in background": ["crowd", "blurry background"],
    "out of focus background": ["blurry background"], "foreground": [],
}

# 실내 장면에 같이 있으면 어색한 태그 (실내 고깃집에 바람, 헬스장에 노을)
_INDOOR_CONFLICTS = {"wind", "sunset", "sky", "cloud", "night sky", "orange sky"}

_WEIGHT_RE = re.compile(r"^\((.+?)(?::\s*([\d.]+))?\)$")


@lru_cache(maxsize=1)
def _load() -> tuple[dict, dict]:
    counts, aliases = {}, {}
    with open(_DATA_PATH, encoding="utf-8") as f:
        for line in f:
            if line.startswith("#") or not line.strip():
                continue
            name, count, alias_str = (line.rstrip("\n").split("\t") + ["", ""])[:3]
            counts[name] = int(count)
            for a in alias_str.split(","):
                if a:
                    aliases.setdefault(a, name)
    return counts, aliases


def _min_posts() -> int:
    try:
        return int(os.environ.get("IMAGE_TAG_MIN_POSTS", "").strip() or 100)
    except ValueError:
        return 100


def enabled() -> bool:
    return os.environ.get("IMAGE_TAG_FILTER", "true").strip().lower() not in ("0", "false", "no", "off")


def canonical(tag: str) -> tuple[str | None, int]:
    """태그 -> (정식 Danbooru 태그(공백 표기), 게시물 수). 못 찾으면 (None, 0). 별칭/복수형도 찾아줌."""
    counts, aliases = _load()
    key = re.sub(r"\s+", "_", tag.strip().lower().replace("\\(", "(").replace("\\)", ")"))
    candidates = [key]
    if key.endswith("ies"):
        candidates.append(key[:-3] + "y")
    if key.endswith("es"):
        candidates.append(key[:-2])
    if key.endswith("s"):
        candidates.append(key[:-1])
    for k in candidates:
        name = k if k in counts else aliases.get(k)
        if name and name in counts:
            return name.replace("_", " "), counts[name]
    return None, 0


def _format(tag: str, weight: str | None) -> str:
    tag = tag.replace("(", "\\(").replace(")", "\\)")  # Danbooru 태그 속 괄호는 ComfyUI 가중치 문법과 겹쳐서 이스케이프
    return f"({tag}:{weight})" if weight else tag


def filter_tags(positive: str) -> tuple[str, list[str], list[str]]:
    """
    쉼표로 구분된 태그 문자열 -> (정리된 문자열, 버린 태그 목록, 바꾼 내역 목록)
    예: "gym, working out, weight bench, dumbbells" -> "gym, exercising, dumbbell"
        버림 ["weight bench(34건)"], 바꿈 ["working out->exercising", "dumbbells->dumbbell"]
    """
    min_posts = _min_posts()
    out, seen, dropped, changed = [], set(), [], []

    def add(tag: str, weight: str | None):
        low = tag.lower()
        if low not in seen:
            seen.add(low)
            out.append(_format(tag, weight) if low not in KEEP_TAGS else (f"({tag}:{weight})" if weight else tag))

    for raw in (t.strip() for t in (positive or "").split(",")):
        if not raw:
            continue
        m = _WEIGHT_RE.match(raw)
        inner, weight = (m.group(1).strip(), m.group(2)) if m else (raw, None)
        low = inner.lower()
        if low in KEEP_TAGS:
            add(inner, weight)
            continue
        replaced = PHRASE_MAP.get(low)
        if replaced is not None:
            changed.append(f"{inner}->{', '.join(replaced) if replaced else '(뺌)'}")
            for r in replaced:
                add(r, weight)
            continue
        name, count = canonical(inner)
        if name is None:
            dropped.append(inner)
            continue
        if count < min_posts:
            dropped.append(f"{inner}({count}건)")
            continue
        if name != low:
            changed.append(f"{inner}->{name}")
        add(name, weight)
    if "indoors" in seen:
        conflicts = [t for t in out if t.lower() in _INDOOR_CONFLICTS]
        out = [t for t in out if t.lower() not in _INDOOR_CONFLICTS]
        dropped += [f"{t}(실내)" for t in conflicts]
    return ", ".join(out), dropped, changed
