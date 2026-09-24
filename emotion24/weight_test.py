"""
AI 감정 가중치 실험용 스크립트 (앱 frontend/backend 코드와 무관한 독립 테스트).

emotion24-bert가 뱉는 24개 감정 softmax 확률에, 퍼스널 검사(HSP/LOT-R) 기반 가중치를
곱해서 renormalize했을 때 top-1/top-3 결과가 어떻게 바뀌는지 확인한다.

가중치 규칙(채택된 모델: 2축 - 정서가 × 각성도):
- LOT-R(낙관성) 점수가 높을수록 "긍정" 정서가 그룹의 확률 배수를 키움
- HSP(민감성) 점수가 높을수록 "고각성"(화나는·불안한처럼 반응이 강한) 감정의 확률 배수를 키움
- 두 축을 곱해서 최종 배수를 만들기 때문에, 같은 긍/부정 그룹 안에서도 고각성/저각성 감정끼리
  서로 다르게 움직인다 (예: 화나는 vs 실망한).
  참고용으로 그룹(긍/부정)만 쓰는 1축 버전(build_weight_vector_1axis)도 남겨둠.

실행:
    ..\sentiment\venv\Scripts\python.exe weight_test.py
"""

import torch
from transformers import AutoTokenizer, BertForSequenceClassification
from emotion_list import ID_TO_EMOTION, EMOTION_LIST

MODEL_DIR = "model/emotion24-bert"
MAX_LEN = 64
DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")

# emotion_list.py의 EMOTION_LIST는 sorted()라서 원래 긍/부정 그룹 순서가 사라짐 ->
# 원본 정의(train.py 등에서 쓰던 분류)를 기준으로 여기서 다시 그룹을 명시.
POSITIVE_EMOTIONS = {
    "행복한", "기쁜", "기대되는", "설레는", "신나는", "열정적인",
    "즐거운", "상쾌한", "뿌듯한", "후련한", "감사한", "편안한",
}
NEGATIVE_EMOTIONS = {
    "우울한", "실망한", "후회되는", "슬픈", "두려운", "불안한",
    "막막한", "피곤한", "외로운", "지루한", "화나는", "짜증나는",
}
assert POSITIVE_EMOTIONS | NEGATIVE_EMOTIONS == set(EMOTION_LIST)

# --- 실험 2: 정서가(positive/negative) 축 + 각성도(arousal) 축을 분리한 2축 가중치 ---
# 심리학의 valence-arousal 모델을 참고: 감정을 "긍정/부정"뿐 아니라 "반응이 강한가/차분한가"로도 나눔.
# HIGH_AROUSAL: 화나는·불안한처럼 반응이 강하고 즉각적인 감정
# LOW_AROUSAL: 실망한·지루한처럼 반응이 잔잔하고 오래가는 감정
HIGH_AROUSAL_EMOTIONS = {
    "화나는", "짜증나는", "불안한", "두려운",          # 부정 + 고각성
    "신나는", "설레는", "열정적인", "기대되는", "즐거운",  # 긍정 + 고각성
}
LOW_AROUSAL_EMOTIONS = {
    "우울한", "실망한", "후회되는", "슬픈", "막막한", "피곤한", "외로운", "지루한",  # 부정 + 저각성
    "편안한", "감사한", "뿌듯한", "후련한", "행복한", "기쁜", "상쾌한",           # 긍정 + 저각성
}
assert HIGH_AROUSAL_EMOTIONS | LOW_AROUSAL_EMOTIONS == set(EMOTION_LIST)

# --- 실험 3: 이분법(고/저) 대신 24개 감정 각각에 연속값 각성도(0.0~1.0)를 부여 ---
# 0.5가 중립, 1.0에 가까울수록 반응이 강하고 즉각적, 0.0에 가까울수록 잔잔하고 오래가는 감정.
# (실제 심리학 척도의 정확한 수치가 아니라, 팀 논의를 위한 실험용 가설 순위임)
EMOTION_AROUSAL_LEVEL = {
    # 긍정
    "신나는": 0.95, "설레는": 0.90, "열정적인": 0.90,
    "기대되는": 0.75, "즐거운": 0.70,
    "행복한": 0.55, "기쁜": 0.55, "뿌듯한": 0.50,
    "후련한": 0.40, "감사한": 0.35, "상쾌한": 0.30, "편안한": 0.15,
    # 부정
    "화나는": 0.95, "불안한": 0.85, "두려운": 0.85, "짜증나는": 0.80,
    "막막한": 0.60, "슬픈": 0.50, "실망한": 0.45, "후회되는": 0.45,
    "우울한": 0.35, "외로운": 0.30, "피곤한": 0.15, "지루한": 0.15,
}
assert set(EMOTION_AROUSAL_LEVEL) == set(EMOTION_LIST)

