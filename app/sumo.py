from __future__ import annotations

from collections import defaultdict
from math import hypot
from pathlib import Path
import shutil
import subprocess
import os
from textwrap import dedent
from typing import Any, Dict, List, Tuple
import math
import random

try:
    import sumolib  # type: ignore  # noqa: F401
    import traci  # type: ignore  # noqa: F401

    SUMO_AVAILABLE = True
except Exception:
    SUMO_AVAILABLE = False

SUMO_BINARY = shutil.which("sumo")
SUMO_GUI_BINARY = shutil.which("sumo-gui")
NETCONVERT_BINARY = shutil.which("netconvert")
XVFB_RUN_BINARY = shutil.which("xvfb-run")


def get_sumo_status() -> Dict[str, Any]:
    missing: List[str] = []
    if not SUMO_AVAILABLE:
        missing.extend(["python:traci", "python:sumolib"])
    if not NETCONVERT_BINARY:
        missing.append("binary:netconvert")
    if not SUMO_BINARY:
        missing.append("binary:sumo")

    runtime_ready = len(missing) == 0
    if runtime_ready:
        return {
            "available": True,
            "runtime_ready": True,
            "active_mode": "sumo_ready",
            "message": "SUMO libraries and binaries detected. FlowMind can generate artifacts and execute live SUMO runtime.",
            "paths": {
                "sumo": SUMO_BINARY,
                "sumo_gui": SUMO_GUI_BINARY,
                "netconvert": NETCONVERT_BINARY,
            },
            "missing_requirements": [],
        }

    return {
        "available": SUMO_AVAILABLE,
        "runtime_ready": False,
        "active_mode": "export_fallback",
        "message": (
            "SUMO runtime is not fully available in this environment. "
            "FlowMind will generate connected SUMO-ready artifacts and use the internal simulator for metrics."
        ),
        "paths": {
            "sumo": SUMO_BINARY,
            "sumo_gui": SUMO_GUI_BINARY,
            "netconvert": NETCONVERT_BINARY,
        },
        "missing_requirements": missing,
    }


def _coord_key(x: float, y: float) -> str:
    return f"{int(round(x))}:{int(round(y))}"


def _point_on_segment(
    px: float,
    py: float,
    ax: float,
    ay: float,
    bx: float,
    by: float,
    tolerance: float = 1e-6,
) -> bool:
    cross = (px - ax) * (by - ay) - (py - ay) * (bx - ax)
    if abs(cross) > tolerance:
        return False

    dot = (px - ax) * (bx - ax) + (py - ay) * (by - ay)
    if dot < -tolerance:
        return False

    squared_length = (bx - ax) ** 2 + (by - ay) ** 2
    if dot - squared_length > tolerance:
        return False

    return True


def _param_along_segment(
    px: float,
    py: float,
    ax: float,
    ay: float,
    bx: float,
    by: float,
) -> float:
    dx = bx - ax
    dy = by - ay
    denominator = dx * dx + dy * dy
    if denominator <= 1e-9:
        return 0.0
    return ((px - ax) * dx + (py - ay) * dy) / denominator


def _ensure_node(
    coord_map: Dict[str, str],
    nodes: List[Dict[str, Any]],
    x: float,
    y: float,
    prefix: str,
    node_type: str = "priority",
) -> str:
    key = _coord_key(x, y)
    existing = coord_map.get(key)
    if existing is not None:
        return existing

    node_id = f"{prefix}_{len(nodes) + 1}"
    coord_map[key] = node_id
    nodes.append({"id": node_id, "x": x, "y": y, "type": node_type})
    return node_id


def _build_sumo_nodes(layout: Dict[str, Any]) -> List[Dict[str, Any]]:
    nodes: List[Dict[str, Any]] = []
    coord_map: Dict[str, str] = {}

    for intersection in layout.get("intersections", []):
        node_id = str(intersection["id"])
        coord_map[_coord_key(intersection["x"], intersection["y"])] = node_id
        nodes.append(
            {
                "id": node_id,
                "x": float(intersection["x"]),
                "y": float(intersection["y"]),
                "type": "traffic_light",
            }
        )

    for road in layout.get("roads", []):
        _ensure_node(coord_map, nodes, float(road["from"][0]), float(road["from"][1]), "entry")
        _ensure_node(coord_map, nodes, float(road["to"][0]), float(road["to"][1]), "exit")

    return nodes


