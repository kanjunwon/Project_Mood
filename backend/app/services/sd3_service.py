"""
app/services/sd3_service.py
재유 담당 - 그림일기 이미지 생성 (파일명은 sd3지만 실제로는 SDXL/Illustrious 사용 중, 상세는 sd3_loader.py 참고)

파이프라인:
일기 생성(LLM 1번째 호출) -> 감정분석(KoBERT) -> 이미지 프롬프트 변환(LLM 2번째 호출, image_prompt_service) -> ComfyUI

ComfyUI API(/prompt, /history, /view)를 호출해 이미지를 만들고,
결과를 Supabase Storage에 업로드한 뒤 공개 URL을 반환한다.
"""
import re
import time
import uuid

import requests

from app.models.sd3_loader import COMFYUI_URL, load_workflow_template
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
GLASSES_TAG_MAP = {
    "horn_rimmed": "horn-rimmed glasses",
    "round": "round glasses",
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

    tags.append("blunt bangs" if bangs else "no bangs")

    length_tag = {"short": "short hair", "medium": "medium hair", "long": "long hair"}.get(
        hair_length, "medium hair"
    )
    tags.append(length_tag)

    color_tag = _HAIR_COLOR_MAP.get(hair_color, hair_color if hair_color else "black hair")
    tags.append(color_tag)

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
) -> str:
    """
    일기 텍스트 + 대표 감정 + Who/Where/When + 아바타 속성(안경/앞머리/머리길이/머리색) -> 그림일기 이미지 URL.
    glasses: "horn_rimmed" | "round" | "none"
    gender: 계정 성별("남성"/"여성"). template 모드는 프롬프트 생성에, 공통으로 apply_gender()가 1인 구도 성별 태그를 보정
    timings: dict를 넘기면 단계별 소요시간(초)을 채워줌 (측정용)
    """
    if timings is None:
        timings = {}

    t0 = time.time()
    prompt_result = translate_to_image_prompt(
        diary_text=diary_text, who=who or [], emotion=top_emotion, where=where, when=when, gender=gender
    )
    positive_body = prompt_result["positive"]
    negative = prompt_result.get("negative") or FALLBACK_NEGATIVE_PROMPT
    positive_body_before = positive_body
    positive_body, negative = ensure_solo_person(positive_body, negative, who, gender)
    positive_body, negative = apply_gender(positive_body, negative, gender)
    positive = f"{positive_body}, {_avatar_tags(glasses, bangs, hair_length, hair_color)}"
    print(
        f"  [성별 반영] 계정 성별={gender!r} -> {normalize_gender(gender)}, "
        f"who={who!r}, 보정 {'적용됨' if positive_body != positive_body_before else '없음'}"
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