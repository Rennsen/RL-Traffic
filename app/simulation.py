from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Dict, List, Tuple

import numpy as np

from .config import DIRECTIONS, PHASE_TO_DIRECTIONS

State = Tuple[int, int, int, int, int]


@dataclass(frozen=True)
class StepDemand:
    arrivals: Dict[str, int]
    emergency: Dict[str, int]


@dataclass(frozen=True)
class IntersectionNode:
    node_id: str
    x: float
    y: float
    row: int
    col: int


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


def build_network_metadata(layout: Dict[str, object]) -> Dict[str, object]:
    intersections = layout.get("intersections", [])
    if not intersections:
        return {
            "intersection_ids": [],
            "intersection_count": 0,
            "corridor_count": 0,
            "boundary_nodes": [],
            "rows": 0,
            "cols": 0,
        }

    xs = sorted({int(node["x"]) for node in intersections})
    ys = sorted({int(node["y"]) for node in intersections})

    boundary_nodes: List[str] = []
    for node in intersections:
        if (
            int(node["x"]) == xs[0]
            or int(node["x"]) == xs[-1]
            or int(node["y"]) == ys[0]
            or int(node["y"]) == ys[-1]
        ):
            boundary_nodes.append(str(node["id"]))

    return {
        "intersection_ids": [str(node["id"]) for node in intersections],
        "intersection_count": len(intersections),
        "corridor_count": max(1, len(xs) + len(ys)),
        "boundary_nodes": boundary_nodes,
        "rows": len(ys),
        "cols": len(xs),
    }


