"""
app/services/sd3_service.py
재유 담당 - 그림일기 이미지 생성 (파일명은 sd3지만 실제로는 SDXL/Illustrious 사용 중, 상세는 sd3_loader.py 참고)

파이프라인:
일기 생성(LLM 1번째 호출) -> 감정분석(KoBERT) -> 이미지 프롬프트 변환(LLM 2번째 호출, image_prompt_service) -> ComfyUI

ComfyUI API(/prompt, /history, /view)를 호출해 이미지를 만들고,
결과를 Supabase Storage에 업로드한 뒤 공개 URL을 반환한다.
"""
import os
import re
import time
import uuid

import requests

from app.models.sd3_loader import COMFYUI_URL, load_workflow_template
from app.services.cast import build_cast, strip_person_tags
from app.services import danbooru_tags
from app.services.image_prompt_service import translate_to_image_prompt
from app.database import supabase

STORAGE_BUCKET = "diary-images"  # Supabase Storage에 미리 만들어둬야 함 (public bucket)

# 실제 export한 workflow_api.json 기준으로 확인된 노드 ID
POSITIVE_PROMPT_NODE_ID = "4"
NEGATIVE_PROMPT_NODE_ID = "5"
SEED_NODE_ID = "8"

FALLBACK_NEGATIVE_PROMPT = (
    "bad anatomy, extra limbs, missing limbs, deformed arm, malformed hands, "
    "extra fingers, missing fingers, fused fingers, mutated hands, disfigured, "
    "distorted, blurry, low quality, photorealistic, realistic, photo, 3d render, "
    "text, watermark, gibberish text, chinese text, chinese characters, kanji, hanzi, hanja"
)

# 안경 3종 (디자인 확정: 뿔테/동그란/안 씀)
# patch 13: "horn-rimmed glasses"는 Danbooru 태그가 아니라서 둥근 안경으로 그려지곤 했음 -> 정식 태그로
#   뿔테에 가장 가까운 태그: black-framed eyewear(36,715건), 동그란: round eyewear(42,592건, "round glasses"의 정식 이름)
#   (eyewear 태그만으로도 안경이 그려져서 "glasses"는 따로 안 붙임 - 프롬프트 75토큰 안에 넣으려고)
GLASSES_TAG_MAP = {
    "horn_rimmed": "black-framed eyewear",
    "round": "round eyewear",
    "none": None,  # 안경 안 씀 -> 태그 자체를 안 붙임
}

_HAIR_COLOR_MAP = {
    "검정": "black hair", "검정색": "black hair", "black": "black hair",
    "갈색": "brown hair", "brown": "brown hair",
    "금발": "blonde hair", "blonde": "blonde hair",
    "밝은갈색": "light brown hair",
    "회색": "grey hair", "은발": "silver hair", "gray": "grey hair", "grey": "grey hair",
    "빨강": "red hair", "red": "red hair",
    "분홍": "pink hair", "pink": "pink hair",
}


def _avatar_tags(glasses: str, bangs: bool, hair_length: str, hair_color: str) -> str:
    """
    사용자 프로필의 아바타 속성(안경/앞머리/머리길이/머리색)을 프롬프트 태그로 변환.
    LLM(image_prompt_service)한테 맡기면 가끔 빼먹거나 다르게 표현하는 경우가 있어서,
    여기서 결정론적으로(항상 동일하게) 붙여 일관성을 보장한다.
    """
    tags = []
    glasses_tag = GLASSES_TAG_MAP.get(glasses)
    if glasses_tag:
        tags.append(glasses_tag)

    # "no bangs"는 Danbooru 태그가 아님 -> 앞머리 없이 이마가 보이는 "forehead"(44,455건)로 (patch 13)
    tags.append("blunt bangs" if bangs else "forehead")

    length_tag = {"short": "short hair", "medium": "medium hair", "long": "long hair"}.get(
        hair_length, "medium hair"
    )
    tags.append(length_tag)

    # 앱이 "blackhair"처럼 붙여쓴 값을 보내면 그대로 태그가 돼서 색이 안 먹었음 -> 공백/대소문자 정규화 후 매핑
    key = re.sub(r"[\s_-]+", "", str(hair_color or "")).lower()
    color_tag = _HAIR_COLOR_MAP.get(key)
    if color_tag is None and key.endswith("hair") and key[:-4].isascii() and key[:-4].isalpha():
        color_tag = _HAIR_COLOR_MAP.get(key[:-4]) or f"{key[:-4]} hair"
    tags.append(color_tag or "black hair")

    return ", ".join(tags)


