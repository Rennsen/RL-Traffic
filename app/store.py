from __future__ import annotations

from datetime import datetime, timedelta, timezone
import uuid
from typing import Any, Dict, List, Optional
import os

from sqlalchemy import desc

from .config import DISTRICT_PROFILES
from .db import SessionLocal
from .db_models import (
    ActivityEvent,
    AuditLog,
    DistrictNote,
    DistrictSetting,
    DistrictTarget,
    Preset,
    Role,
    Run,
    User,
    UserRole,
)
from .models import PresetCreate, RunSummary
from .security import hash_password

MAX_RUNS_PER_DISTRICT = 50


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _build_summary(run: Dict[str, Any], status: str | None = None) -> Dict[str, Any]:
    comparison = run.get("comparison", {})
    rl_metrics = comparison.get("rl", {})
    improvements = comparison.get("improvements", {})
    district = run.get("district", {})

    summary = RunSummary(
        run_id=run["run_id"],
        district_id=district.get("district_id", ""),
        district_name=district.get("name", ""),
        created_at=run["created_at"],
        avg_wait=float(rl_metrics.get("avg_wait", 0.0)),
        avg_queue=float(rl_metrics.get("avg_queue", 0.0)),
        throughput=float(rl_metrics.get("throughput", 0.0)),
        clearance_ratio=float(rl_metrics.get("clearance_ratio", 0.0)),
        improvements=improvements,
        status=status,
    )
    return summary.model_dump()


def _hydrate_run_result(run: Dict[str, Any]) -> Dict[str, Any]:
    district = run.get("district")
    if district is None or not isinstance(district, dict):
        district = {}
        run["district"] = district

    district_id = district.get("district_id")
    if not district_id:
        district_id = (
            run.get("config", {})
            .get("request", {})
            .get("district_id")
        )
        if district_id:
            district["district_id"] = district_id

    profile = DISTRICT_PROFILES.get(district_id) if district_id else None
    if not profile:
        return run

    for key in ("name", "description", "manager", "traffic_pattern", "default_params", "actual_metrics", "layout"):
        if district.get(key) is None:
            district[key] = profile.get(key)

    if district.get("network") is None and district.get("layout"):
        from .simulation import build_network_metadata

        district["network"] = build_network_metadata(district["layout"])

    return run


def ensure_roles() -> None:
    roles = ["Operator", "Analyst", "Manager", "Admin"]
    with SessionLocal() as db:
        existing = {role.name for role in db.query(Role).all()}
        for role_name in roles:
            if role_name not in existing:
                db.add(Role(name=role_name))
        db.commit()


def ensure_admin_user() -> None:
    email = os.getenv("ADMIN_EMAIL")
    password = os.getenv("ADMIN_PASSWORD")
    name = os.getenv("ADMIN_NAME", "Admin User")
    if not email or not password:
        return

    with SessionLocal() as db:
        user = db.query(User).filter(User.email == email).first()
        if not user:
            user = User(email=email, name=name, password_hash=hash_password(password), auth_provider="local")
            db.add(user)
            db.commit()
            db.refresh(user)
        role = db.query(Role).filter(Role.name == "Admin").first()
        if role:
            exists = db.query(UserRole).filter(UserRole.user_id == user.id, UserRole.role_id == role.id).first()
            if not exists:
                db.add(UserRole(user_id=user.id, role_id=role.id))
                db.commit()


def record_run(run: Dict[str, Any], created_by: str | None = None) -> Dict[str, Any]:
    run_id = run.get("run_id") or str(uuid.uuid4())
    created_at = run.get("created_at") or _now_iso()

    run["run_id"] = run_id
    run["created_at"] = created_at

    summary = _build_summary(run, status="pending")

    with SessionLocal() as db:
        db.add(
            Run(
                id=run_id,
                district_id=summary["district_id"],
                created_by=created_by,
                status="pending",
                summary=summary,
                full_result=run,
            )
        )
        db.commit()

    return run


def list_runs(
    district_id: str | None = None,
    limit: int = 20,
    status: str | None = None,
) -> List[Dict[str, Any]]:
    with SessionLocal() as db:
        query = db.query(Run)
        if district_id:
            query = query.filter(Run.district_id == district_id)
        if status:
            query = query.filter(Run.status == status)
        runs = query.order_by(desc(Run.created_at)).limit(max(1, min(limit, 200))).all()
        return [run.summary for run in runs]