# 가중치 강도: 점수 0~1 기준, score=0.5(중립)일 때 배수 1.0, score=1.0일 때 최대 배수
# CLI에서 --alpha로 덮어쓸 수 있도록 기본값만 유지 (0이면 가중치 없음, 값이 클수록 편향이 강해짐)
WEIGHT_ALPHA = 0.6


def build_weight_vector_1axis(hsp_score: float, lotr_score: float, alpha: float = WEIGHT_ALPHA) -> dict[str, float]:
    """참고/비교용 구버전: 긍정/부정 그룹에만 가중치를 준다 (그룹 내부 서열은 절대 안 바뀜)."""
    neg_multiplier = 1.0 + alpha * (hsp_score - 0.5) * 2
    pos_multiplier = 1.0 + alpha * (lotr_score - 0.5) * 2

    weights = {}
    for emotion in EMOTION_LIST:
        if emotion in POSITIVE_EMOTIONS:
            weights[emotion] = pos_multiplier
        else:
            weights[emotion] = neg_multiplier
    return weights


def build_weight_vector(hsp_score: float, lotr_score: float, alpha: float = WEIGHT_ALPHA) -> dict[str, float]:
    """
    채택된 모델: LOT-R는 정서가(긍정/부정), HSP는 각성도(강함/차분함) 축을 독립적으로 담당.
    같은 부정 그룹 안에서도 고각성(화나는)과 저각성(실망한)이 서로 다르게 움직인다.
    hsp_score, lotr_score는 0.0(낮음)~1.0(높음)로 정규화된 페르소나 점수.
    """
    valence_pos_mult = 1.0 + alpha * (lotr_score - 0.5) * 2
    valence_neg_mult = 2.0 - valence_pos_mult  # lotr_score 기준으로 대칭

    arousal_high_mult = 1.0 + alpha * (hsp_score - 0.5) * 2
    arousal_low_mult = 2.0 - arousal_high_mult  # hsp_score 기준으로 대칭

    weights = {}
    for emotion in EMOTION_LIST:
        valence_mult = valence_pos_mult if emotion in POSITIVE_EMOTIONS else valence_neg_mult
        arousal_mult = arousal_high_mult if emotion in HIGH_AROUSAL_EMOTIONS else arousal_low_mult
        weights[emotion] = valence_mult * arousal_mult
    return weights


def build_weight_vector_graded(hsp_score: float, lotr_score: float, alpha: float = WEIGHT_ALPHA) -> dict[str, float]:
    """
    실험 3: 각성도를 이분법(고/저)이 아니라 EMOTION_AROUSAL_LEVEL의 연속값(0~1)으로 반영.
    같은 "고각성" 버킷 안에 있던 화나는(0.95)/짜증나는(0.80)/불안한(0.85)도 이제 서로 다른 배수를 받는다.
    """
    valence_pos_mult = 1.0 + alpha * (lotr_score - 0.5) * 2
    valence_neg_mult = 2.0 - valence_pos_mult

    hsp_tilt = alpha * (hsp_score - 0.5) * 2  # -alpha ~ +alpha

    weights = {}
    for emotion in EMOTION_LIST:
        valence_mult = valence_pos_mult if emotion in POSITIVE_EMOTIONS else valence_neg_mult
        arousal_level = EMOTION_AROUSAL_LEVEL[emotion]  # 0.0~1.0
        arousal_mult = 1.0 + hsp_tilt * (arousal_level - 0.5) * 2  # arousal_level=0.5면 항상 1.0
        weights[emotion] = valence_mult * arousal_mult
    return weights