# --- 성별 반영 (2026-10 추가) ---
# 이미지 프롬프트 변환 LLM(llm 모드)은 계정 성별을 전혀 모르고, 예시도 전부 1girl이라 기본이 여성으로 나옴.
# LLM 출력 규칙(SYSTEM_PROMPT 해시 고정)은 건드리지 않고, 변환 결과를 여기서 결정론적으로 보정한다.
_MALE_SWAP = {
    "1girl": "1boy",
    "young adult woman": "young adult man",
    "woman": "man",
    "girl": "boy",
    "female focus": "male focus",
}
# 모델/LoRA가 여성 쪽으로 쏠려 있어서, 남성일 때는 가중치 문법 (태그:1.3)으로 강하게 지정한다.
# (ComfyUI CLIPTextEncode가 지원하는 문법)
_MALE_POSITIVE_PREFIX = "(1boy:1.3), (male focus:1.2)"
_MALE_EXTRA_NEGATIVE = "(1girl:1.3), (girl:1.2), (female:1.2), feminine"
_PERSON_TAG = re.compile(r"^(\d+)(girl|girls|boy|boys)$")


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


def apply_gender(positive: str, negative: str, gender) -> tuple[str, str]:
    """
    계정 성별이 남성이고 프롬프트가 '혼자 나오는 1인' 구도일 때만 1girl -> 1boy 등으로 바꾼다.
    - 인원 태그가 정확히 1개(1girl 또는 1boy)일 때만 동작 -> 커플/친구들("2girls, 1boy" 등)은 건드리지 않음
    - 여성/미입력/기타는 변경 없음 (기본값이 이미 여성형이라)
    """
    if normalize_gender(gender) != "male":
        return positive, negative
    tags = [t.strip() for t in positive.split(",") if t.strip()]
    person_tags = [t for t in tags if _PERSON_TAG.match(t)]
    if person_tags != ["1girl"] and person_tags != ["1boy"]:
        return positive, negative
    swapped = [t for t in (_MALE_SWAP.get(t, t) for t in tags) if t not in ("1boy", "male focus")]
    new_positive = ", ".join([_MALE_POSITIVE_PREFIX] + swapped)
    new_negative = f"{negative}, {_MALE_EXTRA_NEGATIVE}" if negative else _MALE_EXTRA_NEGATIVE
    return new_positive, new_negative


# --- "혼자" 인원 보정 (2026-10 추가) ---
# 이미지 프롬프트 변환 LLM이 가끔 인원 태그(1girl/1boy/solo)를 통째로 빼먹는다.
# 사람 수 태그가 없으면 모델이 임의로 여러 명을 그리므로, Who가 "혼자"뿐이면 서버가 직접 확정한다.
_SOLO_NEGATIVE = "multiple girls, multiple boys, 2girls, 2boys, 3girls, 3boys, group"


def is_solo(who) -> bool:
    """Who가 '혼자'만 선택된 경우 True (문자열 "혼자" / ["혼자"] / "혼자, 혼자" 모두)."""
    if isinstance(who, str):
        items = re.split(r"[,/]", who)
    else:
        items = [str(x) for x in (who or [])]
    items = [i.strip() for i in items if i and i.strip()]
    return bool(items) and all(i == "혼자" for i in items)


def ensure_solo_person(positive: str, negative: str, who, gender) -> tuple[str, str]:
    """
    Who가 '혼자'인데 LLM 프롬프트에 인원 태그가 하나도 없으면, 맨 앞에 '1boy|1girl, solo'를 넣는다.
    - 성별 남성: 1boy, 여성: 1girl, 모르면 solo만
    - 인원 태그가 이미 있으면(LLM이 제대로 만든 경우) 손대지 않고 solo 태그만 보강
    """
    if not is_solo(who):
        return positive, negative
    tags = [t.strip() for t in positive.split(",") if t.strip()]
    if any(_PERSON_TAG.match(t) for t in tags):
        if "solo" not in tags and "alone" not in tags:
            tags.insert(0, "solo")
            positive = ", ".join(tags)
        return positive, negative
    kind = normalize_gender(gender)
    lead = {"male": ["1boy", "solo"], "female": ["1girl", "solo"]}.get(kind, ["solo"])
    new_negative = f"{negative}, {_SOLO_NEGATIVE}" if negative else _SOLO_NEGATIVE
    return ", ".join(lead + tags), new_negative


