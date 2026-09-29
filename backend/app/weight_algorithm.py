"""
app/weight_algorithm.py
퍼스널 검사(HSP/LOT-R) 기반 감정 가중치 알고리즘 (종현 설계, 2026-09-24 확정).

채택 모델: 정서가(LOT-R) x 연속값 각성도(HSP, 24개 감정 개별 값)
alpha = 0.4 로 고정 (설계 노트에서 수학적으로 검증됨, 이 값을 바꾸려면
종현/재유랑 먼저 상의할 것 - 코드 여기저기 흩어져있지 않게 이 파일에만 있음)

긍정/부정 분류, 24개 감정 목록은 emotion_taxonomy.py를 그대로 재사용해서
(중복 정의 안 함) 감정 체계가 나중에 바뀌어도 여기가 안 어긋나게 함.
"""
from typing import Dict, List, Tuple

from app.emotion_taxonomy import EMOTION_CATEGORIES, get_valence

ALPHA = 0.4  # 확정 파라미터, 임의로 바꾸지 말 것

# 1.0에 가까울수록 반응이 강하고 즉각적, 0.0에 가까울수록 잔잔하고 오래감. 0.5는 중립.
# (종현 실험 스크립트의 EMOTION_AROUSAL_LEVEL 그대로, 정확한 수치는 가설값이지만
#  순서/방향성은 박인조·민경환(2005) 논문으로 부분 검증됨)
EMOTION_AROUSAL_LEVEL = {
    "신나는": 0.95, "설레는": 0.90, "열정적인": 0.90,
    "기대되는": 0.75, "즐거운": 0.70,
    "행복한": 0.55, "기쁜": 0.55, "뿌듯한": 0.50,
    "후련한": 0.40, "감사한": 0.35, "상쾌한": 0.30, "편안한": 0.15,
    "화나는": 0.95, "불안한": 0.85, "두려운": 0.85, "짜증나는": 0.80,
    "막막한": 0.60, "슬픈": 0.50, "실망한": 0.45, "후회되는": 0.45,
    "우울한": 0.35, "외로운": 0.30, "피곤한": 0.15, "지루한": 0.15,
}
assert set(EMOTION_AROUSAL_LEVEL) == set(EMOTION_CATEGORIES), (
    "EMOTION_AROUSAL_LEVEL이 emotion_taxonomy.EMOTION_CATEGORIES(24개)랑 안 맞음"
)

# HSP 13문항 + LOT-R 6문항, 1~5점 척도 (1=매우 아니다 ~ 5=매우 그렇다)
HSP_QUESTION_COUNT = 13
LOTR_QUESTION_COUNT = 6
# LOT-R 6문항 중 2/4/5번째가 역채점 (personal_test_questions.py의 id 15/17/18과 동일 문항)
LOTR_REVERSE_POSITIONS = {2, 4, 5}


def _answer_to_score(answer: int) -> float:
    """1~5점 응답 -> -0.4~+0.4 (종현 스크립트의 "매우 그렇다"=0.4 등과 수학적으로 동일)."""
    return (answer - 3) * 0.2


def compute_persona_scores(hsp_answers: List[int], lotr_answers: List[int]) -> Tuple[float, float]:
    """
    hsp_answers: HSP 1~13번 응답을 순서대로(1~5점)
    lotr_answers: LOT-R 1~6번 응답을 순서대로(1~5점), 2/4/5번째는 이 함수 안에서 자동 역채점
    반환: (hsp_score, lotr_score) - 둘 다 0.0~1.0으로 정규화됨
    """
    if len(hsp_answers) != HSP_QUESTION_COUNT:
        raise ValueError(f"HSP는 {HSP_QUESTION_COUNT}문항이어야 합니다 (받은 개수: {len(hsp_answers)})")
    if len(lotr_answers) != LOTR_QUESTION_COUNT:
        raise ValueError(f"LOT-R은 {LOTR_QUESTION_COUNT}문항이어야 합니다 (받은 개수: {len(lotr_answers)})")

    hsp_avg = sum(_answer_to_score(a) for a in hsp_answers) / HSP_QUESTION_COUNT

    lotr_signed = []
    for position, answer in enumerate(lotr_answers, start=1):
        raw = _answer_to_score(answer)
        lotr_signed.append(-raw if position in LOTR_REVERSE_POSITIONS else raw)
    lotr_avg = sum(lotr_signed) / LOTR_QUESTION_COUNT

    hsp_score = hsp_avg / 0.8 + 0.5
    lotr_score = lotr_avg / 0.8 + 0.5
    return hsp_score, lotr_score


def build_weight_vector(hsp_score: float, lotr_score: float, alpha: float = ALPHA) -> Dict[str, float]:
    """채택 모델(3, 연속값 각성도): 24개 감정 각각에 서로 다른 배수를 만든다."""
    valence_pos_mult = 1.0 + alpha * (lotr_score - 0.5) * 2
    valence_neg_mult = 2.0 - valence_pos_mult

    hsp_tilt = alpha * (hsp_score - 0.5) * 2

    weights = {}
    for emotion in EMOTION_CATEGORIES:
        valence_mult = valence_pos_mult if get_valence(emotion) == "긍정감정" else valence_neg_mult
        arousal_level = EMOTION_AROUSAL_LEVEL[emotion]
        arousal_mult = 1.0 + hsp_tilt * (arousal_level - 0.5) * 2
        weights[emotion] = valence_mult * arousal_mult
    return weights


def apply_weight(emotion_scores: Dict[str, float], weight_vector: Dict[str, float]) -> Dict[str, float]:
    """KoBERT가 뽑은 24개 감정 확률에 가중치를 곱하고 renormalize."""
    weighted = {}
    for emotion, score in emotion_scores.items():
        weighted[emotion] = score * weight_vector.get(emotion, 1.0)

    total = sum(weighted.values())
    if total <= 0:
        return emotion_scores  # 방어적 처리 - 전부 0이면 원본 그대로

    return {emotion: value / total for emotion, value in weighted.items()}