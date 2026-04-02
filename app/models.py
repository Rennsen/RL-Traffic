from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


TrafficPattern = Literal[
    "balanced",
    "rush_hour_ns",
    "rush_hour_ew",
    "event_spike",
    "random",
]

AgentAlgorithm = Literal[
    "q_learning",
    "dqn",
    "ppo",
]

SimulationBackend = Literal[
    "internal",
    "sumo",
]

DistrictId = Literal[
    "downtown_core",
    "university_ring",
    "industrial_port",
]


class SimulationRequest(BaseModel):
    district_id: DistrictId = "downtown_core"
    algorithm: AgentAlgorithm = "q_learning"
    backend: SimulationBackend = "internal"

    episodes: int = Field(default=260, ge=50, le=1500)
    steps_per_episode: int = Field(default=240, ge=60, le=900)
    traffic_pattern: TrafficPattern = "rush_hour_ns"

    fixed_cycle: int = Field(default=18, ge=4, le=120)
    service_rate: int = Field(default=3, ge=1, le=8)
    emergency_rate: float = Field(default=0.02, ge=0.0, le=0.3)

    learning_rate: float = Field(default=0.12, ge=0.01, le=1.0)
    discount_factor: float = Field(default=0.95, ge=0.5, le=0.999)
    epsilon_start: float = Field(default=1.0, ge=0.01, le=1.0)
    epsilon_min: float = Field(default=0.05, ge=0.0, le=0.5)
    epsilon_decay: float = Field(default=0.992, ge=0.9, le=0.9999)

    switch_penalty: float = Field(default=1.1, ge=0.0, le=5.0)
    seed: int = Field(default=42, ge=0, le=10_000_000)

    actual_avg_wait: float | None = Field(default=None, ge=0.0, le=5000.0)
    actual_avg_queue: float | None = Field(default=None, ge=0.0, le=5000.0)
    actual_throughput: float | None = Field(default=None, ge=0.0, le=100_000.0)
    actual_emergency_avg_wait: float | None = Field(default=None, ge=0.0, le=5000.0)
    actual_clearance_ratio: float | None = Field(default=None, ge=0.0, le=1.5)


class PresetCreate(BaseModel):
    name: str = Field(min_length=2, max_length=80)
    description: str | None = Field(default=None, max_length=240)
    config: SimulationRequest


class Preset(BaseModel):
    preset_id: str
    name: str
    description: str | None = None
    config: SimulationRequest
    created_at: str


class RunSummary(BaseModel):
    run_id: str
    district_id: DistrictId
    district_name: str
    created_at: str
    avg_wait: float
    avg_queue: float
    throughput: float
    clearance_ratio: float
    improvements: dict
    status: str | None = None


class Alert(BaseModel):
    alert_id: str
    district_id: DistrictId
    title: str
    message: str
    severity: Literal["low", "medium", "high"]
    metric: str
    value: float
    threshold: float
    created_at: str


class DistrictSettingsUpdate(BaseModel):
    default_params: dict | None = None
    benchmark_overrides: dict | None = None


class DistrictNoteCreate(BaseModel):
    note: str = Field(min_length=2, max_length=1000)


class DistrictTargetsUpdate(BaseModel):
    targets: dict


class AIRecommendRequest(BaseModel):
    district_id: DistrictId
    summary: dict | None = None


class AIChatMessageCreate(BaseModel):
    district_id: DistrictId
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=4000)


class LocalAuthRequest(BaseModel):
    email: str = Field(min_length=3, max_length=255)
    password: str = Field(min_length=6, max_length=128)
    name: str | None = Field(default=None, max_length=120)
