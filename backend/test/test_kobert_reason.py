import os

os.environ["MOCK_MODE"] = "true"

import pytest

from app.services import kobert_service as ks


def _result(scores):
    top = max(scores, key=scores.get)
    return {"top_emotion": top, "scores": scores, "sentiment_score": 0.0}


@pytest.fixture
def fake_kobert(monkeypatch):
    """일기 본문이면 '편안한'이 1등, 이유 답변이면 '실망한'이 1등인 가짜 KoBERT"""
    calls = []

    def fake(text):
        calls.append(text)
        if text == "아쉽다":
            return _result({"편안한": 0.1, "실망한": 0.9})
        return _result({"편안한": 0.6, "실망한": 0.4})

    monkeypatch.delenv("KOBERT_WHY_WEIGHT", raising=False)
    monkeypatch.setattr(ks, "analyze_emotion", fake)
    return calls


def test_reason_changes_top_emotion_with_default_weight(fake_kobert):
    r = ks.analyze_emotion_with_reason("시험을 봤다. 집에 왔다.", "아쉽다")
    # 0.6*편안 + 0.4*... : 편안 0.6*0.6+0.4*0.1=0.40, 실망한 0.6*0.4+0.4*0.9=0.60
    assert r["top_emotion"] == "실망한"
    assert r["scores"]["실망한"] == pytest.approx(0.60)
    assert set(r) == {"top_emotion", "scores", "sentiment_score"}  # 통계 파이프라인이 기대하는 형태 유지
    assert fake_kobert == ["시험을 봤다. 집에 왔다.", "아쉽다"]


def test_weight_zero_or_empty_why_is_old_behavior(fake_kobert, monkeypatch):
    old = ks.analyze_emotion("시험을 봤다.")
    assert ks.analyze_emotion_with_reason("시험을 봤다.", "") == old
    monkeypatch.setenv("KOBERT_WHY_WEIGHT", "0")
    assert ks.analyze_emotion_with_reason("시험을 봤다.", "아쉽다") == old


def test_bad_env_value_falls_back_and_weight_is_clamped(fake_kobert, monkeypatch):
    monkeypatch.setenv("KOBERT_WHY_WEIGHT", "abc")
    assert ks.analyze_emotion_with_reason("시험", "아쉽다")["scores"]["실망한"] == pytest.approx(0.60)
    r = ks.analyze_emotion_with_reason("시험", "아쉽다", why_weight=5)
    assert r["scores"]["실망한"] == pytest.approx(0.9)  # 1로 잘림 -> 이유 점수만
