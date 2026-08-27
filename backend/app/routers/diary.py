import os
from fastapi import APIRouter, HTTPException
from app.schemas.diary import DiaryRequest, DiaryResponse
from app.services.llama_service import generate_diary_text
from app.services.kobert_service import analyze_emotion
from app.repositories.diary_repository import save_diary, get_diary_by_user

router = APIRouter()

MOCK_MODE = os.environ.get("MOCK_MODE", "false").lower() == "true"


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
        emotion_result = analyze_emotion(diary_text)
    except Exception as e:
        print(f"감정 분석 실패: {e}")
        emotion_result = {"top_emotion": None, "scores": None, "sentiment_score": None}

    # SD3 이미지 생성 - 실패해도 일기 자체는 정상 응답되게 try/except로 감쌈
    # (ComfyUI 서버가 꺼져있거나, 재유 컴퓨터랑 연결 안 되는 경우가 흔히 있을 수 있어서)
    image_url = None
    if not MOCK_MODE:
        try:
            from app.services.sd3_service import generate_diary_image
            image_url = generate_diary_image(
                diary_text=diary_text,
                top_emotion=emotion_result.get("top_emotion") or "편안한",
            )
        except Exception as e:
            print(f"이미지 생성 실패 (일기 생성은 성공): {e}")

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
            "top_emotion": emotion_result["top_emotion"],
            "emotion_scores": emotion_result["scores"],
            "sentiment_score": emotion_result["sentiment_score"],
            "image_url": image_url,
        })
    except Exception as e:
        print(f"DB 저장 실패 (일기 생성은 성공): {e}")

    return DiaryResponse(
        status="success",
        generated_diary=diary_text,
        validation_failed=failed,
        top_emotion=emotion_result["top_emotion"],
        emotion_scores=emotion_result["scores"],
        sentiment_score=emotion_result["sentiment_score"],
        image_url=image_url,
    )


@router.get("/diaries/{user_id}")
def get_diaries(user_id: str):
    try:
        diaries = get_diary_by_user(user_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"조회 중 오류 발생: {str(e)}")

    return {"status": "success", "diaries": diaries}