# --- 이미지 품질 보정 (2026-10-09 ComfyUI 시드 고정 비교 테스트 결과 반영) ---
# Illustrious는 품질 태그를 맨 앞에 두는 게 권장됨. LLM이 이미 같은 태그를 넣었으면 중복 제거.
QUALITY_PREFIX = "masterpiece, best quality, amazing quality, very aesthetic, absurdres"
_QUALITY_TAGS = {t.strip() for t in QUALITY_PREFIX.split(",")} | {"good quality", "high quality", "highres"}


def _quality_prefix() -> str:
    """
    patch 13: .env IMAGE_QUALITY_PREFIX로 바꿔볼 수 있게 함 (기본값은 그대로).
    Illustrious 공식 모델 카드의 품질 태그 목록은 worst/bad/average/good/best quality, masterpiece라서
    amazing quality, very aesthetic은 목록에 없음. 빼면 6토큰 줄어서 75토큰 안에 들어가기 쉬움 -> 시드 고정 비교 후 결정.
    예) IMAGE_QUALITY_PREFIX=masterpiece, best quality, absurdres
    """
    return os.environ.get("IMAGE_QUALITY_PREFIX", "").strip() or QUALITY_PREFIX

# negative는 길게 쌓지 않고 핵심만 쓴다 (긴 목록 vs 짧은 목록을 같은 시드로 비교했을 때 차이가 없었음).
# 이미지 프롬프트 LLM이 내놓는 negative(고정 긴 문자열)는 쓰지 않고 이걸로 대체한다.
# 인원/성별 negative(girl 계열 등)는 계정/구도에 따라 아래 보정 함수들이 따로 덧붙임.
# patch 13: Illustrious 공식 모델 카드(v0.1)의 negative 예시에 있는 lowres, multiple views, comic 추가
#   (multiple views/comic: 한 장에 여러 컷/만화 칸이 생기는 것 방지)
IMAGE_NEGATIVE_BASE = (
    "(text:1.3), (signboard:1.3), (letters:1.2), keyboard, monitor, "
    "worst quality, low quality, lowres, bad anatomy, bad hands, extra fingers, blurry, watermark, extra people, "
    "multiple views, comic, "
    "photorealistic, realistic, 3d, cyberpunk, sci-fi, futuristic, neon lights, glowing, oversaturated"
)

# patch 13: 나이 보정. 성별 보정 단계에서 'young adult man'이 지워지고(Danbooru 태그도 아님) 1boy만 남으면
# 어린 소년처럼 그려지는 경우가 있었음. Illustrious는 학습 데이터 특성상 어려 보이게 나오는 경향이 있어서
# 커뮤니티 가이드가 negative에 child, aged down을 권함 (완벽하진 않음). 자녀/아이가 같이 있으면 넣지 않음.
_AGE_NEGATIVE = "child, aged down"
_CHILD_WORDS = ("자녀", "아이", "딸", "아들", "조카", "아기", "애기")

# patch 13: 구도 태그. 공식 모델 카드가 upper body / cowboy shot / full body 같은 구도 태그를 쓰라고 권함.
# 구도가 없으면 전신+복잡한 자세가 나오기 쉬워서(헬스장: 벤치에 엎드리고 바벨이 떠 있음) 장면에 맞춰 하나만 붙임.
_COMPOSITION_TAGS = ("upper body", "cowboy shot", "full body", "portrait", "close-up")
_TABLE_SCENE = {"eating", "drinking", "food", "table", "studying", "reading", "talking", "cup", "bowl",
                "chopsticks", "writing", "desk", "laptop", "notebook"}
_FULL_BODY_SCENE = {"walking", "running", "jogging", "riding bicycle", "dancing", "hiking", "skiing", "swimming"}

# LoRA 화풍을 확실히 끌어내는 태그. 품질 태그 바로 뒤(프롬프트 앞쪽)에 둔다.
# 2026-10 테스트: 트리거(gamjeong style)가 맨 끝에 있고 컴퓨터 태그가 많아 SF/네온풍으로 나옴.
STYLE_PREFIX = "gamjeong style, illustration, flat color, soft colors, warm colors"

