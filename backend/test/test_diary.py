import os
os.environ["MOCK_MODE"] = "true"  # 테스트는 항상 mock 모드로 (GPU 필요 없게)

from fastapi.testclient import TestClient
from app.main import app
from app.services.auth_service import create_access_token

client = TestClient(app)

# DB 연결 없는 CI 환경이라, /signup을 실제로 호출하지 않고
# create_access_token으로 토큰만 직접 만들어서 씀 (test_auth.py랑 같은 방식)
_TEST_TOKEN = create_access_token(user_id=1)
_AUTH_HEADERS = {"Authorization": f"Bearer {_TEST_TOKEN}"}


def test_health_check():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_generate_diary_success():
    payload = {
        "what": "카페에서 과제 하기",
        "why": "시험기간이라 집중해서 공부하려고",
        "who": ["혼자"],
        "when": "주말 오후 2시",
        "where": "집 앞 카페",
    }
    response = client.post("/generate-diary", json=payload, headers=_AUTH_HEADERS)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "generated_diary" in data
    assert isinstance(data["validation_failed"], bool)


def test_generate_diary_missing_field():
    payload = {
        "why": "이유만 있음",
        "who": "혼자",
        "when": "오늘",
        "where": "집",
    }
    response = client.post("/generate-diary", json=payload, headers=_AUTH_HEADERS)
    assert response.status_code == 422


def test_generate_diary_requires_auth():
    # 토큰 없이 요청하면 401이어야 함 (2026-09 JWT 필수화 검증)
    payload = {
        "what": "카페에서 과제 하기",
        "why": "시험기간이라",
        "who": ["혼자"],
        "when": "오늘",
        "where": "집",
    }
    response = client.post("/generate-diary", json=payload)
    assert response.status_code in (401, 403)


def test_get_diaries_no_db():
    # DB 연결 안 된 상태(테스트 환경)라 빈 목록이 정상 응답으로 와야 함 (에러 X)
    response = client.get("/diaries/me", headers=_AUTH_HEADERS)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["diaries"] == []

# ---------------------------------------------------------------------------
# 2026-10 추가: 날짜(date) 처리 + 비동기 job 방식
# ---------------------------------------------------------------------------
from datetime import datetime, timedelta, timezone

_KST = timezone(timedelta(hours=9))


def _payload(**extra):
    base = {"what": "카페에서 과제 하기", "why": "시험기간이라", "who": ["혼자"],
            "when": "주말 오후 2시", "where": "집 앞 카페"}
    base.update(extra)
    return base


def test_generate_diary_rejects_future_date():
    tomorrow = (datetime.now(_KST).date() + timedelta(days=1)).isoformat()
    r = client.post("/generate-diary", json=_payload(date=tomorrow), headers=_AUTH_HEADERS)
    assert r.status_code == 400


def test_generate_diary_rejects_bad_date_format():
    r = client.post("/generate-diary", json=_payload(date="내일"), headers=_AUTH_HEADERS)
    assert r.status_code == 400


def test_generate_diary_accepts_past_and_today_and_aliases():
    today = datetime.now(_KST).date()
    for d, key in [(today, "date"), (today - timedelta(days=3), "date"), (today - timedelta(days=1), "entry_date")]:
        r = client.post("/generate-diary", json=_payload(**{key: d.isoformat()}), headers=_AUTH_HEADERS)
        assert r.status_code == 200, (key, d, r.text)


def test_created_at_for_backdated_keeps_same_date_in_utc_and_kst():
    from app.routers.diary import _created_at_for
    today = datetime.now(_KST).date()
    assert _created_at_for(None) is None
    assert _created_at_for(today) is None  # 오늘은 DB 기본값(now()) 그대로
    past = today - timedelta(days=5)
    stamp = datetime.fromisoformat(_created_at_for(past))
    assert stamp.astimezone(_KST).date() == past
    assert stamp.astimezone(timezone.utc).date() == past  # created_at[:10](UTC)로 묶여도 같은 날짜


def test_job_flow_create_and_poll():
    r = client.post("/generate-diary/jobs", json=_payload(), headers=_AUTH_HEADERS)
    assert r.status_code == 202
    job_id = r.json()["job_id"]
    s = client.get(f"/generate-diary/jobs/{job_id}", headers=_AUTH_HEADERS)
    assert s.status_code == 200
    body = s.json()
    assert body["status"] in ("processing", "done")
    assert body["status"] == "done"  # TestClient는 백그라운드 작업까지 끝낸 뒤 응답함
    assert body["result"]["status"] == "success"
    assert body["error"] is None


def test_job_rejects_future_date_immediately():
    tomorrow = (datetime.now(_KST).date() + timedelta(days=1)).isoformat()
    r = client.post("/generate-diary/jobs", json=_payload(date=tomorrow), headers=_AUTH_HEADERS)
    assert r.status_code == 400


def test_job_not_visible_to_other_user():
    r = client.post("/generate-diary/jobs", json=_payload(), headers=_AUTH_HEADERS)
    job_id = r.json()["job_id"]
    other = {"Authorization": f"Bearer {create_access_token(user_id=2)}"}
    assert client.get(f"/generate-diary/jobs/{job_id}", headers=other).status_code == 404
    assert client.get("/generate-diary/jobs/nonexistent", headers=_AUTH_HEADERS).status_code == 404


def test_job_requires_auth():
    assert client.post("/generate-diary/jobs", json=_payload()).status_code in (401, 403)


def test_date_is_read_from_when_text_when_app_sends_no_date():
    from app.routers.diary import _date_from_when
    year = datetime.now(_KST).year
    assert _date_from_when("10월 3일 금요일 오후 2시").year == year
    assert (_date_from_when("1월 5일 월요일 오전 9시").month, _date_from_when("1월 5일 월요일 오전 9시").day) == (1, 5)
    assert _date_from_when("주말 오후 2시") is None
    assert _date_from_when("2월 31일") is None  # 없는 날짜는 무시
    assert _date_from_when(None) is None


def test_future_when_text_is_rejected_without_date_field():
    t = datetime.now(_KST).date() + timedelta(days=2)
    when = f"{t.month}월 {t.day}일 오후 2시"
    r = client.post("/generate-diary", json=_payload(when=when), headers=_AUTH_HEADERS)
    assert r.status_code == 400
    r2 = client.post("/generate-diary/jobs", json=_payload(when=when), headers=_AUTH_HEADERS)
    assert r2.status_code == 400


def test_past_when_text_is_accepted_without_date_field():
    t = datetime.now(_KST).date() - timedelta(days=1)
    when = f"{t.month}월 {t.day}일 오후 2시"
    r = client.post("/generate-diary", json=_payload(when=when), headers=_AUTH_HEADERS)
    assert r.status_code == 200, r.text
