from app.database import supabase


def save_personal_test_result(user_id: str, answers: dict, weight_profile: dict = None) -> None:
    """personal_test_results 테이블에 저장. supabase 클라이언트 없으면(키 미설정) 조용히 skip."""
    if supabase is None:
        return

    supabase.table("personal_test_results").insert({
        "user_id": user_id,
        "answers": answers,
        "weight_profile": weight_profile,
    }).execute()


def get_latest_weight_profile(user_id: str):
    """
    이 사용자의 가장 최근 퍼스널 검사 결과에서 weight_profile만 꺼내온다.
    검사를 한 번도 안 했거나 DB 연결이 없으면 None 반환 (호출 쪽에서 "가중치 미적용"으로 처리).
    """
    if supabase is None:
        return None

    response = (
        supabase.table("personal_test_results")
        .select("weight_profile")
        .eq("user_id", user_id)
        .order("completed_at", desc=True)
        .limit(1)
        .execute()
    )
    if not response.data:
        return None
    return response.data[0].get("weight_profile")