tokenizer = AutoTokenizer.from_pretrained(MODEL_DIR)
model = BertForSequenceClassification.from_pretrained(MODEL_DIR)
model.to(DEVICE)
model.eval()


def raw_probs(text: str):
    enc = tokenizer(text, truncation=True, max_length=MAX_LEN, padding="max_length", return_tensors="pt")
    enc = {k: v.to(DEVICE) for k, v in enc.items()}
    with torch.no_grad():
        logits = model(**enc).logits
        probs = torch.softmax(logits, dim=-1).cpu().numpy()[0]
    return probs


def apply_weight(probs, weight_vector: dict[str, float]):
    weighted = probs.copy()
    for idx, emotion in ID_TO_EMOTION.items():
        weighted[idx] *= weight_vector[emotion]
    weighted /= weighted.sum()  # renormalize
    return weighted


def topk(probs, k=3):
    top_ids = probs.argsort()[::-1][:k]
    return [(ID_TO_EMOTION[i], probs[i] * 100) for i in top_ids]


def format_topk(entries):
    return ", ".join(f"{e} {p:.1f}%" for e, p in entries)


# 2축 모델은 감정마다 배수가 최대 4종류(긍정+고각성/긍정+저각성/부정+고각성/부정+저각성)라
# 대표 감정 하나씩으로 각 배수를 보여준다.
REPRESENTATIVE_EMOTIONS = {
    "부정+고각성(화나는)": "화나는",
    "부정+저각성(실망한)": "실망한",
    "긍정+고각성(신나는)": "신나는",
    "긍정+저각성(편안한)": "편안한",
}


def format_multipliers(weight_vector: dict[str, float]) -> str:
    return ", ".join(f"{label}={weight_vector[emotion]:.2f}x" for label, emotion in REPRESENTATIVE_EMOTIONS.items())


# --- 실제 설문 응답(매우 그렇다~매우 아니다)에서 hsp_score/lotr_score를 계산 ---
# 응답을 -0.4~+0.4로 매핑한 뒤 "합계"가 아니라 "평균"을 내서, HSP(13문항)와 LOT-R(6문항)처럼
# 문항 수가 달라도 둘 다 항상 -0.4~+0.4 범위로 나오게 만든다(문항 수 차이로 인한 편향 제거).
ANSWER_SCORE_MAP = {
    "매우 그렇다": 0.4,
    "그렇다": 0.2,
    "보통이다": 0.0,
    "아니다": -0.2,
    "매우 아니다": -0.4,
}

HSP_QUESTION_COUNT = 13
LOTR_QUESTION_COUNT = 6
# LOT-R 문항은 1~6번 중 2/4/5번이 역채점(backend/app/personal_test_questions.py의 15/17/18번과 동일 문항)
LOTR_REVERSE_POSITIONS = {2, 4, 5}


def compute_persona_scores(hsp_answers: list[str], lotr_answers: list[str]) -> tuple[float, float]:
    """
    hsp_answers: HSP 1~13번 응답을 순서대로, 각 값은 ANSWER_SCORE_MAP의 키 중 하나
    lotr_answers: LOT-R 1~6번 응답을 순서대로 (2/4/5번 역채점은 이 함수에서 자동 반영)
    반환: (hsp_score, lotr_score) - 둘 다 0.0~1.0으로 정규화되어 build_weight_vector에 바로 사용 가능
    """
    if len(hsp_answers) != HSP_QUESTION_COUNT:
        raise ValueError(f"HSP는 {HSP_QUESTION_COUNT}문항이어야 합니다 (받은 개수: {len(hsp_answers)})")
    if len(lotr_answers) != LOTR_QUESTION_COUNT:
        raise ValueError(f"LOT-R은 {LOTR_QUESTION_COUNT}문항이어야 합니다 (받은 개수: {len(lotr_answers)})")

    hsp_avg = sum(ANSWER_SCORE_MAP[a] for a in hsp_answers) / HSP_QUESTION_COUNT

    lotr_signed = []
    for position, answer in enumerate(lotr_answers, start=1):
        raw = ANSWER_SCORE_MAP[answer]
        lotr_signed.append(-raw if position in LOTR_REVERSE_POSITIONS else raw)
    lotr_avg = sum(lotr_signed) / LOTR_QUESTION_COUNT

    # -0.4~+0.4 -> 0.0~1.0 (0.4는 매핑 최댓값, 0.5는 build_weight_vector의 중립점)
    hsp_score = hsp_avg / 0.8 + 0.5
    lotr_score = lotr_avg / 0.8 + 0.5
    return hsp_score, lotr_score


