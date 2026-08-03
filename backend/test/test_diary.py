import os
os.environ["MOCK_MODE"] = "true"  # 테스트는 항상 mock 모드로 (GPU 필요 없게)

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


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
    response = client.post("/generate-diary", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "generated_diary" in data
    assert isinstance(data["validation_failed"], bool)


def test_generate_diary_missing_field():
    # 필수 필드(what) 빠뜨리면 422 에러 떠야 정상
    payload = {
        "why": "이유만 있음",
        "who": "혼자",
        "when": "오늘",
        "where": "집",
    }
    response = client.post("/generate-diary", json=payload)
    assert response.status_code == 422
