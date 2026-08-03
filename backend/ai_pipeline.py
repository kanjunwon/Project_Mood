"""
AI 파이프라인 함수 모음.

지금은 EEVE-Rosetta / KoBERT / SD3가 학습 중이라 더미(mock) 로직으로 채워둠.
실제 모델 학습이 끝나면 이 파일 안의 함수 3개 내부만 교체하면 되고,
diaries 라우터 쪽 코드는 손댈 필요 없음 (인터페이스 고정).
"""
import time as time_module
from typing import List, Tuple


def generate_diary_text(what: str, why: str, who: List[str], when: str, where: str) -> str:
    """EEVE-Rosetta: 5문항 답변 → 1인칭 일기문 생성"""
    # TODO: 실제 모델 연동 시 아래 더미 로직을 EEVE-Rosetta 추론 코드로 교체
    time_module.sleep(1)  # 실제 모델 추론 시간 흉내
    who_str = ", ".join(who)
    return f"{where}에서 {who_str}와(과) 함께 {what}. {why}."


def analyze_emotion(diary_text: str) -> List[Tuple[str, float]]:
    """KoBERT: 일기 텍스트 → (감정, 점수) 리스트, score 내림차순"""
    # TODO: 실제 모델 연동 시 KoBERT 추론 코드로 교체
    time_module.sleep(1)
    return [("뿌듯함", 0.60), ("편안함", 0.30), ("행복함", 0.10)]


def generate_diary_image(diary_text: str, primary_emotion: str) -> str:
    """SD3 + LoRA: 일기 내용 + 감정 키워드 → 그림일기 이미지 생성 후 URL 반환"""
    # TODO: 실제 모델 연동 시 SD3 추론 + Supabase Storage 업로드 코드로 교체
    time_module.sleep(1)
    return "https://placehold.co/512x512?text=diary+image+placeholder"
