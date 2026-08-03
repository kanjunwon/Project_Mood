from app.services.stats_service import compute_daily_stats, compute_monthly_stats

MOCK_ENTRIES = [
    {
        "who": "친구, 연인",
        "where_": "한강공원",
        "created_at": "2026-08-01T10:00:00",
        "emotion_scores": {"기쁨": 0.6, "슬픔": 0.05, "분노": 0.05, "불안": 0.1, "평온": 0.15, "놀람": 0.05},
        "sentiment_score": 0.7,
    },
    {
        "who": "가족",
        "where_": "본가",
        "created_at": "2026-08-02T18:00:00",
        "emotion_scores": {"기쁨": 0.4, "슬픔": 0.1, "분노": 0.05, "불안": 0.05, "평온": 0.35, "놀람": 0.05},
        "sentiment_score": 0.5,
    },
    {
        "who": "친구",
        "where_": "한강공원",
        "created_at": "2026-08-02T20:00:00",
        "emotion_scores": {"기쁨": 0.1, "슬픔": 0.5, "분노": 0.1, "불안": 0.2, "평온": 0.05, "놀람": 0.05},
        "sentiment_score": -0.4,
    },
]


def test_compute_daily_stats():
    day_entries = [e for e in MOCK_ENTRIES if e["created_at"].startswith("2026-08-01")]
    result = compute_daily_stats(day_entries, "2026-08-01")

    assert result["date"] == "2026-08-01"
    assert result["top_emotion"] == "기쁨"
    assert len(result["top3_emotions"]) == 3
    assert "친구" in result["companions"]
    assert "연인" in result["companions"]
    assert "한강공원" in result["places"]


def test_compute_daily_stats_empty():
    result = compute_daily_stats([], "2026-08-05")
    assert result["top_emotion"] is None
    assert result["companions"] == []


def test_compute_monthly_stats():
    result = compute_monthly_stats(MOCK_ENTRIES, 2026, 8)

    assert result["year"] == 2026
    assert result["month"] == 8
    assert len(result["emotion_flow"]) == 2  # 8/1, 8/2 이렇게 2일치
    assert len(result["emotion_distribution"]) == 6  # 감정 카테고리 6개 다 나와야 함
    assert result["top_companion"] is not None
    assert result["top_place"]["name"] == "한강공원"  # 한강공원이 2번 나와서 1등이어야 함
    assert result["top_place"]["count"] == 2


def test_compute_monthly_stats_empty():
    result = compute_monthly_stats([], 2026, 8)
    assert result["top_emotion"] is None
    assert result["emotion_flow"] == []
