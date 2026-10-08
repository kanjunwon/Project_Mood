import os
os.environ["MOCK_MODE"] = "true"

from app.services.sd3_service import apply_gender, normalize_gender, ensure_solo_person, is_solo

NEG = "bad anatomy, blurry"


def test_normalize_gender():
    assert normalize_gender("남성") == "male"
    assert normalize_gender("남자") == "male"
    assert normalize_gender("male") == "male"
    assert normalize_gender("여성") == "female"
    assert normalize_gender("female") == "female"
    assert normalize_gender("Female") == "female"
    assert normalize_gender(None) is None
    assert normalize_gender("") is None
    assert normalize_gender("기타") is None


def test_male_solo_girl_is_swapped_to_boy():
    pos, neg = apply_gender("1girl, young adult woman, solo, cafe, gamjeong style", NEG, "남성")
    assert "1girl" not in pos and "young adult woman" not in pos
    assert pos.startswith("(1boy:1.3), (male focus:1.2), young adult man, solo")
    assert "(1girl:1.3)" in neg and neg.startswith(NEG)


def test_male_already_boy_gets_emphasis_without_duplicates():
    pos, _ = apply_gender("1boy, solo, park, gamjeong style", NEG, "남성")
    assert pos == "(1boy:1.3), (male focus:1.2), solo, park, gamjeong style"
    assert pos.count("1boy") == 1


def test_female_and_unknown_gender_untouched():
    src = "1girl, solo, cafe, gamjeong style"
    for g in ("여성", None, "기타"):
        assert apply_gender(src, NEG, g) == (src, NEG)


def test_groups_and_couples_are_not_modified():
    for src in ("3girls, 2boys, karaoke room, gamjeong style",
                "1girl, young adult woman, 1boy, young adult man, couple, gamjeong style",
                "2girls, foreground, amusement park, gamjeong style"):
        assert apply_gender(src, NEG, "남성") == (src, NEG)


def test_male_without_any_person_tag_untouched():
    src = "cafe, window seat, gamjeong style"
    assert apply_gender(src, NEG, "남성") == (src, NEG)


# --- 혼자(solo) 인원 보정 ---
LLM_NO_PERSON = "programming, laptop, coding, typing, chair, home, afternoon, gamjeong style"


def test_is_solo():
    assert is_solo("혼자") and is_solo(["혼자"]) and is_solo("혼자, 혼자")
    assert not is_solo("친구") and not is_solo(["혼자", "친구"]) and not is_solo("혼자, 가족")
    assert not is_solo(None) and not is_solo([]) and not is_solo("")


def test_solo_without_person_tag_gets_one_person():
    pos, neg = ensure_solo_person(LLM_NO_PERSON, NEG, "혼자", "남성")
    assert pos.startswith("1boy, solo, programming")
    assert "multiple girls" in neg and neg.startswith(NEG)
    pos, _ = ensure_solo_person(LLM_NO_PERSON, NEG, ["혼자"], "여성")
    assert pos.startswith("1girl, solo, programming")
    pos, _ = ensure_solo_person(LLM_NO_PERSON, NEG, "혼자", None)
    assert pos.startswith("solo, programming")


def test_not_solo_is_untouched_even_without_person_tag():
    assert ensure_solo_person(LLM_NO_PERSON, NEG, "친구", "남성") == (LLM_NO_PERSON, NEG)


def test_existing_person_tag_is_kept_solo_added():
    pos, neg = ensure_solo_person("1girl, cafe, gamjeong style", NEG, "혼자", "여성")
    assert pos == "solo, 1girl, cafe, gamjeong style" and neg == NEG
    same = "1girl, solo, cafe, gamjeong style"
    assert ensure_solo_person(same, NEG, "혼자", "여성") == (same, NEG)


def test_full_chain_for_male_solo_without_person_tag():
    pos, neg = ensure_solo_person(LLM_NO_PERSON, NEG, "혼자", "남성")
    pos, neg = apply_gender(pos, neg, "남성")
    assert pos.startswith("(1boy:1.3), (male focus:1.2), solo, programming")
    assert pos.count("1boy") == 1
    assert "(1girl:1.3)" in neg and "multiple girls" in neg
