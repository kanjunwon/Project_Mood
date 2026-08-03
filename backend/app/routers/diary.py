from fastapi import APIRouter, HTTPException
from app.schemas.diary import DiaryRequest, DiaryResponse
from app.services.llama_service import generate_diary_text
from app.repositories.diary_repository import save_diary

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
        # 모델 생성 중 뭔가 터져도 서버 전체가 죽지 않고, 프론트에 에러 메시지로 알려줌
        raise HTTPException(status_code=500, detail=f"일기 생성 중 오류 발생: {str(e)}")

    who_str = ", ".join(request.who) if isinstance(request.who, list) else request.who

    try:
        save_diary({
            "user_id": request.user_id,
            "what": request.what,
            "why": request.why,
            "who": who_str,
            "when_": request.when,
            "where": request.where,
            "generated_diary": diary_text,
        })
    except Exception as e:
        # DB 저장 실패해도 일기 생성 자체는 이미 성공했으니, 응답은 그대로 내려줌
        print(f"DB 저장 실패 (일기 생성은 성공): {e}")

    return DiaryResponse(
        status="success",
        generated_diary=diary_text,
        validation_failed=failed,
    )