# 이전 대화에서 정의했던 4개 페르소나에 대응하는 (hsp_score, lotr_score) 조합
PERSONAS = {
    "섬세한 낙관가 (HSP↑ LOT-R↑)": (0.9, 0.9),
    "섬세한 걱정러 (HSP↑ LOT-R↓)": (0.9, 0.1),
    "단단한 낙관가 (HSP↓ LOT-R↑)": (0.1, 0.9),
    "단단한 현실주의자 (HSP↓ LOT-R↓)": (0.1, 0.1),
}

TEST_SENTENCES = [
    "오늘 발표가 드디어 끝나서 마음이 놓인다.",
    "친구가 약속을 어겨서 너무 화가 났다.",
    "혼자 자취방에 있으니 갑자기 쓸쓸해졌다.",
    "내일 시험 생각하니 손이 떨리고 초조하다.",
    "별거 없는 하루였다, 그냥 흘러갔다.",
]


def main():
    for text in TEST_SENTENCES:
        probs = raw_probs(text)
        print(f"\n문장: {text}")
        print(f"  [가중치 없음]        {format_topk(topk(probs))}")
        for persona_name, (hsp, lotr) in PERSONAS.items():
            weight_vector = build_weight_vector(hsp, lotr)
            weighted = apply_weight(probs, weight_vector)
            print(f"  [{persona_name}] {format_topk(topk(weighted))}")


# --- 팀 회의용: HSP:LOT-R 점수 비율을 0:1(=0:10) ~ 1:0(=10:0)까지 양끝 극단값 포함해서 스캔 ---
# ratio_hsp가 클수록 "민감형 쪽"(부정 감정 배수 ↑), ratio_lotr가 클수록 "낙관형 쪽"(긍정 감정 배수 ↑)
# 두 점수는 항상 합이 10이 되게(0:10, 1:9, ... 10:0) 잡아서, 한쪽으로 얼마나 치우쳤는지를 스캔한다.
RATIO_STEPS = [(r, 10 - r) for r in range(0, 11)]  # (hsp_tenths, lotr_tenths): (0,10) ~ (10,0)


def sweep_ratios(alpha: float = WEIGHT_ALPHA):
    print(f"\n{'=' * 60}\nWEIGHT_ALPHA = {alpha}\n{'=' * 60}")
    for text in TEST_SENTENCES:
        probs = raw_probs(text)
        base_top1 = topk(probs, k=1)[0]
        print(f"\n문장: {text}")
        print(f"  기준(가중치 없음): {base_top1[0]} {base_top1[1]:.1f}%")
        for hsp_tenths, lotr_tenths in RATIO_STEPS:
            hsp_score = hsp_tenths / 10
            lotr_score = lotr_tenths / 10
            weight_vector = build_weight_vector(hsp_score, lotr_score, alpha)
            weighted = apply_weight(probs, weight_vector)
            ratio_label = f"{hsp_tenths}:{lotr_tenths}"
            print(f"  비율 {ratio_label:<6} [{format_multipliers(weight_vector)}]")
            print(f"      -> {format_topk(topk(weighted))}")


# --- 실제 설문 응답 예시로 persona score 계산 -> 가중치 적용까지 확인 ---
# 가상의 두 사람: A는 HSP 문항에 "그렇다" 계열, LOT-R 문항에도 낙관적으로 응답
#                B는 HSP 문항에 "매우 그렇다" 계열(고민감), LOT-R은 비관적으로 응답
EXAMPLE_RESPONDENTS = {
    "응답자 A (약간 민감 + 약간 낙관)": {
        "hsp": ["그렇다"] * 13,
        "lotr": ["그렇다", "아니다", "그렇다", "아니다", "아니다", "그렇다"],
    },
    "응답자 B (매우 민감 + 매우 비관)": {
        "hsp": ["매우 그렇다"] * 13,
        "lotr": ["아니다", "매우 그렇다", "아니다", "매우 그렇다", "매우 그렇다", "아니다"],
    },
}


