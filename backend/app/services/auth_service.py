import os
import jwt
from datetime import datetime, timedelta, timezone
from passlib.context import CryptContext

JWT_SECRET = os.environ.get("JWT_SECRET", "dev-only-change-this-in-production")
if "JWT_SECRET" not in os.environ and os.environ.get("MOCK_MODE", "false").lower() != "true":
    # 기본값으로 돌면 누구나 같은 비밀키로 토큰을 만들 수 있음 (로그인 우회). .env에 긴 무작위 값을 꼭 넣을 것.
    print("[경고] JWT_SECRET이 .env에 없어서 기본값으로 동작 중 - 토큰 위조 가능. .env에 JWT_SECRET을 설정하세요.")
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_HOURS = 24 * 7  # 일주일

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(plain_password: str) -> str:
    return pwd_context.hash(plain_password)


def verify_password(plain_password: str, password_hash: str) -> bool:
    return pwd_context.verify(plain_password, password_hash)


def create_access_token(user_id: int) -> str:
    expire = datetime.now(timezone.utc) + timedelta(hours=JWT_EXPIRE_HOURS)
    payload = {"sub": str(user_id), "exp": expire}
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_access_token(token: str):
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return int(payload["sub"])
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None
