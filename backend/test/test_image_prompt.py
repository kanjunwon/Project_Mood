import hashlib
import os

os.environ["MOCK_MODE"] = "true"  # 테스트는 항상 mock 모드로 (GPU 필요 없게)

import pytest

from app.emotion_list import EMOTION_LIST
from app.services import image_prompt_service as ips
from app.services import llama_service
from app.services.image_prompt_template import EMOTION_TAGS, build_template_prompt

# 분리 전 원본 SYSTEM_PROMPT(커밋 95bdc05)의 sha256. 예시 개수/negative 옵션 기본값에서
# 프롬프트가 글자 하나라도 바뀌면 기존 동작이 바뀐 것이므로 실패해야 함.
ORIGINAL_SYSTEM_PROMPT_SHA256 = "3bb3c4ae38be02cb1beb9133e9562da480bbaf04ca84c79b177101de65258787"

FORBIDDEN_COUNT_PHRASES = ("multiple people", "multiple girls", "multiple boys", "group of people")


# ---------- 기본값 = 기존 동작 ----------

@pytest.fixture(autouse=True)
def clean_env(monkeypatch):
    for env_name, _ in ips._ENV_KEYS.values():
        monkeypatch.delenv(env_name, raising=False)


@pytest.fixture
def fake_llm(monkeypatch):
    """_generate_once를 가짜로 바꿔서 호출 인자를 기록. outputs 리스트 순서대로 응답."""
    calls = []
    outputs = []

    def fake(prompt_str, temperature, max_new_tokens=220, do_sample=True, extra_stop_strings=None, stats=None,
             **kwargs):
        calls.append({"prompt": prompt_str, "temperature": temperature, "max_new_tokens": max_new_tokens,
                      "do_sample": do_sample, "extra_stop_strings": extra_stop_strings})
        if stats is not None:
            stats.update(input_tokens=100, output_tokens=10, elapsed_sec=0.0)
        return outputs.pop(0)

    monkeypatch.setattr(llama_service, "_generate_once", fake)
    monkeypatch.setattr(llama_service, "MOCK_MODE", False)
    return calls, outputs


VALID_JSON = '{"positive": "1girl, solo, cafe, gamjeong style", "negative": "bad anatomy"}'


@pytest.fixture
def legacy_llm(monkeypatch):
    """patch 12 전 기본값(llm 모드, negative도 LLM이 출력)으로 되돌림 - 예전 llm 경로 테스트용"""
    monkeypatch.setenv("IMAGE_PROMPT_MODE", "llm")
    monkeypatch.setenv("IMAGE_PROMPT_FIXED_NEGATIVE", "false")


def test_default_system_prompt_is_identical_to_original():
    assert hashlib.sha256(ips.SYSTEM_PROMPT.encode("utf-8")).hexdigest() == ORIGINAL_SYSTEM_PROMPT_SHA256
    assert ips.build_system_prompt() == ips.SYSTEM_PROMPT


def test_default_config_patch12():
    # patch 12: 기본 hybrid 모드 + negative 고정 (나머지는 예전 값 그대로)
    assert ips.get_config() == {
        "mode": "hybrid", "max_new_tokens": 200, "do_sample": True, "temperature": 0.3,
        "num_examples": 5, "stop_on_json_close": False, "fixed_negative": True, "max_attempts": 2,
    }


def test_default_llm_call_uses_previous_arguments(fake_llm, legacy_llm):
    calls, outputs = fake_llm
    outputs.append(VALID_JSON)
    result = ips.translate_to_image_prompt("일기", ["혼자"], "편안한", "카페", "오후 2시")
    assert result == {"positive": "1girl, solo, cafe, gamjeong style", "negative": "bad anatomy"}
    assert len(calls) == 1
    assert calls[0]["temperature"] == 0.3
    assert calls[0]["max_new_tokens"] == 200
    assert calls[0]["do_sample"] is True
    assert calls[0]["extra_stop_strings"] is None
    assert ips.SYSTEM_PROMPT in calls[0]["prompt"]


def test_retry_once_then_success(fake_llm, legacy_llm):
    calls, outputs = fake_llm
    outputs.extend(["깨진 출력 {", VALID_JSON])
    report = {}
    ips.translate_to_image_prompt("일기", "혼자", "편안한", "", "", report=report)
    assert len(calls) == 2
    assert [c["is_retry"] for c in report["calls"]] == [False, True]
    assert [c["parse_ok"] for c in report["calls"]] == [False, True]
    assert report["fallback_used"] is False