def get_run(run_id: str) -> Dict[str, Any] | None:
    with SessionLocal() as db:
        run = db.query(Run).filter(Run.id == run_id).first()
        if not run:
            return None
        return _hydrate_run_result(run.full_result)


def latest_runs_by_district() -> Dict[str, Dict[str, Any]]:
    latest: Dict[str, Dict[str, Any]] = {}
    with SessionLocal() as db:
        for district_id in DISTRICT_PROFILES.keys():
            run = (
                db.query(Run)
                .filter(Run.district_id == district_id)
                .order_by(desc(Run.created_at))
                .first()
            )
            if run:
                latest[district_id] = run.full_result
    return latest


def latest_run_full(district_id: str) -> Dict[str, Any] | None:
    with SessionLocal() as db:
        run = (
            db.query(Run)
            .filter(Run.district_id == district_id)
            .order_by(desc(Run.created_at))
            .first()
        )
        if not run:
            return None
        return _hydrate_run_result(run.full_result)


def update_run_status(run_id: str, status: str, approved_by: str | None = None) -> Dict[str, Any] | None:
    with SessionLocal() as db:
        run = db.query(Run).filter(Run.id == run_id).first()
        if not run:
            return None
        run.status = status
        if isinstance(run.summary, dict):
            run.summary["status"] = status
        if status in {"approved", "rejected"}:
            run.approved_by = approved_by
            run.approved_at = datetime.now(timezone.utc)
        db.commit()
        return run.summary


def list_presets() -> List[Dict[str, Any]]:
    with SessionLocal() as db:
        presets = db.query(Preset).order_by(desc(Preset.created_at)).all()
        return [
            {
                "preset_id": preset.id,
                "name": preset.name,
                "description": preset.description,
                "config": preset.config,
                "created_at": preset.created_at.isoformat(),
            }
            for preset in presets
        ]


def create_preset(payload: PresetCreate, created_by: str | None = None) -> Dict[str, Any]:
    with SessionLocal() as db:
        preset = Preset(
            name=payload.name,
            description=payload.description,
            config=payload.config.model_dump(),
            created_by=created_by,
        )
        db.add(preset)
        db.commit()
        db.refresh(preset)
        return {
            "preset_id": preset.id,
            "name": preset.name,
            "description": preset.description,
            "config": preset.config,
            "created_at": preset.created_at.isoformat(),
        }


def delete_preset(preset_id: str) -> bool:
    with SessionLocal() as db:
        preset = db.query(Preset).filter(Preset.id == preset_id).first()
        if not preset:
            return False
        db.delete(preset)
        db.commit()
        return True


def seed_presets() -> None:
    with SessionLocal() as db:
        if db.query(Preset).count() > 0:
            return

    defaults = [
        {
            "name": "Morning Rush Core",
            "description": "High NS commuter surge with emergency priority.",
            "config": {
                "district_id": "downtown_core",
                "algorithm": "q_learning",
                "backend": "internal",
                "episodes": 320,
                "steps_per_episode": 260,
                "traffic_pattern": "rush_hour_ns",
                "fixed_cycle": 16,
                "service_rate": 3,
                "emergency_rate": 0.03,
                "learning_rate": 0.12,
                "discount_factor": 0.95,
                "epsilon_start": 1.0,
                "epsilon_min": 0.05,
                "epsilon_decay": 0.992,
                "switch_penalty": 1.1,
                "seed": 42,
                "actual_avg_wait": None,
                "actual_avg_queue": None,
                "actual_throughput": None,
                "actual_emergency_avg_wait": None,
                "actual_clearance_ratio": None,
            },
        },
        {
            "name": "Campus Event Spike",
            "description": "Event-day east/west surges around campus ring.",
            "config": {
                "district_id": "university_ring",
                "algorithm": "q_learning",
                "backend": "internal",
                "episodes": 240,
                "steps_per_episode": 220,
                "traffic_pattern": "event_spike",
                "fixed_cycle": 14,
                "service_rate": 2,
                "emergency_rate": 0.02,
                "learning_rate": 0.11,
                "discount_factor": 0.94,
                "epsilon_start": 1.0,
                "epsilon_min": 0.06,
                "epsilon_decay": 0.993,
                "switch_penalty": 1.0,
                "seed": 128,
                "actual_avg_wait": None,
                "actual_avg_queue": None,
                "actual_throughput": None,
                "actual_emergency_avg_wait": None,
                "actual_clearance_ratio": None,
            },
        },
        {
            "name": "Port Freight Push",
            "description": "EW freight pressure with higher service rate.",
            "config": {
                "district_id": "industrial_port",
                "algorithm": "q_learning",
                "backend": "internal",
                "episodes": 360,
                "steps_per_episode": 280,
                "traffic_pattern": "rush_hour_ew",
                "fixed_cycle": 20,
                "service_rate": 4,
                "emergency_rate": 0.015,
                "learning_rate": 0.1,
                "discount_factor": 0.96,
                "epsilon_start": 1.0,
                "epsilon_min": 0.05,
                "epsilon_decay": 0.991,
                "switch_penalty": 1.3,
                "seed": 256,
                "actual_avg_wait": None,
                "actual_avg_queue": None,
                "actual_throughput": None,
                "actual_emergency_avg_wait": None,
                "actual_clearance_ratio": None,
            },
        },
    ]

    for preset in defaults:
        create_preset(PresetCreate(**preset))


