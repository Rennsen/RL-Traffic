from __future__ import annotations

import os
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
from fastapi.responses import HTMLResponse, StreamingResponse, FileResponse
import asyncio
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from .alerts import build_alerts
from .anomalies import build_anomalies
from .notifications import build_notifications
from .templates_catalog import list_scenario_templates
from .auth import (
    callback,
    get_current_user,
    get_current_user_optional,
    login,
    login_local,
    logout,
    register_local,
    require_roles,
)
from .db import init_db
from .models import (
    AIRecommendRequest,
    AIChatMessageCreate,
    LocalAuthRequest,
    DistrictNoteCreate,
    DistrictSettingsUpdate,
    DistrictTargetsUpdate,
    PresetCreate,
    SimulationRequest,
)
from .service import list_district_catalog, run_experiment
from .store import (
    add_activity,
    add_audit,
    add_note,
    create_preset,
    delete_preset,
    ensure_roles,
    ensure_admin_user,
    get_district_setting,
    get_run,
    get_targets,
    leaderboard,
    latest_run_summary,
    latest_run_full,
    list_activity,
    list_audit,
    list_ai_history,
    list_notes,
    list_presets,
    list_runs,
    record_ai_message,
    seed_presets,
    team_performance,
    update_run_status,
    upsert_district_setting,
    upsert_targets,
)
from .sumo import get_sumo_status

BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parent
ARTIFACTS_DIR = PROJECT_ROOT / "artifacts"
ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)

app = FastAPI(
    title="FlowMind",
    description="Adaptive traffic signal optimization with reinforcement learning.",
    version="1.0.0",
)

session_secret = os.getenv("SESSION_SECRET", "dev_session_secret_change_me")
app.add_middleware(SessionMiddleware, secret_key=session_secret, same_site="lax")

