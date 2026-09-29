"""
app/dependencies.py
JWT 토큰(Authorization: Bearer <token>)에서 로그인된 user_id를 추출하는 의존성.

HTTPBearer로 바꾼 이유: Header(...) 방식은 Swagger UI에 "Authorize" 자물쇠 버튼이
안 생겨서 매 요청마다 authorization 헤더를 손으로 다시 넣어야 했음.
HTTPBearer로 바꾸면 Swagger가 진짜 인증 방식으로 인식해서, 한 번만 Authorize 해두면
그 뒤로는 모든 요청에 토큰이 자동으로 실림.
"""
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.services.auth_service import decode_access_token

bearer_scheme = HTTPBearer()


def get_current_user_id(credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme)) -> int:
    token = credentials.credentials  # "Bearer " 접두사는 HTTPBearer가 알아서 떼고 줌
    user_id = decode_access_token(token)
    if user_id is None:
        raise HTTPException(status_code=401, detail="유효하지 않거나 만료된 토큰입니다")
    return user_id