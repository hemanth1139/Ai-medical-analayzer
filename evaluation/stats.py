"""Statistical helpers for evaluation reporting."""

import math
from typing import Iterable, Optional


def mean(values: Iterable[float]) -> float:
    vals = list(values)
    if not vals:
        return 0.0
    return sum(vals) / len(vals)


def std_dev(values: Iterable[float]) -> float:
    vals = list(values)
    n = len(vals)
    if n < 2:
        return 0.0
    m = mean(vals)
    variance = sum((x - m) ** 2 for x in vals) / (n - 1)
    return math.sqrt(variance)


def summarize(values: Iterable[float], label: str = "metric") -> dict:
    vals = list(values)
    if not vals:
        return {
            "label": label,
            "n": 0,
            "mean": 0.0,
            "std": 0.0,
            "min": 0.0,
            "max": 0.0,
        }
    return {
        "label": label,
        "n": len(vals),
        "mean": round(mean(vals), 3),
        "std": round(std_dev(vals), 3),
        "min": round(min(vals), 3),
        "max": round(max(vals), 3),
    }


def format_mean_std(values: Iterable[float], decimals: int = 2) -> str:
    vals = list(values)
    if not vals:
        return "N/A"
    m = mean(vals)
    s = std_dev(vals)
    if len(vals) < 2:
        return f"{m:.{decimals}f}"
    return f"{m:.{decimals}f} ± {s:.{decimals}f}"


def pass_rate(flags: Iterable[bool]) -> float:
    vals = list(flags)
    if not vals:
        return 0.0
    return round(100.0 * sum(1 for f in vals if f) / len(vals), 1)
