from __future__ import annotations

from typing import Any, Dict, List

from .agent import QLearningAgent, QLearningHyperParams
from .config import DISTRICT_PROFILES
from .models import SimulationRequest
from .simulation import TrafficEnvironment, generate_traffic_scenario


def list_district_catalog() -> List[Dict[str, Any]]:
    districts: List[Dict[str, Any]] = []
    for district_id, profile in DISTRICT_PROFILES.items():
        districts.append(
            {
                "district_id": district_id,
                "name": profile["name"],
                "description": profile["description"],
                "manager": profile["manager"],
                "traffic_pattern": profile["traffic_pattern"],
                "default_params": profile["default_params"],
                "actual_metrics": profile["actual_metrics"],
                "layout": profile["layout"],
            }
        )
    return districts


def _moving_average(values: List[float], window: int = 10) -> List[float]:
    smoothed: List[float] = []
    for idx in range(len(values)):
        start = max(0, idx - window + 1)
        subset = values[start : idx + 1]
        smoothed.append(round(sum(subset) / len(subset), 3))
    return smoothed


def _fixed_timer_action(step: int, fixed_cycle: int) -> int:
    if fixed_cycle <= 0:
        return 0
    return 1 if step > 0 and step % fixed_cycle == 0 else 0


def _evaluate_controller(
    mode: str,
    scenario_seed: int,
    effective_config: Dict[str, Any],
    agent: QLearningAgent | None = None,
) -> Dict[str, Any]:
    scenario = generate_traffic_scenario(
        steps=effective_config["steps_per_episode"],
        pattern=effective_config["traffic_pattern"],
        seed=scenario_seed,
        emergency_rate=effective_config["emergency_rate"],
    )
    env = TrafficEnvironment(
        scenario=scenario,
        service_rate=effective_config["service_rate"],
        switch_penalty=effective_config["switch_penalty"],
    )

    state = env.reset()
    done = False
    step = 0

    while not done:
        if mode == "rl":
            if agent is None:
                raise ValueError("Agent is required in RL mode.")
            action = agent.select_action(state, explore=False)
        else:
            action = _fixed_timer_action(step=step, fixed_cycle=effective_config["fixed_cycle"])

        state, _, done, _ = env.step(action)
        step += 1

    return {
        "metrics": env.summary(),
        "series": env.series,
    }


def _percent_delta(lower_is_better: bool, candidate_value: float, baseline_value: float) -> float:
    denominator = max(abs(baseline_value), 1e-9)
    if lower_is_better:
        return round(((baseline_value - candidate_value) / denominator) * 100.0, 2)
    return round(((candidate_value - baseline_value) / denominator) * 100.0, 2)


def _build_improvement_report(rl_metrics: Dict[str, float], fixed_metrics: Dict[str, float]) -> Dict[str, float]:
    return {
        "avg_wait_pct": _percent_delta(True, rl_metrics["avg_wait"], fixed_metrics["avg_wait"]),
        "avg_queue_pct": _percent_delta(True, rl_metrics["avg_queue"], fixed_metrics["avg_queue"]),
        "emergency_avg_wait_pct": _percent_delta(
            True,
            rl_metrics["emergency_avg_wait"],
            fixed_metrics["emergency_avg_wait"],
        ),
        "throughput_pct": _percent_delta(False, rl_metrics["throughput"], fixed_metrics["throughput"]),
        "clearance_ratio_pct": _percent_delta(
            False,
            rl_metrics["clearance_ratio"],
            fixed_metrics["clearance_ratio"],
        ),
        "remaining_vehicles_pct": _percent_delta(
            True,
            rl_metrics["remaining_vehicles"],
            fixed_metrics["remaining_vehicles"],
        ),
    }


def _resolve_effective_config(request: SimulationRequest, district_profile: Dict[str, Any]) -> Dict[str, Any]:
    config = request.model_dump()
    default_config = SimulationRequest().model_dump()

    district_defaults = district_profile["default_params"]
    for field in ("fixed_cycle", "service_rate", "emergency_rate"):
        if config[field] == default_config[field]:
            config[field] = district_defaults[field]

    if config["traffic_pattern"] == default_config["traffic_pattern"]:
        config["traffic_pattern"] = district_profile["traffic_pattern"]

    return config


def _collect_actual_benchmark(
    request: SimulationRequest,
    district_profile: Dict[str, Any],
) -> Dict[str, float]:
    actual = dict(district_profile["actual_metrics"])

    overrides = {
        "avg_wait": request.actual_avg_wait,
        "avg_queue": request.actual_avg_queue,
        "throughput": request.actual_throughput,
        "emergency_avg_wait": request.actual_emergency_avg_wait,
        "clearance_ratio": request.actual_clearance_ratio,
    }

    for metric_name, override in overrides.items():
        if override is not None:
            actual[metric_name] = float(override)

    return actual


