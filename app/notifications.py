from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List

from .alerts import build_alerts
from .anomalies import build_anomalies
from .store import list_activity


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def build_notifications() -> List[Dict[str, Any]]:
    notifications: List[Dict[str, Any]] = []

    for alert in build_alerts():
        notifications.append(
            {
                "notification_id": str(uuid.uuid4()),
                "title": alert["title"],
                "message": alert["message"],
                "severity": alert["severity"],
                "category": "alert",
                "district_id": alert["district_id"],
                "created_at": alert.get("created_at", _now_iso()),
            }
        )

    for anomaly in build_anomalies():
        notifications.append(
            {
                "notification_id": str(uuid.uuid4()),
                "title": anomaly["title"],
                "message": anomaly["message"],
                "severity": anomaly["severity"],
                "category": "anomaly",
                "district_id": anomaly["district_id"],
                "created_at": anomaly.get("created_at", _now_iso()),
            }
        )

    for activity in list_activity(limit=15):
        notifications.append(
            {
                "notification_id": str(uuid.uuid4()),
                "title": "Activity Update",
                "message": activity["message"],
                "severity": "low",
                "category": "activity",
                "district_id": activity.get("district_id"),
                "created_at": activity.get("created_at", _now_iso()),
            }
        )

    notifications.sort(key=lambda item: item["created_at"], reverse=True)
    return notifications[:50]
