import os
import re

MOCK_MODE = os.environ.get("MOCK_MODE", "false").lower() == "true"

SYSTEM_PREAMBLE = (
    "A chat between a curious user and an artificial intelligence assistant. "
    "The assistant는 20대 대학생 본인이다. 남한테 보여주려고 쓰는 게 아니라, "
    "그날 있었던 일을 그냥 편하게 적어두는 개인 일기를 쓴다.\n\n"
    "[무조건 지켜야 하는 필수 규칙]\n"
    "1. 말투: 반말로 쓴다. '~했다', '~하더라', '~잖아', '~하나' 등 자연스러운 반말 어미를 자유롭게 섞어 쓴다. "
    "(존댓말 '~했어요', '~습니다', '~네요'는 절대 쓰지 않는다)\n"
    "2. 절대 교훈으로 마무리하지 않는다: '~덕분에 힘이 났다', '~라는 걸 느꼈다', "
    "'정말 소중한 시간이었다', '앞으로 살아갈 힘이 됐다' 같은 감동적인 결론으로 끝내지 않는다. "
    "그냥 있었던 일을 담백하게 적고 끝내거나, 사소한 잡생각으로 끝나도 된다.\n"
    "3. 과한 비유 금지: '마법처럼', '별처럼 빛나는', '환상적인' 같은 문학적이고 꾸며진 표현을 쓰지 않는다.\n"
    "4. 문장 길이를 일부러 들쭉날쭉하게 쓴다.\n"
    "5. 근거 없는 디테일 금지: 글에 등장하는 모든 구체적인 내용(사람, 음식, 장소, 대화 주제, "
    "사건, 감정, 결과 등 전부)은 반드시 주어진 정보에서 나온 것이어야 한다. 입력에 없는 디테일이 "
    "필요한 순간이 오면, 절대 구체적으로 채워 넣지 말고 뭉뚱그려서 담백하게 넘어간다. "
    "예를 들어 무슨 얘기를 나눴는지 정보가 없으면 '취업 얘기를 했다'처럼 지어내지 말고 "
    "그냥 '이런저런 얘기를 나눴다' 정도로만 쓴다.\n"
    "6. 외래어 대신 순수 한국어를 쓴다.\n"
    "7. 분량은 90~120자 정도를 목표로 하되, 내용에 따라 자연스럽게 짧아지거나 길어져도 된다.\n"
    "8. '다행이다', '다행히' 같은 말을 습관적으로 쓰지 않는다. 한 일기 안에서 절대 두 번 이상 쓰지 않는다.\n"
)