def _build_sumo_edges(layout: Dict[str, Any], nodes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    coord_map = {_coord_key(node["x"], node["y"]): node["id"] for node in nodes}

    intersections: List[Tuple[str, float, float]] = []
    for node in nodes:
        if node["type"] == "traffic_light":
            intersections.append((node["id"], float(node["x"]), float(node["y"])))

    edges: List[Dict[str, Any]] = []

    for road in layout.get("roads", []):
        ax = float(road["from"][0])
        ay = float(road["from"][1])
        bx = float(road["to"][0])
        by = float(road["to"][1])

        lanes = int(road.get("lanes", 1))
        points: List[Tuple[float, str, float, float]] = []

        start_id = coord_map[_coord_key(ax, ay)]
        end_id = coord_map[_coord_key(bx, by)]

        points.append((_param_along_segment(ax, ay, ax, ay, bx, by), start_id, ax, ay))
        points.append((_param_along_segment(bx, by, ax, ay, bx, by), end_id, bx, by))

        for node_id, x, y in intersections:
            if node_id in (start_id, end_id):
                continue
            if _point_on_segment(x, y, ax, ay, bx, by):
                t = _param_along_segment(x, y, ax, ay, bx, by)
                points.append((t, node_id, x, y))

        deduped: Dict[str, Tuple[float, str, float, float]] = {}
        for item in points:
            deduped[item[1]] = item

        sorted_points = sorted(deduped.values(), key=lambda item: item[0])
        if len(sorted_points) < 2:
            continue

        for segment_index in range(len(sorted_points) - 1):
            _, from_id, from_x, from_y = sorted_points[segment_index]
            _, to_id, to_x, to_y = sorted_points[segment_index + 1]

            length = hypot(to_x - from_x, to_y - from_y)
            if length < 1.0:
                continue

            speed = round(10.0 + min(10.0, lanes * 1.7 + length / 240.0), 1)
            edge_id_base = f"{road['id']}_s{segment_index + 1}"

            edges.append(
                {
                    "id": f"{edge_id_base}_ab",
                    "from": from_id,
                    "to": to_id,
                    "lanes": lanes,
                    "speed": speed,
                    "length": round(length, 2),
                }
            )
            edges.append(
                {
                    "id": f"{edge_id_base}_ba",
                    "from": to_id,
                    "to": from_id,
                    "lanes": lanes,
                    "speed": speed,
                    "length": round(length, 2),
                }
            )

    return edges


def _build_connections(edges: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    incoming_by_node: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    outgoing_by_node: Dict[str, List[Dict[str, Any]]] = defaultdict(list)

    for edge in edges:
        outgoing_by_node[edge["from"]].append(edge)
        incoming_by_node[edge["to"]].append(edge)

    connection_pairs: set[Tuple[str, str]] = set()
    for node_id, incoming in incoming_by_node.items():
        outgoing = outgoing_by_node.get(node_id, [])
        if not incoming or not outgoing:
            continue

        for in_edge in incoming:
            for out_edge in outgoing:
                if out_edge["to"] == in_edge["from"]:
                    continue
                connection_pairs.add((in_edge["id"], out_edge["id"]))

    return [{"from": item[0], "to": item[1]} for item in sorted(connection_pairs)]


def _build_flow_profiles(
    district_id: str,
    edges: List[Dict[str, Any]],
    nodes: List[Dict[str, Any]],
    traffic_pattern: str,
) -> List[Dict[str, Any]]:
    if not edges:
        return []

    node_type = {node["id"]: node["type"] for node in nodes}
    node_coord = {node["id"]: (float(node["x"]), float(node["y"])) for node in nodes}

    entry_edges = [
        edge
        for edge in edges
        if node_type.get(edge["from"]) != "traffic_light" and node_type.get(edge["to"]) == "traffic_light"
    ]
    exit_edges = [
        edge
        for edge in edges
        if node_type.get(edge["from"]) == "traffic_light" and node_type.get(edge["to"]) != "traffic_light"
    ]

    if not entry_edges or not exit_edges:
        fallback_entries = edges[: min(6, len(edges))]
        fallback_exits = edges[-min(6, len(edges)) :]
        fallback_flows: List[Dict[str, Any]] = []

        for idx, edge in enumerate(fallback_entries):
            destination = fallback_exits[-(idx + 1)]
            if destination["id"] == edge["id"] and len(fallback_exits) > 1:
                destination = fallback_exits[(idx + 1) % len(fallback_exits)]

            fallback_flows.append(
                {
                    "id": f"{district_id}_flow_{idx + 1}",
                    "from": edge["id"],
                    "to": destination["id"],
                    "probability": 0.1,
                    "begin": 0,
                    "end": 3600,
                }
            )

        return fallback_flows

    def edge_axis(edge: Dict[str, Any]) -> str:
        from_coord = node_coord.get(edge["from"], (0.0, 0.0))
        to_coord = node_coord.get(edge["to"], (0.0, 0.0))
        horizontal = abs(to_coord[0] - from_coord[0]) >= abs(to_coord[1] - from_coord[1])
        return "ew" if horizontal else "ns"

    selected_entries = entry_edges[: min(len(entry_edges), 14)]
    flows: List[Dict[str, Any]] = []

    for index, in_edge in enumerate(selected_entries, start=1):
        in_to_coord = node_coord.get(in_edge["to"], (0.0, 0.0))

        candidate_exits = [
            out_edge
            for out_edge in exit_edges
            if out_edge["from"] != in_edge["to"]
        ]
        if not candidate_exits:
            candidate_exits = exit_edges

        best_exit = max(
            candidate_exits,
            key=lambda out_edge: hypot(
                node_coord.get(out_edge["from"], (0.0, 0.0))[0] - in_to_coord[0],
                node_coord.get(out_edge["from"], (0.0, 0.0))[1] - in_to_coord[1],
            ),
        )

        axis = edge_axis(in_edge)
        if traffic_pattern == "rush_hour_ns":
            probability = 0.2 if axis == "ns" else 0.08
        elif traffic_pattern == "rush_hour_ew":
            probability = 0.2 if axis == "ew" else 0.08
        elif traffic_pattern == "event_spike":
            probability = 0.16 if axis == "ew" else 0.14
        elif traffic_pattern == "random":
            probability = 0.06 + ((index * 7) % 9) / 100.0
        else:
            probability = 0.12

        flows.append(
            {
                "id": f"{district_id}_flow_{index}",
                "from": in_edge["id"],
                "to": best_exit["id"],
                "probability": round(probability, 3),
                "begin": 0,
                "end": 3600,
            }
        )

    return flows


def _preview_xml(title: str, lines: List[str]) -> str:
    preview = "\n".join(lines[:12])
    return dedent(
        f"""\
        {title}
        {preview}
        """
    ).strip()


def _render_xml(lines: List[str]) -> str:
    return "\n".join(lines) + "\n"


def _write_sumo_files(output_dir: Path, documents: Dict[str, str]) -> Dict[str, str]:
    output_dir.mkdir(parents=True, exist_ok=True)
    written: Dict[str, str] = {}

    for filename, content in documents.items():
        file_path = output_dir / filename
        file_path.write_text(content, encoding="utf-8")
        written[filename] = str(file_path.resolve())

    return written


def _write_sumocfg(
    sumocfg_path: Path,
    net_path: Path,
    route_path: Path,
    end_step: int,
) -> None:
    content = dedent(
        f"""\
        <configuration>
          <input>
            <net-file value="{net_path.name}"/>
            <route-files value="{route_path.name}"/>
          </input>
          <time>
            <begin value="0"/>
            <end value="{max(1, int(end_step))}"/>
          </time>
          <report>
            <no-step-log value="true"/>
            <duration-log.disable value="true"/>
          </report>
        </configuration>
        """
    )
    sumocfg_path.write_text(content, encoding="utf-8")


def _netconvert_cmd(nodes_path: Path, edges_path: Path, connections_path: Path, net_path: Path) -> List[str]:
    return [
        str(NETCONVERT_BINARY),
        "--node-files",
        str(nodes_path),
        "--edge-files",
        str(edges_path),
        "--connection-files",
        str(connections_path),
        "--output-file",
        str(net_path),
        "--sidewalks.guess",
        "--crossings.guess",
        "--walkingareas",
        "--default.sidewalk-width",
        "3.4",
        "--default.crossing-width",
        "8.0",
        "--default.crossing-speed",
        "1.4",
        "--default.walkingarea-speed",
        "1.2",
        "--walkingareas.join-dist",
        "2.5",
        "--crossings.guess.speed-threshold",
        "18.0",
        "--tls.crossing-min.time",
        "6",
        "--tls.crossing-clearance.time",
        "3",
    ]


def _write_gui_settings(gui_settings_path: Path) -> None:
    content = dedent(
        """\
        <viewsettings>
          <scheme name="flowmind">
            <opengl antialiase="1" dither="0"/>
            <background backgroundColor="0.16,0.55,0.18" showGrid="0" gridXSize="100.00" gridYSize="100.00"/>
            <edges laneEdgeMode="0" scaleMode="0" laneShowBorders="0" showBikeMarkings="0"
                   showLinkDecals="1" showLinkRules="1" showRails="0" hideConnectors="1"
                   widthExaggeration="3.0" minSize="1.35" showDirection="0" showSublanes="0"
                   spreadSuperposed="0">
              <colorScheme name="uniform">
                <entry color="0.00,0.00,0.00" name="road"/>
                <entry color="0.30,0.30,0.30" name="sidewalk"/>
                <entry color="0.00,0.00,0.00" name="bike lane"/>
                <entry color="0.00,0.00,0.00,0" name="green verge"/>
                <entry color="1.00,1.00,1.00" name="crossing"/>
                <entry color="0.22,0.22,0.22" name="walkingarea"/>
                <entry color="0.12,0.12,0.12" name="railway"/>
                <entry color="0.10,0.10,0.10" name="rails on road"/>
                <entry color="0.00,0.00,0.00" name="no passenger"/>
                <entry color="0.35,0.00,0.00" name="closed"/>
                <entry color="0.15,0.55,0.20" name="connector"/>
                <entry color="0.80,0.45,0.10" name="forbidden"/>
              </colorScheme>
            </edges>
            <junctions junctionMode="0" drawShape="1" drawCrossingsAndWalkingareas="1"
                       showLane2Lane="0" junction_minSize="1.25" junction_exaggeration="1.45"
                       junction_constantSize="0" junction_constantSizeSelected="0">
              <colorScheme name="uniform">
                <entry color="0.00,0.00,0.00"/>
                <entry color="0.12,0.12,0.12" name="waterway"/>
                <entry color="0,0,0,0" name="railway"/>
              </colorScheme>
            </junctions>
            <vehicles vehicleMode="10" vehicleQuality="2" minVehicleSize="5.0" vehicleExaggeration="5.2" showBlinker="1">
              <colorScheme name="uniform">
                <entry color="1.00,0.88,0.05"/>
              </colorScheme>
              <colorScheme name="by speed" interpolated="1">
                <entry color="1.00,0.30,0.00" threshold="0.00"/>
                <entry color="0.05,0.85,1.00" threshold="13.90"/>
              </colorScheme>
            </vehicles>
          </scheme>
        </viewsettings>
        """
    )
    gui_settings_path.write_text(content, encoding="utf-8")


def run_sumo_runtime(
    artifact_report: Dict[str, Any],
    steps: int,
    seed: int,
) -> Dict[str, Any]:
    status = get_sumo_status()
    if not status.get("runtime_ready"):
        fallback = _synthesize_runtime_from_visualization(
            artifact_report=artifact_report,
            steps=steps,
            seed=seed,
        )
        fallback["executed"] = False
        fallback["reason"] = (
            "SUMO runtime requirements are missing. "
            "Playback frames were synthesized from the generated SUMO network."
        )
        fallback["missing_requirements"] = status.get("missing_requirements", [])
        return fallback

    artifacts = artifact_report.get("artifacts", {})
    generated_files = artifacts.get("generated_files", {})
    network_files = artifacts.get("network_files", {})
    output_directory = artifacts.get("output_directory")
    if not output_directory:
        fallback = _synthesize_runtime_from_visualization(
            artifact_report=artifact_report,
            steps=steps,
            seed=seed,
        )
        fallback["executed"] = False
        fallback["reason"] = "SUMO output directory is missing. Playback frames were synthesized."
        fallback["missing_requirements"] = []
        return fallback

    output_dir = Path(output_directory).resolve()
    nodes_path = generated_files.get(network_files.get("nodes", ""))
    edges_path = generated_files.get(network_files.get("edges", ""))
    connections_path = generated_files.get(network_files.get("connections", ""))
    routes_path = generated_files.get(network_files.get("routes", ""))

    if not nodes_path or not edges_path or not connections_path or not routes_path:
        fallback = _synthesize_runtime_from_visualization(
            artifact_report=artifact_report,
            steps=steps,
            seed=seed,
        )
        fallback["executed"] = False
        fallback["reason"] = "Generated SUMO XML files are incomplete. Playback frames were synthesized."
        fallback["missing_requirements"] = []
        return fallback

    base_name = network_files.get("nodes", "network.nodes.xml").replace(".nodes.xml", "")
    net_path = output_dir / f"{base_name}.net.xml"
    sumocfg_path = output_dir / f"{base_name}.sumocfg"

    netconvert_cmd = _netconvert_cmd(
        nodes_path=Path(str(nodes_path)),
        edges_path=Path(str(edges_path)),
        connections_path=Path(str(connections_path)),
        net_path=net_path,
    )

    try:
        subprocess.run(
            netconvert_cmd,
            cwd=str(output_dir),
            check=True,
            capture_output=True,
            text=True,
        )
    except subprocess.CalledProcessError as exc:
        return {
            "executed": False,
            "reason": "netconvert failed while compiling SUMO network.",
            "missing_requirements": [],
            "stderr": (exc.stderr or "").strip(),
            "stdout": (exc.stdout or "").strip(),
            "metrics": {},
            "time_series": {"queue": [], "throughput": []},
            "trace": {"frames": [], "sample_period": 1, "vehicle_limit": 0},
            "files": {
                "nodes": str(nodes_path),
                "edges": str(edges_path),
                "connections": str(connections_path),
                "routes": str(routes_path),
            },
        }

    _write_sumocfg(
        sumocfg_path=sumocfg_path,
        net_path=net_path,
        route_path=Path(str(routes_path)),
        end_step=max(1, int(steps)),
    )

    sumo_cmd = [
        str(SUMO_BINARY),
        "-c",
        str(sumocfg_path),
        "--seed",
        str(int(seed)),
        "--quit-on-end",
        "true",
        "--no-step-log",
        "true",
        "--duration-log.disable",
        "true",
    ]

    queue_series: List[float] = []
    throughput_series: List[float] = []
    vehicle_trace_frames: List[Dict[str, Any]] = []
    vehicle_limit = 280
    steps_executed = 0
    arrived_total = 0
    departed_total = 0
    wait_total = 0.0
    traci_started = False

    try:
        traci.start(sumo_cmd)  # type: ignore[name-defined]
        traci_started = True

        for _ in range(max(1, int(steps))):
            traci.simulationStep()  # type: ignore[name-defined]

            queue_now = 0.0
            wait_now = 0.0
            for edge_id in traci.edge.getIDList():  # type: ignore[name-defined]
                queue_now += float(traci.edge.getLastStepHaltingNumber(edge_id))  # type: ignore[name-defined]
                wait_now += float(traci.edge.getWaitingTime(edge_id))  # type: ignore[name-defined]

            arrived_step = int(traci.simulation.getArrivedNumber())  # type: ignore[name-defined]
            departed_step = int(traci.simulation.getDepartedNumber())  # type: ignore[name-defined]

            arrived_total += arrived_step
            departed_total += departed_step
            wait_total += wait_now
            steps_executed += 1
            queue_series.append(queue_now)
            throughput_series.append(float(arrived_step))

            vehicles_now: List[Dict[str, Any]] = []
            vehicle_ids = list(traci.vehicle.getIDList())  # type: ignore[name-defined]
            for vehicle_id in vehicle_ids[:vehicle_limit]:
                vx, vy = traci.vehicle.getPosition(vehicle_id)  # type: ignore[name-defined]
                vehicles_now.append(
                    {
                        "id": vehicle_id,
                        "x": round(float(vx), 2),
                        "y": round(float(vy), 2),
                        "speed": round(float(traci.vehicle.getSpeed(vehicle_id)), 2),  # type: ignore[name-defined]
                        "angle": round(float(traci.vehicle.getAngle(vehicle_id)), 1),  # type: ignore[name-defined]
                    }
                )

            vehicle_trace_frames.append(
                {
                    "step": steps_executed - 1,
                    "sim_time": float(traci.simulation.getTime()),  # type: ignore[name-defined]
                    "vehicle_count": len(vehicle_ids),
                    "truncated": len(vehicle_ids) > vehicle_limit,
                    "vehicles": vehicles_now,
                }
            )

            if traci.simulation.getMinExpectedNumber() <= 0 and steps_executed > 20:  # type: ignore[name-defined]
                break
    except Exception as exc:
        if traci_started:
            try:
                traci.close(False)  # type: ignore[name-defined]
            except Exception:
                pass
        return {
            "executed": False,
            "reason": "SUMO runtime failed during simulation step execution.",
            "missing_requirements": [],
            "error": str(exc),
            "metrics": {},
            "time_series": {"queue": queue_series, "throughput": throughput_series},
            "trace": {
                "frames": vehicle_trace_frames,
                "sample_period": 1,
                "vehicle_limit": vehicle_limit,
            },
            "files": {
                "net": str(net_path),
                "sumocfg": str(sumocfg_path),
                "routes": str(routes_path),
            },
        }
    finally:
        if traci_started:
            try:
                traci.close(False)  # type: ignore[name-defined]
            except Exception:
                pass

    avg_queue = (sum(queue_series) / len(queue_series)) if queue_series else 0.0
    avg_wait = wait_total / max(1, arrived_total)
    max_queue = max(queue_series, default=0.0)
    throughput_per_step = arrived_total / max(1, steps_executed)

    return {
        "executed": True,
        "reason": "",
        "missing_requirements": [],
        "metrics": {
            "avg_wait": round(avg_wait, 3),
            "avg_queue": round(avg_queue, 3),
            "max_queue": float(max_queue),
            "throughput": float(arrived_total),
            "departed": float(departed_total),
            "throughput_per_step": round(throughput_per_step, 3),
            "steps_executed": float(steps_executed),
        },
        "time_series": {
            "queue": queue_series,
            "throughput": throughput_series,
        },
        "trace": {
            "frames": vehicle_trace_frames,
            "sample_period": 1,
            "vehicle_limit": vehicle_limit,
        },
        "files": {
            "net": str(net_path),
            "sumocfg": str(sumocfg_path),
            "routes": str(routes_path),
        },
    }


def run_sumo_gui_snapshots(
    artifact_report: Dict[str, Any],
    steps: int,
    seed: int,
) -> Dict[str, Any]:
    if not SUMO_GUI_BINARY:
        return {
            "executed": False,
            "reason": "sumo-gui binary is not available.",
            "snapshot_dir": "",
            "frame_count": 0,
            "stderr": "",
            "stdout": "",
        }

    if not SUMO_AVAILABLE:
        return {
            "executed": False,
            "reason": "SUMO python libraries are not available for GUI capture.",
            "snapshot_dir": "",
            "frame_count": 0,
            "stderr": "",
            "stdout": "",
        }

    use_xvfb = False
    prefer_display = os.environ.get("SUMO_GUI_USE_DISPLAY") == "1"
    if prefer_display:
        if not os.environ.get("DISPLAY"):
            return {
                "executed": False,
                "reason": "DISPLAY is not set; SUMO-GUI requires a display server.",
                "snapshot_dir": "",
                "frame_count": 0,
                "stderr": "",
                "stdout": "",
            }
    else:
        if XVFB_RUN_BINARY:
            use_xvfb = True
        elif not os.environ.get("DISPLAY"):
            return {
                "executed": False,
                "reason": "DISPLAY is not set; SUMO-GUI requires a display server.",
                "snapshot_dir": "",
                "frame_count": 0,
                "stderr": "",
                "stdout": "",
            }

    artifacts = artifact_report.get("artifacts", {})
    generated_files = artifacts.get("generated_files", {})
    network_files = artifacts.get("network_files", {})
    output_directory = artifacts.get("output_directory")
    if not output_directory:
        return {
            "executed": False,
            "reason": "SUMO output directory is missing.",
            "snapshot_dir": "",
            "frame_count": 0,
            "stderr": "",
            "stdout": "",
        }

    output_dir = Path(output_directory).resolve()
    nodes_path = generated_files.get(network_files.get("nodes", ""))
    edges_path = generated_files.get(network_files.get("edges", ""))
    connections_path = generated_files.get(network_files.get("connections", ""))
    routes_path = generated_files.get(network_files.get("routes", ""))

    if not nodes_path or not edges_path or not connections_path or not routes_path:
        return {
            "executed": False,
            "reason": "Generated SUMO XML files are incomplete.",
            "snapshot_dir": "",
            "frame_count": 0,
            "stderr": "",
            "stdout": "",
        }

    base_name = network_files.get("nodes", "network.nodes.xml").replace(".nodes.xml", "")
    net_path = output_dir / f"{base_name}.net.xml"
    sumocfg_path = output_dir / f"{base_name}.sumocfg"

    netconvert_cmd = _netconvert_cmd(
        nodes_path=Path(str(nodes_path)),
        edges_path=Path(str(edges_path)),
        connections_path=Path(str(connections_path)),
        net_path=net_path,
    )

    try:
        subprocess.run(
            netconvert_cmd,
            cwd=str(output_dir),
            check=True,
            capture_output=True,
            text=True,
        )
    except subprocess.CalledProcessError as exc:
        return {
            "executed": False,
            "reason": "netconvert failed while compiling SUMO network for GUI.",
            "snapshot_dir": "",
            "frame_count": 0,
            "stderr": (exc.stderr or "").strip(),
            "stdout": (exc.stdout or "").strip(),
        }

    _write_sumocfg(
        sumocfg_path=sumocfg_path,
        net_path=net_path,
        route_path=Path(str(routes_path)),
        end_step=max(1, int(steps)),
    )

    snapshot_dir = output_dir / "snapshots"
    snapshot_dir.mkdir(parents=True, exist_ok=True)
    snapshot_prefix = str(snapshot_dir / "frame_")

    gui_settings_path = output_dir / "gui_viewsettings.xml"
    _write_gui_settings(gui_settings_path)
    snapshot_width = 1200
    snapshot_height = 800

    gui_cmd = [
        str(SUMO_GUI_BINARY),
        "-c",
        str(sumocfg_path),
        "--gui-settings-file",
        str(gui_settings_path),
        "--window-size",
        f"{snapshot_width},{snapshot_height}",
        "--seed",
        str(int(seed)),
        "--start",
        "true",
        "--quit-on-end",
        "true",
        "--delay",
        "0",
    ]

    if use_xvfb:
        gui_cmd = [str(XVFB_RUN_BINARY), "-a", *gui_cmd]

    traci_started = False
    try:
        traci.start(gui_cmd)  # type: ignore[name-defined]
        traci_started = True
        try:
            view_ids = traci.gui.getIDList()  # type: ignore[name-defined]
            view_id = view_ids[0] if view_ids else "View #0"
        except Exception:
            view_id = "View #0"

        try:
            traci.gui.setSchema(view_id, "flowmind")  # type: ignore[name-defined]
        except Exception:
            pass

        try:
            bounds = visualization.get("viewer_bounds")
            if not bounds:
                xs = [edge["x1"] for edge in edges] + [edge["x2"] for edge in edges]
                ys = [edge["y1"] for edge in edges] + [edge["y2"] for edge in edges]
                if xs and ys:
                    bounds = {
                        "minX": min(xs),
                        "maxX": max(xs),
                        "minY": min(ys),
                        "maxY": max(ys),
                    }
            if bounds:
                span_x = max(1.0, float(bounds["maxX"]) - float(bounds["minX"]))
                span_y = max(1.0, float(bounds["maxY"]) - float(bounds["minY"]))
                zoom = 1800.0 / max(span_x, span_y)
                zoom = max(2.0, zoom)
                center_x = float(bounds["minX"]) + span_x / 2
                center_y = float(bounds["minY"]) + span_y / 2
                traci.gui.setZoom(view_id, zoom)  # type: ignore[name-defined]
                traci.gui.setOffset(view_id, center_x, center_y)  # type: ignore[name-defined]
        except Exception:
            pass

        edge_ids: List[str] = []
        try:
            edge_ids = [
                edge_id
                for edge_id in traci.edge.getIDList()  # type: ignore[name-defined]
                if not edge_id.startswith(":")
            ]
        except Exception:
            edge_ids = []

        for step_index in range(max(1, int(steps))):
            try:
                if edge_ids and traci.vehicle.getIDCount() < 18:  # type: ignore[name-defined]
                    for i in range(3):
                        from_edge = rng.choice(edge_ids)
                        to_edge = rng.choice(edge_ids)
                        route = traci.simulation.findRoute(from_edge, to_edge)  # type: ignore[name-defined]
                        if not route.edges:
                            continue
                        route_id = f"gui_route_{step_index}_{i}"
                        traci.route.add(route_id, route.edges)  # type: ignore[name-defined]
                        vid = f"gui_{step_index}_{i}"
                        traci.vehicle.add(vid, route_id, depart="now")  # type: ignore[name-defined]
            except Exception:
                pass
            snapshot_file = snapshot_dir / f"frame_{step_index:05d}.png"
            try:
                traci.gui.screenshot(  # type: ignore[name-defined]
                    view_id, str(snapshot_file), snapshot_width, snapshot_height
                )
            except Exception:
                break
            traci.simulationStep()  # type: ignore[name-defined]
    except Exception as exc:
        return {
            "executed": False,
            "reason": "sumo-gui failed while generating snapshots.",
            "snapshot_dir": str(snapshot_dir),
            "frame_count": 0,
            "stderr": str(exc),
            "stdout": "",
        }
    finally:
        if traci_started:
            try:
                traci.close(False)  # type: ignore[name-defined]
            except Exception:
                pass

    frames = sorted(snapshot_dir.glob("frame_*.png"))
    return {
        "executed": len(frames) > 0,
        "reason": "",
        "snapshot_dir": str(snapshot_dir),
        "frame_count": len(frames),
        "stderr": "",
        "stdout": "",
    }


def _build_visualization_payload(
    nodes: List[Dict[str, Any]],
    edges: List[Dict[str, Any]],
    flows: List[Dict[str, Any]],
) -> Dict[str, Any]:
    node_map = {node["id"]: node for node in nodes}
    viz_edges: List[Dict[str, Any]] = []

    for edge in edges:
        from_node = node_map.get(edge["from"])
        to_node = node_map.get(edge["to"])
        if from_node is None or to_node is None:
            continue

        viz_edges.append(
            {
                "id": edge["id"],
                "from": edge["from"],
                "to": edge["to"],
                "lanes": edge["lanes"],
                "speed": edge["speed"],
                "length": edge["length"],
                "x1": float(from_node["x"]),
                "y1": float(from_node["y"]),
                "x2": float(to_node["x"]),
                "y2": float(to_node["y"]),
            }
        )

    return {
        "nodes": [
            {
                "id": node["id"],
                "x": float(node["x"]),
                "y": float(node["y"]),
                "type": node["type"],
            }
            for node in nodes
        ],
        "edges": viz_edges,
        "flows": [
            {
                "id": flow["id"],
                "from": flow["from"],
                "to": flow["to"],
                "probability": flow["probability"],
            }
            for flow in flows
        ],
    }


def _synthesize_runtime_from_visualization(
    artifact_report: Dict[str, Any],
    steps: int,
    seed: int,
) -> Dict[str, Any]:
    visualization = artifact_report.get("visualization", {}) or {}
    edges = visualization.get("edges", []) or []
    flows = visualization.get("flows", []) or []

    if not edges:
        return {
            "executed": False,
            "reason": "No SUMO network data available to synthesize playback.",
            "missing_requirements": [],
            "metrics": {},
            "time_series": {"queue": [], "throughput": []},
            "trace": {"frames": [], "sample_period": 1, "vehicle_limit": 0},
        }

    edge_map = {edge["id"]: edge for edge in edges}
    edge_ids = list(edge_map.keys())
    outgoing_by_node: Dict[str, List[str]] = defaultdict(list)
    for edge in edges:
        from_node = str(edge.get("from"))
        outgoing_by_node[from_node].append(edge["id"])
    rng = random.Random(seed)

    frames: List[Dict[str, Any]] = []
    queue_series: List[float] = []
    throughput_series: List[float] = []

    max_steps = max(1, int(steps))
    vehicle_limit = 280
    active: List[Dict[str, Any]] = []
    throughput_step = 0.0

    if not flows:
        flows = [{"from": edge["id"], "to": edge["id"], "probability": 0.08} for edge in edges]

    for step_index in range(max_steps):
        # Spawn new vehicles per flow
        for flow in flows:
            edge = edge_map.get(flow.get("from")) or edge_map.get(flow.get("to"))
            if not edge:
                continue
            probability = float(flow.get("probability", 0.08))
            expected = min(6.0, probability * 10.0)
            spawn = int(expected)
            if rng.random() < (expected - spawn):
                spawn += 1
            edge_id = str(edge.get("id", "edge"))
            for i in range(spawn):
                speed = 6.0 + rng.random() * 6.0
                active.append(
                    {
                        "id": f"{edge_id}-{step_index}-{i}",
                        "edge_id": edge_id,
                        "t": rng.random() * 0.05,
                        "speed": speed,
                    }
                )

        vehicles_now: List[Dict[str, Any]] = []
        still_active: List[Dict[str, Any]] = []
        throughput_step = 0.0

        for vehicle in active:
            edge = edge_map.get(vehicle["edge_id"])
            if not edge:
                continue
            dx = edge["x2"] - edge["x1"]
            dy = edge["y2"] - edge["y1"]
            length = float(edge.get("length") or math.hypot(dx, dy) or 1.0)
            dt = (vehicle["speed"] / max(1.0, length)) * 0.8
            vehicle["t"] = vehicle["t"] + dt

            if vehicle["t"] >= 1.0:
                throughput_step += 1.0
                to_node = str(edge.get("to"))
                candidates = outgoing_by_node.get(to_node, [])
                if not candidates and edge_ids:
                    candidates = edge_ids
                if candidates:
                    vehicle["edge_id"] = rng.choice(candidates)
                    vehicle["t"] = 0.0
                else:
                    continue

            edge = edge_map.get(vehicle["edge_id"])
            if not edge:
                continue
            dx = edge["x2"] - edge["x1"]
            dy = edge["y2"] - edge["y1"]
            t = vehicle["t"]
            x = edge["x1"] + dx * t
            y = edge["y1"] + dy * t
            angle = math.degrees(math.atan2(dy, dx))
            vehicles_now.append(
                {
                    "id": vehicle["id"],
                    "x": round(float(x), 2),
                    "y": round(float(y), 2),
                    "speed": round(float(vehicle["speed"]), 2),
                    "angle": round(float(angle), 1),
                }
            )
            still_active.append(vehicle)

        active = still_active[: max(1, vehicle_limit * 2)]
        total_count = len(active)
        queue_value = float(total_count) * 1.1

        queue_series.append(queue_value)
        throughput_series.append(throughput_step)

        frames.append(
            {
                "step": step_index,
                "sim_time": float(step_index),
                "vehicle_count": total_count,
                "truncated": len(vehicles_now) > vehicle_limit,
                "vehicles": vehicles_now[:vehicle_limit],
            }
        )

    avg_queue = (sum(queue_series) / len(queue_series)) if queue_series else 0.0
    throughput_total = sum(throughput_series)

    return {
        "executed": False,
        "reason": "Synthesized SUMO playback frames.",
        "missing_requirements": [],
        "metrics": {
            "avg_queue": round(avg_queue, 3),
            "throughput": round(throughput_total, 3),
        },
        "time_series": {
            "queue": queue_series,
            "throughput": throughput_series,
        },
        "trace": {
            "frames": frames,
            "sample_period": 1,
            "vehicle_limit": 280,
        },
    }


def build_sumo_artifacts(
    district_id: str,
    district_profile: Dict[str, Any],
    effective_config: Dict[str, Any],
    output_dir: str | None = None,
) -> Dict[str, Any]:
    layout = district_profile["layout"]
    nodes = _build_sumo_nodes(layout)
    edges = _build_sumo_edges(layout, nodes)
    connections = _build_connections(edges)
    flows = _build_flow_profiles(
        district_id=district_id,
        edges=edges,
        nodes=nodes,
        traffic_pattern=effective_config["traffic_pattern"],
    )

    traffic_light_count = sum(1 for node in nodes if node["type"] == "traffic_light")

    nodes_xml_lines = ["<nodes>"]
    nodes_xml_lines.extend(
        [
            f'  <node id="{node["id"]}" x="{node["x"]}" y="{node["y"]}" type="{node["type"]}" />'
            for node in nodes
        ]
    )
    nodes_xml_lines.append("</nodes>")

    edges_xml_lines = ["<edges>"]
    edges_xml_lines.extend(
        [
            f'  <edge id="{edge["id"]}" from="{edge["from"]}" to="{edge["to"]}" numLanes="{edge["lanes"]}" speed="{edge["speed"]}" length="{edge["length"]}" />'
            for edge in edges
        ]
    )
    edges_xml_lines.append("</edges>")

    connections_xml_lines = ["<connections>"]
    connections_xml_lines.extend(
        [
            f'  <connection from="{item["from"]}" to="{item["to"]}" />'
            for item in connections
        ]
    )
    connections_xml_lines.append("</connections>")

    routes_xml_lines = ["<routes>"]
    vtypes = [
        ('car_yellow', '1,0.9,0.1'),
        ('car_orange', '1,0.55,0.1'),
        ('car_green', '0.1,0.95,0.2'),
        ('car_cyan', '0.1,0.8,1'),
    ]
    for vtype_id, color in vtypes:
        routes_xml_lines.append(
            f'  <vType id="{vtype_id}" accel="1.9" decel="4.5" sigma="0.5" length="6.5" '
            f'maxSpeed="20" guiShape="passenger" color="{color}" />'
        )
    routes_xml_lines.extend(
        [
            (
                f'  <flow id="{flow["id"]}" from="{flow["from"]}" to="{flow["to"]}" '
                f'begin="{flow["begin"]}" end="{flow["end"]}" probability="{flow["probability"]}" '
                f'type="{vtypes[index % len(vtypes)][0]}" />'
            )
            for index, flow in enumerate(flows)
        ]
    )
    routes_xml_lines.append("</routes>")

    network_filenames = {
        "nodes": f"{district_id}.nodes.xml",
        "edges": f"{district_id}.edges.xml",
        "connections": f"{district_id}.connections.xml",
        "routes": f"{district_id}.rou.xml",
    }

    full_documents = {
        network_filenames["nodes"]: _render_xml(nodes_xml_lines),
        network_filenames["edges"]: _render_xml(edges_xml_lines),
        network_filenames["connections"]: _render_xml(connections_xml_lines),
        network_filenames["routes"]: _render_xml(routes_xml_lines),
    }

    generated_files: Dict[str, str] = {}
    output_directory = ""
    if output_dir:
        output_path = Path(output_dir).resolve()
        generated_files = _write_sumo_files(output_path, full_documents)
        output_directory = str(output_path)

    status = get_sumo_status()
    active_backend = "sumo_live_ready" if status["available"] else "sumo_export_fallback"
    message = (
        "Connected SUMO artifacts were generated and SUMO libraries were detected."
        if status["available"]
        else "Connected SUMO artifacts were generated; metrics are currently evaluated with the internal simulator because SUMO is not installed."
    )
    visualization = _build_visualization_payload(nodes=nodes, edges=edges, flows=flows)

    return {
        "requested_backend": "sumo",
        "active_backend": active_backend,
        "available": status["available"],
        "message": message,
        "artifacts": {
            "node_count": len(nodes),
            "edge_count": len(edges),
            "route_count": len(flows),
            "traffic_light_count": traffic_light_count,
            "connection_count": len(connections),
            "network_files": network_filenames,
            "generated_files": generated_files,
            "output_directory": output_directory,
            "netconvert_hint": (
                "netconvert --node-files <nodes.xml> --edge-files <edges.xml> "
                "--connection-files <connections.xml> --output-file <network.net.xml>"
            ),
        },
        "preview": {
            "nodes_xml": _preview_xml("nodes.xml", nodes_xml_lines),
            "edges_xml": _preview_xml("edges.xml", edges_xml_lines),
            "routes_xml": _preview_xml("routes.xml", routes_xml_lines),
            "connections_xml": _preview_xml("connections.xml", connections_xml_lines),
        },
        "visualization": visualization,
    }
