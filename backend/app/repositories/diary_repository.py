from app.database import supabase

# 재유가 만든 테이블 이름/컬럼명에 맞춰서 여기만 고치면 됨
TABLE_NAME = "diary_entries"


def save_diary(data: dict):
    if supabase is None:
        print("DB 연결 안 됨 -> 저장 스킵 (테스트 모드)")
        return None
    response = supabase.table(TABLE_NAME).insert(data).execute()
    return response.data


def get_diary_by_user(user_id: str):
    if supabase is None:
        return []
    response = supabase.table(TABLE_NAME).select("*").eq("user_id", user_id).execute()
    return response.data
