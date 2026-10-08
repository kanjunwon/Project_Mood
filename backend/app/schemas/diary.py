from pydantic import AliasChoices, BaseModel, Field
from typing import List, Optional, Union, Dict


class DiaryRequest(BaseModel):
    what: str
    why: str
    who: Union[str, List[str]]
    when: str
    where: str
    # 사용자가 앱에서 고른 일기 날짜 (YYYY-MM-DD). 안 보내면 오늘로 처리(기존 앱 호환).
    # 앱이 다른 이름으로 보내도 받을 수 있게 별칭 허용: date / entry_date / diary_date
    date: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("date", "entry_date", "diary_date"),
    )
    # user_id는 더 이상 여기 안 받음 - 로그인 토큰(Authorization 헤더)에서만 가져옴


class DiaryResponse(BaseModel):
    status: str
    generated_diary: str
    validation_failed: bool
    top_emotion: Optional[str] = None
    emotion_scores: Optional[Dict[str, float]] = None
    sentiment_score: Optional[float] = None
    image_url: Optional[str] = None  # SD3로 생성된 그림일기 이미지, 실패하거나 MOCK_MODE면 None
    id: Optional[int] = None  # 저장된 diary_entries.id (DB 저장 실패/미연결이면 None)


class DiaryJobCreated(BaseModel):
    job_id: str
    status: str  # 항상 "processing"


class DiaryJobStatus(BaseModel):
    job_id: str
    status: str  # "processing" | "done" | "error"
    result: Optional[DiaryResponse] = None  # status == "done"일 때만
    error: Optional[str] = None  # status == "error"일 때만
