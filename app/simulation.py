from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Dict, List, Tuple

import numpy as np

from .config import DIRECTIONS, PHASE_TO_DIRECTIONS


@dataclass(frozen=True)
class StepDemand:
    arrivals: Dict[str, int]
    emergency: Dict[str, int]


def _pattern_rates(
    pattern: str,
    progress: float,
    rng: np.random.Generator,
) -> Dict[str, float]:
    rates = {direction: 1.0 for direction in DIRECTIONS}

    if pattern == "balanced":
        wave = 0.25 * math.sin(progress * 2.0 * math.pi)
        for direction in DIRECTIONS:
            rates[direction] = 1.0 + wave

    elif pattern == "rush_hour_ns":
        rush = 0.7 + 1.0 * (math.sin(progress * math.pi) ** 2)
        rates["N"] = 1.0 + 1.25 * rush
        rates["S"] = 1.0 + 1.15 * rush
        rates["E"] = 0.7 + 0.3 * (math.cos(progress * 2.0 * math.pi) ** 2)
        rates["W"] = 0.7 + 0.25 * (math.sin(progress * 2.0 * math.pi) ** 2)

    elif pattern == "rush_hour_ew":
        rush = 0.7 + 1.0 * (math.sin(progress * math.pi) ** 2)
        rates["E"] = 1.0 + 1.25 * rush
        rates["W"] = 1.0 + 1.15 * rush
        rates["N"] = 0.7 + 0.3 * (math.cos(progress * 2.0 * math.pi) ** 2)
        rates["S"] = 0.7 + 0.25 * (math.sin(progress * 2.0 * math.pi) ** 2)

    elif pattern == "event_spike":
        for direction in DIRECTIONS:
            rates[direction] = 0.9 + 0.2 * math.sin(progress * 6.0)

        if 0.4 <= progress <= 0.6:
            rates["E"] += 2.4
            rates["W"] += 2.1

    elif pattern == "random":
        for direction in DIRECTIONS:
            rates[direction] = float(rng.uniform(0.45, 2.4))

    return {direction: max(0.05, value) for direction, value in rates.items()}


def generate_traffic_scenario(
    steps: int,
    pattern: str,
    seed: int,
    emergency_rate: float,
) -> List[StepDemand]:
    rng = np.random.default_rng(seed)
    scenario: List[StepDemand] = []

    for step in range(steps):
        progress = step / max(1, steps - 1)
        rates = _pattern_rates(pattern=pattern, progress=progress, rng=rng)

        arrivals: Dict[str, int] = {}
        emergency: Dict[str, int] = {}

        for direction in DIRECTIONS:
            arrivals[direction] = int(rng.poisson(rates[direction]))

            pressure_boost = 1.6 if rates[direction] > 1.7 else 1.0
            p_emergency = min(0.4, emergency_rate * pressure_boost)
            emergency[direction] = int(rng.random() < p_emergency)

        scenario.append(StepDemand(arrivals=arrivals, emergency=emergency))

    return scenario