def test_two_failures_fall_back(fake_llm, legacy_llm):
    calls, outputs = fake_llm
    outputs.extend(["no json", '{"positive": "x"'])
    result = ips.translate_to_image_prompt("일기", "혼자", "슬픈", "", "")
    assert len(calls) == 2  # 최대 2번까지만
    assert result == ips._fallback_prompt("슬픈")


def test_mock_mode_llm_returns_fallback_without_calling_llm(monkeypatch, legacy_llm):
    monkeypatch.setattr(llama_service, "MOCK_MODE", True)
    monkeypatch.setattr(llama_service, "_generate_once", lambda *a, **k: pytest.fail("LLM 호출되면 안 됨"))
    assert ips.translate_to_image_prompt("일기", "혼자", "기쁜", "", "") == ips._fallback_prompt("기쁜")


# ---------- 환경변수 설정 ----------

def test_env_overrides(monkeypatch, fake_llm, legacy_llm):
    calls, outputs = fake_llm
    monkeypatch.setenv("IMAGE_PROMPT_MAX_NEW_TOKENS", "120")
    monkeypatch.setenv("IMAGE_PROMPT_DO_SAMPLE", "false")
    monkeypatch.setenv("IMAGE_PROMPT_TEMPERATURE", "0.1")
    monkeypatch.setenv("IMAGE_PROMPT_NUM_EXAMPLES", "2")
    monkeypatch.setenv("IMAGE_PROMPT_STOP_ON_JSON_CLOSE", "true")
    outputs.append(VALID_JSON)
    ips.translate_to_image_prompt("일기", "혼자", "편안한", "", "")
    call = calls[0]
    assert call["max_new_tokens"] == 120
    assert call["do_sample"] is False
    assert call["temperature"] == 0.1
    assert call["extra_stop_strings"] == ips.JSON_CLOSE_STOP_STRINGS
    assert "[예시 2]" in call["prompt"] and "[예시 3]" not in call["prompt"]


def test_overrides_take_precedence_over_env(monkeypatch):
    monkeypatch.setenv("IMAGE_PROMPT_MAX_NEW_TOKENS", "120")
    assert ips.get_config({"max_new_tokens": 80})["max_new_tokens"] == 80


def test_invalid_mode_and_unknown_key_raise(monkeypatch):
    with pytest.raises(ValueError):
        ips.get_config({"nope": 1})
    monkeypatch.setenv("IMAGE_PROMPT_MODE", "gpt")
    with pytest.raises(ValueError):
        ips.get_config()


def test_example_reduction_keeps_priority_order():
    two = ips.build_system_prompt(2)
    assert "골골송" in two and "노래방" in two  # 1인 + 친구들(인원 추정)
    assert "셀프 세차장" not in two and "칠순" not in two
    three = ips.build_system_prompt(3)
    assert "롤러코스터" in three


def test_fixed_negative_prompt_and_parse(fake_llm, legacy_llm):
    prompt = ips.build_system_prompt(5, fixed_negative=True)
    assert '"negative"' not in prompt
    calls, outputs = fake_llm
    outputs.append('{"positive": "1girl, solo, gamjeong style"}')
    result = ips.translate_to_image_prompt("일기", "혼자", "편안한", "", "", config={"fixed_negative": True})
    assert result == {"positive": "1girl, solo, gamjeong style", "negative": ips.FALLBACK_NEGATIVE}


def test_fixed_negative_equals_system_prompt_negative_exactly(fake_llm, legacy_llm):
    # SYSTEM_PROMPT가 원본(커밋 95bdc05)과 같다는 건 해시 테스트가 보장하므로,
    # 여기서는 그 프롬프트 "텍스트"에서 negative를 직접 뽑아 fixed_negative 경로의 실제 반환값과 비교함
    import re
    assert hashlib.sha256(ips.SYSTEM_PROMPT.encode("utf-8")).hexdigest() == ORIGINAL_SYSTEM_PROMPT_SHA256
    negatives = re.findall(r'"negative": "([^"]*)"', ips.SYSTEM_PROMPT)
    assert len(negatives) == 6  # 출력 형식 1개 + 예시 5개
    assert len(set(negatives)) == 1  # 프롬프트 안의 negative 6개가 전부 동일

    calls, outputs = fake_llm
    outputs.append('{"positive": "1girl, solo, gamjeong style"}')
    result = ips.translate_to_image_prompt("일기", "혼자", "편안한", "", "", config={"fixed_negative": True})
    assert result["negative"] == negatives[0]
    # template 모드도 같은 negative를 씀
    assert build_template_prompt("일기", "혼자", "편안한", "", "")["negative"] == negatives[0]
    # v3 인원수 초과 방지 항목 포함 확인
    for item in ("extra people", "extra person", "additional people", "crowd", "too many people",
                 "duplicate character", "clone", "multiple views", "split screen"):
        assert item in result["negative"]


