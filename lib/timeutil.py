"""Time helpers — everything user-facing is Asia/Jakarta (WIB, UTC+7)."""
from __future__ import annotations

from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from lib.config import TIMEZONE

TZ = ZoneInfo(TIMEZONE)


def now_tz() -> datetime:
    return datetime.now(TZ)


def epoch_to_tz(epoch: float) -> datetime:
    return datetime.fromtimestamp(epoch, tz=timezone.utc).astimezone(TZ)


def fmt_age(seconds: float) -> str:
    s = int(max(0, seconds))
    if s < 60:
        return f"{s}s ago"
    if s < 3600:
        return f"{s // 60}m {s % 60}s ago"
    return f"{s // 3600}h {(s % 3600) // 60}m ago"
