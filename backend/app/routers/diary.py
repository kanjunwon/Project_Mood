from fastapi import APIRouter
from app.schemas.diary import DiaryRequest, DiaryResponse
from app.services.llama_service import generate_diary_text
from app.repositories.diary_repository import save_diary

router = APIRouter()


@router.post("/generate-diary", response_model=DiaryResponse)
def generate_diary(request: DiaryRequest):
    diary_text, failed = generate_diary_text(
        what=request.what,
        why=request.why,
        who=request.who,
        when=request.when,
        where=request.where,
    )

    who_str = ", ".join(request.who) if isinstance(request.who, list) else request.who

    save_diary({
        "user_id": request.user_id,
        "what": request.what,
        "why": request.why,
        "who": who_str,
        "when_": request.when,
        "where": request.where,
        "generated_diary": diary_text,
    })

    return DiaryResponse(
        status="success",
        generated_diary=diary_text,
        validation_failed=failed,
    )