def persona_demo(alpha: float = WEIGHT_ALPHA):
    for name, answers in EXAMPLE_RESPONDENTS.items():
        hsp_score, lotr_score = compute_persona_scores(answers["hsp"], answers["lotr"])
        print(f"\n{name}")
        print(f"  hsp_score={hsp_score:.3f}, lotr_score={lotr_score:.3f} (alpha={alpha})")
        weight_vector = build_weight_vector(hsp_score, lotr_score, alpha)
        print(f"  [{format_multipliers(weight_vector)}]")
        for text in TEST_SENTENCES:
            probs = raw_probs(text)
            weighted = apply_weight(probs, weight_vector)
            print(f"    {text}")
            print(f"      가중치 없음: {format_topk(topk(probs))}")
            print(f"      가중치 적용: {format_topk(topk(weighted))}")


# --- 실험 2 비교용: 기존 1축(그룹 단위) vs 신규 2축(정서가+각성도) 방식 나란히 비교 ---
def compare_axis_models(alpha: float = WEIGHT_ALPHA):
    # 대비가 뚜렷하게 보이도록 양 극단 조합만 테스트
    combos = {
        "HSP↑(고각성 강조) LOT-R↓(부정 강조)": (0.9, 0.1),
        "HSP↓(저각성 강조) LOT-R↑(긍정 강조)": (0.1, 0.9),
    }
    for text in TEST_SENTENCES:
        probs = raw_probs(text)
        print(f"\n문장: {text}")
        print(f"  가중치 없음(1축/2축 공통 기준): {format_topk(topk(probs))}")
        for combo_name, (hsp, lotr) in combos.items():
            v1 = apply_weight(probs, build_weight_vector_1axis(hsp, lotr, alpha))
            v2 = apply_weight(probs, build_weight_vector(hsp, lotr, alpha))
            print(f"  [{combo_name}]")
            print(f"    1축(그룹만, 참고용):     {format_topk(topk(v1))}")
            print(f"    2축(정서가+각성도, 채택): {format_topk(topk(v2))}")


# --- 실험 3 비교용: 2축(고/저 이분법) vs 3(연속값 각성도) 나란히 비교 ---
def compare_graded_model(alpha: float = WEIGHT_ALPHA):
    combos = {
        "HSP↑(고각성 강조) LOT-R↓(부정 강조)": (0.9, 0.1),
        "HSP↓(저각성 강조) LOT-R↑(긍정 강조)": (0.1, 0.9),
    }
    for text in TEST_SENTENCES:
        probs = raw_probs(text)
        print(f"\n문장: {text}")
        print(f"  가중치 없음: {format_topk(topk(probs))}")
        for combo_name, (hsp, lotr) in combos.items():
            v2 = apply_weight(probs, build_weight_vector(hsp, lotr, alpha))
            v3 = apply_weight(probs, build_weight_vector_graded(hsp, lotr, alpha))
            print(f"  [{combo_name}]")
            print(f"    2축(고/저 이분법):     {format_topk(topk(v2))}")
            print(f"    3(연속값 각성도):      {format_topk(topk(v3))}")


if __name__ == "__main__":
    import sys

    args = sys.argv[1:]

    def parse_alphas(default):
        if "--alpha" in args:
            alpha_idx = args.index("--alpha")
            return [float(a) for a in args[alpha_idx + 1:] if not a.startswith("--")]
        return [default]

    if "--persona-demo" in args:
        for alpha in parse_alphas(WEIGHT_ALPHA):
            persona_demo(alpha)
    elif "--2axis-demo" in args:
        for alpha in parse_alphas(WEIGHT_ALPHA):
            compare_axis_models(alpha)
    elif "--graded-demo" in args:
        for alpha in parse_alphas(WEIGHT_ALPHA):
            compare_graded_model(alpha)
    elif "--sweep" in args:
        # --alpha 0.3 0.6 0.9 처럼 여러 값을 한 번에 비교 가능. 안 주면 기본값 하나만 실행.
        for alpha in parse_alphas(WEIGHT_ALPHA):
            sweep_ratios(alpha)
    else:
        main()
