from fastapi import APIRouter, HTTPException

from app.schemas.personal_test import PersonalTestSubmitRequest, PersonalTestSubmitResponse
from app.repositories.personal_test_repository import save_personal_test_result

router = APIRouter()


@router.post("/personal-test", response_model=PersonalTestSubmitResponse)
def submit_personal_test(req: PersonalTestSubmitRequest):
    """
    19문항 응답 제출 → 저장.

    weight_profile(가중치 프로필)은 아직 계산 로직이 없어서 지금은 항상 None으로 저장됨.
    가중치 알고리즘 설계되면 여기서 계산해서 넣으면 됨 (사용자에게는 노출 안 하고 내부용으로만 씀).
    """
    try:
        save_personal_test_result(
            user_id=req.user_id,
            answers=req.answers,
            weight_profile=None,  # TODO: 가중치 알고리즘 완성되면 계산해서 전달
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"검사 결과 저장 중 오류 발생: {e}")

    return PersonalTestSubmitResponse(status="success")
