from dotenv import load_dotenv
load_dotenv()

import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import diary, stats, personal_test, auth, profile, account

app = FastAPI(title="감정 서가 API")

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
