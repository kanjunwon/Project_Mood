import os

os.environ["MOCK_MODE"] = "true"  # 테스트는 항상 mock 모드로 (GPU 필요 없게)

import pytest

from app.services import llama_service as ls

GOOD = "주말에 카페에 가서 과제를 했다. 창가 자리에 앉아서 노트북을 켰다. 생각보다 오래 걸렸지만 다 끝내고 나왔다."
WITH_ALCOHOL = "친구랑 노래방에 갔다. 끝나고 맥주도 한잔 했다. 늦게 들어왔다."


@pytest.fixture
def fake_llm(monkeypatch):
    outputs = []
    calls = []

    def fake(prompt_str, temperature, max_new_tokens=220, do_sample=True, extra_stop_strings=None, stats=None,
             no_repeat_ngram_size=0, bad_words=None):
        calls.append({"prompt": prompt_str, "temperature": temperature,
                      "no_repeat_ngram_size": no_repeat_ngram_size, "bad_words": bad_words})
        if stats is not None:
            stats.update(input_tokens=1500, output_tokens=120, tokens_per_sec=18.0, hit_max_new_tokens=False)
        return outputs.pop(0)

    monkeypatch.setattr(ls, "MOCK_MODE", False)
    monkeypatch.setattr(ls, "_generate_once", fake)
    return outputs, calls


def _gen(timings):
    return ls.generate_diary_text("과제", "마감이라", "혼자", "10월 4일 토요일 오후 2시", "카페", timings=timings)


def test_attempt_details_recorded_with_reasons(fake_llm):
    outputs, calls = fake_llm
    outputs.extend([WITH_ALCOHOL, GOOD])
    timings = {}
    text, failed = _gen(timings)
    assert text == GOOD and failed is False
    details = timings["diary_attempt_details"]
    assert [d["passed"] for d in details] == [False, True]
    assert any("술 지어냄" in r for r in details[0]["reasons"])
    assert details[0]["output_tokens"] == 120 and details[0]["tokens_per_sec"] == 18.0
    assert details[0]["text"] == WITH_ALCOHOL
    assert timings["diary_attempts"] == 2 and timings["diary_fallback"] is False
    assert [c["temperature"] for c in calls] == pytest.approx([0.45, 0.55])  # patch 13: 0.45부터 조금씩 올림
    assert calls[0]["no_repeat_ngram_size"] == 4
    assert "맥주" in calls[0]["bad_words"] and "아침" in calls[0]["bad_words"]


def test_fallback_after_three_failures_is_recorded(fake_llm):
    outputs, calls = fake_llm
    outputs.extend([WITH_ALCOHOL] * 3)
    timings = {}
    text, failed = _gen(timings)
    assert failed is True
    assert text == ls._safe_fallback_diary("과제", "마감이라", "혼자", "10월 4일 토요일 오후 2시", "카페")
    assert timings["diary_fallback"] is True and len(timings["diary_attempt_details"]) == 3


def test_timings_optional(fake_llm):
    outputs, _ = fake_llm
    outputs.append(GOOD)
    assert _gen(None) == (GOOD, False)


# ---------- 프롬프트 변형 ----------
import hashlib

# main(b266c31)의 SYSTEM_PREAMBLE + FEWSHOT_EXAMPLES sha256. 기본 프롬프트가 바뀌면 실패해야 함.
MAIN_PROMPT_SHA256 = "c7a1071a5e05de2049305a92a3d26ae7e2dc287f33a72bc24ec8a8a02432b1a1"
CONTENT = "무엇을: X\n이유: Y\n누구와: 혼자\n언제: 오후 2시\n어디서: 집"


def test_default_prompt_unchanged_from_main():
    assert hashlib.sha256((ls.SYSTEM_PREAMBLE + ls.FEWSHOT_EXAMPLES).encode()).hexdigest() == MAIN_PROMPT_SHA256
    # patch 12: 기본 변형은 app_style (base/fewshot_no_mealtime은 측정·되돌리기용으로 그대로 남김)
    assert ls.build_prompt(CONTENT) == ls.build_prompt(CONTENT, "app_style")
    assert ls.build_prompt(CONTENT).startswith(ls.SYSTEM_PREAMBLE_APP + "\n" + ls.FEWSHOT_APP_STYLE)


def test_emotion_word_variant_changes_only_rule2_tail():
    base, variant = ls.SYSTEM_PREAMBLE, ls.SYSTEM_PREAMBLE_EMOTION_WORD
    assert base != variant
    # 규칙 2번의 교훈형/과장형 금지 문구는 그대로 남아 있어야 함
    for phrase in ("교훈적으로 정리하거나", "'최고의 하루였다'", "과장된 비유도 쓰지 않는다", "'마법처럼'"):
        assert phrase in variant
    assert "'재밌었다'" in variant and "'답답했다'" in variant
    # 바뀐 건 규칙 2번 마지막 문장 하나뿐 (다른 줄은 동일)
    diff = [(a, b) for a, b in zip(base.split("\n"), variant.split("\n")) if a != b]
    assert len(diff) == 1 and diff[0][0].startswith("2. 담백하게")
    assert ls.build_prompt(CONTENT, "emotion_word").startswith(variant)


