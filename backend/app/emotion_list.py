EMOTION_LIST = sorted([
    "행복한", "기쁜", "기대되는", "설레는", "신나는", "열정적인", "즐거운", "상쾌한",
    "뿌듯한", "후련한", "감사한", "편안한",
    "우울한", "실망한", "후회되는", "슬픈", "두려운", "불안한", "막막한", "피곤한",
    "외로운", "지루한", "화나는", "짜증나는",
])

EMOTION_TO_ID = {emotion: idx for idx, emotion in enumerate(EMOTION_LIST)}
ID_TO_EMOTION = {idx: emotion for idx, emotion in enumerate(EMOTION_LIST)}
