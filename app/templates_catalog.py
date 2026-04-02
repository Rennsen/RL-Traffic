from __future__ import annotations

from typing import Any, Dict, List


def list_scenario_templates() -> List[Dict[str, Any]]:
    return [
        {
            "template_id": "rush_hour_morning",
            "name": "Morning Rush Hour",
            "description": "Peak commuter surge with elevated emergency arrivals.",
            "config": {
                "traffic_pattern": "rush_hour_ns",
                "episodes": 280,
                "steps_per_episode": 240,
                "fixed_cycle": 16,
                "service_rate": 3,
                "emergency_rate": 0.03,
                "learning_rate": 0.12,
                "discount_factor": 0.95,
                "epsilon_decay": 0.992,
            },
        },
        {
            "template_id": "event_day",
            "name": "Event Day Spike",
            "description": "Short but intense east-west demand pulse.",
            "config": {
                "traffic_pattern": "event_spike",
                "episodes": 220,
                "steps_per_episode": 220,
                "fixed_cycle": 14,
                "service_rate": 2,
                "emergency_rate": 0.02,
                "learning_rate": 0.11,
                "discount_factor": 0.94,
                "epsilon_decay": 0.993,
            },
        },
        {
            "template_id": "freight_corridor",
            "name": "Freight Corridor Push",
            "description": "Industrial freight pressure with higher throughput target.",
            "config": {
                "traffic_pattern": "rush_hour_ew",
                "episodes": 320,
                "steps_per_episode": 280,
                "fixed_cycle": 20,
                "service_rate": 4,
                "emergency_rate": 0.015,
                "learning_rate": 0.1,
                "discount_factor": 0.96,
                "epsilon_decay": 0.991,
            },
        },
        {
            "template_id": "emergency_clearance",
            "name": "Emergency Clearance",
            "description": "Prioritize emergency vehicles while keeping base queues stable.",
            "config": {
                "traffic_pattern": "balanced",
                "episodes": 260,
                "steps_per_episode": 220,
                "fixed_cycle": 15,
                "service_rate": 3,
                "emergency_rate": 0.06,
                "learning_rate": 0.13,
                "discount_factor": 0.93,
                "epsilon_decay": 0.994,
            },
        },
    ]
