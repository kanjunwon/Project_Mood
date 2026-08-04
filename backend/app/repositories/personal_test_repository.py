from app.database import supabase


def save_personal_test_result(user_id: str | None, answers: dict, weight_profile: dict | None = None) -> None:
    """personal_test_results 테이블에 저장. supabase 클라이언트 없으면(키 미설정) 조용히 skip."""
    if supabase is None:
        return

    supabase.table("personal_test_results").insert({
        "user_id": user_id,
        "answers": answers,
        "weight_profile": weight_profile,  # 가중치 알고리즘 완성 전까지는 None
    }).execute()