# ---------- template 모드 ----------

def test_template_mode_never_calls_llm(monkeypatch):
    monkeypatch.setattr(llama_service, "MOCK_MODE", False)
    monkeypatch.setattr(llama_service, "_generate_once", lambda *a, **k: pytest.fail("LLM 호출되면 안 됨"))
    monkeypatch.setenv("IMAGE_PROMPT_MODE", "template")
    result = ips.translate_to_image_prompt("카페에서 공부했다", "혼자", "뿌듯한", "카페", "오후 2시")
    assert result["positive"].startswith("1girl, solo")


def _check_common_rules(result):
    pos = result["positive"]
    assert pos.endswith("gamjeong style")
    assert result["negative"] == ips.FALLBACK_NEGATIVE
    assert "extra people" in result["negative"] and "too many people" in result["negative"]
    for phrase in FORBIDDEN_COUNT_PHRASES:
        assert phrase not in pos
    first = pos.split(", ")[0]
    assert first[0].isdigit() and ("girl" in first or "boy" in first)  # 인원 태그가 맨 앞


def test_template_solo_female_default():
    r = build_template_prompt("퇴근하고 집에 왔다.", "혼자", "피곤한", "집", "10월 4일 토요일 오후 9시")
    _check_common_rules(r)
    assert r["positive"].startswith("1girl, solo, young adult woman")
    assert "tired expression" in r["positive"] and "dim lighting" in r["positive"]
    assert "living room" in r["positive"] and "night" in r["positive"]


def test_template_solo_male_from_gender():
    r = build_template_prompt("산책했다.", ["혼자"], "상쾌한", "동네", "오전 8시", gender="남성")
    _check_common_rules(r)
    assert r["positive"].startswith("1boy, solo, young adult man")
    assert "morning" in r["positive"]
    assert "mountain" not in r["positive"]  # "산책"의 "산"이 장소로 잡히면 안 됨
    assert "reading book" not in r["positive"]  # "산책"의 "책"이 행동으로 잡히면 안 됨


def test_template_couple_exact_tags():
    r = build_template_prompt("데이트했다.", "연인", "설레는", "카페", "")
    _check_common_rules(r)
    assert r["positive"].startswith("1girl, young adult woman, 1boy, young adult man, couple")


def test_template_family_includes_parents_and_dedupes():
    r = build_template_prompt("본가에 갔다.", "가족,엄마,아빠", "편안한", "본가", "", gender="남성")
    _check_common_rules(r)
    pos = r["positive"]
    assert pos.startswith("1girl, 2boys")  # 본인(남) + 엄마 + 아빠 = 3명, 엄마/아빠 중복 없음
    assert "mature female, mother" in pos and "mature male, father" in pos
    assert "young adult man" in pos
    assert pos.count("mother") == 1


def test_template_caps_at_six_people():
    who = "가족,할머니,할아버지,친구,여성친구,남성친구,연인"
    r = build_template_prompt("다 같이 모였다.", who, "행복한", "식당", "")
    _check_common_rules(r)
    counts = r["positive"].split(", gamjeong")[0]
    girls = boys = 0
    for tag in counts.split(", "):
        if tag[:1].isdigit():
            n = int(tag[0])
            if "girl" in tag:
                girls = n
            elif "boy" in tag:
                boys = n
    assert girls + boys == 6
    assert "flat color, cel shading, line art, illustration" in r["positive"]  # 4명 이상


def test_template_crowded_place_limits_foreground():
    r = build_template_prompt("친구들이랑 놀이공원 갔다.", "친구,여성친구,남성친구,가족", "신나는", "놀이공원", "")
    _check_common_rules(r)
    pos = r["positive"]
    n_people = sum(int(t[0]) for t in pos.split(", ") if t[:1].isdigit() and ("girl" in t or "boy" in t))
    assert n_people <= 3
    assert "blurred crowd silhouettes in background" in pos and "bokeh" in pos
    assert "crowd," not in pos.replace("blurred crowd silhouettes", "")


