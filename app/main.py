from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from .models import SimulationRequest
from .service import list_district_catalog, run_experiment

BASE_DIR = Path(__file__).resolve().parent

app = FastAPI(
    title="FlowMind",
    description="Adaptive traffic signal optimization with reinforcement learning.",
    version="1.0.0",
)

templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")


@app.get("/", response_class=HTMLResponse)
async def index(request: Request) -> HTMLResponse:
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/api/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/districts")
async def districts() -> dict[str, list[dict]]:
    return {"districts": list_district_catalog()}


@app.post("/api/run")
async def run(payload: SimulationRequest) -> dict:
    return run_experiment(payload)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
