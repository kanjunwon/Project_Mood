"""
app/services/sd3_service.py
재유 담당 - 그림일기 이미지 생성 (파일명은 sd3지만 실제로는 SDXL/Illustrious 사용 중, 상세는 sd3_loader.py 참고)

파이프라인:
일기 생성(LLM 1번째 호출) -> 감정분석(KoBERT) -> 이미지 프롬프트 변환(LLM 2번째 호출, image_prompt_service) -> ComfyUI

ComfyUI API(/prompt, /history, /view)를 호출해 이미지를 만들고,
결과를 Supabase Storage에 업로드한 뒤 공개 URL을 반환한다.
"""
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
) -> str:
    """
    일기 텍스트 + 대표 감정 + Who/Where/When + 아바타 속성(안경/앞머리/머리길이/머리색) -> 그림일기 이미지 URL.
    glasses: "horn_rimmed" | "round" | "none"
    """
    prompt_result = translate_to_image_prompt(
        diary_text=diary_text, who=who or [], emotion=top_emotion, where=where, when=when
    )
    positive = f"{prompt_result['positive']}, {_avatar_tags(glasses, bangs, hair_length, hair_color)}"
    negative = prompt_result.get("negative") or FALLBACK_NEGATIVE_PROMPT

    prompt_id = _submit_workflow(positive, negative)
    image_bytes = _wait_for_result(prompt_id)
    return _upload_to_storage(image_bytes)