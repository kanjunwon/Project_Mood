from collections import Counter, defaultdict
from app.emotion_taxonomy import EMOTION_CATEGORIES, SUB_TO_MID, get_valence

# 재유가 정한 중분류(8개) 색상 - 색채심리학 기반
MID_COLORS = {
    "상승형": "#E4A4C2",
    "활동형": "#FABE7D",
    "해소형": "#8CDECE",
    "안정형": "#C5E8A8",
    "경계형": "#79BCE2",
    "침체형": "#5071A9",
    "소모형": "#957AA1",
    "폭발형": "#B26D6D",
}

# 소분류(24개) 각각은 자기가 속한 중분류 색을 그대로 씀
# SUB_TO_MID가 emotion_taxonomy.py에 있는 매핑 그대로라, 거기서 카테고리가 바뀌어도 자동으로 맞춰짐
EMOTION_COLORS = {emotion: MID_COLORS[mid] for emotion, mid in SUB_TO_MID.items()}


def _top_n_emotions(entries: list, n: int = 3) -> list:
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

    by_date = defaultdict(list)
    for entry in entries:
        created = entry.get("created_at", "")
        date_str = created[:10] if created else "unknown"
        by_date[date_str].append(entry)

    emotion_flow = []
    for date_str in sorted(by_date.keys()):
        day_entries = by_date[date_str]
        avg_sentiment = sum(e.get("sentiment_score", 0) or 0 for e in day_entries) / len(day_entries)
        day_top1 = _top_n_emotions(day_entries, n=1)
        emotion_flow.append({
            "date": date_str,
            "sentiment_score": round(avg_sentiment, 3),
            "top_emotion": day_top1[0]["emotion"] if day_top1 else None,
        })

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
            "valence": get_valence(emotion) if emotion in EMOTION_CATEGORIES else None,
        }
        for emotion, score in sorted(total_scores.items(), key=lambda x: x[1], reverse=True)
    ]

    most_positive_day = max(emotion_flow, key=lambda d: d["sentiment_score"])["date"] if emotion_flow else None
    most_negative_day = min(emotion_flow, key=lambda d: d["sentiment_score"])["date"] if emotion_flow else None

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