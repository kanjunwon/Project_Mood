from app.database import supabase

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


def get_diaries_by_date_range(user_id: str, start_date: str, end_date: str):
    """
    start_date, end_date는 'YYYY-MM-DD' 형태 문자열
    end_date는 미포함(exclusive) - 예: 월간 조회면 다음달 1일을 end_date로 넘기면 됨
    """
    if supabase is None:
        return []
    response = (
        supabase.table(TABLE_NAME)
        .select("*")
        .eq("user_id", user_id)
        .gte("created_at", start_date)
        .lt("created_at", end_date)
        .execute()
    )
    return response.data
