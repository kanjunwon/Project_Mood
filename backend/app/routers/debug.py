"""
app/routers/debug.py
측정 전용 엔드포인트. .env에 ENABLE_DEBUG_ENDPOINTS=true일 때만 main.py에서 등록됨 (기본은 아예 없음).
scripts/measure_image_prompt.py가 이걸 호출해서, 서버를 재시작하지 않고 설정 조합을 바꿔가며
이미지 프롬프트 변환 단계만 반복 측정함. 이미 uvicorn에 로딩된 모델을 그대로 쓰므로 GPU 메모리를 추가로 안 씀.
DB에는 아무것도 저장하지 않음. 그래도 LLM을 돌리는 엔드포인트라 JWT는 필수.
"""
from typing import Dict, List, Optional, Union

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel

from app.dependencies import get_current_user_id

router = APIRouter(prefix="/debug", tags=["debug"])


def _git(*args) -> Optional[str]:
    import subprocess
    from pathlib import Path
    try:
        out = subprocess.run(["git", *args], cwd=Path(__file__).resolve().parent, capture_output=True,
                             text=True, encoding="utf-8", errors="replace", timeout=5)
        return out.stdout.strip() if out.returncode == 0 else None
    except Exception:
        return None


# uvicorn이 이 코드를 읽은 시점(=서버 시작 시점)의 커밋. 체크아웃만 하고 재시작을 안 했는지 확인용
_SERVER_GIT = {"branch": _git("rev-parse", "--abbrev-ref", "HEAD"), "commit": _git("rev-parse", "--short", "HEAD")}


@router.get("/info")
def debug_info(user_id: int = Depends(get_current_user_id)):
    from app.services.llama_service import MOCK_MODE
    return {"server_git": _SERVER_GIT, "mock_mode": MOCK_MODE, "debug_endpoints": True}


class ImagePromptDebugRequest(BaseModel):
    diary_text: str
    who: Union[str, List[str]] = ""
    emotion: str = "편안한"
    where: str = ""
    when: str = ""
    gender: Optional[str] = None
    overrides: Dict[str, Union[str, int, float, bool]] = {}  # get_config()의 키 (mode, max_new_tokens, ...)


def _model_info(cfg: dict) -> dict:
    """GPU에 모델이 제대로 올라가 있는지 (CPU로 일부 내려가 있으면 생성 속도가 크게 떨어짐) + 시스템 프롬프트 토큰 수"""
    info = {}
    try:
        import torch
        from app.models.llama_loader import get_model_and_tokenizer
        from app.services.image_prompt_service import build_system_prompt

        model, tokenizer = get_model_and_tokenizer()
        device_map = getattr(model, "hf_device_map", None) or {}
        devices = sorted({str(v) for v in device_map.values()})
        info["llm_devices"] = devices or [str(model.device)]
        info["llm_dtype"] = str(model.dtype)
        if torch.cuda.is_available():
            info["cuda_devices"] = [
                {
                    "index": i,
                    "name": torch.cuda.get_device_name(i),
                    "allocated_gb": round(torch.cuda.memory_allocated(i) / 1024**3, 2),
                    "total_gb": round(torch.cuda.get_device_properties(i).total_memory / 1024**3, 2),
                }
                for i in range(torch.cuda.device_count())
            ]
        system_prompt = build_system_prompt(cfg["num_examples"], cfg["fixed_negative"])
        info["system_prompt_chars"] = len(system_prompt)
        info["system_prompt_tokens"] = len(tokenizer(system_prompt)["input_ids"])
    except Exception as e:
        info["error"] = repr(e)
    return info


@router.post("/image-prompt")
def debug_image_prompt(request: ImagePromptDebugRequest, user_id: int = Depends(get_current_user_id)):
    from app.services.image_prompt_service import translate_to_image_prompt, get_config

    try:
        cfg = get_config(request.overrides)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    report = {}
    result = translate_to_image_prompt(
        diary_text=request.diary_text,
        who=request.who,
        emotion=request.emotion,
        where=request.where,
        when=request.when,
        gender=request.gender,
        config=request.overrides,
        report=report,
    )
    from app.services.llama_service import MOCK_MODE
    if cfg["mode"] == "llm" and not MOCK_MODE:  # MOCK_MODE에서 부르면 모델(약 21GB)을 받기 시작하므로 금지
        report["model_info"] = _model_info(cfg)
    report["positive"] = result["positive"]
    report["negative"] = result["negative"]
    return report


class DiaryDebugJobRequest(BaseModel):
    what: str
    why: str
    who: Union[str, List[str]]
    when: str
    where: str
    date: Optional[str] = None
    prompt_variant: Optional[str] = None  # llama_service.PROMPT_VARIANTS 키. None이면 기본 프롬프트
    save_db: bool = False  # 기본은 저장 안 함 (측정 job이 보관함에 쌓이지 않게)
    make_image: bool = True  # False면 이미지 생성/업로드 생략 (일기/감정 단계만 측정)


