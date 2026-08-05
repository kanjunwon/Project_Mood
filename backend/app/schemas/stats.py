from pydantic import BaseModel
from typing import List, Optional


class EmotionScore(BaseModel):
    emotion: str
    score: float


class DailyStatsResponse(BaseModel):
    date: str
    top_emotion: Optional[str]
    top3_emotions: List[EmotionScore]
    companions: List[str]
    places: List[str]


class EmotionFlowPoint(BaseModel):
    date: str
    sentiment_score: float
    top_emotion: Optional[str]


class EmotionDistributionItem(BaseModel):
    emotion: str
    percentage: float
    color: str
    valence: Optional[str] = None


class TopEntity(BaseModel):
    name: str
    count: int
    top3_emotions: List[EmotionScore]


class MonthlyStatsResponse(BaseModel):
    year: int
    month: int
    top_emotion: Optional[str]
    top3_emotions: List[EmotionScore]
    emotion_flow: List[EmotionFlowPoint]
    emotion_distribution: List[EmotionDistributionItem]
    most_positive_day: Optional[str]
    most_negative_day: Optional[str]
    top_companion: Optional[TopEntity]
    top_place: Optional[TopEntity]