def test_template_friends_group_hint_from_diary():
    one = build_template_prompt("걔랑 밥 먹었다.", "친구", "즐거운", "", "")
    many = build_template_prompt("친구들이랑 다 같이 밥 먹었다.", "친구", "즐거운", "", "")
    assert one["positive"].startswith("2girls")
    assert many["positive"].startswith("2girls, 1boy")


def test_template_pets_do_not_count_as_people():
    r = build_template_prompt("고양이가 반겨줬다.", "반려동물,고양이", "편안한", "자취방", "")
    _check_common_rules(r)
    assert r["positive"].startswith("1girl, solo")
    assert "cat" in r["positive"]


def test_template_unknown_inputs_are_omitted():
    r = build_template_prompt("그냥 그랬다.", "외계인", "알수없는감정", "어딘가", "언젠가")
    _check_common_rules(r)
    assert r["positive"] == "1girl, solo, young adult woman, calm expression, soft lighting, gamjeong style"


def test_template_has_no_duplicate_tags():
    r = build_template_prompt("생일이라 케이크에 초 꽂고 노래 불렀다.", "친구,여성친구,남성친구", "신나는", "친구네 집", "")
    tags = r["positive"].split(", ")
    assert len(tags) == len(set(tags))
    assert "birthday cake" in tags


def test_all_24_emotions_mapped():
    assert set(EMOTION_TAGS) == set(EMOTION_LIST)
    assert len(EMOTION_TAGS) == 24


# ---------- 측정용 디버그 엔드포인트 ----------

def test_debug_endpoints_not_registered_by_default():
    from app.main import app
    assert not any(getattr(r, "path", "").startswith("/debug") for r in app.routes)


def test_debug_paths_return_404_when_not_enabled():
    from fastapi.testclient import TestClient
    from app.main import app
    from app.services.auth_service import create_access_token

    assert os.environ.get("ENABLE_DEBUG_ENDPOINTS", "false").lower() != "true"
    client = TestClient(app)
    headers = {"Authorization": f"Bearer {create_access_token(user_id=1)}"}
    body = {"diary_text": "x", "overrides": {"mode": "template"}}
    assert client.post("/debug/image-prompt", json=body, headers=headers).status_code == 404
    assert client.get("/debug/last-pipeline-timings", headers=headers).status_code == 404


def test_debug_endpoint_template_and_mock_never_load_model(monkeypatch):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from app.models import llama_loader
    from app.routers import debug
    from app.services.auth_service import create_access_token

    monkeypatch.setattr(llama_service, "MOCK_MODE", True)
    monkeypatch.setattr(llama_loader, "get_model_and_tokenizer", lambda: pytest.fail("모델 로딩되면 안 됨"))
    app = FastAPI()
    app.include_router(debug.router)
    client = TestClient(app)
    headers = {"Authorization": f"Bearer {create_access_token(user_id=1)}"}
    body = {"diary_text": "카페에서 공부했다", "who": "혼자", "emotion": "뿌듯한", "where": "카페", "when": "오후 2시"}

    r = client.post("/debug/image-prompt", json={**body, "overrides": {"mode": "template"}}, headers=headers)
    assert r.status_code == 200
    assert r.json()["positive"].startswith("1girl, solo")

    r = client.post("/debug/image-prompt", json={**body, "overrides": {"mode": "llm"}}, headers=headers)
    assert r.status_code == 200
    assert r.json()["fallback_used"] is True

    r = client.post("/debug/image-prompt", json={**body, "overrides": {"nope": 1}}, headers=headers)
    assert r.status_code == 400
    assert client.post("/debug/image-prompt", json=body).status_code in (401, 403)


# ---------- hybrid 모드 (patch 12) ----------

def test_scene_tag_cleaning():
    assert ips.clean_scene_tag("Coffee_Cup") == "coffee cup"
    assert ips.clean_scene_tag("cafe") == "cafe"
    for bad in ("October 16th", "10:13 PM", "information processing technician test",
                "negative emotions", "gamjeong style", "1girl", "", None, 3, "카페"):
        assert ips.clean_scene_tag(bad) is None, bad


def test_parse_scene_filters_and_limits():
    raw = '잡담 {"place": "Exam Hall", "action": "taking exam", "objects": ["desk", "October 16th", "pencil", "eraser", "ruler"]} 끝'
    assert ips.parse_scene(raw) == ["exam hall", "taking exam", "desk"]  # patch 13: objects는 앞 2개 중 통과한 것만
    assert ips.parse_scene("no json") is None
    assert ips.parse_scene('{"place": "Yonsinnae 10th street"}') is None