def get_district_setting(district_id: str) -> Optional[Dict[str, Any]]:
    with SessionLocal() as db:
        setting = db.query(DistrictSetting).filter(DistrictSetting.district_id == district_id).first()
        if not setting:
            return None
        return {
            "district_id": setting.district_id,
            "default_params": setting.default_params,
            "benchmark_overrides": setting.benchmark_overrides,
        }


def upsert_district_setting(
    district_id: str,
    default_params: Dict[str, Any] | None,
    benchmark_overrides: Dict[str, Any] | None,
    updated_by: str | None,
) -> Dict[str, Any]:
    with SessionLocal() as db:
        setting = db.query(DistrictSetting).filter(DistrictSetting.district_id == district_id).first()
        if not setting:
            setting = DistrictSetting(
                district_id=district_id,
                default_params=default_params,
                benchmark_overrides=benchmark_overrides,
                updated_by=updated_by,
            )
            db.add(setting)
        else:
            setting.default_params = default_params
            setting.benchmark_overrides = benchmark_overrides
            setting.updated_by = updated_by
        db.commit()
        db.refresh(setting)
        return {
            "district_id": setting.district_id,
            "default_params": setting.default_params,
            "benchmark_overrides": setting.benchmark_overrides,
        }


def add_audit(action: str, actor_id: str | None, details: Dict[str, Any] | None) -> None:
    with SessionLocal() as db:
        db.add(AuditLog(action=action, actor_id=actor_id, details=details))
        db.commit()


def add_activity(event_type: str, message: str, actor_id: str | None, district_id: str | None = None) -> None:
    with SessionLocal() as db:
        db.add(ActivityEvent(event_type=event_type, message=message, actor_id=actor_id, district_id=district_id))
        db.commit()


def list_audit(limit: int = 50) -> List[Dict[str, Any]]:
    with SessionLocal() as db:
        entries = db.query(AuditLog).order_by(desc(AuditLog.created_at)).limit(limit).all()
        return [
            {
                "id": entry.id,
                "action": entry.action,
                "actor_id": entry.actor_id,
                "details": entry.details,
                "created_at": entry.created_at.isoformat(),
            }
            for entry in entries
        ]


def list_activity(limit: int = 50) -> List[Dict[str, Any]]:
    with SessionLocal() as db:
        entries = db.query(ActivityEvent).order_by(desc(ActivityEvent.created_at)).limit(limit).all()
        return [
            {
                "id": entry.id,
                "event_type": entry.event_type,
                "message": entry.message,
                "actor_id": entry.actor_id,
                "district_id": entry.district_id,
                "created_at": entry.created_at.isoformat(),
            }
            for entry in entries
        ]


def list_notes(district_id: str) -> List[Dict[str, Any]]:
    with SessionLocal() as db:
        notes = (
            db.query(DistrictNote)
            .filter(DistrictNote.district_id == district_id)
            .order_by(desc(DistrictNote.created_at))
            .all()
        )
        return [
            {
                "id": note.id,
                "note": note.note,
                "created_at": note.created_at.isoformat(),
                "created_by": note.created_by,
            }
            for note in notes
        ]


def add_note(district_id: str, note: str, created_by: str | None) -> Dict[str, Any]:
    with SessionLocal() as db:
        entry = DistrictNote(district_id=district_id, note=note, created_by=created_by)
        db.add(entry)
        db.commit()
        db.refresh(entry)
        return {
            "id": entry.id,
            "note": entry.note,
            "created_at": entry.created_at.isoformat(),
            "created_by": entry.created_by,
        }


