from app.database import supabase

TABLE_NAME = "users"


def create_user(email: str, password_hash: str, nickname: str = None):
    if supabase is None:
        raise RuntimeError("DB 연결 안 됨 - 회원가입 불가")
    response = supabase.table(TABLE_NAME).insert({
        "email": email,
        "password_hash": password_hash,
        "nickname": nickname,
    }).execute()
    return response.data[0] if response.data else None


def get_user_by_email(email: str):
    if supabase is None:
        return None
    response = supabase.table(TABLE_NAME).select("*").eq("email", email).execute()
    return response.data[0] if response.data else None
