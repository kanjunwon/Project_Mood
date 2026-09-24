from typing import Literal
from pydantic import BaseModel

GlassesType = Literal["horn_rimmed", "round", "none"]  # 디자인 확정: 뿔테/동그란/안 씀


class ProfileUpdateRequest(BaseModel):
    glasses: GlassesType
    bangs: bool
    hair_length: Literal["short", "medium", "long"]
    hair_color: str  # 프론트 드롭다운에서 고른 값 그대로 (예: "black", "brown", "blonde" 등)


class ProfileResponse(BaseModel):
    status: str
    glasses: GlassesType
    bangs: bool
    hair_length: str
    hair_color: str