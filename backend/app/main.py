from dotenv import load_dotenv
load_dotenv()  # 다른 import보다 먼저 실행되어야 함 (환경변수가 뒤늦게 읽히는 버그 방지)

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import diary, stats, personal_test 

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
app.include_router(personal_test.router)


@app.get("/")
def health_check():
    return {"status": "ok"}