def test_unknown_variant_raises():
    with pytest.raises(ValueError):
        ls.build_prompt(CONTENT, "nope")


def test_variant_is_passed_to_generation(fake_llm):
    outputs, calls = fake_llm
    outputs.append(GOOD)
    timings = {}
    ls.generate_diary_text("과제", "마감이라", "혼자", "오후 2시", "카페", timings=timings, prompt_variant="emotion_word")
    assert calls[0]["prompt"].startswith(ls.SYSTEM_PREAMBLE_EMOTION_WORD)
    assert timings["prompt_variant"] == "emotion_word"


def _fewshot_pairs(fewshot):
    import re
    blocks = fewshot.split("Human: 다음 정보를 바탕으로 감성적인 일기를 작성해라:\n\n")[1:]
    pairs = []
    for b in blocks:
        info, diary = b.split("Assistant:\n")
        f = dict(re.findall(r"(무엇을|이유|누구와|언제|어디서): (.*)", info))
        ctx = ls.expand_context(f"{f['누구와']} {f['무엇을']} {f['이유']} {f['언제']} {f['어디서']}")
        pairs.append((f, diary.strip(), ctx))
    return pairs


def test_current_fewshot_example3_fails_own_validator():
    # 0단계에서 확인한 약점 기록: 기본 few-shot 3번 예시(본가 방문)는 지금 검증 기준으로 불합격
    results = [ls.validate_diary(d, context_str=c)[0] for _, d, c in _fewshot_pairs(ls.FEWSHOT_EXAMPLES)]
    assert results == [True, True, False, True, True]


def test_fewshot_no_mealtime_variant_passes_validator_and_has_no_mealtime_words():
    pairs = _fewshot_pairs(ls.FEWSHOT_EXAMPLES_NO_MEALTIME)
    assert len(pairs) == 5
    for f, diary, ctx in pairs:
        ok, reasons, _ = ls.validate_diary(diary, context_str=ctx)
        assert ok, (f["무엇을"], reasons)
        for word in ls.MEALTIME_KEYWORDS:
            assert word not in diary and word not in f["언제"]
    # 시스템 프롬프트는 그대로, 예시만 바뀜
    assert ls.PROMPT_VARIANTS["fewshot_no_mealtime"][0] == ls.SYSTEM_PREAMBLE



# ---------- patch 12 ----------

def test_env_can_switch_default_variant(monkeypatch):
    monkeypatch.setenv("DIARY_PROMPT_VARIANT", "fewshot_no_mealtime")
    assert ls.build_prompt(CONTENT) == ls.build_prompt(CONTENT, "fewshot_no_mealtime")
    monkeypatch.setenv("DIARY_PROMPT_VARIANT", "없는변형")
    assert ls.build_prompt(CONTENT) == ls.build_prompt(CONTENT, "app_style")


def test_old_variants_prompt_text_unchanged():
    # 예전 변형의 마지막 지시문이 patch 12 전과 같은지 (되돌렸을 때 예전과 같은 동작)
    p = ls.build_prompt(CONTENT, "fewshot_no_mealtime")
    assert "입력의 '무엇을'과 '이유'를 반드시 반영할 것. 3~4문장으로 쓸 것):\n\n" + CONTENT in p


def test_app_style_examples_pass_own_validator_and_have_no_mealtime_words():
    for block in ls.FEWSHOT_APP_STYLE.split("Human: ")[1:]:
        inp, out = block.split("Assistant:\n")
        fields = [line.split(": ", 1)[1] for line in inp.strip().splitlines()[1:] if ": " in line]
        ctx = ls.expand_context(" ".join(fields))
        ok, reasons, _ = ls.validate_diary(out.strip(), ctx)
        assert ok, (reasons, out)
        for w in ls.MEALTIME_KEYWORDS:
            assert w not in out


def test_words_to_block_respects_input():
    block = ls.words_to_block(ls.expand_context("친구 선배랑 술 한잔 오후 7시 포차"))
    assert "선배" not in block and "아침" in block and "맥주" in block
    assert "술" not in block and "형" not in block  # 한 글자는 정상 단어까지 막을 수 있어서 제외


def test_drop_invented_sentences_fallback(fake_llm):
    outputs, _ = fake_llm
    bad = "과제를 하러 카페에 갔다. 끝나고 맥주도 한잔 했다. 창가 자리에서 노트북으로 한참 작업했다. 생각보다 오래 걸렸지만 다 끝내고 나왔다."
    outputs.extend([bad] * 3)
    timings = {}
    text, failed = _gen(timings)
    assert failed is False and timings["diary_repaired"] is True
    assert "맥주" not in text and text.startswith("과제를 하러 카페에 갔다.")


