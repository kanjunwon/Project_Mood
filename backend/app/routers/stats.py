from datetime import date as date_cls, timedelta
from fastapi import APIRouter, HTTPException
from app.schemas.stats import DailyStatsResponse, MonthlyStatsResponse
from app.services.stats_service import compute_daily_stats, compute_monthly_stats
from app.repositories.diary_repository import get_diaries_by_date_range

router = APIRouter()


@router.get("/stats/daily/{user_id}", response_model=DailyStatsResponse)
def get_daily_stats(user_id: str, date: str = None):
    # date 안 주면 오늘 날짜로 (형식: YYYY-MM-DD)
    target_date = date or date_cls.today().isoformat()
    target = date_cls.fromisoformat(target_date)

    start = target.isoformat()
    end = (target + timedelta(days=1)).isoformat()

    try:
        entries = get_diaries_by_date_range(user_id, start, end)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"통계 조회 중 오류 발생: {str(e)}")

    return compute_daily_stats(entries, target_date)


@router.get("/stats/monthly/{user_id}", response_model=MonthlyStatsResponse)
def get_monthly_stats(user_id: str, year: int, month: int):
    start = f"{year:04d}-{month:02d}-01"
    if month == 12:
        end = f"{year + 1:04d}-01-01"
    else:
        end = f"{year:04d}-{month + 1:02d}-01"

    try:
        entries = get_diaries_by_date_range(user_id, start, end)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"통계 조회 중 오류 발생: {str(e)}")

    return compute_monthly_stats(entries, year, month)
