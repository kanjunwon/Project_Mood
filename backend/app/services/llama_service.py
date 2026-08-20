import os
import re

MOCK_MODE = os.environ.get("MOCK_MODE", "false").lower() == "true"

SYSTEM_PREAMBLE = (
    "A chat between a curious user and an artificial intelligence assistant. "
    "The assistant는 20대 대학생 본인이다. 그날 있었던 일을 그냥 편하게 적어두는 개인 일기를 쓴다.\n\n"
    "[가장 중요한 전제]\n"
    "너는 아래 다섯 가지 정보(무엇을, 이유, 누구와, 언제, 어디서) 외에는 그날 무슨 일이 "
    "있었는지 모른다.\n\n"
    "[규칙]\n"
    "1. 반말 일기체로 쓴다. '~했다', '~하더라', '~잖아', '~하나' 등 자연스러운 어미를 "
    "섞어 쓴다. 존댓말은 절대 쓰지 않는다.\n"
    "2. 담백하게 쓴다: 교훈적으로 정리하거나 요약하며 끝내지 않는다 ('~덕분에', '~을 선사했다', "
    "'~라는 걸 느꼈다', '최고의 하루였다', '완벽한 하루였다' 같은 문장으로 마무리하지 않는다). "
    "과장된 비유도 쓰지 않는다 ('마법처럼', '환상적인', '하늘을 날아갈 것 같았다', "
    "'세상을 다 가진 기분' 등). 그냥 있었던 일 적고 끝내거나 사소한 잡생각으로 "
    "끝나도 된다.\n"
    "3. 문장 길이를 들쭉날쭉하게 쓴다. 짧게 끊는 문장과 길게 이어지는 문장을 섞는다.\n"
    "4. 분량은 정해진 게 없다. 정보가 적으면 2~3문장으로 짧게 끝나도 전혀 상관없다.\n"
    "5. 디테일을 채울 땐 위험도를 구분해서 판단해라:\n"
    "   - 괜찮음: 그 장소/상황에서 흔히 있는 배경 묘사 (예: 공원이면 사람들, 생일이면 케이크 정도의 "
    "일반적인 소품) - 이 정도는 자연스러움을 위해 살짝 곁들여도 된다.\n"
    "   - 절대 금지: 확인할 수 없는 결과나 판단(예: '시험을 잘 봤다', '다들 좋아했다'), 구체적인 "
    "대화 내용, 술, 정확한 식사 시간대(아침/점심/저녁) - 이런 건 틀렸을 때 완전히 어색해지는 "
    "내용이라 무슨 일이 있어도 지어내면 안 된다. 애매하게 돌려 말해라.\n"
    "6. '다행이다/다행히'는 한 번 이상 쓰지 않는다.\n"
    "7. 외래어 대신 순수 한국어를 쓴다.\n"
    "8. '어디서' 정보를 그대로 따른다: '친구네 집'이면 내가 친구 집에 간 것이고, '본가'면 "
    "내가 부모님 댁에 간 것이다. 절대 방향을 반대로 바꿔서 '친구가 우리 집에 왔다'처럼 "
    "쓰지 않는다.\n"
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
    "저녁에 동네 카페에서 오랜만에 걔를 만났다. 얼굴 본 지 꽤 됐는데 만나니까 어색함 하나 없었다. "
    "몇 시간을 떠들었는지도 모르겠다. 다음에 또 이렇게 보자고 하고 헤어졌다.\n\n"
    "Human: 다음 정보를 바탕으로 감성적인 일기를 작성해라:\n\n"
    "무엇을: 친구 생일 축하\n"
    "이유: 친한 친구 생일이라 챙겨주고 싶어서\n"
    "누구와: 친구\n"
    "언제: 저녁\n"
    "어디서: 친구네 집\n"
    "Assistant:\n"
    "친구 생일이라고 해서 저녁에 걔네 집으로 갔다. 다른 애들도 몇 명 와있었다. 다 같이 앉아서 "
    "이런저런 얘기 나누다 보니 시간 가는 줄 몰랐다. 늦게까지 있다가 집으로 왔다.\n"
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

ALCOHOL_KEYWORDS = ("소주", "맥주", "막걸리", "와인", "폭탄주", "술")
MEALTIME_KEYWORDS = ("아침", "점심", "저녁", "새벽")

# "술", "형", "과장" 같은 짧은 키워드는 무관한 흔한 단어에도 다 포함돼서 오탐지가 잦음
# (미술관, 인형, 과장해서 등) - 검사 전에 이런 단어들을 먼저 지워버리고 나서 진짜 매칭 확인
FALSE_POSITIVE_EXCLUSIONS = {
    "술": ["미술", "기술", "예술", "수술", "무술", "마술", "서술", "저술", "시술", "학술", "진술", "예술적", "미술관", "기술적"],
    "형": ["인형", "모형", "유형", "형식", "형태", "전형", "변형", "원형", "지형", "체형", "선형", "도형", "균형", "조형", "정형외과", "삼각형", "사각형"],
    "과장": ["과장해서", "과장이", "과장된", "좀 과장", "너무 과장", "과장해", "과장하면", "과장인가"],
}


def _mask_false_positives(text: str, keyword: str) -> str:
    masked = text
    for fp in FALSE_POSITIVE_EXCLUSIONS.get(keyword, []):
        masked = masked.replace(fp, "")
    return masked

CLICHE_PATTERNS = (
    "덕분에 힘", "덕분에 이겨", "앞으로 살아갈 힘", "정말 소중", "말로 표현할 수",
    "마음이 따뜻해지는 것을 느꼈다", "환상적이었다", "마법처럼", "별처럼 빛나",
    "행복이었다", "힐링이 되었다", "위로가 되었다", "선사", "느꼈다는 걸", "라는 걸 느꼈다",
    "최고의 하루", "최고의 순간", "잊지 못할", "평생 기억", "완벽한 하루",
    "날아갈 것", "날아갈 듯", "터질 것 같았다", "구름 위", "세상을 다 가진",
)

FORMAL_ENDING_PATTERN = re.compile(r'(요|습니다|ㅂ니다)[.!?]?$')

MAX_RETRIES = 3  # 전시 당일 응답 속도 고려해서 5->3으로 낮춤 (대부분 1~2번 안에 통과하는 걸 확인함)


def expand_context(context_str: str) -> str:
    extra = []
    for trigger, implied_list in IMPLIED_RELATION_TRIGGERS.items():
        if trigger in context_str:
            extra.extend(implied_list)
    return context_str + " " + " ".join(extra)


def has_invented_word(text: str, context_str: str, keyword_list) -> str | None:
    for kw in keyword_list:
        masked_text = _mask_false_positives(text, kw)
        if kw in masked_text and kw not in context_str:
            return kw
    return None


def validate_diary(text: str, context_str: str = ""):
    text = text.strip()
    reasons = []

    if not text:
        return False, ["empty"], 0

    length_ok = 40 <= len(text) <= 200
    if not length_ok:
        reasons.append(f"길이={len(text)}자")

    sentences = [s for s in re.split(r'(?<=[.!?])\s+', text) if s.strip()]
    count_ok = 2 <= len(sentences) <= 6
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

    invented = has_invented_word(text, context_str, RELATION_KEYWORDS)
    relation_ok = invented is None
    if not relation_ok:
        reasons.append(f"관계 지어냄({invented})")

    invented_alcohol = has_invented_word(text, context_str, ALCOHOL_KEYWORDS)
    alcohol_ok = invented_alcohol is None
    if not alcohol_ok:
        reasons.append(f"술 지어냄({invented_alcohol})")

    invented_meal = has_invented_word(text, context_str, MEALTIME_KEYWORDS)
    meal_ok = invented_meal is None
    if not meal_ok:
        reasons.append(f"식사시간대 지어냄({invented_meal})")

    checks = [length_ok, count_ok, formal_ok, phrase_ok, cliche_ok, dahaeng_ok, relation_ok, alcohol_ok, meal_ok]
    score = sum(checks)
    passed = all(checks)
    return passed, reasons, score


def build_restate_prompt(actual_user_content: str) -> str:
    # 1단계: 본격적으로 쓰기 전에, 주어진 사실만 담백하게 한 번 되짚게 함
    # (모델이 "지금 내가 아는 건 딱 이것뿐"이라는 상태로 다음 단계를 시작하게 유도)
    return (
        "A chat between a curious user and an artificial intelligence assistant.\n\n"
        "Human: 아래 정보를 있는 그대로, 한 문장으로만 요약해라. 추측이나 새로운 내용은 "
        f"절대 덧붙이지 마라.\n\n{actual_user_content}\n"
        "Assistant:\n"
    )


def build_prompt(actual_user_content: str, restated_facts: str = "") -> str:
    reminder = f"\n(방금 확인한 사실: {restated_facts})" if restated_facts else ""
    return (
        f"{SYSTEM_PREAMBLE}\n"
        f"{FEWSHOT_EXAMPLES}\n"
        f"Human: 다음 정보를 바탕으로 감성적인 일기를 작성해라 "
        f"(정보에 없는 음식/음료/시간/대화내용/결과 판단은 절대 지어내지 말 것):\n\n"
        f"{actual_user_content}{reminder}\n"
        f"Assistant:\n"
    )


def _generate_once(prompt_str: str, temperature: float, max_new_tokens: int = 220) -> str:
    import torch
    from app.models.llama_loader import get_model_and_tokenizer

    model, tokenizer = get_model_and_tokenizer()
    input_ids = tokenizer(prompt_str, return_tensors="pt")["input_ids"].to(model.device)
    with torch.no_grad():
        outputs = model.generate(
            input_ids=input_ids,
            max_new_tokens=max_new_tokens,
            do_sample=True,
            temperature=temperature,
            top_p=0.85,  # 0.9 -> 0.85로 낮춰서 극단적으로 튀는 단어 선택 확률 축소
            repetition_penalty=1.2,
            eos_token_id=tokenizer.eos_token_id,
            tokenizer=tokenizer,
            stop_strings=["\nHuman:", "Human:", "무엇을:"]
        )
    generated_text = tokenizer.decode(outputs[0][input_ids.shape[-1]:], skip_special_tokens=True)
    return generated_text.split("Human:")[0].strip()


def _mock_generate(what: str) -> str:
    return f"오늘은 {what} 관련된 하루였다. 이건 목(mock) 응답이라 실제 생성된 건 아니다. 그래도 API 흐름 테스트용으로는 충분하다."


def _safe_fallback_diary(what: str, why: str, who_str: str, when: str, where: str) -> str:
    return f"오늘은 {where}에서 {what}. {why}. 그런 하루였다."


def generate_diary_text(what: str, why: str, who, when: str, where: str):
    who_str = ", ".join(who) if isinstance(who, list) else who

    if MOCK_MODE:
        return _mock_generate(what), False

    actual_user_content = f"무엇을: {what}\n이유: {why}\n누구와: {who_str}\n언제: {when}\n어디서: {where}"

    # 1단계: 사실 되짚기 (낮은 온도로, 짧게)
    restate_prompt = build_restate_prompt(actual_user_content)
    restated_facts = _generate_once(restate_prompt, temperature=0.2, max_new_tokens=100)

    prompt_str = build_prompt(actual_user_content, restated_facts=restated_facts)
    context_str = expand_context(f"{who_str} {what} {why} {when} {where}")

    clean_diary = ""
    best_candidate = ""
    best_score = -1
    passed = False

    for attempt in range(1, MAX_RETRIES + 1):
        temp = max(0.15, 0.45 - (attempt - 1) * 0.15)
        candidate = _generate_once(prompt_str, temperature=temp)
        is_ok, reasons, score = validate_diary(candidate, context_str=context_str)

        if score > best_score:
            best_score = score
            best_candidate = candidate

        if is_ok:
            clean_diary = candidate
            passed = True
            print(f"  {attempt}번째 시도에서 통과")
            break
        else:
            print(f"  {attempt}번째 시도 불합격 ({', '.join(reasons)}): {candidate[:60]}...")

    if not passed:
        print(f"  경고: {MAX_RETRIES}번 다 실패, 안전 템플릿으로 대체함 (최선 후보 점수 {best_score}/9)")
        clean_diary = _safe_fallback_diary(what, why, who_str, when, where)

    return clean_diary, not passed