def test_validator_length_limits(monkeypatch):
    # patch 11까지는 150자/6문장이 상한이라 이런 자연스러운 일기도 버려졌음
    long_ok = ("오늘은 동네 카페에서 밀린 과제를 했다. 창가 자리에 앉아 노트북을 켰다. 생각보다 자료 찾는 데 오래 걸렸다. "
               "중간에 커피를 한 잔 더 시켰다. 그래도 마감 전에 다 끝내서 다행이었다. 집에 오는 길에 공원을 한 바퀴 걸었다. "
               "바람이 시원해서 머리가 맑아졌다. 내일은 조금 더 일찍 시작해야겠다.")
    assert 150 < len(long_ok) < 350
    assert ls.validate_diary(long_ok, "카페 과제")[0]
    assert not ls.validate_diary("오늘은 카페에서 과제를 했다. " * 9, "카페 과제")[0]  # 9문장은 여전히 거름
    monkeypatch.setenv("DIARY_MAX_CHARS", "100")
    assert not ls.validate_diary(long_ok, "카페 과제")[0]


def test_bad_words_ids_with_fake_tokenizer():
    class Tok:
        def __call__(self, text, add_special_tokens=False):
            ids = [ord(c) for c in text]
            return {"input_ids": ids}

        def decode(self, ids):
            return "".join(chr(i) for i in ids)

    ids = ls._bad_words_ids(Tok(), ["아침"])
    assert [ord("아"), ord("침")] in ids and [ord(" "), ord("아"), ord("침")] in ids



# ---------- patch 13: 음식 지어내기 ----------

JJAMPPONG_CTX = ls.expand_context("혼자 짬뽕 먹음 맛있어서 10월 30일 금요일 오후 12시 중국집")


def test_invented_food_is_rejected():
    text = "오늘은 중국집에서 짬뽕을 먹었다. 새우튀김도 하나 같이 시켜서 먹었다. 국물이 얼큰해서 땀이 좀 났다. 기분이 좋았다."
    ok, reasons, _ = ls.validate_diary(text, JJAMPPONG_CTX)
    assert not ok and "음식 지어냄(새우튀김)" in reasons


def test_food_inside_other_words_is_not_flagged():
    # '그만두다'의 만두, '물고기'의 고기, '~이라면'의 라면은 음식이 아님 (앞 글자가 한글이면 건너뜀)
    for text in ("힘들어서 그만두고 싶었다.", "어항 속 물고기를 한참 봤다.", "이번이 마지막이라면 좋겠다."):
        assert ls.has_invented_food(text, "혼자 산책") is None, text


def test_food_said_by_user_or_implied_by_place_is_allowed():
    assert ls.has_invented_food("짬뽕 국물이 얼큰했다.", JJAMPPONG_CTX) is None
    assert ls.has_invented_food("커피를 한 잔 시켰다.", "혼자 과제 카페") is None          # 카페 -> 커피
    assert ls.has_invented_food("케이크에 초를 꽂았다.", "친구 생일 축하 친구네 집") is None  # 생일 -> 케이크
    assert ls.has_invented_food("탕수육도 시켰다.", JJAMPPONG_CTX) == "탕수육"              # 중국집이어도 안 됨


def test_drop_invented_food_sentence_keeps_the_rest():
    text = "오늘은 중국집에서 짬뽕을 먹었다. 새우 튀김도 하나 시켰다. 국물이 얼큰했다. 기분이 좋았다."
    assert ls._drop_invented_sentences(text, JJAMPPONG_CTX) == "오늘은 중국집에서 짬뽕을 먹었다. 국물이 얼큰했다. 기분이 좋았다."


def test_food_words_are_blocked_at_generation_except_ambiguous_ones():
    block = ls.words_to_block(JJAMPPONG_CTX)
    assert "새우튀김" in block and "탕수육" in block and "짬뽕" not in block
    assert "라면" not in block and "만두" not in block  # 다른 말과 토큰이 겹칠 수 있어서 검증기에서만 잡음


def test_bad_words_include_josa_forms_for_mealtime_words():
    class Tok:
        def __call__(self, text, add_special_tokens=False):
            return {"input_ids": [ord(c) for c in text]}

        def decode(self, ids):
            return "".join(chr(i) for i in ids)

    ids = ls._bad_words_ids(Tok(), ["점심", "탕수육"])
    assert [ord(c) for c in " 점심으로"] in ids and [ord(c) for c in "점심에"] in ids
    assert [ord(c) for c in " 탕수육으로"] not in ids  # 조사 형태는 식사시간대/술 단어만 (목록이 너무 커지지 않게)


def test_app_style_prompt_rules_patch13():
    p = ls.SYSTEM_PREAMBLE_APP
    assert "3~4문장, 90~150자" in p and "4~5문장" not in p
    assert "생일이면 케이크" not in p and "답변에 없는 음식·메뉴·음료·물건" in p
    assert "케이크" not in ls.FEWSHOT_APP_STYLE and "과자" not in ls.FEWSHOT_APP_STYLE
    assert "짜장면" in ls.FEWSHOT_APP_STYLE
    assert ls.build_prompt(CONTENT).rstrip().endswith("Assistant:")
    assert "절대 지어내지 말 것" in ls.build_prompt(CONTENT)
