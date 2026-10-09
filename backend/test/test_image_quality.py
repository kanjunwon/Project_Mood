import json
import os

os.environ["MOCK_MODE"] = "true"  # 테스트는 항상 mock 모드로 (GPU 필요 없게)

from app.services import sd3_service
from app.services.sd3_service import (
    IMAGE_NEGATIVE_BASE,
    QUALITY_PREFIX,
    ensure_male_group,
    sanitize_image_tags,
)


# ---------- sanitize_image_tags ----------

def test_neon_tag_replaced_with_colorful_lighting():
    out, changes = sanitize_image_tags("3boys, karaoke room, neon lights, singing")
    assert "neon" not in out
    assert "colorful lighting" in out.split(", ")
    assert any("neon lights" in c for c in changes)


def test_neon_sign_also_replaced_not_dropped_as_sign():
    out, _ = sanitize_image_tags("2boys, neon sign, bar")
    assert out == "2boys, colorful lighting, bar"


def test_text_prone_tags_removed():
    out, changes = sanitize_image_tags("1boy, solo, sign, signboard, text, letters, logo, lyrics, poster, cafe")
    assert out == "1boy, solo, cafe"
    assert len(changes) == 7


def test_similar_words_are_not_removed():
    # "design", "signature pose" 같은 단어 일부에 sign이 들어있어도 지우면 안 됨 (단어 단위로만 매칭)
    out, changes = sanitize_image_tags("1girl, design, signature pose, writing in diary, cafe")
    assert out == "1girl, design, signature pose, writing in diary, cafe"
    assert changes == []


def test_karaoke_place_tags_unified():
    for raw in ("coin karaoke room", "karaoke booth", "coin karaoke", "karaoke box"):
        out, _ = sanitize_image_tags(f"3boys, {raw}, singing")
        assert out == "3boys, karaoke room, singing", raw


def test_duplicate_and_quality_tags_removed_case_insensitive():
    out, _ = sanitize_image_tags("masterpiece, 3boys, Karaoke Room, karaoke room, best quality, singing")
    assert out == "3boys, Karaoke Room, singing"


def test_weighted_neon_tag_is_replaced():
    out, _ = sanitize_image_tags("1boy, (neon sign:1.2), street")
    assert out == "1boy, colorful lighting, street"


def test_empty_input():
    assert sanitize_image_tags("") == ("", [])


# ---------- ensure_male_group ----------

def test_male_group_gets_weight_male_focus_and_girl_negative():
    pos, neg = ensure_male_group("3boys, young adults, friends, karaoke room", IMAGE_NEGATIVE_BASE, "남성")
    tags = pos.split(", ")
    assert tags[0] == "(3boys:1.2)"
    assert tags[1] == "male focus"
    assert neg.startswith(IMAGE_NEGATIVE_BASE)
    assert "girl, 1girl, 2girls, 3girls" in neg


def test_male_group_not_applied_for_female_account():
    pos, neg = ensure_male_group("3boys, friends", IMAGE_NEGATIVE_BASE, "여성")
    assert (pos, neg) == ("3boys, friends", IMAGE_NEGATIVE_BASE)


def test_male_group_not_applied_when_gender_unknown():
    pos, neg = ensure_male_group("3boys, friends", IMAGE_NEGATIVE_BASE, None)
    assert (pos, neg) == ("3boys, friends", IMAGE_NEGATIVE_BASE)


def test_male_group_not_applied_to_mixed_or_family_or_single():
    for prompt in (
        "2girls, 1boy, friends",                      # 인원 태그 둘 -> 혼성
        "3girls, friends",                            # 여성 그룹
        "1boy, solo, cafe",                           # 혼자는 apply_gender 담당
        "2boys, mature female, mother, car wash",    # 엄마 포함
        "3boys, sister, party",                       # 누나 포함
        "friends, karaoke room",                      # 인원 태그 없음
    ):
        pos, neg = ensure_male_group(prompt, IMAGE_NEGATIVE_BASE, "남성")
        assert (pos, neg) == (prompt, IMAGE_NEGATIVE_BASE), prompt


# ---------- generate_diary_image 통합 (ComfyUI/Supabase는 가짜로) ----------

def _run_generate(monkeypatch, llm_positive, llm_negative, gender, who):
    captured = {}
    monkeypatch.setattr(
        sd3_service, "translate_to_image_prompt",
        lambda **kw: {"positive": llm_positive, "negative": llm_negative},
    )
    monkeypatch.setattr(sd3_service, "_submit_workflow",
                        lambda p, n: captured.update(positive=p, negative=n) or "pid")
    monkeypatch.setattr(sd3_service, "_wait_for_result", lambda pid: b"png")
    monkeypatch.setattr(sd3_service, "_upload_to_storage", lambda b: "http://img")
    url = sd3_service.generate_diary_image(
        diary_text="일기", top_emotion="신나는", who=who, where="코인노래방", when="오후 5시",
        glasses="horn_rimmed", bangs=False, hair_length="short", hair_color="검정", gender=gender,
    )
    assert url == "http://img"
    return captured