class TrafficEnvironment:
    def __init__(
        self,
        scenario: List[StepDemand],
        service_rate: int,
        switch_penalty: float,
    ) -> None:
        self.scenario = scenario
        self.steps = len(scenario)
        self.service_rate = service_rate
        self.switch_penalty = switch_penalty

        self.current_step = 0
        self.current_phase = 0

        self.queues: Dict[str, int] = {direction: 0 for direction in DIRECTIONS}
        self.emergency_queues: Dict[str, int] = {direction: 0 for direction in DIRECTIONS}

        self.total_wait_accum = 0.0
        self.emergency_wait_accum = 0.0
        self.total_queue_accum = 0.0
        self.total_arrivals = 0
        self.throughput = 0
        self.normal_served = 0
        self.emergency_served = 0

        self.series = {
            "queue": [],
            "throughput": [],
            "phase": [],
            "avg_wait": [],
            "emergency_queue": [],
            "directional_queue": {direction: [] for direction in DIRECTIONS},
            "directional_emergency": {direction: [] for direction in DIRECTIONS},
            "arrivals_by_direction": {direction: [] for direction in DIRECTIONS},
            "served_by_direction": {direction: [] for direction in DIRECTIONS},
        }

    def reset(self) -> Tuple[int, int, int, int, int]:
        self.current_step = 0
        self.current_phase = 0

        self.queues = {direction: 0 for direction in DIRECTIONS}
        self.emergency_queues = {direction: 0 for direction in DIRECTIONS}

        self.total_wait_accum = 0.0
        self.emergency_wait_accum = 0.0
        self.total_queue_accum = 0.0
        self.total_arrivals = 0
        self.throughput = 0
        self.normal_served = 0
        self.emergency_served = 0

        self.series = {
            "queue": [],
            "throughput": [],
            "phase": [],
            "avg_wait": [],
            "emergency_queue": [],
            "directional_queue": {direction: [] for direction in DIRECTIONS},
            "directional_emergency": {direction: [] for direction in DIRECTIONS},
            "arrivals_by_direction": {direction: [] for direction in DIRECTIONS},
            "served_by_direction": {direction: [] for direction in DIRECTIONS},
        }

        return self._state()

    def _state(self) -> Tuple[int, int, int, int, int]:
        ns_load = (
            self.queues["N"]
            + self.queues["S"]
            + 2 * (self.emergency_queues["N"] + self.emergency_queues["S"])
        )
        ew_load = (
            self.queues["E"]
            + self.queues["W"]
            + 2 * (self.emergency_queues["E"] + self.emergency_queues["W"])
        )

        total_load = ns_load + ew_load
        if total_load < 6:
            queue_bucket = 0
        elif total_load < 12:
            queue_bucket = 1
        elif total_load < 20:
            queue_bucket = 2
        elif total_load < 30:
            queue_bucket = 3
        else:
            queue_bucket = 4

        imbalance = ns_load - ew_load
        if imbalance < -8:
            imbalance_bucket = 0
        elif imbalance < -3:
            imbalance_bucket = 1
        elif imbalance <= 3:
            imbalance_bucket = 2
        elif imbalance <= 8:
            imbalance_bucket = 3
        else:
            imbalance_bucket = 4

        ns_emergency = self.emergency_queues["N"] + self.emergency_queues["S"]
        ew_emergency = self.emergency_queues["E"] + self.emergency_queues["W"]
        if ns_emergency == 0 and ew_emergency == 0:
            emergency_bucket = 0
        elif ns_emergency > ew_emergency:
            emergency_bucket = 1
        elif ew_emergency > ns_emergency:
            emergency_bucket = 2
        else:
            emergency_bucket = 3

        time_bucket = min(3, int((self.current_step / max(1, self.steps)) * 4))
        return (queue_bucket, imbalance_bucket, self.current_phase, emergency_bucket, time_bucket)

    def _serve_green_phase(self) -> Tuple[int, int, Dict[str, int]]:
        served = 0
        emergency_served = 0
        served_by_direction = {direction: 0 for direction in DIRECTIONS}

        for direction in PHASE_TO_DIRECTIONS[self.current_phase]:
            capacity = self.service_rate

            use_for_emergency = min(capacity, self.emergency_queues[direction])
            self.emergency_queues[direction] -= use_for_emergency
            capacity -= use_for_emergency

            use_for_regular = min(capacity, self.queues[direction])
            self.queues[direction] -= use_for_regular

            served += use_for_emergency + use_for_regular
            emergency_served += use_for_emergency
            served_by_direction[direction] = use_for_emergency + use_for_regular

        return served, emergency_served, served_by_direction

    def step(self, action: int) -> Tuple[Tuple[int, int, int, int, int], float, bool, Dict[str, float]]:
        if self.current_step >= self.steps:
            return self._state(), 0.0, True, {}

        switched = 1 if action == 1 else 0
        if switched:
            self.current_phase = 1 - self.current_phase

        demand = self.scenario[self.current_step]
        for direction in DIRECTIONS:
            self.queues[direction] += demand.arrivals[direction]
            self.emergency_queues[direction] += demand.emergency[direction]

        served_step, emergency_served_step, served_by_direction = self._serve_green_phase()

        queue_total = sum(self.queues.values()) + sum(self.emergency_queues.values())
        emergency_total = sum(self.emergency_queues.values())
        red_directions = PHASE_TO_DIRECTIONS[1 - self.current_phase]
        emergency_on_red = sum(self.emergency_queues[direction] for direction in red_directions)
        ns_pressure = (
            self.queues["N"]
            + self.queues["S"]
            + 2 * (self.emergency_queues["N"] + self.emergency_queues["S"])
        )
        ew_pressure = (
            self.queues["E"]
            + self.queues["W"]
            + 2 * (self.emergency_queues["E"] + self.emergency_queues["W"])
        )

        self.total_wait_accum += float(queue_total)
        self.emergency_wait_accum += float(emergency_total)
        self.total_queue_accum += float(queue_total)
        self.total_arrivals += sum(demand.arrivals.values()) + sum(demand.emergency.values())
        self.throughput += served_step
        self.normal_served += served_step - emergency_served_step
        self.emergency_served += emergency_served_step

        reward = -(
            0.70 * queue_total
            + 2.70 * emergency_total
            + 4.00 * emergency_on_red
            + 0.20 * abs(ns_pressure - ew_pressure)
            + switched * self.switch_penalty
        )

        self.series["queue"].append(queue_total)
        self.series["throughput"].append(served_step)
        self.series["phase"].append(self.current_phase)
        self.series["avg_wait"].append(round(self.total_wait_accum / max(1, self.throughput), 3))
        self.series["emergency_queue"].append(emergency_total)
        for direction in DIRECTIONS:
            self.series["directional_queue"][direction].append(self.queues[direction])
            self.series["directional_emergency"][direction].append(self.emergency_queues[direction])
            self.series["arrivals_by_direction"][direction].append(demand.arrivals[direction] + demand.emergency[direction])
            self.series["served_by_direction"][direction].append(served_by_direction[direction])

        self.current_step += 1
        done = self.current_step >= self.steps

        info = {
            "queue": float(queue_total),
            "served": float(served_step),
            "emergency_queue": float(emergency_total),
        }
        return self._state(), reward, done, info

    def summary(self) -> Dict[str, float]:
        avg_wait = self.total_wait_accum / max(1, self.throughput)
        avg_queue = self.total_queue_accum / max(1, self.steps)
        emergency_avg_wait = self.emergency_wait_accum / max(1, self.emergency_served)
        remaining = sum(self.queues.values()) + sum(self.emergency_queues.values())

        return {
            "avg_wait": round(avg_wait, 3),
            "avg_queue": round(avg_queue, 3),
            "throughput": float(self.throughput),
            "throughput_per_step": round(self.throughput / max(1, self.steps), 3),
            "emergency_avg_wait": round(emergency_avg_wait, 3),
            "max_queue": float(max(self.series["queue"], default=0)),
            "clearance_ratio": round(self.throughput / max(1, self.total_arrivals), 3),
            "remaining_vehicles": float(remaining),
        }
