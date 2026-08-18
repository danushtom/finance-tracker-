from __future__ import annotations

from datetime import date


def last_n_months(today: date, n: int) -> list[str]:
    """Returns the last `n` month keys ("YYYY-MM"), most recent (the month
    containing `today`) first."""
    months = []
    year, month = today.year, today.month
    for _ in range(n):
        months.append(f"{year:04d}-{month:02d}")
        month -= 1
        if month == 0:
            month, year = 12, year - 1
    return months