# 이미지 프롬프트 LLM이 '정보처리기사' 같은 단어에서 지어내는 IT/SF 소품 태그 -> 화풍을 SF로 끌고 감, 제거.
_OFF_STYLE_TAG = re.compile(
    r"\d{1,2}:\d{2}|\b\d{1,2}(st|nd|rd|th)\b|\b(january|february|march|april|may|june|july|august|september|october|november|december|"
    r"monday|tuesday|wednesday|thursday|friday|saturday|sunday|nightlife|nightclubs?|clubs?|clubbing|"
    r"dancing|dance floor|electronic music|dj|computers?|keyboards?|laptops?|monitors?|screens?|typing|cyberpunk|sci-?fi|futuristic|hologram\w*|"
    r"server|circuits?|robots?|digital|technology|negative emotions?)\b",
    re.IGNORECASE,
)

# 간판/글자를 부르는 태그: neon 계열은 "간판"이 그려지며 글자가 깨짐 -> 분위기만 남기고 대체, 나머지 글자 계열은 제거.
_NEON_TAG = re.compile(r"\bneon\b", re.IGNORECASE)
_TEXT_PRONE_TAG = re.compile(
    r"\b(signs?|signboard|signage|billboard|banner|poster|text|letters?|lettering|logo|lyrics|subtitles?)\b",
    re.IGNORECASE,
)
# "coin karaoke room"/"karaoke booth"는 발표실/PC방/스튜디오로 그려지는 경우가 있어 "karaoke room"으로 통일
_PLACE_REPLACE = {
    "coin karaoke room": "karaoke room",
    "coin karaoke booth": "karaoke room",
    "coin karaoke": "karaoke room",
    "karaoke booth": "karaoke room",
    "karaoke box": "karaoke room",
}
_GROUP_BOYS_TAG = re.compile(r"^(\d+)boys$")
_MALE_GROUP_NEGATIVE = "girl, 1girl, 2girls, 3girls"


def sanitize_image_tags(positive: str) -> tuple[str, list[str]]:
    """
    이미지 프롬프트 LLM이 만든 positive에서 글자/간판을 부르는 태그를 정리한다.
    - neon 포함 태그 -> "colorful lighting" (분위기는 유지)
    - sign/text/letters/logo 등 글자 계열 태그 -> 제거
    - 장소 태그 통일, 품질 태그 중복/태그 중복 제거
    반환: (정리된 positive, 바뀐 내용 목록 - 로그용)
    """
    changes: list[str] = []
    out: list[str] = []
    seen: set[str] = set()
    for tag in (t.strip() for t in positive.split(",")):
        if not tag:
            continue
        low = tag.lower()
        if low == "gamjeong style":
            changes.append("-gamjeong style(앞쪽 STYLE_PREFIX로 이동)")
            continue
        if _OFF_STYLE_TAG.search(low):
            changes.append(f"-{tag}(SF/IT 소품)")
            continue
        if low in _QUALITY_TAGS:
            changes.append(f"-{tag}(품질 태그 중복)")
            continue
        if low in _PLACE_REPLACE:
            new = _PLACE_REPLACE[low]
            changes.append(f"{tag}->{new}")
            tag, low = new, new
        elif _NEON_TAG.search(low):
            changes.append(f"{tag}->colorful lighting")
            tag, low = "colorful lighting", "colorful lighting"
        elif _TEXT_PRONE_TAG.search(low):
            changes.append(f"-{tag}")
            continue
        if low in seen:
            continue
        seen.add(low)
        out.append(tag)
    return ", ".join(out), changes