FEWSHOT_EXAMPLES = (
    "Human: 다음 정보를 바탕으로 감성적인 일기를 작성해라:\n\n"
    "무엇을: 늦은 밤 혼자 동네 자전거 라이딩\n"
    "이유: 하루 종일 답답했던 마음을 시원한 밤바람으로 날려버리고 싶어서\n"
    "누구와: 혼자\n"
    "언제: 밤 11시\n"
    "어디서: 동네 하천변 자전거도로\n"
    "Assistant:\n"
    "하루 종일 답답해서 그냥 자전거 끌고 나왔다. 밤이라 그런지 하천변에 사람도 별로 없고 조용했다. "
    "한 바퀴 도는데 바람이 좀 차긴 했는데 그것도 나쁘지 않았다. 중간에 벤치에 앉아서 핸드폰도 안 보고 "
    "그냥 멍하니 있다가 왔다. 집에 오니까 좀 살 것 같아서 씻고 바로 잤다.\n\n"
    "Human: 다음 정보를 바탕으로 감성적인 일기를 작성해라:\n\n"
    "무엇을: 오랜만에 친구와 전화 통화\n"
    "이유: 요즘 서로 바빠서 연락이 뜸했는데, 오랜만에 목소리 들으니 반가워서\n"
    "누구와: 친구\n"
    "언제: 저녁 9시\n"
    "어디서: 자취방 침대 위\n"
    "Assistant:\n"
    "저녁 먹고 누워있는데 갑자기 걔한테 연락이 왔다. 뭐 하냐고 물어보길래 그냥 누워있다고 했더니 "
    "지도 똑같다면서 웃었다. 별 얘기도 안 했는데 이런저런 얘기하다 보니까 한 시간 넘게 통화했다. "
    "요즘 서로 사는 게 바빠서 이런 것도 오랜만이다.\n\n"
    "Human: 다음 정보를 바탕으로 감성적인 일기를 작성해라:\n\n"
    "무엇을: 주말에 본가 방문\n"
    "이유: 자취하느라 계속 대충 먹다가, 오랜만에 부모님이 해주시는 밥 먹고 싶어서\n"
    "누구와: 가족\n"
    "언제: 토요일 낮 12시\n"
    "어디서: 본가\n"
    "Assistant:\n"
    "토요일 아침에 짐 좀 챙겨서 본가로 내려갔다. 도착하니까 엄마가 벌써 점심 준비하고 계셨다. "
    "오랜만에 집밥 먹으니까 확실히 맛이 다르긴 다르더라. 아빠랑 티비 좀 보다가 저녁까지 먹고 자취방으로 올라왔다.\n\n"
    "Human: 다음 정보를 바탕으로 감성적인 일기를 작성해라:\n\n"
    "무엇을: 친구랑 카페에서 수다\n"
    "이유: 오랜만에 만나서 반가워서\n"
    "누구와: 친구\n"
    "언제: 저녁 7시\n"
    "어디서: 동네 카페\n"
    "Assistant:\n"
    "저녁 먹을 겸 동네 카페에서 오랜만에 걔를 만났다. 얼굴 본 지 꽤 됐다고 생각했는데 만나니까 "
    "또 어색함 하나 없이 계속 떠들었다. 무슨 얘기를 그렇게 했는지 시간 가는 줄도 몰랐다. "
    "이런 게 오랜 친구구나 싶었다.\n"
)

FORBIDDEN_PHRASES = (
    "도와드릴까요", "궁금하신", "다행이에요", "그러셨군요", "질문해주세요", "제가 그 자리에",
    "기억나?", "그치?", "그렇지?", "알지?", "그지?"
)

RELATION_KEYWORDS = (
    "형", "언니", "누나", "오빠", "동료", "남편", "아내", "여자친구", "남자친구",
    "선배", "후배", "교수님", "사수", "팀장", "과장", "사장"
)

IMPLIED_RELATION_TRIGGERS = {
    "상담": ["교수님"], "진로": ["교수님"], "지도교수": ["교수님"],
    "회식": ["동료", "선배", "후배", "팀장", "과장", "사장", "사수"],
    "출근": ["동료", "선배", "후배", "팀장", "과장", "사장", "사수"],
    "부서": ["동료", "선배", "후배", "팀장", "과장", "사장", "사수"],
    "회사": ["동료", "선배", "후배", "팀장", "과장", "사장", "사수"],
    "사수": ["사수", "선배"], "면접": ["면접관"],
}

CLICHE_PATTERNS = (
    "덕분에 힘", "덕분에 이겨", "앞으로 살아갈 힘", "정말 소중", "말로 표현할 수",
    "마음이 따뜻해지는 것을 느꼈다", "환상적이었다", "마법처럼", "별처럼 빛나",
    "행복이었다", "힐링이 되었다", "위로가 되었다"
)

FORMAL_ENDING_PATTERN = re.compile(r'(요|습니다|ㅂ니다)[.!?]?$')

MAX_RETRIES = 5


def expand_context(context_str: str) -> str:
    extra = []
    for trigger, implied_list in IMPLIED_RELATION_TRIGGERS.items():
        if trigger in context_str:
            extra.extend(implied_list)
    return context_str + " " + " ".join(extra)


def has_invented_relation(text: str, context_str: str):
    for kw in RELATION_KEYWORDS:
        if kw in text and kw not in context_str:
            return kw
    return None


