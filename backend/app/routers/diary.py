from fastapi import APIRouter, HTTPException
from app.schemas.diary import DiaryRequest, DiaryResponse
from app.services.llama_service import generate_diary_text
from app.repositories.diary_repository import save_diary, get_diary_by_user

router = APIRouter()


@router.post("/generate-diary", response_model=DiaryResponse)
def generate_diary(request: DiaryRequest):
    try:
        diary_text, failed = generate_diary_text(
            what=request.what,
            why=request.why,
            who=request.who,
            when=request.when,
            where=request.where,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"일기 생성 중 오류 발생: {str(e)}")

    who_str = ", ".join(request.who) if isinstance(request.who, list) else request.who

    try:
        save_diary({
            "user_id": request.user_id,
            "what": request.what,
            "why": request.why,
            "who": who_str,
            "when_": request.when,
            "where_": request.where,
            "generated_diary": diary_text,
            "validation_failed": failed,
        })
    except Exception as e:
        print(f"DB 저장 실패 (일기 생성은 성공): {e}")

    return DiaryResponse(
        status="success",
        generated_diary=diary_text,
        validation_failed=failed,
    )


@router.get("/diaries/{user_id}")
def get_diaries(user_id: str):
    try:
        diaries = get_diary_by_user(user_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"조회 중 오류 발생: {str(e)}")

    return {"status": "success", "diaries": diaries}
