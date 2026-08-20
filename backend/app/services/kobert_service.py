import os

from app.emotion_taxonomy import get_valence
from app.emotion_list import ID_TO_EMOTION  # 종현이가 준 파일 - 모델 출력 순서(가나다순) 그대로 유지해야 함

MOCK_MODE = os.environ.get("MOCK_MODE", "false").lower() == "true"


def _mock_analyze() -> dict:
    return {
        "top_emotion": "평온",
        "scores": {"편안한": 1.0},
        "sentiment_score": 0.3,
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