import os

from app.emotion_taxonomy import get_valence
from app.emotion_list import ID_TO_EMOTION  # 종현이가 준 파일 - 모델 출력 순서(가나다순) 그대로 유지해야 함

MOCK_MODE = os.environ.get("MOCK_MODE", "false").lower() == "true"


def _mock_analyze() -> dict:
    return {
        "top_emotion": "편안한",
        "scores": {"편안한": 0.6, "감사한": 0.25, "뿌듯한": 0.15},
        "sentiment_score": 1.0,
    }


def analyze_emotion(text: str) -> dict:
    """
    KoBERT로 감정 분석. 종현이가 학습한 24개 소분류 모델 그대로 사용.

    리턴 형태 (통계 파이프라인이 이 구조에 의존하고 있어서 변경 금지):
    {
        "top_emotion": "기쁜",
        "scores": {"행복한": 0.05, "기쁜": 0.4, ..., 24개 전부},
        "sentiment_score": -1.0 ~ 1.0 (긍정감정 확률 합 - 부정감정 확률 합)
    }
    """
    if MOCK_MODE:
        return _mock_analyze()

    import torch
    from app.models.kobert_loader import get_model_and_tokenizer, MAX_LEN

    model, tokenizer, device = get_model_and_tokenizer()

    enc = tokenizer(text, truncation=True, max_length=MAX_LEN, padding="max_length", return_tensors="pt")
    enc = {k: v.to(device) for k, v in enc.items()}

    with torch.no_grad():
        logits = model(**enc).logits
        probs = torch.softmax(logits, dim=-1).cpu().numpy()[0]

    # ID_TO_EMOTION은 학습 시 순서(가나다순) 그대로라서, 이걸로만 디코딩해야 정확함
    scores = {ID_TO_EMOTION[i]: float(probs[i]) for i in range(len(probs))}
    top_emotion = max(scores, key=scores.get)

    positive_sum = sum(score for emotion, score in scores.items() if get_valence(emotion) == "긍정감정")
    negative_sum = sum(score for emotion, score in scores.items() if get_valence(emotion) == "부정감정")
    sentiment_score = round(positive_sum - negative_sum, 3)

    return {
        "top_emotion": top_emotion,
        "scores": scores,
        "sentiment_score": sentiment_score,
    }

def analyze_emotion_with_reason(diary_text: str, why: str = "", why_weight: float | None = None) -> dict:
    """
    patch 12: 생성된 일기 + 사용자가 직접 쓴 '이유' 답변을 같이 보고 감정을 정한다.
    일기는 LLM이 쓴 글이라 감정 단서가 흐리거나(담백하게 쓰라는 규칙) 틀릴 수 있음.
    '이유'("아쉽다", "재미있게 잘 놀아서")는 사용자 본인의 말이라 감정 신호가 가장 직접적임.
    점수 = (1 - w) x 일기 점수 + w x 이유 점수. w는 .env KOBERT_WHY_WEIGHT (기본 0.4, 0이면 예전과 같음)
    리턴 형태는 analyze_emotion과 같음 (통계 파이프라인이 의존).
    """
    if why_weight is None:
        try:
            why_weight = float(os.environ.get("KOBERT_WHY_WEIGHT", "").strip() or 0.4)
        except ValueError:
            why_weight = 0.4
    why_weight = min(max(why_weight, 0.0), 1.0)
    base = analyze_emotion(diary_text)
    if not (why or "").strip() or why_weight <= 0 or not base.get("scores"):
        return base
    reason = analyze_emotion(why)
    keys = set(base["scores"]) | set(reason.get("scores") or {})
    scores = {k: (1 - why_weight) * base["scores"].get(k, 0.0) + why_weight * (reason.get("scores") or {}).get(k, 0.0)
              for k in keys}
    top_emotion = max(scores, key=scores.get)
    positive_sum = sum(v for k, v in scores.items() if get_valence(k) == "긍정감정")
    negative_sum = sum(v for k, v in scores.items() if get_valence(k) == "부정감정")
    return {"top_emotion": top_emotion, "scores": scores, "sentiment_score": round(positive_sum - negative_sum, 3)}
