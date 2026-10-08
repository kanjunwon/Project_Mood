import os

os.environ["MOCK_MODE"] = "true"  # 테스트는 항상 mock 모드로 (GPU 필요 없게)

import pytest

from app.services import llama_service as ls

GOOD = "주말에 카페에 가서 과제를 했다. 창가 자리에 앉아서 노트북을 켰다. 생각보다 오래 걸렸지만 다 끝내고 나왔다."
WITH_ALCOHOL = "친구랑 노래방에 갔다. 끝나고 맥주도 한잔 했다. 늦게 들어왔다."


@pytest.fixture
def fake_llm(monkeypatch):
    outputs = []
    calls = []

    def fake(prompt_str, temperature, max_new_tokens=220, do_sample=True, extra_stop_strings=None, stats=None):
        calls.append({"prompt": prompt_str, "temperature": temperature})
        if stats is not None:
            stats.update(input_tokens=1500, output_tokens=120, tokens_per_sec=18.0, hit_max_new_tokens=False)
        return outputs.pop(0)

    monkeypatch.setattr(ls, "MOCK_MODE", False)
    monkeypatch.setattr(ls, "_generate_once", fake)
    return outputs, calls


def _gen(timings):
    return ls.generate_diary_text("과제", "마감이라", "혼자", "10월 4일 토요일 오후 2시", "카페", timings=timings)


def test_attempt_details_recorded_with_reasons(fake_llm):
    outputs, calls = fake_llm
    outputs.extend([WITH_ALCOHOL, GOOD])
    timings = {}
    text, failed = _gen(timings)
    assert text == GOOD and failed is False
    details = timings["diary_attempt_details"]
    assert [d["passed"] for d in details] == [False, True]
    assert any("술 지어냄" in r for r in details[0]["reasons"])
    assert details[0]["output_tokens"] == 120 and details[0]["tokens_per_sec"] == 18.0
    assert details[0]["text"] == WITH_ALCOHOL
    assert timings["diary_attempts"] == 2 and timings["diary_fallback"] is False
    assert [c["temperature"] for c in calls] == pytest.approx([0.45, 0.3])  # 기존 온도 스케줄 그대로


def test_fallback_after_three_failures_is_recorded(fake_llm):
    outputs, calls = fake_llm
    outputs.extend([WITH_ALCOHOL] * 3)
    timings = {}
    text, failed = _gen(timings)
    assert failed is True
    assert text == ls._safe_fallback_diary("과제", "마감이라", "혼자", "10월 4일 토요일 오후 2시", "카페")
    assert timings["diary_fallback"] is True and len(timings["diary_attempt_details"]) == 3


def test_timings_optional(fake_llm):
    outputs, _ = fake_llm
    outputs.append(GOOD)
    assert _gen(None) == (GOOD, False)


# ---------- 프롬프트 변형 ----------
import hashlib

# main(b266c31)의 SYSTEM_PREAMBLE + FEWSHOT_EXAMPLES sha256. 기본 프롬프트가 바뀌면 실패해야 함.
MAIN_PROMPT_SHA256 = "d8cf44825df360dfd886b3e6372286d125be90e55c4154ae6eee874e43d5763f"
CONTENT = "무엇을: X\n이유: Y\n누구와: 혼자\n언제: 오후 2시\n어디서: 집"


def test_default_prompt_unchanged_from_main():
    assert hashlib.sha256((ls.SYSTEM_PREAMBLE + ls.FEWSHOT_EXAMPLES).encode()).hexdigest() == MAIN_PROMPT_SHA256
    assert ls.build_prompt(CONTENT) == ls.build_prompt(CONTENT, "base")
    assert ls.build_prompt(CONTENT).startswith(ls.SYSTEM_PREAMBLE + "\n" + ls.FEWSHOT_EXAMPLES)


def test_emotion_word_variant_changes_only_rule2_tail():
    base, variant = ls.SYSTEM_PREAMBLE, ls.SYSTEM_PREAMBLE_EMOTION_WORD
    assert base != variant
    # 규칙 2번의 교훈형/과장형 금지 문구는 그대로 남아 있어야 함
    for phrase in ("교훈적으로 정리하거나", "'최고의 하루였다'", "과장된 비유도 쓰지 않는다", "'마법처럼'"):
        assert phrase in variant
    assert "'재밌었다'" in variant and "'답답했다'" in variant
    # 바뀐 건 규칙 2번 마지막 문장 하나뿐 (다른 줄은 동일)
    diff = [(a, b) for a, b in zip(base.split("\n"), variant.split("\n")) if a != b]
    assert len(diff) == 1 and diff[0][0].startswith("2. 담백하게")
    assert ls.build_prompt(CONTENT, "emotion_word").startswith(variant)


def test_unknown_variant_raises():
    with pytest.raises(ValueError):
        ls.build_prompt(CONTENT, "nope")


def test_variant_is_passed_to_generation(fake_llm):
    outputs, calls = fake_llm
    outputs.append(GOOD)
    timings = {}
    ls.generate_diary_text("과제", "마감이라", "혼자", "오후 2시", "카페", timings=timings, prompt_variant="emotion_word")
    assert calls[0]["prompt"].startswith(ls.SYSTEM_PREAMBLE_EMOTION_WORD)
    assert timings["prompt_variant"] == "emotion_word"


def _fewshot_pairs(fewshot):
    import re
    blocks = fewshot.split("Human: 다음 정보를 바탕으로 감성적인 일기를 작성해라:\n\n")[1:]
    pairs = []
    for b in blocks:
        info, diary = b.split("Assistant:\n")
        f = dict(re.findall(r"(무엇을|이유|누구와|언제|어디서): (.*)", info))
        ctx = ls.expand_context(f"{f['누구와']} {f['무엇을']} {f['이유']} {f['언제']} {f['어디서']}")
        pairs.append((f, diary.strip(), ctx))
    return pairs


def test_current_fewshot_example3_fails_own_validator():
    # 0단계에서 확인한 약점 기록: 기본 few-shot 3번 예시(본가 방문)는 지금 검증 기준으로 불합격
    results = [ls.validate_diary(d, context_str=c)[0] for _, d, c in _fewshot_pairs(ls.FEWSHOT_EXAMPLES)]
    assert results == [True, True, False, True, True]


def test_fewshot_no_mealtime_variant_passes_validator_and_has_no_mealtime_words():
    pairs = _fewshot_pairs(ls.FEWSHOT_EXAMPLES_NO_MEALTIME)
    assert len(pairs) == 5
    for f, diary, ctx in pairs:
        ok, reasons, _ = ls.validate_diary(diary, context_str=ctx)
        assert ok, (f["무엇을"], reasons)
        for word in ls.MEALTIME_KEYWORDS:
            assert word not in diary and word not in f["언제"]
    # 시스템 프롬프트는 그대로, 예시만 바뀜
    assert ls.PROMPT_VARIANTS["fewshot_no_mealtime"][0] == ls.SYSTEM_PREAMBLE
