from fastapi import APIRouter, HTTPException
from app.schemas.auth import SignupRequest, LoginRequest, TokenResponse
from app.services.auth_service import hash_password, verify_password, create_access_token
from app.repositories.user_repository import create_user, get_user_by_email

router = APIRouter()


@router.post("/signup", response_model=TokenResponse)
def signup(request: SignupRequest):
    existing = get_user_by_email(request.email)
    if existing:
        raise HTTPException(status_code=409, detail="이미 가입된 이메일입니다.")

    password_hash = hash_password(request.password)

    try:
        user = create_user(request.email, password_hash, request.nickname)
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))

    if user is None:
        raise HTTPException(status_code=500, detail="회원가입 처리 중 오류가 발생했습니다.")

    token = create_access_token(user["id"])
    return TokenResponse(
        status="success",
        access_token=token,
        user_id=user["id"],
        nickname=user.get("nickname"),
    )


@router.post("/login", response_model=TokenResponse)
def login(request: LoginRequest):
    user = get_user_by_email(request.email)
    if user is None or not verify_password(request.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="이메일 또는 비밀번호가 올바르지 않습니다.")

    token = create_access_token(user["id"])
    return TokenResponse(
        status="success",
        access_token=token,
        user_id=user["id"],
        nickname=user.get("nickname"),
    )
