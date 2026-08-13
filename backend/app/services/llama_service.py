import os
import re

MOCK_MODE = os.environ.get("MOCK_MODE", "false").lower() == "true"

SYSTEM_PREAMBLE = (
    "A chat between a curious user and an artificial intelligence assistant. "
    "The assistant는 20대 대학생 본인이다. 그날 있었던 일을 그냥 편하게 적어두는 개인 일기를 쓴다.\n\n"
    "[가장 중요한 전제]\n"
    "너는 아래 다섯 가지 정보(무엇을, 이유, 누구와, 언제, 어디서) 외에는 그날 무슨 일이 "
    "있었는지 전혀 모른다. 무슨 음식을 먹었는지, 무슨 얘기를 나눴는지, 정확히 몇 시에 "
    "뭘 했는지 같은 세부사항은 너에게 안 알려져 있다. 모르는 건 모르는 대로 뭉뚱그려서 "
    "써라 - 아는 척하며 구체적으로 채워 넣지 마라.\n\n"
    "[규칙]\n"
    "1. 반말 일기체로 쓴다. '~했다', '~하더라', '~잖아', '~하나' 등 자연스러운 어미를 "
    "섞어 쓴다. 존댓말은 절대 쓰지 않는다.\n"
    "2. 담백하게 쓴다: 교훈적으로 정리하거나 요약하며 끝내지 않는다 ('~덕분에', '~을 선사했다', "
    "'~라는 걸 느꼈다', '최고의 하루였다', '완벽한 하루였다' 같은 문장으로 마무리하지 않는다). "
    "과장된 비유도 쓰지 않는다 ('마법처럼', '환상적인', '하늘을 날아갈 것 같았다', "
    "'세상을 다 가진 기분' 등). 그냥 있었던 일 적고 끝내거나 사소한 잡생각으로 "
    "끝나도 된다.\n"
    "3. 문장 길이를 들쭉날쭉하게 쓴다. 짧게 끊는 문장과 길게 이어지는 문장을 섞는다.\n"
    "4. 분량은 정해진 게 없다. 줄 정보가 많으면 4~5문장도 되고, 정보가 적으면 "
    "2~3문장으로 짧게 끝나도 전혀 상관없다. 분량을 채우려고 없는 내용을 "
    "지어내는 것보다는 짧은 게 훨씬 낫다.\n"
    "5. '다행이다/다행히'는 한 번 이상 쓰지 않는다.\n"
    "6. 외래어 대신 순수 한국어를 쓴다.\n\n"
    "[쓰기 전에 마지막으로 확인]\n"
    "지금 쓰려는 문장에 위 다섯 가지 정보에 없는 음식 이름, 대화 내용, 시간, 장소 "
    "디테일이 들어가려고 하면, 그 부분을 빼고 애매하게 돌려 말해라.\n\n"
    "[다시 한번 강조]\n"
    "음식, 음료, 술, 정확한 시간대, 대화 내용 - 이런 건 절대로 지어내면 안 된다. "
    "다섯 가지 정보에 문자 그대로 나와있지 않으면 존재하지 않는 것으로 취급해라.\n"
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
    "몇 시간을 떠들었는지도 모르겠다. 다음에 또 이렇게 보자고 하고 헤어졌다.\n"
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

# '~덕분에', '~을 선사했다' 계열 교훈형 마무리 + '최고의 하루' 같은 요약형 마무리 +
# '하늘을 나는 것 같았다' 같은 과장 비유까지 걸러냄
CLICHE_PATTERNS = (
    "덕분에 힘", "덕분에 이겨", "앞으로 살아갈 힘", "정말 소중", "말로 표현할 수",
    "마음이 따뜻해지는 것을 느꼈다", "환상적이었다", "마법처럼", "별처럼 빛나",
    "행복이었다", "힐링이 되었다", "위로가 되었다", "선사", "느꼈다는 걸", "라는 걸 느꼈다",
    # 요약형 마무리 ("진짜 최고의 하루를 보낸 기분이었다" 같은 패턴)
    "최고의 하루", "최고의 순간", "잊지 못할", "평생 기억", "완벽한 하루",
    # 과장된 신체 비유 ("하늘 위로 날아갈 것 같았다" 같은 패턴)
    "날아갈 것", "날아갈 듯", "터질 것 같았다", "구름 위", "세상을 다 가진",
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

    # 분량을 유연하게 풀었으니, 검증도 너무 짧거나(내용 없음) 너무 길면(폭주)만 걸러냄
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
        f"Human: 다음 정보를 바탕으로 감성적인 일기를 작성해라 "
        f"(정보에 없는 음식/음료/시간/대화내용은 절대 지어내지 말 것):\n\n{actual_user_content}\n"
        f"Assistant:\n"
    )


def _generate_once(prompt_str: str, temperature: float) -> str:
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


def _safe_fallback_diary(what: str, why: str, who_str: str, when: str, where: str) -> str:
    # 5번 재시도해도 검증을 통과 못 하면, 모델이 만든 문장(지어낸 내용 남아있을 위험) 대신
    # 입력 필드를 그대로 조합한 100% 안전한 문장으로 대체함.
    # 문학적이진 않지만, 전시회에서 이상한 내용이 나올 위험은 완전히 없앰.
    return f"오늘은 {where}에서 {what}. {why}. 그런 하루였다."


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
        # 안전 최우선이라 temperature를 낮게 시작해서, 재시도할수록 더 보수적으로
        temp = max(0.15, 0.45 - (attempt - 1) * 0.08)
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
        print(f"  경고: {MAX_RETRIES}번 다 실패, {best_score}/7 기준 통과한 후보로 저장됨")

    if not passed:
        print(f"  경고: {MAX_RETRIES}번 다 실패, 안전 템플릿으로 대체함 (최선 후보 점수 {best_score}/7)")
        clean_diary = _safe_fallback_diary(what, why, who_str, when, where)

    return clean_diary, not passed