def _build_actual_comparison(
    rl_metrics: Dict[str, float],
    fixed_metrics: Dict[str, float],
    actual_metrics: Dict[str, float],
) -> Dict[str, Dict[str, float]]:
    lower_is_better_metrics = {
        "avg_wait",
        "avg_queue",
        "emergency_avg_wait",
        "remaining_vehicles",
    }

    rl_vs_actual: Dict[str, float] = {}
    fixed_vs_actual: Dict[str, float] = {}

    for metric_name, actual_value in actual_metrics.items():
        if metric_name not in rl_metrics or metric_name not in fixed_metrics:
            continue

        lower_is_better = metric_name in lower_is_better_metrics
        rl_vs_actual[f"{metric_name}_pct"] = _percent_delta(
            lower_is_better,
            rl_metrics[metric_name],
            actual_value,
        )
        fixed_vs_actual[f"{metric_name}_pct"] = _percent_delta(
            lower_is_better,
            fixed_metrics[metric_name],
            actual_value,
        )

    return {
        "actual": actual_metrics,
        "rl_vs_actual_pct": rl_vs_actual,
        "fixed_vs_actual_pct": fixed_vs_actual,
    }


def run_experiment(request: SimulationRequest) -> Dict[str, Any]:
    district_profile = DISTRICT_PROFILES[request.district_id]
    effective_config = _resolve_effective_config(request=request, district_profile=district_profile)

    agent = QLearningAgent(
        QLearningHyperParams(
            learning_rate=effective_config["learning_rate"],
            discount_factor=effective_config["discount_factor"],
            epsilon_start=effective_config["epsilon_start"],
            epsilon_min=effective_config["epsilon_min"],
            epsilon_decay=effective_config["epsilon_decay"],
            seed=effective_config["seed"],
        )
    )

    training_rewards: List[float] = []
    training_avg_queues: List[float] = []

    for episode in range(effective_config["episodes"]):
        scenario = generate_traffic_scenario(
            steps=effective_config["steps_per_episode"],
            pattern=effective_config["traffic_pattern"],
            seed=effective_config["seed"] + episode,
            emergency_rate=effective_config["emergency_rate"],
        )
        env = TrafficEnvironment(
            scenario=scenario,
            service_rate=effective_config["service_rate"],
            switch_penalty=effective_config["switch_penalty"],
        )

        state = env.reset()
        done = False
        episode_reward = 0.0

        while not done:
            action = agent.select_action(state, explore=True)
            next_state, reward, done, _ = env.step(action)
            agent.update(state, action, reward, next_state, done)
            state = next_state
            episode_reward += reward

        training_rewards.append(round(episode_reward, 3))
        training_avg_queues.append(env.summary()["avg_queue"])
        agent.decay_epsilon()

    evaluation_seed = effective_config["seed"] + 50_000
    rl_result = _evaluate_controller(
        mode="rl",
        scenario_seed=evaluation_seed,
        effective_config=effective_config,
        agent=agent,
    )
    fixed_result = _evaluate_controller(
        mode="fixed",
        scenario_seed=evaluation_seed,
        effective_config=effective_config,
    )

    improvements = _build_improvement_report(
        rl_metrics=rl_result["metrics"],
        fixed_metrics=fixed_result["metrics"],
    )

    actual_benchmark = _collect_actual_benchmark(request=request, district_profile=district_profile)
    benchmark_report = _build_actual_comparison(
        rl_metrics=rl_result["metrics"],
        fixed_metrics=fixed_result["metrics"],
        actual_metrics=actual_benchmark,
    )

    return {
        "config": {
            "request": request.model_dump(),
            "effective": effective_config,
        },
        "district": {
            "district_id": request.district_id,
            "name": district_profile["name"],
            "description": district_profile["description"],
            "manager": district_profile["manager"],
            "layout": district_profile["layout"],
        },
        "training": {
            "episode_rewards": training_rewards,
            "moving_avg_rewards": _moving_average(training_rewards, window=12),
            "episode_avg_queue": training_avg_queues,
            "final_epsilon": round(agent.epsilon, 4),
            "q_table_size": agent.q_table_size,
        },
        "comparison": {
            "rl": rl_result["metrics"],
            "fixed": fixed_result["metrics"],
            "improvements": improvements,
        },
        "benchmark": benchmark_report,
        "time_series": {
            "rl": rl_result["series"],
            "fixed": fixed_result["series"],
        },
    }
