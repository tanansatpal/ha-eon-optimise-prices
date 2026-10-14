"""Validate app periods without copying prices into uncovered intervals."""

import math
from datetime import datetime, timedelta, timezone


def parse_time(value):
    """Require a timezone-aware ISO timestamp and return UTC."""
    if not isinstance(value, str):
        raise ValueError("Price timestamp is not text")
    result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if result.tzinfo is None:
        raise ValueError("Price timestamp has no timezone")
    return result.astimezone(timezone.utc)


def normalise_response(payload):
    """Convert provider cost signs to import cost and export earnings in pence.

    This endpoint's MarketPeriods are half-hourly. Reject other alignment rather
    than silently treating five-minute periods as half-hour prices. Forecasts are
    provider forecasts, not final settlement rates; preserve their provenance.
    """
    if not isinstance(payload, dict) or payload.get("errors"):
        raise ValueError("Price service returned GraphQL errors")
    windows = payload["data"]["sitePricing"]["meterWindows"]
    if not isinstance(windows, list):
        raise ValueError("Invalid price channels")
    result = {}
    for window in windows:
        if not isinstance(window, dict):
            raise ValueError("Invalid price channel")
        direction = {"GENERAL": "import", "FEED_IN": "export"}.get(window["usageType"])
        if direction is None:
            continue
        if direction in result:
            raise ValueError("Ambiguous duplicate price channel")
        periods = {}
        groups = (
            ("previousPeriods", "history"),
            ("forecastPeriods", "forecast"),
            ("currentPeriod", "current"),
        )
        for key, quality in groups:
            entries = [window.get(key)] if key == "currentPeriod" else window.get(key, [])
            for period in entries:
                if period is None:
                    continue
                if not isinstance(period, dict):
                    raise ValueError("Invalid price period")
                start = parse_time(period["start"])
                if start.minute not in (0, 30) or start.second or start.microsecond:
                    raise ValueError("Price period is not half-hour aligned")
                price = period["kwhPriceInCents"]
                if (
                    isinstance(price, bool)
                    or not isinstance(price, (int, float))
                    or not math.isfinite(price)
                ):
                    raise ValueError("Price is not finite numeric data")
                price = -price if direction == "export" else price
                estimate = period.get("estimate")
                if estimate is not None and not isinstance(estimate, bool):
                    raise ValueError("Invalid price estimate flag")
                row = {
                    "valid_from": start.isoformat(),
                    "valid_to": (start + timedelta(minutes=30)).isoformat(),
                    "value_inc_vat": price,
                    "source_quality": quality,
                    "provider_estimate": estimate,
                }
                if start in periods and periods[start]["value_inc_vat"] != price:
                    raise ValueError("Conflicting prices for the same interval")
                periods[start] = row
        result[direction] = [periods[key] for key in sorted(periods)]
    if set(result) != {"import", "export"} or not all(result.values()):
        raise ValueError("Both import and export price channels are required")
    return result


def coverage(rates, now):
    """Return the current price and the end of contiguous provider coverage."""
    current = next(
        (r for r in rates if parse_time(r["valid_from"]) <= now < parse_time(r["valid_to"])), None
    )
    until = parse_time(current["valid_to"]) if current else None
    if until:
        for row in rates:
            if parse_time(row["valid_from"]) == until:
                until = parse_time(row["valid_to"])
    return current, until.isoformat() if until else None
