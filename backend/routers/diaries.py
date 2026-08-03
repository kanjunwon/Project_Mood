from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session

from database import get_db
from models import Diary, EmotionAnalysis
from schemas import DiaryCreateRequest, DiaryCreateResponse, DiaryStatusResponse, EmotionItem
import ai_pipeline

router = APIRouter(prefix="/api/v1/diaries", tags=["diaries"])


def run_pipeline(diary_id: int, what: str, why: str, who: list, when: str, where: str, db: Session):
    """백그라운드에서 실행되는 3단계 AI 파이프라인 (EEVE-Rosetta → KoBERT → SD3)"""
    diary = db.query(Diary).filter(Diary.id == diary_id).first()
    if not diary:
        return

    try:
        diary.status = "processing"
        db.commit()

        # 1. EEVE-Rosetta: 일기 텍스트 생성
        diary_text = ai_pipeline.generate_diary_text(what, why, who, when, where)
        diary.generated_diary_text = diary_text

        # 2. KoBERT: 감정 분석
        emotions = ai_pipeline.analyze_emotion(diary_text)
        for idx, (emotion, score) in enumerate(emotions):
            db.add(EmotionAnalysis(
                diary_id=diary_id,
                emotion=emotion,
                score=score,
                is_primary=(idx == 0),
            ))

        # 3. SD3 + LoRA: 그림일기 이미지 생성
        primary_emotion = emotions[0][0] if emotions else ""
        image_url = ai_pipeline.generate_diary_image(diary_text, primary_emotion)
        diary.image_url = image_url

        diary.status = "completed"
        db.commit()

    except Exception as e:
        diary.status = "failed"
        db.commit()
        # TODO: 로깅 시스템 연동 시 여기서 에러 로그 남기기
        print(f"[diary {diary_id}] 파이프라인 실패: {e}")


@router.post("/generate", response_model=DiaryCreateResponse, status_code=202)
def create_diary(
    req: DiaryCreateRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """5문항 답변을 받아 diary 레코드를 만들고, AI 파이프라인은 백그라운드로 돌림"""
    diary = Diary(
        user_id=None,  # TODO: 인증 붙으면 현재 로그인 유저 id로 교체
        entry_date=req.entry_date,
        what=req.what,
        why=req.why,
        who=req.who,
        event_time=req.when,
        where_=req.where,
        status="pending",
    )
    db.add(diary)
    db.commit()
    db.refresh(diary)

    background_tasks.add_task(
        run_pipeline, diary.id, req.what, req.why, req.who, str(req.when), req.where, db
    )

    return DiaryCreateResponse(diary_id=diary.id, status="processing")


@router.get("/{diary_id}", response_model=DiaryStatusResponse)
def get_diary_status(diary_id: int, db: Session = Depends(get_db)):
    """클라이언트가 폴링해서 생성 상태/결과를 확인하는 엔드포인트"""
    diary = db.query(Diary).filter(Diary.id == diary_id).first()
    if not diary:
        raise HTTPException(status_code=404, detail="diary not found")

    emotions = [
        EmotionItem(emotion=e.emotion, score=float(e.score), is_primary=e.is_primary)
        for e in diary.emotions
    ]

    return DiaryStatusResponse(
        diary_id=diary.id,
        status=diary.status,
        generated_diary_text=diary.generated_diary_text,
        emotions=emotions,
        image_url=diary.image_url,
    )
