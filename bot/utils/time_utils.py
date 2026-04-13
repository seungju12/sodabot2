from __future__ import annotations

from calendar import monthrange
from dataclasses import dataclass
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

KST = ZoneInfo("Asia/Seoul")
TIME_FORMAT = "%Y-%m-%d %H:%M:%S"


@dataclass(slots=True)
class Period:
    year: int
    month: int
    half: int
    start_day: int
    end_day: int

    @property
    def key(self) -> str:
        return f"{self.year:04d}-{self.month:02d}-{self.half}"



def now_kst() -> datetime:
    return datetime.now(KST)



def format_kst(dt: datetime) -> str:
    return dt.astimezone(KST).strftime(TIME_FORMAT)



def get_period_for_date(dt: datetime) -> Period:
    dt = dt.astimezone(KST)
    last_day = monthrange(dt.year, dt.month)[1]
    split_day = 14 if dt.month == 2 else 15
    if dt.day <= split_day:
        return Period(dt.year, dt.month, 1, 1, split_day)
    return Period(dt.year, dt.month, 2, split_day + 1, last_day)



def get_previous_period(dt: datetime) -> Period:
    current = get_period_for_date(dt)
    if current.half == 2:
        split_day = 14 if current.month == 2 else 15
        last_day = monthrange(current.year, current.month)[1]
        return Period(current.year, current.month, 1, 1, split_day)

    prev_month = 12 if current.month == 1 else current.month - 1
    prev_year = current.year - 1 if current.month == 1 else current.year
    prev_last_day = monthrange(prev_year, prev_month)[1]
    split_day = 14 if prev_month == 2 else 15
    return Period(prev_year, prev_month, 2, split_day + 1, prev_last_day)



def is_auto_warning_run_time(dt: datetime) -> bool:
    dt = dt.astimezone(KST)
    if dt.hour != 0 or dt.minute != 0:
        return False
    return dt.day == 1 or dt.day == 16 or (dt.month == 2 and dt.day == 15)



def get_notice_target_date(dt: datetime) -> bool:
    """알림을 보낼 시간인지 확인 (1회만 보내기 위해 bool 반환)
    
    기간 종료 3일 전에 알림:
    - 일반 월: 12일(1차 15일 종료 -3), 말일-3(2차 말일 종료 -3)
    - 2월: 11일(1차 14일 종료 -3), 말일-3(2차 말일 종료 -3)
    """
    dt = dt.astimezone(KST)
    last_day = monthrange(dt.year, dt.month)[1]
    if dt.month == 2:
        target_days = [11, last_day - 3]  # 2월: 11일(14-3), 25/26일(28/29-3)
    else:
        target_days = [12, last_day - 3]  # 일반 월: 12일(15-3), 말일-3
    return dt.day in target_days and dt.hour == 0 and dt.minute == 0
