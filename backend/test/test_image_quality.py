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
    assert "karaoke room" in pos
    assert "colorful lighting" not in pos  # patch 14: 조명 태그는 화풍을 흐려서 뺌 (neon -> colorful lighting -> 제거)
    assert "(4boys:1.2), male focus" in pos  # 나 + 친구 3명
    assert "3boys" not in pos
    # 아바타 태그는 맨 끝 (patch 13: 뿔테/앞머리 없음을 Danbooru 정식 태그로)
    assert pos.endswith("black-framed eyewear, forehead, short hair, black hair")
    assert "upper body" in pos  # patch 13: 여러 명이면 구도 태그 upper body
    neg = cap["negative"]
    assert neg.startswith(IMAGE_NEGATIVE_BASE)
    assert "(girl:1.3), (1girl:1.3), (2girls:1.2), (3girls:1.2)" in neg
    assert "bad anatomy, bad anatomy" not in neg  # LLM 긴 negative 미사용


def test_generate_female_account_friend_is_two_girls(monkeypatch):
    cap = _run_generate(monkeypatch, "3boys, friends, karaoke room", "x", "여성", "친구")
    assert "(2girls:1.2), female focus" in cap["positive"]
    assert "3boys" not in cap["positive"]
    assert cap["negative"].startswith(IMAGE_NEGATIVE_BASE)
    assert "(boy:1.3), (1boy:1.3), (2boys:1.2), (3boys:1.2)" in cap["negative"]


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



# ---------- patch 13: Danbooru 태그 정리 / 구도 / 나이 ----------

from app.services import danbooru_tags as dt


def test_danbooru_filter_fixes_gym_log_tags():
    # 2026-10-30 헬스장 로그의 장면 태그
    out, dropped, changed = dt.filter_tags(
        "smile, open mouth, excited expression, energetic, warm lighting, exercising, sportswear, gym, indoors, "
        "evening, working out, weight bench, dumbbells")
    assert out == "smile, open mouth, excited, exercising, sportswear, gym, indoors, evening, dumbbell"
    assert "weight bench" in dropped  # 게시물 34건이라 데이터 파일(100건 이상)에 없음: 모델이 거의 모르는 태그
    assert "dumbbells->dumbbell" in changed and "working out->exercising" in changed


def test_danbooru_filter_keeps_weights_keep_tags_and_escapes_parens(monkeypatch):
    out, _, _ = dt.filter_tags("(1boy:1.3), karaoke room, colorful lighting, mother, bar (place), grill house")
    assert out == "(1boy:1.3), karaoke room, colorful lighting, mother, bar \\(place\\), restaurant, grill"
    monkeypatch.setenv("IMAGE_TAG_MIN_POSTS", "2000")
    out, dropped, _ = dt.filter_tags("gym, dumbbell")
    assert out == "gym" and dropped == ["dumbbell(1893건)"]


def test_danbooru_filter_can_be_turned_off(monkeypatch):
    monkeypatch.setenv("IMAGE_TAG_FILTER", "false")
    cap = _run_generate(monkeypatch, "1boy, solo, gym, weight bench, dumbbells", "x", "남성", ["혼자"])
    assert "weight bench" in cap["positive"] and "dumbbells" in cap["positive"]


def test_generate_solo_gym_prompt_patch13(monkeypatch):
    cap = _run_generate(monkeypatch, "1boy, solo, young adult man, smile, exercising, gym, indoors, working out, "
                        "weight bench, dumbbells, gamjeong style", "x", "남성", ["혼자"])
    pos, neg = cap["positive"], cap["negative"]
    assert "(1boy:1.3), (male focus:1.2), solo, black-framed eyewear, forehead, short hair, black hair, cowboy shot" in pos
    assert "weight bench" not in pos and "dumbbell" in pos and "working out" not in pos
    assert "child, aged down" in neg and "multiple views, comic" in neg


def test_composition_tag_rules(monkeypatch):
    assert sd3_service._composition_tag("eating, noodles, bowl", solo=True) == "upper body"
    assert sd3_service._composition_tag("walking, park", solo=True) == "full body"
    assert sd3_service._composition_tag("gym, exercising", solo=True) == "cowboy shot"
    assert sd3_service._composition_tag("gym, exercising", solo=False) == "upper body"
    assert sd3_service._composition_tag("full body, park", solo=True) is None  # 이미 있으면 안 붙임
    monkeypatch.setenv("IMAGE_COMPOSITION_TAG", "false")
    assert sd3_service._composition_tag("gym", solo=True) is None


def test_age_negative_skipped_when_child_is_in_picture():
    assert sd3_service._needs_age_negative(["혼자"]) is True
    assert sd3_service._needs_age_negative("친구,3명") is True
    assert sd3_service._needs_age_negative(["자녀"]) is False
    assert sd3_service._needs_age_negative("엄마,아들") is False


def test_avatar_tags_are_danbooru_tags():
    tags = sd3_service._avatar_tags("round", False, "long", "갈색")
    assert tags == "round eyewear, forehead, long hair, brown hair"
    for t in tags.split(", "):
        assert dt.canonical(t)[0] == t, t



