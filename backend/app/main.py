from dotenv import load_dotenv
load_dotenv()

import os
import time
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import diary, stats, personal_test, auth, profile, account



@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    서버 시작 때 LLM/KoBERT를 미리 GPU에 올림.
    안 하면 서버 재시작 후 '첫 요청'이 모델 로딩(약 1~2분)까지 떠안아서 앱에서 실패로 보임.
    - MOCK_MODE=true 이거나 PRELOAD_MODELS=false 면 건너뜀 (로컬 개발/테스트용)
    - 로딩이 끝나야 "Application startup complete"가 뜸 (그 전엔 요청을 안 받음)
    - 로딩 실패해도 서버는 뜨게 하고, 첫 요청 때 예전처럼 다시 시도함
    """
    mock = os.environ.get("MOCK_MODE", "false").lower() == "true"
    preload = os.environ.get("PRELOAD_MODELS", "true").lower() != "false"
    if preload and not mock:
        start = time.time()
        try:
            from app.models.llama_loader import get_model_and_tokenizer as load_llm
            from app.models.kobert_loader import get_model_and_tokenizer as load_kobert
            load_llm()
            load_kobert()
            print(f"[시작] 모델 미리 로딩 완료 ({time.time() - start:.1f}초)")
        except Exception as e:
            print(f"[경고] 모델 미리 로딩 실패, 첫 요청 때 다시 시도함: {e!r}")
    yield


app = FastAPI(title="감정 서가 API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(diary.router)
app.include_router(stats.router)
app.include_router(auth.router)
app.include_router(personal_test.router)
app.include_router(profile.router)
app.include_router(account.router)

# 측정 전용 엔드포인트 (/debug/*) - 기본은 등록 안 함. 측정할 때만 .env에 ENABLE_DEBUG_ENDPOINTS=true
if os.environ.get("ENABLE_DEBUG_ENDPOINTS", "false").lower() == "true":
    from app.routers import debug
    app.include_router(debug.router)
    print("[주의] /debug/* 측정용 엔드포인트가 켜져 있음 (측정 끝나면 ENABLE_DEBUG_ENDPOINTS 지우기)")


@app.get("/")
def health_check():
    return {"status": "ok"}
