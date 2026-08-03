from datetime import date, time
from typing import List, Optional
from pydantic import BaseModel


class DiaryCreateRequest(BaseModel):
    what: str
    why: str
    who: List[str]
    when: time
    where: str
    entry_date: date


class DiaryCreateResponse(BaseModel):
    diary_id: int
    status: str  # "processing"


class EmotionItem(BaseModel):
    emotion: str
    score: float
    is_primary: bool = False


class DiaryStatusResponse(BaseModel):
    diary_id: int
    status: str  # pending | processing | completed | failed
    generated_diary_text: Optional[str] = None
    emotions: List[EmotionItem] = []
    image_url: Optional[str] = None
    error_message: Optional[str] = None
