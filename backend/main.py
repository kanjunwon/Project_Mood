from fastapi import FastAPI, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from database import get_db
from routers import diaries

app = FastAPI(title="Project Mood API")
app.include_router(diaries.router)


@app.get("/")
def root():
    return {"message": "Project Mood API is running"}


@app.get("/health/db")
def check_db_connection(db: Session = Depends(get_db)):
    """DB 연결이 잘 되는지 확인하는 테스트용 엔드포인트"""
    try:
        db.execute(text("SELECT 1"))
        return {"status": "ok", "db_connected": True}
    except Exception as e:
        return {"status": "error", "db_connected": False, "detail": str(e)}


# 앞으로 이 아래에 실제 라우터(예: /api/v1/diaries)를 추가하게 될 예정