from app.weight_algorithm import compute_persona_scores, build_weight_vector, apply_weight, ALPHA
from app.emotion_taxonomy import EMOTION_CATEGORIES


def test_alpha_is_confirmed_value():
    # 종현 설계 노트에서 확정된 값(2026-09-24). 바뀌면 팀 논의 후에만 바뀌어야 하므로 고정 검증.
    assert ALPHA == 0.4


def test_neutral_answers_give_neutral_scores():
    # 전부 "보통이다"(3점)로 응답하면 hsp_score/lotr_score 둘 다 0.5(중립)여야 함
    hsp_answers = [3] * 13
    lotr_answers = [3] * 6
    hsp_score, lotr_score = compute_persona_scores(hsp_answers, lotr_answers)
    assert hsp_score == 0.5
    assert lotr_score == 0.5


def test_neutral_persona_gives_no_weighting():
    # hsp_score=lotr_score=0.5(중립)면 모든 감정의 배수가 1.0이어야 함 (가중치 없음)
    weights = build_weight_vector(0.5, 0.5)
    assert all(abs(w - 1.0) < 1e-9 for w in weights.values())


def test_weight_vector_covers_all_24_emotions():
    weights = build_weight_vector(0.9, 0.1)
    assert set(weights.keys()) == set(EMOTION_CATEGORIES)


def test_high_hsp_low_lotr_favors_negative_high_arousal():
    # HSP 높음(민감) + LOT-R 낮음(비관) 조합이면, 부정+고각성 감정("화나는")이
    # 긍정+저각성 감정("편안한")보다 더 크게 부스트되어야 함
    weights = build_weight_vector(hsp_score=0.9, lotr_score=0.1)
    assert weights["화나는"] > weights["편안한"]


def test_apply_weight_renormalizes_to_1():
    scores = {emotion: 1.0 / len(EMOTION_CATEGORIES) for emotion in EMOTION_CATEGORIES}
    weights = build_weight_vector(0.9, 0.1)
    result = apply_weight(scores, weights)
    assert abs(sum(result.values()) - 1.0) < 1e-9


def test_lotr_reverse_scoring():
    # LOT-R 2/4/5번째 문항은 역채점이라, 거기만 "매우 그렇다"(5)를 줘도 비관 쪽으로 잡혀야 함
    # (2/4/5번째만 5점, 나머지는 중립 3점)
    lotr_answers = [3, 5, 3, 5, 5, 3]
    _, lotr_score = compute_persona_scores([3] * 13, lotr_answers)
    assert lotr_score < 0.5  # 역채점 문항에 "그렇다"를 강하게 답했으니 비관 쪽(0.5 미만)으로 나와야 함