import os
import re
import threading
import time
import uuid
from datetime import date as date_cls, datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from app.dependencies import get_current_user_id
from app.schemas.diary import DiaryRequest, DiaryResponse, DiaryJobCreated, DiaryJobStatus
from app.services.llama_service import generate_diary_text
from app.services.kobert_service import analyze_emotion
from app.repositories.diary_repository import save_diary, get_diary_by_user
from app.repositories.user_repository import get_user_by_id
from app.repositories.personal_test_repository import get_latest_weight_profile
from app.weight_algorithm import apply_weight

router = APIRouter()

MOCK_MODE = os.environ.get("MOCK_MODE", "false").lower() == "true"

# 가장 최근 /generate-diary 요청의 단계별 소요시간(초). 서버 로그에도 찍고,
# 측정 스크립트는 /debug/last-pipeline-timings로 읽어감 (ENABLE_DEBUG_ENDPOINTS=true일 때만)
LAST_PIPELINE_TIMINGS: dict = {}

KST = timezone(timedelta(hours=9))

# 이미지 생성은 GPU 1장을 쓰므로 동시에 여러 개 돌리지 않고 한 번에 하나씩 처리 (나머지는 대기)
_PIPELINE_LOCK = threading.Semaphore(1)

# 비동기 작업(job) 보관소. 서버 프로세스 메모리에만 있음 (uvicorn 워커 1개 기준).
# 서버를 재시작하면 진행 중이던 job 조회는 404가 되지만, 일기는 이미 DB에 저장돼 있음.
_JOBS: dict = {}
_JOBS_LOCK = threading.Lock()
JOB_TTL_SEC = 3600


_MONTH_DAY = re.compile(r"(\d{1,2})\s*월\s*(\d{1,2})\s*일")


def _date_from_when(when: Optional[str]) -> Optional[date_cls]:
    """
    앱이 date를 따로 안 보내던 시절(현재 APK) 호환용.
    when 문자열("10월 3일 금요일 오후 2시")에서 월/일을 읽어 올해 날짜로 만든다. 못 읽으면 None.
    """
    m = _MONTH_DAY.search(when or "")
    if not m:
        return None
    try:
        return date_cls(datetime.now(KST).year, int(m.group(1)), int(m.group(2)))
    except ValueError:
        return None


def _resolve_entry_date(raw: Optional[str], when: Optional[str] = None) -> Optional[date_cls]:
    """
    일기 날짜 결정. 우선순위: 요청의 date(YYYY-MM-DD) -> when 문자열에서 읽은 월/일 -> None(=오늘).
    미래 날짜는 거절 (기준: 한국 시간 오늘).
    """
    if raw:
        try:
            d = date_cls.fromisoformat(str(raw).strip()[:10])
        except ValueError:
            raise HTTPException(status_code=400, detail="date는 YYYY-MM-DD 형식이어야 합니다")
    else:
        d = _date_from_when(when)
        if d is None:
            return None
    if d > datetime.now(KST).date():
        raise HTTPException(status_code=400, detail="미래 날짜의 일기는 작성할 수 없습니다")
    return d


def _created_at_for(entry_date: Optional[date_cls]) -> Optional[str]:
    """
    오늘이거나 날짜 미지정이면 None (DB 기본값 now() 사용 = 기존 동작 그대로).
    과거 날짜면 그 날짜로 created_at을 지정한다.
    통계/보관함이 created_at의 앞 10글자(UTC 기준 날짜)로 날짜를 묶기 때문에,
    한국 시간 09:00~23:59 사이로 잡아야 UTC 날짜와 한국 날짜가 같아진다.
    """
    if entry_date is None or entry_date == datetime.now(KST).date():
        return None
    now = datetime.now(KST)
    seconds_in_window = (now.hour * 3600 + now.minute * 60 + now.second) % (14 * 3600)
    stamp = datetime.combine(entry_date, datetime.min.time(), tzinfo=KST) + timedelta(
        hours=9, seconds=seconds_in_window
    )
    return stamp.isoformat()


