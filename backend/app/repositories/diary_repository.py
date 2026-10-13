from datetime import date as date_cls, timedelta

from app.database import supabase
from app.date_utils import kst_day_start

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
    start_date, end_date는 'YYYY-MM-DD' 형태 문자열 (한국 날짜 기준)
    end_date는 미포함(exclusive) - 예: 월간 조회면 다음달 1일을 end_date로 넘기면 됨
    """
    if supabase is None:
        return []
    response = (
        supabase.table(TABLE_NAME)
        .select("*")
        .eq("user_id", user_id)
        .gte("created_at", kst_day_start(start_date))
        .lt("created_at", kst_day_start(end_date))
        .execute()
    )
    return response.data


def get_diaries_on_date(user_id: str, d: date_cls):
    """한국 날짜 d에 작성된 일기 목록 (하루 1개 규칙 확인용). 최신순."""
    rows = get_diaries_by_date_range(user_id, d.isoformat(), (d + timedelta(days=1)).isoformat()) or []
    return sorted(rows, key=lambda r: r.get("created_at") or "", reverse=True)


def delete_diary(user_id: str, diary_id: int) -> bool:
    """본인 일기만 삭제. 지운 게 없으면(없는 id거나 남의 일기) False."""
    if supabase is None:
        return False
    response = supabase.table(TABLE_NAME).delete().eq("id", diary_id).eq("user_id", user_id).execute()
    return bool(response.data)


def delete_diaries_by_ids(user_id: str, diary_ids: list) -> None:
    if supabase is None or not diary_ids:
        return
    supabase.table(TABLE_NAME).delete().in_("id", diary_ids).eq("user_id", user_id).execute()
