import importlib.util
import os
from pathlib import Path

os.environ["MOCK_MODE"] = "true"

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

_SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "measure_diary_llm.py"
_spec = importlib.util.spec_from_file_location("measure_diary_llm", _SCRIPT)
m = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(m)


# ---------- 감정 단서 / 분류 ----------

def test_detect_cues():
    assert m.cue_valence(m.detect_cues("노래방 갔다. 재밌었다.")) == "긍정감정"
    assert m.cue_valence(m.detect_cues("드라마 봤는데 재미없었다.")) == "부정감정"  # '재미있'으로 잘못 안 잡힘
    assert m.cue_valence(m.detect_cues("힘들었는데 뿌듯했다.")) == "혼합"
    assert m.cue_valence(m.detect_cues("공원 한 바퀴 돌았다.")) == "없음"
    assert m.cue_valence(m.detect_cues("바람이 차긴 했는데 나쁘지 않았다.")) == "긍정감정"


def test_classify_verdicts():
    text = "노래방 갔다. 재밌었다."
    ok = m.classify(text, [["즐거운", 0.5], ["신나는", 0.3]], [["즐거운", 0.55], ["신나는", 0.3]])
    assert ok["verdict"] == "일치" and ok["top1_changed_by_weight"] is False
    flipped = m.classify(text, [["즐거운", 0.4], ["지루한", 0.35]], [["지루한", 0.42], ["즐거운", 0.38]])
    assert flipped["verdict"] == "가중치가 뒤집음" and flipped["top1_changed_by_weight"] is True
    wrong = m.classify(text, [["지루한", 0.6], ["즐거운", 0.2]], [["지루한", 0.6], ["즐거운", 0.2]])
    assert wrong["verdict"] == "KoBERT 원본부터 틀림"
    weak = m.classify("공원 갔다.", [["편안한", 0.31], ["지루한", 0.27]], [["편안한", 0.31], ["지루한", 0.27]])
    assert weak["verdict"] == "단서 없음 + 확률 갈림" and weak["raw_margin"] == 0.04


def test_reason_key_normalizes_validator_reasons():
    assert m.reason_key("길이=212자") == "길이"
    assert m.reason_key("술 지어냄(소주)") == "술 지어냄"
    assert m.reason_key("식사시간대 지어냄(저녁)") == "식사시간대 지어냄"


def _fake_status(attempt_reasons, fallback=False, raw=None, weighted=None, diary="노래방 갔다. 재밌었다."):
    details = [{"attempt": i + 1, "reasons": r, "tokens_per_sec": 18.0} for i, r in enumerate(attempt_reasons)]
    return {"status": "done", "error": None,
            "result": {"generated_diary": diary, "top_emotion": max(weighted, key=weighted.get),
                       "emotion_scores": weighted},
            "diag": {"job_total_sec": 45.0, "queue_wait_sec": 0.1, "diary_total_sec": 20.0,
                     "diary_attempts": len(details), "diary_fallback": fallback, "kobert_sec": 0.2,
                     "image_prompt_sec": 10.0, "comfyui_sec": 12.0, "upload_sec": 2.0,
                     "diary_attempt_details": details, "kobert_raw_scores": raw, "weight_applied": True}}


def test_summarize_and_render():
    raw = {"즐거운": 0.4, "지루한": 0.35, "편안한": 0.25}
    weighted = {"지루한": 0.42, "즐거운": 0.38, "편안한": 0.2}
    s1 = m.summarize_job("base", "노래방", _fake_status([["식사시간대 지어냄(저녁)"], []], raw=raw, weighted=weighted), 46.0)
    assert s1["reasons"] == ["식사시간대 지어냄"] and s1["verdict"] == "가중치가 뒤집음"
    s2 = m.summarize_job("emotion_word", "노래방", _fake_status([[]], raw=raw, weighted=raw), 30.0)
    s2["job_total_sec"] = 70.0
    md = m.render_markdown({"started_at": "t", "user_id": 1, "save_db": False, "emotion": None,
                            "jobs": [s1, s2], "skipped": []})
    assert "| base | 1 | 45.0 / 45.0 | 0 | 1 | 2 | 0/1 | 0/1/0 | 0 | 1/1 | 0/1 | 18.0 |" in md
    assert "| emotion_word | 1 | 70.0 / 70.0 | 1 | 0 | 1 | 0/1 | 0/0/0 | 0 | 1/1 | 1/1 | 18.0 |" in md
    assert "| 식사시간대 지어냄 | 1 | 0 |" in md
    assert "가중치가 뒤집음 | 1 |" in md


# ---------- 측정용 엔드포인트 (MOCK_MODE, DB 없음) ----------

@pytest.fixture
def client():
    from app.routers import debug
    from app.services.auth_service import create_access_token
    app = FastAPI()
    app.include_router(debug.router)
    c = TestClient(app)
    c.headers.update({"Authorization": f"Bearer {create_access_token(user_id=7)}"})
    return c


def test_debug_emotion_endpoint(client):
    r = client.post("/debug/emotion", json={"texts": ["재밌었다.", "그냥 그랬다."]})
    assert r.status_code == 200
    body = r.json()
    assert body["weight_applied"] is False and len(body["items"]) == 2
    assert body["items"][0]["raw_top"][0][0] == "편안한"  # mock KoBERT


def test_debug_diary_job_runs_and_skips_db_by_default(client, monkeypatch):
    from app.routers import diary as diary_router
    monkeypatch.setattr(diary_router, "save_diary", lambda row: pytest.fail("save_db=False인데 저장됨"))
    body = {"what": "노래방", "why": "시험 끝나서", "who": "친구", "when": "10월 2일 목요일 오후 6시",
            "where": "노래방", "prompt_variant": "emotion_word"}
    job_id = client.post("/debug/diary-jobs", json=body).json()["job_id"]
    s = client.get(f"/debug/diary-jobs/{job_id}").json()
    assert s["status"] == "done", s
    assert s["result"]["generated_diary"]
    assert "job_total_sec" in s["diag"] and "queue_wait_sec" in s["diag"]


def test_debug_diary_job_rejects_unknown_variant(client):
    body = {"what": "x", "why": "y", "who": "혼자", "when": "10월 2일 목요일 오후 6시", "where": "집",
            "prompt_variant": "nope"}
    assert client.post("/debug/diary-jobs", json=body).status_code == 400


def test_debug_diary_job_save_db_true_saves(client, monkeypatch):
    from app.routers import diary as diary_router
    saved = []
    monkeypatch.setattr(diary_router, "save_diary", lambda row: saved.append(row) or [{"id": 1}])
    body = {"what": "x", "why": "y", "who": "혼자", "when": "10월 2일 목요일 오후 6시", "where": "집", "save_db": True}
    job_id = client.post("/debug/diary-jobs", json=body).json()["job_id"]
    assert client.get(f"/debug/diary-jobs/{job_id}").json()["status"] == "done"
    assert len(saved) == 1


def test_regular_endpoints_still_save(monkeypatch):
    # 일반 /generate-diary는 save_db 기본값(True) 그대로
    from app.main import app
    from app.routers import diary as diary_router
    from app.services.auth_service import create_access_token
    saved = []
    monkeypatch.setattr(diary_router, "save_diary", lambda row: saved.append(row) or None)
    c = TestClient(app)
    r = c.post("/generate-diary", json={"what": "x", "why": "y", "who": "혼자", "when": "10월 2일 목요일 오후 6시", "where": "집"},
               headers={"Authorization": f"Bearer {create_access_token(user_id=7)}"})
    assert r.status_code == 200 and len(saved) == 1
