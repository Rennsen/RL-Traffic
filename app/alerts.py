from __future__ import annotations

from datetime import datetime, timezone
import uuid
from typing import Any, Dict, List

from .config import DISTRICT_PROFILES
from .store import latest_runs_by_district

THRESHOLDS = {
    "avg_queue": 250.0,
    "avg_wait": 60.0,
    "emergency_avg_wait": 12.0,
    "clearance_ratio": 0.68,
}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _severity(value: float, threshold: float, higher_is_bad: bool = True) -> str:
    if higher_is_bad:
        delta = (value - threshold) / max(threshold, 1e-6)
    else:
        delta = (threshold - value) / max(threshold, 1e-6)
    if delta > 0.25:
        return "high"
    if delta > 0.1:
        return "medium"
    return "low"


def build_alerts() -> List[Dict[str, Any]]:
    alerts: List[Dict[str, Any]] = []
    latest = latest_runs_by_district()

    for district_id, district in DISTRICT_PROFILES.items():
        run = latest.get(district_id)
        if not run:
            continue

        metrics = run.get("comparison", {}).get("rl", {})
        created_at = run.get("created_at", _now_iso())

        avg_queue = float(metrics.get("avg_queue", 0.0))
        if avg_queue > THRESHOLDS["avg_queue"]:
            alerts.append(
                {
                    "alert_id": str(uuid.uuid4()),
                    "district_id": district_id,
                    "title": f"{district['name']} queue spike",
                    "message": f"Average queue length exceeded {THRESHOLDS['avg_queue']} vehicles.",
                    "severity": _severity(avg_queue, THRESHOLDS["avg_queue"], True),
                    "metric": "avg_queue",
                    "value": avg_queue,
                    "threshold": THRESHOLDS["avg_queue"],
                    "created_at": created_at,
                }
            )

        avg_wait = float(metrics.get("avg_wait", 0.0))
        if avg_wait > THRESHOLDS["avg_wait"]:
            alerts.append(
                {
                    "alert_id": str(uuid.uuid4()),
                    "district_id": district_id,
                    "title": f"{district['name']} wait-time pressure",
                    "message": f"Average wait time is above {THRESHOLDS['avg_wait']} seconds.",
                    "severity": _severity(avg_wait, THRESHOLDS["avg_wait"], True),
                    "metric": "avg_wait",
                    "value": avg_wait,
                    "threshold": THRESHOLDS["avg_wait"],
                    "created_at": created_at,
                }
            )

        emergency_wait = float(metrics.get("emergency_avg_wait", 0.0))
        if emergency_wait > THRESHOLDS["emergency_avg_wait"]:
            alerts.append(
                {
                    "alert_id": str(uuid.uuid4()),
                    "district_id": district_id,
                    "title": f"{district['name']} emergency delay",
                    "message": "Emergency vehicles are waiting longer than target.",
                    "severity": _severity(emergency_wait, THRESHOLDS["emergency_avg_wait"], True),
                    "metric": "emergency_avg_wait",
                    "value": emergency_wait,
                    "threshold": THRESHOLDS["emergency_avg_wait"],
                    "created_at": created_at,
                }
            )

        clearance = float(metrics.get("clearance_ratio", 0.0))
        if clearance < THRESHOLDS["clearance_ratio"]:
            alerts.append(
                {
                    "alert_id": str(uuid.uuid4()),
                    "district_id": district_id,
                    "title": f"{district['name']} clearance risk",
                    "message": "Clearance ratio dropped below target.",
                    "severity": _severity(clearance, THRESHOLDS["clearance_ratio"], False),
                    "metric": "clearance_ratio",
                    "value": clearance,
                    "threshold": THRESHOLDS["clearance_ratio"],
                    "created_at": created_at,
                }
            )

    return alerts
