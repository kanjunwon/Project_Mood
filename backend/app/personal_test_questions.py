"""
퍼스널 감정 검사 문항 목록 (총 19문항)
- HSP(Highly Sensitive Person, 민감성) 13문항
- LOT-R(Life Orientation Test-Revised, 낙관성) 6문항
1~5점 척도: 1(매우 아니다) ~ 5(매우 그렇다)

reverse: True인 문항은 나중에 가중치 계산 시 점수를 뒤집어서(6 - 응답값) 써야 함
(LOT-R은 원래 반은 역채점 문항으로 설계된 척도라 표시해둠. 지금은 원본 응답만 저장하고,
 실제 역채점 적용은 weight_profile 계산 로직 만들 때 처리)
"""

QUESTIONS = [
    # HSP (1~13)
    {"id": 1, "category": "HSP", "text": "여러 사람이 말하는 장소에 있으면 금세 피로해진다.", "reverse": False},
    {"id": 2, "category": "HSP", "text": "신체적으로 피곤하면 감정적으로 더 민감해진다.", "reverse": False},
    {"id": 3, "category": "HSP", "text": "타인의 말이나 표정에 과도하게 반응하는 편이다.", "reverse": False},
    {"id": 4, "category": "HSP", "text": "영화나 음악, 책 등의 감동적인 장면에 쉽게 눈물이 난다.", "reverse": False},
    {"id": 5, "category": "HSP", "text": "말 한마디에 쉽게 기분이 영향을 받는다.", "reverse": False},
    {"id": 6, "category": "HSP", "text": "감정의 여운이 오래 남아 쉽게 잊혀지지 않는다.", "reverse": False},
    {"id": 7, "category": "HSP", "text": "타인의 기분 변화에 민감하게 반응한다.", "reverse": False},
    {"id": 8, "category": "HSP", "text": "해야 할 일이 많을 때 무기력하거나 초조해진다.", "reverse": False},
    {"id": 9, "category": "HSP", "text": "예기치 못한 변화에 민감하게 반응한다.", "reverse": False},
    {"id": 10, "category": "HSP", "text": "작은 실수나 오해에도 심한 자책을 한다.", "reverse": False},
    {"id": 11, "category": "HSP", "text": "일이 완벽하지 않으면 불안하고 쉽게 흔들린다.", "reverse": False},
    {"id": 12, "category": "HSP", "text": "내 감정 상태를 자주 되돌아보는 편이다.", "reverse": False},
    {"id": 13, "category": "HSP", "text": "다른 사람과 함께 있을 때에도 내 감정에 집중하느라 피곤함을 느낄 때가 있다.", "reverse": False},
    # LOT-R (14~19)
    {"id": 14, "category": "LOT-R", "text": "불확실한 상황에서도 대개 최선의 결과를 기대한다.", "reverse": False},
    {"id": 15, "category": "LOT-R", "text": "나에게 나쁜 일이 생길 것 같으면, 꼭 그렇게 된다.", "reverse": True},
    {"id": 16, "category": "LOT-R", "text": "나의 미래에 대해 항상 낙관적이다.", "reverse": False},
    {"id": 17, "category": "LOT-R", "text": "하는 일이 내 뜻대로 잘 풀릴 거라고 기대하는 일은 거의 없다.", "reverse": True},
    {"id": 18, "category": "LOT-R", "text": "좋은 일이 일어날 거라고는 거의 기대하지 않는다.", "reverse": True},
    {"id": 19, "category": "LOT-R", "text": "전반적으로 나쁜 일보다 좋은 일이 더 많이 일어날 것이라 기대한다.", "reverse": False},
]

QUESTION_IDS = [q["id"] for q in QUESTIONS]  # [1, 2, ..., 19]
