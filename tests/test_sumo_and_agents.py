import math
from pathlib import Path
import tempfile
import unittest

from app.agent import (
    DQNAgent,
    DQNHyperParams,
    PPOAgent,
    PPOHyperParams,
    QLearningAgent,
    QLearningHyperParams,
)
from app.config import DISTRICT_PROFILES
from app.sumo import build_sumo_artifacts, run_sumo_runtime


class SumoAndAgentTests(unittest.TestCase):
    def test_sumo_artifacts_are_connected_and_route_ready(self) -> None:
        profile = DISTRICT_PROFILES["downtown_core"]
        with tempfile.TemporaryDirectory() as temp_dir:
            artifacts = build_sumo_artifacts(
                district_id="downtown_core",
                district_profile=profile,
                effective_config={"traffic_pattern": "rush_hour_ns"},
                output_dir=temp_dir,
            )

            self.assertGreater(artifacts["artifacts"]["node_count"], 0)
            self.assertGreater(artifacts["artifacts"]["edge_count"], len(profile["layout"]["roads"]) * 2)
            self.assertGreater(artifacts["artifacts"]["connection_count"], 0)

            routes_preview = artifacts["preview"]["routes_xml"]
            self.assertIn('<flow id="', routes_preview)
            self.assertIn(' to="', routes_preview)

            generated_files = artifacts["artifacts"]["generated_files"]
            self.assertGreaterEqual(len(generated_files), 4)
            for path in generated_files.values():
                self.assertTrue(Path(path).exists())

            visualization = artifacts["visualization"]
            self.assertGreater(len(visualization["nodes"]), 0)
            self.assertGreater(len(visualization["edges"]), 0)

    def test_sumo_runtime_fallback_is_graceful_when_missing_runtime(self) -> None:
        profile = DISTRICT_PROFILES["downtown_core"]
        with tempfile.TemporaryDirectory() as temp_dir:
            artifacts = build_sumo_artifacts(
                district_id="downtown_core",
                district_profile=profile,
                effective_config={"traffic_pattern": "rush_hour_ns"},
                output_dir=temp_dir,
            )
            runtime = run_sumo_runtime(
                artifact_report=artifacts,
                steps=60,
                seed=42,
            )

            self.assertIn("executed", runtime)
            if not runtime["executed"]:
                self.assertIn("missing_requirements", runtime)

    def test_q_learning_uses_adaptive_learning_rate(self) -> None:
        agent = QLearningAgent(
            QLearningHyperParams(
                learning_rate=0.2,
                discount_factor=0.95,
                epsilon_start=1.0,
                epsilon_min=0.05,
                epsilon_decay=0.99,
                seed=1,
                min_learning_rate=0.05,
                learning_rate_decay_power=0.5,
            )
        )

        state = (0, 0, 0, 0, 0)
        next_state = (1, 1, 0, 0, 0)

        start_lr = agent._effective_learning_rate(state, 0)
        for _ in range(40):
            agent.update(state, 0, reward=-1.0, next_state=next_state, done=False)
        end_lr = agent._effective_learning_rate(state, 0)

        self.assertGreater(start_lr, end_lr)
        self.assertGreaterEqual(end_lr, 0.05)

    def test_dqn_update_pipeline_executes_with_prioritized_replay(self) -> None:
        agent = DQNAgent(
            DQNHyperParams(
                learning_rate=0.01,
                discount_factor=0.95,
                epsilon_start=1.0,
                epsilon_min=0.1,
                epsilon_decay=0.98,
                seed=7,
                batch_size=8,
                learning_starts=8,
                replay_capacity=256,
                target_sync_interval=16,
            )
        )

        state = (0, 0, 0, 0, 0)
        next_state = (1, 1, 1, 1, 1)
        for idx in range(48):
            action = idx % 2
            reward = -1.0 if action == 0 else -0.5
            done = idx % 11 == 0
            agent.update(state, action, reward, next_state, done)

        before_decay = agent.epsilon
        agent.decay_epsilon()
        self.assertLess(agent.epsilon, before_decay)
        self.assertGreater(agent.model_size, 0)

    def test_ppo_trains_on_terminal_episode(self) -> None:
        agent = PPOAgent(
            PPOHyperParams(
                learning_rate=0.005,
                discount_factor=0.95,
                seed=11,
                hidden_dim=16,
                ppo_epochs=3,
                minibatch_size=8,
            )
        )

        state = (0, 1, 0, 0, 0)
        next_state = (1, 1, 1, 0, 0)

        for _ in range(10):
            action = agent.select_action(state, explore=True)
            agent.update(state, action, reward=-0.2, next_state=next_state, done=False)

        final_action = agent.select_action(state, explore=True)
        agent.update(state, final_action, reward=-0.4, next_state=next_state, done=True)

        self.assertEqual(len(agent._trajectory), 0)
        self.assertTrue(math.isfinite(agent.exploration_value))


if __name__ == "__main__":
    unittest.main()