def _run_pipeline(request: DiaryRequest, user_id: int, entry_date: Optional[date_cls],
                  diag: Optional[dict] = None, prompt_variant: Optional[str] = None,
                  save_db: bool = True) -> DiaryResponse:
    """
    일기 생성 -> 감정 분석 -> 가중치 -> 이미지 -> DB 저장. 동기 /generate-diary와 job 방식이 같이 씀.
    diag: dict를 넘기면 단계별 시간, 일기 시도별 기록, KoBERT 원본 점수를 채워줌 (측정용, 동작은 그대로)
    prompt_variant: 측정용 일기 프롬프트 변형. 일반 엔드포인트는 항상 None(기본 프롬프트)
    save_db: False면 DB 저장만 건너뜀 (측정 job이 사용자 보관함에 쌓이지 않게). 일반 엔드포인트는 항상 True
    """
    timings = diag if diag is not None else {}
    t_start = time.time()

    # user_id는 body가 아니라 로그인 토큰에서만 가져옴. 이 값으로 프로필(아바타 설정)도
    # 같이 조회해서 이미지 생성에 반영.
    profile = get_user_by_id(user_id) or {}
    glasses = profile.get("glasses") or "none"
    bangs = profile.get("bangs", True)
    hair_length = profile.get("hair_length", "medium")
    hair_color = profile.get("hair_color", "black")
    gender = profile.get("gender")  # IMAGE_PROMPT_MODE=template일 때만 쓰임
    timings["profile_sec"] = round(time.time() - t_start, 2)

    t = time.time()
    try:
        diary_text, failed = generate_diary_text(
            what=request.what,
            why=request.why,
            who=request.who,
            when=request.when,
            where=request.where,
            timings=timings,
            prompt_variant=prompt_variant,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"일기 생성 중 오류 발생: {str(e)}")
    timings["diary_total_sec"] = round(time.time() - t, 2)

    who_str = ", ".join(request.who) if isinstance(request.who, list) else request.who

    t = time.time()
    try:
        emotion_result = analyze_emotion(diary_text)
    except Exception as e:
        print(f"감정 분석 실패: {e}")
        emotion_result = {"top_emotion": None, "scores": None, "sentiment_score": None}
    timings["kobert_sec"] = round(time.time() - t, 2)

    # 퍼스널 검사 기반 가중치 적용 (종현 설계, 2026-09-24 확정: 정서가x연속값 각성도, alpha=0.4)
    # 검사를 한 번도 안 했거나 KoBERT 자체가 실패한 경우엔 원본(KoBERT raw) 그대로 사용.
    timings["kobert_raw_scores"] = dict(emotion_result["scores"]) if emotion_result.get("scores") else None
    timings["weight_applied"] = False
    if emotion_result.get("scores"):
        try:
            weight_profile = get_latest_weight_profile(str(user_id))
            if weight_profile and weight_profile.get("weights"):
                timings["weight_applied"] = True
                adjusted_scores = apply_weight(emotion_result["scores"], weight_profile["weights"])
                emotion_result["scores"] = adjusted_scores
                emotion_result["top_emotion"] = max(adjusted_scores, key=adjusted_scores.get)
        except Exception as e:
            print(f"가중치 적용 실패 (KoBERT 원본 결과 그대로 사용): {e}")

    # SD3 이미지 생성 - 실패해도 일기 자체는 정상 응답되게 try/except로 감쌈
    image_url = None
    t = time.time()
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
                gender=gender,
                timings=timings,
            )
        except Exception as e:
            print(f"이미지 생성 실패 (일기 생성은 성공): {e}")
    timings["image_total_sec"] = round(time.time() - t, 2)

    t = time.time()
    saved_id = None
    try:
        row = {
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
        }
        created_at = _created_at_for(entry_date)
        if created_at:
            row["created_at"] = created_at
        saved = save_diary(row) if save_db else None
        if saved:
            saved_id = saved[0].get("id")
    except Exception as e:
        print(f"DB 저장 실패 (일기 생성은 성공): {e}")
    timings["db_save_sec"] = round(time.time() - t, 2)
    timings["total_sec"] = round(time.time() - t_start, 2)

    print(
        "  [TIMING] /generate-diary "
        f"전체 {timings['total_sec']}초 = "
        f"일기생성 {timings['diary_total_sec']}초"
        f"(LLM {timings.get('diary_llm_sec')}초, 검증 {timings.get('diary_validate_sec')}초, {timings.get('diary_attempts')}회 시도) + "
        f"KoBERT {timings['kobert_sec']}초 + "
        f"이미지 {timings['image_total_sec']}초"
        f"(프롬프트 변환 {timings.get('image_prompt_sec')}초, ComfyUI {timings.get('comfyui_sec')}초, "
        f"업로드 {timings.get('upload_sec')}초) + "
        f"DB저장 {timings['db_save_sec']}초 + 프로필조회 {timings['profile_sec']}초"
    )
    LAST_PIPELINE_TIMINGS.clear()
    LAST_PIPELINE_TIMINGS.update(timings)

    return DiaryResponse(
        status="success",
        generated_diary=diary_text,
        validation_failed=failed,
        top_emotion=emotion_result["top_emotion"],
        emotion_scores=emotion_result["scores"],
        sentiment_score=emotion_result["sentiment_score"],
        image_url=image_url,
        id=saved_id,
    )


