import os

os.environ["MOCK_MODE"] = "true"

from app.services.cast import build_cast, strip_person_tags


def c(who, gender="남성"):
    return build_cast(who, gender)


def test_male_with_male_friend_is_two_boys():
    r = c("남성친구")
    assert (r.boys, r.girls) == (2, 0)
    assert "(2boys:1.2)" in r.tags and "male focus" in r.tags


def test_male_with_male_friend_and_3_is_four_boys():
    r = c("남성친구,3명")
    assert (r.boys, r.girls) == (4, 0)
    r = c("남성친구,친구 3명")
    assert r.total == 4


def test_korean_numeral():
    assert c("남성친구,세 명").total == 4


def test_solo():
    r = c("혼자")
    assert r.solo and r.total == 1 and "solo" in r.tags
    assert c("혼자", "여성").tags == ["1girl", "solo"]


def test_plain_friend_same_gender_as_me():
    assert (c("친구", "여성").girls, c("친구", "여성").boys) == (2, 0)
    assert c("친구").boys == 2


def test_mixed_friends():
    r = c("남성친구,여성친구")
    assert (r.boys, r.girls) == (2, 1)
    assert "1girl" in r.tags and "2boys" in r.tags


def test_parents_and_siblings():
    r = c("엄마,아빠")
    assert (r.boys, r.girls) == (2, 1)
    assert "mother" in r.tags and "father" in r.tags
    assert c("남매").girls == 1
    assert c("남매", "여성").boys == 1


def test_cap_four():
    r = c("남성친구,9명")
    assert r.total == 4 and r.trimmed and "out of focus background" in r.tags


def test_pets_do_not_count():
    assert c("혼자,강아지").solo


def test_undecidable_returns_none():
    for who in ("가족", "연인", "자녀", "회사 동료", "남성친구,여성친구,3명"):
        assert c(who) is None, who
    assert c("남성친구", None) is None
    assert c("") is None


def test_strip_person_tags():
    out = strip_person_tags("3boys, young adults, friends, mother, solo, (2girls:1.2), karaoke room, male focus")
    assert out == "young adults, friends, karaoke room"
