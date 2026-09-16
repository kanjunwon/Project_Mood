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