def test_indoor_scene_drops_wind_and_sunset():
    out, dropped, _ = dt.filter_tags("smile, gentle breeze, restaurant, indoors, sunset, night")
    assert out == "smile, restaurant, indoors, night"
    assert "wind(실내)" in dropped and "sunset(실내)" in dropped
    assert dt.filter_tags("smile, gentle breeze, park, outdoors")[0] == "smile, wind, park, outdoors"


def test_quality_prefix_env_override(monkeypatch):
    monkeypatch.setenv("IMAGE_QUALITY_PREFIX", "masterpiece, best quality, absurdres")
    cap = _run_generate(monkeypatch, "1boy, solo, cafe", "x", "남성", ["혼자"])
    assert cap["positive"].startswith("masterpiece, best quality, absurdres, gamjeong style")
    assert "amazing quality" not in cap["positive"]



# ---------- patch 14: 화풍 비교 테스트(C 조합) 반영 ----------

SUBWAY_LLM = ("1boy, solo, young adult man, tired expression, sleepy, slouching, dim lighting, riding, train, book, "
              "subway, subway train, indoors, morning, sunlight, gamjeong style")


def test_generate_matches_style_test_c(monkeypatch):
    # 2026-10-30 ComfyUI 시드 고정 비교에서 화풍대로 나온 C 조합: 짧은 품질 태그 + 조명/시간 태그 없음
    cap = _run_generate(monkeypatch, SUBWAY_LLM, "x", "남성", ["혼자"])
    assert cap["positive"] == (
        "masterpiece, best quality, absurdres, gamjeong style, illustration, flat color, soft colors, warm colors, "
        "(1boy:1.3), (male focus:1.2), solo, black-framed eyewear, forehead, short hair, black hair, cowboy shot, "
        "half-closed eyes, sleepy, slouching, sitting, train, book, "
        "subway, train interior, indoors")


def test_light_time_tags_dropped_but_outdoor_night_kept(monkeypatch):
    assert sd3_service.drop_light_time_tags("smile, dim lighting, cafe, indoors, morning, sunlight") == (
        "smile, cafe, indoors", ["dim lighting", "morning", "sunlight"])
    assert sd3_service.drop_light_time_tags("walking, river, park, outdoors, night, sunset")[0] == (
        "walking, river, park, outdoors, night")
    assert sd3_service.drop_light_time_tags("karaoke room, indoors, night")[0] == "karaoke room, indoors"
    monkeypatch.setenv("IMAGE_LIGHT_TIME_TAGS", "true")
    assert sd3_service.drop_light_time_tags("smile, dim lighting, morning")[0] == "smile, dim lighting, morning"


def test_old_quality_prefix_can_be_restored(monkeypatch):
    old = "masterpiece, best quality, amazing quality, very aesthetic, absurdres"
    monkeypatch.setenv("IMAGE_QUALITY_PREFIX", old)
    cap = _run_generate(monkeypatch, "1boy, solo, cafe, very aesthetic", "x", "남성", ["혼자"])
    assert cap["positive"].startswith(old + ", gamjeong style")
    assert cap["positive"].count("very aesthetic") == 1  # 본문에 LLM이 넣은 건 지워짐


def test_riding_becomes_sitting_unless_bicycle():
    assert dt.filter_tags("riding, train, subway")[0] == "sitting, train, subway"
    assert dt.filter_tags("riding, bicycle, park")[0] == "riding bicycle, bicycle, park"



def _run_generate_avatar(monkeypatch, llm_positive, gender, who, hair_length="long", bangs=True):
    captured = {}
    monkeypatch.setattr(sd3_service, "translate_to_image_prompt", lambda **kw: {"positive": llm_positive, "negative": "x"})
    monkeypatch.setattr(sd3_service, "_submit_workflow", lambda p, n: captured.update(positive=p, negative=n) or "pid")
    monkeypatch.setattr(sd3_service, "_wait_for_result", lambda pid: b"png")
    monkeypatch.setattr(sd3_service, "_upload_to_storage", lambda b: "http://img")
    sd3_service.generate_diary_image(diary_text="일기", top_emotion="즐거운", who=who, where="", when="",
                                     glasses="none", bangs=bangs, hair_length=hair_length, hair_color="갈색", gender=gender)
    return captured["positive"]


def test_male_group_drops_long_hair_and_bangs(monkeypatch):
    # 2026-10-30 로그: 남자 3명(나+친구 2명)인데 아바타 'blunt bangs, long hair'가 모두에게 퍼져 여자 1명이 나옴
    pos = _run_generate_avatar(monkeypatch, "2boys, young adults, friends, laughing, driving, car, park, outdoors",
                               "남성", "친구,2명")
    assert "(3boys:1.2), male focus, multiple boys" in pos
    assert "long hair" not in pos and "blunt bangs" not in pos
    assert pos.endswith("brown hair")  # 머리색은 남김


def test_solo_male_and_female_group_keep_long_hair(monkeypatch):
    pos = _run_generate_avatar(monkeypatch, "1boy, solo, cafe", "남성", ["혼자"])
    assert "blunt bangs, long hair, brown hair" in pos  # 혼자면 (1boy:1.3) 바로 뒤라 괜찮음
    pos = _run_generate_avatar(monkeypatch, "2girls, friends, cafe", "여성", "친구,1명")
    assert "(2girls:1.2), female focus, multiple girls" in pos and "long hair" in pos
