from fastapi import APIRouter, Depends, HTTPException

from app.dependencies import get_current_user_id
from app.schemas.personal_test import PersonalTestSubmitRequest, PersonalTestSubmitResponse
from app.repositories.personal_test_repository import save_personal_test_result
from app.weight_algorithm import compute_persona_scores, build_weight_vector
from app.database import supabase

router = APIRouter()

# personal_test_questions.py 기준: 1~13번 HSP, 14~19번 LOT-R
HSP_IDS = list(range(1, 14))
LOTR_IDS = list(range(14, 20))


@router.post("/personal-test", response_model=PersonalTestSubmitResponse)
def submit_personal_test(req: PersonalTestSubmitRequest, user_id: int = Depends(get_current_user_id)):
    """
    19문항 응답 제출 -> 저장 + weight_profile 계산.

    user_id는 로그인 토큰에서만 가져옴.
    가중치 알고리즘(종현 설계, 2026-09-24 확정) 반영: HSP/LOT-R 응답으로 hsp_score/lotr_score를
    계산하고, 24개 감정 각각에 대한 가중치 벡터를 만들어서 weight_profile에 저장.
    이 값은 사용자에게 노출 안 하고, 일기 생성 시 KoBERT 결과 보정에만 내부적으로 씀.
    """
    hsp_answers = [req.answers[str(qid)] for qid in HSP_IDS]
    lotr_answers = [req.answers[str(qid)] for qid in LOTR_IDS]

    hsp_score, lotr_score = compute_persona_scores(hsp_answers, lotr_answers)
    weights = build_weight_vector(hsp_score, lotr_score)

    weight_profile = {
        "hsp_score": hsp_score,
        "lotr_score": lotr_score,
        "weights": weights,
    }

    try:
        save_personal_test_result(
            user_id=str(user_id),
            answers=req.answers,
            weight_profile=weight_profile,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"검사 결과 저장 중 오류 발생: {e}")

    return PersonalTestSubmitResponse(status="success")


@router.get("/personal-test/status")
def get_personal_test_status(user_id: int = Depends(get_current_user_id)):
    """회원가입 직후 프론트가 "검사 안 했으면 검사 화면으로 강제 이동"시킬 때 쓰는 확인용 API."""
    if supabase is None:
        return {"status": "success", "completed": False}

    response = (
        supabase.table("personal_test_results")
        .select("id, completed_at")
        .eq("user_id", str(user_id))
        .order("completed_at", desc=True)
        .limit(1)
        .execute()
    )
    completed = bool(response.data)
    return {
        "status": "success",
        "completed": completed,
        "last_completed_at": response.data[0]["completed_at"] if completed else None,
    }