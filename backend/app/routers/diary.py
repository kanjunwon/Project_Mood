import os
from fastapi import APIRouter, Depends, HTTPException
from app.dependencies import get_current_user_id
from app.schemas.diary import DiaryRequest, DiaryResponse
from app.services.llama_service import generate_diary_text
from app.services.kobert_service import analyze_emotion
from app.repositories.diary_repository import save_diary, get_diary_by_user
from app.repositories.user_repository import get_user_by_id

router = APIRouter()

MOCK_MODE = os.environ.get("MOCK_MODE", "false").lower() == "true"


@router.post("/generate-diary", response_model=DiaryResponse)
def generate_diary(request: DiaryRequest, user_id: int = Depends(get_current_user_id)):
    # user_id는 body가 아니라 로그인 토큰에서만 가져옴 (2026-09 결정, 클라이언트가 남의 user_id로
    # 요청 보내는 걸 막기 위함). 이 값으로 프로필(아바타 설정)도 같이 조회해서 이미지 생성에 반영.
    profile = get_user_by_id(user_id) or {}
    glasses = profile.get("glasses") or "none"
    bangs = profile.get("bangs", True)
    hair_length = profile.get("hair_length", "medium")
    hair_color = profile.get("hair_color", "black")

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
    # (ComfyUI 서버가 꺼져있거나, 연결 안 되는 경우가 흔히 있을 수 있어서)
    image_url = None
    if not MOCK_MODE:
        try:
            from app.services.sd3_service import generate_diary_image
            image_url = generate_diary_image(
                diary_text=diary_text,
                top_emotion=emotion_result.get("top_emotion") or "편안한",
                who=request.who,
                where=request.where,
                when=request.when,
                glasses=glasses,
                bangs=bangs,
                hair_length=hair_length,
                hair_color=hair_color,
            )
        except Exception as e:
            print(f"이미지 생성 실패 (일기 생성은 성공): {e}")

    try:
        save_diary({
            "user_id": str(user_id),
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


@router.get("/diaries/me")
def get_my_diaries(user_id: int = Depends(get_current_user_id)):
    try:
        diaries = get_diary_by_user(str(user_id))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"조회 중 오류 발생: {str(e)}")

    return {"status": "success", "diaries": diaries}