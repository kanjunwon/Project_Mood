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
    # 하루 1개 규칙: 같은 날짜(한국 날짜)에 일기가 이미 있으면 기본은 409.
    # "다시 작성하기"는 true로 보내면 새 일기 저장에 성공한 뒤 기존 일기를 지움 (생성 실패 시 기존 일기 유지)
    overwrite: bool = False
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
    # 앱이 분기할 수 있는 에러 종류. 지금은 "DIARY_ALREADY_EXISTS"(같은 날짜 일기 있음)만 있고 나머지는 None
    error_code: Optional[str] = None
