"""What we measure, and what we refuse to measure.

The strategy doc names a north-star metric and kill criteria. A product that
cannot compute them is guessing, so every sit-down writes one event.

**Nothing here touches content.** Not the code, not the file path, not the repo
name, not the text of a finding, not a model's raw output. A tool whose pitch is
"your code never leaves your account" does not get to make an exception for its
own analytics. What we keep is shape: which Families sat, who agreed, what it
cost, and whether the fix survived verification.

The prototype writes to a local JSONL file and makes no network calls at all.
The hosted version would ship the same records to a collector -- the schema is
already safe to transmit, which is the point of designing it this way first.
"""
from __future__ import annotations

import json
import os
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

HOME = Path(os.environ.get("GRUMPY_HOME", Path.home() / ".grumpy"))
EVENTS = HOME / "events.jsonl"
INSTALL = HOME / "install_id"

# One switch, honoured everywhere.
DISABLED = os.environ.get("GRUMPY_NO_TELEMETRY", "").lower() in {"1", "true", "yes"}


def install_id() -> str:
    """A random per-machine id. Not derived from anything about the user."""
    try:
        HOME.mkdir(parents=True, exist_ok=True)
        if INSTALL.exists():
            return INSTALL.read_text().strip()
        new = uuid.uuid4().hex
        INSTALL.write_text(new)
        INSTALL.chmod(0o600)
        return new
    except OSError:
        return "unknown"


def classify_error(message: str) -> str:
    """Errors can quote a model's raw output, which can quote the user's code.
    So we store a category, never the message."""
    lowered = message.lower()
    for needle, label in (
        ("could not parse json", "bad_output_shape"),
        ("accessdenied", "no_model_access"),
        ("throttl", "throttled"),
        ("timeout", "timeout"),
        ("validationexception", "invalid_request"),
        ("credential", "no_credentials"),
    ):
        if needle in lowered:
            return label
    return "other"


def record(result, *, surface: str, elapsed_ms: int, don: str, commission: list[str]) -> None:
    """One line per sit-down. Never raises -- analytics must not break a review."""
    if DISABLED:
        return
    try:
        issues = result.issues
        event = {
            "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "install_id": install_id(),
            "surface": surface,
            # Shape of the input, not the input.
            "file_ext": Path(result.filename).suffix or "none",
            "loc": result.original.count("\n") + 1,
            # Who sat, and who could not.
            "don": don,
            "commission": list(commission),
            "families_seated": result.review.committee_size,
            "families_failed": {
                model: classify_error(err) for model, err in result.committee_errors.items()
            },
            # Did agreement actually happen? This is the assumption under the product.
            "findings_raw": sum(len(i.findings) for i in result.review.issues),
            "issues_published": len(issues),
            "unanimous": sum(1 for i in issues if i.agreement == result.review.committee_size),
            "corroborated": sum(1 for i in issues if i.agreement >= 2),
            "contested": sum(1 for i in issues if i.contested),
            "struck_by_don": result.suppressed,
            "severity": {
                level: sum(1 for i in issues if i.severity == level)
                for level in ("high", "medium", "low")
            },
            # Per-Family contribution: who earns their seat.
            "raised_by": {
                model: sum(
                    1 for i in issues if any(f.model_id == model for f in i.findings)
                )
                for model in commission
            },
            "consolidated_by": result.review.method,
            "fix_offered": bool(result.review.fixed_code),
            "fix_status": result.verdict.label if result.verdict else "none",
            "elapsed_ms": elapsed_ms,
        }
        HOME.mkdir(parents=True, exist_ok=True)
        with EVENTS.open("a") as handle:
            handle.write(json.dumps(event) + "\n")
    except Exception:
        pass  # a broken counter must never cost the user a review


def load(path: Path | None = None) -> list[dict]:
    target = path or EVENTS
    if not target.exists():
        return []
    rows = []
    for line in target.read_text().splitlines():
        line = line.strip()
        if line:
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return rows


def now_ms() -> int:
    return int(time.monotonic() * 1000)
