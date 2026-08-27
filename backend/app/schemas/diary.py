from pydantic import BaseModel
from typing import List, Optional, Union, Dict


class DiaryRequest(BaseModel):
    what: str
    why: str
    who: Union[str, List[str]]
    when: str
    where: str
    user_id: Optional[str] = None


class DiaryResponse(BaseModel):
    status: str
    generated_diary: str
    validation_failed: bool
    top_emotion: Optional[str] = None
    emotion_scores: Optional[Dict[str, float]] = None
    sentiment_score: Optional[float] = None
    image_url: Optional[str] = None  # SD3로 생성된 그림일기 이미지, 실패하거나 MOCK_MODE면 None