def validate_diary(text: str, context_str: str = ""):
    text = text.strip()
    reasons = []

    if not text:
        return False, ["empty"], 0

    length_ok = 70 <= len(text) <= 165
    if not length_ok:
        reasons.append(f"길이={len(text)}자")

    sentences = [s for s in re.split(r'(?<=[.!?])\s+', text) if s.strip()]
    count_ok = 3 <= len(sentences) <= 5
    if not count_ok:
        reasons.append(f"문장수={len(sentences)}개")

    formal_ok = not any(FORMAL_ENDING_PATTERN.search(s.strip()) for s in sentences)
    if not formal_ok:
        reasons.append("해요체 섞임")

    phrase_ok = not any(p in text for p in FORBIDDEN_PHRASES)
    if not phrase_ok:
        reasons.append("금지 문구 포함")

    cliche_ok = not any(c in text for c in CLICHE_PATTERNS)
    if not cliche_ok:
        reasons.append("뻔한 마무리")

    dahaeng_ok = text.count("다행") <= 1
    if not dahaeng_ok:
        reasons.append("다행 중복")

    invented = has_invented_relation(text, context_str)
    relation_ok = invented is None
    if not relation_ok:
        reasons.append(f"관계 지어냄({invented})")

    checks = [length_ok, count_ok, formal_ok, phrase_ok, cliche_ok, dahaeng_ok, relation_ok]
    score = sum(checks)
    passed = all(checks)
    return passed, reasons, score


def build_prompt(actual_user_content: str) -> str:
    return (
        f"{SYSTEM_PREAMBLE}\n"
        f"{FEWSHOT_EXAMPLES}\n"
        f"Human: 다음 정보를 바탕으로 감성적인 일기를 작성해라:\n\n{actual_user_content}\n"
        f"Assistant:\n"
    )


def _generate_once(prompt_str: str, temperature: float) -> str:
    # 여기서만 torch/모델 로더를 불러옴 (MOCK_MODE면 이 함수 자체가 안 불림)
    import torch
    from app.models.llama_loader import get_model_and_tokenizer

    model, tokenizer = get_model_and_tokenizer()
    input_ids = tokenizer(prompt_str, return_tensors="pt")["input_ids"].to(model.device)
    with torch.no_grad():
        outputs = model.generate(
            input_ids=input_ids,
            max_new_tokens=220,
            do_sample=True,
            temperature=temperature,
            top_p=0.9,
            repetition_penalty=1.2,
            eos_token_id=tokenizer.eos_token_id,
            tokenizer=tokenizer,
            stop_strings=["\nHuman:", "Human:", "무엇을:"]
        )
    generated_text = tokenizer.decode(outputs[0][input_ids.shape[-1]:], skip_special_tokens=True)
    return generated_text.split("Human:")[0].strip()


def _mock_generate(what: str) -> str:
    return f"오늘은 {what} 관련된 하루였다. 이건 목(mock) 응답이라 실제 생성된 건 아니다. 그래도 API 흐름 테스트용으로는 충분하다."


def generate_diary_text(what: str, why: str, who, when: str, where: str):
    who_str = ", ".join(who) if isinstance(who, list) else who

    if MOCK_MODE:
        return _mock_generate(what), False

    actual_user_content = f"무엇을: {what}\n이유: {why}\n누구와: {who_str}\n언제: {when}\n어디서: {where}"
    prompt_str = build_prompt(actual_user_content)
    context_str = expand_context(f"{who_str} {what} {why}")

    clean_diary = ""
    best_candidate = ""
    best_score = -1
    passed = False

    for attempt in range(1, MAX_RETRIES + 1):
        temp = max(0.35, 0.75 - (attempt - 1) * 0.1)
        candidate = _generate_once(prompt_str, temperature=temp)
        is_ok, reasons, score = validate_diary(candidate, context_str=context_str)

        if score > best_score:
            best_score = score
            best_candidate = candidate

        if is_ok:
            clean_diary = candidate
            passed = True
            break

    if not passed:
        clean_diary = best_candidate

    return clean_diary, not passed