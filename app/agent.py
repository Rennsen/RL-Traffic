from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass
import random
from typing import DefaultDict, Deque, List, Protocol, Tuple

import numpy as np

State = Tuple[int, int, int, int, int]


class RLAgent(Protocol):
    def select_action(self, state: State, explore: bool = True) -> int:
        ...

    def update(
        self,
        state: State,
        action: int,
        reward: float,
        next_state: State,
        done: bool,
    ) -> None:
        ...

    def decay_epsilon(self) -> None:
        ...

    @property
    def model_size(self) -> int:
        ...

    @property
    def model_label(self) -> str:
        ...

    @property
    def exploration_value(self) -> float:
        ...

    @property
    def exploration_label(self) -> str:
        ...


@dataclass
class QLearningHyperParams:
    learning_rate: float
    discount_factor: float
    epsilon_start: float
    epsilon_min: float
    epsilon_decay: float
    seed: int = 0


class QLearningAgent:
    def __init__(self, params: QLearningHyperParams) -> None:
        self.params = params
        self.epsilon = params.epsilon_start
        self._rng = random.Random(params.seed)
        self._q_table: DefaultDict[State, List[float]] = defaultdict(lambda: [0.0, 0.0])

    def select_action(self, state: State, explore: bool = True) -> int:
        if explore and self._rng.random() < self.epsilon:
            return self._rng.randint(0, 1)

        action_values = self._q_table[state]
        return 0 if action_values[0] >= action_values[1] else 1

    def update(
        self,
        state: State,
        action: int,
        reward: float,
        next_state: State,
        done: bool,
    ) -> None:
        lr = self.params.learning_rate
        gamma = self.params.discount_factor

        current_q = self._q_table[state][action]
        future = 0.0 if done else max(self._q_table[next_state])
        target = reward + gamma * future

        self._q_table[state][action] = current_q + lr * (target - current_q)

    def decay_epsilon(self) -> None:
        self.epsilon = max(self.params.epsilon_min, self.epsilon * self.params.epsilon_decay)

    @property
    def model_size(self) -> int:
        return len(self._q_table)

    @property
    def model_label(self) -> str:
        return "Q-table states"

    @property
    def exploration_value(self) -> float:
        return self.epsilon

    @property
    def exploration_label(self) -> str:
        return "Final epsilon"


@dataclass
class DQNHyperParams:
    learning_rate: float
    discount_factor: float
    epsilon_start: float
    epsilon_min: float
    epsilon_decay: float
    seed: int = 0
    hidden_dim: int = 32
    replay_capacity: int = 6000
    batch_size: int = 48
    target_sync_interval: int = 24
    gradient_clip: float = 1.8


@dataclass(frozen=True)
class Transition:
    state: State
    action: int
    reward: float
    next_state: State
    done: bool