def test_generate_uses_quality_prefix_clean_tags_and_short_negative(monkeypatch):
    llm_neg = "bad anatomy, " * 30  # LLM이 길게 줘도 쓰지 않아야 함
    cap = _run_generate(
        monkeypatch,
        "3boys, young adults, friends, coin karaoke room, neon lights, loudspeakers, gamjeong style",
        llm_neg, "남성", ["남성친구", "친구 3명"],
    )
    pos = cap["positive"]
    assert pos.startswith(QUALITY_PREFIX + ", ")
    assert "neon" not in pos and "coin karaoke" not in pos
    assert "karaoke room" in pos and "colorful lighting" in pos
    assert "(4boys:1.2), male focus" in pos  # 나 + 친구 3명
    assert "3boys" not in pos
    # 아바타 태그는 맨 끝
    assert pos.endswith("horn-rimmed glasses, no bangs, short hair, black hair")
    neg = cap["negative"]
    assert neg.startswith(IMAGE_NEGATIVE_BASE)
    assert "girl, 1girl, 2girls, 3girls" in neg
    assert "bad anatomy, bad anatomy" not in neg  # LLM 긴 negative 미사용


def test_generate_female_account_friend_is_two_girls(monkeypatch):
    cap = _run_generate(monkeypatch, "3boys, friends, karaoke room", "x", "여성", "친구")
    assert "(2girls:1.2), female focus" in cap["positive"]
    assert "3boys" not in cap["positive"]
    assert cap["negative"].startswith(IMAGE_NEGATIVE_BASE)
    assert "boy, 1boy, 2boys, 3boys" in cap["negative"]


def test_generate_undecidable_who_falls_back_to_llm_tags(monkeypatch):
    cap = _run_generate(monkeypatch, "3boys, friends, karaoke room", "x", "남성", "가족")
    assert "(3boys:1.2), male focus" in cap["positive"]  # 기존 ensure_male_group


def test_generate_solo_male_keeps_existing_gender_logic(monkeypatch):
    cap = _run_generate(monkeypatch, "1girl, solo, cafe, coffee, gamjeong style", "x", "남성", ["혼자"])
    pos = cap["positive"]
    assert "(1boy:1.3), (male focus:1.2)" in pos
    assert "1girl" not in pos.replace("(1girl", "")  # 1girl -> 1boy 로 바뀜
    assert "(1girl:1.3)" in cap["negative"]  # 기존 남성 보정 negative 유지


# ---------- 워크플로우 JSON (Clip Skip 2 / LoRA 0.8 / 샘플러) ----------

def _workflow():
    path = os.path.join(os.path.dirname(sd3_service.__file__), "..", "comfyui_workflow.json")
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def test_workflow_clip_skip_2_wired_to_both_text_encoders():
    w = _workflow()
    node = w["12"]
    assert node["class_type"] == "CLIPSetLastLayer"
    assert node["inputs"]["stop_at_clip_layer"] == -2
    assert node["inputs"]["clip"] == ["3", 1]  # LoRA의 CLIP 출력에서 받음
    assert w["4"]["inputs"]["clip"] == ["12", 0]
    assert w["5"]["inputs"]["clip"] == ["12", 0]


def test_workflow_lora_and_sampler_settings():
    w = _workflow()
    assert w["3"]["inputs"]["strength_model"] == 0.8
    assert w["3"]["inputs"]["strength_clip"] == 0.8
    ks = w["8"]["inputs"]
    assert ks["sampler_name"] == "euler_ancestral"
    assert ks["cfg"] == 5.5
    assert ks["steps"] == 26


def test_workflow_all_references_point_to_existing_nodes():
    w = _workflow()
    for node_id, node in w.items():
        for key, value in node["inputs"].items():
            if isinstance(value, list) and len(value) == 2 and isinstance(value[0], str):
                assert value[0] in w, f"노드 {node_id}.{key} 가 없는 노드 {value[0]} 를 참조"


def test_workflow_node_ids_used_by_service_unchanged():
    w = _workflow()
    assert w[sd3_service.POSITIVE_PROMPT_NODE_ID]["class_type"] == "CLIPTextEncode"
    assert w[sd3_service.NEGATIVE_PROMPT_NODE_ID]["class_type"] == "CLIPTextEncode"
    assert w[sd3_service.SEED_NODE_ID]["class_type"] == "KSampler"