def get_targets(district_id: str) -> Dict[str, Any] | None:
    with SessionLocal() as db:
        target = db.query(DistrictTarget).filter(DistrictTarget.district_id == district_id).first()
        if not target:
            return None
        return {
            "district_id": target.district_id,
            "targets": target.targets,
            "updated_at": target.updated_at.isoformat(),
        }


def upsert_targets(district_id: str, targets: Dict[str, Any], updated_by: str | None) -> Dict[str, Any]:
    with SessionLocal() as db:
        target = db.query(DistrictTarget).filter(DistrictTarget.district_id == district_id).first()
        if not target:
            target = DistrictTarget(district_id=district_id, targets=targets, updated_by=updated_by)
            db.add(target)
        else:
            target.targets = targets
            target.updated_by = updated_by
        db.commit()
        db.refresh(target)
        return {
            "district_id": target.district_id,
            "targets": target.targets,
            "updated_at": target.updated_at.isoformat(),
        }


def latest_run_summary(district_id: str | None = None) -> List[Dict[str, Any]]:
    with SessionLocal() as db:
        query = db.query(Run)
        if district_id:
            query = query.filter(Run.district_id == district_id)
        run = query.order_by(desc(Run.created_at)).first()
        return [run.summary] if run else []


def leaderboard(limit: int = 10) -> List[Dict[str, Any]]:
    runs = list_runs(limit=200)
    leaderboard_rows = []
    seen = set()
    for run in runs:
        if run["district_id"] in seen:
            continue
        seen.add(run["district_id"])
        leaderboard_rows.append(
            {
                "district_id": run["district_id"],
                "district_name": run["district_name"],
                "avg_wait_pct": run["improvements"].get("avg_wait_pct"),
                "throughput_pct": run["improvements"].get("throughput_pct"),
            }
        )
    leaderboard_rows.sort(key=lambda item: item["avg_wait_pct"] or 0.0, reverse=True)
    return leaderboard_rows[:limit]


def team_performance() -> List[Dict[str, Any]]:
    runs = list_runs(limit=200)
    latest_by_district = {run["district_id"]: run for run in runs}
    rows = []
    for district_id, profile in DISTRICT_PROFILES.items():
        run = latest_by_district.get(district_id)
        rows.append(
            {
                "team": profile["manager"]["team"],
                "district": profile["name"],
                "owner": profile["manager"]["owner"],
                "wait_gain": run["improvements"].get("avg_wait_pct") if run else None,
                "throughput_gain": run["improvements"].get("throughput_pct") if run else None,
            }
        )
    return rows


def report_snapshot(days: int = 7) -> Dict[str, Any]:
    with SessionLocal() as db:
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        runs = (
            db.query(Run)
            .filter(Run.created_at >= cutoff)
            .order_by(desc(Run.created_at))
            .all()
        )
    summaries = [run.summary for run in runs]
    if summaries:
        avg_wait = sum(item.get("avg_wait", 0.0) for item in summaries) / len(summaries)
        avg_queue = sum(item.get("avg_queue", 0.0) for item in summaries) / len(summaries)
        throughput = sum(item.get("throughput", 0.0) for item in summaries)
    else:
        avg_wait = 0.0
        avg_queue = 0.0
        throughput = 0.0
    return {
        "period_days": days,
        "count": len(summaries),
        "avg_wait": round(avg_wait, 3),
        "avg_queue": round(avg_queue, 3),
        "throughput": round(throughput, 3),
        "runs": summaries,
    }


def record_ai_message(district_id: str, role: str, content: str, user_id: str | None) -> Dict[str, Any]:
    from .db_models import AIChatMessage

    with SessionLocal() as db:
        message = AIChatMessage(district_id=district_id, role=role, content=content, user_id=user_id)
        db.add(message)
        db.commit()
        db.refresh(message)
        return {
            "id": message.id,
            "district_id": message.district_id,
            "role": message.role,
            "content": message.content,
            "created_at": message.created_at.isoformat(),
        }


def list_ai_history(district_id: str, limit: int = 40) -> List[Dict[str, Any]]:
    from .db_models import AIChatMessage

    with SessionLocal() as db:
        messages = (
            db.query(AIChatMessage)
            .filter(AIChatMessage.district_id == district_id)
            .order_by(desc(AIChatMessage.created_at))
            .limit(limit)
            .all()
        )
        return [
            {
                "id": message.id,
                "district_id": message.district_id,
                "role": message.role,
                "content": message.content,
                "created_at": message.created_at.isoformat(),
            }
            for message in messages
        ]
