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
