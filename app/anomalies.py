from __future__ import annotations

import math
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List

from .config import DISTRICT_PROFILES
from .store import latest_runs_by_district


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _severity(value: float, threshold: float, higher_is_bad: bool = True) -> str:
    if threshold <= 0:
        return "low"
    delta = (value - threshold) / threshold if higher_is_bad else (threshold - value) / threshold
    if delta > 0.35:
        return "high"
    if delta > 0.15:
        return "medium"
    return "low"


def _series_stats(series: List[float]) -> Dict[str, float]:
    if not series:
        return {"mean": 0.0, "std": 0.0, "max": 0.0, "last": 0.0}
    mean = sum(series) / len(series)
    variance = sum((value - mean) ** 2 for value in series) / len(series)
    return {"mean": mean, "std": math.sqrt(variance), "max": max(series), "last": series[-1]}


def build_anomalies() -> List[Dict[str, Any]]:
    anomalies: List[Dict[str, Any]] = []
    latest = latest_runs_by_district()

    for district_id, profile in DISTRICT_PROFILES.items():
        run = latest.get(district_id)
        if not run:
            continue

        metrics = run.get("comparison", {}).get("rl", {})
        series = run.get("time_series", {}).get("rl", {})
        created_at = run.get("created_at", _now_iso())

        queue_series = [float(v) for v in series.get("queue", [])]
        emergency_series = [float(v) for v in series.get("emergency_queue", [])]
        throughput_series = [float(v) for v in series.get("throughput", [])]

        queue_stats = _series_stats(queue_series)
        emergency_stats = _series_stats(emergency_series)
        throughput_stats = _series_stats(throughput_series)

        avg_queue = float(metrics.get("avg_queue", 0.0))
        avg_wait = float(metrics.get("avg_wait", 0.0))
        emergency_wait = float(metrics.get("emergency_avg_wait", 0.0))
        clearance = float(metrics.get("clearance_ratio", 0.0))

        if queue_stats["max"] > max(180.0, avg_queue * 1.6):
            anomalies.append(
                {
                    "anomaly_id": str(uuid.uuid4()),
                    "district_id": district_id,
                    "title": f"{profile['name']} queue spike",
                    "message": "Queue surged above its recent baseline.",
                    "severity": _severity(queue_stats["max"], max(1.0, avg_queue * 1.4), True),
                    "metric": "queue_max",
                    "value": round(queue_stats["max"], 2),
                    "threshold": round(max(1.0, avg_queue * 1.4), 2),
                    "created_at": created_at,
                }
            )

        if queue_stats["last"] > queue_stats["mean"] + 2 * queue_stats["std"] and queue_stats["last"] > 120:
            anomalies.append(
                {
                    "anomaly_id": str(uuid.uuid4()),
                    "district_id": district_id,
                    "title": f"{profile['name']} sudden congestion",
                    "message": "Latest queue value exceeded the rolling mean by >2σ.",
                    "severity": _severity(queue_stats["last"], queue_stats["mean"] + queue_stats["std"], True),
                    "metric": "queue_last",
                    "value": round(queue_stats["last"], 2),
                    "threshold": round(queue_stats["mean"] + queue_stats["std"], 2),
                    "created_at": created_at,
                }
            )

        if emergency_wait > 12.0:
            anomalies.append(
                {
                    "anomaly_id": str(uuid.uuid4()),
                    "district_id": district_id,
                    "title": f"{profile['name']} emergency delay",
                    "message": "Emergency wait time exceeded target.",
                    "severity": _severity(emergency_wait, 12.0, True),
                    "metric": "emergency_avg_wait",
                    "value": round(emergency_wait, 2),
                    "threshold": 12.0,
                    "created_at": created_at,
                }
            )

        if clearance < 0.65:
            anomalies.append(
                {
                    "anomaly_id": str(uuid.uuid4()),
                    "district_id": district_id,
                    "title": f"{profile['name']} clearance drop",
                    "message": "Clearance ratio is below target for the current run.",
                    "severity": _severity(clearance, 0.65, False),
                    "metric": "clearance_ratio",
                    "value": round(clearance, 3),
                    "threshold": 0.65,
                    "created_at": created_at,
                }
            )

        if throughput_stats["mean"] < 1.5:
            anomalies.append(
                {
                    "anomaly_id": str(uuid.uuid4()),
                    "district_id": district_id,
                    "title": f"{profile['name']} throughput slowdown",
                    "message": "Average throughput per step is below expected levels.",
                    "severity": _severity(throughput_stats["mean"], 1.5, False),
                    "metric": "throughput_per_step",
                    "value": round(throughput_stats["mean"], 2),
                    "threshold": 1.5,
                    "created_at": created_at,
                }
            )

    return anomalies
