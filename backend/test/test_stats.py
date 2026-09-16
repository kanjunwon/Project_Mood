from app.services.stats_service import compute_daily_stats, compute_monthly_stats

# 24개 감정 체계 기준으로 재작성 (2026-09) - 예전 6개(기쁨/슬픔/분노/불안/평온/놀람) 그대로
# 1:1 치환: 기쁨->기쁜, 슬픔->슬픈, 분노->화나는, 불안->불안한, 평온->편안한, 놀람->설레는
# (긍정/부정, 서로 다른 중분류에 걸치도록 골라서 valence/색상 매핑도 같이 검증되게 함)
MOCK_ENTRIES = [
    {
        "who": "친구, 연인",
        "where_": "한강공원",
        "created_at": "2026-08-01T10:00:00",
        "emotion_scores": {"기쁜": 0.6, "슬픈": 0.05, "화나는": 0.05, "불안한": 0.1, "편안한": 0.15, "설레는": 0.05},
        "sentiment_score": 0.7,
    },
    {
        "who": "가족",
        "where_": "본가",
        "created_at": "2026-08-02T18:00:00",
        "emotion_scores": {"기쁜": 0.4, "슬픈": 0.1, "화나는": 0.05, "불안한": 0.05, "편안한": 0.35, "설레는": 0.05},
        "sentiment_score": 0.5,
    },
    {
        "who": "친구",
        "where_": "한강공원",
        "created_at": "2026-08-02T20:00:00",
        "emotion_scores": {"기쁜": 0.1, "슬픈": 0.5, "화나는": 0.1, "불안한": 0.2, "편안한": 0.05, "설레는": 0.05},
        "sentiment_score": -0.4,
    },
]


def test_compute_daily_stats():
    day_entries = [e for e in MOCK_ENTRIES if e["created_at"].startswith("2026-08-01")]
    result = compute_daily_stats(day_entries, "2026-08-01")

    assert result["date"] == "2026-08-01"
    assert result["top_emotion"] == "기쁜"
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
    assert len(result["emotion_distribution"]) == 6  # 이번 테스트 데이터에 등장한 감정 종류 수
    assert result["top_companion"] is not None
    assert result["top_place"]["name"] == "한강공원"  # 한강공원이 2번 나와서 1등이어야 함
    assert result["top_place"]["count"] == 2

    # 24개 체계 도입하면서 emotion_distribution에 색상/긍부정(valence)이 자동으로 붙는지 검증
    # (재유가 정한 중분류 8개 색상 매핑, emotion_taxonomy.get_valence 연동 확인용)
    joy_entry = next(e for e in result["emotion_distribution"] if e["emotion"] == "기쁜")
    assert joy_entry["valence"] == "긍정감정"
    assert joy_entry["color"] is not None

    sad_entry = next(e for e in result["emotion_distribution"] if e["emotion"] == "슬픈")
    assert sad_entry["valence"] == "부정감정"


def test_compute_monthly_stats_empty():
    result = compute_monthly_stats([], 2026, 8)
    assert result["top_emotion"] is None
    assert result["emotion_flow"] == []