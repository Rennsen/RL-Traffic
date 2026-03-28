from __future__ import annotations

from typing import Any, Dict

DIRECTIONS = ("N", "S", "E", "W")
PHASE_TO_DIRECTIONS = {
    0: ("N", "S"),
    1: ("E", "W"),
}
SUPPORTED_PATTERNS = (
    "balanced",
    "rush_hour_ns",
    "rush_hour_ew",
    "event_spike",
    "random",
)

DISTRICT_PROFILES: Dict[str, Dict[str, Any]] = {
    "downtown_core": {
        "name": "Downtown Core",
        "description": "High-density mixed traffic with recurrent commuter peaks.",
        "manager": {
            "owner": "Rayan Derradji",
            "team": "Signal Ops Alpha",
            "contact": "rayan.derradji@flowmind.city",
        },
        "traffic_pattern": "rush_hour_ns",
        "default_params": {
            "fixed_cycle": 16,
            "service_rate": 3,
            "emergency_rate": 0.03,
        },
        "actual_metrics": {
            "avg_wait": 58.4,
            "avg_queue": 268.0,
            "throughput": 1120.0,
            "emergency_avg_wait": 11.5,
            "clearance_ratio": 0.67,
        },
        "layout": {
            "width": 960,
            "height": 560,
            "roads": [
                {"id": "d_r1", "from": [20, 140], "to": [940, 140], "lanes": 3},
                {"id": "d_r2", "from": [20, 300], "to": [940, 300], "lanes": 3},
                {"id": "d_r3", "from": [20, 460], "to": [940, 460], "lanes": 2},
                {"id": "d_r4", "from": [220, 20], "to": [220, 540], "lanes": 2},
                {"id": "d_r5", "from": [480, 20], "to": [480, 540], "lanes": 3},
                {"id": "d_r6", "from": [740, 20], "to": [740, 540], "lanes": 2},
            ],
            "intersections": [
                {"id": "D1", "x": 220, "y": 140},
                {"id": "D2", "x": 480, "y": 140},
                {"id": "D3", "x": 740, "y": 140},
                {"id": "D4", "x": 220, "y": 300},
                {"id": "D5", "x": 480, "y": 300},
                {"id": "D6", "x": 740, "y": 300},
                {"id": "D7", "x": 220, "y": 460},
                {"id": "D8", "x": 480, "y": 460},
                {"id": "D9", "x": 740, "y": 460},
            ],
        },
    },
    "university_ring": {
        "name": "University Ring",
        "description": "Bicycle-heavy and transit-priority corridors with class-hour pulses.",
        "manager": {
            "owner": "Tarek Ait Ahmed",
            "team": "Campus Mobility Cell",
            "contact": "tarek.ait@flowmind.city",
        },
        "traffic_pattern": "event_spike",
        "default_params": {
            "fixed_cycle": 14,
            "service_rate": 2,
            "emergency_rate": 0.02,
        },
        "actual_metrics": {
            "avg_wait": 46.7,
            "avg_queue": 172.0,
            "throughput": 950.0,
            "emergency_avg_wait": 8.9,
            "clearance_ratio": 0.71,
        },
        "layout": {
            "width": 960,
            "height": 560,
            "roads": [
                {"id": "u_r1", "from": [170, 90], "to": [790, 90], "lanes": 2},
                {"id": "u_r2", "from": [790, 90], "to": [790, 470], "lanes": 2},
                {"id": "u_r3", "from": [790, 470], "to": [170, 470], "lanes": 2},
                {"id": "u_r4", "from": [170, 470], "to": [170, 90], "lanes": 2},
                {"id": "u_r5", "from": [310, 160], "to": [650, 160], "lanes": 2},
                {"id": "u_r6", "from": [650, 160], "to": [650, 400], "lanes": 2},
                {"id": "u_r7", "from": [650, 400], "to": [310, 400], "lanes": 2},
                {"id": "u_r8", "from": [310, 400], "to": [310, 160], "lanes": 2},
                {"id": "u_r9", "from": [170, 280], "to": [310, 280], "lanes": 1},
                {"id": "u_r10", "from": [650, 280], "to": [790, 280], "lanes": 1},
                {"id": "u_r11", "from": [480, 90], "to": [480, 160], "lanes": 1},
                {"id": "u_r12", "from": [480, 400], "to": [480, 470], "lanes": 1},
            ],
            "intersections": [
                {"id": "U1", "x": 170, "y": 90},
                {"id": "U2", "x": 480, "y": 90},
                {"id": "U3", "x": 790, "y": 90},
                {"id": "U4", "x": 170, "y": 280},
                {"id": "U5", "x": 790, "y": 280},
                {"id": "U6", "x": 170, "y": 470},
                {"id": "U7", "x": 480, "y": 470},
                {"id": "U8", "x": 790, "y": 470},
                {"id": "U9", "x": 310, "y": 160},
                {"id": "U10", "x": 650, "y": 160},
                {"id": "U11", "x": 650, "y": 400},
                {"id": "U12", "x": 310, "y": 400},
                {"id": "U13", "x": 310, "y": 280},
                {"id": "U14", "x": 650, "y": 280},
            ],
            "parking_lots": [
                {"id": "PK-A", "x": 58, "y": 106, "w": 86, "h": 120, "slots": 28},
                {"id": "PK-B", "x": 816, "y": 106, "w": 86, "h": 120, "slots": 24},
                {"id": "PK-C", "x": 58, "y": 328, "w": 86, "h": 120, "slots": 30},
                {"id": "PK-D", "x": 816, "y": 328, "w": 86, "h": 120, "slots": 26},
            ],
            "green_zones": [
                {"id": "Campus Lawn", "x": 364, "y": 212, "w": 232, "h": 136},
            ],
        },
    },
    "industrial_port": {
        "name": "Industrial Port",
        "description": "Freight-dominant grid with heavy east-west truck pressure.",
        "manager": {
            "owner": "Anes Hadim",
            "team": "Freight Corridor Unit",
            "contact": "anes.hadim@flowmind.city",
        },
        "traffic_pattern": "rush_hour_ew",
        "default_params": {
            "fixed_cycle": 20,
            "service_rate": 4,
            "emergency_rate": 0.015,
        },
        "actual_metrics": {
            "avg_wait": 72.2,
            "avg_queue": 326.0,
            "throughput": 1380.0,
            "emergency_avg_wait": 13.8,
            "clearance_ratio": 0.64,
        },
        "layout": {
            "width": 960,
            "height": 560,
            "roads": [
                {"id": "p_r1", "from": [40, 120], "to": [700, 120], "lanes": 4},
                {"id": "p_r2", "from": [40, 250], "to": [700, 250], "lanes": 3},
                {"id": "p_r3", "from": [40, 390], "to": [700, 390], "lanes": 3},
                {"id": "p_r4", "from": [160, 36], "to": [160, 530], "lanes": 2},
                {"id": "p_r5", "from": [380, 36], "to": [380, 530], "lanes": 2},
                {"id": "p_r6", "from": [600, 36], "to": [600, 530], "lanes": 2},
                {"id": "p_r7", "from": [700, 120], "to": [892, 120], "lanes": 2},
                {"id": "p_r8", "from": [700, 250], "to": [892, 250], "lanes": 2},
                {"id": "p_r9", "from": [700, 390], "to": [892, 390], "lanes": 2},
                {"id": "p_r10", "from": [740, 88], "to": [740, 480], "lanes": 1},
                {"id": "p_r11", "from": [814, 88], "to": [814, 480], "lanes": 1},
                {"id": "p_r12", "from": [888, 88], "to": [888, 480], "lanes": 1},
            ],
            "intersections": [
                {"id": "P1", "x": 160, "y": 120},
                {"id": "P2", "x": 380, "y": 120},
                {"id": "P3", "x": 600, "y": 120},
                {"id": "P4", "x": 160, "y": 250},
                {"id": "P5", "x": 380, "y": 250},
                {"id": "P6", "x": 600, "y": 250},
                {"id": "P7", "x": 160, "y": 390},
                {"id": "P8", "x": 380, "y": 390},
                {"id": "P9", "x": 600, "y": 390},
                {"id": "P10", "x": 740, "y": 120},
                {"id": "P11", "x": 814, "y": 250},
                {"id": "P12", "x": 888, "y": 390},
            ],
            "water": {
                "x": 706,
                "y": 18,
                "w": 236,
                "h": 524,
                "label": "Harbor Channel",
            },
            "port_yards": [
                {"id": "Yard-A", "x": 52, "y": 448, "w": 196, "h": 86},
                {"id": "Yard-B", "x": 274, "y": 448, "w": 196, "h": 86},
                {"id": "Yard-C", "x": 496, "y": 448, "w": 188, "h": 86},
            ],
        },
    },
}

SUPPORTED_DISTRICTS = tuple(DISTRICT_PROFILES.keys())
