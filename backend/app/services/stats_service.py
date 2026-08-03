from collections import Counter, defaultdict

# 프론트(종현)가 그래프 그릴 때 쓸 색상, 감정 카테고리랑 1:1로 고정
EMOTION_COLORS = {
    "기쁨": "#FFD93D",
    "슬픔": "#4D96FF",
    "분노": "#FF6B6B",
    "불안": "#9B59B6",
    "평온": "#6BCB77",
    "놀람": "#FF9F45",
}


def _top_n_emotions(entries: list, n: int = 3) -> list:
    # 여러 일기의 emotion_scores를 다 더해서 상위 n개 감정 뽑기
    total_scores = defaultdict(float)
    for entry in entries:
        scores = entry.get("emotion_scores") or {}
        for emotion, score in scores.items():
            total_scores[emotion] += score

    sorted_emotions = sorted(total_scores.items(), key=lambda x: x[1], reverse=True)
    return [{"emotion": e, "score": round(s, 3)} for e, s in sorted_emotions[:n]]


def compute_daily_stats(entries: list, date: str) -> dict:
    if not entries:
        return {
            "date": date,
            "top_emotion": None,
            "top3_emotions": [],
            "companions": [],
            "places": [],
        }

    top3 = _top_n_emotions(entries, n=3)
    top_emotion = top3[0]["emotion"] if top3 else None

    companions = set()
    places = set()
    for entry in entries:
        who = entry.get("who") or ""
        for person in who.split(","):
            person = person.strip()
            if person:
                companions.add(person)
        where = entry.get("where_") or entry.get("where")
        if where:
            places.add(where.strip())

    return {
        "date": date,
        "top_emotion": top_emotion,
        "top3_emotions": top3,
        "companions": list(companions),
        "places": list(places),
    }


def compute_monthly_stats(entries: list, year: int, month: int) -> dict:
    if not entries:
        return {
            "year": year,
            "month": month,
            "top_emotion": None,
            "top3_emotions": [],
            "emotion_flow": [],
            "emotion_distribution": [],
            "most_positive_day": None,
            "most_negative_day": None,
            "top_companion": None,
            "top_place": None,
        }

    top3 = _top_n_emotions(entries, n=3)
    top_emotion = top3[0]["emotion"] if top3 else None

    # 날짜별로 묶어서(하루에 여러 개 있으면 평균) 감정 흐름 그래프용 데이터 만들기
    by_date = defaultdict(list)
    for entry in entries:
        created = entry.get("created_at", "")
        date_str = created[:10] if created else "unknown"
        by_date[date_str].append(entry)

    emotion_flow = []
    for date_str in sorted(by_date.keys()):
        day_entries = by_date[date_str]
        avg_sentiment = sum(e.get("sentiment_score", 0) or 0 for e in day_entries) / len(day_entries)
        day_top3 = _top_n_emotions(day_entries, n=1)
        emotion_flow.append({
            "date": date_str,
            "sentiment_score": round(avg_sentiment, 3),
            "top_emotion": day_top3[0]["emotion"] if day_top3 else None,
        })

    # 이번달 감정 분포(색상 포함) - 전체 감정 점수 합에서 비율 계산
    total_scores = defaultdict(float)
    for entry in entries:
        scores = entry.get("emotion_scores") or {}
        for emotion, score in scores.items():
            total_scores[emotion] += score
    total_sum = sum(total_scores.values()) or 1
    emotion_distribution = [
        {
            "emotion": emotion,
            "percentage": round(score / total_sum * 100, 1),
            "color": EMOTION_COLORS.get(emotion, "#CCCCCC"),
        }
        for emotion, score in sorted(total_scores.items(), key=lambda x: x[1], reverse=True)
    ]

    # 가장 긍정적/부정적인 날
    most_positive_day = max(emotion_flow, key=lambda d: d["sentiment_score"])["date"] if emotion_flow else None
    most_negative_day = min(emotion_flow, key=lambda d: d["sentiment_score"])["date"] if emotion_flow else None

    # 가장 많이 함께한 사람 + 그 사람과 느낀 감정
    companion_counter = Counter()
    companion_entries = defaultdict(list)
    for entry in entries:
        who = entry.get("who") or ""
        for person in who.split(","):
            person = person.strip()
            if person:
                companion_counter[person] += 1
                companion_entries[person].append(entry)

    top_companion = None
    if companion_counter:
        top_person, count = companion_counter.most_common(1)[0]
        person_top3 = _top_n_emotions(companion_entries[top_person], n=3)
        top_companion = {
            "name": top_person,
            "count": count,
            "top3_emotions": person_top3,
        }

    # 가장 많이 방문한 장소 + 그곳에서 느낀 감정
    place_counter = Counter()
    place_entries = defaultdict(list)
    for entry in entries:
        where = (entry.get("where_") or entry.get("where") or "").strip()
        if where:
            place_counter[where] += 1
            place_entries[where].append(entry)

    top_place = None
    if place_counter:
        top_place_name, count = place_counter.most_common(1)[0]
        place_top3 = _top_n_emotions(place_entries[top_place_name], n=3)
        top_place = {
            "name": top_place_name,
            "count": count,
            "top3_emotions": place_top3,
        }

    return {
        "year": year,
        "month": month,
        "top_emotion": top_emotion,
        "top3_emotions": top3,
        "emotion_flow": emotion_flow,
        "emotion_distribution": emotion_distribution,
        "most_positive_day": most_positive_day,
        "most_negative_day": most_negative_day,
        "top_companion": top_companion,
        "top_place": top_place,
    }