frontend_origin = os.getenv(
    "FRONTEND_ORIGIN",
    "http://localhost:3000,http://127.0.0.1:3000,http://localhost:3001,http://127.0.0.1:3001",
)
frontend_origins = [origin.strip() for origin in frontend_origin.split(",") if origin.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=frontend_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")
app.mount("/artifacts", StaticFiles(directory=str(ARTIFACTS_DIR)), name="artifacts")

@app.on_event("startup")
def _startup() -> None:
    init_db()
    ensure_roles()
    ensure_admin_user()
    seed_presets()


@app.get("/", response_class=HTMLResponse)
async def index(request: Request) -> HTMLResponse:
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/api/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/districts")
async def districts() -> dict[str, list[dict]]:
    districts_list = list_district_catalog()
    for district in districts_list:
        setting = get_district_setting(district["district_id"])
        if setting:
            if setting.get("default_params"):
                district["default_params"].update(setting["default_params"])
            if setting.get("benchmark_overrides"):
                district["actual_metrics"].update(setting["benchmark_overrides"])
    return {"districts": districts_list}


@app.get("/api/sumo/status")
async def sumo_status() -> dict:
    return get_sumo_status()


@app.post("/api/run")
async def run(payload: SimulationRequest, user=Depends(get_current_user_optional)) -> dict:
    created_by = user["id"] if user else None
    result = run_experiment(payload, created_by=created_by)
    add_activity("run_created", f"Simulation run created for {payload.district_id}.", created_by, payload.district_id)
    return result


@app.get("/api/runs")
async def runs(district_id: str | None = None, limit: int = 20, status: str | None = None) -> dict:
    return {"runs": list_runs(district_id=district_id, limit=limit, status=status)}


@app.get("/api/runs/latest")
async def runs_latest(district_id: str | None = None) -> dict:
    return {"runs": latest_run_summary(district_id=district_id)}


@app.get("/api/runs/{run_id}")
async def run_detail(run_id: str) -> dict:
    result = get_run(run_id)
    if not result:
        raise HTTPException(status_code=404, detail="Run not found")
    return result


@app.get("/api/runs/{run_id}/sumo/gui.mjpg")
async def sumo_gui_stream(run_id: str):
    run = get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")

    gui = (run.get("backend") or {}).get("gui") or {}
    snapshot_dir = gui.get("snapshot_dir")
    if not snapshot_dir:
        raise HTTPException(status_code=404, detail="SUMO GUI snapshots not available")

    snapshot_path = Path(snapshot_dir)
    if not snapshot_path.exists():
        raise HTTPException(status_code=404, detail="SUMO GUI snapshot directory not found")

    boundary = "frame"

    async def frame_generator():
        while True:
            files = sorted(snapshot_path.glob("frame_*.png"))
            if not files:
                await asyncio.sleep(0.25)
                continue
            for path in files:
                try:
                    data = path.read_bytes()
                except Exception:
                    continue
                header = (
                    f"--{boundary}\r\n"
                    f"Content-Type: image/png\r\n"
                    f"Content-Length: {len(data)}\r\n\r\n"
                ).encode("utf-8")
                yield header + data + b"\r\n"
                await asyncio.sleep(0.05)
            await asyncio.sleep(0.05)

    return StreamingResponse(frame_generator(), media_type=f"multipart/x-mixed-replace; boundary={boundary}")


@app.get("/api/runs/{run_id}/sumo/gui/frame/{frame_index}")
async def sumo_gui_frame(run_id: str, frame_index: int):
    run = get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")

    gui = (run.get("backend") or {}).get("gui") or {}
    snapshot_dir = gui.get("snapshot_dir")
    if not snapshot_dir:
        raise HTTPException(status_code=404, detail="SUMO GUI snapshots not available")

    snapshot_path = Path(snapshot_dir)
    if not snapshot_path.exists():
        raise HTTPException(status_code=404, detail="SUMO GUI snapshot directory not found")

    files = sorted(snapshot_path.glob("frame_*.png"))
    if not files:
        raise HTTPException(status_code=404, detail="SUMO GUI frames not found")

    safe_index = max(0, min(int(frame_index), len(files) - 1))
    file_path = files[safe_index]

    return FileResponse(
        file_path,
        media_type="image/png",
        headers={"Cache-Control": "no-store, max-age=0"},
    )


@app.get("/api/presets")
async def presets() -> dict:
    return {"presets": list_presets()}


@app.post("/api/presets")
async def create_presets(payload: PresetCreate, user=Depends(require_roles(["Analyst", "Manager", "Admin"]))) -> dict:
    created = create_preset(payload, created_by=user["id"])
    add_audit("preset_created", user["id"], {"preset_id": created["preset_id"]})
    add_activity("preset_created", f"Preset {created['name']} created.", user["id"])
    return created


@app.delete("/api/presets/{preset_id}")
async def remove_preset(preset_id: str, user=Depends(require_roles(["Manager", "Admin"]))) -> dict:
    removed = delete_preset(preset_id)
    if removed:
        add_audit("preset_deleted", user["id"], {"preset_id": preset_id})
    return {"deleted": removed}


@app.get("/api/alerts")
async def alerts() -> dict:
    return {"alerts": build_alerts()}


@app.get("/api/notifications")
async def notifications() -> dict:
    return {"notifications": build_notifications()}


@app.get("/api/templates")
async def templates() -> dict:
    return {"templates": list_scenario_templates()}


@app.patch("/api/districts/{district_id}/settings")
async def update_settings(
    district_id: str,
    payload: DistrictSettingsUpdate,
    user=Depends(require_roles(["Manager", "Admin"])),
) -> dict:
    result = upsert_district_setting(
        district_id=district_id,
        default_params=payload.default_params,
        benchmark_overrides=payload.benchmark_overrides,
        updated_by=user["id"],
    )
    add_audit("district_settings_updated", user["id"], {"district_id": district_id})
    add_activity("district_settings_updated", f"Settings updated for {district_id}.", user["id"], district_id)
    return result


@app.get("/api/districts/{district_id}/notes")
async def notes(district_id: str, user=Depends(get_current_user)) -> dict:
    return {"notes": list_notes(district_id)}


@app.post("/api/districts/{district_id}/notes")
async def add_notes(district_id: str, payload: DistrictNoteCreate, user=Depends(get_current_user)) -> dict:
    result = add_note(district_id, payload.note, user["id"])
    add_activity("district_note_added", f"Note added for {district_id}.", user["id"], district_id)
    return result


@app.get("/api/districts/{district_id}/targets")
async def targets(district_id: str, user=Depends(get_current_user)) -> dict:
    return {"targets": get_targets(district_id)}


@app.put("/api/districts/{district_id}/targets")
async def update_targets(
    district_id: str,
    payload: DistrictTargetsUpdate,
    user=Depends(require_roles(["Manager", "Admin"])),
) -> dict:
    result = upsert_targets(district_id, payload.targets, user["id"])
    add_audit("district_targets_updated", user["id"], {"district_id": district_id})
    add_activity("district_targets_updated", f"Targets updated for {district_id}.", user["id"], district_id)
    return result


@app.post("/api/runs/{run_id}/approve")
async def approve_run(run_id: str, user=Depends(require_roles(["Manager", "Admin"]))) -> dict:
    result = update_run_status(run_id, "approved", approved_by=user["id"])
    if not result:
        raise HTTPException(status_code=404, detail="Run not found")
    add_audit("run_approved", user["id"], {"run_id": run_id})
    add_activity("run_approved", f"Run {run_id} approved.", user["id"])
    return result


@app.post("/api/runs/{run_id}/reject")
async def reject_run(run_id: str, user=Depends(require_roles(["Manager", "Admin"]))) -> dict:
    result = update_run_status(run_id, "rejected", approved_by=user["id"])
    if not result:
        raise HTTPException(status_code=404, detail="Run not found")
    add_audit("run_rejected", user["id"], {"run_id": run_id})
    add_activity("run_rejected", f"Run {run_id} rejected.", user["id"])
    return result


@app.get("/api/audit")
async def audit(limit: int = 50, user=Depends(require_roles(["Admin"]))) -> dict:
    return {"entries": list_audit(limit=limit)}


@app.get("/api/activity")
async def activity(limit: int = 50, user=Depends(get_current_user)) -> dict:
    return {"events": list_activity(limit=limit)}


@app.get("/api/leaderboard")
async def leaderboard_api() -> dict:
    return {"leaderboard": leaderboard()}


@app.get("/api/teams/performance")
async def teams_performance() -> dict:
    return {"teams": team_performance()}


@app.get("/api/reports/weekly")
async def report_weekly() -> dict:
    from .store import report_snapshot

    return report_snapshot(days=7)


@app.get("/api/reports/monthly")
async def report_monthly() -> dict:
    from .store import report_snapshot

    return report_snapshot(days=30)


@app.get("/api/anomalies")
async def anomalies() -> dict:
    return {"anomalies": build_anomalies()}


@app.post("/api/ai/recommend")
async def ai_recommend(payload: AIRecommendRequest) -> dict:
    run = latest_run_full(payload.district_id)
    targets = get_targets(payload.district_id) or {}
    metrics = run.get("comparison", {}).get("rl", {}) if run else {}
    recommendations = []

    avg_wait = metrics.get("avg_wait")
    avg_queue = metrics.get("avg_queue")
    emergency_wait = metrics.get("emergency_avg_wait")
    clearance = metrics.get("clearance_ratio")

    if avg_wait and avg_wait > (targets.get("targets", {}).get("avg_wait", 50) or 50):
        recommendations.append("Lower fixed_cycle by 2-4 steps to reduce wait time.")
    if avg_queue and avg_queue > (targets.get("targets", {}).get("avg_queue", 200) or 200):
        recommendations.append("Increase service_rate by 1 to relieve queue pressure.")
    if emergency_wait and emergency_wait > 12:
        recommendations.append("Boost emergency priority or switch_penalty to favor quicker phase changes.")
    if clearance and clearance < 0.65:
        recommendations.append("Extend green duration on dominant directions to improve clearance ratio.")

    if not recommendations:
        recommendations = [
            "Current performance is within targets. Consider testing a higher discount_factor for stability.",
        ]

    return {"district_id": payload.district_id, "recommendations": recommendations}


@app.get("/api/districts/{district_id}/ai/history")
async def ai_history(district_id: str, user=Depends(get_current_user)) -> dict:
    return {"history": list_ai_history(district_id)}


@app.post("/api/districts/{district_id}/ai/history")
async def ai_history_create(
    district_id: str,
    payload: AIChatMessageCreate,
    user=Depends(get_current_user_optional),
) -> dict:
    if payload.district_id != district_id:
        raise HTTPException(status_code=400, detail="District mismatch")
    return record_ai_message(district_id, payload.role, payload.content, user["id"] if user else None)


@app.get("/api/auth/login")
async def auth_login(request: Request):
    return await login(request)


@app.get("/api/auth/callback", name="auth_callback")
async def auth_callback(request: Request):
    return await callback(request)


@app.post("/api/auth/logout")
async def auth_logout():
    return logout()


@app.get("/api/auth/logout")
async def auth_logout_get():
    return logout()


@app.get("/api/auth/me")
async def auth_me(user=Depends(get_current_user)) -> dict:
    return user


@app.post("/api/auth/register")
async def auth_register(payload: LocalAuthRequest):
    if not payload.name:
        payload.name = payload.email.split("@")[0]
    return register_local(payload.email, payload.name, payload.password)


@app.post("/api/auth/login_local")
async def auth_login_local(payload: LocalAuthRequest):
    return login_local(payload.email, payload.password)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