def test_hybrid_merges_template_and_scene(fake_llm):
    calls, outputs = fake_llm
    outputs.append('{"place": "cafe", "action": "studying", "objects": ["notebook", "coffee cup"]}')
    report = {}
    r = ips.translate_to_image_prompt("오늘은 카페에서 공부를 했다.", "혼자", "뿌듯한", "동네 카페",
                                      "10월 25일 토요일 오후 2시", what="카페에서 공부", why="집중이 잘 돼서",
                                      report=report)
    pos = r["positive"]
    assert pos.startswith("1girl, solo") and pos.endswith("gamjeong style")
    assert "proud smile" in pos and "daytime" in pos           # template: 감정/시간
    assert "notebook" in pos and "studying" in pos              # LLM 장면
    assert len(pos.split(", ")) == len(set(pos.split(", ")))    # 중복 없음
    assert len(calls) == 1 and calls[0]["do_sample"] is False and calls[0]["max_new_tokens"] == ips.SCENE_MAX_NEW_TOKENS
    assert '무엇을="카페에서 공부"' in calls[0]["prompt"] and "오늘은 카페에서" not in calls[0]["prompt"]  # 일기 본문은 안 넣음
    assert report["scene"] == ["cafe", "studying", "notebook", "coffee cup"] and report["fallback_used"] is False


def test_hybrid_falls_back_to_template_when_scene_fails(fake_llm):
    calls, outputs = fake_llm
    outputs.append("죄송합니다")
    r = ips.translate_to_image_prompt("카페에서 공부했다", "혼자", "뿌듯한", "카페", "오후 2시", what="공부")
    assert r == build_template_prompt("공부  카페에서 공부했다", "혼자", "뿌듯한", "카페", "오후 2시")


def test_hybrid_mock_mode_never_calls_llm(monkeypatch):
    monkeypatch.setattr(llama_service, "MOCK_MODE", True)
    monkeypatch.setattr(llama_service, "_generate_once", lambda *a, **k: pytest.fail("LLM 호출되면 안 됨"))
    r = ips.translate_to_image_prompt("카페에서 공부했다", "혼자", "뿌듯한", "카페", "오후 2시", what="공부")
    assert r["positive"].startswith("1girl, solo")



# ---------- patch 13: 템플릿 장소/시간 ----------

def test_restaurant_names_with_jip_are_not_home():
    from app.services.image_prompt_template import _find_place
    assert _find_place("고깃집", "")[1] == "restaurant, yakiniku, grill, indoors"
    assert _find_place("동네 중국집", "")[1] == "restaurant, chinese food, indoors"
    assert _find_place("곱창집", "")[1] == "restaurant, indoors"       # 사전에 없는 'OO집'은 식당
    assert _find_place("우리 집", "")[1] == "home, living room, indoors"
    assert _find_place("집", "")[1] == "home, living room, indoors"
    assert _find_place("친구집", "")[1] == "friend's house, living room, indoors"
    assert _find_place("할머니집", "")[1] == "home, living room, indoors"


def test_indoor_evening_has_no_sunset():
    r = build_template_prompt("운동했다.", "혼자", "신나는", "헬스장", "10월 30일 금요일 오후 6시", gender="남성")
    assert "evening" in r["positive"] and "sunset" not in r["positive"]
    r = build_template_prompt("산책했다.", "혼자", "상쾌한", "공원", "10월 30일 금요일 오후 6시", gender="남성")
    assert "sunset" in r["positive"]


def test_scene_examples_use_danbooru_tags():
    from app.services import danbooru_tags as dt
    for _, ex in ips._SCENE_EXAMPLES:
        for tag in [ex["place"], ex["action"], *ex["objects"]]:
            if tag in dt.KEEP_TAGS:
                continue
            assert dt.canonical(tag)[1] >= 100, tag
        assert len(ex["objects"]) <= ips.MAX_SCENE_OBJECTS



def test_scene_objects_drop_people_and_lighting():
    raw = '{"place": "classroom", "action": "listening", "objects": ["teacher", "whiteboard"]}'
    assert ips.parse_scene(raw) == ["classroom", "listening", "whiteboard"]  # patch 14: 사람 태그는 소품에서 뺌
    assert ips.clean_scene_tag("sunlight") is None and ips.clean_scene_tag("students") is None
