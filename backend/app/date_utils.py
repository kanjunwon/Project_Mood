"""
일기 날짜는 전부 한국 날짜(Asia/Seoul) 기준으로 판단한다.
앱이 서울 시간 기준으로 날짜를 표시/집계하므로, 서버도 created_at을 UTC 날짜가 아니라
한국 날짜로 바꿔서 묶어야 새벽(00~09시)에 쓴 일기가 전날로 잡히지 않는다.
"""
import re
from datetime import date as date_cls, datetime, timedelta, timezone
from typing import Optional

KST = timezone(timedelta(hours=9))

_FRACTION = re.compile(r"\.(\d+)")


def today_kst() -> date_cls:
    return datetime.now(KST).date()


def kst_day_start(d) -> str:
    """'YYYY-MM-DD'(또는 date) -> 그 날 한국 시간 0시의 ISO 문자열. timestamptz 비교에 그대로 넘기면 됨."""
    if not isinstance(d, date_cls):
        d = date_cls.fromisoformat(str(d)[:10])
    return datetime.combine(d, datetime.min.time(), tzinfo=KST).isoformat()


def kst_date_of(created_at: Optional[str]) -> Optional[str]:
    """
    DB의 created_at 문자열 -> 한국 날짜 'YYYY-MM-DD'.
    타임존이 없는 값은 UTC로 간주 (Supabase timestamptz는 항상 +00:00으로 내려옴).
    파싱이 안 되면 앞 10글자를 그대로 씀 (예전 동작).
    """
    if not created_at:
        return None
    s = str(created_at).strip().replace("Z", "+00:00")
    # Python 3.10 이하 fromisoformat은 소수점 자리가 3/6자리가 아니면 실패해서 6자리로 맞춤
    s = _FRACTION.sub(lambda m: "." + m.group(1)[:6].ljust(6, "0"), s, count=1)
    try:
        dt = datetime.fromisoformat(s)
    except ValueError:
        return s[:10]
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(KST).date().isoformat()