def ensure_male_group(positive: str, negative: str, gender) -> tuple[str, str]:
    """
    남성 계정이고 LLM이 '남자만 N명(2boys, 3boys ...)'으로 만들었을 때, 여성이 섞여 그려지는 걸 줄인다.
    - 인원 태그가 정확히 하나(Nboys, N>=2)이고 여성 관련 태그가 없을 때만 동작
      (엄마/누나가 포함된 구성, 커플 등은 건드리지 않음 / 여성 계정도 본인이 여성일 수 있으니 건드리지 않음)
    - (Nboys:1.2) 가중치 + male focus + negative에 girl 계열 추가
    """
    if normalize_gender(gender) != "male":
        return positive, negative
    tags = [t.strip() for t in positive.split(",") if t.strip()]
    person_tags = [t for t in tags if _PERSON_TAG.match(t)]
    if len(person_tags) != 1 or not _GROUP_BOYS_TAG.match(person_tags[0]):
        return positive, negative
    if int(_GROUP_BOYS_TAG.match(person_tags[0]).group(1)) < 2:
        return positive, negative
    if any(w in t.lower() for t in tags for w in ("girl", "woman", "female", "mother", "mom", "sister")):
        return positive, negative
    idx = tags.index(person_tags[0])
    tags[idx] = f"({person_tags[0]}:1.2)"
    if "male focus" not in tags:
        tags.insert(idx + 1, "male focus")
    new_negative = f"{negative}, {_MALE_GROUP_NEGATIVE}" if negative else _MALE_GROUP_NEGATIVE
    return ", ".join(tags), new_negative


def _submit_workflow(positive_prompt: str, negative_prompt: str) -> str:
    workflow = load_workflow_template()
    workflow[POSITIVE_PROMPT_NODE_ID]["inputs"]["text"] = positive_prompt
    workflow[NEGATIVE_PROMPT_NODE_ID]["inputs"]["text"] = negative_prompt or FALLBACK_NEGATIVE_PROMPT
    workflow[SEED_NODE_ID]["inputs"]["seed"] = uuid.uuid4().int % (2**32)

    resp = requests.post(f"{COMFYUI_URL}/prompt", json={"prompt": workflow}, timeout=10)
    resp.raise_for_status()
    return resp.json()["prompt_id"]


def _wait_for_result(prompt_id: str, timeout: int = 120, poll_interval: int = 2) -> bytes:
    start = time.time()
    while time.time() - start < timeout:
        resp = requests.get(f"{COMFYUI_URL}/history/{prompt_id}", timeout=10)
        history = resp.json()
        if prompt_id in history:
            for node_output in history[prompt_id]["outputs"].values():
                if "images" in node_output and node_output["images"]:
                    img_info = node_output["images"][0]
                    img_resp = requests.get(
                        f"{COMFYUI_URL}/view",
                        params={
                            "filename": img_info["filename"],
                            "subfolder": img_info.get("subfolder", ""),
                            "type": img_info.get("type", "output"),
                        },
                        timeout=30,
                    )
                    img_resp.raise_for_status()
                    return img_resp.content
        time.sleep(poll_interval)
    raise TimeoutError(f"ComfyUI 이미지 생성이 {timeout}초 내에 끝나지 않음 (prompt_id={prompt_id})")


def _upload_to_storage(image_bytes: bytes) -> str:
    filename = f"{uuid.uuid4()}.png"
    supabase.storage.from_(STORAGE_BUCKET).upload(
        filename, image_bytes, {"content-type": "image/png"}
    )
    return supabase.storage.from_(STORAGE_BUCKET).get_public_url(filename)


def _composition_tag(body: str, solo: bool) -> str | None:
    """장면 태그를 보고 구도 태그 하나를 고름. 이미 구도 태그가 있으면 None (IMAGE_COMPOSITION_TAG=false면 끔)"""
    if os.environ.get("IMAGE_COMPOSITION_TAG", "true").strip().lower() in ("0", "false", "no", "off"):
        return None
    tags = {t.strip().lower() for t in body.split(",")}
    if tags & set(_COMPOSITION_TAGS):
        return None
    if tags & _TABLE_SCENE:
        return "upper body"
    if tags & _FULL_BODY_SCENE:
        return "full body"
    return "cowboy shot" if solo else "upper body"


def _needs_age_negative(who) -> bool:
    items = who if isinstance(who, list) else [who or ""]
    text = " ".join(str(x) for x in items)
    return not any(w in text for w in _CHILD_WORDS)