class DQNAgent:
    def __init__(self, params: DQNHyperParams) -> None:
        self.params = params
        self.epsilon = params.epsilon_start
        self._rng = random.Random(params.seed)
        self._np_rng = np.random.default_rng(params.seed)
        self._state_scale = np.array([4.0, 4.0, 1.0, 3.0, 3.0], dtype=np.float64)

        input_dim = len(self._state_scale)
        hidden_dim = params.hidden_dim
        output_dim = 2

        self._w1 = self._np_rng.normal(0.0, 0.12, size=(input_dim, hidden_dim))
        self._b1 = np.zeros(hidden_dim, dtype=np.float64)
        self._w2 = self._np_rng.normal(0.0, 0.12, size=(hidden_dim, output_dim))
        self._b2 = np.zeros(output_dim, dtype=np.float64)

        self._target_w1 = self._w1.copy()
        self._target_b1 = self._b1.copy()
        self._target_w2 = self._w2.copy()
        self._target_b2 = self._b2.copy()

        self._memory: Deque[Transition] = deque(maxlen=params.replay_capacity)
        self._train_steps = 0

    def _encode_state(self, state: State) -> np.ndarray:
        encoded = np.array(state, dtype=np.float64)
        return encoded / self._state_scale

    def _forward(
        self,
        inputs: np.ndarray,
        use_target: bool = False,
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        w1 = self._target_w1 if use_target else self._w1
        b1 = self._target_b1 if use_target else self._b1
        w2 = self._target_w2 if use_target else self._w2
        b2 = self._target_b2 if use_target else self._b2

        hidden_linear = inputs @ w1 + b1
        hidden = np.maximum(hidden_linear, 0.0)
        output = hidden @ w2 + b2
        return hidden_linear, hidden, output

    def _predict(self, state: State, use_target: bool = False) -> np.ndarray:
        inputs = self._encode_state(state).reshape(1, -1)
        _, _, output = self._forward(inputs, use_target=use_target)
        return output[0]

    def select_action(self, state: State, explore: bool = True) -> int:
        if explore and self._rng.random() < self.epsilon:
            return self._rng.randint(0, 1)

        q_values = self._predict(state)
        return int(np.argmax(q_values))

    def update(
        self,
        state: State,
        action: int,
        reward: float,
        next_state: State,
        done: bool,
    ) -> None:
        self._memory.append(
            Transition(
                state=state,
                action=action,
                reward=reward,
                next_state=next_state,
                done=done,
            )
        )

        if len(self._memory) < self.params.batch_size:
            return

        batch = self._rng.sample(list(self._memory), self.params.batch_size)
        self._train_batch(batch)
        self._train_steps += 1

        if self._train_steps % self.params.target_sync_interval == 0:
            self._sync_target_network()

    def _train_batch(self, batch: List[Transition]) -> None:
        states = np.vstack([self._encode_state(item.state) for item in batch])
        next_states = np.vstack([self._encode_state(item.next_state) for item in batch])
        actions = np.array([item.action for item in batch], dtype=np.int64)
        rewards = np.array([item.reward for item in batch], dtype=np.float64)
        dones = np.array([item.done for item in batch], dtype=np.float64)

        hidden_linear, hidden, outputs = self._forward(states)
        _, _, next_online_outputs = self._forward(next_states, use_target=False)
        _, _, next_target_outputs = self._forward(next_states, use_target=True)

        next_actions = np.argmax(next_online_outputs, axis=1)
        next_best = next_target_outputs[np.arange(len(batch)), next_actions]
        targets = rewards + (1.0 - dones) * self.params.discount_factor * next_best

        selected_q = outputs[np.arange(len(batch)), actions]
        td_error = selected_q - targets
        quadratic = np.clip(td_error, -1.0, 1.0)
        linear = td_error - quadratic
        huber_grad = (quadratic + np.sign(linear)) / len(batch)

        grad_output = np.zeros_like(outputs)
        grad_output[np.arange(len(batch)), actions] = huber_grad

        grad_w2 = hidden.T @ grad_output
        grad_b2 = np.sum(grad_output, axis=0)

        grad_hidden = grad_output @ self._w2.T
        grad_hidden[hidden_linear <= 0.0] = 0.0

        grad_w1 = states.T @ grad_hidden
        grad_b1 = np.sum(grad_hidden, axis=0)

        clip = self.params.gradient_clip
        grad_w2 = np.clip(grad_w2, -clip, clip)
        grad_b2 = np.clip(grad_b2, -clip, clip)
        grad_w1 = np.clip(grad_w1, -clip, clip)
        grad_b1 = np.clip(grad_b1, -clip, clip)

        lr = self.params.learning_rate
        self._w2 -= lr * grad_w2
        self._b2 -= lr * grad_b2
        self._w1 -= lr * grad_w1
        self._b1 -= lr * grad_b1

    def _sync_target_network(self) -> None:
        self._target_w1 = self._w1.copy()
        self._target_b1 = self._b1.copy()
        self._target_w2 = self._w2.copy()
        self._target_b2 = self._b2.copy()

    def decay_epsilon(self) -> None:
        self.epsilon = max(self.params.epsilon_min, self.epsilon * self.params.epsilon_decay)

    @property
    def model_size(self) -> int:
        return int(self._w1.size + self._b1.size + self._w2.size + self._b2.size)

    @property
    def model_label(self) -> str:
        return "DQN parameters"

    @property
    def exploration_value(self) -> float:
        return self.epsilon

    @property
    def exploration_label(self) -> str:
        return "Final epsilon"


@dataclass
class PPOHyperParams:
    learning_rate: float
    discount_factor: float
    seed: int = 0
    hidden_dim: int = 32
    clip_ratio: float = 0.2
    value_coef: float = 0.5
    entropy_coef: float = 0.02
    ppo_epochs: int = 6
    gradient_clip: float = 1.0


@dataclass(frozen=True)
class PPOTransition:
    state: State
    action: int
    reward: float
    done: bool
    old_log_prob: float
    value_estimate: float


class PPOAgent:
    def __init__(self, params: PPOHyperParams) -> None:
        self.params = params
        self._np_rng = np.random.default_rng(params.seed)
        self._state_scale = np.array([4.0, 4.0, 1.0, 3.0, 3.0], dtype=np.float64)
        self._trajectory: List[PPOTransition] = []
        self._last_entropy = 0.0

        input_dim = len(self._state_scale)
        hidden_dim = params.hidden_dim

        self._policy_w1 = self._np_rng.normal(0.0, 0.10, size=(input_dim, hidden_dim))
        self._policy_b1 = np.zeros(hidden_dim, dtype=np.float64)
        self._policy_w2 = self._np_rng.normal(0.0, 0.10, size=(hidden_dim, 2))
        self._policy_b2 = np.zeros(2, dtype=np.float64)

        self._value_w1 = self._np_rng.normal(0.0, 0.10, size=(input_dim, hidden_dim))
        self._value_b1 = np.zeros(hidden_dim, dtype=np.float64)
        self._value_w2 = self._np_rng.normal(0.0, 0.10, size=(hidden_dim, 1))
        self._value_b2 = np.zeros(1, dtype=np.float64)

    def _encode_state(self, state: State) -> np.ndarray:
        encoded = np.array(state, dtype=np.float64)
        return encoded / self._state_scale

    def _policy_forward(self, inputs: np.ndarray) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        hidden_linear = inputs @ self._policy_w1 + self._policy_b1
        hidden = np.maximum(hidden_linear, 0.0)
        logits = hidden @ self._policy_w2 + self._policy_b2
        return hidden_linear, hidden, logits

    def _value_forward(self, inputs: np.ndarray) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        hidden_linear = inputs @ self._value_w1 + self._value_b1
        hidden = np.maximum(hidden_linear, 0.0)
        values = hidden @ self._value_w2 + self._value_b2
        return hidden_linear, hidden, values

    def _softmax(self, logits: np.ndarray) -> np.ndarray:
        shifted = logits - np.max(logits, axis=1, keepdims=True)
        exp_values = np.exp(shifted)
        return exp_values / np.sum(exp_values, axis=1, keepdims=True)

    def _policy_probs(self, state: State) -> np.ndarray:
        inputs = self._encode_state(state).reshape(1, -1)
        _, _, logits = self._policy_forward(inputs)
        return self._softmax(logits)[0]

    def _state_value(self, state: State) -> float:
        inputs = self._encode_state(state).reshape(1, -1)
        _, _, values = self._value_forward(inputs)
        return float(values[0, 0])

    def select_action(self, state: State, explore: bool = True) -> int:
        probs = self._policy_probs(state)
        self._last_entropy = float(-np.sum(probs * np.log(np.clip(probs, 1e-9, 1.0))))
        if explore:
            return int(self._np_rng.choice(len(probs), p=probs))
        return int(np.argmax(probs))

    def update(
        self,
        state: State,
        action: int,
        reward: float,
        next_state: State,
        done: bool,
    ) -> None:
        probs = self._policy_probs(state)
        self._trajectory.append(
            PPOTransition(
                state=state,
                action=action,
                reward=reward,
                done=done,
                old_log_prob=float(np.log(np.clip(probs[action], 1e-9, 1.0))),
                value_estimate=self._state_value(state),
            )
        )

        if done:
            self._train_from_trajectory()
            self._trajectory.clear()

    def _train_from_trajectory(self) -> None:
        if not self._trajectory:
            return

        states = np.vstack([self._encode_state(item.state) for item in self._trajectory])
        actions = np.array([item.action for item in self._trajectory], dtype=np.int64)
        rewards = np.array([item.reward for item in self._trajectory], dtype=np.float64)
        dones = np.array([item.done for item in self._trajectory], dtype=np.float64)
        old_log_probs = np.array([item.old_log_prob for item in self._trajectory], dtype=np.float64)
        values = np.array([item.value_estimate for item in self._trajectory], dtype=np.float64)

        returns = np.zeros_like(rewards)
        running_return = 0.0
        for idx in range(len(rewards) - 1, -1, -1):
            running_return = rewards[idx] + self.params.discount_factor * running_return * (1.0 - dones[idx])
            returns[idx] = running_return

        advantages = returns - values
        advantages = (advantages - np.mean(advantages)) / (np.std(advantages) + 1e-8)

        clip = self.params.gradient_clip
        lr = self.params.learning_rate

        for _ in range(self.params.ppo_epochs):
            policy_h_linear, policy_hidden, policy_logits = self._policy_forward(states)
            probs = self._softmax(policy_logits)
            selected_probs = np.clip(probs[np.arange(len(actions)), actions], 1e-9, 1.0)
            new_log_probs = np.log(selected_probs)
            ratios = np.exp(new_log_probs - old_log_probs)

            clipped_ratios = np.clip(ratios, 1.0 - self.params.clip_ratio, 1.0 + self.params.clip_ratio)
            use_clipped = (ratios * advantages) > (clipped_ratios * advantages)

            coeff = np.zeros(len(actions), dtype=np.float64)
            coeff[~use_clipped] = -advantages[~use_clipped] * ratios[~use_clipped]

            grad_logits = probs.copy()
            grad_logits[np.arange(len(actions)), actions] -= 1.0
            grad_logits *= coeff[:, None] / len(actions)

            entropy_grad = probs * (
                np.sum(probs * (np.log(np.clip(probs, 1e-9, 1.0)) + 1.0), axis=1, keepdims=True)
                - (np.log(np.clip(probs, 1e-9, 1.0)) + 1.0)
            )
            grad_logits += self.params.entropy_coef * entropy_grad / len(actions)

            grad_policy_w2 = policy_hidden.T @ grad_logits
            grad_policy_b2 = np.sum(grad_logits, axis=0)
            grad_policy_hidden = grad_logits @ self._policy_w2.T
            grad_policy_hidden[policy_h_linear <= 0.0] = 0.0
            grad_policy_w1 = states.T @ grad_policy_hidden
            grad_policy_b1 = np.sum(grad_policy_hidden, axis=0)

            value_h_linear, value_hidden, value_outputs = self._value_forward(states)
            value_error = (value_outputs[:, 0] - returns) / len(actions)
            grad_value_output = (2.0 * self.params.value_coef * value_error).reshape(-1, 1)
            grad_value_w2 = value_hidden.T @ grad_value_output
            grad_value_b2 = np.sum(grad_value_output, axis=0)
            grad_value_hidden = grad_value_output @ self._value_w2.T
            grad_value_hidden[value_h_linear <= 0.0] = 0.0
            grad_value_w1 = states.T @ grad_value_hidden
            grad_value_b1 = np.sum(grad_value_hidden, axis=0)

            grad_policy_w2 = np.clip(grad_policy_w2, -clip, clip)
            grad_policy_b2 = np.clip(grad_policy_b2, -clip, clip)
            grad_policy_w1 = np.clip(grad_policy_w1, -clip, clip)
            grad_policy_b1 = np.clip(grad_policy_b1, -clip, clip)
            grad_value_w2 = np.clip(grad_value_w2, -clip, clip)
            grad_value_b2 = np.clip(grad_value_b2, -clip, clip)
            grad_value_w1 = np.clip(grad_value_w1, -clip, clip)
            grad_value_b1 = np.clip(grad_value_b1, -clip, clip)

            self._policy_w2 -= lr * grad_policy_w2
            self._policy_b2 -= lr * grad_policy_b2
            self._policy_w1 -= lr * grad_policy_w1
            self._policy_b1 -= lr * grad_policy_b1

            self._value_w2 -= lr * grad_value_w2
            self._value_b2 -= lr * grad_value_b2
            self._value_w1 -= lr * grad_value_w1
            self._value_b1 -= lr * grad_value_b1

        self._last_entropy = float(-np.mean(np.sum(probs * np.log(np.clip(probs, 1e-9, 1.0)), axis=1)))

    def decay_epsilon(self) -> None:
        return

    @property
    def model_size(self) -> int:
        return int(
            self._policy_w1.size
            + self._policy_b1.size
            + self._policy_w2.size
            + self._policy_b2.size
            + self._value_w1.size
            + self._value_b1.size
            + self._value_w2.size
            + self._value_b2.size
        )

    @property
    def model_label(self) -> str:
        return "PPO parameters"

    @property
    def exploration_value(self) -> float:
        return self._last_entropy

    @property
    def exploration_label(self) -> str:
        return "Policy entropy"


def build_agent(
    algorithm: str,
    learning_rate: float,
    discount_factor: float,
    epsilon_start: float,
    epsilon_min: float,
    epsilon_decay: float,
    seed: int,
) -> RLAgent:
    if algorithm == "dqn":
        return DQNAgent(
            DQNHyperParams(
                learning_rate=learning_rate,
                discount_factor=discount_factor,
                epsilon_start=epsilon_start,
                epsilon_min=epsilon_min,
                epsilon_decay=epsilon_decay,
                seed=seed,
            )
        )

    if algorithm == "ppo":
        return PPOAgent(
            PPOHyperParams(
                learning_rate=min(learning_rate, 0.05),
                discount_factor=discount_factor,
                seed=seed,
            )
        )

    return QLearningAgent(
        QLearningHyperParams(
            learning_rate=learning_rate,
            discount_factor=discount_factor,
            epsilon_start=epsilon_start,
            epsilon_min=epsilon_min,
            epsilon_decay=epsilon_decay,
            seed=seed,
        )
    )