class TrafficEnvironment:
    def __init__(
        self,
        scenario: List[StepDemand],
        service_rate: int,
        switch_penalty: float,
        layout: Dict[str, object],
    ) -> None:
        self.scenario = scenario
        self.steps = len(scenario)
        self.service_rate = service_rate
        self.switch_penalty = switch_penalty
        self.layout = layout

        self.nodes = self._build_nodes(layout)
        self.node_ids = [node.node_id for node in self.nodes]
        self.neighbors = self._build_neighbors()

        self.current_step = 0
        self.network_mode = 0
        self.current_phase_by_node = {node_id: 0 for node_id in self.node_ids}

        self.queues = {
            node_id: {direction: 0 for direction in DIRECTIONS}
            for node_id in self.node_ids
        }
        self.emergency_queues = {
            node_id: {direction: 0 for direction in DIRECTIONS}
            for node_id in self.node_ids
        }

        self.total_wait_accum = 0.0
        self.emergency_wait_accum = 0.0
        self.total_queue_accum = 0.0
        self.total_arrivals = 0
        self.throughput = 0
        self.normal_served = 0
        self.emergency_served = 0
        self.network_switches = 0

        self.series = self._empty_series()

    def _empty_series(self) -> Dict[str, object]:
        return {
            "queue": [],
            "throughput": [],
            "phase": [],
            "avg_wait": [],
            "emergency_queue": [],
            "active_mode": [],
            "directional_queue": {direction: [] for direction in DIRECTIONS},
            "directional_emergency": {direction: [] for direction in DIRECTIONS},
            "arrivals_by_direction": {direction: [] for direction in DIRECTIONS},
            "served_by_direction": {direction: [] for direction in DIRECTIONS},
            "intersection_phase": {node_id: [] for node_id in self.node_ids},
            "intersection_queue": {node_id: [] for node_id in self.node_ids},
            "intersection_emergency": {node_id: [] for node_id in self.node_ids},
        }

    def _build_nodes(self, layout: Dict[str, object]) -> List[IntersectionNode]:
        raw_nodes = layout.get("intersections", [])
        if not raw_nodes:
            return [IntersectionNode(node_id="I1", x=0.0, y=0.0, row=0, col=0)]

        xs = sorted({float(node["x"]) for node in raw_nodes})
        ys = sorted({float(node["y"]) for node in raw_nodes})

        nodes: List[IntersectionNode] = []
        for raw_node in raw_nodes:
            x = float(raw_node["x"])
            y = float(raw_node["y"])
            nodes.append(
                IntersectionNode(
                    node_id=str(raw_node["id"]),
                    x=x,
                    y=y,
                    row=ys.index(y),
                    col=xs.index(x),
                )
            )
        return nodes

    def _build_neighbors(self) -> Dict[str, Dict[str, str | None]]:
        neighbors: Dict[str, Dict[str, str | None]] = {}
        for node in self.nodes:
            north: Tuple[float, str] | None = None
            south: Tuple[float, str] | None = None
            east: Tuple[float, str] | None = None
            west: Tuple[float, str] | None = None

            for other in self.nodes:
                if other.node_id == node.node_id:
                    continue

                same_column = other.col == node.col
                same_row = other.row == node.row

                if same_column and other.y < node.y:
                    distance = node.y - other.y
                    if north is None or distance < north[0]:
                        north = (distance, other.node_id)
                if same_column and other.y > node.y:
                    distance = other.y - node.y
                    if south is None or distance < south[0]:
                        south = (distance, other.node_id)
                if same_row and other.x > node.x:
                    distance = other.x - node.x
                    if east is None or distance < east[0]:
                        east = (distance, other.node_id)
                if same_row and other.x < node.x:
                    distance = node.x - other.x
                    if west is None or distance < west[0]:
                        west = (distance, other.node_id)

            neighbors[node.node_id] = {
                "N": south[1] if south else None,
                "S": north[1] if north else None,
                "E": west[1] if west else None,
                "W": east[1] if east else None,
            }
        return neighbors

    def reset(self) -> State:
        self.current_step = 0
        self.network_mode = 0
        self.current_phase_by_node = {node_id: 0 for node_id in self.node_ids}

        self.queues = {
            node_id: {direction: 0 for direction in DIRECTIONS}
            for node_id in self.node_ids
        }
        self.emergency_queues = {
            node_id: {direction: 0 for direction in DIRECTIONS}
            for node_id in self.node_ids
        }

        self.total_wait_accum = 0.0
        self.emergency_wait_accum = 0.0
        self.total_queue_accum = 0.0
        self.total_arrivals = 0
        self.throughput = 0
        self.normal_served = 0
        self.emergency_served = 0
        self.network_switches = 0

        self.series = self._empty_series()

        return self._state()

    def _node_queue_total(self, node_id: str) -> int:
        return sum(self.queues[node_id].values()) + sum(self.emergency_queues[node_id].values())

    def _aggregate_directional_loads(self) -> Dict[str, int]:
        totals = {direction: 0 for direction in DIRECTIONS}
        for node_id in self.node_ids:
            for direction in DIRECTIONS:
                totals[direction] += self.queues[node_id][direction] + self.emergency_queues[node_id][direction]
        return totals

    def _state(self) -> State:
        totals = self._aggregate_directional_loads()
        ns_load = totals["N"] + totals["S"]
        ew_load = totals["E"] + totals["W"]
        total_load = ns_load + ew_load

        if total_load < 18:
            queue_bucket = 0
        elif total_load < 36:
            queue_bucket = 1
        elif total_load < 60:
            queue_bucket = 2
        elif total_load < 92:
            queue_bucket = 3
        else:
            queue_bucket = 4

        imbalance = ns_load - ew_load
        if imbalance < -18:
            imbalance_bucket = 0
        elif imbalance < -6:
            imbalance_bucket = 1
        elif imbalance <= 6:
            imbalance_bucket = 2
        elif imbalance <= 18:
            imbalance_bucket = 3
        else:
            imbalance_bucket = 4

        ns_emergency = sum(
            self.emergency_queues[node_id]["N"] + self.emergency_queues[node_id]["S"]
            for node_id in self.node_ids
        )
        ew_emergency = sum(
            self.emergency_queues[node_id]["E"] + self.emergency_queues[node_id]["W"]
            for node_id in self.node_ids
        )
        if ns_emergency == 0 and ew_emergency == 0:
            emergency_bucket = 0
        elif ns_emergency > ew_emergency:
            emergency_bucket = 1
        elif ew_emergency > ns_emergency:
            emergency_bucket = 2
        else:
            emergency_bucket = 3

        time_bucket = min(3, int((self.current_step / max(1, self.steps)) * 4))
        return (queue_bucket, imbalance_bucket, self.network_mode, emergency_bucket, time_bucket)

    def _network_phase_for_node(self, node: IntersectionNode) -> int:
        cycle_span = 6
        if self.network_mode == 0:
            offset = (node.row * 2 + node.col) % cycle_span
            return 0 if ((self.current_step + offset) % cycle_span) < 4 else 1

        offset = (node.col * 2 + node.row) % cycle_span
        return 1 if ((self.current_step + offset) % cycle_span) < 4 else 0

    def _weights_for_direction(self, direction: str) -> List[float]:
        if not self.nodes:
            return [1.0]

        if direction == "N":
            distances = [node.y for node in self.nodes]
        elif direction == "S":
            max_y = max(node.y for node in self.nodes)
            distances = [max_y - node.y for node in self.nodes]
        elif direction == "E":
            max_x = max(node.x for node in self.nodes)
            distances = [max_x - node.x for node in self.nodes]
        else:
            distances = [node.x for node in self.nodes]

        max_distance = max(distances) if distances else 1.0
        weights: List[float] = []
        for distance in distances:
            normalized = 1.0 - (distance / max(1.0, max_distance))
            weights.append(1.0 + 2.4 * normalized)
        return weights

    def _distribute_to_nodes(self, count: int, direction: str) -> Dict[str, int]:
        weights = self._weights_for_direction(direction)
        total_weight = sum(weights)
        allocations: Dict[str, int] = {node_id: 0 for node_id in self.node_ids}

        if count <= 0 or total_weight <= 0:
            return allocations

        raw_values = [(count * weight) / total_weight for weight in weights]
        remainders: List[Tuple[float, str]] = []
        assigned = 0

        for node, raw_value in zip(self.nodes, raw_values):
            base = int(math.floor(raw_value))
            allocations[node.node_id] = base
            assigned += base
            remainders.append((raw_value - base, node.node_id))

        remainders.sort(key=lambda item: (-item[0], item[1]))
        for _, node_id in remainders[: count - assigned]:
            allocations[node_id] += 1

        return allocations

    def _serve_intersection(
        self,
        node_id: str,
        phase: int,
    ) -> Tuple[int, int, Dict[str, int], List[Tuple[str, str, int, int]]]:
        served = 0
        emergency_served = 0
        served_by_direction = {direction: 0 for direction in DIRECTIONS}
        transfers: List[Tuple[str, str, int, int]] = []

        for direction in PHASE_TO_DIRECTIONS[phase]:
            capacity = self.service_rate

            use_for_emergency = min(capacity, self.emergency_queues[node_id][direction])
            self.emergency_queues[node_id][direction] -= use_for_emergency
            capacity -= use_for_emergency

            use_for_regular = min(capacity, self.queues[node_id][direction])
            self.queues[node_id][direction] -= use_for_regular

            downstream = self.neighbors[node_id][direction]
            transfer_regular = 0
            transfer_emergency = 0
            if downstream is not None:
                transfer_regular = int(round(use_for_regular * 0.45))
                transfer_emergency = int(round(use_for_emergency * 0.65))
                if transfer_regular or transfer_emergency:
                    transfers.append((downstream, direction, transfer_regular, transfer_emergency))

            served_here = use_for_regular + use_for_emergency
            served += served_here
            emergency_served += use_for_emergency
            served_by_direction[direction] = served_here

        return served, emergency_served, served_by_direction, transfers

    def step(self, action: int) -> Tuple[State, float, bool, Dict[str, float]]:
        if self.current_step >= self.steps:
            return self._state(), 0.0, True, {}

        switched = 1 if action == 1 else 0
        if switched:
            self.network_mode = 1 - self.network_mode
            self.network_switches += 1

        for node in self.nodes:
            self.current_phase_by_node[node.node_id] = self._network_phase_for_node(node)

        demand = self.scenario[self.current_step]
        for direction in DIRECTIONS:
            arrival_split = self._distribute_to_nodes(demand.arrivals[direction], direction)
            emergency_split = self._distribute_to_nodes(demand.emergency[direction], direction)
            for node_id in self.node_ids:
                self.queues[node_id][direction] += arrival_split[node_id]
                self.emergency_queues[node_id][direction] += emergency_split[node_id]

        transfers: List[Tuple[str, str, int, int]] = []
        served_step = 0
        emergency_served_step = 0
        served_by_direction_total = {direction: 0 for direction in DIRECTIONS}

        for node_id in self.node_ids:
            phase = self.current_phase_by_node[node_id]
            served, emergency_served, served_by_direction, node_transfers = self._serve_intersection(
                node_id=node_id,
                phase=phase,
            )
            served_step += served
            emergency_served_step += emergency_served
            transfers.extend(node_transfers)
            for direction in DIRECTIONS:
                served_by_direction_total[direction] += served_by_direction[direction]

        for downstream, direction, regular_count, emergency_count in transfers:
            self.queues[downstream][direction] += regular_count
            self.emergency_queues[downstream][direction] += emergency_count

        directional_totals = self._aggregate_directional_loads()
        queue_total = sum(directional_totals.values())
        emergency_total = sum(
            self.emergency_queues[node_id][direction]
            for node_id in self.node_ids
            for direction in DIRECTIONS
        )
        node_totals = {node_id: self._node_queue_total(node_id) for node_id in self.node_ids}

        self.total_wait_accum += float(queue_total)
        self.emergency_wait_accum += float(emergency_total)
        self.total_queue_accum += float(queue_total)
        self.total_arrivals += sum(demand.arrivals.values()) + sum(demand.emergency.values())
        self.throughput += served_step
        self.normal_served += served_step - emergency_served_step
        self.emergency_served += emergency_served_step

        pressure_spread = max(node_totals.values(), default=0) - min(node_totals.values(), default=0)
        reward = -(
            0.68 * queue_total
            + 2.75 * emergency_total
            + 0.18 * pressure_spread
            + switched * self.switch_penalty
        )

        dominant_phase = 0
        phase_zero_count = sum(1 for phase in self.current_phase_by_node.values() if phase == 0)
        if phase_zero_count < len(self.current_phase_by_node) / 2:
            dominant_phase = 1

        self.series["queue"].append(queue_total)
        self.series["throughput"].append(served_step)
        self.series["phase"].append(dominant_phase)
        self.series["avg_wait"].append(round(self.total_wait_accum / max(1, self.throughput), 3))
        self.series["emergency_queue"].append(emergency_total)
        self.series["active_mode"].append(self.network_mode)

        for direction in DIRECTIONS:
            self.series["directional_queue"][direction].append(directional_totals[direction])
            self.series["directional_emergency"][direction].append(
                sum(self.emergency_queues[node_id][direction] for node_id in self.node_ids)
            )
            self.series["arrivals_by_direction"][direction].append(
                demand.arrivals[direction] + demand.emergency[direction]
            )
            self.series["served_by_direction"][direction].append(served_by_direction_total[direction])

        for node_id in self.node_ids:
            self.series["intersection_phase"][node_id].append(self.current_phase_by_node[node_id])
            self.series["intersection_queue"][node_id].append(node_totals[node_id])
            self.series["intersection_emergency"][node_id].append(
                sum(self.emergency_queues[node_id].values())
            )

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
        remaining = sum(self._node_queue_total(node_id) for node_id in self.node_ids)
        busiest_intersection = max(
            (max(values, default=0) for values in self.series["intersection_queue"].values()),
            default=0,
        )

        return {
            "avg_wait": round(avg_wait, 3),
            "avg_queue": round(avg_queue, 3),
            "avg_intersection_queue": round(avg_queue / max(1, len(self.node_ids)), 3),
            "throughput": float(self.throughput),
            "throughput_per_step": round(self.throughput / max(1, self.steps), 3),
            "emergency_avg_wait": round(emergency_avg_wait, 3),
            "max_queue": float(max(self.series["queue"], default=0)),
            "busiest_intersection_queue": float(busiest_intersection),
            "clearance_ratio": round(self.throughput / max(1, self.total_arrivals), 3),
            "remaining_vehicles": float(remaining),
            "network_switches": float(self.network_switches),
        }