@router.post("/generate-diary", response_model=DiaryResponse)
def generate_diary(request: DiaryRequest, user_id: int = Depends(get_current_user_id)):
    """기존 방식(요청 한 번에 결과까지). 100초 넘으면 RunPod 프록시가 524를 주므로 앱은 jobs 방식 권장."""
    entry_date = _resolve_entry_date(request.date, request.when)
    with _PIPELINE_LOCK:
        return _run_pipeline(request, user_id, entry_date)


def _cleanup_jobs() -> None:
    now = time.time()
    with _JOBS_LOCK:
        for jid in [j for j, v in _JOBS.items() if now - v["created"] > JOB_TTL_SEC]:
            del _JOBS[jid]


def _job_worker(job_id: str, request: DiaryRequest, user_id: int, entry_date: Optional[date_cls]) -> None:
    with _JOBS_LOCK:
        diag = _JOBS[job_id].setdefault("diag", {}) if job_id in _JOBS else {}
    try:
        with _PIPELINE_LOCK:
            diag["lock_acquired_at"] = time.time()  # 앞 작업 대기시간과 실제 처리시간을 구분하려고
            result = _run_pipeline(request, user_id, entry_date, diag=diag)
        update = {"status": "done", "result": result, "error": None}
    except HTTPException as e:
        update = {"status": "error", "result": None, "error": str(e.detail)}
    except Exception as e:
        update = {"status": "error", "result": None, "error": f"일기 생성 중 오류 발생: {e}"}
    with _JOBS_LOCK:
        if job_id in _JOBS:
            _JOBS[job_id].update(update)


@router.post("/generate-diary/jobs", response_model=DiaryJobCreated, status_code=202)
def create_diary_job(request: DiaryRequest, background_tasks: BackgroundTasks,
                     user_id: int = Depends(get_current_user_id)):
    """
    일기 생성을 백그라운드로 시작하고 job_id를 바로 돌려준다 (1초 이내).
    앱은 GET /generate-diary/jobs/{job_id}를 2~3초마다 조회하다가 status가 done이면
    result(일기+그림)를 한 번에 화면에 보여주면 된다.
    날짜 오류(미래 날짜 등)는 여기서 바로 400.
    """
    entry_date = _resolve_entry_date(request.date, request.when)
    _cleanup_jobs()
    job_id = uuid.uuid4().hex
    with _JOBS_LOCK:
        _JOBS[job_id] = {"user_id": user_id, "created": time.time(),
                         "status": "processing", "result": None, "error": None}
    background_tasks.add_task(_job_worker, job_id, request, user_id, entry_date)
    return DiaryJobCreated(job_id=job_id, status="processing")


@router.get("/generate-diary/jobs/{job_id}", response_model=DiaryJobStatus)
def get_diary_job(job_id: str, user_id: int = Depends(get_current_user_id)):
    with _JOBS_LOCK:
        job = _JOBS.get(job_id)
        snapshot = dict(job) if job else None
    # 남의 job_id로는 존재 여부도 알 수 없게 404로 통일
    if snapshot is None or snapshot["user_id"] != user_id:
        raise HTTPException(status_code=404, detail="job을 찾을 수 없습니다 (만료되었거나 서버가 재시작됨). /diaries/me로 확인하세요")
    return DiaryJobStatus(job_id=job_id, status=snapshot["status"],
                          result=snapshot["result"], error=snapshot["error"])


@router.get("/diaries/me")
def get_my_diaries(user_id: int = Depends(get_current_user_id)):
    try:
        diaries = get_diary_by_user(str(user_id))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"조회 중 오류 발생: {str(e)}")

    return {"status": "success", "diaries": diaries}