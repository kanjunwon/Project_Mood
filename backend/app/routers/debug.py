"""
app/routers/debug.py
측정 전용 엔드포인트. .env에 ENABLE_DEBUG_ENDPOINTS=true일 때만 main.py에서 등록됨 (기본은 아예 없음).
scripts/measure_image_prompt.py가 이걸 호출해서, 서버를 재시작하지 않고 설정 조합을 바꿔가며
이미지 프롬프트 변환 단계만 반복 측정함. 이미 uvicorn에 로딩된 모델을 그대로 쓰므로 GPU 메모리를 추가로 안 씀.
DB에는 아무것도 저장하지 않음. 그래도 LLM을 돌리는 엔드포인트라 JWT는 필수.
"""
from typing import Dict, List, Optional, Union

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.dependencies import get_current_user_id

router = APIRouter(prefix="/debug", tags=["debug"])


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


@router.get("/last-pipeline-timings")
def last_pipeline_timings(user_id: int = Depends(get_current_user_id)):
    from app.routers.diary import LAST_PIPELINE_TIMINGS
    return dict(LAST_PIPELINE_TIMINGS)
