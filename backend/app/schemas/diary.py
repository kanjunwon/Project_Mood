from pydantic import BaseModel
from typing import List, Optional, Union


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
