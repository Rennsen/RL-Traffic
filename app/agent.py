from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass
import random
from typing import DefaultDict, Deque, List, Protocol, Tuple

import numpy as np

State = Tuple[int, int, int, int, int]


class RLAgent(Protocol):
    epsilon: float

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


@dataclass
class DQNHyperParams:
    learning_rate: float
    discount_factor: float
    epsilon_start: float
    epsilon_min: float
    epsilon_decay: float
    seed: int = 0
    hidden_dim: int = 24
    replay_capacity: int = 4000
    batch_size: int = 32
    target_sync_interval: int = 30


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

        self._w1 = self._np_rng.normal(0.0, 0.18, size=(input_dim, hidden_dim))
        self._b1 = np.zeros(hidden_dim, dtype=np.float64)
        self._w2 = self._np_rng.normal(0.0, 0.18, size=(hidden_dim, output_dim))
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
        _, _, next_outputs = self._forward(next_states, use_target=True)
        next_best = np.max(next_outputs, axis=1)
        targets = rewards + (1.0 - dones) * self.params.discount_factor * next_best

        selected_q = outputs[np.arange(len(batch)), actions]
        action_errors = selected_q - targets

        grad_output = np.zeros_like(outputs)
        grad_output[np.arange(len(batch)), actions] = (2.0 * action_errors) / len(batch)

        grad_w2 = hidden.T @ grad_output
        grad_b2 = np.sum(grad_output, axis=0)

        grad_hidden = grad_output @ self._w2.T
        grad_hidden[hidden_linear <= 0.0] = 0.0

        grad_w1 = states.T @ grad_hidden
        grad_b1 = np.sum(grad_hidden, axis=0)

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