@router.post("/diary-jobs", status_code=202)
def create_debug_diary_job(request: DiaryDebugJobRequest, background_tasks: BackgroundTasks,
                           user_id: int = Depends(get_current_user_id)):
    """
    /generate-diary/jobs와 같은 job 흐름(같은 파이프라인 락, 같은 job 보관소)으로 돌리되,
    프롬프트 변형/DB 저장 여부를 고를 수 있고 결과에 diag(단계별 시간, 시도별 기록, KoBERT 원본 점수)가 붙음.
    """
    import time
    import uuid
    from app.routers import diary as diary_router
    from app.schemas.diary import DiaryRequest
    from app.services.llama_service import PROMPT_VARIANTS

    if request.prompt_variant and request.prompt_variant not in PROMPT_VARIANTS:
        raise HTTPException(status_code=400, detail=f"prompt_variant는 {list(PROMPT_VARIANTS)} 중 하나")
    diary_request = DiaryRequest(what=request.what, why=request.why, who=request.who,
                                 when=request.when, where=request.where, date=request.date)
    entry_date = diary_router._resolve_entry_date(diary_request.date, diary_request.when)

    job_id = uuid.uuid4().hex
    created = time.time()
    with diary_router._JOBS_LOCK:
        diary_router._JOBS[job_id] = {"user_id": user_id, "created": created, "status": "processing",
                                      "result": None, "error": None, "diag": {}}

    def worker():
        diag = diary_router._JOBS[job_id]["diag"]
        try:
            with diary_router._PIPELINE_LOCK:
                diag["lock_acquired_at"] = time.time()
                result = diary_router._run_pipeline(diary_request, user_id, entry_date, diag=diag,
                                                    prompt_variant=request.prompt_variant,
                                                    save_db=request.save_db,
                                                    make_image=request.make_image)
            update = {"status": "done", "result": result, "error": None}
        except HTTPException as e:
            update = {"status": "error", "result": None, "error": str(e.detail)}
        except Exception as e:
            update = {"status": "error", "result": None, "error": repr(e)}
        diag["finished_at"] = time.time()
        with diary_router._JOBS_LOCK:
            diary_router._JOBS[job_id].update(update)

    background_tasks.add_task(worker)
    return {"job_id": job_id, "status": "processing"}


@router.get("/diary-jobs/{job_id}")
def get_debug_diary_job(job_id: str, user_id: int = Depends(get_current_user_id)):
    from app.routers import diary as diary_router

    with diary_router._JOBS_LOCK:
        job = diary_router._JOBS.get(job_id)
        snapshot = dict(job) if job else None
    if snapshot is None or snapshot["user_id"] != user_id:
        raise HTTPException(status_code=404, detail="job 없음")
    diag = dict(snapshot.get("diag") or {})
    if "lock_acquired_at" in diag:
        diag["queue_wait_sec"] = round(diag["lock_acquired_at"] - snapshot["created"], 2)
    if "finished_at" in diag:
        diag["job_total_sec"] = round(diag["finished_at"] - snapshot["created"], 2)
    result = snapshot["result"]
    return {"job_id": job_id, "status": snapshot["status"], "error": snapshot["error"],
            "result": result.model_dump() if result is not None else None, "diag": diag}


class EmotionDebugRequest(BaseModel):
    texts: List[str]


@router.post("/emotion")
def debug_emotion(request: EmotionDebugRequest, user_id: int = Depends(get_current_user_id)):
    """
    같은 일기 문장에 대해 KoBERT 원본 확률과 (요청한 사용자의) 가중치 적용 후 확률을 나란히 돌려줌.
    LLM은 안 씀. 가중치 프로필이 없으면 weight_applied=False이고 weighted는 원본과 같음.
    """
    from app.services.kobert_service import analyze_emotion
    from app.repositories.personal_test_repository import get_latest_weight_profile
    from app.weight_algorithm import apply_weight

    weights = None
    try:
        profile = get_latest_weight_profile(str(user_id))
        weights = profile.get("weights") if profile else None
    except Exception as e:
        print(f"[debug/emotion] 가중치 프로필 조회 실패: {e!r}")

    def top(d, n=5):
        return [[e, round(v, 4)] for e, v in sorted(d.items(), key=lambda x: -x[1])[:n]]

    items = []
    for text in request.texts:
        raw = analyze_emotion(text)["scores"] or {}
        weighted = apply_weight(raw, weights) if (weights and raw) else dict(raw)
        items.append({
            "text": text,
            "raw_top": top(raw),
            "weighted_top": top(weighted),
            "weights_of_top": {e: round(weights.get(e, 1.0), 3) for e, _ in top(raw, 3) + top(weighted, 3)}
            if weights else None,
        })
    return {"weight_applied": bool(weights), "items": items}


@router.get("/last-pipeline-timings")
def last_pipeline_timings(user_id: int = Depends(get_current_user_id)):
    from app.routers.diary import LAST_PIPELINE_TIMINGS
    return dict(LAST_PIPELINE_TIMINGS)
