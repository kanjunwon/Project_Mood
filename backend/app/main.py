from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import diary

app = FastAPI(title="감정 서가 API")

# 나중에 프론트(종현)에서 이 API 호출할 때 막히지 않게 미리 열어둠
# 배포 직전엔 "*" 대신 실제 프론트 도메인으로 좁히는 게 안전함
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(diary.router)


@app.get("/")
def health_check():
    return {"status": "ok"}
