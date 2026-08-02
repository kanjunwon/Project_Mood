from fastapi import FastAPI
from app.routers import diary

app = FastAPI(title="감정 서가 API")

app.include_router(diary.router)


@app.get("/")
def health_check():
    return {"status": "ok"}