def generate_diary_image(
    diary_text: str,
    top_emotion: str,
    who=None,
    where: str = "",
    when: str = "",
    glasses: str = "none",
    bangs: bool = True,
    hair_length: str = "medium",
    hair_color: str = "black",
    gender: str | None = None,
    timings: dict | None = None,
    what: str = "",
    why: str = "",
) -> str:
    """
    일기 텍스트 + 대표 감정 + Who/Where/When + 아바타 속성(안경/앞머리/머리길이/머리색) -> 그림일기 이미지 URL.
    what/why: 사용자 답변 원문 (patch 12, hybrid 모드에서 장면 추출에 씀)
    glasses: "horn_rimmed" | "round" | "none"
    gender: 계정 성별("남성"/"여성"). template 모드는 프롬프트 생성에, 공통으로 apply_gender()가 1인 구도 성별 태그를 보정
    timings: dict를 넘기면 단계별 소요시간(초)을 채워줌 (측정용)
    """
    if timings is None:
        timings = {}

    t0 = time.time()
    prompt_result = translate_to_image_prompt(
        diary_text=diary_text, who=who or [], emotion=top_emotion, where=where, when=when, gender=gender,
        what=what, why=why,
    )
    # 글자/간판을 부르는 태그 정리 + negative는 LLM이 준 긴 문자열 대신 핵심만 쓰는 고정값 사용
    positive_body, tag_changes = sanitize_image_tags(prompt_result["positive"])
    # patch 13: Danbooru 태그 기준으로 정리 (별칭/복수형 -> 정식 태그, 모르는 태그/게시물 적은 태그는 버림)
    if danbooru_tags.enabled():
        positive_body, dropped, renamed = danbooru_tags.filter_tags(positive_body)
        print(f"  [태그 사전] 바꿈: {', '.join(renamed) or '없음'} / 버림: {', '.join(dropped) or '없음'}")
    negative = IMAGE_NEGATIVE_BASE
    if _needs_age_negative(who):
        negative = f"{negative}, {_AGE_NEGATIVE}"
    positive_body_before = positive_body
    # 인원/성별은 앱 입력(Who)과 계정 성별로 서버가 확정한다 ("나"는 항상 포함). 판단 불가면 예전 보정 체인 사용.
    cast = build_cast(who, gender)
    avatar = _avatar_tags(glasses, bangs, hair_length, hair_color)
    avatar_front = False
    if cast is not None:
        rest = strip_person_tags(positive_body)
        # patch 12: 혼자 그림이면 아바타 태그(안경/앞머리/머리)를 인물 태그 바로 뒤로 (앞쪽 태그일수록 영향이 큼).
        # 여러 명일 땐 모두에게 같은 머리/안경이 적용될 수 있어서 예전처럼 맨 끝에 둠.
        avatar_front = cast.solo
        comp = _composition_tag(rest, cast.solo)
        head = cast.tags + ([avatar] if avatar_front else []) + ([comp] if comp else [])
        positive_body = ", ".join(head + ([rest] if rest else []))
        if cast.negative:
            negative = f"{negative}, {cast.negative}"
        positive_body_gender = positive_body
        print(f"  [인원 구성] {cast.summary}")
    else:
        print("  [인원 구성] 판단 불가 -> LLM 인원 태그 + 기존 보정 사용")
        positive_body, negative = ensure_solo_person(positive_body, negative, who, gender)
        positive_body, negative = apply_gender(positive_body, negative, gender)
        positive_body_gender = positive_body
        positive_body, negative = ensure_male_group(positive_body, negative, gender)
        comp = _composition_tag(positive_body, solo=False)
        if comp:
            positive_body = f"{positive_body}, {comp}"
    positive = f"{_quality_prefix()}, {STYLE_PREFIX}, {positive_body}" + ("" if avatar_front else f", {avatar}")
    print(f"  [태그 정리] {', '.join(tag_changes) if tag_changes else '변경 없음'}")
    print(
        f"  [성별 반영] 계정 성별={gender!r} -> {normalize_gender(gender)}, "
        f"who={who!r}, 보정 {'적용됨' if positive_body_gender != positive_body_before else '없음'}, "
        f"남성 그룹 보정 {'적용됨' if positive_body != positive_body_gender else '없음'}"
    )
    print(f"  [최종 positive] {positive}")
    print(f"  [최종 negative] {negative}")
    t1 = time.time()
    timings["image_prompt_sec"] = round(t1 - t0, 2)

    prompt_id = _submit_workflow(positive, negative)
    image_bytes = _wait_for_result(prompt_id)
    t2 = time.time()
    timings["comfyui_sec"] = round(t2 - t1, 2)

    url = _upload_to_storage(image_bytes)
    timings["upload_sec"] = round(time.time() - t2, 2)
    return url