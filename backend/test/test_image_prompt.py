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

    def fake(prompt_str, temperature, max_new_tokens=220, do_sample=True, extra_stop_strings=None, stats=None):
        calls.append({"prompt": prompt_str, "temperature": temperature, "max_new_tokens": max_new_tokens,
                      "do_sample": do_sample, "extra_stop_strings": extra_stop_strings})
        if stats is not None:
            stats.update(input_tokens=100, output_tokens=10, elapsed_sec=0.0)
        return outputs.pop(0)

    monkeypatch.setattr(llama_service, "_generate_once", fake)
    monkeypatch.setattr(llama_service, "MOCK_MODE", False)
    return calls, outputs


VALID_JSON = '{"positive": "1girl, solo, cafe, gamjeong style", "negative": "bad anatomy"}'


def test_default_system_prompt_is_identical_to_original():
    assert hashlib.sha256(ips.SYSTEM_PROMPT.encode("utf-8")).hexdigest() == ORIGINAL_SYSTEM_PROMPT_SHA256
    assert ips.build_system_prompt() == ips.SYSTEM_PROMPT


def test_default_config_matches_previous_hardcoded_values():
    assert ips.get_config() == {
        "mode": "llm", "max_new_tokens": 200, "do_sample": True, "temperature": 0.3,
        "num_examples": 5, "stop_on_json_close": False, "fixed_negative": False, "max_attempts": 2,
    }


def test_default_llm_call_uses_previous_arguments(fake_llm):
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


def test_retry_once_then_success(fake_llm):
    calls, outputs = fake_llm
    outputs.extend(["깨진 출력 {", VALID_JSON])
    report = {}
    ips.translate_to_image_prompt("일기", "혼자", "편안한", "", "", report=report)
    assert len(calls) == 2
    assert [c["is_retry"] for c in report["calls"]] == [False, True]
    assert [c["parse_ok"] for c in report["calls"]] == [False, True]
    assert report["fallback_used"] is False


def test_two_failures_fall_back(fake_llm):
    calls, outputs = fake_llm
    outputs.extend(["no json", '{"positive": "x"'])
    result = ips.translate_to_image_prompt("일기", "혼자", "슬픈", "", "")
    assert len(calls) == 2  # 최대 2번까지만
    assert result == ips._fallback_prompt("슬픈")


def test_mock_mode_llm_returns_fallback_without_calling_llm(monkeypatch):
    monkeypatch.setattr(llama_service, "MOCK_MODE", True)
    monkeypatch.setattr(llama_service, "_generate_once", lambda *a, **k: pytest.fail("LLM 호출되면 안 됨"))
    assert ips.translate_to_image_prompt("일기", "혼자", "기쁜", "", "") == ips._fallback_prompt("기쁜")


# ---------- 환경변수 설정 ----------

def test_env_overrides(monkeypatch, fake_llm):
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


def test_fixed_negative_prompt_and_parse(fake_llm):
    prompt = ips.build_system_prompt(5, fixed_negative=True)
    assert '"negative"' not in prompt
    calls, outputs = fake_llm
    outputs.append('{"positive": "1girl, solo, gamjeong style"}')
    result = ips.translate_to_image_prompt("일기", "혼자", "편안한", "", "", config={"fixed_negative": True})
    assert result == {"positive": "1girl, solo, gamjeong style", "negative": ips.FALLBACK_NEGATIVE}


def test_fixed_negative_equals_system_prompt_negative_exactly(fake_llm):
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
