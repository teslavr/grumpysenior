"""Turning the event log into the numbers the strategy doc promised.

Each metric here answers a question that was written down before the data
existed -- which is the only way a metric is worth anything.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass, field


@dataclass
class Metrics:
    runs: int = 0
    users: int = 0
    files_reviewed: int = 0
    total_issues: int = 0
    # "Do vendors describe the same defect similarly enough to agree?"
    # If this collapses, the product has no floor. It is the first kill signal.
    corroboration_rate: float = 0.0
    unanimity_rate: float = 0.0
    # "Does the no-veto rule earn its keep, or is it just noise?"
    contested_rate: float = 0.0
    struck_by_don: int = 0
    # "Do fixes survive mechanical verification?" -- proxy for the north star
    # until merge tracking exists.
    fix_offer_rate: float = 0.0
    fix_verified_rate: float = 0.0
    # "Does anyone come back?"
    runs_per_user: float = 0.0
    repeat_user_rate: float = 0.0
    median_seconds: float = 0.0
    per_family: dict = field(default_factory=dict)
    failures: Counter = field(default_factory=Counter)
    severity: Counter = field(default_factory=Counter)
    surfaces: Counter = field(default_factory=Counter)
    by_day: dict = field(default_factory=dict)


def _median(values: list[float]) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    mid = len(ordered) // 2
    return ordered[mid] if len(ordered) % 2 else (ordered[mid - 1] + ordered[mid]) / 2


def compute(events: list[dict]) -> Metrics:
    m = Metrics()
    if not events:
        return m

    m.runs = len(events)
    per_user = Counter(e.get("install_id", "unknown") for e in events)
    m.users = len(per_user)
    m.runs_per_user = round(m.runs / m.users, 1)
    m.repeat_user_rate = round(sum(1 for n in per_user.values() if n > 1) / m.users, 2)
    m.files_reviewed = m.runs

    issues = sum(e.get("issues_published", 0) for e in events)
    m.total_issues = issues
    if issues:
        m.corroboration_rate = round(sum(e.get("corroborated", 0) for e in events) / issues, 2)
        m.unanimity_rate = round(sum(e.get("unanimous", 0) for e in events) / issues, 2)
        m.contested_rate = round(sum(e.get("contested", 0) for e in events) / issues, 2)
    m.struck_by_don = sum(e.get("struck_by_don", 0) for e in events)

    offered = [e for e in events if e.get("fix_offered")]
    m.fix_offer_rate = round(len(offered) / m.runs, 2)
    if offered:
        m.fix_verified_rate = round(
            sum(1 for e in offered if e.get("fix_status") == "verified") / len(offered), 2
        )

    m.median_seconds = round(_median([e.get("elapsed_ms", 0) / 1000 for e in events]), 1)

    seated: Counter = Counter()
    raised: Counter = Counter()
    failed: Counter = Counter()
    for e in events:
        for model in e.get("commission", []):
            seated[model] += 1
        for model, count in (e.get("raised_by") or {}).items():
            raised[model] += count
        for model, reason in (e.get("families_failed") or {}).items():
            failed[model] += 1
            m.failures[reason] += 1
        for level, count in (e.get("severity") or {}).items():
            m.severity[level] += count
        m.surfaces[e.get("surface", "unknown")] += 1
        day = (e.get("ts") or "")[:10]
        if day:
            m.by_day[day] = m.by_day.get(day, 0) + 1

    # Per-Family: does this seat earn its keep, or does it mostly fail to show?
    m.per_family = {
        model: {
            "sat": seated[model],
            "findings": raised.get(model, 0),
            "findings_per_sitting": round(raised.get(model, 0) / seated[model], 2) if seated[model] else 0.0,
            "failures": failed.get(model, 0),
            "failure_rate": round(failed.get(model, 0) / seated[model], 2) if seated[model] else 0.0,
        }
        for model in seated
    }
    return m
